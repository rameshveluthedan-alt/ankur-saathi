"""
Each group's skill for the day: what the app proposes from the teacher's decisions at the last review (Advance / Re-teach / Not sure), a teacher's choice of skill for a group, and the protection of those decisions.

    python tests/test_group_skills.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import io
import json
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]

failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def obj(v):
    return json.loads(v) if isinstance(v, str) else (v or {})


async def main():
    import _scratch
    import anthropic
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import group_skills as gs, plan_service
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    real_client = anthropic.AsyncAnthropic
    D = date.today() + timedelta(days=30)

    async def put_plan(day, targets, decisions, selected="N2.3.2", tid=None, rolls=None, content=None):
        snap = {l: {"count": len((rolls or {}).get(l, [])) or 1, "rolls": list((rolls or {}).get(l, [])), "target": t} for l, t in targets.items()}
        expl = {f"teacher_decision_{l}": d for l, d in decisions.items()}
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
                            VALUES ($1, $2, 'numeracy', $3, $6::jsonb, $4::jsonb, $5::jsonb)
                            ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET explainability = EXCLUDED.explainability, plan_content = EXCLUDED.plan_content,
                                   groups_snapshot = EXCLUDED.groups_snapshot, selected_competency_id = EXCLUDED.selected_competency_id""",
                         tid or teacher_id, day, selected, json.dumps(expl), json.dumps(snap), json.dumps(content or {}))

    t2 = school2 = None
    try:
        print("what the app proposes, from the teacher's decisions at the last review")
        none = await gs.propose(db, teacher_id, "numeracy", D)
        check("no earlier plan: no history, nothing proposed (the plan derives the skills as before)", none["has_history"] is False and none["groups"] == {})
        await put_plan(D - timedelta(days=1), {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"},
                       {"beginner": "advance", "progressor": "reteach", "proficient": "advance"})
        p = await gs.propose(db, teacher_id, "numeracy", D)
        g = p["groups"]
        check("it reads the last plan's date and each group's skill and decision", p["has_history"] and p["previous_date"] == str(D - timedelta(days=1)) and g["beginner"]["previous_target"]["id"] == "N2.3.1" and g["progressor"]["previous_decision"] == "reteach")
        check("Advance: the Beginners move from N2.3.1 to the skill that depends on it, N2.3.2", g["beginner"]["proposed"]["id"] == "N2.3.2" and g["beginner"]["reason"] == "advance")
        check("Re-teach: the Progressors stay on N2.3.2", g["progressor"]["proposed"]["id"] == "N2.3.2" and g["progressor"]["reason"] == "reteach")
        nxt = await gs.next_options(db, "N3.3.1")
        check("Advance for the Proficients: the graph's first skill after N3.3.1, with the alternatives listed so the teacher can choose another", nxt and g["proficient"]["proposed"]["id"] == nxt[0]["id"] and g["proficient"]["alternatives"][0]["id"] == nxt[0]["id"], (nxt[:1], g["proficient"]["proposed"]))
        check("names come with the proposal so the screen can show them", g["beginner"]["proposed"]["name_hi"] and g["beginner"]["previous_target"]["name_en"])

        await put_plan(D - timedelta(days=1), {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}, {"beginner": "not_sure", "progressor": "bogus"})
        p = (await gs.propose(db, teacher_id, "numeracy", D))["groups"]
        check("'Not sure' keeps the group on its skill, and a missing or unknown decision proposes nothing for that group", p["beginner"]["proposed"]["id"] == "N2.3.1" and p["beginner"]["reason"] == "not_sure" and p["progressor"]["proposed"] is None and p["progressor"]["reason"] == "no_decision" and p["proficient"]["proposed"] is None)
        leaf = await db.fetchval("""SELECT c.id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id WHERE s.domain_id = 'numeracy'
                                    AND NOT EXISTS (SELECT 1 FROM competency_prerequisites cp WHERE cp.prerequisite_id = c.id AND cp.prerequisite_type = 'hard') ORDER BY c.id LIMIT 1""")
        await put_plan(D - timedelta(days=1), {"beginner": leaf, "progressor": "N2.3.2", "proficient": "N3.3.1"}, {"beginner": "advance"})
        p = (await gs.propose(db, teacher_id, "numeracy", D))["groups"]["beginner"]
        check("Advance from a skill nothing depends on: the group stays on it, and the reason says why", p["proposed"]["id"] == leaf and p["reason"] == "advance_no_next" and p["alternatives"] == [], p)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await put_plan(D - timedelta(days=15), {"beginner": "N2.3.1"}, {"beginner": "advance"})
        check("a plan older than two weeks is not 'yesterday'", (await gs.propose(db, teacher_id, "numeracy", D))["has_history"] is False)
        await put_plan(D, {"beginner": "N2.3.1"}, {"beginner": "advance"})
        check("a plan for the SAME date is not 'yesterday' either", (await gs.propose(db, teacher_id, "numeracy", D))["has_history"] is False)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)

        print("\nthe app's own recommendation from the children's evidence (a third of those assessed, rounded up)")
        check("the rule: 6 assessed need 2, 7 need 3, 4 need 2, 9 need 3", [gs.recommend(a, 0)["needed"] for a in (6, 7, 4, 9)] == [2, 3, 2, 3])
        check("2 of 6 recommends a re-teach, 1 of 6 does not (so up to two thirds can still move on), and 2 of 4 does", gs.recommend(6, 2)["recommend"] and not gs.recommend(6, 1)["recommend"] and gs.recommend(4, 2)["recommend"] and not gs.recommend(4, 1)["recommend"])
        r3 = gs.recommend(3, 3)
        check("under 4 assessed is a very small group: the numbers are shown but nothing is recommended, even when every child made a mistake", r3["very_small"] and not r3["recommend"] and r3["assessed"] == 3 and r3["with_mistakes"] == 3)
        r0 = gs.recommend(0, 0)
        check("nobody assessed: nothing to say", not r0["recommend"] and not r0["very_small"] and r0["needed"] == 0)

        lv2 = {**{r: "beginner" for r in range(1, 5)}, **{r: "progressor" for r in range(5, 11)}, **{r: "proficient" for r in (11, 12)}}
        t2, school2 = await _scratch.make_class(db, {r: (lv, lv) for r, lv in lv2.items()}, grade="grade_2")
        kids2 = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", t2)}
        mis = {c: [r["id"] for r in await db.fetch("SELECT id FROM misconceptions WHERE competency_id = $1 ORDER BY id", c)] for c in ("N2.3.1", "N2.3.2", "N3.3.1", "N2.3.3")}
        prevday = D - timedelta(days=1)
        rolls2 = {"beginner": [1, 2, 3, 4], "progressor": [5, 6, 7, 8, 9, 10], "proficient": [11, 12]}
        tg2 = {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}

        async def ev(roll, comp, ids, day=None):
            await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date) "
                             "VALUES ($1, $2, $3, 'written_photo', $4, '{}'::jsonb, $5, $6)", kids2[roll], comp, t2, "not_achieved" if ids else "achieved", ids, day or prevday)

        async def prop2(decisions):
            await put_plan(prevday, tg2, decisions, tid=t2, rolls=rolls2)
            return (await gs.propose(db, t2, "numeracy", D))["groups"]
        for roll in range(5, 11):                                            # the Progressors: 6 assessed on N2.3.2, rolls 5 and 6 made the first mistake
            await ev(roll, "N2.3.2", [mis["N2.3.2"][0]] if roll in (5, 6) else [])
        for roll in range(1, 5):                                             # the Beginners: 4 assessed on N2.3.1, only roll 1 made a mistake
            await ev(roll, "N2.3.1", [mis["N2.3.1"][0]] if roll == 1 else [])
        for roll in (11, 12):                                                # the Proficients: only 2 assessed, both made a mistake
            await ev(roll, "N3.3.1", [mis["N3.3.1"][0]])
        gp = await prop2({})
        e = gp["progressor"]["evidence"]
        check("the Progressors: 2 of 6 assessed made a mistake, 2 are needed: a re-teach is recommended, with the children's rolls and the mistake named", e["assessed"] == 6 and e["with_mistakes"] == 2 and e["needed"] == 2 and e["recommend"] and e["rolls"] == [5, 6] and e["mistakes"][0]["misconception_id"] == mis["N2.3.2"][0] and e["mistakes"][0]["children"] == 2 and e["mistakes"][0]["name_hi"], e)
        check("no decision was recorded, so the evidence proposes staying on yesterday's skill, and says why", gp["progressor"]["proposed"]["id"] == "N2.3.2" and gp["progressor"]["reason"] == "recommended" and gp["progressor"]["recommendation"] == "reteach" and gp["progressor"]["conflict"] is False)
        eb = gp["beginner"]["evidence"]
        check("the Beginners: 1 of 4, 2 are needed: NOT recommended, and nothing is proposed for them (the plan derives their skill)", eb["assessed"] == 4 and eb["with_mistakes"] == 1 and eb["needed"] == 2 and not eb["recommend"] and gp["beginner"]["proposed"] is None and gp["beginner"]["recommendation"] is None)
        ep = gp["proficient"]["evidence"]
        check("the Proficients: only 2 assessed is a very small group: shown, not recommended, and flagged", ep["assessed"] == 2 and ep["very_small"] and not ep["recommend"] and gp["proficient"]["recommendation"] == "very_small" and gp["proficient"]["proposed"] is None)
        gp = await prop2({"progressor": "advance"})
        check("the teacher chose ADVANCE although the evidence recommends a re-teach: the teacher's decision stands (the next skill is proposed), and the conflict is flagged so the screen can ask", gp["progressor"]["reason"] == "advance" and gp["progressor"]["proposed"]["id"] != "N2.3.2" and gp["progressor"]["conflict"] is True)
        gp = await prop2({"progressor": "reteach"})
        check("the teacher chose RE-TEACH: it stays a re-teach by the teacher's decision, with no conflict", gp["progressor"]["reason"] == "reteach" and gp["progressor"]["conflict"] is False)
        await ev(5, "N2.3.2", [mis["N2.3.2"][0]])                              # a second sheet for the same child
        await ev(7, "N2.3.3", [mis["N2.3.3"][0]] if mis["N2.3.3"] else [])    # another skill
        await ev(8, "N2.3.2", [mis["N2.3.2"][1]], prevday - timedelta(days=3)) # another day
        await ev(3, "N2.3.2", [mis["N2.3.2"][0]])                              # a Beginner: not in the Progressors' rolls
        e = (await prop2({}))["progressor"]["evidence"]
        check("a child counts once however many sheets; another skill, another day and another group's child are ignored", e["assessed"] == 6 and e["with_mistakes"] == 2 and e["rolls"] == [5, 6], e)
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1 AND competency_id = 'N2.3.2' AND child_id = $2", t2, kids2[6])
        await ev(6, "N2.3.2", [])
        gp = await prop2({})
        check("only 1 of 6 now: no recommendation, nothing proposed, and the evidence is still shown", not gp["progressor"]["evidence"]["recommend"] and gp["progressor"]["proposed"] is None and gp["progressor"]["evidence"]["with_mistakes"] == 1)
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", t2)
        e0 = (await prop2({}))["progressor"]
        check("no review evidence at all: assessed 0, nothing recommended, and the proposal is what it was before (nothing)", e0["evidence"]["assessed"] == 0 and e0["recommendation"] is None and e0["proposed"] is None)
        for roll in range(5, 11):
            await ev(roll, "N2.3.2", [mis["N2.3.2"][0]] if roll in (5, 6) else [])
        await put_plan(prevday, tg2, {}, tid=t2, rolls=rolls2)
        with TestClient(app) as c0:
            j0 = c0.get(f"/api/plan/proposal/{t2}/numeracy?plan_date={D}").json()
        check("the API carries the evidence and the recommendation to the screen", j0["groups"]["progressor"]["evidence"]["recommend"] is True and j0["groups"]["progressor"]["recommendation"] == "reteach" and j0["groups"]["progressor"]["evidence"]["rolls"] == [5, 6], j0["groups"]["progressor"])
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", t2)
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", t2)

        print("\na teacher's choice of skill for a group is checked")
        ok = await gs.clean_group_skills(db, "numeracy", "N2.3.2", {"beginner": "N2.3.2", "proficient": "N3.3.6"})
        check("valid choices pass through", ok == {"beginner": "N2.3.2", "proficient": "N3.3.6"}, ok)
        check("nothing given means no overrides", await gs.clean_group_skills(db, "numeracy", "N2.3.2", None) == {} and await gs.clean_group_skills(db, "numeracy", "N2.3.2", {"beginner": ""}) == {})
        check("naming the Progressors' skill as the day's skill is harmless", await gs.clean_group_skills(db, "numeracy", "N2.3.2", {"progressor": "N2.3.2"}) == {})

        async def refused(skills, domain="numeracy"):
            try:
                await gs.clean_group_skills(db, domain, "N2.3.2", skills)
                return None
            except gs.GroupSkillError as e:
                return str(e)
        check("an unknown skill is refused with a message", "not a skill of this subject" in (await refused({"beginner": "N9.9.9"}) or ""))
        check("a skill of the OTHER subject is refused", "not a skill of this subject" in (await refused({"proficient": "L1.3.2"}) or ""))
        check("a different skill for the Progressors is refused (they follow the day's skill)", "day's skill" in (await refused({"progressor": "N2.3.1"}) or ""))
        check("an unknown group is refused", "Unknown group" in (await refused({"teacher": "N2.3.1"}) or ""))

        print("\nwhich skills a group may take (the first screen let a tester pick N3.6.1 for the Beginners and N0.2.1 for the Proficients)")
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        opts = (await gs.ladder(db, "N2.3.2"))["options"]
        check("the ladder offers the foundations for the Beginners (nearest first) and the skills that build on it for the Proficients", opts["beginner"][0]["id"] == "N2.3.1" and opts["proficient"][0]["id"] == "N3.3.1" and len(opts["beginner"]) >= 5 and all(x["name_hi"] for x in opts["beginner"] + opts["proficient"]), opts["proficient"])
        al = await gs.allowed_skills(db, teacher_id, "numeracy", D, "N2.3.2")
        check("Beginners: today's skill and its foundations; Proficients: today's skill and what builds on it", {"N2.3.2", "N2.3.1", "N1.3.1"} <= al["beginner"] and {"N2.3.2", "N3.3.1", "N3.5.2", "N3.3.6"} <= al["proficient"])
        check("N3.6.1 is not allowed for the Beginners and N0.2.1 not for the Proficients (the two the tester tried), though N0.2.1 IS a foundation for the Beginners", "N3.6.1" not in al["beginner"] and "N0.2.1" not in al["proficient"] and "N0.2.1" in al["beginner"])

        async def refused_for(skills):
            try:
                await gs.clean_group_skills(db, "numeracy", "N2.3.2", skills, allowed=al)
                return None
            except gs.GroupSkillError as e:
                return str(e)
        check("a Grade 3 skill for the Beginners and a Balvatika skill for the Proficients are refused, with a message in Hindi and English", "उचित कौशल नहीं" in (await refused_for({"beginner": "N3.6.1"}) or "") and "is not a sensible skill for the Proficient group" in (await refused_for({"proficient": "N0.2.1"}) or ""))
        check("a foundation, today's skill and a skill that builds on it are accepted", await refused_for({"beginner": "N1.3.1", "proficient": "N3.5.2"}) is None and await refused_for({"beginner": "N2.3.2", "proficient": "N2.3.2"}) is None)
        check("precondition: N1.1.1 (Grade 1) is not one of N2.3.2's foundations, so only 'yesterday' can make it a choice", "N1.1.1" not in al["beginner"])
        await put_plan(D - timedelta(days=1), {"beginner": "N1.1.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}, {"beginner": "reteach"})
        al2 = await gs.allowed_skills(db, teacher_id, "numeracy", D, "N2.3.2")
        check("a group may stay where it was yesterday, even far from today's skill, if it is not AHEAD of it (the Beginners on Grade 1 N1.1.1, today's skill being Grade 2)", "N1.1.1" in al2["beginner"])
        await put_plan(D - timedelta(days=1), {"beginner": "N3.6.1", "progressor": "N2.3.2", "proficient": "N0.2.1"}, {})
        al3 = await gs.allowed_skills(db, teacher_id, "numeracy", D, "N2.3.2")
        check("...but not when that is AHEAD of today's skill for the Beginners (Grade 3 N3.6.1) or BEHIND it for the Proficients (Balvatika N0.2.1)", "N3.6.1" not in al3["beginner"] and "N0.2.1" not in al3["proficient"])
        await put_plan(D - timedelta(days=1), {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.6.1"}, {})
        al4 = await gs.allowed_skills(db, teacher_id, "numeracy", D, "N2.3.2")
        check("...while Proficients who were AHEAD (Grade 3 N3.6.1) may stay ahead", "N3.6.1" in al4["proficient"])
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)

        print("\nwhat yesterday's plan DID (found on the click-through: the plan had a Progressor re-teach and the screen showed no trace of it)")
        tg = {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}
        async def retaught(content):
            await put_plan(D - timedelta(days=1), tg, {}, content=content)
            g = (await gs.propose(db, teacher_id, "numeracy", D))["groups"]
            return {k: g[k]["previous_reteach"] for k in g}
        check("the teacher's choice recorded in the plan (reteach_groups) is remembered: only the Progressors re-taught", await retaught({"reteach_groups": ["progressor"]}) == {"beginner": False, "progressor": True, "proficient": False})
        check("a teach block marked as a re-teach counts, with or without the list", await retaught({"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "beginner", "reteach": True}, {"type": "teach", "teach_group": "progressor", "reteach": False}]}}) == {"beginner": True, "progressor": False, "proficient": False})
        check("a plan made the old way (a separate re-teach block that names its group) counts too", (await retaught({"rotation_schedule": {"blocks": [{"type": "reteach", "teach_group": "proficient"}]}}))["proficient"] is True)
        check("a plan without any re-teach, an empty plan and an unknown group in the list remember nothing", await retaught({}) == {"beginner": False, "progressor": False, "proficient": False} and await retaught({"reteach_groups": ["nobody"]}) == {"beginner": False, "progressor": False, "proficient": False})
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)

        print("\nthe day's skill is NOT the one yesterday's decisions were about (found on the click-through: N0.1.1 chosen, the Beginners were given N2.3.2)")
        check("the rule by grade: the Beginners are never ahead, the Proficients never behind, the same grade fits, and an unknown grade fits",
              gs.fits_day("beginner", "grade_2", "balvatika") is False and gs.fits_day("beginner", "balvatika", "grade_2") and gs.fits_day("beginner", "grade_2", "grade_2")
              and gs.fits_day("proficient", "balvatika", "grade_2") is False and gs.fits_day("proficient", "grade_3", "grade_2") and gs.fits_day("proficient", None, "grade_2") and gs.fits_day("beginner", "grade_9", "grade_2"))
        await put_plan(D - timedelta(days=1), {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}, {"beginner": "advance"})
        alb = await gs.allowed_skills(db, teacher_id, "numeracy", D, "N0.1.1")
        check("with N0.1.1 chosen for the day, the Beginners' Advance suggestion (N2.3.2) and yesterday's skill (N2.3.1) are NOT choices: only N0.1.1", alb["beginner"] == {"N0.1.1"}, alb["beginner"])
        check("...and the Proficients, who were on Grade 3 N3.3.1, may stay there (it is ahead of the day's skill, not behind it)", "N3.3.1" in alb["proficient"])
        refusal = None
        try:
            await gs.clean_group_skills(db, "numeracy", "N0.1.1", {"beginner": "N2.3.2"}, allowed=alb)
        except gs.GroupSkillError as e:
            refusal = str(e)
        check("choosing N2.3.2 for the Beginners on an N0.1.1 day is refused, saying why in Hindi and English", refusal is not None and "आज के कौशल से आगे" in refusal and "cannot be ahead of today's skill" in refusal, refusal)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        calls0 = None

        print("\na re-teach is the SAME skill as yesterday (the first screen warned, but still let the plan be made)")
        sk_today = {"beginner": "N2.3.2", "progressor": "N2.3.2", "proficient": "N3.3.1"}
        await gs.check_reteach_same_skill(db, teacher_id, "numeracy", D, ["beginner"], sk_today)
        check("no yesterday: nothing to compare, nothing is refused", True)
        await put_plan(D - timedelta(days=1), {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}, {})
        try:
            await gs.check_reteach_same_skill(db, teacher_id, "numeracy", D, ["beginner"], sk_today)
            check("the Beginners were on N2.3.1 yesterday and are on N2.3.2 today: a re-teach is refused", False)
        except gs.GroupSkillError as e:
            check("the Beginners were on N2.3.1 yesterday and are on N2.3.2 today: a re-teach is refused, with both skills named", "N2.3.1" in str(e) and "N2.3.2" in str(e) and "A re-teach is the same skill as yesterday" in str(e), str(e))
        await gs.check_reteach_same_skill(db, teacher_id, "numeracy", D, ["progressor", "proficient"], sk_today)
        check("the groups that ARE on yesterday's skill may re-teach, and a group not chosen is not checked", True)
        before = fake_calls_probe = None
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)

        print("\nplan generation with a teacher's choice (a stand-in model)")

        class Fake:
            def __init__(self):
                self.calls, self.prompt = 0, ""

            async def create(self, **kw):
                self.calls += 1
                self.prompt = kw["messages"][0]["content"]
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(SAMPLE, ensure_ascii=False))], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))
        fake = Fake()
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)

        async def gen(day, skills=None, comp="N2.3.2", reteach=None):
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, comp, "numeracy", day, group_skills=skills, reteach_groups=reteach)
            row = await db.fetchrow("SELECT plan_content, groups_snapshot, explainability FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'numeracy'", teacher_id, day)
            return obj(row["plan_content"]), obj(row["groups_snapshot"]), obj(row["explainability"])

        pc, snap, _ = await gen(D)
        check("without a choice nothing changes: Beginners N2.3.1, Progressors N2.3.2, Proficients N3.3.1, all marked as derived",
              {k: v["target"] for k, v in snap.items()} == {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"} and pc["group_skills"] == {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}
              and pc["group_skills_source"] == {"beginner": "derived", "progressor": "selected", "proficient": "derived"}, (snap, pc.get("group_skills")))
        name332 = await db.fetchval("SELECT name_en FROM competencies WHERE id = 'N3.3.6'")
        pc, snap, _ = await gen(D + timedelta(days=1), {"beginner": "N2.3.2", "proficient": "N3.3.6"})
        check("a teacher's choice sets the group's skill in the saved plan and the group snapshot (Beginners N2.3.2, Proficients N3.3.6), marked as the teacher's",
              {k: v["target"] for k, v in snap.items()} == {"beginner": "N2.3.2", "progressor": "N2.3.2", "proficient": "N3.3.6"} and pc["group_skills_source"] == {"beginner": "teacher", "progressor": "selected", "proficient": "teacher"}, (snap, pc.get("group_skills_source")))
        check("...and the skill reaches the model's request", name332 in fake.prompt, name332)
        pc, snap, _ = await gen(D + timedelta(days=2), {"proficient": "N3.3.6"})
        check("a choice for ONE group leaves the other derived", snap["beginner"]["target"] == "N2.3.1" and snap["proficient"]["target"] == "N3.3.6" and pc["group_skills_source"]["beginner"] == "derived")
        calls = fake.calls
        try:
            await gen(D + timedelta(days=21), {"beginner": "N3.6.1"})
            check("a Grade 3 skill for the Beginners is refused when generating", False)
        except gs.GroupSkillError:
            check("a Grade 3 skill for the Beginners is refused when generating, BEFORE the model is called", fake.calls == calls)
        await put_plan(D + timedelta(days=21) - timedelta(days=1), {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}, {"beginner": "reteach"})
        try:
            await gen(D + timedelta(days=21), {"beginner": "N2.3.2"}, reteach=["beginner"])
            check("a re-teach on a different skill than yesterday's is refused when generating", False)
        except gs.GroupSkillError:
            check("a re-teach on a different skill than yesterday's is refused when generating, BEFORE the model is called", fake.calls == calls)
        await gen(D + timedelta(days=21), None, reteach=["beginner"])
        check("...and the same re-teach on yesterday's skill (N2.3.1, the derived one) is accepted", fake.calls == calls + 1)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        calls = fake.calls
        try:
            await gen(D + timedelta(days=3), {"beginner": "N9.9.9"})
            check("a bad skill is refused", False)
        except gs.GroupSkillError:
            check("a bad skill is refused BEFORE the model is called (no money spent)", fake.calls == calls)

        print("\nthe teacher's recorded decisions survive regenerating the plan")
        day = D + timedelta(days=5)
        await put_plan(day, {"beginner": "N2.3.1"}, {"beginner": "advance", "progressor": "reteach"})
        _, _, expl = await gen(day)
        check("regenerating the plan for a date keeps the decisions recorded for it (the plan's own notes are replaced, the decisions are not)", expl.get("teacher_decision_beginner") == "advance" and expl.get("teacher_decision_progressor") == "reteach", expl)

        print("\nthe skills the plan derives, which the screen shows before generating (one rule for both)")
        lad = await gs.ladder(db, "N2.3.2")
        check("selecting N2.3.2 gives Beginners N2.3.1, Progressors N2.3.2, Proficients N3.3.1", (lad["beginner"]["id"], lad["progressor"]["id"], lad["proficient"]["id"]) == ("N2.3.1", "N2.3.2", "N3.3.1"), lad)
        l2, l3 = await gs.ladder(db, "N3.3.1"), await gs.ladder(db, "N2.3.3")
        check("the ladder is a graph, not a chain: N3.3.1 gives N2.2.2 and N3.5.2, and subtraction N2.3.3 gives N1.2.4 and N2.3.4", (l2["beginner"]["id"], l2["proficient"]["id"], l3["beginner"]["id"], l3["proficient"]["id"]) == ("N2.2.2", "N3.5.2", "N1.2.4", "N2.3.4"))
        leaf2 = await gs.ladder(db, leaf)
        check("a skill nothing depends on gives itself as the Proficients' skill, and names come with it", leaf2["proficient"]["id"] == leaf and leaf2["proficient"]["name_hi"] and lad["beginner"]["name_en"])
        check("an unknown skill has no ladder", await gs.ladder(db, "N9.9.9") is None)
        pcl, snapl, _ = await gen(D + timedelta(days=20))
        check("the plan's own groups are exactly what the ladder said (the plan and the panel use ONE rule)", {k: v["target"] for k, v in snapl.items()} == {k: lad[k]["id"] for k in ("beginner", "progressor", "proficient")}, snapl)

        print("\nwhat the API offers the app")
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await put_plan(D - timedelta(days=1), {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}, {"beginner": "advance", "progressor": "reteach"})
        with TestClient(app) as c:
            r = c.get("/api/plan/ladder/N2.3.2")
            check("GET /plan/ladder returns the derived skills with names, and an unknown skill is 404", r.status_code == 200 and r.json()["proficient"]["id"] == "N3.3.1" and r.json()["beginner"]["name_hi"] and c.get("/api/plan/ladder/N9.9.9").status_code == 404, r.text[:140])
            r = c.get(f"/api/plan/proposal/{teacher_id}/numeracy?plan_date={D}")
            j = r.json() if r.status_code == 200 else {}
            check("GET /plan/proposal returns the proposal (the route is not swallowed by the cached-plan route)", r.status_code == 200 and j.get("has_history") and j["groups"]["beginner"]["proposed"]["id"] == "N2.3.2", r.text[:160])
            check("an unknown subject is refused", c.get(f"/api/plan/proposal/{teacher_id}/bogus?plan_date={D}").status_code == 400)
            r = c.post(f"/api/plan/generate?teacher_id={teacher_id}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(D + timedelta(days=9)), "group_skills": {"beginner": "N9.9.9"}})
            check("POST /plan/generate with a bad skill for a group: HTTP 400 with a code the app can show, and no plan is made", r.status_code == 400 and r.json().get("detail", {}).get("code") == "bad_group_skill", r.text[:160])
            r = c.post(f"/api/plan/generate?teacher_id={teacher_id}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(D + timedelta(days=9))})
            check("the old request (no group_skills) still works", r.status_code == 200 and r.json()["plan"]["group_skills"]["beginner"] == "N2.3.1", r.text[:160])
    finally:
        anthropic.AsyncAnthropic = real_client
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        if t2:
            await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", t2)
            await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", t2)
            await _scratch.remove_class(db, t2, school2)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: each group's skill is proposed from the teacher's decisions, a teacher's choice is checked and used, and the recorded decisions survive")


if __name__ == "__main__":
    asyncio.run(main())
