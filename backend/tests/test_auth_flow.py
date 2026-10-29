"""
Sign-in end to end, with enforcement ON: registration (a practice database only: SELF_REGISTRATION), login by EMPLOYEE CODE, lockout, session tokens on every kind of route,
changing a password, and the school leader's reset. Uses scratch schools and removes them afterwards.

    cd backend && python tests/test_auth_flow.py

Needs the database with db/schema/09_auth.sql loaded (and 07/08). The app connects as it normally does (DATABASE_URL).
"""
import asyncio
import io
import os
import sys
import time

os.environ["SESSION_SECRET"] = "integration-test-secret"
os.environ["PIN_HASH_ITERATIONS"] = "2000"
os.environ["AUTH_MODE"] = "enforce"
os.environ["SELF_REGISTRATION"] = "true"          # the scratch accounts below are made through the registration route; section 1a shows that the DEFAULT is closed
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), p) for p in ("..", "../../prompts", "../../scripts")]

import asyncpg
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.services import auth_service as a

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def sql(q, *args, fetch=False):
    async def go():
        import anchor_common as ac
        import argparse
        ap = argparse.ArgumentParser(); ac.add_db_args(ap)
        db = await ac.connect(ap.parse_args([]))
        try:
            return await (db.fetch(q, *args) if fetch else db.execute(q, *args))
        finally:
            await db.close()
    return asyncio.run(go())


def clean():
    sql("DELETE FROM teachers WHERE phone_hash LIKE 'hash_authtest_%' OR phone_hash LIKE 'ZZT1__'")
    sql("DELETE FROM schools WHERE school_code LIKE 'AUTHTEST-%'")          # a school's consent rows go with it (ON DELETE CASCADE)


H = lambda t: {"Authorization": f"Bearer {t}"}
clean()
with TestClient(app) as c:
    reg = lambda phone, pin, school, grades=("grade_1",), join=None: c.post("/api/auth/register", json={"phone_hash": f"hash_authtest_{phone}", "pin": pin, "school_code": school, "enrolled_grades": list(grades), "consent_version": "v1", "join_code": join})
    login = lambda phone, pin: c.post("/api/auth/login", json={"phone_hash": f"hash_authtest_{phone}", "pin": pin})
    code = lambda r: (r.json().get("detail") or {}).get("code") if isinstance(r.json().get("detail"), dict) else None

    print("1. registration: the first teacher of a school is its admin; the rest need the join code")
    r = reg("a1", "482615", "authtest-a"); A1 = r.json()
    check("a new school: the first teacher becomes its admin and gets a join code", r.status_code == 200 and A1["role"] == "school_admin" and len(A1.get("join_code") or "") == 6 and A1.get("token"), r.text[:100])
    check("a weak password is refused", reg("w1", "123456", "authtest-w").status_code == 400)
    r = reg("w2", "482615"[:4], "authtest-w")
    check("a 4-digit password can no longer be chosen: refused, and the message says 6 to 12 letters or digits", r.status_code == 400 and "6 to 12" in r.text, r.text[:140])
    check("the same phone number twice is refused", reg("a1", "482615", "authtest-a").status_code == 409)
    check("a teacher joining that school WITHOUT the code is refused", reg("a2", "593715", "authtest-a").status_code == 403)
    check("...with a WRONG code is refused", reg("a2", "593715", "authtest-a", join="WRONG1").status_code == 403)
    r = reg("a2", "593715", "authtest-a", join=A1["join_code"].lower()); A2 = r.json()
    check("...with the right code (any case) is accepted as a teacher", r.status_code == 200 and A2["role"] == "teacher", r.text[:100])
    B1 = reg("b1", "604815", "authtest-b").json()

    print("1a. the default: nobody can register themselves")
    get_settings().self_registration = False
    r = reg("c9", "482615", "authtest-c9")
    check("with self-registration off (the default) the route answers 403, registration_closed, and says who makes accounts", r.status_code == 403 and code(r) == "registration_closed" and "school leader" in r.text, r.text[:160])
    check("...and nothing was created", not sql("SELECT 1 FROM schools WHERE school_code = 'AUTHTEST-C9'", fetch=True) and not sql("SELECT 1 FROM teachers WHERE phone_hash = 'hash_authtest_c9'", fetch=True))
    get_settings().self_registration = True
    check("the setting is OFF unless someone turns it on", type(get_settings()).model_fields["self_registration"].default is False)

    print("1b. consent: a NEW school needs the school's confirmation (kept with its exact wording); joining one does not")
    post_new = lambda phone, school, **extra: c.post("/api/auth/register", json={"phone_hash": f"hash_authtest_{phone}", "pin": "739215", "school_code": school, "enrolled_grades": ["grade_1"], **extra})
    r = post_new("c0", "authtest-c")
    check("a new school WITHOUT the confirmation is refused (400, consent_required), with a message in Hindi as well", r.status_code == 400 and code(r) == "consent_required" and "सहमति" in r.text, r.text[:140])
    check("...and nothing was created: no school and no teacher", not sql("SELECT 1 FROM schools WHERE school_code = 'AUTHTEST-C'", fetch=True) and not sql("SELECT 1 FROM teachers WHERE phone_hash = 'hash_authtest_c0'", fetch=True))
    r = post_new("c0", "authtest-c", consent_version="v0")
    check("a confirmation of an OLD wording is refused too", r.status_code == 400 and code(r) == "consent_required", r.text[:120])
    r = post_new("c1", "authtest-c", consent_version="v1"); C1 = r.json()
    check("the current wording creates the school, with its admin", r.status_code == 200 and C1["role"] == "school_admin" and C1.get("join_code"), r.text[:140])
    rows = sql("SELECT version, statement, attested_by FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'AUTHTEST-C')", fetch=True)
    check("ONE confirmation is kept: its version, who gave it, and the exact wording in English AND Hindi (the server's own, not text from the browser)",
          len(rows) == 1 and rows[0]["version"] == "v1" and rows[0]["attested_by"] is not None and "Children’s names are never sent to the AI." in rows[0]["statement"] and "अनुमति" in rows[0]["statement"], [dict(x) for x in rows][:1])
    r = c.post("/api/auth/register", json={"phone_hash": "hash_authtest_c2", "pin": "739215", "school_code": "authtest-c", "enrolled_grades": ["grade_1"], "join_code": C1["join_code"]})
    check("a teacher JOINING that school with its join code needs no confirmation: the school gave it when it was created", r.status_code == 200 and r.json()["role"] == "teacher", r.text[:120])
    C2 = r.json()
    r = c.get("/api/admin/school", headers=H(C1["token"])); sch = r.json()
    check("the admin's school screen shows the confirmation: version, the date and only the END of the phone number", r.status_code == 200 and sch["consent"]["version"] == "v1" and sch["consent"]["by"].startswith("••••") and sch["consent"]["attested_at"], r.text[:200])
    check("...and the exact wording to read (both languages), so a school created earlier can confirm it", sch["consent_text"]["version"] == "v1" and "classwork" in sch["consent_text"]["en"] and "कक्षा-कार्य" in sch["consent_text"]["hi"])
    sql("DELETE FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'AUTHTEST-A')")          # school A becomes one registered before this existed
    r = c.get("/api/admin/school", headers=H(A1["token"]))
    check("a school registered BEFORE this existed (simulated: its record removed) shows 'nothing recorded' (None), not an error", r.status_code == 200 and r.json()["consent"] is None, r.text[:160])
    check("the leader of that school is told to confirm at the next sign-in (consent_needed), and a teacher of the school never is", login("a1", "482615").json()["consent_needed"] is True and login("a2", "593715").json()["consent_needed"] is False)
    r = c.post("/api/admin/school/consent", headers=H(A1["token"]), json={"version": "v0"})
    check("an admin confirming the OLD wording is refused (409, consent_stale)", r.status_code == 409 and code(r) == "consent_stale", r.text[:120])
    r = c.post("/api/admin/school/consent", headers=H(A1["token"]), json={"version": "v1"})
    check("an admin confirms for a school that has none: recorded, and her school screen now shows it", r.status_code == 200 and r.json()["consent"]["version"] == "v1" and c.get("/api/admin/school", headers=H(A1["token"])).json()["consent"] is not None, r.text[:160])
    check("...and once she has confirmed, she is not asked again", login("a1", "482615").json()["consent_needed"] is False)
    r = c.post("/api/admin/school/consent", headers=H(C1["token"]), json={"version": "v1"})
    check("confirming again adds a second row and the LATEST counts (the first is kept: it shows what was agreed, and when)", r.status_code == 200 and sql("SELECT count(*) AS n FROM school_consents WHERE school_id = (SELECT id FROM schools WHERE school_code = 'AUTHTEST-C')", fetch=True)[0]["n"] == 2)
    r = c.post("/api/admin/school/consent", headers=H(C2["token"]), json={"version": "v1"})
    check("an ordinary teacher cannot confirm for the school (403, not_admin)", r.status_code == 403 and code(r) == "not_admin", r.text[:120])
    check("...and nobody without a session can (401)", c.post("/api/admin/school/consent", json={"version": "v1"}).status_code == 401)

    print("2. login")
    r = login("a1", "482615"); check("the right password signs in and returns a token", r.status_code == 200 and r.json()["token"])
    w = login("a1", "9999"); u = login("nobody", "9999")
    check("a wrong PIN and an unknown phone give the SAME answer (nothing reveals which numbers exist)", w.status_code == u.status_code == 401 and w.json() == u.json(), (w.json(), u.json()))
    sql("INSERT INTO teachers (school_id, phone_hash, enrolled_grades) SELECT id, 'hash_authtest_np', ARRAY['grade_1'] FROM schools WHERE school_code = 'AUTHTEST-A'")
    r = login("np", "482615"); check("an account with no PIN cannot sign in and says why", r.status_code == 403 and code(r) == "pin_not_set")

    print("2b. employee codes")
    r = c.post("/api/auth/register", json={"phone_hash": "zzt101", "pin": "k7m4qx", "school_code": "authtest-a", "enrolled_grades": ["grade_1"], "join_code": A1["join_code"]})
    check("an account is made with an employee code, which is stored in capitals", r.status_code == 200 and sql("SELECT 1 FROM teachers WHERE phone_hash = 'ZZT101'", fetch=True) and r.json()["employee_code"] == "ZZT101", r.text[:140])
    ec = lambda code_, pw: c.post("/api/auth/login", json={"employee_code": code_, "pin": pw})
    check("it signs in with the code in capitals, in small letters, or with spaces around it, and the profile carries the code", all(ec(x, "k7m4qx").status_code == 200 and ec(x, "k7m4qx").json()["employee_code"] == "ZZT101" for x in ("ZZT101", "zzt101", " ZzT101 ")))
    w, u = ec("ZZT101", "wrong1"), ec("ZZT999", "wrong1")
    check("a wrong password and an unknown code give the SAME answer, which names the code and the password (nothing reveals which codes exist)", w.status_code == u.status_code == 401 and w.json() == u.json() and "employee code or password" in w.text, (w.json(), u.json()))
    check("a code that is not six letters or digits is just 'not right' (401), never an error page", all(ec(x, "k7m4qx").status_code == 401 for x in ("ZZT10", "ZZT1011", "ZZ-101", "")))
    check("a sign-in with neither a code nor a phone name is refused (401)", c.post("/api/auth/login", json={"pin": "482615"}).status_code == 401)
    rows_ = c.get("/api/admin/teachers", headers=H(tA1_ := login("a1", "482615").json()["token"])).json().get("teachers", [])
    check("the leader's list shows that account by its employee code", "ZZT101" in {t["code"] for t in rows_}, [t["code"] for t in rows_])

    print("3. lockout")
    for _ in range(4):
        login("a2", "0001")
    r = login("a2", "0001"); check("the 5th wrong PIN locks the account (429)", r.status_code == 429 and code(r) == "locked")
    check("while locked even the RIGHT PIN is refused", login("a2", "593715").status_code == 429)
    r = c.post(f"/api/admin/teachers/{A2['teacher_id']}/unlock", headers=H(A1["token"])); check("the school admin unlocks it", r.status_code == 200)
    check("then the right PIN works", login("a2", "593715").status_code == 200)
    for _ in range(5):
        login("a2", "0001")
    sql("UPDATE teachers SET locked_until = now() - interval '1 minute' WHERE phone_hash = 'hash_authtest_a2'")
    check("a lock expires by itself after 15 minutes", login("a2", "593715").status_code == 200)

    tA1, tA2, tB1 = A1["token"], login("a2", "593715").json()["token"], B1["token"]
    ida1, ida2, idb1 = A1["teacher_id"], A2["teacher_id"], B1["teacher_id"]
    print("4. every kind of route needs the token, and the RIGHT teacher's token")
    check("no token: 401 (path route)", c.get(f"/api/plan/groups/{ida1}/numeracy").status_code == 401)
    check("own token: 200", c.get(f"/api/plan/groups/{ida1}/numeracy", headers=H(tA1)).status_code == 200)
    r = c.get(f"/api/plan/groups/{ida1}/numeracy", headers=H(tA2)); check("another teacher's token on my id: 403 (path route)", r.status_code == 403 and code(r) == "not_yours")
    r = c.post(f"/api/review/observed?teacher_id={ida1}", json={"session_date": "2026-10-19", "items": []}, headers=H(tA2)); check("another teacher's token (query route): 403", r.status_code == 403, r.status_code)
    r = c.post("/api/review/analyse-photos", data={"teacher_id": ida1, "session_date": "2026-10-19", "domain_id": "numeracy", "competency_id": "N2.3.2", "worksheet_level": "progressor"},
               files=[("photos", ("p.jpg", b"x", "image/jpeg"))], headers=H(tA2)); check("another teacher's token (form route, photo upload): 403", r.status_code == 403, r.status_code)
    r = c.post("/api/register/preview", data={"teacher_id": ida1}, files={"file": ("r.csv", b"grade,roll_number\n1,1\n", "text/csv")}, headers=H(tA2)); check("another teacher's token (form route, register preview): 403", r.status_code == 403)
    r = c.post("/api/register/commit", json={"teacher_id": ida1, "rows": []}, headers=H(tA2)); check("another teacher's token (body route, register commit): 403", r.status_code == 403)
    check("no token on a form route: 401", c.post("/api/register/preview", data={"teacher_id": ida1}, files={"file": ("r.csv", b"x", "text/csv")}).status_code == 401)
    check("public reference data needs no token", c.get("/api/plan/competencies/numeracy").status_code == 200 and c.get("/api/register/template").status_code == 200 and c.get("/health").status_code == 200)
    check("the old unauthenticated 'login with only a phone' is gone", c.post("/api/auth/login", json={"phone_hash": "hash_authtest_a1"}).status_code == 422)

    print("5. tokens cannot be forged or reused")
    body, sig = tA1.split(".")
    r = c.get(f"/api/plan/groups/{ida1}/numeracy", headers=H(a._b64(b'{"tid":"%s","role":"school_admin","pv":0,"exp":9999999999}' % ida1.encode()) + "." + sig)); check("a forged payload is refused", r.status_code == 401)
    r = c.get(f"/api/plan/groups/{ida1}/numeracy", headers=H(a.make_token({"tid": ida1, "pv": 0}, hours=-1))); check("an expired token is refused", r.status_code == 401 and code(r) == "expired")

    print("6. changing a PIN")
    r = c.post("/api/auth/change-pin", json={"current_pin": "0000", "new_pin": "847215"}, headers=H(tA2)); check("a wrong current PIN is refused", r.status_code == 401)
    r = c.post("/api/auth/change-pin", json={"current_pin": "593715", "new_pin": "1234"}, headers=H(tA2)); check("a weak new password is refused", r.status_code == 400)
    r = c.post("/api/auth/change-pin", json={"current_pin": "593715", "new_pin": "8472"}, headers=H(tA2)); check("a new password of 4 digits is refused: it must be 6 to 12 letters or digits", r.status_code == 400 and "6 to 12" in r.text)
    r = c.post("/api/auth/change-pin", json={"current_pin": "593715", "new_pin": "593715"}, headers=H(tA2)); check("the same PIN again is refused", r.status_code == 400)
    r = c.post("/api/auth/change-pin", json={"current_pin": "593715", "new_pin": "847215"}, headers=H(tA2)); tA2n = r.json().get("token")
    check("a valid change returns a fresh session", r.status_code == 200 and tA2n)
    check("the OLD session now stops working (401)", c.get(f"/api/plan/groups/{ida2}/numeracy", headers=H(tA2)).status_code == 401)
    check("the new session works", c.get(f"/api/plan/groups/{ida2}/numeracy", headers=H(tA2n)).status_code == 200)
    check("the old PIN no longer signs in, the new one does", login("a2", "593715").status_code == 401 and login("a2", "847215").status_code == 200)
    tA2 = tA2n

    print("7. the school admin")
    r = c.get("/api/admin/teachers", headers=H(tA1)); rows = r.json().get("teachers", [])
    check("the admin lists their school's accounts (4)", r.status_code == 200 and len(rows) == 4, len(rows))
    check("...showing each account by its employee code (an old account: only the end of its phone number) and no child data", all(t["code"] and "phone_hash" not in t and "phone_end" not in t and "name" not in t and "roll_number" not in t for t in rows))
    r = c.get("/api/admin/teachers", headers=H(tA2)); check("an ordinary teacher cannot use admin routes (403)", r.status_code == 403 and code(r) == "not_admin")
    check("another school's admin sees only their own school", len(c.get("/api/admin/teachers", headers=H(tB1)).json()["teachers"]) == 1)
    r = c.post(f"/api/admin/teachers/{ida2}/reset-pin", headers=H(tB1)); check("...and cannot reset a teacher of ANOTHER school (404)", r.status_code == 404)
    r = c.post(f"/api/admin/teachers/{ida1}/reset-pin", headers=H(tA1)); check("an admin cannot reset their own PIN this way (400)", r.status_code == 400)
    r = c.post(f"/api/admin/teachers/{ida2}/reset-pin", headers=H(tA1)); temp = r.json().get("temporary_pin")
    check("the admin resets a teacher's PIN: a 6-digit temporary PIN, shown once", r.status_code == 200 and temp and len(temp) == 6)
    check("the teacher's earlier session ends", c.get(f"/api/plan/groups/{ida2}/numeracy", headers=H(tA2)).status_code == 401)
    check("the old PIN no longer works", login("a2", "847215").status_code == 401)
    r = login("a2", temp); tmp = r.json(); check("the temporary PIN signs in, flagged must_change_pin", r.status_code == 200 and tmp["must_change_pin"] is True)
    r = c.get(f"/api/plan/groups/{ida2}/numeracy", headers=H(tmp["token"])); check("...but it opens nothing else (403 pin_change_required)", r.status_code == 403 and code(r) == "pin_change_required")
    check("...except who-am-I", c.get("/api/auth/me", headers=H(tmp["token"])).status_code == 200)
    r = c.post("/api/auth/change-pin", json={"current_pin": temp, "new_pin": "739115"}, headers=H(tmp["token"])); tfin = r.json().get("token")
    check("choosing a new PIN completes the reset", r.status_code == 200 and r.json()["must_change_pin"] is False)
    check("and now the class opens", c.get(f"/api/plan/groups/{ida2}/numeracy", headers=H(tfin)).status_code == 200)
    sql("UPDATE teachers SET pin_fixed = TRUE WHERE phone_hash = 'hash_authtest_a2'")
    r = c.post("/api/auth/change-pin", json={"current_pin": "739115", "new_pin": "615415"}, headers=H(tfin)); check("a shared demo account (pin_fixed) cannot change its PIN", r.status_code == 403 and code(r) == "pin_fixed")
    r = c.post(f"/api/admin/teachers/{ida2}/reset-pin", headers=H(tA1)); check("...nor can an admin reset it", r.status_code == 403 and code(r) == "pin_fixed")
    sql("UPDATE teachers SET pin_fixed = FALSE WHERE phone_hash = 'hash_authtest_a2'")

    print("8. there is no join code any more")
    check("the route that rotated the join code is gone", c.post("/api/admin/school/join-code", headers=H(tA1)).status_code in (404, 405))
    r = c.get("/api/admin/school", headers=H(tA1)); check("the leader's school screen has no join code", r.status_code == 200 and "join_code" not in r.json() and r.json()["school_code"] == "AUTHTEST-A", r.text[:140])

    print("9. the audit trail")
    r = c.get(f"/api/progress/export/class/{ida1}", headers=H(tA1)); check("exporting a class report (it has names) works for the owner", r.status_code == 200)
    ev = {x["event"] for x in sql("SELECT event FROM auth_events WHERE teacher_id IN (SELECT id FROM teachers WHERE phone_hash LIKE 'hash_authtest_%')", fetch=True)}
    want = {"registered", "login_ok", "login_failed", "locked", "unlocked", "pin_changed", "pin_reset_by_admin", "class_report_export", "consent_recorded"}
    check("every sign-in event is recorded", want <= ev, want - ev)
clean()
if failures:
    print(f"\nFAILED ({len(failures)})")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("\nOK: sign-in, lockout, session tokens on every kind of route, password change, employee codes and the leader's reset all behave")
