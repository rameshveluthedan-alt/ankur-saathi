"""
The teacher decides, and a re-teach is the group's MAIN teach block (no separate 5-minute block). The decision comes from the Review screen (Advance / Re-teach / Not sure) through the Plan screen.
The code marks the block and fills in which children and which mistakes: a child's roll number never goes to the AI.

    cd backend && AUTH_MODE=off python tests/test_reteach_main.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import copy
import io
import json
import os
import re
import sys
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
import anthropic
from fastapi.testclient import TestClient
from orchestrate import pick_priority_group, RETEACH_MAIN_RULES
from app.main import app
from app.services import group_skills as gs, plan_service
from app.services.plan_service import stamp_reteach_main

TODAY = date.today()
failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("the group taught first, when the teacher decided (no database)")
items = [{"affected_by_group": {"beginner": 1, "progressor": 3}, "competency_id": "N2.3.2"}, {"affected_by_group": {"proficient": 5}, "competency_id": "N2.3.2"}]
check("nothing chosen: the Beginners, as before", pick_priority_group(items, [])[0] == "beginner")
legacy_items = [{"group": "beginner", "affected_count": 1}, {"group": "progressor", "affected_count": 3}, {"group": "proficient", "affected_count": 5}]
check("the old way (not asked) is unchanged: the group with most children who made the mistake (items in the old shape: group and affected_count)", pick_priority_group(legacy_items, None)[0] == "proficient" and pick_priority_group(legacy_items)[0] == "proficient")
check("of the groups the teacher CHOSE, the one with most children who made a mistake (the Proficients' 5 children do not count if they were not chosen)", pick_priority_group(items, ["beginner", "progressor"])[0] == "progressor")
g, why = pick_priority_group(items, ["progressor"])
check("the reason says the TEACHER chose it", g == "progressor" and "teacher chose to re-teach the Progressor" in why, why)
check("a chosen group with no mistakes recorded still goes first, and a tie goes to the group furthest behind", pick_priority_group([], ["progressor", "proficient"])[0] == "progressor" and pick_priority_group([], ["proficient"])[0] == "proficient")

print("\nthe block is marked by the code (no database)")
def blocks():
    return [{"type": "anchor"}, {"type": "setup"}, {"type": "teach", "teach_group": "progressor", "other_groups_hi": "x"}, {"type": "transition"},
            {"type": "teach", "teach_group": "beginner"}, {"type": "transition"}, {"type": "teach", "teach_group": "proficient"}]
its = [{"competency_id": "N2.3.2", "misconception_id": "N2.3.2-M1", "misconception_name_hi": "हासिल भूलना", "affected_by_group": {"progressor": 2, "beginner": 1}, "rolls_by_group": {"progressor": [27, 25], "beginner": [3]}},
       {"competency_id": "N2.3.2", "misconception_id": "N2.3.2-M2", "misconception_name_hi": "पूरा योग लिखना", "affected_by_group": {"progressor": 1}, "rolls_by_group": {"progressor": [25]}},
       {"competency_id": "N2.3.1", "misconception_id": "N2.3.1-M1", "misconception_name_hi": "स्तम्भ गड़बड़", "affected_by_group": {"progressor": 4}, "rolls_by_group": {"progressor": [9, 10, 11, 12]}}]
skills = {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}
b = blocks()
marked = stamp_reteach_main(b, ["progressor"], its, skills)
check("only the chosen group's teach block is marked", marked == ["progressor"] and b[2].get("reteach") is True and "reteach" not in b[4] and "reteach" not in b[6])
check("it lists the children of THAT group who made a mistake in THAT group's skill today: sorted, each once (not the Beginner, not the other skill's four children)", b[2]["affected_rolls"] == [25, 27], b[2]["affected_rolls"])
check("and the mistakes, with how many children made each", [(m["misconception_id"], m["children"]) for m in b[2]["reteach_mistakes"]] == [("N2.3.2-M1", 2), ("N2.3.2-M2", 1)], b[2]["reteach_mistakes"])
check("the model's own text in the block is kept", b[2]["other_groups_hi"] == "x")
b = blocks()
stamp_reteach_main(b, ["beginner"], its, skills)
check("the Beginners are taught N2.3.1 today, so the N2.3.2 mistake their roll 3 made is NOT theirs to re-teach (it is only listed if the skill matches)", b[4]["affected_rolls"] == [] and b[4]["reteach_mistakes"] == [] and b[4]["reteach"] is True, b[4])
b = blocks()
stamp_reteach_main(b, ["beginner"], its, dict(skills, beginner="N2.3.2"))
check("...but if the teacher put the Beginners on N2.3.2, it is", b[4]["affected_rolls"] == [3] and b[4]["reteach_mistakes"][0]["children"] == 1, b[4])
b = blocks()
check("nobody chosen: nothing is marked", stamp_reteach_main(b, [], its, skills) == [] and all("reteach" not in x for x in b))
check("a separate re-teach block, if the model wrote one, is not touched", stamp_reteach_main([{"type": "reteach", "teach_group": None}], ["progressor"], its, skills) == [])
check("the rules for the block are in ONE constant that says: the mistake first, find and fix, a short try, no child named", all(w in RETEACH_MAIN_RULES for w in ("show the mistake FIRST", "FIND AND FIX", "Name no child")))
check("...and the teachers' points: recall first, new numbers, ERASE the wrong working (no red cross), the pace, visit the children quietly and never call out roll numbers, re-teach the step at once if a quarter is wrong", all(w in RETEACH_MAIN_RULES for w in ("कल हमने क्या सीखा था", "NEW numbers", "ERASE it", "recall 2, I Do 6, We Do 7", "quietly", "never call out", "more than a quarter")))
check("the choice is checked", gs.clean_reteach_groups(None) is None and gs.clean_reteach_groups([]) == [] and gs.clean_reteach_groups(["progressor", "progressor", "beginner"]) == ["progressor", "beginner"])
for bad in (["nobody"], "progressor", [1]):
    try:
        gs.clean_reteach_groups(bad)
        check(f"a bad choice {bad!r} is refused", False)
    except gs.GroupSkillError:
        check(f"a bad choice {bad!r} is refused", True)


class FakeMessages:
    def __init__(self):
        self.prompts, self.stray = [], False

    async def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        plan = copy.deepcopy(SAMPLE)
        if self.stray:                                           # the model writes a separate re-teach block although it was told not to
            plan["rotation_schedule"]["blocks"].insert(2, {"type": "reteach", "script_hi": None, "time_start": "0:12", "teach_group": None, "talking_points": None, "other_groups_hi": None, "duration_minutes": 5})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(plan, ensure_ascii=False))], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    real_client, fake = anthropic.AsyncAnthropic, FakeMessages()
    anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
    try:
        kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
        m = await db.fetch("SELECT id, competency_id, name_hi FROM misconceptions WHERE competency_id = 'N2.3.2' ORDER BY id")
        m1, m2 = m[0], m[1]
        for rolls, mis in (([4, 5], m1), ([1], m2)):
            for r in rolls:
                await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date) "
                                 "VALUES ($1, $2, $3, 'written_photo', 'not_achieved', '{}'::jsonb, $4, $5)", kids[r], mis["competency_id"], teacher_id, [mis["id"]], TODAY - timedelta(days=1))

        async def gen(day, **kw):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", day, **kw)
            row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'numeracy'", teacher_id, day)
            pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
            return pc, {b_["teach_group"]: b_ for b_ in pc["rotation_schedule"]["blocks"] if b_["type"] == "teach"}, fake.prompts[-1], buf.getvalue()

        print("\na whole plan, the OLD way (the teacher was not asked): a separate 5-minute block, as before")
        pc, tb, prompt_old, _ = await gen(TODAY)
        check("the model is told about a 5-minute re-teaching segment and PART C lists it", "5-minute re-teaching segment" in prompt_old and "- Re-teach: 5 min" in prompt_old)
        check("no block is marked as a re-teach main block, and the plan has no 'reteach_groups'", not any(b_.get("reteach") for b_ in tb.values()) and "reteach_groups" not in pc)

        print("\nthe teacher chose to re-teach the PROGRESSORS")
        pc, tb, prompt, _ = await gen(TODAY + timedelta(days=1), reteach_groups=["progressor"])
        check("the model is told the teacher decided, that the main block is the re-teach, and that there is NO separate block", "RE-TEACH: PROGRESSOR" in prompt and "NO separate re-teach block" in prompt)
        check("PART C has no separate 5 minutes, and the Progressors' block is marked as the re-teach", "- Re-teach: 5 min" not in prompt and "5-minute re-teaching segment" not in prompt and re.search(r"TEACH progressor \(\d+ min\) — RE-TEACH", prompt) is not None, [l for l in prompt.splitlines() if l.startswith("- Block")])
        check("the mistake the Progressors made is named, with the number of children (2) and nothing else about them", f"{m1['id']}" in prompt and "(2 children)" in prompt)
        check("the rules for the block are in the request", "show the mistake FIRST" in prompt and "FIND AND FIX" in prompt)
        check("the stick rules tell the model not to explain the kit limit in the talking points (a real run did, although the example fitted)", "NEVER explain the kit size" in prompt)
        check("the Progressors are taught first, and the reason says why", re.search(r"Block 1: TEACH progressor .*teacher chose to re-teach the Progressor", prompt) is not None)
        check("NO child's roll number reached the AI", "affected_rolls" not in prompt and "rolls_by_group" not in prompt)
        check("the stored plan: the Progressors' block is marked, with rolls 4 and 5 and the mistake, in code", tb["progressor"].get("reteach") is True and tb["progressor"]["affected_rolls"] == [4, 5] and tb["progressor"]["reteach_mistakes"][0]["misconception_id"] == m1["id"] and tb["progressor"]["reteach_mistakes"][0]["children"] == 2, tb["progressor"].get("reteach_mistakes"))
        check("the other groups' blocks are NOT marked, there is no separate re-teach block, and the plan records the groups", not tb["beginner"].get("reteach") and not tb["proficient"].get("reteach") and pc["reteach_groups"] == ["progressor"] and not any(b_["type"] == "reteach" for b_ in pc["rotation_schedule"]["blocks"]))

        print("\nthe teacher chose to MOVE ON with every group (although yesterday's photos found mistakes)")
        pc, tb, prompt, _ = await gen(TODAY + timedelta(days=2), reteach_groups=[])
        check("the model is told there is no re-teach, and no 5-minute block", "MOVE ON with every group" in prompt and "- Re-teach: 5 min" not in prompt and "5-minute re-teaching segment" not in prompt)
        check("nothing is marked, and the plan records that the teacher decided", not any(b_.get("reteach") for b_ in tb.values()) and pc["reteach_groups"] == [])

        print("\nthe skill matters: the Beginners are taught N2.3.1, so a mistake in N2.3.2 is not theirs (until the teacher puts them on N2.3.2)")
        pc, tb, prompt, _ = await gen(TODAY + timedelta(days=3), reteach_groups=["beginner"])
        check("re-teach the Beginners (N2.3.1): no recorded mistake of THEIR skill, so the model is told to use the commonest mistakes, and no roll numbers are stamped", "No specific mistake was recorded for this group" in prompt and tb["beginner"]["reteach"] is True and tb["beginner"]["affected_rolls"] == [], tb["beginner"])
        try:
            await gen(TODAY + timedelta(days=4), reteach_groups=["beginner"], group_skills={"beginner": "N2.3.2"})
            check("re-teaching the Beginners on N2.3.2 when yesterday they were on N2.3.1 is REFUSED (a re-teach is the same skill as yesterday)", False)
        except gs.GroupSkillError as e:
            check("re-teaching the Beginners on N2.3.2 when yesterday they were on N2.3.1 is REFUSED (a re-teach is the same skill as yesterday), before the model is called", "N2.3.1" in str(e) and "N2.3.2" in str(e))
        await db.execute("UPDATE daily_plans SET groups_snapshot = jsonb_set(groups_snapshot, '{beginner,target}', '\"N2.3.2\"') WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=3))
        pc, tb, prompt, _ = await gen(TODAY + timedelta(days=4), reteach_groups=["beginner"], group_skills={"beginner": "N2.3.2"})      # now yesterday the Beginners WERE on N2.3.2
        check("with the Beginners put on N2.3.2 (step 1), roll 1's mistake IS theirs: named in the request, and roll 1 is stamped in the block", f"{m2['id']}" in prompt and tb["beginner"]["affected_rolls"] == [1], tb["beginner"])

        print("\na model that disobeys")
        fake.stray = True
        pc, tb, prompt, out = await gen(TODAY + timedelta(days=5), reteach_groups=["progressor"])
        fake.stray = False
        check("a separate re-teach block written anyway is reported as a plan shape warning, and the main block is still marked", "a separate re-teach block was written" in out and tb["progressor"].get("reteach") is True)

        print("\nthe API")
        with TestClient(app) as c:
            r = c.post(f"/api/plan/generate?teacher_id={teacher_id}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(TODAY + timedelta(days=9)), "reteach_groups": ["nobody"]})
            check("an unknown group is HTTP 400 with a code the app can show, before any paid call", r.status_code == 400 and r.json()["detail"]["code"] == "bad_group_skill", r.text[:140])
            r = c.post(f"/api/plan/generate?teacher_id={teacher_id}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(TODAY + timedelta(days=9)), "reteach_groups": "progressor"})
            check("a string instead of a list is refused", r.status_code == 422, r.status_code)
            r = c.post(f"/api/plan/generate?teacher_id={teacher_id}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(TODAY + timedelta(days=9)), "reteach_groups": ["progressor"]})
            check("a valid choice works through the API, and the reply carries the plan with its re-teach marks", r.status_code == 200 and r.json()["plan"]["reteach_groups"] == ["progressor"], r.text[:140])
    finally:
        anthropic.AsyncAnthropic = real_client
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: the teacher's decision makes the re-teach the group's main block, marked by the code, with no separate block and no roll number sent to the AI")


if __name__ == "__main__":
    asyncio.run(main())
