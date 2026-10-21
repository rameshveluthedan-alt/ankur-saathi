"""
A re-teach is FOR the group whose children made the mistake, and that group is taught first. It used to be written in as 'the Progressors' for
every mistake, whoever made it. Pure rules, then a real class with children at all three levels, then a whole plan through the pipeline.

    cd backend && AUTH_MODE=off python tests/test_reteach_group.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import copy
import io
import json
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prompts"))
import _scratch
import anthropic
from orchestrate import choose_reteach_group, pick_priority_group
from app.services import plan_service
from app.services.plan_service import stamp_reteach_block

TODAY = date.today()
failures = []
SAMPLE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("the rule, with no database")
check("most children wins", choose_reteach_group({"beginner": 1, "progressor": 3, "proficient": 0}) == "progressor")
check("a tie goes to the group furthest behind", choose_reteach_group({"beginner": 2, "progressor": 2}) == "beginner" and choose_reteach_group({"progressor": 1, "proficient": 1}) == "progressor")
check("nobody could be placed in a group: the Progressors (today's skill is theirs), as before", choose_reteach_group({}) == "progressor")
check("one proficient child is enough when nobody else made it", choose_reteach_group({"proficient": 1}) == "proficient")
check("no re-teach: the Beginners go first, as before", pick_priority_group([])[0] == "beginner")
g, why = pick_priority_group([{"group": "beginner", "affected_count": 3}, {"group": "progressor", "affected_count": 1}])
check("several mistakes are added up BY GROUP (3 beginners outweigh 1 progressor)", g == "beginner" and "Beginner" in why, (g, why))
check("...and the reverse", pick_priority_group([{"group": "beginner", "affected_count": 1}, {"group": "progressor", "affected_count": 4}])[0] == "progressor")
check("an item with no group is treated as the Progressors (older data)", pick_priority_group([{"affected_count": 2}])[0] == "progressor")


print("the re-teach block is filled in by the code, with no database")
def blocks():
    return [{"type": "anchor"}, {"type": "setup"}, {"type": "reteach", "teach_group": None, "other_groups_hi": None, "duration_minutes": 5},
            {"type": "teach", "teach_group": "progressor", "other_groups_hi": "शुरुआती: ... दक्ष: ..."}, {"type": "transition"}, {"type": "teach", "teach_group": "beginner", "other_groups_hi": "प्रगतिशील: ..."}]
items = [{"group": "progressor", "affected_count": 2, "rolls_by_group": {"progressor": [27, 25], "beginner": [3]}},
         {"group": "progressor", "affected_count": 1, "rolls_by_group": {"progressor": [25, 14]}}]
b = blocks()
check("a re-teach block is found", stamp_reteach_block(b, items) is True)
rt = b[2]
check("it says which group it is for", rt["teach_group"] == "progressor")
check("it lists the children of THAT group who made the mistake: sorted, each once, with no children of other groups", rt["affected_rolls"] == [14, 25, 27], rt["affected_rolls"])
check("the other groups' work is copied from the NEXT teach block (they start it during the re-teach)", rt["other_groups_hi"] == "शुरुआती: ... दक्ष: ...")
b = blocks(); b[2]["other_groups_hi"] = "the model wrote this itself"
stamp_reteach_block(b, items)
check("work the model DID write for the other groups is kept", b[2]["other_groups_hi"] == "the model wrote this itself")
b = [{"type": "anchor"}, {"type": "teach", "other_groups_hi": "x"}]
check("a plan with no re-teach block is left alone", stamp_reteach_block(b, items) is False and "teach_group" not in b[1] and "affected_rolls" not in b[1])
b = [{"type": "reteach", "other_groups_hi": None}, {"type": "teach", "other_groups_hi": None}]
stamp_reteach_block(b, [{"group": "beginner", "affected_count": 1, "rolls_by_group": {}}])
check("with nothing to copy and no children placed it still names the group and an empty list (nothing breaks)", b[0]["teach_group"] == "beginner" and b[0]["affected_rolls"] == [] and not b[0]["other_groups_hi"])

class FakeMessages:
    def __init__(self):
        self.prompts = []

    async def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        plan = copy.deepcopy(SAMPLE)                                                # the model writes a re-teach block but does NOT say which group
        blocks = plan["rotation_schedule"]["blocks"]
        blocks.insert(2, {"type": "reteach", "script_hi": None, "time_start": "0:12", "teach_group": None, "talking_points": None, "other_groups_hi": None, "duration_minutes": 5})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(plan, ensure_ascii=False))], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    real_client, fake = anthropic.AsyncAnthropic, FakeMessages()
    anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
    try:
        kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
        num = await db.fetch("""SELECT m.id, m.competency_id FROM misconceptions m JOIN competencies c ON c.id = m.competency_id JOIN subdomains s ON s.id = c.subdomain_id
                                WHERE s.domain_id = 'numeracy' ORDER BY m.id LIMIT 2""")
        m1, m2 = num[0], num[1]
        groups = await plan_service.get_current_groups(db, teacher_id, "numeracy")

        async def clear():
            await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)

        async def made(mis, rolls, day_offset=1):
            for r in rolls:
                await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date) "
                                 "VALUES ($1, $2, $3, 'written_photo', 'not_achieved', '{}'::jsonb, $4, $5)", kids[r], mis["competency_id"], teacher_id, [mis["id"]], TODAY - timedelta(days=day_offset))

        async def items(mids, groups_=None):
            return await plan_service.build_reteach_items(db, teacher_id, mids, TODAY - timedelta(days=1), groups_ if groups_ is not None else groups)

        print("a real class: rolls 1 to 3 Beginners, 4 to 6 Progressors, 7 and 8 Proficients")
        check("the groups are as built", {g["label"]: sorted(int(x) for x in g["roll_numbers"]) for g in groups} == {"beginner": [1, 2, 3], "progressor": [4, 5, 6], "proficient": [7, 8]})
        await made(m1, [1, 2])
        it = (await items([m1["id"]]))[0]
        check("two Beginners made the mistake: the re-teach is for the BEGINNERS (it used to say Progressors)", it["group"] == "beginner" and it["affected_count"] == 2 and it["affected_by_group"] == {"beginner": 2}, it)
        check("...and the roll numbers of those children are kept, by group", it["rolls_by_group"] == {"beginner": [1, 2]}, it)
        await clear(); await made(m1, [4])
        check("one Progressor: the Progressors", (await items([m1["id"]]))[0]["group"] == "progressor")
        await clear(); await made(m1, [7, 8])
        check("two Proficients: the Proficients", (await items([m1["id"]]))[0]["group"] == "proficient")
        await clear(); await made(m1, [1, 4, 5])
        it = (await items([m1["id"]]))[0]
        check("one Beginner and two Progressors: the Progressors, and all three children are counted", it["group"] == "progressor" and it["affected_count"] == 3 and it["affected_by_group"] == {"beginner": 1, "progressor": 2}, it)
        await clear(); await made(m1, [1, 4])
        check("a tie (one Beginner, one Progressor): the Beginners, furthest behind", (await items([m1["id"]]))[0]["group"] == "beginner")
        await clear(); await made(m1, [1, 1, 1]); await made(m1, [1], day_offset=1)
        check("a child with several evidence rows is counted once", (await items([m1["id"]]))[0]["affected_count"] == 1)
        await clear(); await made(m1, [1, 2, 3]); await made(m2, [4])
        its = await items([m1["id"], m2["id"]])
        check("two mistakes: each has its own group, and the group taught first is the one with most children (the Beginners, 3 against 1)",
              [i["group"] for i in its] == ["beginner", "progressor"] and pick_priority_group(its)[0] == "beginner", its)
        await clear(); await made(m1, [1])
        other = [dict(g, roll_numbers=[r for r in g["roll_numbers"] if str(r) != "1"]) for g in groups]
        check("a child who is in no group now (the level changed) cannot be placed: the Progressors, as before", (await items([m1["id"]], other))[0]["group"] == "progressor")
        check("an unknown misconception id is skipped, not a crash", await items(["NO-SUCH-ID"]) == [])

        print("a whole plan through the real pipeline: Beginners made the mistake yesterday")
        await clear(); await made(m1, [1, 2, 3])
        with contextlib.redirect_stdout(io.StringIO()):
            res = await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY)
        prompt = fake.prompts[-1]
        check("the model is told the re-teach is FOR the Beginners", "in the BEGINNER group: the re-teach is FOR them" in prompt and "mainly in the Beginner group" in prompt)
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        rt = [b for b in pc["rotation_schedule"]["blocks"] if b["type"] == "reteach"]
        check("the stored re-teach block says 'beginner' although the model left it blank: the code stamps it", len(rt) == 1 and rt[0]["teach_group"] == "beginner", rt)
        check("...it lists the children who made the mistake (rolls 1, 2, 3)", rt[0]["affected_rolls"] == [1, 2, 3], rt[0].get("affected_rolls"))
        first_teach = next(b for b in pc["rotation_schedule"]["blocks"] if b["type"] == "teach")
        check("...and the other groups' work is the first teach block's, so the 5 minutes are not empty for them", bool(rt[0]["other_groups_hi"]) and rt[0]["other_groups_hi"] == first_teach["other_groups_hi"])
        check("no child's roll number was sent to the AI (only counts and groups)", "affected_rolls" not in prompt and "rolls_by_group" not in prompt)
        await clear(); await made(m1, [4, 5])
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY)
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        rt2 = [b for b in pc["rotation_schedule"]["blocks"] if b["type"] == "reteach"]
        check("Progressors made it: the block says 'progressor' and lists rolls 4 and 5", [b["teach_group"] for b in rt2] == ["progressor"] and rt2[0]["affected_rolls"] == [4, 5], rt2)
    finally:
        anthropic.AsyncAnthropic = real_client
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: the re-teach is for the group that made the mistake, that group goes first, and the plan says so")


if __name__ == "__main__":
    asyncio.run(main())
