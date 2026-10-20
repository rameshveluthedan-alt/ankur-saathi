"""
The AI budget end to end, on a scratch school. Every call is metered, and every way a call can be stopped is checked: the teacher,
school and global daily caps, the reserve rule, an exhausted budget, a switched-off AI, expired credits, a shared demo account, and
the operator's batch mode. When a PLAN is stopped, a recorded plan for the same skill is served (and labelled); a PHOTO analysis
says why it cannot run. A paid reply that cannot be read is still counted.

    cd backend && AUTH_MODE=off python tests/test_ai_budget_flow.py --env-file .env

Safe against a database that has real usage: it only ever reads totals, sets its caps RELATIVE to them, and deletes only its own rows.
"""
import asyncio
import contextlib
import copy
import io
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
import _scratch
import anthropic
from PIL import Image
from fastapi.testclient import TestClient
from app.core.config import get_settings
from app.main import app
from app.services import ai_budget as b, plan_service, register_service as rs, review_service

S = get_settings()
KEEP = {k: getattr(S, k) for k in type(S).model_fields if k.startswith("ai_")}
failures, calls, mode = [], {"plan": 0, "vision": 0}, {"plan": "ok", "vision": "ok"}
SAMPLE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "db", "seeds", "sample_plans", "N2.2.1.json"), encoding="utf-8"))
QUIET = lambda: contextlib.redirect_stdout(io.StringIO())


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


class FakeMessages:
    """Stands in for the AI. A vision call has a list as its message content; a plan call has text."""
    async def create(self, **kw):
        vision = isinstance(kw["messages"][0]["content"], list)
        kind = "vision" if vision else "plan"
        calls[kind] += 1
        usage = SimpleNamespace(input_tokens=6000, output_tokens=9000) if not vision else SimpleNamespace(input_tokens=4000, output_tokens=3000)
        if mode[kind] == "junk":
            text = "this is not JSON"
        elif vision:
            text = json.dumps([{"roll_number": 1, "roll_number_confidence": "high", "problems": [{"number": 1, "extracted_answer": "25", "correct_answer": "25", "is_correct": True, "confidence": "high"}],
                                "summary": {"needs_verification": [], "detected_misconceptions": []}}])
        else:
            text = json.dumps(SAMPLE, ensure_ascii=False)
        blocks = [] if mode[kind] == "notext" else [SimpleNamespace(type="text", text=text)]
        return SimpleNamespace(content=blocks, stop_reason="end_turn", usage=usage)


class FakeClient:
    def __init__(self, **kw):
        self.messages = FakeMessages()


def reset_settings(**over):
    for k, v in KEEP.items():
        setattr(S, k, v)
    S.ai_price_input_per_mtok, S.ai_price_output_per_mtok = 2.0, 10.0
    for k, v in over.items():
        setattr(S, k, v)
    b.NOW_OVERRIDE = None
    b.operator_mode(False)


async def main():
    db = await _scratch.connect()
    levels = {r: ("beginner", "progressor", "proficient")[r % 3] for r in range(1, 19)}
    A, school = await _scratch.make_class(db, {r: (l, l) for r, l in levels.items()}, grade="grade_2")
    code = (await db.fetchval("SELECT school_code FROM schools WHERE school_code = $1", school))
    bt = await rs.register_teacher(db, f"hash_tst_b_{school[-6:].lower()}", code, ["grade_2"], enforce_join=False)
    await rs.commit_register(db, bt["teacher_id"], [{"row": i + 2, "grade": "grade_2", "roll": str(r), "name": "", "numeracy": l, "literacy": l} for i, (r, l) in enumerate(levels.items())], "b.csv")
    B = bt["teacher_id"]
    real_client = anthropic.AsyncAnthropic
    anthropic.AsyncAnthropic = FakeClient
    try:
        async def gen(teacher, day, comp="N2.2.1"):
            with QUIET():
                return await plan_service.generate_dainik_yojana(db, teacher, comp, "numeracy", day)

        async def reason(teacher, kind="plan"):
            try:
                await b.check(db, teacher, kind)
                return None
            except b.AICapReached as e:
                return e.reason

        since = lambda: b.day_start()
        spent = lambda teacher: b._spent(db, "teacher_id = $1", teacher)
        D = lambda n: date(2031, 10, n)

        print("1. every paid call is metered")
        reset_settings()
        r1 = await gen(A, D(1))
        rows = await db.fetch("SELECT kind, input_tokens, output_tokens FROM ai_usage WHERE teacher_id = $1", A)
        check("a plan is served from the AI and one call is made", r1["served_from"] == "ai" and calls["plan"] == 1)
        check("its tokens are recorded (6,000 in, 9,000 out)", [(r["kind"], r["input_tokens"], r["output_tokens"]) for r in rows][:1] == [("plan", 6000, 9000)], rows)
        check("the cost follows from the tokens and the current prices ($0.102)", abs(await spent(A) - 0.102) < 0.001, await spent(A))
        S.ai_price_output_per_mtok = 20.0
        check("correcting a price re-prices everything already recorded", abs(await spent(A) - (0.012 + 0.18)) < 0.001)
        reset_settings()

        print("2. a teacher's daily cap, and the recorded-plan fallback")
        S.ai_cap_teacher_daily_usd = 0.15
        check("under the cap: still the AI", (await gen(A, D(2)))["served_from"] == "ai" and calls["plan"] == 2)
        before = calls["plan"]
        r3 = await gen(A, D(3))
        check("over the cap: the skill's RECORDED plan is served, with NO call to the AI", r3["served_from"] == "sample" and calls["plan"] == before)
        check("...and it is a full plan for this class (worksheets, groups, passages)", bool(r3["plan"].get("worksheets")) and len(r3["groups"]) == 3)
        stored = await db.fetchrow("SELECT claude_model, plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", A, D(3))
        pc = json.loads(stored["plan_content"]) if isinstance(stored["plan_content"], str) else stored["plan_content"]
        check("it is stored as a sample, so the screen keeps saying so", stored["claude_model"] == "sample-replay" and pc["served_from"] == "sample")
        check("the reason a check gives is the teacher's cap", await reason(A) == "teacher_daily")
        try:
            await gen(A, D(4), comp="N2.3.1")
            check("a skill with NO recorded plan cannot be faked: it is refused", False)
        except b.AICapReached as e:
            check("a skill with NO recorded plan cannot be faked: it is refused with the reason", e.reason == "teacher_daily")

        print("3. a shared demo account has a higher cap")
        reset_settings(ai_cap_teacher_daily_usd=0.15, ai_cap_shared_demo_daily_usd=5.0)
        await db.execute("UPDATE teachers SET pin_fixed = TRUE WHERE id = $1", A)
        check("the same spending is allowed for a shared demo account", await reason(A) is None)
        await db.execute("UPDATE teachers SET pin_fixed = FALSE WHERE id = $1", A)
        check("...and refused for an ordinary account", await reason(A) == "teacher_daily")

        print("4. the school cap and the global cap")
        reset_settings(ai_cap_teacher_daily_usd=1000, ai_cap_school_daily_usd=0.999 * await b._spent(db, "school_id = (SELECT school_id FROM teachers WHERE id = $1) AND created_at >= $2", A, since()))
        check("another teacher of the SAME school is stopped by the school's cap", await reason(B) == "school_daily")
        reset_settings(ai_cap_teacher_daily_usd=1000, ai_cap_school_daily_usd=1000, ai_cap_global_daily_usd=0.999 * await b._spent(db, "created_at >= $1", since()))
        check("everyone is stopped by the global daily cap (the kill switch)", await reason(B) == "global_daily" and await reason(A) == "global_daily")

        print("5. the reserve rule")
        metered = await b._spent(db)
        S_ = dict(ai_cap_teacher_daily_usd=1000, ai_cap_school_daily_usd=1000, ai_cap_global_daily_usd=1e6)
        tz = timezone(timedelta(hours=5, minutes=30))          # fixed offset: no time zone database is needed
        reset_settings(**S_, ai_allocation_usd=S.ai_spend_offset_usd + metered + S.ai_reserve_usd - 0.01)
        b.NOW_OVERRIDE = datetime(2026, 10, 25, 12, tzinfo=tz)
        check("before 1 Nov, development cannot spend into the reserve", await reason(B) == "reserve")
        b.NOW_OVERRIDE = datetime(2026, 11, 2, 12, tzinfo=tz)
        check("from 1 Nov the SAME state is allowed: the reserve is released", await reason(B) is None)
        reset_settings(**S_, ai_allocation_usd=S.ai_spend_offset_usd + metered)
        b.NOW_OVERRIDE = datetime(2026, 11, 2, 12, tzinfo=tz)
        check("a budget with nothing left is 'exhausted' after 1 Nov", await reason(B) == "exhausted")
        b.NOW_OVERRIDE = datetime(2026, 10, 25, 12, tzinfo=tz)
        check("...and before the reserve date", await reason(B) == "exhausted")

        print("6. switched off, expired, and the operator's batch mode")
        reset_settings(**S_, ai_enabled=False)
        check("AI_ENABLED=false stops every call", await reason(B) == "disabled")
        before = calls["plan"]
        check("...but a recorded plan is still served", (await gen(B, D(5)))["served_from"] == "sample" and calls["plan"] == before)
        reset_settings(**S_)
        b.NOW_OVERRIDE = datetime(2026, 11, 21, 12, tzinfo=tz)
        check("after the credits expire (20 Nov) no call is made", await reason(B) == "expired")
        reset_settings(ai_cap_teacher_daily_usd=0.0, ai_cap_school_daily_usd=0.0, ai_cap_global_daily_usd=0.0)
        check("with every daily cap at zero a normal call is stopped", await reason(B) == "global_daily")
        b.operator_mode(True)
        check("the operator's batch mode skips the DAILY caps", await reason(B) is None)
        S.ai_allocation_usd = S.ai_spend_offset_usd + await b._spent(db)
        check("...but never the total budget", await reason(B) == "exhausted")
        reset_settings()

        print("7. today's caps ignore yesterday")
        yesterday = datetime.now(tz) - timedelta(days=1)
        await db.execute("INSERT INTO ai_usage (teacher_id, school_id, kind, model, input_tokens, output_tokens, created_at) VALUES ($1, (SELECT school_id FROM teachers WHERE id = $1), 'plan', 'x', 2500000, 0, $2)", B, yesterday)
        check("a $5 spend yesterday is not counted against today", True)
        reset_settings(ai_cap_teacher_daily_usd=1.0, ai_cap_school_daily_usd=1000, ai_cap_global_daily_usd=1e6)
        check("so the teacher is still allowed today", await reason(B) is None)
        await db.execute("INSERT INTO ai_usage (teacher_id, school_id, kind, model, input_tokens, output_tokens) VALUES ($1, (SELECT school_id FROM teachers WHERE id = $1), 'plan', 'x', 600000, 0)", B)
        check("...until today's own spending reaches the cap", await reason(B) == "teacher_daily")

        print("8. a paid reply that cannot be read is still counted")
        reset_settings()
        n0 = await db.fetchval("SELECT count(*) FROM ai_usage WHERE teacher_id = $1 AND kind = 'plan'", A)
        mode["plan"] = "junk"
        try:
            await gen(A, D(6))
            check("a reply that is not JSON is an error", False)
        except Exception:
            check("a reply that is not JSON is an error", True)
        check("...and it was still metered (it cost money)", await db.fetchval("SELECT count(*) FROM ai_usage WHERE teacher_id = $1 AND kind = 'plan'", A) == n0 + 1)
        mode["plan"] = "ok"

        print("9. photo analysis: metered, capped, and refused honestly")
        plan = {"worksheets": {"progressor": {"required_count": 1, "problems": [{"number": 1, "problem_hi": "12 + 13", "answer": "25"}]}}}
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
                            VALUES ($1, $2, 'numeracy', 'N2.3.2', $3::jsonb, '{}'::jsonb, '{}'::jsonb)""", B, date.today(), json.dumps(plan))
        buf = io.BytesIO(); Image.new("RGB", (120, 90), "white").save(buf, "JPEG"); img = buf.getvalue()
        async def analyse():
            with QUIET():
                return await review_service.analyse_worksheet_photos(db, B, date.today(), "numeracy", "N2.3.2", "progressor", [img], None)
        reset_settings()
        await analyse()
        v = await db.fetch("SELECT input_tokens, output_tokens FROM ai_usage WHERE teacher_id = $1 AND kind = 'vision'", B)
        check("a photo analysis is metered (4,000 in, 3,000 out)", [(r["input_tokens"], r["output_tokens"]) for r in v] == [(4000, 3000)], v)
        mode["vision"] = "notext"
        try:
            await analyse()
        except Exception:
            pass
        check("a photo reply with no text is an error, and it was still counted", await db.fetchval("SELECT count(*) FROM ai_usage WHERE teacher_id = $1 AND kind = 'vision'", B) == 2)
        mode["vision"] = "ok"
        reset_settings(ai_cap_teacher_daily_usd=0.0)
        n_calls = calls["vision"]
        try:
            await analyse()
            check("over the cap, a photo analysis is refused", False)
        except b.AICapReached as e:
            check("over the cap, a photo analysis is refused, with the reason, and the AI is not called", e.reason in ("teacher_daily", "global_daily", "school_daily") and calls["vision"] == n_calls)

        print("10. what the API tells the app")
        reset_settings(ai_cap_teacher_daily_usd=0.0)
        with TestClient(app) as c:
            r = c.post(f"/api/plan/generate?teacher_id={B}", json={"competency_id": "N2.3.1", "domain_id": "numeracy", "plan_date": "2031-10-09"})
            d = r.json().get("detail", {})
            check("a skill with no recorded plan: HTTP 429 with a code the app can show", r.status_code == 429 and d.get("code") == "ai_cap" and d.get("message"), r.text[:120])
            check("...and it lists the skills that DO have a recorded plan", {"N2.2.1", "N2.3.2"} <= set(d.get("sample_skills", [])))
            r = c.post(f"/api/plan/generate?teacher_id={B}", json={"competency_id": "N2.2.1", "domain_id": "numeracy", "plan_date": "2031-10-10"})
            check("a skill WITH a recorded plan: served, labelled 'sample'", r.status_code == 200 and r.json().get("served_from") == "sample", r.text[:120])
            g = c.get(f"/api/plan/{B}/2031-10-10/numeracy")
            check("the cached plan keeps its label when the page reloads", g.status_code == 200 and g.json().get("served_from") == "sample")
    finally:
        anthropic.AsyncAnthropic = real_client
        reset_settings()
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        for t in (B,):
            await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", t)
            await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", t)
            await db.execute("DELETE FROM teachers WHERE id = $1", t)
        await _scratch.remove_class(db, A, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: every call is metered, every way of being stopped works, and a stopped plan falls back to a labelled recorded one")


if __name__ == "__main__":
    asyncio.run(main())
