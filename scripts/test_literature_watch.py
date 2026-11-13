#!/usr/bin/env python3
"""Offline regression tests for collection, identity and isolated persistence."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse
import urllib.request
import urllib.error


HERE = Path(__file__).resolve().parent


def module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


persistence = module("persist_literature_state")
watch = module("literature_watch")

NOW = watch.timestamp("2026-11-13T00:00:00Z")
SINCE = watch.timestamp("2026-11-01T00:00:00Z")
CONFIG = {"initial_lookback_days": 30, "overlap_days": 3, "page_size": 2,
          "max_pages": 2, "existing_arxiv_budget": 10, "existing_doi_budget": 10,
          "topics": [{"id": "galois", "terms": ["Galois group", "Legendre polynomial"],
                      "articles": ["frobenius"]}]}
KNOWN = {"doi": {}, "arxiv": {}}
DYNAMICS_CONFIG = {**CONFIG, "topics": [{"id": "dynamics", "terms": ["arboreal", "dynamical irreducibility"],
                                        "articles": ["arboreal-galois"]}]}


def record(identifier="2611.00001", provider="arxiv", version="v1", doi=""):
    return {"provider": provider, "id": identifier, "title": "Galois group of a polynomial",
            "authors": ["A. Author"], "url": "https://arxiv.org/abs/" + identifier + version,
            "doi": doi, "arxiv": identifier if provider == "arxiv" else "", "version": version,
            "published": "2026-11-01T00:00:00Z", "updated": "2026-11-10T00:00:00Z",
            "journal": "", "abstract": "", "relations": {}}


def atom(entries, total=None):
    body = ['<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">']
    if total is not None:
        body.append('<opensearch:totalResults>' + str(total) + '</opensearch:totalResults>')
    for ident, updated in entries:
        body.append('<entry><id>http://arxiv.org/abs/' + ident + '</id><title>Galois groups\nof polynomials</title>'
                    '<author><name>A. Author</name></author><published>2026-01-01T00:00:00Z</published>'
                    '<updated>' + updated + '</updated><summary>Galois group</summary></entry>')
    return ''.join(body + ['</feed>']).encode()


class FakeFetcher:
    def __init__(self, values):
        self.values = iter(values)
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value

    json = get


class ParserIdentityTests(unittest.TestCase):
    def test_title_newlines_are_word_separators(self):
        records, _ = watch.atom_records(atom([("2611.00001v1", "2026-11-10T00:00:00Z")]))
        self.assertEqual(records[0]["title"], "Galois groups of polynomials")

    def test_arxiv_legacy_ids_and_versions(self):
        records, total = watch.atom_records(atom([("math/0406308v2", "2026-11-10T00:00:00Z")], 1))
        self.assertEqual((records[0]["id"], records[0]["version"], total), ("math/0406308", "v2", 1))

    def test_atom_provider_errors_and_entity_declarations_fail(self):
        error = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#bad_query</id><title>Error</title></entry></feed>'
        for payload in (error, b'<!DOCTYPE feed [<!ENTITY data "bad">]><feed/>'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                watch.atom_records(payload)

    def test_doi_canonicalization(self):
        self.assertEqual(watch.canonical_doi("https://doi.org/10.1000/ABC%2FDef"), "10.1000/abc/def")
        self.assertEqual(watch.canonical_doi("javascript:alert(1)"), "")

    def test_crossref_published_date_parts_preserved(self):
        data = watch.crossref_record({"DOI": "10.1000/test", "title": ["Galois group"],
                                     "published": {"date-parts": [[2026, 11, 12]]}})
        self.assertEqual(data["published"], "2026-11-12")

    def test_crossref_bibliographic_changes_generate_events(self):
        original = {"DOI": "10.1000/test", "title": ["Galois groups of polynomials"],
                    "volume": "12", "issue": "3", "page": "1-20", "article-number": "e123",
                    "publisher": "Example publisher", "published-online": {"date-parts": [[2026, 11, 1]]},
                    "published-print": {"date-parts": [[2026, 12, 1]]}}
        changes = [("volume", "13", "volume"), ("issue", "4", "issue"),
                   ("page", "21-40", "pages"), ("article-number", "e124", "article_number"),
                   ("publisher", "Corrected publisher", "publisher"),
                   ("published-online", {"date-parts": [[2026, 11, 2]]}, "published_online"),
                   ("published-print", {"date-parts": [[2027, 1, 1]]}, "published_print")]
        for field, value, stored_field in changes:
            with self.subTest(field=field):
                state = watch.new_state()
                before = watch.crossref_record(original)
                watch.observe(state, before, CONFIG, KNOWN, watch.iso(NOW))
                revised = copy.deepcopy(original)
                revised[field] = value
                after = watch.crossref_record(revised)
                self.assertNotEqual(before[stored_field], after[stored_field])
                self.assertTrue(watch.observe(state, after, CONFIG, KNOWN, "2026-11-14T00:00:00Z"))
                self.assertEqual(len(state["events"]), 2)

    def test_abstract_only_change_is_detected_without_storing_abstract(self):
        original = {"DOI": "10.1000/test", "title": ["Galois groups of polynomials"],
                    "abstract": "Unshared abstract evidence unique text. We prove the theorem for odd degree."}
        state = watch.new_state()
        watch.observe(state, watch.crossref_record(original), CONFIG, KNOWN, watch.iso(NOW))
        original["abstract"] = "Unshared abstract evidence unique text. We prove the theorem for even degree."
        self.assertTrue(watch.observe(state, watch.crossref_record(original), CONFIG, KNOWN, "2026-11-14T00:00:00Z"))
        self.assertNotIn("Unshared abstract evidence unique text", json.dumps(state))
        self.assertEqual(len(state["events"]), 2)
        for snapshot in state["records"]["crossref:10.1000/test"]["snapshots"]:
            self.assertNotIn("abstract", snapshot["metadata"])
            self.assertEqual(len(snapshot["metadata"]["abstract_sha256"]), 64)

    def test_abstract_markup_and_whitespace_do_not_create_false_change(self):
        data = record(identifier="10.1000/test", provider="crossref", version="", doi="10.1000/test")
        data["abstract"] = "A theorem on\nGalois groups."
        state = watch.new_state()
        watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        data["abstract"] = "<p>A theorem on Galois groups.</p>"
        self.assertFalse(watch.observe(state, data, CONFIG, KNOWN, "2026-11-14T00:00:00Z"))

    def test_zenodo_citation_is_not_work_identity(self):
        data = watch.zenodo_record({"id": 17, "metadata": {"title": "A dataset",
            "related_identifiers": [{"identifier": "https://arxiv.org/abs/2611.00001", "relation": "cites"}]}})
        self.assertEqual(data["arxiv"], "")

    def test_citation_index_uses_explicit_arxiv_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "content/articles").mkdir(parents=True)
            (root / "content/references.json").write_text(json.dumps({"references": [
                {"id": "Historical", "arxiv": "math/0406308v2", "url": "https://example.com/paper"},
                {"id": "Second", "url": "https://arxiv.org/abs/2611.00002v1"}]}))
            (root / "content/articles/a.json").write_text(json.dumps([{"id": "frobenius", "sections": [
                {"id": "cycle", "citations": [{"key": "Historical"}]}]}]))
            known = watch.citation_index(root)
            self.assertIn("math/0406308", known["arxiv"])
            self.assertIn("articles/frobenius.html#cycle", known["arxiv"]["math/0406308"]["pages"])

    def test_secondary_source_is_not_primary_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "content/articles").mkdir(parents=True)
            (root / "content/references.json").write_text(json.dumps({"references": [
                {"id": "Historical", "doi": "10.1000/old", "url": "https://example.com/paper",
                 "verification_urls": ["https://arxiv.org/abs/2611.00002v1"]}]}))
            known = watch.citation_index(root)
            self.assertNotIn("2611.00002", known["arxiv"])

    def test_plural_topic_terms_match(self):
        data = record()
        data["title"] = "Irreducibility of Legendre polynomials"
        topics, _, _ = watch.related(data, CONFIG, KNOWN)
        self.assertIn("galois", topics)

    def test_observation_keeps_versions_and_ignores_duplicate_fetch(self):
        data = record()
        state = watch.new_state()
        self.assertTrue(watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW)))
        self.assertFalse(watch.observe(state, data, CONFIG, KNOWN, "2026-11-14T00:00:00Z"))
        data["version"] = "v2"
        data["url"] = "https://arxiv.org/abs/2611.00001v2"
        self.assertTrue(watch.observe(state, data, CONFIG, KNOWN, "2026-11-15T00:00:00Z"))
        self.assertEqual(len(state["records"]["arxiv:2611.00001"]["snapshots"]), 2)
        self.assertEqual(len(state["events"]), 2)

    def test_first_scan_flags_cited_arxiv_version_difference(self):
        known = {"doi": {}, "arxiv": {"2611.00001": {
            "references": ["Existing"], "pages": ["articles/frobenius.html#cycle"],
            "cited_versions": ["v1"]}}}
        state = watch.new_state()
        watch.observe(state, record(version="v2"), CONFIG, known, watch.iso(NOW))
        self.assertEqual(state["events"][0]["kind"], "cited-version-differs")
        self.assertIn("2611.00001v2", watch.digest(state))

    def test_matching_cited_version_is_baseline(self):
        known = {"doi": {}, "arxiv": {"2611.00001": {
            "references": ["Existing"], "pages": [], "cited_versions": ["v1"]}}}
        state = watch.new_state()
        watch.observe(state, record(version="v1"), CONFIG, known, watch.iso(NOW))
        self.assertEqual(state["events"][0]["kind"], "baseline")

    def test_crossref_index_refresh_is_not_substantive_change(self):
        data = record(identifier="10.1000/test", provider="crossref", version="", doi="10.1000/test")
        state = watch.new_state()
        watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        data["updated"] = "2026-11-14T00:00:00Z"
        self.assertFalse(watch.observe(state, data, CONFIG, KNOWN, "2026-11-14T00:00:00Z"))
        self.assertEqual(len(state["events"]), 1)

    def test_added_collector_fields_are_marked_as_schema_enrichment(self):
        data = record(identifier="10.1000/test", provider="crossref", version="", doi="10.1000/test")
        state = watch.new_state()
        watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        state["records"]["crossref:10.1000/test"]["metadata_schema"] = 1
        data["volume"] = "12"
        self.assertTrue(watch.observe(state, data, CONFIG, KNOWN, "2026-11-14T00:00:00Z"))
        self.assertEqual(state["events"][-1]["kind"], "collector-schema-enriched")

    def test_real_change_during_schema_upgrade_is_not_hidden(self):
        data = record(identifier="10.1000/test", provider="crossref", version="", doi="10.1000/test")
        state = watch.new_state()
        watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        state["records"]["crossref:10.1000/test"]["metadata_schema"] = 1
        data["volume"] = "12"
        data["title"] = "Corrected Galois groups of polynomials"
        self.assertTrue(watch.observe(state, data, CONFIG, KNOWN, "2026-11-14T00:00:00Z"))
        self.assertEqual(state["events"][-1]["kind"], "changed")

    def test_correction_annotation_does_not_cause_repeated_change(self):
        data = record(identifier="10.1000/correction", provider="crossref", version="", doi="10.1000/correction")
        data["relations"]["monitored_update_of"] = "10.1000/original"
        state = watch.new_state()
        watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        saved = state["records"]["crossref:10.1000/correction"]
        saved["references"] = ["Original"]
        saved["affected_pages"] = ["articles/frobenius.html#cycle"]
        del data["relations"]["monitored_update_of"]
        self.assertFalse(watch.observe(state, data, CONFIG, KNOWN, "2026-11-14T00:00:00Z"))
        self.assertIn("Original", saved["references"])
        self.assertIn("articles/frobenius.html#cycle", saved["affected_pages"])

    def test_zenodo_versions_share_concept_group(self):
        state = watch.new_state()
        for identifier in (17, 18):
            data = watch.zenodo_record({"id": identifier, "conceptrecid": 16,
                "metadata": {"title": "Galois groups of polynomials", "version": str(identifier)}})
            watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        self.assertEqual(sorted(map(len, watch.grouped_records(state))), [2])

    def test_exact_doi_groups_but_same_title_does_not(self):
        state = watch.new_state()
        for data in (record(doi="10.1000/test"),
                     record(identifier="10.1000/test", provider="crossref", doi="10.1000/test"),
                     record(identifier="2611.00003")):
            watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        self.assertEqual(sorted(map(len, watch.grouped_records(state))), [1, 2])

    def test_digest_uses_each_event_exact_snapshot(self):
        state = watch.new_state()
        data = record()
        watch.observe(state, data, CONFIG, KNOWN, watch.iso(NOW))
        data["version"] = "v2"
        data["url"] = "https://arxiv.org/abs/2611.00001v2"
        watch.observe(state, data, CONFIG, KNOWN, "2026-11-14T00:00:00Z")
        rendered = watch.digest(state)
        self.assertIn("https://arxiv.org/abs/2611.00001v1", rendered)
        self.assertIn("https://arxiv.org/abs/2611.00001v2", rendered)


class CollectionTests(unittest.TestCase):
    def source(self, kind="arxiv", max_pages=2):
        return {"id": kind, "kind": kind, "endpoint": "https://example.com/api", "max_pages": max_pages}

    def test_arxiv_stops_below_checkpoint_not_submission_date(self):
        fetcher = FakeFetcher([atom([("2611.00001v1", "2026-11-10T00:00:00Z"),
                                     ("2601.00002v2", "2026-10-01T00:00:00Z")], 50)])
        records, complete = watch.query_records(fetcher, self.source(), {"query": "Galois"}, SINCE, NOW, CONFIG)
        self.assertTrue(complete)
        self.assertEqual([r["id"] for r in records], ["2611.00001"])
        self.assertNotIn("submittedDate", fetcher.urls[0])
        self.assertIn("lastUpdatedDate", fetcher.urls[0])

    def test_pagination_cap_retains_checkpoint_and_records(self):
        old_checkpoint = "2026-10-31T00:00:00Z"
        state = watch.new_state()
        state["sources"]["arxiv/q"] = {"last_success": old_checkpoint}
        fetcher = FakeFetcher([atom([("2611.00001v1", "2026-11-10T00:00:00Z"),
                                     ("2611.00002v1", "2026-11-09T00:00:00Z")], 10)])
        self.assertFalse(watch.scan_source(state, fetcher, self.source(max_pages=1),
                                          {"id": "q", "query": "Galois"}, CONFIG, KNOWN, NOW))
        self.assertEqual(state["sources"]["arxiv/q"]["status"], "truncated")
        self.assertEqual(state["sources"]["arxiv/q"]["last_success"], old_checkpoint)
        self.assertEqual(len(state["records"]), 2)

    def test_http_failure_does_not_advance_checkpoint(self):
        state = watch.new_state()
        state["sources"]["arxiv/q"] = {"last_success": "2026-10-31T00:00:00Z"}
        fetcher = FakeFetcher([RuntimeError("rate limit")])
        self.assertFalse(watch.scan_source(state, fetcher, self.source(),
                                          {"id": "q", "query": "Galois"}, CONFIG, KNOWN, NOW))
        self.assertEqual(state["sources"]["arxiv/q"]["last_success"], "2026-10-31T00:00:00Z")
        self.assertEqual(state["sources"]["arxiv/q"]["status"], "failed")

    def test_empty_success_advances_checkpoint(self):
        state = watch.new_state()
        self.assertTrue(watch.scan_source(state, FakeFetcher([atom([], 0)]), self.source(),
                                         {"id": "q", "query": "Galois"}, CONFIG, KNOWN, NOW))
        self.assertEqual(state["sources"]["arxiv/q"]["last_success"], watch.iso(NOW))

    def test_repeated_crossref_page_is_incomplete(self):
        response = {"message": {"items": [{"DOI": "10.1000/one", "title": ["Galois group"]},
                                          {"DOI": "10.1000/two", "title": ["Galois group"]}],
                                 "next-cursor": "*"}}
        _, complete = watch.query_records(FakeFetcher([response, copy.deepcopy(response)]), self.source("crossref"),
                                         {"query": "Galois"}, SINCE, NOW, CONFIG)
        self.assertFalse(complete)

    def test_same_crossref_cursor_with_distinct_pages_is_valid(self):
        def response(first, second):
            return {"message": {"items": [{"DOI": "10.1000/" + first, "title": ["Galois group"]},
                                           {"DOI": "10.1000/" + second, "title": ["Galois group"]}],
                                "next-cursor": "unchanged-cursor"}}
        fetcher = FakeFetcher([response("one", "two"), response("three", "four"),
                               {"message": {"items": [], "next-cursor": "unchanged-cursor"}}])
        records, complete = watch.query_records(fetcher, self.source("crossref", max_pages=3),
                                               {"query": "Galois"}, SINCE, NOW, CONFIG)
        self.assertTrue(complete)
        self.assertEqual(len(records), 4)

    def test_zenodo_anonymous_page_size_capped(self):
        fetcher = FakeFetcher([{"hits": {"hits": []}, "links": {}}])
        watch.query_records(fetcher, self.source("zenodo"), {"query": "Galois"}, SINCE, NOW,
                            {**CONFIG, "page_size": 100})
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(fetcher.urls[0]).query)["size"], ["25"])

    def test_missing_existing_arxiv_id_is_not_checked(self):
        known = {"arxiv": {"2611.00001": {"references": ["Example"], "pages": []}}, "doi": {}}
        state = watch.new_state()
        self.assertFalse(watch.check_existing(state, FakeFetcher([atom([], 0)]), CONFIG, known, NOW))
        self.assertNotIn("arxiv:2611.00001", state["reference_checks"])

    def test_correction_discovery_links_original_pages(self):
        known = {"arxiv": {}, "doi": {"10.1000/original": {
            "references": ["Original"], "pages": ["articles/frobenius.html#cycle"]}}}
        config = {**CONFIG, "existing_doi_budget": 0, "existing_correction_budget": 1}
        response = {"message": {"total-results": 1, "items": [{"DOI": "10.1000/correction",
                    "title": ["Correction"], "update-to": [{"DOI": "10.1000/original"}]}]}}
        state = watch.new_state()
        fetcher = FakeFetcher([response])
        self.assertTrue(watch.check_existing(state, fetcher, config, known, NOW))
        saved = state["records"]["crossref:10.1000/correction"]
        self.assertIn("Original", saved["references"])
        self.assertIn("articles/frobenius.html#cycle", saved["affected_pages"])
        self.assertEqual(state["reference_checks"]["corrections:10.1000/original"], watch.iso(NOW))
        self.assertIn("updates%3A10.1000%2Foriginal", fetcher.urls[0])

    def test_non_crossref_dois_are_reported_without_invalid_requests(self):
        known = {"arxiv": {}, "doi": {key: {"references": ["Existing"], "pages": []}
                 for key in ("10.48550/arxiv.2611.00001", "10.5281/zenodo.123")}}
        state = watch.new_state()
        fetcher = FakeFetcher([])
        watch.check_existing(state, fetcher, CONFIG, known, NOW)
        self.assertEqual(fetcher.urls, [])
        self.assertEqual(state["sources"]["existing-non-crossref"]["status"], "not-covered")
        self.assertEqual(len(state["sources"]["existing-non-crossref"]["identifiers"]), 2)

    def test_adaptive_backlog_only_advances_completed_window(self):
        state = watch.new_state()
        state["sources"]["crossref/q"] = {
            "last_success": "2026-10-01T00:00:00Z",
            "pending": {"since": "2026-10-01T00:00:00Z", "until": "2026-10-08T00:00:00Z",
                        "target": "2026-11-13T00:00:00Z"}}
        fetcher = FakeFetcher([{"message": {"items": []}}])
        self.assertFalse(watch.scan_source(state, fetcher, self.source("crossref"),
                                          {"id": "q", "query": "Galois"}, CONFIG, KNOWN, NOW))
        saved = state["sources"]["crossref/q"]
        self.assertEqual(saved["status"], "catching-up")
        self.assertEqual(saved["last_success"], "2026-10-08T00:00:00Z")
        self.assertEqual(saved["pending"]["since"], "2026-10-08T00:00:00Z")


class RelevanceTests(unittest.TestCase):
    def legacy_record(self, title="Paleobiogeography of arboreal marsupials"):
        legacy_config = {**DYNAMICS_CONFIG, "topics": [{"id": "dynamics",
            "terms": ["marsupial", "spider", "paleobiogeography"], "articles": ["arboreal-galois"]}]}
        data = record()
        data["title"] = title
        state = watch.new_state()
        watch.observe(state, data, legacy_config, KNOWN, watch.iso(NOW))
        self.assertEqual(len(state["events"]), 1)
        return state

    def test_standalone_arboreal_biology_is_not_a_math_match(self):
        for title in ("Paleobiogeography of arboreal marsupials", "Foraging behavior of arboreal spiders"):
            with self.subTest(title=title):
                data = record()
                data["title"] = title
                state = watch.new_state()
                self.assertFalse(watch.observe(state, data, DYNAMICS_CONFIG, KNOWN, watch.iso(NOW)))
                self.assertEqual(state["records"], {})

    def test_arboreal_mathematics_and_other_dynamics_remain_relevant(self):
        for title in ("Arboreal Galois representations", "Arboreal groups of iterated polynomials",
                      "Dynamical irreducibility in quadratic families"):
            with self.subTest(title=title):
                data = record()
                data["title"] = title
                state = watch.new_state()
                self.assertTrue(watch.observe(state, data, DYNAMICS_CONFIG, KNOWN, watch.iso(NOW)))

    def test_legacy_biology_leaves_digest_but_preserves_history(self):
        state = self.legacy_record()
        before_events = copy.deepcopy(state["events"])
        before_snapshots = copy.deepcopy(state["records"]["arxiv:2611.00001"]["snapshots"])
        self.assertEqual(watch.rescreen_legacy(state, DYNAMICS_CONFIG, KNOWN, watch.iso(NOW)), 1)
        self.assertEqual(len(state["records"]), 1)
        self.assertEqual(state["records"]["arxiv:2611.00001"]["snapshots"], before_snapshots)
        self.assertEqual([x["id"] for x in state["events"]], [x["id"] for x in before_events])
        self.assertEqual(state["events"][0]["review_status"], "screened-out")
        self.assertNotIn("Paleobiogeography", watch.digest(state))

    def test_existing_reference_is_never_auto_screened_out(self):
        state = self.legacy_record()
        known = {"doi": {}, "arxiv": {"2611.00001": {"references": ["Existing"], "pages": []}}}
        state["records"]["arxiv:2611.00001"]["references"] = ["Existing"]
        self.assertEqual(watch.rescreen_legacy(state, DYNAMICS_CONFIG, known, watch.iso(NOW)), 0)
        self.assertEqual(state["events"][0]["review_status"], "unreviewed")

    def test_later_exact_reference_restores_screened_record_to_review(self):
        state = self.legacy_record()
        self.assertEqual(watch.rescreen_legacy(state, DYNAMICS_CONFIG, KNOWN, watch.iso(NOW)), 1)
        saved = state["records"]["arxiv:2611.00001"]
        snapshots = copy.deepcopy(saved["snapshots"])
        known = {"doi": {}, "arxiv": {"2611.00001": {"references": ["NewlyCited"], "pages": []}}}
        watch.observe(state, copy.deepcopy(saved["metadata"]), DYNAMICS_CONFIG, known, "2026-11-14T00:00:00Z")
        self.assertEqual(saved["screening_status"], "eligible")
        self.assertEqual(state["events"][0]["review_status"], "unreviewed")
        self.assertEqual(saved["snapshots"], snapshots)
        self.assertEqual(len(saved["screening_history"]), 2)

    def test_correction_is_never_auto_screened_out(self):
        state = self.legacy_record()
        state["records"]["arxiv:2611.00001"]["metadata"]["relations"]["monitored_update_of"] = "10.1000/original"
        self.assertEqual(watch.rescreen_legacy(state, DYNAMICS_CONFIG, KNOWN, watch.iso(NOW)), 0)
        self.assertEqual(state["events"][0]["review_status"], "unreviewed")

    def test_absent_abstract_context_does_not_blanket_remove_old_mathematics(self):
        state = self.legacy_record()
        state["records"]["arxiv:2611.00001"]["metadata"]["title"] = "New theorems about arboreal representations"
        self.assertEqual(watch.rescreen_legacy(state, DYNAMICS_CONFIG, KNOWN, watch.iso(NOW)), 0)
        self.assertEqual(state["events"][0]["review_status"], "unreviewed")


class UntrustedInputTests(unittest.TestCase):
    def test_private_and_credential_destinations_rejected(self):
        for url in ("http://example.com", "https://127.0.0.1/x", "https://[::1]/",
                    "https://169.254.169.254/", "https://example.internal/",
                    "https://user:pass@example.com/", "https://example.com:8443/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                watch.safe_url(url, resolve=False)

    def test_private_dns_resolution_rejected(self):
        with patch.object(watch.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.2", 443))]):
            with self.assertRaises(ValueError):
                watch.safe_url("https://outside.example/path")

    def test_redirect_to_private_destination_rejected(self):
        redirect = watch.PublicRedirect()
        request = urllib.request.Request("https://example.com/")
        with self.assertRaises(ValueError):
            redirect.redirect_request(request, None, 302, "Found", {}, "https://127.0.0.1/")

    def test_request_budget_prevents_network_call(self):
        fetcher = watch.Fetcher(budget=0)
        with patch.object(watch, "safe_url", return_value="https://example.com/"), patch.object(fetcher.opener, "open") as opener:
            with self.assertRaisesRegex(RuntimeError, "budget"):
                fetcher.get("https://example.com/")
            opener.assert_not_called()

    def test_elapsed_budget_stops_before_job_timeout(self):
        fetcher = watch.Fetcher(max_seconds=-1)
        with patch.object(watch, "safe_url", return_value="https://example.com/"), patch.object(fetcher.opener, "open") as opener:
            with self.assertRaisesRegex(RuntimeError, "time budget"):
                fetcher.get("https://example.com/")
            opener.assert_not_called()

    def test_repeated_host_failure_preserves_budget_for_other_hosts(self):
        fetcher = watch.Fetcher()
        with patch.object(watch, "safe_url", side_effect=lambda url: url), patch.object(watch.time, "sleep"), \
                patch.object(fetcher.opener, "open", side_effect=TimeoutError("unavailable")) as opener:
            for _ in range(2):
                with self.assertRaises(TimeoutError):
                    fetcher.get("https://unavailable.example/api")
            self.assertEqual(opener.call_count, 6)
            with self.assertRaisesRegex(RuntimeError, "temporarily skipped"):
                fetcher.get("https://unavailable.example/another-path")
            self.assertEqual(opener.call_count, 6)
            opener.side_effect = None
            opener.return_value.__enter__.return_value.read.return_value = b"ok"
            self.assertEqual(fetcher.get("https://available.example/api"), b"ok")
            self.assertEqual(opener.call_count, 7)

    def test_missing_record_does_not_trip_host_breaker(self):
        fetcher = watch.Fetcher()
        error = urllib.error.HTTPError("https://example.com/api", 404, "Not found", {}, None)
        with patch.object(watch, "safe_url", side_effect=lambda url: url), patch.object(watch.time, "sleep"), \
                patch.object(fetcher.opener, "open", side_effect=error) as opener:
            for index in range(3):
                with self.assertRaises(urllib.error.HTTPError):
                    fetcher.get("https://example.com/record/" + str(index))
            self.assertEqual(opener.call_count, 3)
            self.assertEqual(fetcher.host_failures.get("example.com", 0), 0)

    def test_rate_limit_stops_host_without_retrying_early(self):
        fetcher = watch.Fetcher()
        error = urllib.error.HTTPError("https://example.com/api", 429, "Too many requests", {"Retry-After": "3600"}, None)
        with patch.object(watch, "safe_url", side_effect=lambda url: url), patch.object(watch.time, "sleep") as sleep, \
                patch.object(fetcher.opener, "open", side_effect=error) as opener:
            with self.assertRaises(urllib.error.HTTPError):
                fetcher.get("https://example.com/api")
            self.assertEqual(opener.call_count, 1)
            with self.assertRaises(RuntimeError):
                fetcher.get("https://example.com/another-path")
            self.assertEqual(opener.call_count, 1)
            sleep.assert_not_called()
        fresh_run = watch.Fetcher()
        self.assertEqual(fresh_run.host_failures.get("example.com", 0), 0)

    def test_successful_request_resets_host_failure_count(self):
        fetcher = watch.Fetcher()
        fetcher.host_failures["example.com"] = 1
        with patch.object(watch, "safe_url", side_effect=lambda url: url), patch.object(fetcher.opener, "open") as opener:
            opener.return_value.__enter__.return_value.read.return_value = b"ok"
            self.assertEqual(fetcher.get("https://example.com/api"), b"ok")
            self.assertEqual(fetcher.host_failures["example.com"], 0)

    def test_markdown_escapes_remote_control_syntax(self):
        escaped = watch.markdown('<script>alert(1)</script> [click](javascript:evil) @someone | bad\x01')
        self.assertNotIn("<script", escaped)
        self.assertNotIn("@someone", escaped)
        self.assertNotIn("\x01", escaped)
        self.assertIn("\\[click\\]", escaped)

    def test_page_marker_failure_preserves_checkpoint(self):
        state = watch.new_state()
        state["sources"]["notes/page"] = {"last_success": "2026-10-31T00:00:00Z"}
        source = {"id": "notes", "kind": "page", "url": "https://example.com/notes",
                  "text_contains": "Research notes", "topics": ["galois"]}
        self.assertFalse(watch.scan_source(state, FakeFetcher([b'<html>Log in to continue</html>']),
                                          source, {}, CONFIG, KNOWN, NOW))
        self.assertEqual(state["sources"]["notes/page"]["last_success"], "2026-10-31T00:00:00Z")

    def test_pdf_monitor_rejects_html_challenge(self):
        source = {"id": "notes-pdf", "url": "https://example.com/notes.pdf", "expected_format": "pdf"}
        with self.assertRaises(ValueError):
            watch.webpage_record(b'<html>Confirm you are human</html>', source)
        data = watch.webpage_record(b'%PDF-1.7\nexample bytes', source)
        self.assertEqual(len(data["version"]), 64)


def state():
    return {"schema_version": 1, "records": {}, "sources": {},
            "reference_checks": {}, "events": [], "last_run": "2026-11-13T00:00:00Z"}


class FakeGitHub:
    repository = "example/atlas"

    def __init__(self, parent=None, previous=None):
        self.parent = parent
        self.previous = previous or {}
        self.calls = []

    def head(self):
        return self.parent

    def files(self, sha):
        return self.previous

    def api(self, path, method="GET", body=None, missing_ok=False):
        self.calls.append((path, method, body))
        return {"sha": "c" * 40}


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        (self.directory / "state.json").write_bytes(persistence.json_bytes(state()))
        (self.directory / "digest.md").write_text("# Literature candidates\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def lease(self, parent=None):
        (self.directory / "lease.json").write_bytes(persistence.json_bytes({
            "schema_version": 1, "repository": "example/atlas",
            "branch": "literature-state", "parent_sha": parent,
        }))

    def test_schema_rejects_non_dictionary_records(self):
        broken = state()
        broken["records"] = []
        (self.directory / "state.json").write_bytes(persistence.json_bytes(broken))
        with self.assertRaises(persistence.StateError):
            persistence.payloads(self.directory)

    def test_symlink_payload_rejected(self):
        p = self.directory / "digest.md"
        p.unlink()
        p.symlink_to(self.directory / "state.json")
        with self.assertRaises(persistence.StateError):
            persistence.payloads(self.directory)

    def test_stale_parent_refuses_all_writes(self):
        self.lease("a" * 40)
        remote = FakeGitHub(parent="b" * 40)
        with self.assertRaisesRegex(persistence.StateError, "changed"):
            persistence.publish(remote, self.directory)
        self.assertEqual(remote.calls, [])

    def test_other_repository_lease_refuses_all_writes(self):
        self.lease()
        lease = json.loads((self.directory / "lease.json").read_text())
        lease["repository"] = "someone/else"
        (self.directory / "lease.json").write_bytes(persistence.json_bytes(lease))
        remote = FakeGitHub()
        with self.assertRaises(persistence.StateError):
            persistence.publish(remote, self.directory)
        self.assertEqual(remote.calls, [])

    def test_first_publish_is_orphan_and_contains_only_data(self):
        self.lease()
        (self.directory / "unexpected.py").write_text("raise Exception('must not be published')")
        remote = FakeGitHub()
        persistence.publish(remote, self.directory)
        tree = next(body for path, _, body in remote.calls if path == "/git/trees")
        self.assertEqual({item["path"] for item in tree["tree"]}, {"state.json", "digest.md"})
        self.assertNotIn("base_tree", tree)
        commit = next(body for path, _, body in remote.calls if path == "/git/commits")
        self.assertEqual(commit["parents"], [])
        self.assertEqual(remote.calls[-1][2]["ref"], "refs/heads/literature-state")

    def test_update_uses_parent_and_never_force(self):
        self.lease("a" * 40)
        remote = FakeGitHub(parent="a" * 40, previous={"state.json": "d" * 40, "digest.md": "e" * 40})
        persistence.publish(remote, self.directory)
        commit = next(body for path, _, body in remote.calls if path == "/git/commits")
        self.assertEqual(commit["parents"], ["a" * 40])
        self.assertEqual(remote.calls[-1][:2], ("/git/refs/heads/literature-state", "PATCH"))
        self.assertIs(remote.calls[-1][2]["force"], False)

    def test_unchanged_payload_is_noop(self):
        self.lease("a" * 40)
        previous = {name: persistence.git_blob_sha(raw)
                    for name, raw in persistence.payloads(self.directory).items()}
        remote = FakeGitHub(parent="a" * 40, previous=previous)
        persistence.publish(remote, self.directory)
        self.assertEqual(remote.calls, [])

    def test_fetch_does_not_reuse_local_stale_files(self):
        with self.assertRaisesRegex(persistence.StateError, "previous state"):
            persistence.fetch(FakeGitHub(), self.directory)

    def test_initial_absent_branch_creates_only_lease(self):
        for path in self.directory.iterdir():
            path.unlink()
        persistence.fetch(FakeGitHub(), self.directory)
        self.assertEqual({p.name for p in self.directory.iterdir()}, {"lease.json"})
        self.assertIsNone(json.loads((self.directory / "lease.json").read_text())["parent_sha"])

    def test_fetch_checksum_failure_never_writes_lease(self):
        for path in self.directory.iterdir():
            path.unlink()
        remote = FakeGitHub(parent="a" * 40, previous={"state.json": "b" * 40, "digest.md": "c" * 40})
        remote.api = lambda *args, **kwargs: {"encoding": "base64", "content": base64.b64encode(b"wrong").decode()}
        with self.assertRaisesRegex(persistence.StateError, "checksum"):
            persistence.fetch(remote, self.directory)
        self.assertFalse((self.directory / "lease.json").exists())


if __name__ == "__main__":
    unittest.main()
