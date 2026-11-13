#!/usr/bin/env python3
"""Collect literature metadata for editorial review. Never edits atlas content.

Standard library only. Sources are untrusted data; no downloaded code is run.
Partial scans are saved with their previous successful checkpoint and exit 2.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
ATOM = {"a": "http://www.w3.org/2005/Atom", "o": "http://a9.com/-/spec/opensearch/1.1/", "x": "http://arxiv.org/schemas/atom"}
MAX_BYTES = 5_000_000
ARXIV_RE = re.compile(r"(?:arxiv(?:\.org)/(?:abs|pdf)/|arxiv:\s*)([a-z.-]+/\d{7}|\d{4}\.\d{4,5})(v\d+)?", re.I)


def iso(value=None):
    return (value or dt.datetime.now(UTC)).astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def timestamp(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except ValueError:
        return None


def clean(value, limit=2000):
    """Plain text metadata; reject hidden controls, collapse markup/whitespace."""
    if isinstance(value, list):
        value = "; ".join(str(v) for v in value)
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    value = re.sub(r"[\n\r\t]", " ", value)
    value = "".join(c for c in value if c >= " " and unicodedata.category(c) not in {"Cc", "Cf"})
    return " ".join(value.split())[:limit]


def markdown(value):
    value = clean(value)
    # Escaping HTML also prevents tags in Markdown-rendering software.
    value = html.escape(value, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value).replace("@", "＠")


def canonical_doi(value):
    value = str(value or "").strip()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value, flags=re.I)
    value = urllib.parse.unquote(value).lower()
    return value if re.fullmatch(r"10\.\d{4,9}/\S+", value) else ""


def arxiv_identifier(value):
    match = ARXIV_RE.search(str(value or ""))
    if match:
        return match.group(1).lower(), match.group(2) or ""
    return "", ""


def safe_url(url, *, resolve=True):
    """Validate every request and redirect; no local/private network destinations."""
    parsed = urllib.parse.urlsplit(str(url))
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only HTTPS URLs without credentials are allowed")
    if parsed.port not in (None, 443):
        raise ValueError("Only HTTPS port 443 is allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local hostnames are not allowed")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise ValueError("Non-public address is not allowed")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
        if resolve:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
                raise ValueError("Host resolves to a non-public address")
    return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


def display_url(value):
    value = str(value or "")
    if value.startswith("http://"):
        value = "https://" + value[7:]
    try:
        return safe_url(value, resolve=False)
    except (ValueError, TypeError):
        return ""


def url_query(endpoint, params):
    return endpoint + ("&" if "?" in endpoint else "?") + urllib.parse.urlencode(params)


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Fetcher:
    def __init__(self, budget=180, timeout=25, max_bytes=MAX_BYTES, max_seconds=900):
        self.budget = budget
        self.deadline = time.monotonic() + max_seconds
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.requests = 0
        self.last_request = {}
        self.host_failures = {}
        self.opener = urllib.request.build_opener(PublicRedirect())

    def get(self, url):
        host = urllib.parse.urlsplit(url).hostname
        if self.host_failures.get(host, 0) >= 2:
            raise RuntimeError("Host temporarily skipped after two exhausted request failures: " + str(host))
        try:
            url = safe_url(url)
        except socket.gaierror:
            self.host_failures[host] = self.host_failures.get(host, 0) + 1
            raise
        interval = 3.1 if host in {"export.arxiv.org", "arxiv.org", "hexagonmath.org"} else 0.6
        for attempt in range(3):
            if time.monotonic() >= self.deadline:
                raise RuntimeError("Run time budget exhausted")
            if self.requests >= self.budget:
                raise RuntimeError("Run request budget exhausted")
            delay = interval - (time.monotonic() - self.last_request.get(host, 0))
            if delay > 0:
                time.sleep(delay)
            self.requests += 1
            self.last_request[host] = time.monotonic()
            req = urllib.request.Request(url, headers={
                "User-Agent": "PolynomialArithmeticAtlas-LiteratureWatch/1.0 (+https://github.com/KhaiHoanMath/polynomial-arithmetic-atlas)",
                "Accept": "application/json, application/atom+xml, application/xml, text/html;q=0.8, */*;q=0.1",
            })
            try:
                with self.opener.open(req, timeout=self.timeout) as response:
                    payload = response.read(self.max_bytes + 1)
                    if len(payload) > self.max_bytes:
                        raise ValueError("Response exceeds byte limit")
                    self.host_failures[host] = 0
                    return payload
            except urllib.error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise
                if attempt == 2:
                    self.host_failures[host] = self.host_failures.get(host, 0) + 1
                    raise
                retry = exc.headers.get("Retry-After", "")
                delay = min(30, max(1, int(retry))) if retry.isdigit() else 2 ** (attempt + 1)
                time.sleep(delay)
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 2:
                    self.host_failures[host] = self.host_failures.get(host, 0) + 1
                    raise
                time.sleep(2 ** (attempt + 1))
        raise RuntimeError("Request failed")

    def json(self, url):
        return json.loads(self.get(url))


def atom_records(payload, provider="arxiv"):
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("XML declarations are not accepted")
    root = ET.fromstring(payload)
    if root.tag != "{http://www.w3.org/2005/Atom}feed":
        raise ValueError("Expected Atom feed")
    records = []
    for item in root.findall("a:entry", ATOM):
        ident = item.findtext("a:id", "", ATOM)
        if "api/errors" in ident:
            raise ValueError("Provider returned an Atom error entry")
        aid, version = arxiv_identifier(ident)
        if not aid:
            tail = urllib.parse.urlsplit(ident).path.rstrip("/").split("/")[-1]
            match = re.fullmatch(r"(.+?)(v\d+)?", tail)
            aid, version = (match.group(1), match.group(2) or "") if match else (ident, "")
        records.append({
            "provider": provider, "id": aid,
            "title": clean(item.findtext("a:title", "", ATOM)),
            "authors": [clean(x.findtext("a:name", "", ATOM)) for x in item.findall("a:author", ATOM)],
            "url": display_url(ident), "version": version,
            "published": item.findtext("a:published", "", ATOM),
            "updated": item.findtext("a:updated", "", ATOM),
            "doi": canonical_doi(item.findtext("x:doi", "", ATOM)),
            "arxiv": aid if provider == "arxiv" else "",
            "journal": clean(item.findtext("x:journal_ref", "", ATOM)),
            "abstract": clean(item.findtext("a:summary", "", ATOM), MAX_BYTES),
            "relations": {},
        })
    total = root.findtext("o:totalResults", None, ATOM)
    return records, int(total) if total is not None else None


def crossref_record(item):
    doi = canonical_doi(item.get("DOI"))
    def date(key):
        value = item.get(key) or {}
        if value.get("date-time"): return value["date-time"]
        parts = value.get("date-parts", [])
        if parts and parts[0]: return "-".join(str(x).zfill(4 if i == 0 else 2) for i, x in enumerate(parts[0]))
        return ""
    return {"provider": "crossref", "id": doi, "doi": doi, "arxiv": "", "version": "",
            "title": clean(item.get("title", [])), "authors": [clean(" ".join([x.get("given", ""), x.get("family", "")])) for x in item.get("author", [])],
            "url": "https://doi.org/" + doi, "published": date("published"),
            "updated": date("indexed") or date("deposited"), "journal": clean(item.get("container-title", [])),
            "volume": clean(item.get("volume")), "issue": clean(item.get("issue")),
            "pages": clean(item.get("page")), "article_number": clean(item.get("article-number")),
            "publisher": clean(item.get("publisher")), "published_online": date("published-online"),
            "published_print": date("published-print"),
            "abstract": clean(item.get("abstract", ""), MAX_BYTES),
            "relations": {"relation": item.get("relation", {}), "update-to": item.get("update-to", []), "type": item.get("type", "")}}


def hal_record(item):
    ident = clean(item.get("halId_s", item.get("docid", "")))
    return {"provider": "hal", "id": ident, "doi": canonical_doi(item.get("doiId_s")), "arxiv": "", "version": str(item.get("version_i", "")),
            "title": clean(item.get("title_s", [])), "authors": [clean(a) for a in item.get("authFullName_s", [])],
            "url": display_url(item.get("uri_s", "https://hal.science/" + ident)), "published": item.get("producedDate_s", ""),
            "updated": item.get("modifiedDate_tdate", item.get("modifiedDate_s", "")), "journal": clean(item.get("journalTitle_s", "")),
            "abstract": clean(item.get("abstract_s", ""), MAX_BYTES), "relations": {}}


def zenodo_record(item):
    meta = item.get("metadata", {})
    relation = meta.get("related_identifiers", [])
    aid = next((arxiv_identifier(r.get("identifier", ""))[0] for r in relation if r.get("relation", "").lower() == "isidenticalto" and arxiv_identifier(r.get("identifier", ""))[0]), "")
    return {"provider": "zenodo", "id": str(item["id"]), "doi": canonical_doi(item.get("doi", meta.get("doi", ""))), "arxiv": aid,
            "version": str(meta.get("version", item.get("id", ""))), "title": clean(meta.get("title")),
            "authors": [clean(a.get("name", "")) for a in meta.get("creators", [])],
            "url": display_url(item.get("links", {}).get("self_html", "https://zenodo.org/records/" + str(item["id"]))),
            "published": meta.get("publication_date", ""), "updated": item.get("updated", item.get("modified", "")),
            "journal": clean(meta.get("journal", {}).get("title", "")), "abstract": clean(meta.get("description", ""), MAX_BYTES),
            "relations": {"related_identifiers": relation, "conceptrecid": str(item.get("conceptrecid", "")), "files": [{"key": f.get("key"), "checksum": f.get("checksum")} for f in item.get("files", [])]}}


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}: self.hidden += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden: self.hidden -= 1
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def webpage_record(payload, source):
    url = source["url"]
    if source.get("expected_format") == "pdf" and not payload.startswith(b"%PDF"):
        raise ValueError("Expected PDF bytes; provider may have returned an HTML challenge")
    if payload.startswith(b"%PDF"):
        digest = hashlib.sha256(payload).hexdigest()
    else:
        parser = VisibleText(); parser.feed(payload.decode("utf-8", "replace"))
        text = clean(" ".join(parser.parts), MAX_BYTES)
        marker = source.get("text_contains")
        if marker and marker not in text:
            raise ValueError("Configured page marker is absent")
        digest = hashlib.sha256(text.encode()).hexdigest()
    return {"provider": "page", "id": source["id"], "doi": "", "arxiv": "", "version": digest,
            "title": source.get("title", source["id"]), "authors": [], "url": url, "published": "", "updated": "", "journal": "", "abstract": "", "relations": {"sha256": digest}}


def query_records(fetcher, source, query, since, until, config, progress=None):
    """Return (observations, complete). Pagination limits are never success."""
    kind, endpoint = source["kind"], source["endpoint"]
    page_size = int(source.get("page_size", config.get("page_size", 50)))
    page_size = max(1, min(25 if kind == "zenodo" else 100, page_size))
    max_pages = int(source.get("max_pages", config.get("max_pages", 5)))
    progress = progress if progress is not None else {}
    records, cursor, start = [], "*", 0
    seen_pages = set()
    for page in range(max_pages):
        if kind == "arxiv":
            params = {"search_query": query["query"], "start": start, "max_results": page_size, "sortBy": "lastUpdatedDate", "sortOrder": "descending"}
            batch, total = atom_records(fetcher.get(url_query(endpoint, params)), source["id"])
            if any(timestamp(r["updated"]) is None for r in batch):
                raise ValueError("Missing updated date prevents reliable catch-up")
            if not batch and total is not None and total > start:
                raise ValueError("Atom feed omits entries before its reported total")
            fresh = [r for r in batch if timestamp(r["updated"]) >= since]
            records.extend(fresh)
            if len(fresh) < len(batch) or len(batch) < page_size or (total is not None and start + len(batch) >= total):
                return records, True
            start += len(batch)
        elif kind == "crossref":
            date_filter = "update" if source.get("date_filter") == "update" else "index"
            query_parameter = source.get("query_parameter", "query")
            if query_parameter not in {"query", "query.title", "query.bibliographic"}: raise ValueError("Unsupported Crossref query parameter")
            params = {query_parameter: query["query"], "filter": "from-" + date_filter + "-date:" + since.date().isoformat() + ",until-" + date_filter + "-date:" + until.date().isoformat(), "rows": page_size, "cursor": cursor}
            message = fetcher.json(url_query(endpoint, params))["message"]
            batch = message["items"]; records.extend(crossref_record(x) for x in batch)
            if len(batch) < page_size: return records, True
            next_cursor = message.get("next-cursor")
            if not next_cursor: return records, False
            cursor = next_cursor
        elif kind == "hal":
            params = {"q": query["query"], "fq": "modifiedDate_tdate:[" + iso(since) + " TO " + iso(until) + "]", "wt": "json", "rows": page_size, "cursorMark": cursor, "sort": "docid asc", "fl": "docid,halId_s,title_s,authFullName_s,modifiedDate_tdate,version_i,doiId_s,uri_s,producedDate_s,journalTitle_s,abstract_s"}
            result = fetcher.json(url_query(endpoint, params))
            batch = result["response"]["docs"]; records.extend(hal_record(x) for x in batch)
            next_cursor = result.get("nextCursorMark")
            if len(batch) < page_size or next_cursor == cursor: return records, True
            if not next_cursor: return records, False
            cursor = next_cursor
        elif kind == "zenodo":
            params = {"q": "(" + query["query"] + ") AND updated:[" + iso(since) + " TO " + iso(until) + "]", "size": page_size, "page": page + 1, "sort": "mostrecent", "all_versions": "true"}
            result = fetcher.json(url_query(endpoint, params)); batch = result["hits"]["hits"]
            records.extend(zenodo_record(x) for x in batch)
            if len(batch) < page_size or not result.get("links", {}).get("next"): return records, True
        else:
            raise ValueError("Unsupported query source kind: " + kind)
        identities = [x.get("DOI", x.get("id", x.get("docid"))) for x in batch]
        signature = hashlib.sha256(json.dumps(identities if all(identities) else batch, sort_keys=True).encode()).hexdigest()
        if signature in seen_pages: return records, False
        seen_pages.add(signature)
    return records, False


def citation_index(root):
    refs = json.loads((root / "content/references.json").read_text())["references"]
    index = {r["id"]: [] for r in refs}
    def cited(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k == "key" and isinstance(v, str) and v in index: yield v
                else: yield from cited(v)
        elif isinstance(value, list):
            for v in value: yield from cited(v)
    for path in sorted((root / "content/articles").glob("*.json")):
        for article in json.loads(path.read_text()):
            for section in article.get("sections", []):
                target = "articles/" + article["id"] + ".html#" + section["id"]
                for key in set(cited(section)): index[key].append(target)
            target = "articles/" + article["id"] + ".html"
            for key in set(cited(article)):
                if not any(x.startswith(target) for x in index[key]): index[key].append(target)
    known = {"doi": {}, "arxiv": {}}
    for ref in refs:
        ids = {"doi": {canonical_doi(ref.get("doi"))}, "arxiv": set()}
        versions = {}
        primary_doi = canonical_doi(ref.get("doi"))
        if primary_doi.startswith("10.48550/arxiv."):
            ids["arxiv"].add(primary_doi.split("arxiv.", 1)[1])
        explicit_arxiv = str(ref.get("arxiv", ""))
        aid, version = arxiv_identifier("arxiv:" + explicit_arxiv)
        if aid:
            ids["arxiv"].add(aid)
            if version: versions.setdefault(aid, set()).add(version)
        # Secondary verification URLs may cite a DIFFERENT supporting work.
        for value in [ref.get("url", ""), ref.get("open_url", "")]:
            aid, version = arxiv_identifier(value)
            if aid:
                ids["arxiv"].add(aid)
                if version: versions.setdefault(aid, set()).add(version)
            if "doi.org/" in str(value): ids["doi"].add(canonical_doi(value))
        for namespace, values in ids.items():
            for value in values - {""}:
                entry = known[namespace].setdefault(value, {"references": [], "pages": [], "cited_versions": []})
                entry["references"].append(ref["id"]); entry["pages"].extend(index[ref["id"]])
                if namespace == "arxiv": entry["cited_versions"] = sorted(set(entry["cited_versions"]) | versions.get(value, set()))
    return known


def aliases(record):
    result = [record["provider"] + ":" + record["id"]]
    if record.get("doi"): result.append("doi:" + canonical_doi(record["doi"]))
    if record.get("arxiv"): result.append("arxiv:" + record["arxiv"])
    if record.get("provider") == "zenodo" and record.get("relations", {}).get("conceptrecid"):
        result.append("zenodo-concept:" + str(record["relations"]["conceptrecid"]))
    return sorted(set(result))


def related(record, config, known, forced_topics=()):
    text = clean(record.get("title", "") + " " + record.get("abstract", ""), 20000).casefold()
    topic_ids, pages, references = set(forced_topics), set(), set()
    for topic in config.get("topics", []):
        if any(re.search(r"(?<!\w)" + re.escape(term.casefold()) + r"s?(?!\w)", text) for term in topic.get("terms", [])):
            topic_ids.add(topic["id"])
        if topic["id"] in topic_ids:
            pages.update("articles/" + aid + ".html" for aid in topic.get("articles", []))
    for namespace in ("doi", "arxiv"):
        entry = known[namespace].get(record.get(namespace, ""))
        if entry:
            references.update(entry["references"]); pages.update(entry["pages"])
    return sorted(topic_ids), sorted(pages), sorted(references)


def observe(state, record, config, known, now, forced_topics=(), exact_reference=False):
    if not record.get("id") or not record.get("title"):
        raise ValueError("Record lacks identifier or title")
    # Query hints do not bypass relevance screening for broad search APIs.
    topics, pages, references = related(record, config, known, forced_topics if record["provider"] == "page" else ())
    if not topics and not references and not exact_reference:
        return False
    record = copy.deepcopy(record)
    abstract = clean(record.pop("abstract", ""), MAX_BYTES)
    if abstract: record["abstract_sha256"] = hashlib.sha256(abstract.encode()).hexdigest()
    record["title"] = clean(record["title"])
    key = record["provider"] + ":" + record["id"]
    substantive = copy.deepcopy(record)
    if record["provider"] == "crossref":
        substantive.pop("updated", None)
        substantive.get("relations", {}).pop("monitored_update_of", None)
    fingerprint = hashlib.sha256(json.dumps(substantive, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    previous = state["records"].get(key)
    cited_versions = known["arxiv"].get(record.get("arxiv", ""), {}).get("cited_versions", [])
    enriched_schema = False
    if previous and previous.get("metadata_schema", 1) < 2:
        old_substantive = copy.deepcopy(previous["metadata"])
        if record["provider"] == "crossref":
            old_substantive.pop("updated", None)
            old_substantive.get("relations", {}).pop("monitored_update_of", None)
        enriched_schema = all(substantive.get(k) == v for k, v in old_substantive.items())
    snapshot = {"observed_at": now, "fingerprint": fingerprint, "metadata": record}
    if previous is None:
        entry = {"first_seen": now, "last_seen": now, "snapshots": [snapshot]}
    else:
        entry = previous; entry["last_seen"] = now
        if entry["fingerprint"] != fingerprint: entry["snapshots"].append(snapshot)
    if previous:
        pages = sorted(set(pages + previous.get("affected_pages", [])))
        references = sorted(set(references + previous.get("references", [])))
    changed = previous is None or entry.get("fingerprint") != fingerprint
    entry.update({"metadata_schema": 2, "fingerprint": fingerprint, "metadata": record, "aliases": aliases(record), "topics": topics, "affected_pages": pages, "references": references, "cited_versions": cited_versions})
    state["records"][key] = entry
    if changed:
        event_id = hashlib.sha256((key + ":" + fingerprint).encode()).hexdigest()[:20]
        if not any(e["id"] == event_id for e in state["events"]):
            kind = "baseline" if previous is None and (references or record["provider"] == "page") else "new" if previous is None else "changed"
            if enriched_schema: kind = "collector-schema-enriched"
            if previous is None and record["provider"] == "arxiv" and cited_versions and record.get("version") and record["version"] not in cited_versions:
                kind = "cited-version-differs"
            state["events"].append({"id": event_id, "record": key, "detected_at": now, "kind": kind, "fingerprint": fingerprint, "review_status": "unreviewed"})
    return changed


def new_state():
    return {"schema_version": 1, "last_run": None, "records": {}, "sources": {}, "reference_checks": {}, "reference_attempts": {}, "reference_errors": {}, "events": []}


def validate_state(state):
    if not isinstance(state, dict) or state.get("schema_version") != 1: raise ValueError("Unsupported state schema")
    for key in ("records", "sources", "reference_checks"):
        if not isinstance(state.get(key), dict): raise ValueError("Invalid state field: " + key)
    if not isinstance(state.get("events"), list): raise ValueError("Invalid events")
    # Backward-compatible addition; never replace successful-check timestamps.
    for key in ("reference_attempts", "reference_errors"):
        if key not in state: state[key] = {}
        if not isinstance(state[key], dict): raise ValueError("Invalid state field: " + key)
    return state


def scan_source(state, fetcher, source, query, config, known, now):
    key = source["id"] + "/" + query.get("id", "page")
    previous = state["sources"].get(key, {})
    since = (timestamp(previous.get("last_success")) or now - dt.timedelta(days=config.get("initial_lookback_days", 30))) - dt.timedelta(days=config.get("overlap_days", 3))
    until, target = now, now
    progress = {}
    pending = previous.get("pending", {})
    if pending:
        since = timestamp(pending["since"]); until = timestamp(pending["until"]); target = timestamp(pending["target"])
        progress = {"offset": pending.get("offset", 0)}
    status = {**previous, "last_attempt": iso(now), "status": "failed", "items": 0, "error": ""}
    try:
        if source["kind"] == "page":
            records, complete = [webpage_record(fetcher.get(source["url"]), source)], True
        else:
            records, complete = query_records(fetcher, source, query, since, until, config, progress)
        for record in records:
            observe(state, record, config, known, iso(now), source.get("topics", []))
        status.update(status="ok" if complete else "truncated", items=len(records))
        if complete:
            status["last_success"] = iso(until)
            status.pop("pending", None)
            if until < target:
                width = max(dt.timedelta(days=1), until - since)
                status["pending"] = {"since": iso(until), "until": iso(min(target, until + width)), "target": iso(target)}
                status["status"] = "catching-up"
                status["error"] = "Completed one date window; later backlog remains"
        else:
            # Crossref cursors expire: continue using bounded date windows, not stale cursors.
            if source["kind"] in {"crossref", "hal", "zenodo"}:
                narrowed = since + (until - since) / 2
                if until - since > dt.timedelta(days=1): until = max(since + dt.timedelta(days=1), narrowed)
                status["pending"] = {"since": iso(since), "until": iso(until), "target": iso(target)}
            else:
                # Atom result order can change between runs. Restart from offset 0;
                # do not claim completeness from a persisted offset into a mutable feed.
                status["pending"] = {"since": iso(since), "until": iso(until), "target": iso(target)}
            status["error"] = "Pagination limit or repeated page; previous checkpoint retained; backlog saved"
    except Exception as exc:
        status["error"] = clean(type(exc).__name__ + ": " + str(exc), 500)
    state["sources"][key] = status
    return status["status"] == "ok"


def check_existing(state, fetcher, config, known, now):
    """Fair rotation by last attempt; failures never masquerade as success."""
    outcomes = []
    non_crossref = sorted(doi for doi in known["doi"] if doi.startswith(("10.48550/", "10.5281/", "10.5169/")))
    if non_crossref:
        state["sources"]["existing-non-crossref"] = {"last_attempt": iso(now), "status": "not-covered", "items": 0, "identifiers": non_crossref, "error": f"{len(non_crossref)} known non-Crossref DOIs excluded from Crossref checks; arXiv identifiers are checked separately; other repository updates require editorial follow-up"}
    for namespace, budget in (("arxiv", int(config.get("existing_arxiv_budget", 100))), ("doi", int(config.get("existing_doi_budget", 25))), ("corrections", int(config.get("existing_correction_budget", 10)))):
        registry = known["doi" if namespace == "corrections" else namespace]
        if namespace in {"doi", "corrections"}: registry = {key: value for key, value in registry.items() if key not in non_crossref}
        identifiers = sorted(registry, key=lambda k: (state["reference_attempts"].get(namespace + ":" + k, ""), k))[:budget]
        errors, processed = [], 0
        groups = [identifiers[i:i+40] for i in range(0, len(identifiers), 40)] if namespace == "arxiv" else [[x] for x in identifiers]
        for group in groups:
            for ident in group: state["reference_attempts"][namespace + ":" + ident] = iso(now)
            try:
                if namespace == "arxiv":
                    records, _ = atom_records(fetcher.get(url_query("https://export.arxiv.org/api/query", {"id_list": ",".join(group), "max_results": len(group)})))
                    returned = {r["arxiv"] for r in records}
                elif namespace == "doi":
                    response = fetcher.json("https://api.crossref.org/works/" + urllib.parse.quote(group[0], safe=""))
                    records = [crossref_record(response["message"])]; returned = {r["doi"] for r in records}
                else:
                    response = fetcher.json(url_query("https://api.crossref.org/works", {"filter": "updates:" + group[0], "rows": 100}))
                    message = response["message"]; records = [crossref_record(r) for r in message["items"]]
                    if message.get("total-results", len(records)) > len(records):
                        raise ValueError("Correction lookup truncated")
                    returned = set(group)
                for record in records:
                    if namespace == "corrections":
                        record["relations"]["monitored_update_of"] = group[0]
                    observe(state, record, config, known, iso(now), exact_reference=True)
                    if namespace == "corrections":
                        saved = state["records"][record["provider"] + ":" + record["id"]]
                        saved["references"] = sorted(set(saved["references"] + registry[group[0]]["references"]))
                        saved["affected_pages"] = sorted(set(saved["affected_pages"] + registry[group[0]]["pages"]))
                for ident in group:
                    key = namespace + ":" + ident
                    if ident not in returned:
                        error = "Provider omitted " + ident; errors.append(error); state["reference_errors"][key] = {"at": iso(now), "error": error}
                    else:
                        state["reference_checks"][key] = iso(now); state["reference_errors"].pop(key, None); processed += 1
            except Exception as exc:
                error = clean(type(exc).__name__ + ": " + str(exc), 200)
                for ident in group:
                    state["reference_errors"][namespace + ":" + ident] = {"at": iso(now), "error": error}
                errors.append(", ".join(group) + ": " + error)
        key = "existing-" + namespace
        status = {**state["sources"].get(key, {}), "last_attempt": iso(now), "status": "failed" if errors else "ok", "items": processed, "scheduled": len(identifiers), "total_registered": len(registry), "error": "; ".join(errors)[:1200]}
        if not errors: status["last_success"] = iso(now)
        state["sources"][key] = status; outcomes.append(not errors)
    return all(outcomes)


def grouped_records(state):
    """Connected components of exact identifiers; title similarity is never identity."""
    parent = {k: k for k in state["records"]}
    def find(key):
        while parent[key] != key: parent[key] = parent[parent[key]]; key = parent[key]
        return key
    owners = {}
    for key, item in state["records"].items():
        for alias in item["aliases"]:
            if alias in owners: parent[find(key)] = find(owners[alias])
            else: owners[alias] = key
    groups = {}
    for key in parent: groups.setdefault(find(key), []).append(key)
    return list(groups.values())


def digest(state):
    lines = ["# Literature watch", "", "Last attempted scan: " + str(state["last_run"]), "", "Metadata leads for editorial review. A match or changed file does not verify a mathematical claim. Baselines record existing sources; they are not new publications.", "", "## Source coverage", "", "| Source / query | Result | Items | Last complete check | Detail |", "|---|---|---:|---|---|"]
    for key, value in sorted(state["sources"].items()):
        detail = value.get("error", "")
        if "total_registered" in value:
            detail = f"Rotating batch: {value.get('scheduled', 0)} attempted of {value['total_registered']} registered. " + detail
        lines.append("| " + " | ".join([markdown(key), value["status"], str(value["items"]), str(value.get("last_success", "never")), markdown(detail)]) + " |")
    lines += ["", "## Unreviewed discoveries and changes", ""]
    events = [e for e in state["events"] if e.get("review_status") == "unreviewed" and e["kind"] != "baseline"]
    for event in sorted(events, key=lambda e: (e["detected_at"], e["id"]), reverse=True)[:150]:
        item = state["records"][event["record"]]
        meta = next((s["metadata"] for s in item["snapshots"] if s["fingerprint"] == event["fingerprint"]), item["metadata"])
        lines += ["### " + markdown(meta["title"]), "", "- Event: `" + event["id"] + "` (" + event["kind"] + ", detected " + event["detected_at"] + ")", "- Source: " + markdown(meta["provider"]) + "; version: " + markdown(meta.get("version") or "metadata only")]
        if meta.get("url"): lines.append("- Link: <" + meta["url"].replace(">", "%3E").replace("<", "%3C") + ">")
        if item.get("cited_versions"): lines.append("- Versions cited by atlas: " + ", ".join(markdown(v) for v in item["cited_versions"]))
        if item["references"]: lines.append("- Existing reference keys: " + ", ".join(markdown(x) for x in item["references"]))
        if item["affected_pages"]: lines.append("- Possible affected pages: " + ", ".join("`" + p + "`" for p in item["affected_pages"]))
        lines += ["- Check the exact statement, definitions, version history and corrections before proposing text.", ""]
    if not events: lines.append("No unreviewed non-baseline events are currently recorded.")
    if len(events) > 150: lines.append("Showing the latest 150 of " + str(len(events)) + " events; state.json retains the complete queue.")
    lines += ["", "## Record totals", "", str(len(state["records"])) + " source records; " + str(len(grouped_records(state))) + " groups linked by exact identifiers. Similar titles alone are not merged.", "", "Metadata and webpage monitoring are selective. Failed or truncated scans retain their previous checkpoint. The weekly editor also searches outside this source register.", ""]
    return "\n".join(lines)


def validate_config(config):
    if config.get("version") != 1: raise ValueError("Unsupported configuration version")
    ids = set()
    for source in config.get("sources", []):
        if source["id"] in ids: raise ValueError("Duplicate source ID")
        ids.add(source["id"])
        if source.get("kind") not in {"arxiv", "crossref", "hal", "zenodo", "page"}: raise ValueError("Unknown source kind")
        safe_url(source.get("url") if source["kind"] == "page" else source.get("endpoint"), resolve=False)
        qids = set()
        for query in source.get("queries", []):
            if query["id"] in qids: raise ValueError("Duplicate query ID")
            qids.add(query["id"])
    for key in ("request_budget", "max_pages", "page_size"):
        if key in config and (not isinstance(config[key], int) or config[key] <= 0): raise ValueError("Invalid " + key)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="literature/watchlist.json")
    parser.add_argument("--state-dir", default="literature-state")
    parser.add_argument("--root", default=".")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv); root = Path(args.root).resolve()
    config = json.loads(Path(args.config).read_text()); validate_config(config)
    directory = Path(args.state_dir); state_path = directory / "state.json"
    state = validate_state(json.loads(state_path.read_text())) if state_path.exists() else new_state()
    if args.validate_only:
        print("Configuration and state schema validated"); return 0
    known = citation_index(root); fetcher = Fetcher(config.get("request_budget", 180)); now = dt.datetime.now(UTC)
    outcomes = []
    # Existing reference revisions have priority over broad discovery.
    outcomes.append(check_existing(state, fetcher, config, known, now))
    for source in config.get("sources", []):
        if not source.get("enabled", True): continue
        queries = [{}] if source["kind"] == "page" else source.get("queries", [])
        for query in queries: outcomes.append(scan_source(state, fetcher, source, query, config, known, now))
    state["last_run"] = iso(now); state["request_count"] = fetcher.requests
    state["last_run_complete"] = all(outcomes)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n"); temporary.replace(state_path)
    (directory / "digest.md").write_text(digest(state))
    print(json.dumps({"complete": all(outcomes), "requests": fetcher.requests, "records": len(state["records"]), "sources": len(state["sources"])}))
    return 0 if all(outcomes) else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("Fatal collector error: " + clean(str(error), 1000), file=sys.stderr)
        sys.exit(1)
