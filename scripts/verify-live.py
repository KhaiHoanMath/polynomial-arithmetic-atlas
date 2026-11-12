#!/usr/bin/env python3
# Copyright © 2026 Khai-Hoan Nguyen-Dang. All rights reserved.
"""Compare the deployed HTML with the build and check withdrawn file paths."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BASE = "https://khaihoanmath.github.io/polynomial-arithmetic-atlas/"
REVISION = os.environ.get("GITHUB_SHA", "release-check")
REMOVED = [
    "downloads/polynomial_arithmetic_atlas_handbook.pdf",
    "downloads/polynomial_arithmetic_atlas_handbook.tex",
    "handbook.html",
    "downloads/polynomial-atlas-offline.zip",
    "downloads/polynomial-atlas-source.zip",
    "downloads/atlas_references.bib",
    "downloads/atlas_references.json",
    "downloads/atlas_references.csv",
    "downloads/atlas_content.json",
    "downloads/atlas_certificates.py",
    "downloads/review_certificates.py",
    "downloads/polynomial_bibliography.pdf",
    "content/references.json",
    "content/articles/random.json",
    "scripts/build.mjs",
    "author-only/bibliography/atlas_references.bib",
]

def check(item):
    relative, expected = item
    url = urljoin(BASE, relative) + "?release=" + REVISION
    reason = ""
    for attempt in range(5):
        try:
            request = Request(url, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=20) as response:
                actual = response.read()
                if expected is None:
                    reason = "withdrawn file returned HTTP " + str(response.status)
                elif actual == expected:
                    return None
                else:
                    reason = "deployed HTML differs from the build"
        except HTTPError as error:
            if expected is None and error.code == 404:
                return None
            reason = "HTTP " + str(error.code)
        except (URLError, TimeoutError, OSError) as error:
            reason = str(error)
        if attempt < 4:
            time.sleep(5)
    return relative + ": " + reason

def main():
    pages = [(p.relative_to(DIST).as_posix(), p.read_bytes())
             for p in sorted(DIST.rglob("*.html"))]
    if not pages:
        raise SystemExit("No built HTML to verify.")
    tasks = pages + [(path, None) for path in REMOVED]
    with ThreadPoolExecutor(max_workers=6) as pool:
        failures = [result for result in pool.map(check, tasks) if result]
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print(f"Verified {len(pages)} live HTML pages byte for byte; "
          f"{len(REMOVED)} withdrawn or private file paths returned 404.")

if __name__ == "__main__":
    main()
