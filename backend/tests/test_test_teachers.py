"""
The demo and test accounts, named by EMPLOYEE CODE (docs/DEMO_ACCESS.md): ONE school, MP-DEMO-001, with ONE leader (MPA101), the demo teacher (MPT101), the practice account (MPT199)
and the test teachers MPT102 upwards, all plain teachers.

Accounts made before employee codes were named by a phone number, and the test teachers lived in a test school of their own with its own admin (9000000100). The migration
(scripts/migrate_to_employee_codes.py, run first by the nightly job) renames them, keeps each one's class and history, moves the test teachers into the demo school and removes the old test admin
and the empty test schools.

    cd backend && python tests/test_test_teachers.py --env-file .env

Everything runs inside a transaction that is rolled back, so it never changes the accounts in your database. It covers what must change AND what must not: an employee code looks the same as a real
teacher's (MPT150, say), so a teacher of ANOTHER school with a test-looking code must never be renamed, moved, reset or deleted by any of these scripts.
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
import auth_admin as aa
import create_test_teachers as ct
import demo_accounts as da
from migrate_to_employee_codes import migrate, describe
from app.services import auth_service as auth, register_service as rs

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


async def row(db, ident):
    r = await db.fetchrow("""SELECT t.phone_hash, t.role, s.school_code, t.pin_fixed, t.is_demo, t.pin_hash, t.id::text AS id
                             FROM teachers t JOIN schools s ON s.id = t.school_id WHERE t.phone_hash = $1""", ident)
    return dict(r) if r else None


async def kids(db, teacher_id):
    return await db.fetchval("SELECT count(*) FROM children WHERE teacher_id = $1::uuid AND is_active", teacher_id)


async def run_quiet(coro):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        await coro
    return buf.getvalue()


async def main():
    db = await _scratch.connect()
    await auth.ensure_consent_table(db)                  # created and COMMITTED first: the test transaction below is rolled back
    tr = db.transaction()
    await tr.start()
    try:
        if not await db.fetchval("SELECT 1 FROM schools WHERE school_code = $1", da.DEMO_SCHOOL):
            print("SKIPPED: the demo school is not in this database (load db/seeds/classroom/01_profile.sql first).")
            return
        # ---- start from nothing: every test account of either layout, inside the transaction (so nothing real is lost)
        gone = [r["id"] for r in await db.fetch("""SELECT t.id FROM teachers t JOIN schools s ON s.id = t.school_id
                                                   WHERE s.school_code LIKE 'MP-TEST-%' OR (s.school_code = $1 AND (t.phone_hash ~ $2 OR t.phone_hash ~ '^hash_90000001'))""", da.DEMO_SCHOOL, da.TEST_CODE_RE)]
        await da.wipe_teachers(db, gone)
        await db.execute("DELETE FROM schools WHERE school_code LIKE 'MP-TEST-%'")
        # ---- put the three fixed demo accounts in their OLD state (named by a phone number), whatever state this database is in
        for new, old, role in ((da.DEMO_TEACHER, "hash_9876543210", "teacher"), (da.LEADER, "hash_9876500000", "school_admin"), (da.PRACTICE, "hash_9000000199", "teacher")):
            if await row(db, new):
                await db.execute("UPDATE teachers SET phone_hash = $2 WHERE phone_hash = $1", new, old)
            elif not await row(db, old):
                await aa.ensure_account(db, old[5:], role, ["grade_1"])
        # ---- bystanders that must never be touched: teachers of ANOTHER school with test-looking identifiers
        await rs.register_teacher(db, "ZZADM1", "ZZ-OTHER-1", ["grade_1"], pin_hash=auth.hash_pin("gh7k2m"), enforce_join=False)          # first in its school: its leader
        await rs.register_teacher(db, "MPT150", "ZZ-OTHER-1", ["grade_1"], pin_hash=auth.hash_pin("gh7k2m"), enforce_join=False)          # a REAL-looking employee code in the test range
        await rs.register_teacher(db, "hash_9000000150", "ZZ-OTHER-1", ["grade_1"], pin_hash=auth.hash_pin("gh7k2m"), enforce_join=False)  # an old-style number in the test range
        by_before = {k: await row(db, k) for k in ("ZZADM1", "MPT150", "hash_9000000150")}

        print("the OLD layout of 25 Oct: a test school with its own admin and five test teachers; plus one teacher alone in a school of their own (the older layout)")
        old = {}
        await rs.register_teacher(db, "hash_9000000100", "MP-TEST-01", ["grade_1"], pin_hash=auth.hash_pin("7351"), enforce_join=False)     # first: the test school's admin
        for n in range(1, 6):
            me = await rs.register_teacher(db, f"hash_900000010{n}", "MP-TEST-01", ["grade_1", "grade_2", "grade_3"], pin_hash=auth.hash_pin("4826"), enforce_join=False)
            await db.execute("UPDATE teachers SET is_demo = TRUE, pin_fixed = TRUE WHERE id = $1::uuid", me["teacher_id"])
            old[n] = me["teacher_id"]
        alone = await rs.register_teacher(db, "hash_9000000106", "MP-TEST-02", ["grade_1"], pin_hash=auth.hash_pin("4826"), enforce_join=False)      # alone in a school: its admin
        old[6] = alone["teacher_id"]
        await rs.commit_register(db, old[3], ct.register_rows(3, False), "x.csv")
        fixed_before = {k: await row(db, k) for k in ("hash_9876543210", "hash_9876500000", "hash_9000000199")}
        kids_before = {n: await kids(db, old[n]) for n in old}
        check("reproduced: the old test school has an admin and five teachers, a sixth teacher is alone in MP-TEST-02, and one class has 24 children",
              (await row(db, "hash_9000000100"))["role"] == "school_admin" and (await row(db, "hash_9000000106"))["role"] == "school_admin" and kids_before[3] == 24 and kids_before[1] == 0)

        print("\nthe migration: phone numbers become employee codes")
        done = await migrate(db)
        check("nine accounts are renamed: the demo teacher, the leader, the practice account and the six test teachers", len(done["renamed"]) == 9, done["renamed"])
        same_fixed = [(await row(db, new))["id"] == fixed_before[o]["id"] for o, new in (("hash_9876543210", "MPT101"), ("hash_9876500000", "MPA101"), ("hash_9000000199", "MPT199"))]
        same_tests = [(await row(db, da.test_code(n)))["id"] == old[n] for n in range(1, 7)]
        check("each keeps the SAME account (the same id, so the same sign-in, class and history), now under its employee code", all(same_fixed) and all(same_tests), (same_fixed, same_tests))
        tests_rows = [await row(db, da.test_code(n)) for n in range(1, 7)]
        check("the test teachers MPT102 to MPT107 are plain TEACHERS of the demo school, including the one that was the admin of a school of its own",
              all(r and r["role"] == "teacher" and r["school_code"] == da.DEMO_SCHOOL for r in tests_rows), tests_rows)
        check("the leader is still the school leader (the role comes from the account, never from the letters of the code)", (await row(db, "MPA101"))["role"] == "school_admin" and (await row(db, "MPT101"))["role"] == "teacher")
        check("the class data stays with its teacher (24 children for the third test teacher, none for the first)", await kids(db, old[3]) == 24 and await kids(db, old[1]) == 0)
        check("the old test admin and BOTH old test schools are gone", not await row(db, "hash_9000000100") and not await db.fetchval("SELECT 1 FROM schools WHERE school_code LIKE 'MP-TEST-%'") and done["removed_admins"] == 1 and done["removed_schools"] == 2, done)
        check("no account is named by a phone number any more in the demo school", not await db.fetchval("SELECT 1 FROM teachers t JOIN schools s ON s.id = t.school_id WHERE s.school_code = $1 AND t.phone_hash LIKE 'hash\\_%'", da.DEMO_SCHOOL))

        print("\nwhat must NOT change")
        by_after = {k: await row(db, k) for k in by_before}
        check("a teacher of ANOTHER school whose code looks like a test code (MPT150), its leader and an old-style number in the test range are untouched: the same school, role, password and id", by_after == by_before, by_after)
        snap = {r["phone_hash"]: dict(r) for r in await db.fetch("SELECT phone_hash, role, school_id::text, id::text FROM teachers")}
        done2 = await migrate(db)
        snap2 = {r["phone_hash"]: dict(r) for r in await db.fetch("SELECT phone_hash, role, school_id::text, id::text FROM teachers")}
        check("running it again changes nothing, and says so", snap == snap2 and "already use employee codes" in describe(done2), describe(done2))

        print("\nsigning in and the leader's list")
        res = await auth.login(db, "MPT102", "4826")
        check("a test teacher signs in with the employee code, and her profile carries it", res["employee_code"] == "MPT102" and res["role"] == "teacher" and bool(res["token"]), res.get("employee_code"))
        try:
            await auth.login(db, "hash_9000000101", "4826"); old_works = True
        except auth.AuthError as e:
            old_works = e.code != "bad_login"
        check("the old phone-number name no longer signs in", not old_works)
        listed = await auth.admin_teachers(db, (await row(db, "MPA101"))["id"])
        in_school = await db.fetchval("SELECT count(*) FROM teachers t JOIN schools s ON s.id = t.school_id WHERE s.school_code = $1", da.DEMO_SCHOOL)
        codes = {x["code"] for x in listed}
        check("the school leader sees every account of the school (and only that school), each by its employee code", len(listed) == in_school and {"MPT101", "MPT102", "MPT107", "MPA101", "MPT199"} <= codes and "MPT150" not in codes, sorted(codes))
        try:
            await auth.admin_teachers(db, (await row(db, "MPT102"))["id"]); denied = False
        except auth.AuthError as e:
            denied = e.code == "not_admin"
        check("a teacher is refused the list (the role is really 'teacher')", denied)

        print("\ndemo-setup sets the demo passwords, in the demo school only")
        await run_quiet(aa.cmd_demo_setup(db, SimpleNamespace(demo_pin="4826", admin_pin="7351", practice_pin="3917")))
        fixed_ok = [auth.verify_pin("4826", (await row(db, c))["pin_hash"]) for c in ("MPT101", "MPT102", "MPT107")]
        check("the demo teacher and the test teachers have the fixed published password, and the leader has hers", all(fixed_ok) and auth.verify_pin("7351", (await row(db, "MPA101"))["pin_hash"]), fixed_ok)
        p = await row(db, "MPT199")
        check("the practice account is NOT fixed (it can change and reset its password) and has the published one", p["pin_fixed"] is False and auth.verify_pin("3917", p["pin_hash"]))
        b = await row(db, "MPT150")
        check("the bystander MPT150 of another school kept its own password (demo-setup never resets a real teacher with a test-looking code)", auth.verify_pin("gh7k2m", b["pin_hash"]) and not auth.verify_pin("4826", b["pin_hash"]))
        await run_quiet(aa.cmd_restore_practice(db, SimpleNamespace(practice_pin="3917")))
        check("restore-practice leaves the bystanders alone too", {k: await row(db, k) for k in by_before} == by_before)

        print("\ncreate and remove")
        await run_quiet(ct.cmd_remove(db, SimpleNamespace(yes=True)))
        still = [await row(db, c) for c in ("MPT101", "MPA101", "MPT199")]
        check("`remove` deletes the test teachers MPT102 to MPT198 of the demo school and nothing else", not await ct.test_ids(db) and all(still) and {k: await row(db, k) for k in by_before} == by_before)
        await run_quiet(ct.cmd_create(db, SimpleNamespace(count=2, recreate=False, pin="4826", no_names=True)))
        new = {c: await row(db, c) for c in ("MPT102", "MPT103")}
        made_ok = [bool(v) and v["role"] == "teacher" and v["school_code"] == da.DEMO_SCHOOL and v["pin_fixed"] and auth.verify_pin("4826", v["pin_hash"]) for v in new.values()]
        made_kids = [await kids(db, v["id"]) for v in new.values()]
        check("create makes MPT102 and MPT103: plain teachers of the demo school with a fixed demo password and a class of 24 children each", all(made_ok) and made_kids == [24, 24], (made_ok, made_kids))
        leader_list = {x["code"] for x in await auth.admin_teachers(db, (await row(db, "MPA101"))["id"])}
        check("the leader's list now has the new teachers", {"MPT102", "MPT103"} <= leader_list)
        await run_quiet(ct.cmd_create(db, SimpleNamespace(count=1, recreate=True, pin="4826", no_names=True)))
        again2 = {c: await row(db, c) for c in ("MPT102", "MPT103")}
        check("--recreate rebuilds only that teacher (a new account) and keeps the other", again2["MPT102"]["id"] != new["MPT102"]["id"] and again2["MPT103"]["id"] == new["MPT103"]["id"])
        await run_quiet(ct.cmd_create(db, SimpleNamespace(count=2, recreate=False, pin="4826", no_names=True)))
        check("creating again without --recreate leaves everything as it is", {c: await row(db, c) for c in ("MPT102", "MPT103")} == again2)

        print("\nthe rules in the scripts, and the nightly job")
        check("the test range is MPT102 to MPT198: it never matches the demo teacher MPT101, the practice account MPT199 or the leader MPA101",
              all(re.match(da.TEST_CODE_RE, c) for c in ("MPT102", "MPT110", "MPT150", "MPT198")) and not any(re.match(da.TEST_CODE_RE, c) for c in ("MPT101", "MPT199", "MPA101", "MPT100", "MPT200", "MPB101")))
        check("an old number maps to its code (9000000101 to MPT102, 9000000197 to MPT198); the old test admin and numbers outside the range map to nothing",
              da.new_code_for("hash_9000000101") == "MPT102" and da.new_code_for("hash_9000000197") == "MPT198" and da.new_code_for("hash_9000000100") is None and da.new_code_for("hash_9000000198") is None and da.new_code_for("hash_5551234567") is None)
        try:
            da.test_code(98); refused = False
        except ValueError:
            refused = True
        check("there are 97 test teachers at most (MPT102 to MPT198): the 98th would collide with the practice account", refused and da.test_code(97) == "MPT198" and da.test_code(1) == "MPT102")
        nightly = (ROOT / "scripts" / "nightly_reset.py").read_text(encoding="utf-8")
        i, j = nightly.index('os.path.join(HERE, "migrate_to_employee_codes.py")'), nightly.index('os.path.join(HERE, "auth_admin.py")')
        check("the nightly job runs the migration BEFORE everything else, as a step that cannot stop the demo reset (so the cloud converts itself after the next deploy)", i < j and 'migrate_to_employee_codes.py")], env_args, fatal=False' in nightly)
        mig = (ROOT / "scripts" / "migrate_to_employee_codes.py").read_text(encoding="utf-8")
        check("the migration is scoped: it reads only accounts of the demo school or of an old test school, and moves only teachers OF an old test school", "s.school_code = $1 OR s.school_code LIKE $2" in mig and "school_id IN (SELECT id FROM schools WHERE school_code LIKE $3)" in mig)
    finally:
        await tr.rollback()
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: employee codes for the demo and test accounts; the old layouts convert without touching class data, and no other school's account is ever touched")


if __name__ == "__main__":
    asyncio.run(main())
