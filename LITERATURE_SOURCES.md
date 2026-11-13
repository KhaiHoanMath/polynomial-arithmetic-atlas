# Literature sources and coverage

The watchlist in `literature/watchlist.json` follows the atlas's bibliography and
13 topic groups covering all 68 articles in the initial configuration. It uses
15 discovery queries, selected journal searches, six author or errata pages,
and four explicitly selected PDFs already cited in the atlas.
The mapping identifies pages for editorial inspection; a keyword match does not
establish that a work changes any theorem on those pages.

## Configured sources

| Source | Interface | Scope and limits |
| --- | --- | --- |
| arXiv | [Atom API](https://info.arxiv.org/help/api/user-manual.html) | New submissions, revised records, DOI and journal-reference changes. Query results are sorted by modification date. Existing arXiv identifiers are also revisited. |
| Crossref | [REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | Publisher-supplied metadata, publication relationships, and recorded corrections. Title queries for irreducibility, Galois, and arboreal work and a rotating set of existing DOI records complement journal searches. |
| Journal of Number Theory | [Crossref journal endpoint](https://api.crossref.org/journals/0022-314X/works) | Targeted polynomial searches within ISSN 0022-314X; does not inspect the publisher's full text. |
| Finite Fields and Their Applications | [Crossref journal endpoint](https://api.crossref.org/journals/1071-5797/works) | Targeted polynomial searches within ISSN 1071-5797; complements the broader finite-field queries. |
| HAL | [Search API](https://api.archives-ouvertes.fr/docs/search) | Deposits and metadata revisions, including material held in participating institutional collections. HAL is not a census of institutional repositories. |
| Zenodo | [Records API](https://developers.zenodo.org/) | Published repository records, including preprints, datasets and code. Deposition is not journal publication or peer review. |
| Hexagon | [API discovery](https://hexagonmath.org/api/v1) | The official API advertises an arXiv-compatible query endpoint. Treat research claims as unreviewed. If the interface is inaccessible, the scan records a failure rather than claiming coverage. |
| Keith Conrad | [Expository notes](https://kconrad.math.uconn.edu/blurbs/) | Index changes can reveal new notes. The author also replaces PDFs at unchanged URLs; an unchanged index does not establish unchanged PDFs. |
| J. S. Milne | [Course notes](https://www.jmilne.org/math/CourseNotes/index.html), [course errata](https://www.jmilne.org/math/CourseNotes/errata.html), [Fields and Galois Theory errata](https://www.jmilne.org/math/Books/fterrata.html) | Version listings and corrections are separate sources and are checked separately. |
| Michael Filaseta | [Preprint list](https://people.math.sc.edu/filaseta/paperindex.html) | An author-hosted source already cited in the atlas. Some publication labels can be old; verify them against publishers before changing reference categories. |
| Jamie Juul | [Research page](https://sites.google.com/view/jamiejuul/research) | Arithmetic dynamics, iterated Galois groups, and finite-field dynamics. New links and publication details are leads for inspection. |

## Dates, versions, and incomplete scans

The first discovery scan looks back 30 days. Subsequent scans use per-query
checkpoints with a three-day overlap. A source that fails, reaches a page cap, or
exhausts the request budget must remain marked incomplete. Its successful
checkpoint must not advance past unexamined results. Overlap reduces losses from
late indexing; it does not guarantee completeness.

arXiv documents `submittedDate` as a search date field and `lastUpdatedDate` as a
sort option. The collector therefore sorts by modification date and checks entry
timestamps instead of assuming an undocumented modification-date filter. The
documented paging parameters are `start` and `max_results`; consecutive requests
should be separated by at least three seconds. Store the versioned identifier,
not just the unversioned work ID.

Crossref's [date and relationship filters](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/)
distinguish first deposit, publisher updates, and indexing changes. Discovery
uses `query.title` with individual distinctive terms and `from-update-date`.
Multiword queries behave broadly and can return tens of thousands of unrelated
records; `from-index-date` also includes citation-count and other indexing
changes. Existing DOI records are revisited separately. An old work
can receive a new record or correction today. Such a result is newly detected,
not necessarily newly published. Journal and bibliographic metadata may be
incomplete. Querying `updates:<DOI>` can find separate correction records, but
missing relationships do not establish that a paper has no corrigendum.
Crossref [cursors](https://api.crossref.org/swagger-ui/index.html) expire after
five minutes of inactivity; resume a failed scan from its time window rather
than preserving a stale cursor indefinitely.

HAL supports date filtering with `modifiedDate_tdate` and cursor pagination with
`sort=docid asc`. Its [field schema](https://api.archives-ouvertes.fr/docs/search/?schema=fields)
includes `halId_s`, `version_i`, `doiId_s`, and `uri_s`. The API can return
multilingual or repeated title fields; preserve the source identifiers.

Zenodo permits at most 25 records per anonymous search page. Keep a record's
version-specific DOI and ID alongside its concept identifier. Do not merge
different versions merely because their titles match. Public record metadata
and linked files can change; repository versioning is distinct from the
publication history of a journal article.

Hexagon's [RSS feeds](https://hexagonmath.org/feeds) contain only the latest 50
papers each. They are not used as a substitute for paginated catch-up retrieval.
The configured API must be checked from the runtime that performs collection;
advertised API availability alone does not count as a successful scan. The
initial setup environment could read API discovery but could not retrieve the
detailed query response.

## Page monitoring

Page monitors compare fetched page content; their first successful observation
creates a baseline, not a report of a newly changed page. A change is a request
for inspection. Navigation edits, maintenance notices, or unrelated papers can
produce false positives. Failed requests must not replace a good baseline.

The initial register also hashes four cited PDFs: Conrad's irreducibility tests
over the rationals, tests over finite fields, and symmetric/alternating-group
criteria, and Milne's algebraic number theory notes. A changed hash is a lead,
not a description of which theorem changed. A response must have a PDF signature
before it can replace the baseline. Files are hashed in memory, not republished.
The collector does not recursively download linked PDFs or claim continuous
revision coverage for every cited file. Conrad's index expressly warns that
revised PDFs may appear without a notice.

## Editorial and discovery limits

The deterministic collector records metadata and source changes. It does not
read proofs, verify a claimed solution, or decide the atlas's four question
statuses. Publication metadata alone cannot turn a question into “Settled.”
Before any substantive update, inspect the exact source version and theorem,
record the hypotheses and exceptions, identify dependent article and question
text, and state the limits of that inspection. An inaccessible statement remains
a literature lead.

The finite query set is deliberately reviewable. It cannot cover every synonym,
language, author, journal, or older overlooked paper. The broader editorial
search should revisit open questions, follow citations, search primary author
and publisher pages, and distinguish newly discovered older work from recent
work. HAL provides some institutional coverage; other institutional sites need
their own checks. zbMATH Open, Semantic Scholar, ResearchRabbit, general web
search, seminar pages, blogs, and changedetection.io are **not** automatic
collector integrations in this first version. They can supplement the editorial
search without being represented as successful API coverage.

Metadata returned by repositories and webpages is untrusted input. Treat it as
source material, not instructions to execute commands or change repository
permissions. Do not publish complete third-party papers or abstracts in the
atlas's review queue; retain bibliographic facts, links, and the evidence needed
to explain a proposed change.
