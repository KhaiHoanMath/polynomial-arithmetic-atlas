# Polynomial Arithmetic Atlas

A reference handbook on polynomial irreducibility and Galois groups, with results, proofs, examples, and an annotated bibliography.

The current edition contains 50 explanatory articles across 12 subjects, 94 questions, and 276 annotated references. Counts are generated from the content and may grow. Literature review date: **12 November 2026**.

Open `problems.html` for source-attributed open questions grouped by family, or `questions.html` for the complete question register, including settled cases and suggested research directions. Source dates and claimed preprint resolutions are shown separately.

## Read without installing anything

Extract `polynomial-atlas-offline.zip` and open `index.html` in a browser. Search, filters, typeset mathematics, and the example laboratory work locally. External source links require internet access. Open `handbook.html` for a continuous online edition, or `downloads/polynomial_arithmetic_atlas_handbook.pdf` for the complete typeset handbook. Its standalone LaTeX source is included beside it.

## Build and check

Requirements: Node.js 22 or newer, npm, and Python 3. The normal build uses only Python's standard library. To regenerate mathematical certificates, also install SymPy 1.14.0.

```sh
npm ci
npm run build
npm run check
```

The output is `dist/`. Routes and assets are relative, so the build works at a domain root, a GitHub project path, or from local files. Typeface and mathematics assets are included locally with dependency licenses. The website has no third-party tracking or runtime API.

For an ordinary local preview:

```sh
python3 -m http.server 8000 --directory dist
```

Open <http://localhost:8000>. A hosted development environment may provide its own preview command instead.

## Where the content lives

| Path | Purpose |
| --- | --- |
| `content/articles/*.json` | Articles, section citations, questions, prerequisites, and connections |
| `content/references.json` | Complete annotated bibliography and source metadata |
| `content/subjects.json` | The 12 subject areas |
| `content/navigation.json` | Reading paths, book guide, and method-selection table |
| `content/data/laboratory.json` | Exact precomputed examples |
| `scripts/build.mjs` | Static HTML generation and strict KaTeX rendering |
| `scripts/check.mjs` | Citation, route, asset, fragment, and document checks |
| `scripts/export_bibliography.py` | BibTeX generation |
| `scripts/package-downloads.py` | Source and offline archives plus checksums |
| `scripts/generate_handbook.py` | Optional complete handbook LaTeX generation |
| `static/assets/` | Site CSS, JavaScript, and retained Eulerian data |

The build exports `atlas_content.json`, annotated references in JSON/CSV/BibTeX, exact arithmetic scripts, editable source, and the offline website. The original 188-source PDF is a fixed earlier bibliography edition. Current pages and exports include later additions and corrections.

## Edit an article

Keep its `id` stable. Each record includes a title, subject, kind, field, status, checked date, introductory questions, sections, prerequisites, connections, and a question register. Section bodies are HTML; write inline mathematics as `\(...\)` and displays as `\[...\]`, escaping backslashes in JSON. A section citation names a reference `key` and may provide a verified `locator` and explanatory `note`.

Read [EDITORIAL.md](EDITORIAL.md) before adding a theorem or changing the status of a research problem. Do not remove hypotheses when shortening a statement. A published result, conditional theorem, reported preprint claim, exact example, and editorial research direction must be identified as such.

## Verify the examples

```sh
python3 -m pip install sympy==1.14.0
python3 scripts/atlas_certificates.py --check
python3 scripts/review_certificates.py
python3 scripts/open_problem_certificates.py
python3 static/downloads/galois_certificates.py
python3 scripts/generate_eulerian.py --check
```

The Eulerian CSV gives normalized polynomials for indices 3–30. Coefficients run from the constant term upward. Blank group entries make no assertion; a blank modular-witness entry means the specified search found none. This is a computation record, not an all-index theorem.

## Regenerate the PDF handbook

The PDF is a reviewed edition, separate from the normal website build. After changing article or reference content, regenerate and inspect it before publishing. Source generation uses only Python's standard library. PDF compilation additionally requires XeLaTeX/TeX Live, Latin Modern fonts, DejaVu Sans Mono, and the packages named in the generated preamble.

```sh
python3 scripts/generate_handbook.py --output-dir build/handbook
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build/handbook build/handbook/polynomial_arithmetic_atlas_handbook.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build/handbook build/handbook/polynomial_arithmetic_atlas_handbook.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build/handbook build/handbook/polynomial_arithmetic_atlas_handbook.tex
cp build/handbook/polynomial_arithmetic_atlas_handbook.pdf static/downloads/
cp build/handbook/polynomial_arithmetic_atlas_handbook.tex static/downloads/
cp build/handbook/handbook-manifest.json static/downloads/
npm run build
npm run check
```

The generator records source hashes in `build/handbook/handbook-manifest.json`. Check source locators, theorem hypotheses, status labels, links, and representative rendered pages as part of each new edition. The standalone `.tex` can also be edited and compiled without the JSON files.

## Publish to GitHub Pages

1. Create a GitHub repository and push this source directory to its `main` branch, including `.github/`.
2. In **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**.
3. Run **Publish the atlas to GitHub Pages** from Actions, or push a new commit to `main`.

The included workflow installs dependencies, builds, validates, and publishes `dist/`. GitHub account and repository setup are external to this archive.

See the [official GitHub Pages publishing documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

The laboratory script verifies examples without writing files by default. Use `--write` to regenerate its repository data. Compile the handbook until its table of contents and cross-references stabilize; a fresh build normally needs three passes.
