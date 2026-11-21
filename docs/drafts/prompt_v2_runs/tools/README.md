# Test tools for prompt v2 (lab only)

Copied from the scratch folder `C:\dev\ankur-scratch\v2_run\` on 21 Nov 2026 so a new session has them. Run them from `backend/` of the lab
worktree. They use absolute lab paths (`C:\dev\Ankur-Saathi-lab`).

- `run_v2_matrix.py`: makes plans with the REAL model through the app's pipeline on a scratch class (removed afterwards). Costs money: only with
  the lead's OK. Example (Sonnet, the 45-minute column): `AI_ENABLED=true AI_CREDIT_EXPIRES=2026-11-30 venv/Scripts/python.exe <path>/run_v2_matrix.py --env-file .env --minutes 45 --max-usd 1`.
  Options: `--skills`, `--minutes`, `--max-usd`; environment: `V2_OUT` (output folder name, default `out` next to the script), `CLAUDE_MODEL`,
  `CLAUDE_THINKING_OVERRIDE` (JSON), `V2_EXAMPLE=1` (adds a reviewed example via `example_hook.py`), `AI_PRICE_*` for another model's prices.
  If the run is stopped half way, its scratch classes (school codes `TST-…`) stay in the lab database: remove them with `_scratch.remove_class`.
- `check_v2_matrix.py`: reads an output folder and checks every plan (minutes, 3 + N, own mistakes, You Do range, banned Hindi, show-me kept,
  cost per call). `V2_OUT` and `P_IN/P_OUT/P_CR/P_CW` (prices) as above. No AI.
- `load_for_review.py`: loads the plans in `docs/drafts/prompt_v2_runs/` into six lab review accounts (V245NA … V290NB, password 4826) dated
  today. No AI.
- `example_hook.py`: the test-only "reviewed example" section (used by `V2_EXAMPLE=1`).
