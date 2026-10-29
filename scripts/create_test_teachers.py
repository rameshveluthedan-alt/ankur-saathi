#!/usr/bin/env python3
"""
Create test teachers, each with their own multi-grade class, so several testers can use the app at the same time
without sharing one account (and without one tester's photos changing another's groups).

THE LAYOUT (since 27 Oct): ONE school, the demo school MP-DEMO-001, with ONE leader (MPA101: the head teacher) and the teachers: the demo teacher MPT101,
the practice account MPT199, and the test teachers MPT102 upwards (up to MPT198), all plain TEACHERS with a fixed published demo password. Earlier the test teachers were in a test school of their
own with its own admin (9000000100, a phone number): `normalise` renames those accounts, moves the teachers into the demo school and removes the old admin and the empty test school
(it runs scripts/migrate_to_employee_codes.py; classes, children and evidence stay with their teacher).

Each teacher is registered and has a register uploaded through the SAME code the app's screens use
(app/services/register_service.py), so this also exercises it. The class is multi-grade on purpose: Grade 1 rolls 1-10,
Grade 2 rolls 1-8, Grade 3 rolls 1-6, so the school rolls repeat across grades and the children get class numbers that
carry the grade (Grade 3, roll 5 = 305). Starting levels are spread over beginner / progressor / proficient
(6 / 12 / 6 children in each class, but which children differ from teacher to teacher).

  python scripts/create_test_teachers.py create --count 5 --env-file backend/.env
  python scripts/create_test_teachers.py normalise --env-file backend/.env       (the old layout -> the current one; safe to repeat; the nightly job runs it)
  python scripts/create_test_teachers.py list   --env-file backend/.env
  python scripts/create_test_teachers.py remove --env-file backend/.env          (deletes only these test teachers)

Log in with the employee codes it prints (MPT102 upwards).
Requires: pip install asyncpg
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.dirname(__file__))

import anchor_common as ac
from app.services import auth_service as auth, register_service as rs
from demo_accounts import DEMO_SCHOOL, TEST_CODE_RE, test_code, wipe_teachers
from migrate_to_employee_codes import migrate, describe

TEST_SCHOOL = DEMO_SCHOOL          # the test teachers teach in the demo school: one school, one leader
CLASS = {"grade_1": 10, "grade_2": 8, "grade_3": 6}
LEVELS = ("beginner", "progressor", "progressor", "proficient")      # a realistic spread
# FICTIONAL first names, for the demo only. Real names are entered by the teacher in her own app and never belong in this repository.
NAMES = ("आरव", "अनन्या", "विहान", "सान्वी", "अर्जुन", "इशिता", "कबीर", "मीरा", "रेयांश", "तारा", "दिव्यांश", "नेहा", "अयान", "काव्या", "रुद्र", "पीहू",
         "यश", "सिया", "वेदांत", "रिया", "आदित्य", "परी", "ध्रुव", "जिया", "कृष", "अवनि", "लक्ष्य", "मायरा", "शौर्य", "नव्या", "अथर्व", "आन्या",
         "दक्ष", "तनिष्का", "युवान", "रुही", "अंश", "मिहिका", "हर्ष", "ओजस्वी")


def register_rows(teacher_no: int, with_names: bool = True) -> list:
    rows, i = [], teacher_no
    for grade, n in CLASS.items():
        for roll in range(1, n + 1):
            i += 1
            rows.append({"row": len(rows) + 2, "grade": grade, "roll": str(roll), "name": NAMES[i % len(NAMES)] if with_names else "",
                         "numeracy": LEVELS[i % 4], "literacy": LEVELS[(i + 1) % 4]})
    return rows


async def test_ids(db, code=None) -> list:
    """The test teachers of the demo school (MPT102 to MPT198), or just one of them. Never the demo teacher MPT101 and never the practice account MPT199."""
    rows = await db.fetch("""SELECT t.id FROM teachers t JOIN schools s ON s.id = t.school_id
                             WHERE s.school_code = $1 AND t.phone_hash ~ $2 AND ($3::text IS NULL OR t.phone_hash = $3)""", DEMO_SCHOOL, TEST_CODE_RE, code)
    return [r["id"] for r in rows]


async def cmd_normalise(db, args):
    """Bring accounts made by an OLDER version (phone numbers, a test school of their own) into the current layout. Idempotent; see migrate_to_employee_codes.py."""
    print(describe(await migrate(db)))


async def cmd_create(db, args):
    await migrate(db)
    for n in range(1, args.count + 1):
        code = test_code(n)
        if await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", code):
            if not args.recreate:
                print(f"  {code}: already exists (use --recreate to rebuild it)")
                continue
            await wipe_teachers(db, await test_ids(db, code))
        me = await rs.register_teacher(db, code, DEMO_SCHOOL, list(CLASS.keys()), pin_hash=auth.hash_pin(args.pin), enforce_join=False)
        await db.execute("UPDATE teachers SET is_demo = TRUE, pin_fixed = TRUE, role = 'teacher' WHERE id = $1", me["teacher_id"])        # a plain teacher; a shared demo account: its password is fixed
        plan = await rs.commit_register(db, me["teacher_id"], register_rows(n, not args.no_names), f"test_class_{n}.csv")
        print(f"  {code}: school {me['school_code']}, {plan['added']} children ({plan['names_saved']} with fictional names), class numbers {plan['numbering']}  (teacher_id {me['teacher_id']})")
    print(f"\nSign in with the employee code and the password {args.pin} (a published, fixed demo password: these accounts hold fictional data only). Each teacher has their own class (class numbers 101-110, 201-208, 301-306), with different children at different levels.")


async def cmd_list(db, args):
    rows = await db.fetch("""SELECT t.phone_hash AS code, s.school_code, t.role, t.id,
                                    (SELECT count(*) FROM children c WHERE c.teacher_id = t.id AND c.is_active) AS kids
                             FROM teachers t JOIN schools s ON s.id = t.school_id WHERE s.school_code = $1 AND t.phone_hash ~ $2 ORDER BY t.phone_hash""", DEMO_SCHOOL, TEST_CODE_RE)
    for r in rows:
        print(f"  {r['code']}  {r['school_code']}  {r['role']:<12} {r['kids']} children  {r['id']}")
    print(f"{len(rows)} test teacher(s)")


async def cmd_remove(db, args):
    if not args.yes:
        if input(f"Delete every test teacher (MPT102 to MPT198, in {DEMO_SCHOOL}) and their data? Type 'yes': ").strip().lower() != "yes":
            print("Cancelled.")
            return
    print(f"Removed {await wipe_teachers(db, await test_ids(db))} test teacher(s).")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["create", "normalise", "list", "remove"])
    ap.add_argument("--count", type=int, default=5, help="how many test teachers (default 5)")
    ap.add_argument("--recreate", action="store_true", help="rebuild a test teacher that already exists")
    ap.add_argument("--pin", default=os.environ.get("DEMO_PIN", "4826"), help="the published demo password for the test teachers (default 4826)")
    ap.add_argument("--no-names", action="store_true", help="enrol the children without (fictional) names")
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        await {"create": cmd_create, "normalise": cmd_normalise, "list": cmd_list, "remove": cmd_remove}[args.command](db, args)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
