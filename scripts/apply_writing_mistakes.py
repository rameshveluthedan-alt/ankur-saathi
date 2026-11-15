#!/usr/bin/env python3
"""
Load the 9 writing-skill mistakes (L2.7.1, L2.7.2, L3.7.1; reviewed by Vaishnavi on 14 Nov 2026) into an EXISTING database, e.g. the live one.
They are in db/seeds/literacy/03_misconceptions.sql, but the seeds are loaded only at the first setup. Safe to run again: rows already there are left
as they are (ON CONFLICT DO NOTHING).

    python scripts/apply_writing_mistakes.py --env-file backend/.env          a local or lab database
    (as a Cloud Run job: --command=python --args="^@^/srv/scripts/apply_writing_mistakes.py"; the database settings come from the job's environment)
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.dirname(__file__))

import anchor_common as ac
from writing_mistakes_draft import MISTAKES

SQL = """INSERT INTO misconceptions (id, competency_id, name_en, name_hi, error_pattern, diagnostic_indicator, example_correct, example_incorrect,
                                     intervention_strategy, intervention_template_ids, severity, frequency, sort_order)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::text[], $11, $12, $13) ON CONFLICT (id) DO NOTHING"""


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ac.add_db_args(ap)            # --env-file and --db-*: the same database choice as the other scripts
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        before = await db.fetchval("SELECT COUNT(*) FROM misconceptions")
        order = {}
        for mid, skill, en, hi, pattern, shows, right, wrong, todo, ints, sev, freq in MISTAKES:
            order[skill] = order.get(skill, 0) + 1
            await db.execute(SQL, mid, skill, en, hi, pattern, shows, right, wrong, todo, list(ints), sev, freq, order[skill])
        after = await db.fetchval("SELECT COUNT(*) FROM misconceptions")
        have = await db.fetch("SELECT competency_id, COUNT(*) AS n FROM misconceptions WHERE competency_id IN ('L2.7.1', 'L2.7.2', 'L3.7.1') GROUP BY 1 ORDER BY 1")
        print(f"misconceptions: {before} -> {after} ({after - before} added)")
        print("writing skills now: " + ", ".join(f"{r['competency_id']} {r['n']}" for r in have))
        if any(r["n"] < 3 for r in have) or len(have) < 3:
            sys.exit("NOT DONE: a writing skill has fewer than 3 mistakes")
        print("OK")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
