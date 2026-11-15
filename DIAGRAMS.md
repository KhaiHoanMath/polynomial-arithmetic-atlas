# Connected diagrams

© 2026 Khai-Hoan Nguyen-Dang. All rights reserved.

The diagrams extend the articles with explicit mathematical dependencies. The
directory is generated at `diagrams.html`; each diagram is embedded once, beside
its explanation, and linked from the articles used by its nodes. The build also
produces a standalone SVG whose links return to the article and its evidence.

## Content records

Edit the arrays in `content/diagrams/*.json`. Keep IDs stable: they determine
article fragments, evidence-row fragments, and SVG filenames.

Each record contains:

- `id`, `title`, `summary`, `scope`, `status`, and `checked`;
- `placements`, with an existing `article` and `afterSection`;
- `nodes`, each with an `id`, short `label`, and `kind`; linked nodes also give
  an `article` and optionally a `section`;
- `edges`, each with `from`, `to`, `type`, `label`, `explanation`, and local
  `citations`; set `preprint: true` when the deduction depends on a preprint claim;
- `sources`, with local `id`, bibliography `key`, exact `locator`, versioned or
  published `url`, and an optional scope/access `note`;
- `body`, containing the precise statement, examples, exceptions, and limits;
- `related`, for explicit continuation links.

Node kinds are `object`, `hypothesis`, `method`, `result`, and `gate`. Use an
`AND` gate when multiple hypotheses are needed together, and an `OR` gate for
alternatives. A collection of arrows into a conclusion must not disguise a
missing joint hypothesis.

Arrow types are `deduction`, `equivalence`, and `flow`. Only `equivalence` gets
arrowheads at both ends. A `flow` arrow records construction or proof input;
it does not assert a new theorem. Every deduction or equivalence needs exact
support, and every source must be attached to a connection. Classical facts
quoted through a recent paper remain classical when their proof or earlier
attribution is explicit. An unreviewed new conclusion remains a preprint claim.

The diagram's publication label is separate from the four question statuses.
Adding a diagram must not automatically promote a question to “Settled”.

## Presentation and verification

The renderer in `scripts/diagrams.mjs` uses Dagre at build time. It generates
static, accessible SVG without a client-side graph library. Node links open
related explanations; numbered arrow links open the corresponding evidence
row. Native disclosures keep the article compact. The small helper in
`static/assets/site.js` reveals evidence on direct clicks and incoming fragments;
printing includes the evidence even when it was collapsed on screen.

Run the checks listed in the README. The diagram tests check typed arrowheads,
preprint styling, links, disclosure behavior, unique IDs, and layout bounds.
`scripts/check.mjs` validates both HTML and standalone SVG destinations.
`scripts/diagram_certificates.py` verifies exact displayed examples and finite
data; these checks do not certify an infinite family theorem or an entire paper.

Before publication, read the stated source version, check all parameter ranges
and low-degree cases, and inspect the rendered diagram. Keep each diagram
focused and labels short. Preserve complete hypotheses in the scope and
evidence rather than forcing them into tiny node labels. On narrow screens,
the diagram scrolls horizontally so that labels remain readable.

The live-release check compares the generated HTML, SVGs, diagram CSS, and
site JavaScript byte for byte with GitHub Pages, and checks that withdrawn or
private paths remain unavailable.
