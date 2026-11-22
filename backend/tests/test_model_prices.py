"""
The per-model price table (backend/app/services/model_prices.py, 22 Nov 2026): the meter prices each call by the model that made it, so a
switch of model, or plans and photos on different models, are metered right; a correction (AI_MODEL_PRICES) re-prices history. The
database part works inside a transaction that is rolled back. No AI.

    python backend/tests/test_model_prices.py --env-file backend/.env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import asyncio
import os
import sys
from types import SimpleNamespace

import _scratch
from app.core.config import get_settings
from app.services import ai_budget as b, model_prices as mp

S = get_settings()
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def near(a, x):
    return abs(a - x) < 1e-9


S.ai_model_prices = ""
S.ai_price_input_per_mtok, S.ai_price_output_per_mtok, S.ai_price_cache_read_per_mtok, S.ai_price_cache_write_per_mtok = 2.0, 10.0, 0.10, 2.5

print("the table")
check("Sonnet 5.5: $2 / $10, cache read $0.10, write $2.50 (1.25x)", mp.prices_for("claude-sonnet-5-5") == (2.0, 10.0, 0.10, 2.5))
check("Opus 5.5: $4 / $20, cache read $0.20, write $5 (1.25x)", mp.prices_for("claude-opus-5-5") == (4.0, 20.0, 0.20, 5.0))
check("Haiku 5.5: $0.10 / $0.50 (cache read assumed 0.1x)", mp.prices_for("claude-haiku-5-5")[:2] == (0.10, 0.50))
check("every cache write in the table is 1.25x its input price (the 5-minute cache)", all(near(p[3], 1.25 * p[0]) for p in mp.PRICES.values()))
check("a dated id takes its model's prices", mp.prices_for("claude-opus-5-5-20261101") == mp.prices_for("claude-opus-5-5"))
check("...but not a different model that merely starts the same way", mp.source_of("claude-opus-5-50") != "the table")
S.ai_price_input_per_mtok = 7.0
check("a model NOT in the table, and an old row with no model, use the AI_PRICE_* settings",
      mp.prices_for("some-new-model")[0] == 7.0 and mp.prices_for(None)[0] == 7.0 and mp.source_of(None).startswith("AI_PRICE_"))
S.ai_price_input_per_mtok = 2.0

print("\nthe meter's cost")
check("cost_usd with no model is as before (the settings): 6,000 in + 9,000 out = $0.102", near(b.cost_usd(6000, 9000), 0.102))
check("the same tokens on Opus cost twice as much: $0.204", near(b.cost_usd(6000, 9000, model="claude-opus-5-5"), 0.204))
check("cached tokens on Opus: 1M read $0.20 + 1M written $5", near(b.cost_usd(0, 0, 1_000_000, 1_000_000, "claude-opus-5-5"), 5.2))

print("\na correction without a code change (AI_MODEL_PRICES)")
S.ai_model_prices = '{"claude-opus-5-5": [3, 15, 0.3, 3.75]}'
check("it wins over the table", mp.prices_for("claude-opus-5-5") == (3.0, 15.0, 0.3, 3.75) and mp.source_of("claude-opus-5-5") == "AI_MODEL_PRICES")
check("...for that model only", mp.prices_for("claude-sonnet-5-5") == (2.0, 10.0, 0.10, 2.5))
S.ai_model_prices = "not json"
check("a broken setting is ignored (the table is used), not an error", mp.prices_for("claude-opus-5-5") == (4.0, 20.0, 0.20, 5.0))
S.ai_model_prices = ""


async def db_part():
    db = await _scratch.connect()
    tr = db.transaction()
    await tr.start()
    try:
        await db.execute("DELETE FROM ai_usage")          # inside the transaction: rolled back at the end
        usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000, cache_read_input_tokens=0, cache_creation_input_tokens=0)
        await b.record(db, None, "plan", "claude-sonnet-5-5", usage)        # $2 + $1 = $3
        await b.record(db, None, "vision", "claude-opus-5-5", usage)        # $4 + $2 = $6
        await b.record(db, None, "library", "claude-opus-5-5", usage)       # $6
        est = {r["kind"]: float(r["est_cost_usd"]) for r in await db.fetch("SELECT kind, est_cost_usd FROM ai_usage")}
        check("each call's stored estimate is at its own model's prices (plan on Sonnet $3, photo on Opus $6)", est == {"plan": 3.0, "vision": 6.0, "library": 6.0}, est)
        total = await b._spent(db)
        check("the total mixes models correctly: $3 + $6 + $6 = $15 (one price set would have said $9)", near(total, 15.0), total)
        st = await b.status(db)
        check("the report gives each model its own line", {k: round(c, 6) for k, (n, c) in st["by_model"].items()} == {"claude-sonnet-5-5": 3.0, "claude-opus-5-5": 12.0}, st["by_model"])
        check("...and each kind its cost (vision $6 on Opus, plan $3 on Sonnet)", round(st["by_kind"]["vision"][1], 6) == 6.0 and round(st["by_kind"]["plan"][1], 6) == 3.0, st["by_kind"])
        check("the days add up to the total", near(sum(c for _, _, c in st["days"]), 15.0), st["days"])
        S.ai_model_prices = '{"claude-opus-5-5": [2, 10, 0.1, 2.5]}'
        check("a corrected price re-prices history (tokens are stored, not money): Opus at Sonnet's prices -> $9", near(await b._spent(db), 9.0))
        S.ai_model_prices = ""
        await db.execute("INSERT INTO ai_usage (kind, model, input_tokens, output_tokens) VALUES ('plan', NULL, 1000000, 0)")
        check("an old row with no model is priced by the settings ($2)", near(await b._spent(db), 17.0))
    finally:
        await tr.rollback()
        await db.close()


print("\nin the database (rolled back)")
asyncio.run(db_part())

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: each call is priced by its own model; mixing models, a correction and old rows are all metered right")
