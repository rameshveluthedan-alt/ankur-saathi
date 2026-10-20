#!/usr/bin/env python3
"""
Where the AI budget stands (docs/AI_BUDGET.md).

  python scripts/ai_usage.py status    --env-file backend/.env
  python scripts/ai_usage.py schedule  --env-file backend/.env
  python scripts/ai_usage.py calibrate --env-file backend/.env --actual-usd 12.40 [--since 2026-10-20]

status     what is spent (metered plus the pre-meter estimate), what is left, what may be spent right now, today's spend by account, and a
           warning at 50, 70 and 80 percent (the organisers are told at 80, so we want to know long before).
schedule   the phases from today to the end of the credits, with the daily budget each can afford, set against the current caps.
calibrate  the meter counts tokens and multiplies by the prices in the settings (AI_PRICE_*). If you know what was ACTUALLY spent over
           the same period (from the organisers or the console), this says how far the prices are off and what to set them to.

The settings are read from the environment, and from the --env-file (AI_* lines as well as the database ones).
Requires: pip install asyncpg
"""

import argparse
import asyncio
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.dirname(__file__))

import anchor_common as ac


def load_env(path):
    """Put KEY=VALUE lines of the env file into the environment (without overriding what is already set)."""
    if not path or not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip().upper(), v.strip().strip('"').strip("'"))


def money(x):
    return f"${x:,.2f}"


async def cmd_status(db, args):
    from app.core.config import get_settings
    from app.services import ai_budget as ab
    s = get_settings()
    try:
        st = await ab.status(db)
    except Exception as e:
        if e.__class__.__name__ == "UndefinedTableError":
            sys.exit("The AI meter table is missing: run  psql -f db/schema/10_ai_usage.sql  and restart the backend. Until then NOTHING is metered or capped.")
        raise
    print(f"AI budget                    (credits valid until {s.ai_credit_expires}; the AI is {'ON' if s.ai_enabled else 'OFF'})")
    print(f"  allocation                 {money(st['allocation'])}")
    print(f"  spent before the meter     {money(st['offset'])}      (an estimate: AI_SPEND_OFFSET_USD)")
    print(f"  metered since              {money(st['metered'])}      in {st['calls']} calls " + ", ".join(f"{k} {n}" for k, (n, _) in st["by_kind"].items()))
    print(f"  TOTAL SPENT                {money(st['spent'])}      ({st['pct']:.1f}% of the allocation)")
    print(f"  remaining                  {money(st['remaining'])}")
    hold = s.ai_reserve_usd if st["reserve_active"] else s.ai_final_margin_usd
    print(f"  usable right now           {money(max(st['available_now'], 0))}      (holding back {money(hold)}: " + (f"the evaluator reserve until {s.ai_reserve_from}" if st["reserve_active"] else "the final margin") + ")")
    print(f"  today                      {money(st['today'])}      (global cap {money(s.ai_cap_global_daily_usd)}, school {money(s.ai_cap_school_daily_usd)}, teacher {money(s.ai_cap_teacher_daily_usd)}, shared demo {money(s.ai_cap_shared_demo_daily_usd)})")
    print(f"  prices in use              ${s.ai_price_input_per_mtok}/M input, ${s.ai_price_output_per_mtok}/M output  (check them against the real prices: calibrate)")
    for pct in (50, 70, 80):
        if st["pct"] >= pct:
            print(f"  !! {pct}% of the allocation has been used" + ("  (the organisers are alerted at 80%)" if pct == 80 else ""))
    if st["days"]:
        print("\n  last days (India time)")
        for d, n, c in st["days"]:
            print(f"    {d}  {n:>4} calls  {money(c):>9}")
    if st["top_today"]:
        print("\n  most spent today")
        for t, n, c in st["top_today"]:
            print(f"    account {t}...  {n:>3} calls  {money(c):>8}")


async def cmd_schedule(db, args):
    from app.core.config import get_settings
    from app.services import ai_budget as ab
    s = get_settings()
    today = ab.now().date()
    reserve_from, expires = date.fromisoformat(s.ai_reserve_from), date.fromisoformat(s.ai_credit_expires)
    metered = (await ab.status(db))["metered"]
    spent = s.ai_spend_offset_usd + metered
    dev_days, eval_days = max((reserve_from - today).days, 0), max((expires - max(reserve_from, today)).days + 1, 1)
    dev_budget = max(s.ai_allocation_usd - spent - s.ai_reserve_usd, 0)
    eval_budget = max(min(s.ai_allocation_usd - spent, s.ai_reserve_usd) - s.ai_final_margin_usd, 0)
    print(f"Today is {today}. Allocation {money(s.ai_allocation_usd)}, spent {money(spent)}.\n")
    print(f"  now to {reserve_from} (build and test)      {dev_days:>2} days   may spend {money(dev_budget)}   about {money(dev_budget / dev_days) if dev_days else '-'} a day")
    print(f"      the 101-skill batch run costs roughly 101 plans x your per-plan cost (see `status` after the first few); do it inside this window")
    print(f"  {reserve_from} to {expires} (evaluation)    {eval_days:>2} days   may spend {money(eval_budget)}   about {money(eval_budget / eval_days)} a day on average")
    print(f"\n  the global daily cap is {money(s.ai_cap_global_daily_usd)}: in the first 10 evaluation days that could use up to {money(10 * s.ai_cap_global_daily_usd)}"
          + ("  <- MORE than the evaluation budget: lower AI_CAP_GLOBAL_DAILY_USD" if 10 * s.ai_cap_global_daily_usd > eval_budget else "  (within the evaluation budget)"))
    print("\n  if you are shortlisted and receive the extra credit: raise AI_ALLOCATION_USD (and AI_RESERVE_USD if you want a new reserve), and restart.")
    print("  the credits end on", expires, "and the keys stop working: recorded plans keep the demo explorable after that.")


async def cmd_calibrate(db, args):
    from app.core.config import get_settings
    from app.services import ai_budget as ab
    s = get_settings()
    if args.actual_usd is None:
        sys.exit("--actual-usd is required: what was really spent over the same period")
    where, params = "TRUE", []
    if args.since:
        where, params = "created_at >= $1", [datetime.fromisoformat(args.since).replace(tzinfo=ab._tz())]
    row = await db.fetchrow(f"SELECT COALESCE(sum(input_tokens),0) AS i, COALESCE(sum(output_tokens),0) AS o, count(*) AS n FROM ai_usage WHERE {where}", *params)
    metered = ab.cost_usd(row["i"], row["o"])
    print(f"The meter counted {row['n']} calls: {row['i']:,} input and {row['o']:,} output tokens.")
    print(f"At the prices in the settings (${s.ai_price_input_per_mtok}/M in, ${s.ai_price_output_per_mtok}/M out) that is {money(metered)}.")
    if metered <= 0:
        sys.exit("Nothing metered in that period, so there is nothing to compare.")
    f = args.actual_usd / metered
    print(f"What was actually spent: {money(args.actual_usd)}  ->  the prices are {'too low' if f > 1 else 'too high'} by a factor of {f:.2f}.")
    print(f"If the input and output prices are off by the same factor, set  AI_PRICE_INPUT_PER_MTOK={s.ai_price_input_per_mtok * f:.2f}  AI_PRICE_OUTPUT_PER_MTOK={s.ai_price_output_per_mtok * f:.2f}")
    print("(Better: take the real per-million prices for your model from Anthropic's pricing page. History is re-priced automatically, because tokens are what is stored.)")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "schedule", "calibrate"])
    ap.add_argument("--actual-usd", type=float, help="calibrate: what was really spent in the period")
    ap.add_argument("--since", help="calibrate: count only calls since this date (YYYY-MM-DD)")
    ac.add_db_args(ap)
    args = ap.parse_args()
    load_env(getattr(args, "env_file", None))
    db = await ac.connect(args)
    try:
        await {"status": cmd_status, "schedule": cmd_schedule, "calibrate": cmd_calibrate}[args.command](db, args)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
