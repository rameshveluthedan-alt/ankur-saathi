"""
Check for understanding in every lesson: the model writes show-me questions, the CODE decides which a teacher may use.
Pure rules (the checks, the cleaning, the prompt), then a real class through the whole pipeline with a stand-in model, then the switch.

    python scripts/add_cfu_setting.py        (once: adds the CFU_ENABLED line to config.py; the switch test needs it)
    cd backend && AUTH_MODE=off python tests/test_cfu.py --env-file .env
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
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]
import _scratch
import anthropic
import cfu_prompt
from app.services import cfu
from app.services import plan_service
from app.core.config import get_settings

TODAY = date.today()
failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


lf = lambda mid, w: [{"misconception_id": mid, "wrong_answer_hi": w}]
V = {"X-M1", "X-M2"}
ck = lambda item, avoid=(), rules=None: cfu.check_item(item, valid_ids=V, avoid=set(avoid), rules=rules or {})

print("the checks on one question")
check("compute: a right expected answer passes", not ck({"kind": "compute", "question_hi": "58 + 27 कितना होगा?", "expected_hi": "85", "listen_for": lf("X-M1", "75")}))
check("compute: a wrong expected answer is dropped", "real result 85" in " ".join(ck({"kind": "compute", "question_hi": "58 + 27 कितना होगा?", "expected_hi": "84", "listen_for": lf("X-M1", "75")})))
check("compute: a question that states its own answer is dropped", ck({"kind": "compute", "question_hi": "58 + 27 = 85 कैसे?", "expected_hi": "85", "listen_for": lf("X-M1", "75")}) != [])
check("choose: passes when the real result is offered and expected", not ck({"kind": "choose", "question_hi": "58 + 27: उत्तर 75 है या 85?", "expected_hi": "85, क्योंकि 8 + 7 = 15", "listen_for": lf("X-M1", "75")}))
check("choose: dropped when the real result is not among the offered answers", ck({"kind": "choose", "question_hi": "58 + 27: उत्तर 75 है या 95?", "expected_hi": "85", "listen_for": lf("X-M1", "75")}) != [])
check("spot_error: passes when the worked line really is wrong and the answer gives the real result", not ck({"kind": "spot_error", "question_hi": "47 + 25 = 612: सही या गलत?", "expected_hi": "गलत। सही उत्तर 72", "listen_for": lf("X-M2", "612")}))
check("spot_error: dropped when the line is actually right", ck({"kind": "spot_error", "question_hi": "47 + 25 = 72: सही या गलत?", "expected_hi": "सही", "listen_for": lf("X-M1", "x")}) != [])
check("a wrong worked line in the expected answer is dropped (8 + 7 = 14)", ck({"kind": "answer", "question_hi": "इकाई का योग क्या है?", "expected_hi": "8 + 7 = 14", "listen_for": lf("X-M1", "5")}) != [])
check("subtraction and multiplication are checked too", not ck({"kind": "compute", "question_hi": "78 − 35 कितना होगा?", "expected_hi": "43", "listen_for": [], "shows_hi": "x"}) and not ck({"kind": "compute", "question_hi": "4 × 5 कितना होगा?", "expected_hi": "20", "listen_for": [], "shows_hi": "x"})
      and ck({"kind": "compute", "question_hi": "78 − 35 कितना होगा?", "expected_hi": "44", "listen_for": [], "shows_hi": "x"}) != [])
check("an invented mistake id with no 'shows' line is dropped", ck({"kind": "answer", "question_hi": "इकाई क्या है?", "expected_hi": "2", "listen_for": lf("N9.9.9-M1", "12")}) != [])
check("a question with no recorded mistake is fine if it says what a right answer shows", not ck({"kind": "answer", "question_hi": "इकाई क्या है?", "expected_hi": "2", "listen_for": [], "shows_hi": "बच्चा इकाई पहचानता है"}))
check("reusing an example from the lesson or worksheet is dropped (in either order)", ck({"kind": "compute", "question_hi": "38 + 45 कितना होगा?", "expected_hi": "83", "listen_for": lf("X-M1", "73")}, avoid={("+", 38, 45)}) != []
      and ck({"kind": "compute", "question_hi": "45 + 38 कितना होगा?", "expected_hi": "83", "listen_for": lf("X-M1", "73")}, avoid={("+", 38, 45)}) != [])
check("a skill 'without regrouping' gets no question that needs a carry", ck({"kind": "compute", "question_hi": "38 + 47 कितना होगा?", "expected_hi": "85", "listen_for": [], "shows_hi": "x"}, rules={"no_carry": True}) != []
      and not ck({"kind": "compute", "question_hi": "21 + 36 कितना होगा?", "expected_hi": "57", "listen_for": [], "shows_hi": "x"}, rules={"no_carry": True}))
check("a skill 'without borrowing' gets no question that needs a borrow", ck({"kind": "compute", "question_hi": "52 − 17 कितना होगा?", "expected_hi": "35", "listen_for": [], "shows_hi": "x"}, rules={"no_borrow": True}) != []
      and not ck({"kind": "compute", "question_hi": "86 − 43 कितना होगा?", "expected_hi": "43", "listen_for": [], "shows_hi": "x"}, rules={"no_borrow": True}))
check("an answer too long to write on a slate is dropped", ck({"kind": "answer", "question_hi": "क्यों?", "expected_hi": "x" * 200, "listen_for": lf("X-M1", "x")}) != [])
check("rules are read from the skill's name", cfu.skill_rules("Adds two 2-digit numbers without regrouping")["no_carry"] and cfu.skill_rules("Subtracts 2-digit numbers without borrowing")["no_borrow"] and not any(cfu.skill_rules("Adds with regrouping").values()))

print("cleaning a whole plan")
KB = {"progressor": {"competency_id": "X", "name_en": "Adds with regrouping", "name_hi": "x", "mistakes": [
          {"id": "X-M1", "name_hi": "हासिल भूलना", "diagnostic_indicator": "Answer is exactly 10 less than correct"}, {"id": "X-M2", "name_hi": "पूरा योग लिखना", "diagnostic_indicator": "Three digits where two expected"}]},
      "beginner": {"competency_id": "Y", "name_en": "Adds two 2-digit numbers without regrouping", "name_hi": "y", "mistakes": []}}
good = lambda q, e, mid, w: {"kind": "compute", "question_hi": q, "expected_hi": e, "listen_for": lf(mid, w)}
plan = {"worksheets": {"progressor": {"problems": [{"problem_hi": "12 + 19"}]}},
        "rotation_schedule": {"blocks": [{"type": "anchor", "cfu": [{"junk": 1}]},
            {"type": "teach", "teach_group": "progressor", "talking_points": {"i_do_hi": "बोर्ड पर 47 + 25 लिखें।", "we_do_hi": "", "you_do_hi": ""}, "cfu": [
                good("58 + 27 कितना होगा?", "85", "X-M1", "75"),                         # fine
                good("29 + 48 कितना होगा?", "76", "X-M1", "x"),                          # wrong answer: dropped
                good("47 + 25 कितना होगा?", "72", "X-M1", "x"),                          # reuses the lesson's example: dropped
                good("12 + 19 कितना होगा?", "31", "X-M1", "x"),                          # reuses a worksheet problem: dropped
                {"kind": "answer", "question_hi": "इकाई का योग 13: इकाई में क्या?", "expected_hi": "3", "listen_for": [{"misconception_id": "X-M2", "wrong_answer_hi": "13"}, {"misconception_id": "N9-M9", "wrong_answer_hi": "q"}]},
                good("36 + 48 कितना होगा?", "84", "X-M2", "714"), good("67 + 15 कितना होगा?", "82", "X-M1", "72"), good("28 + 46 कितना होगा?", "74", "X-M1", "64")]},
            {"type": "teach", "teach_group": "beginner", "talking_points": {}, "cfu": [{"kind": "compute", "question_hi": "21 + 36 कितना होगा?", "expected_hi": "57", "listen_for": [], "shows_hi": "बच्चा दहाई और इकाई अलग जोड़ता है"}]},
            {"type": "teach", "teach_group": "proficient", "talking_points": {}}]}}
lines, stats = cfu.clean_plan_cfu(plan, KB)
blocks = plan["rotation_schedule"]["blocks"]
prog, beg, prof = blocks[1], blocks[2], blocks[3]
check("a block that is not a teach block gets no CFU, whatever the model wrote", "cfu" not in blocks[0])
check("the invalid questions are dropped and the valid ones kept (58+27, the grounded answer item, 36+48, 67+15, 28+46: five, but only four are allowed)", len(prog["cfu"]) == 4 and prog["cfu"][0]["question_hi"].startswith("58 + 27"), [q["question_hi"] for q in prog["cfu"]])
check("the dropped ones say why (wrong answer, reused lesson example, reused worksheet problem)", sum("dropped" in l for l in lines) == 3 and any("already used" in l for l in lines) and any("real result 77" in l for l in lines), lines)
check("a question beyond the four allowed is left out, and that is logged", any("beyond the 4 allowed" in l for l in lines))
item = prog["cfu"][1]
check("the mistake's Hindi name and its detect sign come from the knowledge base, not from the model", item["listen_for"] == [{"misconception_id": "X-M2", "misconception_name_hi": "पूरा योग लिखना", "detect_en": "Three digits where two expected", "wrong_answer_hi": "13"}], item["listen_for"])
check("an invented mistake id is removed from listen_for, the rest of the question stays", len(item["listen_for"]) == 1 and any("N9-M9" in l for l in lines))
check("a skill with recorded mistakes is marked grounded, and every kept question names one", prog["cfu_grounded"] is True and all(q["grounded"] for q in prog["cfu"]) and "cfu_note_hi" not in prog)
check("a skill with NO recorded mistakes is kept only through 'what a right answer shows', marked, and the screen note is set by the code", beg["cfu_grounded"] is False and len(beg["cfu"]) == 1 and beg["cfu"][0]["grounded"] is False and "दर्ज नहीं" in beg["cfu_note_hi"] and beg["cfu_note_en"])
check("a block where the model wrote no CFU gets an empty list and is logged", prof["cfu"] == [] and any("proficient: no CFU written" in l for l in lines))
check("the stats say what was written and kept", stats["progressor"] == {"written": 8, "kept": 4, "grounded_items": 4, "skill_has_mistakes": True} and stats["beginner"]["kept"] == 1, stats)
check("strip_cfu removes everything", (cfu.strip_cfu(plan) or True) and not any(k in b for b in blocks for k in ("cfu", "cfu_grounded", "cfu_note_hi")))

print("the prompt")
M = [{"id": "A-M1", "name_hi": "एक", "severity": "moderate", "frequency": "uncommon", "error_pattern": "p1", "diagnostic_indicator": "d1", "example_correct": "c", "example_incorrect": "w"},
     {"id": "A-M2", "name_hi": "दो", "severity": "critical", "frequency": "very_common", "error_pattern": "p2", "diagnostic_indicator": "d2", "example_correct": None, "example_incorrect": None},
     {"id": "A-M3", "name_hi": "तीन", "severity": "moderate", "frequency": "common", "error_pattern": "p3", "diagnostic_indicator": "d3", "example_correct": "c", "example_incorrect": "w"}]
check("mistakes are ranked: most common and most serious first", [m["id"] for m in cfu_prompt.rank_mistakes(M, {})] == ["A-M2", "A-M3", "A-M1"])
check("...and a mistake detected at the last review comes before everything", [m["id"] for m in cfu_prompt.rank_mistakes(M, {"A-M1": 2})][0] == "A-M1")
txt = cfu_prompt.render_cfu_section({"beginner": {"competency_id": "B", "name_en": "b", "name_hi": "ब", "mistakes": []}, "progressor": {"competency_id": "A", "name_en": "a", "name_hi": "अ", "mistakes": M}}, {"A-M1": 2})
check("the section carries the rules, the show-me, and no choral answering", "SHOW-ME" in txt and "Never choral" in txt and '"cfu"' in txt)
check("each group gets its own skill and its own mistakes, the detected one flagged first", "GROUP PROGRESSOR" in txt and txt.index("A-M1") < txt.index("A-M2") and "DETECTED at the last review in 2 child(ren)" in txt)
check("a group with no recorded mistakes is told to test the key idea", "No mistakes are recorded for this skill" in txt.split("GROUP PROGRESSOR")[0])
check("at most four mistakes per group", cfu_prompt.render_cfu_section({"progressor": {"competency_id": "A", "mistakes": [dict(M[0], id=f"A-M{i}") for i in range(9)]}}).count("pattern:") == 4)
check("nothing at all when CFU is switched off", cfu_prompt.render_cfu_section(None) == "" and cfu_prompt.render_cfu_section({}) == "")


class FakeMessages:
    def __init__(self, cfu_by_group):
        self.prompts, self.cfu_by_group = [], cfu_by_group

    async def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        plan = copy.deepcopy(SAMPLE)
        for b in plan["rotation_schedule"]["blocks"]:
            if b.get("type") == "teach" and b.get("teach_group") in self.cfu_by_group:
                b["cfu"] = copy.deepcopy(self.cfu_by_group[b["teach_group"]])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(plan, ensure_ascii=False))], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    real_client = anthropic.AsyncAnthropic
    settings = get_settings()
    try:
        ids = {c: [r["id"] for r in await db.fetch("SELECT id FROM misconceptions WHERE competency_id = $1 ORDER BY sort_order", c)] for c in ("N2.3.1", "N2.3.2", "N3.3.1", "N2.3.3")}
        print("\nthe whole pipeline, with a stand-in model (selected skill N2.3.2; Beginner N2.3.1, Progressor N2.3.2, Proficient N3.3.1)")
        check("the knowledge base has recorded mistakes for the three skills and none for N2.3.3", all(ids[c] for c in ("N2.3.1", "N2.3.2", "N3.3.1")) and not ids["N2.3.3"], ids)
        M1, M2 = [i for i in ids["N2.3.2"] if i.endswith("M1")][0], [i for i in ids["N2.3.2"] if i.endswith("M2")][0]
        written = {
            "progressor": [{"kind": "compute", "question_hi": "68 + 17 कितना होगा?", "expected_hi": "85", "listen_for": lf(M1, "75")},
                           {"kind": "choose", "question_hi": "39 + 46: उत्तर 75 है या 85?", "expected_hi": "85", "listen_for": lf(M1, "75")},
                           {"kind": "compute", "question_hi": "29 + 48 कितना होगा?", "expected_hi": "76", "listen_for": lf(M1, "66")},              # wrong answer: dropped
                           {"kind": "answer", "question_hi": "इकाई का योग 13 आए तो इकाई में क्या?", "expected_hi": "3", "listen_for": lf("N9.9.9-M1", "13")}],  # invented id, no shows: dropped
            "beginner": [{"kind": "compute", "question_hi": "21 + 36 कितना होगा?", "expected_hi": "57", "listen_for": lf(ids["N2.3.1"][0], "x")},
                         {"kind": "compute", "question_hi": "38 + 47 कितना होगा?", "expected_hi": "85", "listen_for": lf(ids["N2.3.1"][0], "x")},                # needs a carry: dropped
                         {"kind": "answer", "question_hi": "47 में कितनी दहाई हैं?", "expected_hi": "4", "listen_for": [], "shows_hi": "बच्चा दहाई पहचानता है"}],
            "proficient": "not a list at all"}
        # a mistake detected at the last review: two Progressors made M2 yesterday
        kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
        mrow = await db.fetchrow("SELECT competency_id FROM misconceptions WHERE id = $1", M2)
        for r in (4, 5):
            await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date) VALUES ($1, $2, $3, 'written_photo', 'not_achieved', '{}'::jsonb, $4, $5)",
                             kids[r], mrow["competency_id"], teacher_id, [M2], TODAY - timedelta(days=1))
        fake = FakeMessages(written)
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY)
        log, prompt = buf.getvalue(), fake.prompts[-1]
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        blocks = {b["teach_group"]: b for b in pc["rotation_schedule"]["blocks"] if b.get("type") == "teach"}
        check("the prompt carries the CFU rules", "CHECK FOR UNDERSTANDING" in prompt and "SHOW-ME" in prompt)
        check("each group's OWN skill and its recorded mistakes are in the prompt (the Beginners' N2.3.1 and the Proficients' N3.3.1, not only the selected skill's)",
              all(f"GROUP {g.upper()}" in prompt for g in ("BEGINNER", "PROGRESSOR", "PROFICIENT")) and ids["N2.3.1"][0] in prompt and ids["N3.3.1"][0] in prompt and M1 in prompt)
        sec = prompt[prompt.index("GROUP PROGRESSOR"):]
        check("the mistake detected at the last review is flagged and listed before the other Progressor mistakes", "DETECTED at the last review in 2 child(ren)" in sec and sec.index(M2) < sec.index(M1), sec[:300])
        check("the Progressor block keeps its two valid questions and drops the two bad ones", [q["question_hi"][:8] for q in blocks["progressor"]["cfu"]] == ["68 + 17 ", "39 + 46:"], blocks["progressor"].get("cfu"))
        check("...with the mistake's Hindi name from the knowledge base", blocks["progressor"]["cfu"][0]["listen_for"][0]["misconception_name_hi"] and blocks["progressor"]["cfu_grounded"] is True)
        check("the Beginner block drops the question that needs a carry (the skill is 'without regrouping') and keeps the others", [q["question_hi"][:8] for q in blocks["beginner"]["cfu"]] == ["21 + 36 ", "47 में क"], blocks["beginner"].get("cfu"))
        check("a model answer that is not a list for the Proficients gives an empty CFU, no crash", blocks["proficient"]["cfu"] == [])
        check("the log says what was dropped and what was kept", "CFU kept:" in log and "dropped" in log, log[-400:])
        check("no question is stored that was not checked: every stored question is in the knowledge base's terms", all(q["kind"] in cfu.KINDS for b in blocks.values() for q in b["cfu"]))

        print("\na skill with no recorded mistakes (N2.3.3 selected)")
        fake2 = FakeMessages({"progressor": [{"kind": "compute", "question_hi": "78 − 35 कितना होगा?", "expected_hi": "43", "listen_for": [], "shows_hi": "बच्चा स्तंभ-दर-स्तंभ घटाता है"},
                                             {"kind": "compute", "question_hi": "64 − 23 कितना होगा?", "expected_hi": "41", "listen_for": lf("N9.9.9-M1", "x"), "shows_hi": "बच्चा घटाव पक्का करता है"}]})
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake2)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.3", "numeracy", TODAY + timedelta(days=1))
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=1))
        pc2 = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        b2 = {b["teach_group"]: b for b in pc2["rotation_schedule"]["blocks"] if b.get("type") == "teach"}["progressor"]
        check("the prompt tells the model that this skill has no recorded mistakes", "No mistakes are recorded for this skill" in fake2.prompts[-1])
        check("the questions are kept through 'what a right answer shows', marked ungrounded, with the screen note", len(b2["cfu"]) == 2 and b2["cfu_grounded"] is False and all(not q["grounded"] for q in b2["cfu"]) and "दर्ज नहीं" in b2["cfu_note_hi"], b2)
        check("an invented mistake id is removed, not trusted", all(q["listen_for"] == [] for q in b2["cfu"]))

        print("\nthe switch")
        settings.cfu_enabled = False
        try:
            fake3 = FakeMessages(written)
            anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake3)
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=2))
            row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=2))
            pc3 = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
            check("switched off: the prompt has no CFU section", "CHECK FOR UNDERSTANDING" not in fake3.prompts[-1] and "GROUP BEGINNER" not in fake3.prompts[-1])
            check("switched off: nothing the model wrote reaches the plan", not any(k in b for b in pc3["rotation_schedule"]["blocks"] for k in ("cfu", "cfu_grounded", "cfu_note_hi")) and "cfu_stats" not in pc3)
        finally:
            settings.cfu_enabled = True
    finally:
        anthropic.AsyncAnthropic = real_client
        settings.cfu_enabled = True
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: every CFU question is checked by the code, each group gets its own mistakes, and the switch removes it all")


if __name__ == "__main__":
    asyncio.run(main())
