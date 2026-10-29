#!/usr/bin/env python3
"""
Rename the demonstration accounts from phone numbers to EMPLOYEE CODES (docs/DEMO_ACCESS.md), keeping each account's class, children, plans and evidence.

  9876543210 -> MPT101 (the demo teacher)      9876500000 -> MPA101 (the school leader)      9000000199 -> MPT199 (the practice account)
  9000000101 to 9000000197 -> MPT102 to MPT198 (the test teachers, who now teach in the DEMO school: one school, one leader)
  9000000100 (the old test school's admin) and the empty test school are removed.

Safe to repeat: a second run changes nothing. An account that already has its new code is left alone. The nightly job runs it first, so a deploy converts the cloud database by itself.

  python scripts/migrate_to_employee_codes.py --env-file backend/.env
Requires: pip install asyncpg
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import anchor_common as ac
from demo_accounts import DEMO_SCHOOL, OLD_TEST_ADMIN, OLD_TEST_SCHOOL_PREFIX, TEST_CODE_RE, new_code_for, wipe_teachers


async def migrate(db) -> dict:
    """Returns what it did: {'renamed': [...], 'moved': n, 'removed_admins': n, 'removed_schools': n}."""
    done = {"renamed": [], "moved": 0, "removed_admins": 0, "removed_schools": 0}
    async with db.transaction():
        # ONLY accounts of the demo school and of the old test schools are touched. An employee code such as MPT150 can belong to a real teacher of a real school: that one is never renamed,
        # moved or reset by this script.
        old = await db.fetch("""SELECT t.phone_hash, s.school_code FROM teachers t JOIN schools s ON s.id = t.school_id
                                WHERE t.phone_hash LIKE 'hash\\_%' AND (s.school_code = $1 OR s.school_code LIKE $2)""", DEMO_SCHOOL, OLD_TEST_SCHOOL_PREFIX + "%")
        for r in sorted(old, key=lambda r: r["phone_hash"]):
            ident, new = r["phone_hash"], new_code_for(r["phone_hash"])
            if new and not await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", new):
                await db.execute("UPDATE teachers SET phone_hash = $2 WHERE phone_hash = $1", ident, new)
                done["renamed"].append(f"{ident[5:]} -> {new}")
        demo = await db.fetchval("SELECT id FROM schools WHERE school_code = $1", DEMO_SCHOOL)
        if demo:
            moved = await db.fetch("""UPDATE teachers SET school_id = $1, role = 'teacher'
                                      WHERE phone_hash ~ $2 AND school_id IN (SELECT id FROM schools WHERE school_code LIKE $3) RETURNING phone_hash""", demo, TEST_CODE_RE, OLD_TEST_SCHOOL_PREFIX + "%")
            done["moved"] = len(moved)
            admin = await db.fetchval("SELECT t.id FROM teachers t JOIN schools s ON s.id = t.school_id WHERE t.phone_hash = $1 AND s.school_code LIKE $2", OLD_TEST_ADMIN, OLD_TEST_SCHOOL_PREFIX + "%")
            if admin:
                done["removed_admins"] = await wipe_teachers(db, [admin])
            gone = await db.fetch("DELETE FROM schools WHERE school_code LIKE $1 AND NOT EXISTS (SELECT 1 FROM teachers t WHERE t.school_id = schools.id) RETURNING school_code", OLD_TEST_SCHOOL_PREFIX + "%")
            done["removed_schools"] = len(gone)
    return done


def describe(done: dict) -> str:
    if not (done["renamed"] or done["moved"] or done["removed_admins"] or done["removed_schools"]):
        return "  The accounts already use employee codes: nothing to do."
    return (f"  {len(done['renamed'])} account(s) renamed to employee codes ({'; '.join(done['renamed'])}); {done['moved']} test teacher(s) moved into {DEMO_SCHOOL}; "
            f"{done['removed_admins']} old test admin and {done['removed_schools']} empty test school removed.")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        print(describe(await migrate(db)))
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
