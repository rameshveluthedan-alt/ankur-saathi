#!/usr/bin/env python3
"""
Operator tools for sign-in (docs/AUTH.md and docs/DEMO_ACCESS.md).

  python scripts/auth_admin.py demo-setup --env-file backend/.env      set up the demo accounts jurors use, and print the credentials
  python scripts/auth_admin.py restore-practice --env-file backend/.env  put the "Change PIN" account back (run it nightly)
  python scripts/auth_admin.py set-pin --phone 9876543210 --pin 4826 [--fixed] [--demo]
  python scripts/auth_admin.py unlock --phone 9876543210
  python scripts/auth_admin.py list

The demo accounts hold FICTIONAL data only. Their PINs are published to jurors, so they are not secrets:
  * the shared demo accounts have a FIXED PIN (cannot be changed or reset), so one juror cannot lock out another;
  * one "Change PIN" account (the practice account) can change and reset its PIN freely, and `restore-practice` puts it right again.
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

DEMO_SCHOOL = "MP-DEMO-001"
JOIN_CODE = "DEMO26"
ACCOUNTS = {       # phone -> (what it is)
    "9876543210": "demo teacher (the 30-child multi-grade class, with fictional names and data)",
    "9876500000": "demo school admin (can see the school's accounts and reset the 'Change PIN' account)",
    "9000000199": "'Change PIN' account (पिन बदलना): change its PIN, reset it as the admin, lock it out: nothing else is affected",
}


def phone_hash(phone: str) -> str:
    return "hash_" + phone.strip()


async def set_pin(db, phone, pin, fixed=None, demo=None, must_change=False):
    reason = auth.validate_pin(pin) if (fixed is None) else None       # a published demo PIN need not pass the rules for real teachers
    if reason and not fixed:
        sys.exit(f"Refused: {reason}")
    flags = ""
    if fixed is not None:
        flags += f", pin_fixed = {bool(fixed)}"
    if demo is not None:
        flags += f", is_demo = {bool(demo)}"
    n = await db.execute(f"""UPDATE teachers SET pin_hash = $2, pin_version = pin_version + 1, must_change_pin = $3, failed_pin_attempts = 0, locked_until = NULL,
                             pin_changed_at = now(){flags} WHERE phone_hash = $1""", phone_hash(phone), auth.hash_pin(pin), must_change)
    return n.endswith("1")


async def ensure_account(db, phone, role, grades, school=DEMO_SCHOOL):
    if await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", phone_hash(phone)):
        return False
    school_id = await db.fetchval("SELECT id FROM schools WHERE school_code = $1", school)
    await db.execute("INSERT INTO teachers (school_id, phone_hash, enrolled_grades, is_multigrade, role) VALUES ($1, $2, $3, $4, $5)", school_id, phone_hash(phone), grades, len(grades) > 1, role)
    return True


async def cmd_demo_setup(db, args):
    if not await db.fetchval("SELECT 1 FROM schools WHERE school_code = $1", DEMO_SCHOOL):
        sys.exit(f"The demo school {DEMO_SCHOOL} is not in the database: load db/seeds/classroom/01_profile.sql first.")
    await db.execute("UPDATE schools SET join_code = $2 WHERE school_code = $1", DEMO_SCHOOL, JOIN_CODE)
    made = await ensure_account(db, "9876500000", "school_admin", ["grade_1"])
    made_p = await ensure_account(db, "9000000199", "teacher", ["grade_1"])
    if made_p:                                           # the practice teacher gets a small fictional class, so there is something to look at
        from create_test_teachers import NAMES, LEVELS
        tid = await db.fetchval("SELECT id FROM teachers WHERE phone_hash = $1", phone_hash("9000000199"))
        rows = [{"row": i + 2, "grade": "grade_1", "roll": str(i + 1), "name": NAMES[i], "numeracy": LEVELS[i % 4], "literacy": LEVELS[(i + 1) % 4]} for i in range(12)]
        await rs.commit_register(db, str(tid), rows, "practice.csv")
    await set_pin(db, "9876543210", args.demo_pin, fixed=True, demo=True)
    await set_pin(db, "9876500000", args.admin_pin, fixed=True, demo=True)
    await set_pin(db, "9000000199", args.practice_pin, fixed=False, demo=True)
    tests = await db.fetch("SELECT substr(phone_hash, 6) AS phone FROM teachers WHERE phone_hash LIKE 'hash_90000001%' AND phone_hash <> 'hash_9000000199' ORDER BY phone_hash")
    for t in tests:
        await set_pin(db, t["phone"], args.demo_pin, fixed=True, demo=True)
    print("\nDEMO ACCOUNTS (fictional data; publish these to jurors)\n")
    print(f"  {'phone':<12}{'PIN':<8}what")
    print(f"  {'9876543210':<12}{args.demo_pin:<8}{ACCOUNTS['9876543210']}")
    print(f"  {'9876500000':<12}{args.admin_pin:<8}{ACCOUNTS['9876500000']}")
    print(f"  {'9000000199':<12}{args.practice_pin:<8}{ACCOUNTS['9000000199']}")
    for t in tests:
        print(f"  {t['phone']:<12}{args.demo_pin:<8}test teacher with their own multi-grade class (use one each, so you do not overwrite each other)")
    if not tests:
        print("  (no test teachers yet: run  python scripts/create_test_teachers.py create --count 5  then run this again)")
    print(f"\n  School join code for anyone who wants to register a new teacher into the demo school: {JOIN_CODE}")


async def cmd_restore_practice(db, args):
    ok = await set_pin(db, "9000000199", args.practice_pin, fixed=False, demo=True)
    print("The 'Change PIN' account is restored." if ok else "The 'Change PIN' account does not exist: run demo-setup first.")


async def cmd_set_pin(db, args):
    ok = await set_pin(db, args.phone, args.pin, fixed=True if args.fixed else None, demo=True if args.demo else None, must_change=args.must_change)
    print("PIN set." if ok else "No account with that phone number.")


async def cmd_unlock(db, args):
    n = await db.execute("UPDATE teachers SET failed_pin_attempts = 0, locked_until = NULL WHERE phone_hash = $1", phone_hash(args.phone))
    print("Unlocked." if n.endswith("1") else "No account with that phone number.")


async def cmd_list(db, args):
    rows = await db.fetch("""SELECT substr(t.phone_hash, 6) AS phone, s.school_code, t.role, t.pin_hash IS NOT NULL AS has_pin, t.is_demo, t.pin_fixed, t.must_change_pin,
                                    (t.locked_until > now()) AS locked FROM teachers t JOIN schools s ON s.id = t.school_id ORDER BY s.school_code, t.created_at""")
    print(f"  {'phone':<12}{'school':<14}{'role':<14}PIN  demo fixed change locked")
    for r in rows:
        print(f"  {r['phone']:<12}{r['school_code']:<14}{r['role']:<14}{'yes' if r['has_pin'] else 'NO ':<5}{'yes ' if r['is_demo'] else '    '}{'yes  ' if r['pin_fixed'] else '     '}{'yes   ' if r['must_change_pin'] else '      '}{'LOCKED' if r['locked'] else ''}")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["demo-setup", "restore-practice", "set-pin", "unlock", "list"])
    ap.add_argument("--phone")
    ap.add_argument("--pin")
    ap.add_argument("--fixed", action="store_true", help="a shared demo account: the PIN cannot be changed or reset")
    ap.add_argument("--demo", action="store_true", help="mark as a demo account (a banner is shown; fictional data only)")
    ap.add_argument("--must-change", action="store_true", help="the teacher must choose a new PIN at the next sign-in")
    ap.add_argument("--demo-pin", default=os.environ.get("DEMO_PIN", "4826"))
    ap.add_argument("--admin-pin", default=os.environ.get("DEMO_ADMIN_PIN", "7351"))
    ap.add_argument("--practice-pin", default=os.environ.get("DEMO_PRACTICE_PIN", "3917"))
    ac.add_db_args(ap)
    args = ap.parse_args()
    if args.command in ("set-pin", "unlock") and not args.phone:
        ap.error("--phone is required")
    if args.command == "set-pin" and not args.pin:
        ap.error("--pin is required")
    db = await ac.connect(args)
    try:
        await {"demo-setup": cmd_demo_setup, "restore-practice": cmd_restore_practice, "set-pin": cmd_set_pin, "unlock": cmd_unlock, "list": cmd_list}[args.command](db, args)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
