"""
REAL accounts for a pilot (scripts/auth_admin.py create-school / create-account): a school of its own (never the demo school), a leader and its
teachers, each with a temporary password that must be changed at the first sign-in; demo-style codes and codes in use are refused; nothing is
left half-made. Runs on the lab database with scratch codes, removed afterwards.

    python backend/tests/test_real_accounts.py --env-file backend/.env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import io
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = Path(HERE).parents[1]
import _scratch
sys.path.insert(0, str(ROOT / "scripts"))
import auth_admin as aa
from app.services import auth_service as auth

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


async def run(cmd, db, **kw):
    """(output, exited): runs a command, catching the SystemExit a refusal uses."""
    buf = io.StringIO()
    exited = None
    try:
        with contextlib.redirect_stdout(buf):
            await cmd(db, SimpleNamespace(grades=None, **kw))
    except SystemExit as e:
        exited = str(e)
    return buf.getvalue(), exited


async def main():
    db = await _scratch.connect()
    tag = uuid.uuid4().hex[:4].upper()
    school, leader, t1, t2 = f"PILOTX-{tag}", f"XA{tag}", f"XT{tag}", f"XU{tag}"
    school2 = f"PILOTY-{tag}"
    try:
        print("refusals (nothing is created)")
        out, ex = await run(aa.cmd_create_school, db, school="MP-DEMO-001", leader=leader, teachers=t1)
        check("the demo school is refused", ex and "demo school" in ex and not await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", leader))
        out, ex = await run(aa.cmd_create_school, db, school=school, leader="MPT150", teachers=t1)
        check("a demo-style test code is refused", ex and "demo or test" in ex and not await db.fetchval("SELECT 1 FROM schools WHERE school_code = $1", school))
        out, ex = await run(aa.cmd_create_school, db, school=school, leader=leader, teachers=f"{t1},{t1}")
        check("the same code twice is refused", ex and "twice" in ex)
        out, ex = await run(aa.cmd_create_school, db, school=school, leader=leader, teachers="MPT101")
        check("a code already in use is refused (here the demo teacher's)", ex and ("in use" in ex or "demo" in ex))
        out, ex = await run(aa.cmd_create_school, db, school=school, leader=leader, teachers=t1, block="x" * 61)
        check("a block name over 60 characters is refused, nothing made", ex and "block" in ex and not await db.fetchval("SELECT 1 FROM schools WHERE school_code = $1", school))
        out, ex = await run(aa.cmd_create_school, db, school=school, leader=leader, teachers=t1, district="<b>Sehore</b>")
        check("a district with markup is refused, nothing made", ex and "district" in ex and not await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", leader))
        out, ex = await run(aa.cmd_create_school, db, school=school, leader=leader, teachers=t1, printer="maybe")
        check("a printer value other than yes or no is refused", ex and "printer" in ex)

        print("\na real school with a leader and two teachers, its block, district and printer")
        out, ex = await run(aa.cmd_create_school, db, school=school, leader=leader, teachers=f"{t1},{t2}", block="  सीहोर   ब्लॉक ", district="Sehore", printer="yes")
        srow = await db.fetchrow("SELECT block_name, district_name, has_printer FROM schools WHERE school_code = $1", school)
        check("block (spaces tidied), district and printer stored", srow and (srow["block_name"], srow["district_name"], srow["has_printer"]) == ("सीहोर ब्लॉक", "Sehore", True), dict(srow or {}))
        check("the details are printed after the passwords", "School details: block सीहोर ब्लॉक, district Sehore, printer yes" in out, out)
        rows = {r["phone_hash"]: dict(r) for r in await db.fetch("""SELECT t.phone_hash, t.role, t.must_change_pin, t.is_demo, t.pin_fixed, t.pin_hash, s.school_code
                                                                  FROM teachers t JOIN schools s ON s.id = t.school_id WHERE t.phone_hash = ANY($1::text[])""", [leader, t1, t2])}
        check("created, no refusal", ex is None and len(rows) == 3, (ex, list(rows)))
        check("the leader is the school's admin, the others teachers, all in the new school",
              rows.get(leader, {}).get("role") == "school_admin" and rows.get(t1, {}).get("role") == "teacher" and all(r["school_code"] == school for r in rows.values()))
        check("not demo accounts, not fixed: they can choose their own password", all(not r["is_demo"] and not r["pin_fixed"] for r in rows.values()))
        check("each must change the temporary password at the first sign-in", all(r["must_change_pin"] for r in rows.values()))
        temps = [l.split("temporary password: ")[1].strip() for l in out.splitlines() if "temporary password: " in l]
        check("each temporary password is printed once, and it is the one stored",
              len(temps) == 3 and all(auth.verify_pin(p, rows[c]["pin_hash"]) for p, c in zip(temps, [leader, t1, t2])), out)
        out, ex = await run(aa.cmd_create_school, db, school=school, leader=f"XB{tag}", teachers="")
        check("the same school cannot be created twice", ex and "already exists" in ex)
        out, ex = await run(aa.cmd_create_school, db, school=school2, leader=f"XC{tag}", teachers="")
        srow2 = await db.fetchrow("SELECT block_name, district_name, has_printer FROM schools WHERE school_code = $1", school2)
        check("without the options: no block or district, no printer (as before)", ex is None and srow2 and (srow2["block_name"], srow2["district_name"], srow2["has_printer"]) == (None, None, False), (ex, dict(srow2 or {})))

        print("\none more teacher")
        t3 = f"XV{tag}"
        out, ex = await run(aa.cmd_create_account, db, school=school, code=t3)
        r3 = await db.fetchrow("SELECT t.role, t.must_change_pin, s.school_code FROM teachers t JOIN schools s ON s.id = t.school_id WHERE t.phone_hash = $1", t3)
        check("added to the existing school as a teacher, with a temporary password", ex is None and r3 and r3["role"] == "teacher" and r3["school_code"] == school and r3["must_change_pin"])
        out, ex = await run(aa.cmd_create_account, db, school="NO-SUCH-SCHOOL", code=f"XW{tag}")
        check("an unknown school is refused", ex and "does not exist" in ex)
        out, ex = await run(aa.cmd_create_account, db, school=school, code=t3)
        check("a code in use is refused", ex and "in use" in ex)
    finally:
        for code in (school, school2):
            await db.execute("DELETE FROM teachers WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", code)
            await db.execute("DELETE FROM schools WHERE school_code = $1", code)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: real pilot accounts in a school of their own, temporary passwords that must be changed, demo codes and codes in use refused")
