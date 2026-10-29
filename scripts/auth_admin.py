#!/usr/bin/env python3
"""
Operator tools for sign-in (docs/AUTH.md and docs/DEMO_ACCESS.md). An account is named by its EMPLOYEE CODE: six letters or digits, for example MPT101.

  python scripts/auth_admin.py demo-setup --env-file backend/.env         set up the demo accounts reviewers use, and print the credentials
  python scripts/auth_admin.py restore-practice --env-file backend/.env   put the practice account (MPT199) back (run it nightly)
  python scripts/auth_admin.py set-pin --code MPT101 --pin 482600 [--fixed] [--demo]      (--pin is the PASSWORD: the option keeps its old name)
  python scripts/auth_admin.py unlock --code MPT101
  python scripts/auth_admin.py list

The demo accounts hold FICTIONAL data only. Their passwords are published to reviewers, so they are not secrets:
  * the shared demo accounts have a FIXED password (cannot be changed or reset), so one reviewer cannot lock out another;
  * one practice account (MPT199) can change and reset its password freely, and `restore-practice` puts it right again.
Accounts made before employee codes (named by a phone number) are renamed first, by migrate_to_employee_codes.py.
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
from demo_accounts import DEMO_SCHOOL, DEMO_TEACHER, LEADER, PRACTICE, TEST_CODE_RE
from migrate_to_employee_codes import migrate, describe

ACCOUNTS = {       # code -> what it is
    DEMO_TEACHER: "demo teacher (the 30-child multi-grade class, with fictional names and data)",
    LEADER: "demo school leader (the head teacher: teaches too; sees the school's accounts, resets the practice account's password)",
    PRACTICE: "practice account: change its password, reset it as the school leader, lock it out; nothing else is affected",
}


def account_id(value: str) -> str:
    """An employee code (any case). For an account made before employee codes, a phone number."""
    v = str(value).strip()
    return auth.normalise_code(v) or ("hash_" + v)


async def set_pin(db, code, pin, fixed=None, demo=None, must_change=False, school=None):
    """school: act only on an account of THIS school (the demo operations pass the demo school: a real teacher with the same employee code in another school is never touched)."""
    reason = auth.validate_pin(pin, account_id(code)) if (fixed is None) else None       # a published demo password need not pass the rules for real teachers
    if reason and not fixed:
        sys.exit(f"Refused: {reason}")
    flags = ""
    if fixed is not None:
        flags += f", pin_fixed = {bool(fixed)}"
    if demo is not None:
        flags += f", is_demo = {bool(demo)}"
    n = await db.execute(f"""UPDATE teachers SET pin_hash = $2, pin_version = pin_version + 1, must_change_pin = $3, failed_pin_attempts = 0, locked_until = NULL,
                             pin_changed_at = now(){flags} WHERE phone_hash = $1 AND ($4::text IS NULL OR school_id = (SELECT id FROM schools WHERE school_code = $4))""", account_id(code), auth.hash_pin(pin), must_change, school)
    return n.endswith("1")


async def ensure_account(db, code, role, grades, school=DEMO_SCHOOL):
    if await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", account_id(code)):
        return False                                     # (an account with this code in ANOTHER school is left alone too: the demo operations then find nothing in the demo school)
    school_id = await db.fetchval("SELECT id FROM schools WHERE school_code = $1", school)
    await db.execute("INSERT INTO teachers (school_id, phone_hash, enrolled_grades, is_multigrade, role) VALUES ($1, $2, $3, $4, $5)", school_id, account_id(code), grades, len(grades) > 1, role)
    return True


async def cmd_demo_setup(db, args):
    if not await db.fetchval("SELECT 1 FROM schools WHERE school_code = $1", DEMO_SCHOOL):
        sys.exit(f"The demo school {DEMO_SCHOOL} is not in the database: load db/seeds/classroom/01_profile.sql first.")
    print(describe(await migrate(db)))                    # accounts made before employee codes are renamed first
    await auth.ensure_demo_consent(db, DEMO_SCHOOL)          # the demo school says that everything in it is fictional
    await ensure_account(db, LEADER, "school_admin", ["grade_1"])
    made_p = await ensure_account(db, PRACTICE, "teacher", ["grade_1"])
    if made_p:                                           # the practice teacher gets a small fictional class, so there is something to look at
        from create_test_teachers import NAMES, LEVELS
        tid = await db.fetchval("SELECT id FROM teachers WHERE phone_hash = $1", account_id(PRACTICE))
        rows = [{"row": i + 2, "grade": "grade_1", "roll": str(i + 1), "name": NAMES[i], "numeracy": LEVELS[i % 4], "literacy": LEVELS[(i + 1) % 4]} for i in range(12)]
        await rs.commit_register(db, str(tid), rows, "practice.csv")
    await set_pin(db, DEMO_TEACHER, args.demo_pin, fixed=True, demo=True, school=DEMO_SCHOOL)
    await set_pin(db, LEADER, args.admin_pin, fixed=True, demo=True, school=DEMO_SCHOOL)
    await set_pin(db, PRACTICE, args.practice_pin, fixed=False, demo=True, school=DEMO_SCHOOL)
    tests = await db.fetch("""SELECT t.phone_hash AS code FROM teachers t JOIN schools s ON s.id = t.school_id
                              WHERE s.school_code = $1 AND t.phone_hash ~ $2 ORDER BY t.phone_hash""", DEMO_SCHOOL, TEST_CODE_RE)
    for t in tests:
        await set_pin(db, t["code"], args.demo_pin, fixed=True, demo=True, school=DEMO_SCHOOL)
    print("\nDEMO ACCOUNTS (fictional data; publish these to reviewers)\n")
    print(f"  {'code':<9}{'password':<10}what")
    print(f"  {DEMO_TEACHER:<9}{args.demo_pin:<10}{ACCOUNTS[DEMO_TEACHER]}")
    print(f"  {LEADER:<9}{args.admin_pin:<10}{ACCOUNTS[LEADER]}")
    print(f"  {PRACTICE:<9}{args.practice_pin:<10}{ACCOUNTS[PRACTICE]}")
    for t in tests:
        print(f"  {t['code']:<9}{args.demo_pin:<10}test teacher with their own multi-grade class (use one each, so you do not overwrite each other)")
    if not tests:
        print("  (no test teachers yet: run  python scripts/create_test_teachers.py create --count 5  then run this again)")


async def cmd_restore_practice(db, args):
    await migrate(db)                                    # the nightly job runs this: a database made before employee codes converts itself
    await auth.ensure_demo_consent(db, DEMO_SCHOOL)          # ... and a cloud demo school gets its statement without a manual step
    ok = await set_pin(db, PRACTICE, args.practice_pin, fixed=False, demo=True, school=DEMO_SCHOOL)
    print(f"The practice account ({PRACTICE}) is restored." if ok else f"The practice account ({PRACTICE}) does not exist: run demo-setup first.")


async def cmd_set_pin(db, args):
    ok = await set_pin(db, args.code, args.pin, fixed=True if args.fixed else None, demo=True if args.demo else None, must_change=args.must_change)
    print("Password set." if ok else "No account with that employee code.")


async def cmd_unlock(db, args):
    n = await db.execute("UPDATE teachers SET failed_pin_attempts = 0, locked_until = NULL WHERE phone_hash = $1", account_id(args.code))
    print("Unlocked." if n.endswith("1") else "No account with that employee code.")


async def cmd_list(db, args):
    rows = await db.fetch("""SELECT t.phone_hash AS code, s.school_code, t.role, t.pin_hash IS NOT NULL AS has_pin, t.is_demo, t.pin_fixed, t.must_change_pin,
                                    (t.locked_until > now()) AS locked FROM teachers t JOIN schools s ON s.id = t.school_id ORDER BY s.school_code, t.created_at""")
    print(f"  {'code':<12}{'school':<14}{'role':<14}password  demo fixed change locked")
    for r in rows:
        print(f"  {auth.display_code(r['code']):<12}{r['school_code']:<14}{r['role']:<14}{'yes' if r['has_pin'] else 'NO ':<10}{'yes ' if r['is_demo'] else '    '}{'yes  ' if r['pin_fixed'] else '     '}{'yes   ' if r['must_change_pin'] else '      '}{'LOCKED' if r['locked'] else ''}")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["demo-setup", "restore-practice", "set-pin", "unlock", "list"])
    ap.add_argument("--code", "--phone", dest="code", help="the employee code, for example MPT101 (--phone is the old name of this option)")
    ap.add_argument("--pin", help="the password")
    ap.add_argument("--fixed", action="store_true", help="a shared demo account: the password cannot be changed or reset")
    ap.add_argument("--demo", action="store_true", help="mark as a demo account (a banner is shown; fictional data only)")
    ap.add_argument("--must-change", action="store_true", help="the teacher must choose a new password at the next sign-in")
    ap.add_argument("--demo-pin", default=os.environ.get("DEMO_PIN", "4826"), help="the published demo password of the teachers (default 4826)")
    ap.add_argument("--admin-pin", default=os.environ.get("DEMO_ADMIN_PIN", "7351"), help="the published demo password of the school leader (default 7351)")
    ap.add_argument("--practice-pin", default=os.environ.get("DEMO_PRACTICE_PIN", "3917"), help="the published password of the practice account (default 3917)")
    ac.add_db_args(ap)
    args = ap.parse_args()
    if args.command in ("set-pin", "unlock") and not args.code:
        ap.error("--code is required")
    if args.command == "set-pin" and not args.pin:
        ap.error("--pin is required")
    db = await ac.connect(args)
    try:
        await {"demo-setup": cmd_demo_setup, "restore-practice": cmd_restore_practice, "set-pin": cmd_set_pin, "unlock": cmd_unlock, "list": cmd_list}[args.command](db, args)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
