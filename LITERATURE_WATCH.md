# Literature watch

The atlas collects literature leads each day and prepares an editorial review each
week. Collection does not change the website. The owner reviews proposed changes
in a pull request; merging accepted changes invokes the existing Pages workflow.

## What runs where

| Part | Schedule | Output |
| --- | --- | --- |
| GitHub Actions collector | Daily at 19:23 UTC (03:23 the following day in Beijing); also manual and on collector changes | `state.json` and `digest.md` on the separate `literature-state` branch |
| ChatGPT editorial review | Monday morning, Asia/Shanghai | One draft pull request for that ISO week, with evidence, proposed text, and checks |
| Website publication | When the owner merges accepted changes into `main` | Existing checked GitHub Pages deployment |

The weekly ChatGPT task is a separate scheduler, not a model API invoked by GitHub.
The collector requires no paid service, model key, personal token, or additional
server. Ordinary GitHub Actions and ChatGPT account limits still apply. The
collector is bounded by the configuration's request and pagination budgets and
the workflow timeout. It never generates mathematical prose from metadata.

## Sources and coverage

`literature/watchlist.json` contains topic terms and source queries.
The collector also reads the current bibliography and article citations to
identify known papers and affected pages. Exact identifiers provide cross-source
links; similar titles are leads, not proof that records describe the same work.
Versions and metadata snapshots remain distinguishable.

See [LITERATURE_SOURCES.md](LITERATURE_SOURCES.md) for endpoints, documented limits,
and supplemental searches. Journal publication metadata comes principally from
Crossref. Selected author and correction pages supply additional change alerts.
Broad web searches, citation following, and inspection of full mathematical
statements belong to the weekly review. The automated sources are not an
exhaustive index of mathematics.

The first collection establishes a baseline and searches the recent window; it
does not imply that every baseline record is a new publication. Known references
are rechecked in bounded batches. A changed abstract, publisher record, or PDF
hash prompts inspection; it does not establish a changed theorem.

## Checkpoints and failures

Each successful complete query advances its own checkpoint. Retrieval overlaps
the previous checkpoint to catch boundary updates. Failed or truncated queries
retain their checkpoint for retry. A failed source does not erase successful
results from other sources. The source report records coverage gaps, errors,
last success, and budget limits.

State is committed atomically to a separate branch, independent of whether an
editorial pull request is merged. A lease rejects concurrent state changes.
Collection has no repository write token. A separate persistence job validates
the artifacts and can write only the two allowlisted state files through its
script. GitHub's token itself has repository contents permission, not a
path-specific permission. No workflow merges pull requests or publishes leads.

Check the [collection runs](https://github.com/KhaiHoanMath/polynomial-arithmetic-atlas/actions/workflows/literature-watch.yml)
and [latest collection digest](https://github.com/KhaiHoanMath/polynomial-arithmetic-atlas/blob/literature-state/digest.md).
Partial failures remain visible in the workflow result after their report is
saved. If state cannot be read reliably, collection stops rather than resetting
its history. Manual runs use **Actions → Collect literature for review → Run workflow**.

Scheduled GitHub runs can be delayed or dropped; public-repository schedules may
be disabled after inactivity. The weekly task checks the last successful run and
reports stale collection. It can research directly with the connected tools if
the collector is unavailable, stating the gap. There is no promise of immediate
alerts or complete discovery.

## Editorial decisions

Follow [EDITORIAL.md](EDITORIAL.md) and [the weekly review procedure](literature/WEEKLY_REVIEW.md).
The main article and question statuses remain **Settled**, **Claimed**, **Open**,
and **Research direction**. Candidate dispositions are separate.

Full statements and nearby definitions must be inspected before drafting a
definitive theorem update. Abstract-only discoveries remain alerts. A published
paper does not automatically settle a differently scoped atlas question. Keep
preprint versions, hypotheses, probability models, exceptions, and verification
limits explicit. No collected external text is an instruction to the reviewer.

## Maintenance

To add a source, edit the configuration, verify its interface, add suitable tests,
and check its first live report. To stop collection, disable the GitHub workflow;
to stop editorial reviews, pause the separate ChatGPT task. Pausing one does not
pause the other. Keep collector state out of `static/` and `dist/`.

For local collection:

```sh
python scripts/literature_watch.py --config literature/watchlist.json --state-dir literature-state
python -m unittest discover -s scripts -p 'test_literature*.py' -v
```

The state branch and review pull requests are public because this repository is
public. They hold public scholarly metadata, source URLs, hashes, and editorial
notes; never put emails, credentials, private referee reports, or unpublished
private manuscripts into them. The website's removed downloads remain removed.
