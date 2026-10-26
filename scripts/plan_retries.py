#!/usr/bin/env python3
"""
How often did a Generate need a SECOND plan call? (the model's first reply could not be read, so the app asked again: another minute and another 14 cents)

    python scripts\\plan_retries.py --env-file backend\\.env            the last 30 days
    python scripts\\plan_retries.py --env-file backend\\.env --days 7 --gap 100

A retry leaves TWO 'plan' rows in ai_usage for the same teacher, with the SAME input size (the same prompt), the second one about a minute after the first (the length of one call).
A teacher who presses Generate again on purpose leaves two rows too, but much further apart: so only pairs closer than --gap seconds (default 100) are counted. Changes nothing.
Run from the repo root WITH --env-file (it reads the database it is given). To read the cloud, use the usage job of deploy\\DEPLOY.md: this script reads the database you point it at.
"""
import argparse
import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "backend")]
import anchor_common as ac                                  # noqa: E402


def find_retries(rows, gap_seconds=100):
    """rows: dicts with teacher_id, created_at, input_tokens, output_tokens, est_cost_usd, ordered by teacher_id then time. Returns (the retry pairs, the number of Generates).
    A pair = two consecutive plan calls of ONE teacher with the SAME input size and less than gap_seconds between them. A call belongs to one pair at most."""
    pairs, used = [], set()
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        if i - 1 in used or a["teacher_id"] != b["teacher_id"] or a["input_tokens"] != b["input_tokens"]:
            continue
        if (b["created_at"] - a["created_at"]).total_seconds() <= gap_seconds:
            pairs.append((a, b))
            used.update((i - 1, i))
    return pairs, len(rows) - len(pairs)


async def main():
    ap = argparse.ArgumentParser(description="How often did a Generate need a second plan call?")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--gap", type=int, default=100, help="seconds: two calls closer than this, with the same input, are a retry")
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        if not await db.fetchval("SELECT to_regclass('ai_usage') IS NOT NULL"):
            print("There is no ai_usage table in this database: nothing was metered here.")
            return 0
        rows = [dict(r) for r in await db.fetch("""SELECT teacher_id, created_at, input_tokens, output_tokens, est_cost_usd FROM ai_usage
                                                   WHERE kind = 'plan' AND created_at > now() - make_interval(days => $1) ORDER BY teacher_id, created_at""", args.days)]
    finally:
        await db.close()
    if not rows:
        print(f"No plan calls in the last {args.days} days in this database.")
        return 0
    pairs, generates = find_retries(rows, args.gap)
    extra = sum(float(a["est_cost_usd"] or 0) for a, _ in pairs)
    print(f"{len(rows)} plan calls in the last {args.days} days = {generates} Generate(s); {len(pairs)} needed a SECOND call ({100 * len(pairs) / max(1, generates):.0f}%), which cost about ${extra:.2f} extra and about {len(pairs)} extra minute(s) of waiting.")
    for a, b in pairs[-12:]:
        print(f"  {a['created_at']:%d %b %H:%M:%S}  then {b['created_at']:%H:%M:%S} ({(b['created_at'] - a['created_at']).total_seconds():.0f} s later)   input {a['input_tokens']} tokens, output {a['output_tokens']} then {b['output_tokens']}")
    print("(A retry is a Generate whose first reply could not be read as JSON. The server log of that moment says 'Model JSON problem (attempt 1 of 2)'.)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
