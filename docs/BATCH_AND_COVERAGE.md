# Real-model batch test and coverage labels

The Plan screen labels every skill with how much of the knowledge base stands behind it (`tested`, `ai_written`,
`experimental`, `untested`; see `COVERAGE.md`). The labels come from a batch run of the **real** pipeline.

## Run it (your machine, your Anthropic credits)

```powershell
cd C:\dev\Ankur-Saathi
psql -U postgres -d ankur_saathi -f db/schema/05_coverage.sql        # once
python scripts/batch_generate.py --limit 3                            # a first, cheap try (about 40 cents)
python scripts/batch_generate.py                                      # all 101 skills: about 2 hours, about $13
python scripts/build_coverage.py --load                               # labels -> database, seed, report, summary
```

- It uses `backend/.env` (`ANTHROPIC_API_KEY`, `DATABASE_URL`) and asks before it spends anything.
- `--max-cost 15` stops it when the estimate reaches that many dollars. Run it again to **resume**: skills already ok are skipped.
- `--domain numeracy` or `--only N2.3.2,L2.6.1 --redo` run part of it. `--stub` runs a dry run with a fake model (no key, no cost).
- Plans are written on far-future dates (2031) and deleted afterwards, so your real plans are never touched.
- Costs are estimates (assumed $2 / $10 per million input / output tokens: change with `--price-in` / `--price-out`).

## What it records

One row per skill in `docs/batch/batch_results.csv`: time, tokens, estimated cost, checks still failing after the automatic
repairs, how many repairs ran, the anchor match tier, the passage match, and whether all three worksheets render.
Commit that file: it is the evidence for the evaluation slide of the deck.

## What the labels mean

| Label | Meaning |
| --- | --- |
| tested | passed every check with the real model, an exact anchor from the bank (and a bank passage for literacy) |
| ai_written | passed, but the opening activity is adapted or written by the AI, or no bank passage fits |
| experimental | failed, or checks still flag problems after the automatic repairs |
| untested | not yet run with the real model |

Run `build_coverage.py` again whenever the anchors, the passages or the batch results change, and commit the new
`db/seeds/content/06_coverage.sql`.
