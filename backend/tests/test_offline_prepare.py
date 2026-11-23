"""
Offline plans, step 1 (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md): the quick plan from the block library (source "library": no AI call), and the
plans PREPARED for the phone (POST /api/offline/prepare: built by the server's own pipeline, never stored). The key promise: a prepared plan is
exactly the plan the server stores for the same choice. A scratch class; the AI is a fake that fails the test if it is ever called.

    python backend/tests/test_offline_prepare.py --env-file backend/.env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import asyncio
import json
import os
import sys
from datetime import date, timedelta

os.environ.setdefault("AUTH_MODE", "off")
import _scratch
os.environ["LIBRARY_FALLBACK"] = "1"
os.environ.pop("PLAN_SOURCE", None)
import anthropic
from fastapi.testclient import TestClient
from app.main import app
from app.services import library_assembler as la

failures = []
AI_CALLS = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


class NoAI:
    """Any AI call is a failure: a library plan must never reach the model."""
    def __init__(self, *a, **k):
        self.messages = self

    async def create(self, **kw):
        AI_CALLS.append(kw.get("model"))
        raise RuntimeError("the AI was called")


anthropic.AsyncAnthropic = NoAI
D0 = date(2031, 5, 5)


def teacher_facing(p: dict) -> dict:
    """What the teacher sees and what the review uses (the plan, its groups and skills): the comparison of 'the same plan'."""
    keep = {k: v for k, v in p["plan"].items() if k not in ("served_from",)}
    return {"plan": keep, "groups": p["groups"], "selected": p["selected_competency_id"]}


async def main():
    db = await _scratch.connect()
    levels = {r: ("beginner" if r <= 8 else ("progressor" if r <= 20 else "proficient"),) * 2 for r in range(1, 31)}
    tid, school = await _scratch.make_class(db, levels, grade="grade_2")
    try:
        with TestClient(app) as c:
            print("the quick plan (source 'library'): no AI call, stored as the day's plan")
            r = c.post(f"/api/plan/generate?teacher_id={tid}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(D0),
                                                                    "session_minutes": 45, "source": "library"})
            body = r.json() if r.status_code == 200 else {}
            check("served from the library, with the teacher's 45 minutes", r.status_code == 200 and body.get("served_from") == "library"
                  and body["plan"]["session_minutes"] == 45, r.text[:200])
            check("no AI call was made", AI_CALLS == [], AI_CALLS)
            stored = await db.fetchval("SELECT claude_model FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'numeracy'", tid, D0)
            check("it is stored as the day's plan, marked 'library'", stored == "library", stored)
            r2 = c.post(f"/api/plan/generate?teacher_id={tid}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(D0),
                                                                     "session_minutes": 45, "source": "library"})
            check("a second quick plan for the same day is refused like any plan (409 plan_exists) unless the teacher confirms", r2.status_code == 409
                  and r2.json()["detail"]["code"] == "plan_exists")
            real = la.assemble
            la.assemble = lambda *a, **k: None
            try:
                r3 = c.post(f"/api/plan/generate?teacher_id={tid}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(D0 + timedelta(days=1)),
                                                                         "session_minutes": 60, "source": "library"})
            finally:
                la.assemble = real
            check("when the library cannot build it: 409 library_unavailable with a Hindi message (never a recorded plan, never an AI message)",
                  r3.status_code == 409 and r3.json()["detail"]["code"] == "library_unavailable" and "तैयार हिस्सों" in r3.json()["detail"]["message"], r3.text[:200])
            check("...and nothing was stored for that day", not await db.fetchval("SELECT 1 FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", tid, D0 + timedelta(days=1)))

            print("\nprepared plans (POST /api/offline/prepare): built by the server's pipeline, never stored")
            items = [{"key": f"N2.3.2|{m}|{d}", "competency_id": "N2.3.2", "plan_date": str(D0 + timedelta(days=d)), "session_minutes": m, "reteach_groups": []}
                     for d in (2, 3) for m in (45, 60, 90)]
            items.append({"key": "L2.5.1|60|2", "competency_id": "L2.5.1", "plan_date": str(D0 + timedelta(days=2)), "session_minutes": 60, "reteach_groups": []})
            items.append({"key": "bad", "competency_id": "N9.9.9", "plan_date": str(D0 + timedelta(days=2)), "session_minutes": 60})
            num = [i for i in items if i["competency_id"] != "L2.5.1"]
            r = c.post(f"/api/offline/prepare?teacher_id={tid}", json={"domain_id": "numeracy", "items": num})
            out = r.json() if r.status_code == 200 else {}
            got = {p["key"]: p for p in out.get("plans", [])}
            check("every choice comes back under its own key, the library's version with them", r.status_code == 200 and set(got) == {i["key"] for i in num}
                  and isinstance(out.get("library_version"), str) and len(out["library_version"]) == 12, r.text[:200])
            check("each is a library plan laid out for its length", all(got[k]["ok"] and got[k]["result"]["served_from"] == "library"
                                                                      and got[k]["result"]["plan"]["session_minutes"] == int(k.split("|")[1]) for k in got if k != "bad"))
            check("a choice the server cannot build is reported, not fatal", got.get("bad", {}).get("ok") is False, got.get("bad"))
            check("no AI call", AI_CALLS == [], AI_CALLS)
            n = await db.fetchval("SELECT count(*) FROM daily_plans WHERE teacher_id = $1 AND plan_date >= $2", tid, D0 + timedelta(days=2))
            check("NOTHING was stored: prepared plans are not the teacher's plans", n == 0, n)
            r = c.post(f"/api/offline/prepare?teacher_id={tid}", json={"domain_id": "numeracy", "items": num})
            again = {p["key"]: p for p in r.json()["plans"]}
            check("the same choices give the same plans (nothing random)", all(teacher_facing(again[k]["result"]) == teacher_facing(got[k]["result"]) for k in got if got[k]["ok"]))

            print("\nthe promise: a prepared plan IS the plan the server stores for the same choice")
            k = "N2.3.2|60|3"
            it = next(i for i in num if i["key"] == k)
            r = c.post(f"/api/plan/generate?teacher_id={tid}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": it["plan_date"],
                                                                    "session_minutes": 60, "reteach_groups": [], "source": "library"})
            check("prepared and stored are the same plan, groups and skills", r.status_code == 200 and teacher_facing(r.json()) == teacher_facing(got[k]["result"]),
                  [x for x in got[k]["result"]["plan"] if got[k]["result"]["plan"].get(x) != r.json()["plan"].get(x)] if r.status_code == 200 else r.text[:200])
            lit = c.post(f"/api/offline/prepare?teacher_id={tid}", json={"domain_id": "r1_literacy", "items": [items[-2]]}).json()["plans"][0]
            r = c.post(f"/api/plan/generate?teacher_id={tid}", json={"competency_id": "L2.5.1", "domain_id": "r1_literacy", "plan_date": items[-2]["plan_date"],
                                                                    "session_minutes": 60, "reteach_groups": [], "source": "library"})
            check("...also for literacy, where the server swaps in bank passages", lit["ok"] and r.status_code == 200 and teacher_facing(r.json()) == teacher_facing(lit["result"]))

            print("\nupload (step 4): a plan used offline, sent when the phone is back online")
            used = D0 + timedelta(days=9)
            prep = got["N2.3.2|60|3"]["result"]
            sent = dict(prep)
            sent["groups"] = [dict(g, roll_numbers=list(g["roll_numbers"]) + ([999] if g["label"] == "beginner" else [])) for g in prep["groups"]]
            body = {"client_id": "phone-abc-1", "plan_date": str(used), "domain_id": "numeracy", "competency_id": "N2.3.2",
                    "prepared_for": prep["plan_date"], "made_at": "2031-05-14T03:00:00Z", "result": sent}
            r = c.post(f"/api/plan/offline?teacher_id={tid}", json=body)
            check("stored", r.status_code == 200 and r.json() == {"status": "stored"}, r.text[:200])
            row = await db.fetchrow("SELECT plan_content, groups_snapshot, claude_model FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", tid, used)
            pc, snap = json.loads(row["plan_content"]), json.loads(row["groups_snapshot"])
            check("as the day's plan, marked made offline, with its client id and the day it was prepared for", row["claude_model"] == "library_offline"
                  and pc["served_from"] == "library_offline" and pc["offline"]["client_id"] == "phone-abc-1" and pc["offline"]["prepared_for"] == prep["plan_date"])
            check("the lesson itself is the prepared one, unchanged", pc["rotation_schedule"] == prep["plan"]["rotation_schedule"] and pc["worksheets"] == prep["plan"]["worksheets"])
            check("the groups as the phone planned them, limited to this teacher's own children (a roll 999 is dropped)",
                  999 not in snap["beginner"]["rolls"] and snap["beginner"]["rolls"] == sorted(prep["groups"][0]["roll_numbers"]) and snap["progressor"]["target"] == "N2.3.2", snap.get("beginner"))
            from app.services.sampling import sample_for_group
            want = sample_for_group(snap["progressor"]["rolls"], used, "progressor", "N2.3.2")["rolls"]
            check("the photo sample is worked out for the day the plan was USED (not the day it was prepared for)",
                  pc["review_prompts"]["photo_sample_rolls"]["progressor"] == want, (pc["review_prompts"]["photo_sample_rolls"]["progressor"], want))
            r = c.post(f"/api/plan/offline?teacher_id={tid}", json=body)
            n_rows = await db.fetchval("SELECT count(*) FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", tid, used)
            check("the same client id again (a retry on a flaky network): 'duplicate', still ONE plan", r.status_code == 200 and r.json() == {"status": "duplicate"} and n_rows == 1)
            r = c.post(f"/api/plan/offline?teacher_id={tid}", json=dict(body, client_id="phone-other-2"))
            check("another plan for that day (another phone, or one made online meanwhile): the stored one is kept, 409 plan_exists with a Hindi message",
                  r.status_code == 409 and r.json()["detail"]["code"] == "plan_exists" and "रखी गई" in r.json()["detail"]["message"]
                  and json.loads(await db.fetchval("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", tid, used))["offline"]["client_id"] == "phone-abc-1")
            g = c.get(f"/api/plan/{tid}/{used}/numeracy")
            check("afterwards it is read back like any plan (the Teach and Review screens use this)", g.status_code == 200 and g.json()["plan"]["served_from"] == "library_offline"
                  and [x["label"] for x in g.json()["groups"]] == ["beginner", "progressor", "proficient"])
            bad = c.post(f"/api/plan/offline?teacher_id={tid}", json=dict(body, client_id="phone-bad-3", plan_date=str(used + timedelta(days=1)), result={"plan": {"anchor": {}}}))
            check("something that is not a plan is refused (400), nothing stored", bad.status_code == 400 and bad.json()["detail"]["code"] == "bad_offline_plan"
                  and not await db.fetchval("SELECT 1 FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", tid, used + timedelta(days=1)))
            check("no AI call in any of this", AI_CALLS == [])

            print("\nlimits")
            r = c.post(f"/api/offline/prepare?teacher_id={tid}", json={"domain_id": "numeracy", "items": [num[0]] * 121})
            check("more than 120 plans in one request is refused (422)", r.status_code == 422)
            r = c.post(f"/api/offline/prepare?teacher_id={tid}", json={"domain_id": "maths", "items": [num[0]]})
            check("an unknown subject is refused (400)", r.status_code == 400)
    finally:
        await _scratch.remove_class(db, tid, school)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: quick plans and prepared plans come from the library with no AI call; a prepared plan is the plan the server would store, and is never stored itself")
