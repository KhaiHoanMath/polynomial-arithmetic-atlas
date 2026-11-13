#!/usr/bin/env python3
"""Read/write the isolated literature-state branch with a checked parent lease.

Only state.json and digest.md can be written. No git checkout of downloaded
content, shell execution, forced ref update, or default-branch write is used.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BRANCH = "literature-state"
FILES = {"state.json", "digest.md"}
MAX_STATE_BYTES = 15 * 1024 * 1024
MAX_DIGEST_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 24 * 1024 * 1024


class StateError(RuntimeError):
    pass


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def state_bytes(path):
    if path.is_symlink() or not path.is_file():
        raise StateError("Missing or unsafe state.json")
    if path.stat().st_size > MAX_STATE_BYTES:
        raise StateError("state.json exceeds size limit")
    raw = path.read_bytes()
    try:
        state = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise StateError("Invalid state JSON") from exc
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise StateError("Unsupported state schema")
    for key in ("records", "sources", "reference_checks"):
        if not isinstance(state.get(key), dict):
            raise StateError("State requires dictionary: " + key)
    if not isinstance(state.get("events"), list):
        raise StateError("State requires events list")
    if not isinstance(state.get("last_run"), str):
        raise StateError("State requires last_run timestamp")
    return raw


def payloads(directory):
    state = state_bytes(directory / "state.json")
    digest_path = directory / "digest.md"
    if digest_path.is_symlink() or not digest_path.is_file():
        raise StateError("Missing or unsafe digest.md")
    if digest_path.stat().st_size > MAX_DIGEST_BYTES:
        raise StateError("digest.md exceeds size limit")
    digest = digest_path.read_bytes()
    try:
        digest.decode("utf-8")
    except UnicodeError as exc:
        raise StateError("Invalid digest UTF-8") from exc
    return {"state.json": state, "digest.md": digest}


def git_blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise StateError("Unexpected GitHub API redirect")


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise StateError("Invalid repository name")
        if not token:
            raise StateError("GITHUB_TOKEN is required")
        self.repository = repository
        self.token = token
        self.base = "https://api.github.com/repos/" + repository
        self.opener = urllib.request.build_opener(NoRedirect())

    def api(self, path, method="GET", body=None, missing_ok=False):
        if not path.startswith("/") or ".." in path:
            raise StateError("Invalid API path")
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "polynomial-arithmetic-atlas-literature-watch",
        }
        data = None if body is None else json_bytes(body)
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=60) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            # Do not print server bodies: neither credentials nor remote content
            # should be copied into workflow logs by an error message.
            raise StateError(f"GitHub {method} {path} returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            raise StateError(f"GitHub {method} request failed: {type(exc).__name__}") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise StateError("GitHub response exceeds size limit")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise StateError("GitHub returned invalid JSON") from exc

    def head(self):
        ref = self.api("/git/ref/heads/" + BRANCH, missing_ok=True)
        if ref is None:
            return None
        if ref.get("ref") != "refs/heads/" + BRANCH or ref.get("object", {}).get("type") != "commit":
            raise StateError("Unexpected state branch reference")
        sha = ref["object"]["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise StateError("Invalid state commit SHA")
        return sha

    def files(self, sha):
        commit = self.api("/git/commits/" + sha)
        tree = self.api("/git/trees/" + commit["tree"]["sha"])
        entries = tree.get("tree", [])
        if tree.get("truncated") or {e.get("path") for e in entries} != FILES:
            raise StateError("State branch contains unexpected or missing paths")
        if any(e.get("type") != "blob" or e.get("mode") != "100644" for e in entries):
            raise StateError("State branch contains unsafe file entries")
        return {e["path"]: e["sha"] for e in entries}


def fetch(github, directory):
    directory.mkdir(parents=True, exist_ok=True)
    # Refusing pre-existing files prevents a failed restore from silently
    # collecting on stale checkout data or accidentally creating a fresh state.
    if any((directory / name).exists() for name in FILES | {"lease.json"}):
        raise StateError("Restore directory must contain no previous state files")
    sha = github.head()
    if sha is not None:
        entries = github.files(sha)
        for name, blob_sha in entries.items():
            blob = github.api("/git/blobs/" + blob_sha)
            if blob.get("encoding") != "base64":
                raise StateError("Unsupported state blob encoding")
            try:
                raw = base64.b64decode("".join(blob["content"].split()), validate=True)
            except (KeyError, ValueError) as exc:
                raise StateError("Invalid encoded state blob") from exc
            if git_blob_sha(raw) != blob_sha:
                raise StateError("State blob checksum mismatch")
            (directory / name).write_bytes(raw)
        payloads(directory)
    lease = {
        "schema_version": 1,
        "repository": github.repository,
        "branch": BRANCH,
        "parent_sha": sha,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    (directory / "lease.json").write_bytes(json_bytes(lease))
    print("Restored persisted literature state." if sha else "No previous literature state; starting the first scan.")


def publish(github, directory):
    data = payloads(directory)
    lease_path = directory / "lease.json"
    if lease_path.is_symlink() or not lease_path.is_file() or lease_path.stat().st_size > 4096:
        raise StateError("Missing or unsafe parent lease")
    lease = json.loads(lease_path.read_text("utf-8"))
    if lease.get("schema_version") != 1 or lease.get("repository") != github.repository or lease.get("branch") != BRANCH:
        raise StateError("State lease is for a different repository or branch")
    parent = lease.get("parent_sha")
    if parent is not None and not re.fullmatch(r"[0-9a-f]{40}", parent):
        raise StateError("Invalid parent lease SHA")
    if github.head() != parent:
        raise StateError("State branch changed after collection; refusing to overwrite newer checkpoints")
    if parent is not None:
        previous = github.files(parent)
        if all(previous[name] == git_blob_sha(raw) for name, raw in data.items()):
            print("Literature state is unchanged.")
            return
    entries = []
    for name in sorted(FILES):
        blob = github.api("/git/blobs", "POST", {"content": base64.b64encode(data[name]).decode("ascii"), "encoding": "base64"})
        entries.append({"path": name, "type": "blob", "mode": "100644", "sha": blob["sha"]})
    # A complete tree is used, with no base tree, so code or content cannot leak
    # from the default branch into this data-only branch.
    tree = github.api("/git/trees", "POST", {"tree": entries})
    commit = github.api("/git/commits", "POST", {
        "message": "Record literature scan " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "tree": tree["sha"],
        "parents": [] if parent is None else [parent],
    })
    if parent is None:
        github.api("/git/refs", "POST", {"ref": "refs/heads/" + BRANCH, "sha": commit["sha"]})
    else:
        # If a competing update occurred after the check above, this commit is
        # not its descendant. GitHub rejects the update because force is false.
        github.api("/git/refs/heads/" + BRANCH, "PATCH", {"sha": commit["sha"], "force": False})
    print("Saved literature state: https://github.com/" + github.repository + "/tree/" + BRANCH)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "publish", "validate"])
    parser.add_argument("--state-dir", type=Path, default=Path("literature-state"))
    args = parser.parse_args()
    try:
        if args.command == "validate":
            payloads(args.state_dir)
            print("Literature state payloads validated.")
        else:
            github = GitHub(os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_TOKEN", ""))
            (fetch if args.command == "fetch" else publish)(github, args.state_dir)
    except (StateError, ValueError, KeyError, OSError) as exc:
        print("Literature persistence failed: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
