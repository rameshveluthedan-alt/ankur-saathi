"""
The test accounts: ONE test school with its own admin, and the test teachers as plain TEACHERS (not each the admin of a school of one).

Found on 25 Oct: every test teacher (9000000101...) was the only person in a school of their own, and the first account in a new school becomes its admin, so each "teacher" logged in with
the admin role and saw admin screens a real teacher never sees. `normalise` converts the old layout in place; `create` now builds the new one.

    cd backend && python tests/test_test_teachers.py --env-file .env

Everything runs inside a transaction that is rolled back, so it never changes the accounts in your database. It covers what must change AND what must not: class data stays with its teacher, and
accounts that are not in a test school (the demo school's teacher, admin and "Change PIN" account) are never touched, whatever their phone number looks like.
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import io
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
os.environ.setdefault("PIN_HASH_ITERATIONS", "2000")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "backend"), str(ROOT / "prompts"), str(HERE)]
import _scratch
import create_test_teachers as ct
from app.services import auth_service as auth, register_service as rs

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


async def snapshot(db, like="hash_9%"):
    rows = await db.fetch("""SELECT t.phone_hash, t.role, s.school_code, t.pin_fixed, t.is_demo, t.id::text AS id FROM teachers t JOIN schools s ON s.id = t.school_id WHERE t.phone_hash LIKE $1 ORDER BY t.phone_hash""", like)
    return {r["phone_hash"][5:]: dict(r) for r in rows}


async def tests_only(db):
    """The test accounts, found the way the script finds them: by their SCHOOL (a phone pattern alone also matches accounts that are not test accounts)."""
    rows = await db.fetch("""SELECT t.phone_hash, t.role, s.school_code, t.pin_fixed, t.is_demo, t.id::text AS id FROM teachers t JOIN schools s ON s.id = t.school_id WHERE s.school_code LIKE 'MP-TEST-%' ORDER BY t.phone_hash""")
    return {r["phone_hash"][5:]: dict(r) for r in rows}


async def kids(db, teacher_id):
    return await db.fetchval("SELECT count(*) FROM children WHERE teacher_id = $1::uuid AND is_active", teacher_id)


async def run_quiet(coro):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        await coro
    return buf.getvalue()


async def main():
    db = await _scratch.connect()
    tr = db.transaction()
    await tr.start()
    try:
        await ct.wipe(db, "hash_90000001%", "MP-TEST-%")                          # start from nothing (inside the transaction, so nothing real is lost)
        # ---- bystanders that must never be touched: accounts OUTSIDE a test school, one with a phone number inside the test range
        await rs.register_teacher(db, "hash_9000000151", "ZZ-OTHER-1", ["grade_1"], pin_hash=None, enforce_join=False)          # first in its school: admin
        await rs.register_teacher(db, "hash_9000000150", "ZZ-OTHER-1", ["grade_1"], pin_hash=None, enforce_join=False)          # a teacher whose number LOOKS like a test teacher's
        bystanders_before = {k: v for k, v in (await snapshot(db)).items() if k in ("9000000150", "9000000151", "9000000199", "9876543210", "9876500000")}

        print("the OLD layout (what was in the database): five test teachers, each alone in a school of their own")
        old = {}
        for n in range(1, 6):
            me = await rs.register_teacher(db, f"hash_900000010{n}", f"MP-TEST-0{n}", ["grade_1", "grade_2", "grade_3"], pin_hash=auth.hash_pin("4826"), enforce_join=False)
            await db.execute("UPDATE teachers SET is_demo = TRUE, pin_fixed = TRUE WHERE id = $1::uuid", me["teacher_id"])
            old[n] = me["teacher_id"]
        await rs.commit_register(db, old[3], ct.register_rows(3, False), "x.csv")
        kids_before = {n: await kids(db, old[n]) for n in old}
        before = await tests_only(db)
        check("reproduced: all five test teachers are school ADMINS, in five different schools", all(before[f"900000010{n}"]["role"] == "school_admin" for n in range(1, 6)) and len({before[f"900000010{n}"]["school_code"] for n in range(1, 6)}) == 5)
        check("...and one of them has a class of 24 children", kids_before[3] == 24 and kids_before[1] == 0)

        print("\nnormalise: the old layout becomes the current one")
        out = await run_quiet(ct.cmd_normalise(db, SimpleNamespace(admin_pin="7351")))
        after = await tests_only(db)
        schools = [r["school_code"] for r in await db.fetch("SELECT school_code FROM schools WHERE school_code LIKE 'MP-TEST-%' ORDER BY 1")]
        check("ONE test school is left (MP-TEST-01); the four empty ones are removed", schools == ["MP-TEST-01"], schools)
        check("the five test teachers are now plain TEACHERS, all in that school", all(after[f"900000010{n}"]["role"] == "teacher" and after[f"900000010{n}"]["school_code"] == "MP-TEST-01" for n in range(1, 6)), {k: (v["role"], v["school_code"]) for k, v in after.items()})
        check("a new ADMIN account (9000000100) exists in that school, with a fixed demo PIN", after.get("9000000100", {}).get("role") == "school_admin" and after["9000000100"]["school_code"] == "MP-TEST-01" and after["9000000100"]["pin_fixed"] and after["9000000100"]["is_demo"], after.get("9000000100"))
        check("each teacher keeps the SAME account (the same id, so the same sign-in, PIN, class and history)", all(after[f"900000010{n}"]["id"] == before[f"900000010{n}"]["id"] for n in range(1, 6)))
        check("the class data stays with its teacher (24 children for teacher 3, none for the others)", {n: await kids(db, old[n]) for n in old} == kids_before)
        check("the report says what happened", "plain teacher" in out and "empty test school" in out, out)
        admin_id = after["9000000100"]["id"]
        listed = await auth.admin_teachers(db, admin_id)
        check("the test school's admin sees all SIX accounts of the school, and only that school", len(listed) == 6, len(listed))
        try:
            await auth.admin_teachers(db, after["9000000101"]["id"])
            denied = False
        except auth.AuthError as e:
            denied = e.code == "not_admin"
        check("a test teacher is refused the admin list (the role is really 'teacher' now)", denied)

        print("\nwhat must NOT change")
        bystanders_after = {k: v for k, v in (await snapshot(db)).items() if k in bystanders_before}
        check("accounts outside the test school are untouched: the demo teacher, demo admin and 'Change PIN' account (whichever exist here), and a teacher of another school whose number looks like a test one", bystanders_after == bystanders_before, (bystanders_before, bystanders_after))
        check("...in particular 9000000150 stays a teacher of ZZ-OTHER-1, not moved into the test school", bystanders_after["9000000150"]["school_code"] == "ZZ-OTHER-1" and bystanders_after["9000000150"]["role"] == "teacher")
        out2 = await run_quiet(ct.cmd_normalise(db, SimpleNamespace(admin_pin="7351")))
        check("running it again changes nothing (idempotent) and says so", await tests_only(db) == after and "already in order" in out2, out2)

        print("\ncreate: the current layout from scratch")
        await ct.wipe(db, "hash_90000001%", "MP-TEST-%")
        gone = await tests_only(db)
        check("the wipe removed the test accounts and the test school (and only those)", not gone and not await db.fetchval("SELECT 1 FROM schools WHERE school_code LIKE 'MP-TEST-%'") and await db.fetchval("SELECT 1 FROM schools WHERE school_code = 'ZZ-OTHER-1'"))
        args = SimpleNamespace(count=2, recreate=False, pin="4826", admin_pin="7351", no_names=True)
        await run_quiet(ct.cmd_create(db, args))
        new = await tests_only(db)
        check("create makes the admin first and then the teachers: admin + 2 plain teachers, all in MP-TEST-01", {k: v["role"] for k, v in new.items()} == {"9000000100": "school_admin", "9000000101": "teacher", "9000000102": "teacher"} and {v["school_code"] for v in new.values()} == {"MP-TEST-01"}, {k: (v["role"], v["school_code"]) for k, v in new.items()})
        check("each test teacher has a class of 24 children and a fixed demo PIN; the admin has no class", await kids(db, new["9000000101"]["id"]) == 24 and await kids(db, new["9000000102"]["id"]) == 24 and await kids(db, new["9000000100"]["id"]) == 0 and all(v["pin_fixed"] for v in new.values()))
        check("the admin sees both teachers and itself (3 accounts)", len(await auth.admin_teachers(db, new["9000000100"]["id"])) == 3)
        await run_quiet(ct.cmd_create(db, SimpleNamespace(count=1, recreate=True, pin="4826", admin_pin="7351", no_names=True)))
        again = await tests_only(db)
        check("--recreate rebuilds only that teacher (a new account) and keeps the admin and the other teacher", again["9000000101"]["id"] != new["9000000101"]["id"] and again["9000000100"]["id"] == new["9000000100"]["id"] and again["9000000102"]["id"] == new["9000000102"]["id"] and await kids(db, again["9000000101"]["id"]) == 24)
        await run_quiet(ct.cmd_create(db, SimpleNamespace(count=2, recreate=False, pin="4826", admin_pin="7351", no_names=True)))
        check("creating again without --recreate leaves everything as it is", await tests_only(db) == again)
        await run_quiet(ct.cmd_remove(db, SimpleNamespace(yes=True)))
        check("`remove` deletes the admin, the teachers and the test school, and leaves the other school's accounts alone", not await tests_only(db) and {k: v for k, v in (await snapshot(db)).items() if k in bystanders_before} == bystanders_before)

        print("\nthe nightly job and the documents")
        nightly = (ROOT / "scripts" / "nightly_reset.py").read_text(encoding="utf-8")
        check("the nightly job runs `normalise` as a step that cannot stop the demo reset (so the cloud fixes itself after the next deploy)", 'create_test_teachers.py"), "normalise"], env_args, fatal=False' in nightly)
        check("the safety rule is still in the script: only test-school teachers are found by phone (9000000199 is never in the pattern)", not re.match(ct.TEST_PHONE, "hash_9000000199") and re.match(ct.TEST_PHONE, "hash_9000000100") and re.match(ct.TEST_PHONE, "hash_9000000105") and re.match(ct.TEST_PHONE, "hash_9000000198") and not re.match(ct.TEST_PHONE, "hash_9000000200"))
    finally:
        await tr.rollback()
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: one test school with its admin and plain teachers; the old layout converts without touching class data or any other account")


if __name__ == "__main__":
    asyncio.run(main())
