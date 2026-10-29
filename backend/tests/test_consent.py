"""
The school's consent confirmation (docs/PRIVACY.md, "Consent").

A school that is created confirms, once, that the children's parents or guardians have been told and have given their permission; the exact wording and its version are kept with the date and
who gave it. Joining an existing school asks for nothing. This checks the rules the screens cannot show: the wording on the screen is word for word the wording on the server, the school, its
admin and its record exist together or not at all, and what a stranger or an ordinary teacher can and cannot do.

    cd backend && python tests/test_consent.py --env-file .env
Everything runs inside a transaction that is rolled back.
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("AUTH_MODE", "off")
os.environ.setdefault("PIN_HASH_ITERATIONS", "2000")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "backend"), str(ROOT / "prompts"), str(HERE)]
import _scratch
from app.services import auth_service as auth, register_service as rs

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


async def rows(db, sql, *a):
    return [dict(r) for r in await db.fetch(sql, *a)]


async def main():
    print("the wording: the same on the screen and on the server")
    js = (ROOT / "pwa" / "src" / "services" / "consent.js").read_text(encoding="utf-8")
    grab = lambda key: re.search(rf'^\s*{key}:\s*"(.*)",?\s*$', js, re.M).group(1)
    check("the app's version is the server's version", grab("version") == auth.CONSENT_VERSION, (grab("version"), auth.CONSENT_VERSION))
    check("the English wording is word for word the same", grab("en") == auth.CONSENT_TEXT["en"])
    check("the Hindi wording is word for word the same", grab("hi") == auth.CONSENT_TEXT["hi"])
    en, hi = auth.CONSENT_TEXT["en"], auth.CONSENT_TEXT["hi"]
    check("it says the three things a school is confirming: parents were told and gave permission; photos are not kept; names never go to the AI",
          all(x in en for x in ("parents or guardians", "has their permission", "not kept", "never sent to the AI")) and all(x in hi for x in ("अभिभावकों", "अनुमति", "सहेजी नहीं", "कभी नहीं भेजे")))
    check("what it says about photos and names is what the code does: the tests for those promises exist", (ROOT / "backend" / "tests" / "test_names_never_reach_ai.py").is_file() and (ROOT / "backend" / "tests" / "test_names_static_guard.py").is_file())
    check("the statement as kept is English then Hindi", auth.consent_statement() == en + "\n" + hi)

    db = await _scratch.connect()
    await auth.ensure_consent_table(db)                  # created and COMMITTED first: the test transaction below is rolled back
    tr = db.transaction()
    await tr.start()
    try:
        print("\nthe table")
        await auth.ensure_consent_table(db); await auth.ensure_consent_table(db)
        check("creating the table twice is harmless (it is created on first use, and by the nightly job for the demonstration schools)", await db.fetchval("SELECT to_regclass('school_consents') IS NOT NULL"))

        print("\na NEW school needs the confirmation")
        async def reg(phone, school, **kw):
            return await rs.register_teacher(db, phone, school, ["grade_1"], pin_hash=auth.hash_pin("7392"), join_code=kw.pop("join_code", None), **kw)
        async def gone(phone, school):
            return not await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", phone) and not await db.fetchval("SELECT 1 FROM schools WHERE school_code = $1", school)
        try:
            await reg("hash_ct_0", "CT-NEW-0", require_consent=True); refused = False
        except rs.ConsentRequired as e:
            refused = "सहमति" in str(e) and "confirm" in str(e)
        check("with no confirmation it is refused, with a message in English and Hindi", refused)
        check("...and NOTHING was created: no school, no teacher", await gone("hash_ct_0", "CT-NEW-0"))
        try:
            await reg("hash_ct_0", "CT-NEW-0", require_consent=True, consent_version="v0"); stale = False
        except rs.ConsentRequired as e:
            stale = "changed" in str(e)
        check("a confirmation of an OLD wording is refused, saying the wording changed", stale and await gone("hash_ct_0", "CT-NEW-0"))
        made = await reg("hash_ct_1", "CT-NEW-1", require_consent=True, consent_version=auth.CONSENT_VERSION)
        recs = await rows(db, "SELECT version, statement, attested_by FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'CT-NEW-1')")
        check("the current wording creates the school and its admin", made["role"] == "school_admin" and made["join_code"])
        check("...and keeps ONE record: the version, the server's own wording in both languages, and who gave it", len(recs) == 1 and recs[0]["version"] == "v1" and recs[0]["statement"] == auth.consent_statement() and str(recs[0]["attested_by"]) == made["teacher_id"], recs)

        print("\nthe school and its record exist together, or not at all")
        original = auth.record_consent
        async def broken(*a, **k):
            raise RuntimeError("the database refused the record")
        auth.record_consent = broken
        try:
            await reg("hash_ct_2", "CT-NEW-2", require_consent=True, consent_version=auth.CONSENT_VERSION); failed = False
        except RuntimeError:
            failed = True
        finally:
            auth.record_consent = original
        check("if keeping the record fails, the whole registration is undone: no school without its confirmation, no teacher without a school", failed and await gone("hash_ct_2", "CT-NEW-2"))

        print("\njoining a school that exists")
        joined = await reg("hash_ct_3", "CT-NEW-1", join_code=made["join_code"], require_consent=True)
        check("a teacher who joins with the join code needs no confirmation, and none is added", joined["role"] == "teacher" and await db.fetchval("SELECT count(*) FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'CT-NEW-1')") == 1)
        legacy = await rs.register_teacher(db, "hash_ct_4", "CT-LEGACY", ["grade_1"], pin_hash=auth.hash_pin("7392"), enforce_join=False)
        check("the operator's own scripts still create schools with no confirmation (it is the API that asks), so the demo and test schools are not blocked", legacy["role"] == "school_admin" and await db.fetchval("SELECT count(*) FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'CT-LEGACY')") == 0)

        print("\nthe admin's screen and what the admin can do")
        sch = await auth.admin_school(db, made["teacher_id"])
        check("the admin sees the confirmation (version, date, only the END of the phone number) and the wording to read", sch["consent"]["version"] == "v1" and sch["consent"]["by"].startswith("••••") and sch["consent"]["demo"] is False and sch["consent_text"]["version"] == "v1" and sch["consent_text"]["hi"] == hi)
        sch = await auth.admin_school(db, legacy["teacher_id"])
        check("a school with no record shows None (not an error) and still offers the wording", sch["consent"] is None and sch["consent_text"]["en"] == en)
        try:
            await auth.admin_record_consent(db, legacy["teacher_id"], "v0"); r1 = False
        except auth.AuthError as e:
            r1 = e.status == 409 and e.code == "consent_stale"
        check("an admin confirming an OLD wording is refused (409, consent_stale)", r1)
        done = await auth.admin_record_consent(db, legacy["teacher_id"], "v1")
        check("an admin of an older school confirms: it is recorded and her screen shows it", done["consent"]["version"] == "v1" and (await auth.admin_school(db, legacy["teacher_id"]))["consent"] is not None)
        await auth.admin_record_consent(db, legacy["teacher_id"], "v1")
        check("confirming again ADDS a row (what was agreed, and when, stays on record) and the latest is the one shown", await db.fetchval("SELECT count(*) FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'CT-LEGACY')") == 2)
        try:
            await auth.admin_record_consent(db, joined["teacher_id"], "v1"); r2 = False
        except auth.AuthError as e:
            r2 = e.status == 403 and e.code == "not_admin"
        check("an ordinary teacher cannot confirm for the school (403, not_admin)", r2)
        ev = [r["event"] for r in await rows(db, "SELECT event FROM auth_events WHERE teacher_id = $1::uuid", legacy["teacher_id"])]
        check("the confirmation is written to the audit trail", "consent_recorded" in ev)

        print("\nthe demonstration schools")
        check("a demonstration school with no record gets the statement that everything in it is fictional, once", await auth.ensure_demo_consent(db, "CT-LEGACY") is False and await auth.ensure_demo_consent(db, "CT-NO-SUCH") is False)
        await rs.register_teacher(db, "hash_ct_5", "CT-DEMO", ["grade_1"], pin_hash=None, enforce_join=False)
        check("(a school that has none) is given it...", await auth.ensure_demo_consent(db, "CT-DEMO") is True)
        check("...once: the second call changes nothing", await auth.ensure_demo_consent(db, "CT-DEMO") is False and await db.fetchval("SELECT count(*) FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'CT-DEMO')") == 1)
        shown = await auth.latest_consent(db, await db.fetchval("SELECT id FROM schools WHERE school_code = 'CT-DEMO'"))
        check("its admin screen says it is a demonstration school", shown["demo"] is True and shown["version"] == "demo")

        print("\nwhen a school is deleted its records go with it")
        await db.execute("DELETE FROM teachers WHERE school_id = (SELECT id FROM schools WHERE school_code = 'CT-NEW-1')")
        await db.execute("DELETE FROM schools WHERE school_code = 'CT-NEW-1'")
        check("the school's confirmations are deleted with it (ON DELETE CASCADE): nothing is left behind", await db.fetchval("SELECT count(*) FROM school_consents WHERE statement = $1 AND school_id NOT IN (SELECT id FROM schools)", auth.consent_statement()) == 0)
    finally:
        await tr.rollback()
        await db.close()

    print("\nthe scripts")
    nightly_src = (ROOT / "scripts" / "auth_admin.py").read_text(encoding="utf-8")
    check("the nightly job's 'restore-practice' gives the demo school its statement (so the cloud needs no manual step)", "ensure_demo_consent(db, DEMO_SCHOOL)" in nightly_src.split("async def cmd_restore_practice")[1].split("async def ")[0])
    check("'demo-setup' does too", "ensure_demo_consent(db, DEMO_SCHOOL)" in nightly_src.split("async def cmd_demo_setup")[1].split("async def ")[0])
    check("there is no separate test school any more: the test teachers teach in the demo school, which has the statement", "ensure_demo_consent" not in (ROOT / "scripts" / "create_test_teachers.py").read_text(encoding="utf-8") and "TEST_SCHOOL = DEMO_SCHOOL" in (ROOT / "scripts" / "create_test_teachers.py").read_text(encoding="utf-8"))
    sql = (ROOT / "db" / "schema" / "13_school_consent.sql").read_text(encoding="utf-8")
    check("the table is only CREATED, never ALTERed: no change to an existing table, so it works with the app's own database rights", "CREATE TABLE IF NOT EXISTS school_consents" in sql and not re.search(r"^\s*ALTER\s+TABLE", sql, re.I | re.M))
    check("the table cascades with the school and keeps the wording and the version", "ON DELETE CASCADE" in sql and "statement" in sql and "version" in sql)
    privacy = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")
    check("docs/PRIVACY.md describes it (and says plainly that it is the school's confirmation, not a record from each parent)", "## Consent" in privacy and "each parent" in privacy)


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: a new school is created only with its confirmation, kept with the exact wording, atomically; joining needs none; the admin can confirm for an older school")
