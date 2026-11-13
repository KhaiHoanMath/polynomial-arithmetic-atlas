# Polynomial Arithmetic Atlas

© 2026 Khai-Hoan Nguyen-Dang. All rights reserved. See [LICENSE](LICENSE).

A reference website on polynomial irreducibility and Galois groups, with results,
methods, examples, and annotated sources. The edition reviewed on 12 November
2026 contains 68 articles, 116 questions, and 370 references across 12 subjects.
The collection is selective; cited source versions and verification limits are
recorded in the entries.

## Build and check

Requires Node.js 22 or newer and npm.

```sh
npm ci
npm run build
npm run check
```

Only `dist/` is published. The build includes individual HTML pages, CSS,
JavaScript, the favicon, fonts, and third-party licence notices. It does not
publish the complete handbook, PDFs, TeX, archives, bibliographic exports,
source JSON, CSV tables, or verification scripts. The release check rejects
these files and download links. Search metadata includes headings and citation
keys, not duplicate full article bodies.

## Literature updates

Daily collection and a weekly editorial review keep track of new papers, revisions,
publication changes, and correction leads. See [LITERATURE_WATCH.md](LITERATURE_WATCH.md)
for the schedules, source coverage, review procedure, and failure reports. Candidate
records stay separate from website content; substantive changes require the owner's
review and merge.

## Editing articles

Edit `content/articles/*.json`, `content/references.json`, and the navigation or
subject records. Keep article and section IDs stable. Read [EDITORIAL.md](EDITORIAL.md)
before changing a theorem, source attribution, or problem status.

Optional author exports belong in `author-only/`, which is ignored by git and
excluded from the deployment. Never copy them into `static/` or `dist/`.
The generators enforce this separation. Third-party source links remain available
in the bibliography; their presence grants no republication rights.

## Verification

Install SymPy 1.14.0 to run the exact example checks:

```sh
python3 scripts/atlas_certificates.py --check
python3 scripts/review_certificates.py
python3 scripts/open_problem_certificates.py
python3 scripts/literature_certificates.py
python3 scripts/generate_eulerian.py --check
```

The retained Eulerian computation record is `content/data/eulerian.csv`.
Blank witness or group entries make no assertion. These checks verify particular
examples, not results for an entire family.

## Publication and access

The GitHub Actions workflow builds, validates, and publishes only `dist/` to
GitHub Pages. A public website necessarily sends its displayed HTML, styles,
and scripts to readers. Copyright notices are not technical copy protection.

Removing files in a commit does not erase earlier commits, forks, caches, or
copies already downloaded. A public repository exposes its source and history.
Keeping the author repository private while using GitHub Pages requires an
eligible GitHub plan; check the account's Pages eligibility before changing
visibility so the website remains available.

## Moderated comments

GraphComment Basic is registered with site-wide pre-moderation. Guest submission, approval, replies, and rejection have been tested. Registered-user posting and edits remain untested; see [COMMENTS.md](COMMENTS.md) for the owner guide, verification scope, and configuration. When enabled, comments load only after a reader selects “Show comments”; articles and questions have separate, stable discussion IDs.
