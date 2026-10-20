#!/usr/bin/env python3
"""
Create test teachers, each with their own multi-grade class, so several testers can use the app at the same time
without sharing one account (and without one tester's photos changing another's groups).

Each teacher is registered and has a register uploaded through the SAME code the app's screens use
(app/services/register_service.py), so this also exercises it. The class is multi-grade on purpose: Grade 1 rolls 1-10,
Grade 2 rolls 1-8, Grade 3 rolls 1-6, so the school rolls repeat across grades and the children get class numbers that
carry the grade (Grade 3, roll 5 = 305). Starting levels are spread over beginner / progressor / proficient
(6 / 12 / 6 children in each class, but which children differ from teacher to teacher).

  python scripts/create_test_teachers.py create --count 5 --env-file backend/.env
  python scripts/create_test_teachers.py list   --env-file backend/.env
  python scripts/create_test_teachers.py remove --env-file backend/.env          (deletes only these test teachers)

Log in with the phone numbers it prints (for example 9000000101).
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

PHONE_BASE = 9000000100          # test teacher 1 = 9000000101
SCHOOL_PREFIX = "MP-TEST-"
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


async def wipe(db, phone_like: str, school_like: str):
    """Remove test teachers and everything hanging off them (evidence and plans are not cascaded by the schema)."""
    # only teachers whose SCHOOL is a test school: a phone number pattern alone once matched the demo school's "Change PIN" account
    ids = [r["id"] for r in await db.fetch("""SELECT t.id FROM teachers t JOIN schools s ON s.id = t.school_id
                                              WHERE t.phone_hash LIKE $1 AND s.school_code LIKE $2""", phone_like, school_like)]
    if ids:
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = ANY($1::uuid[])", ids)
        await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = ANY($1::uuid[]))", ids)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = ANY($1::uuid[])", ids)
        await db.execute("DELETE FROM teachers WHERE id = ANY($1::uuid[])", ids)
    await db.execute("DELETE FROM schools WHERE school_code LIKE $1 AND NOT EXISTS (SELECT 1 FROM teachers t WHERE t.school_id = schools.id)", school_like)
    return len(ids)


async def cmd_create(db, args):
    for n in range(1, args.count + 1):
        phone = str(PHONE_BASE + n)
        phone_hash = "hash_" + phone
        if await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", phone_hash):
            if not args.recreate:
                print(f"  {phone}: already exists (use --recreate to rebuild it)")
                continue
            await wipe(db, phone_hash, SCHOOL_PREFIX + "%")
        me = await rs.register_teacher(db, phone_hash, f"{SCHOOL_PREFIX}{n:02d}", list(CLASS.keys()), pin_hash=auth.hash_pin(args.pin), enforce_join=False)
        await db.execute("UPDATE teachers SET is_demo = TRUE, pin_fixed = TRUE WHERE id = $1", me["teacher_id"])        # a shared demo account: its PIN is fixed
        plan = await rs.commit_register(db, me["teacher_id"], register_rows(n, not args.no_names), f"test_class_{n}.csv")
        print(f"  {phone}: school {me['school_code']}, {plan['added']} children ({plan['names_saved']} with fictional names), class numbers {plan['numbering']}  (teacher_id {me['teacher_id']})")
    print(f"\nSign in with the phone number and PIN {args.pin} (a published, fixed demo PIN: these accounts hold fictional data only). Each teacher has their own class (class numbers 101-110, 201-208, 301-306), with different children at each level.")


async def cmd_list(db, args):
    rows = await db.fetch("""SELECT substr(t.phone_hash, 6) AS phone, s.school_code, t.id,
                                    (SELECT count(*) FROM children c WHERE c.teacher_id = t.id AND c.is_active) AS kids
                             FROM teachers t JOIN schools s ON s.id = t.school_id WHERE s.school_code LIKE $1 ORDER BY s.school_code""", SCHOOL_PREFIX + "%")
    for r in rows:
        print(f"  {r['phone']}  {r['school_code']}  {r['kids']} children  {r['id']}")
    print(f"{len(rows)} test teacher(s)")


async def cmd_remove(db, args):
    if not args.yes:
        if input(f"Delete every test teacher ({SCHOOL_PREFIX}*) and their data? Type 'yes': ").strip().lower() != "yes":
            print("Cancelled.")
            return
    print(f"Removed {await wipe(db, 'hash_90000001%', SCHOOL_PREFIX + '%')} test teacher(s).")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["create", "list", "remove"])
    ap.add_argument("--count", type=int, default=5, help="how many test teachers (default 5)")
    ap.add_argument("--recreate", action="store_true", help="rebuild a test teacher that already exists")
    ap.add_argument("--pin", default=os.environ.get("DEMO_PIN", "4826"), help="the published demo PIN for these accounts (default 4826)")
    ap.add_argument("--no-names", action="store_true", help="enrol the children without (fictional) names")
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        await {"create": cmd_create, "list": cmd_list, "remove": cmd_remove}[args.command](db, args)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
