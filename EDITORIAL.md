# Editorial conventions

© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.

The atlas is a curated mathematical handbook, not an exhaustive census of the literature or a certification of every cited proof. The current review date is 15 November 2026.

## Statements and hypotheses

Record the ground field, polynomial normalization, parameters, quantifiers, assumptions, and exact conclusion. Distinguish irreducibility, containment of the alternating group, and equality with the symmetric group. For reciprocal polynomials, identify the natural wreath-product action first.

For asymptotic results, specify what tends to infinity and what remains fixed. Fixed-degree height counting, growing-degree random coefficients, finite-field limits, and random characteristic polynomials are different models. A conditional result retains its hypothesis wherever it is summarized.

## Attribution and source checks

1. Prefer the original paper or an authoritative exposition. Give a theorem, proposition, section, or page locator only after checking it.
2. A publisher page verifies bibliographic metadata; an abstract verifies only what its authors report there. Neither by itself verifies the proof or every hypothesis of a theorem.
3. Read the theorem and nearby definitions before writing a precise statement. Check errata and version history. Keep a version-specific link for unstable preprints and a stable DOI or journal link for published work.
4. Distinguish an explicit proof supplied by the atlas from a proof sketch, a published theorem, and a reported preprint claim. Do not imply that a proof was independently checked when it was not.
5. Test boundary cases: forced factors, zero discriminants, low-degree exceptions, symmetry, and changing parameter regimes.
6. Preserve indirect attribution. If an original historical text was not inspected, say which later source supplies its statement or metadata.

Each reference has a stable key, annotation, publication status, exact links, and a checked date. Section source lists state what their citations support. A reference may be further reading without a current explanatory article.

## Questions and conjectures

Use exactly four question statuses: **Settled** (proved in published work), **Claimed** (a proof given or claimed in a preprint or unpublished work), **Open** (an unresolved question or conjecture, whether its source is published or a preprint), and **Research direction** (a suggested topic for further study). Keep publication details and conjecture attribution in the citations and body. The source validator enforces these four labels.

An open problem is scoped to a dated source. A source reporting it open does not establish that no later paper resolves it. Attribute named conjectures, distinguish editorial research directions, and label proposed preprint resolutions without promoting them to settled results.

## Corrections

Record the article ID, section ID, old statement, corrected statement, reason, and exact source or counterexample. Update summaries, method tables, questions, bibliography annotations, author-only exports, and related pages together. Preserve public article IDs; version control retains earlier text.

The original 188-source PDF is a fixed historical reading guide retained only in author archives. Current pages supersede it where corrections or additions occur. In particular, the random-models article and BlacharBreuillardKozma2026 record identify the discriminant-zero scope obstruction in version 1; they do not claim to repair or independently certify the full preprint proof.

## Examples and software

An exact calculation concerns the stated example. Keep coefficient conventions, primes, factorizations, valuations, and group-theoretic inferences explicit. Separate a search finding no witness from a proof that none exists. Numerical approximation alone is not a Galois-group certificate.

The laboratory uses exact precomputed data, not a live remote algebra system. The verification script checks products, irreducible factors, factor-degree exclusions, and Newton polygons.

## Release checklist

- Run `npm run build` and `npm run check`.
- Run exact certificate scripts when examples change.
- Validate BibTeX with a standard parser when reference fields change.
- Inspect home, a long article, bibliography, questions, and laboratory at desktop and narrow widths.
- Check representative search, filter, sort, and citation paths. Verify that removed download paths remain unavailable.
- Check that author-only exports are absent from the deployed artifact.
- Preserve the existing public audience and URL when deploying an update.

Substantive updates are editorial. The literature collector prepares candidates separately; it does not change mathematical statements or question statuses automatically.

## Review of 12 November 2026

This pass added critical-point monodromy, residual-polynomial methods, restricted coefficient models, repeated-root results, power specialization, arboreal examples, and recent algorithmic developments. It checked selected theorem statements against primary sources, compared independent readings, and tested boundary examples. It is not a complete proof audit of every reference.

The Laguerre entry records the explicit degree-one obstruction to an unrestricted power-substitution assertion in the linked source. The Wronskian entry excludes a constant remainder from irreducibility. Both observations are documented beside the relevant theorem and reference. Historical citation-verification links retain their role throughout the site. Reading paths are validated as a data graph, including IDs not rendered as links.

## Final review for GitHub Pages

The standalone summaries now retain three assumptions already present in their full statements: degree at least two for the Selmer trinomial family, characteristic zero for the Morse criterion, and a monic integral polynomial with an odd prime in the discriminant-valuation-one criterion. This pass introduces no new theorem or change to a conjecture's status. The website is regenerated from the current source records. Author-only exports are optional and are never published by the website build.

## Writing

Use direct mathematical prose and short, descriptive headings. Prefer “Example”, “Proof”, and “Remark” where appropriate; distinguish a proof from a proof sketch. Define notation before using it and explain each logical step. Remove repetition, slogans, and commentary that does not help the reader understand the mathematics. Preserve hypotheses, exceptions, attribution, and publication status when shortening text.

The exposition review of 12 November revised all 37 articles, the reading and method guides, and reference annotations. Formula strings, citation records, public identifiers, and source metadata were compared with the preceding edition.

## Literature expansion of 12 November 2026

Added 49 references, three articles, and 13 questions after searching Hexagon, arXiv, Zenodo, journal sites, and author pages. The Taylor article records Nguyen-Dang’s version 3, with separate attribution to Wei, Seki, and Sun. The update also covers sparse algorithms, Ehrhart polynomials, primitive normal bases, dynatomic geometry, local specialization, trace forms, Jacobians, and discriminant counting.

Corrected the higher-level Maeda multiplicativity discussion and recorded the original eventual-stability counterexample. The Morgan–Mullen and strong van der Waerden updates retain their preprint status. Generalized Bessel references include the published corrigendum; parameter-dependent claims not checked in the correction are not asserted. Source review checks statements, hypotheses, versions, and selected examples; it does not certify every proof or establish bibliographic completeness.


## Review before announcement · 12 November 2026

Read all 53 articles and their 107 questions, along with reading paths and method summaries. Clarified separability and degree-preserving reduction, sparse input and output conventions, reciprocal and dynatomic group bounds, fixed-degree limits, and the precise ensembles in random-matrix statements. Preprint claims retain version-specific attribution; question statuses remain Settled, Claimed, Open, or Research direction.

The release includes canonical page URLs and sharing metadata. Exact example checks, formula rendering, citation IDs, internal links, and representative browser controls were checked. This is a statement and exposition review, not an independent proof verification of every source.

## Foundations and subject expansion · 12 November 2026

The current edition contains 68 articles, 116 questions, and 370 references. This revision adds 15 articles and 44 references, with extended treatments of field extensions, the Galois correspondence, several variables, composition and iteration, finite fields, and specialization. Every article overview and the reading and method guides were reviewed for direct, precise prose.

New exact checks cover finite-field arithmetic and bases, decomposition and iteration, Newton polytopes, specialization, and Gao’s differential equations. Existing article, question, and section links are preserved. Recent preprints remain identified as claims. The review checks statements, sources, and selected examples; it does not certify the proofs of all cited works or claim an exhaustive bibliography.

## Connected diagrams · 15 November 2026

Added 19 diagrams with 170 nodes and 170 connections, embedded in 17 articles.
The catalogue now contains 387 references. Every mathematical arrow has an
explanation and an exact source locator; definitions and combined inputs are
distinguished from deductions. Preprint-dependent arrows are dashed, and
conditional results retain their hypotheses. No question status changed.

The review checked source versions and selected proof bottlenecks, including
the reciprocal square-class criterion, the fixed-field Fekete equivalence,
Legendre/Jacobi local arguments, Catalan resultants and finite witnesses, and
the selected quadratic arboreal family. Exact example checks and bounded
computations supplement the source readings. They do not amount to a complete
independent proof audit of every source or an exhaustive literature search.

Two specific proof limitations are recorded publicly:

- `orthogonal-families#jacobi-trace-forms` previously summarized the 2026
  trace-form formulas without distinguishing the normalization problem. It
  now cites the power-sum-minor method separately and records that
  arXiv:2608.12019v1, Theorem 6, gives `D_0=n/(alpha+beta+2n+1)`, whereas its
  definition in §1.2 gives `D_0=Delta_1/Delta_0=n`. That displayed diagonal
  formula is not used by the atlas. The reference annotation matches this limit.
- `laguerre#diagram-laguerre-positive-complete-strip` presents the proposed
  all-degree classification as a claim. In arXiv:2610.10614v1, Lemma 6.1(iii),
  pp. 13–14, the statement imposes simultaneous valuation bounds where its
  proof derives alternatives; further proof branches are absent from the
  statement. The later finite pruning uses that lemma. Its exhaustiveness
  under the weaker restrictions has not been verified. The exact reducible
  examples are checked separately. This is a proof concern, not a counterexample
  to the classification.

The Fekete fixed-field statement is explicitly presented as an elementary
corollary of a published recurrence, with its proof supplied. Its “Published”
label identifies the underlying source; it does not claim that the atlas's
formulation appeared there as a numbered theorem.
