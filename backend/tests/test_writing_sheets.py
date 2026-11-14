"""
Writing skills get WRITING worksheets (backend/app/services/writing_sheets.py, 12 Nov 2026): a composition sheet (one task on the You Do's topic, a checklist,
short items on the parts), a dictation sheet (numbered blank lines; the sentences only in the teacher's plan), a formation sheet (no passage). The photo
analysis marks a composition against its checklist and a dictation word by word; a writing task weighs as many points as its checklist has items.
The AI is a fake: no paid call.

    cd backend && AUTH_MODE=off python tests/test_writing_sheets.py --env-file .env
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
import sys
from datetime import date
from types import SimpleNamespace as NS

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
import anthropic
import hindi_style
from app.services import plan_service, writing_sheets as W
from app.services.worksheet_service import render_worksheet
from vision_analysis import build_vision_prompt, rescore

TODAY = date.today()
failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "L2.7.2.json"), encoding="utf-8"))
SKILLS = {"beginner": "L2.7.1", "progressor": "L2.7.2", "proficient": "L3.7.1"}
SENTENCES = ["मोहन ने किताब पढ़ी।", "चिड़िया पेड़ पर बैठी है।", "हम मेले में गए।", "दीदी ने खीर बनाई।"]


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def new_shape(plan):
    """The L2.7.2 recorded plan, its sheets written the NEW way (as the prompt now asks), plus the faults the code must undo."""
    p = copy.deepcopy(plan)
    ws = p["worksheets"]
    ws["beginner"] = {"sheet_kind": "dictation", "instructions_hi": "सुनकर लिखिए।", "example_block": None, "passage_block": None,
                      "dictation_sentences": SENTENCES,
                      # the fault: the model ALSO printed a sentence for the child
                      "problems": [{"number": 1, "problem_hi": "शिक्षक बोलेंगे: 'मोहन ने किताब पढ़ी।' लिखिए।", "answer": "मोहन ने किताब पढ़ी।", "answer_type": "lines"}]}
    for lvl, topic in (("progressor", "मेरा पसंदीदा खेल"), ("proficient", "बारिश का एक दिन")):
        ws[lvl] = {"sheet_kind": "composition", "instructions_hi": "लिखिए।", "required_count": 4,
                   "passage_block": {"title": "पानी बचाओ", "text": "पानी अनमोल है।"},          # the fault: a passage on a writing sheet
                   "writing_task": {"topic_hi": topic, "lines": 8},
                   "checklist": [{"item_hi": "कम से कम 3 वाक्य", "item_en": "3+ sentences"}, {"item_hi": "सभी वाक्य विषय पर", "item_en": "on topic"},
                                 {"item_hi": "हर वाक्य के अंत में ।", "item_en": "each ends with ।"}, {"item_hi": "वाक्य 'और / फिर' से जुड़े", "item_en": "joined"}],
                   "problems": [{"number": 1, "problem_hi": "दो वाक्य 'और' से जोड़िए: राम आया। श्याम आया।", "answer": "राम और श्याम आए।", "answer_type": "lines", "answer_lines": 2},
                                {"number": 2, "problem_hi": f"'{topic}' पर 3-5 जुड़े वाक्य लिखिए।", "answer": "CHECKLIST", "answer_type": "lines"},
                                {"number": 3, "problem_hi": "पूर्ण विराम लगाइए: बारिश हुई बच्चे खेले", "answer": "बारिश हुई। बच्चे खेले।", "answer_type": "box"},
                                {"number": 4, "problem_hi": "बैंक का प्रश्न", "answer": "x", "from_bank": True}]}
    for b in p["rotation_schedule"]["blocks"]:
        if b.get("teach_group") in ("progressor", "proficient"):
            topic = ws[b["teach_group"]]["writing_task"]["topic_hi"]
            b["talking_points"]["you_do_hi"] = f"अब '{topic}' पर वर्कशीट की समस्या 1 में लिखिए।"
    return p


def unit():
    print("which sheet each skill gets")
    check("strand 7 is writing: L2.7.1 dictation; L2.7.2, L3.7.1, L3.7.3 composition; L2.7.3, L3.7.2 usage; L0.7.x, L1.7.x formation; others reading; numeracy none",
          [W.sheet_kind(c) for c in ("L2.7.1", "L2.7.2", "L3.7.1", "L3.7.3", "L0.7.2", "L1.7.3", "L2.7.3", "L3.7.2", "L2.6.1", "L1.6.1")]
          == ["dictation", "composition", "composition", "composition", "formation", "formation", "usage", "usage", "reading", "reading"]
          and W.sheet_kind("N2.3.2", "numeracy") is None)
    sec = W.prompt_section(SKILLS, "r1_literacy")
    check("the prompt names each writing group's sheet and says the passage rules do not apply to them",
          all(f'{lvl} ({c}): sheet_kind "{W.sheet_kind(c)}"' in sec for lvl, c in SKILLS.items()) and "passage_block null" in sec and "CHECKLIST" in sec and "dictation_sentences" in sec)
    check("...the writing topic must be the You Do's and not the teacher's model", "the one the group's You Do names" in sec and "must NOT be the topic" in sec)
    check("no writing group: no section (reading plans are unchanged)", W.prompt_section({"beginner": "L1.3.2", "progressor": "L2.6.1", "proficient": "L3.6.1"}, "r1_literacy") == ""
          and W.prompt_section({"progressor": "N2.3.2"}, "numeracy") == "")

    print("\nthe code makes each writing sheet a writing sheet")
    p = new_shape(SAMPLE)
    log = W.apply_writing_sheets(p, SKILLS, "r1_literacy")
    b = p["worksheets"]["beginner"]
    check("dictation: rebuilt as one numbered blank line per sentence; no sentence is printed for the child", [x["problem_hi"] for x in b["problems"]] == ["वाक्य 1", "वाक्य 2", "वाक्य 3", "वाक्य 4"]
          and [x["answer"] for x in b["problems"]] == SENTENCES and b["required_count"] == 4 and not any("मोहन" in x["problem_hi"] for x in b["problems"]))
    pr = p["worksheets"]["progressor"]
    check("composition: the passage and the bank question are removed", pr["passage_block"] is None and not any(x.get("from_bank") for x in pr["problems"]))
    check("...the writing task is problem 1, marked, with 8 lines and its topic; the part items follow, renumbered", pr["problems"][0].get("writing_task") and pr["problems"][0]["answer"] == "CHECKLIST"
          and pr["problems"][0]["answer_lines"] == 8 and pr["problems"][0]["topic_hi"] == "मेरा पसंदीदा खेल" and [x["number"] for x in pr["problems"]] == [1, 2, 3])
    check("...the checklist is kept (4 items)", len(pr["checklist"]) == 4)
    check("the log says what was changed", any("dictation sheet built from 4" in l for l in log) and any("passage removed" in l for l in log), log)
    check("the new-shape plan passes the writing checks", W.check_writing_sheets(p, SKILLS, "r1_literacy") == [], W.check_writing_sheets(p, SKILLS, "r1_literacy"))

    print("\nthe checks catch what is still wrong")
    q = copy.deepcopy(p)
    q["worksheets"]["progressor"]["checklist"] = q["worksheets"]["progressor"]["checklist"][:2]
    for blk in q["rotation_schedule"]["blocks"]:
        if blk.get("teach_group") == "proficient":
            blk["talking_points"]["i_do_hi"] = "मैं 'बारिश का एक दिन' पर लिखता/लिखती हूँ। हम मेले में गए।"
        if blk.get("teach_group") == "beginner":
            blk["talking_points"]["we_do_hi"] = "बोर्ड पर लिखें: चिड़िया पेड़ पर बैठी है।"
    iss = W.check_writing_sheets(q, SKILLS, "r1_literacy")
    check("a checklist of 2 items", any("checklist has 2" in i for i in iss), iss)
    check("the writing topic is the teacher's own model", any("«बारिश का एक दिन» is the teacher's own model" in i for i in iss), iss)
    check("a dictated sentence is on the board (the lesson)", any("«चिड़िया पेड़ पर बैठी है।» is in the lesson" in i for i in iss), iss)
    q2 = copy.deepcopy(p)
    q2["worksheets"]["beginner"]["problems"][0]["problem_hi"] = "मोहन ने किताब पढ़ी"
    check("a dictated sentence printed on the child's sheet (punctuation ignored)", any("printed on the child's sheet" in i for i in W.check_writing_sheets(q2, SKILLS, "r1_literacy")))
    q3 = copy.deepcopy(p)
    for blk in q3["rotation_schedule"]["blocks"]:
        if blk.get("teach_group") == "progressor":
            blk["talking_points"]["you_do_hi"] = "अब 'हमारा स्कूल' पर लिखिए।"
    check("the You Do names another topic than the sheet's", any("the You Do names the topic «हमारा स्कूल», but the sheet's topic is «मेरा पसंदीदा खेल»" in i for i in W.check_writing_sheets(q3, SKILLS, "r1_literacy")))
    q4 = copy.deepcopy(p)
    for blk in q4["rotation_schedule"]["blocks"]:
        if blk.get("teach_group") == "progressor":
            blk["talking_points"]["you_do_hi"] = "अब आप वर्कशीट पर दिए विषय पर 3-5 जुड़े वाक्य लिखेंगे।"
    check("...but a You Do that points to the sheet's topic ('दिए विषय पर') is fine (the first real run, 13 Nov)", not any("You Do" in i for i in W.check_writing_sheets(q4, SKILLS, "r1_literacy")))
    q5 = copy.deepcopy(p)
    q5["worksheets"]["proficient"]["problems"].append({"number": 9, "problem_hi": "खाली जगह में सही शब्द लिखें (फिर / क्योंकि): 'मैं देर से सोया ___ सुबह देर से उठा।'", "answer": "इसलिए", "answer_type": "box"})
    check("a fill-in answer that is none of the options it offers (the first real run: '(फिर / क्योंकि)' -> 'इसलिए')",
          any("the answer «इसलिए» is not one of the options it offers (फिर / क्योंकि)" in i for i in W.check_writing_sheets(q5, SKILLS, "r1_literacy")))
    q5["worksheets"]["proficient"]["problems"][-1]["answer"] = "फिर"
    check("...and one of them passes", not any("not one of the options" in i for i in W.check_writing_sheets(q5, SKILLS, "r1_literacy")))

    print("\nthe recorded L2.7.2 plan (old shape)")
    old = copy.deepcopy(SAMPLE)
    log = W.apply_writing_sheets(old, SKILLS, "r1_literacy")
    check("its comprehension sheets are left as they are (reshaping would leave questions about a removed passage)",
          old["worksheets"]["progressor"]["problems"] == SAMPLE["worksheets"]["progressor"]["problems"] and old["worksheets"]["progressor"].get("passage_block"))
    check("...its dictation sheet is fixed: the sentences come off the child's sheet", all(x["problem_hi"].startswith("वाक्य ") for x in old["worksheets"]["beginner"]["problems"]))
    iss = W.check_writing_sheets(old, SKILLS, "r1_literacy")
    check("...and the checks report what must be recorded again", any("progressor (composition): has a reading passage" in i for i in iss) and any("problem 1 is not the writing task" in i for i in iss), iss)

    print("\nreading plans are unchanged")
    r = copy.deepcopy(SAMPLE)
    W.apply_writing_sheets(r, {"beginner": "L1.3.2", "progressor": "L2.6.1", "proficient": "L3.6.1"}, "r1_literacy")
    check("nothing changes on a reading plan", r == SAMPLE)

    print("\nthe printed sheet")
    html_c = render_worksheet(p, "progressor", "L2.7.2", "जुड़े वाक्य", "connected sentences", "r1_literacy", str(TODAY))
    check("a composition sheet prints the checklist with tick boxes, and no passage", "जाँच सूची" in html_c and html_c.count('class="tick-box"') == 4 and "अनुच्छेद पढ़" not in html_c)
    check("...the task has lines, not a tracing grid", 'letter-cell' not in html_c.split("जाँच सूची")[0].split("मेरा पसंदीदा खेल")[-1][:2000])
    html_d = render_worksheet(p, "beginner", "L2.7.1", "श्रुतलेख", "dictation", "r1_literacy", str(TODAY))
    check("a dictation sheet says to listen and write on the numbered line, and prints none of the sentences", "सुनकर उसी नंबर की लाइन पर" in html_d and not any(s.rstrip("।") in html_d for s in SENTENCES))

    print("\nthe photo analysis")
    spec_c = W.vision_spec(p["worksheets"]["progressor"])
    vp = build_vision_prompt("progressor", "L2.7.2", "जुड़े वाक्य", p["worksheets"]["progressor"]["problems"], [], [1, 2], domain_id="r1_literacy", writing=spec_c)
    check("a composition is marked against its checklist, item by item (checklist_met)", "THE WRITING TASK" in vp and "checklist_met" in vp and "कम से कम 3 वाक्य" in vp and "Problem(s) 1 ask" in vp)
    vd = build_vision_prompt("beginner", "L2.7.1", "श्रुतलेख", p["worksheets"]["beginner"]["problems"], [], [1, 2], domain_id="r1_literacy", writing=W.vision_spec(p["worksheets"]["beginner"]))
    check("a dictation is marked word by word, matras included, with the wrong words listed", "SPELLING IS THE SKILL" in vd and "wrong_words" in vd)
    check("a reading sheet gets neither", "THE WRITING TASK" not in build_vision_prompt("progressor", "L2.6.1", "x", [{"number": 1, "answer": "a"}], [], [1], domain_id="r1_literacy"))
    child = {"summary": {}, "problems": [{"number": 1, "extracted_answer": "मेरा खेल...", "checklist_met": [True, True, False, True], "is_correct": False},
                                         {"number": 2, "extracted_answer": "राम और श्याम आए।", "is_correct": True},
                                         {"number": 3, "extracted_answer": "बारिश हुई बच्चे खेले", "is_correct": False}]}
    s = rescore(child, 3)
    check("a writing task counts one point per checklist item: 3 of 4 met + 1 of 2 items = 4 of 6", s["correct"] == 4 and s["total_problems"] == 6, s)
    child["problems"][0]["extracted_answer"] = ""
    check("...a blank task earns nothing, and still counts its 4 points", rescore(child, 3)["correct"] == 1 and rescore(child, 3)["total_problems"] == 6)

    print("\nthe teacher's first person")
    check("'मैं बोलती हूँ' and 'पढ़ा रही हूँ' become the neutral pair, once", hindi_style.neutral_first_person("मैं बोलती हूँ और पढ़ा रही हूँ।")[0] == "मैं बोलता/बोलती हूँ और पढ़ा रहा/रही हूँ।"
          and hindi_style.neutral_first_person("मैं बोलता/बोलती हूँ।")[0] == "मैं बोलता/बोलती हूँ।")
    pl = {"rotation_schedule": {"blocks": [{"teach_group": "beginner", "talking_points": {"i_do_hi": "मैं बोलती हूँ।"}}]},
          "worksheets": {"beginner": {"problems": [{"problem_hi": "'मैं गाती हूँ', रानी ने कहा।"}]}}}
    hindi_style.soften_plan(pl)
    check("...in the teacher's speech only: a girl in a worksheet story keeps her words", pl["rotation_schedule"]["blocks"][0]["talking_points"]["i_do_hi"] == "मैं बोलता/बोलती हूँ।"
          and "गाती हूँ" in pl["worksheets"]["beginner"]["problems"][0]["problem_hi"] and "गाता/" not in pl["worksheets"]["beginner"]["problems"][0]["problem_hi"])


async def flow():
    print("\nthrough plan generation (the AI is a fake)")
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "progressor", 4: "progressor", 5: "progressor", 6: "proficient", 7: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2", domain="r1_literacy") \
        if "domain" in _scratch.make_class.__code__.co_varnames else await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    reply = new_shape(SAMPLE)
    seen = {}

    class Fake:
        async def create(self, **kw):
            seen["prompt"] = kw["messages"][0]["content"]
            return NS(content=[NS(type="text", text=json.dumps(reply, ensure_ascii=False))], stop_reason="end_turn", usage=NS(input_tokens=6000, output_tokens=9000))
    real_client = anthropic.AsyncAnthropic
    anthropic.AsyncAnthropic = lambda **kw: NS(messages=Fake())
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            res = await plan_service.generate_dainik_yojana(db, teacher_id, "L2.7.2", "r1_literacy", TODAY)
        row = await db.fetchrow("SELECT plan_content, groups_snapshot FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'r1_literacy'", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        snap = json.loads(row["groups_snapshot"]) if isinstance(row["groups_snapshot"], str) else row["groups_snapshot"]
        skills = {lvl: (snap.get(lvl) or {}).get("target") for lvl in ("beginner", "progressor", "proficient")}
        check("(the fixture: the class's groups are on writing skills)", all(W.sheet_kind(c) in ("dictation", "composition", "formation") for c in skills.values() if c), skills)
        prompt = seen.get("prompt", "")
        check("the prompt carries the WRITING WORKSHEETS rules, and no bank passage for a writing group", "### WRITING WORKSHEETS" in prompt
              and not any(f"- {lvl} worksheet: passage_id" in prompt for lvl in ("progressor", "proficient") if W.sheet_kind(skills.get(lvl)) != "reading"))
        wb = pc["worksheets"]["beginner"]
        if W.sheet_kind(skills.get("beginner")) == "dictation":
            check("the stored beginner sheet is a dictation sheet with blank numbered lines", wb.get("sheet_kind") == "dictation" and all(x["problem_hi"].startswith("वाक्य ") for x in wb["problems"]))
        wp = pc["worksheets"]["progressor"]
        check("the stored progressor sheet is a composition: task first, checklist, no passage", wp.get("sheet_kind") == "composition" and wp["problems"][0].get("writing_task") and wp.get("passage_block") is None)
        check("the generation log names the writing sheets", "Writing sheet:" in out.getvalue())
    finally:
        anthropic.AsyncAnthropic = real_client
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


FLUENCY_SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "L2.5.1.json"), encoding="utf-8"))
FL_SKILLS = {"beginner": "L1.4.2", "progressor": "L2.5.1", "proficient": "L2.6.1"}
WORDS = ["बरसात", "इकट्ठा", "ज़रूरी", "सीमित", "किसान", "उपयोग"]


def fluency_shape(plan, skills=FL_SKILLS):
    """The L2.5.1 recorded plan with the Progressors' sheet written the NEW (reading-aloud) way, plus faults for the code to undo."""
    p = copy.deepcopy(plan)
    ws = p["worksheets"]["progressor"]
    ws["warmup_words"] = WORDS
    ws["problems"] = [{"number": n, "problem_hi": f"सवाल {n}", "answer": "x"} for n in range(1, 6)]           # 5 questions: too many for a practice sheet
    ws["problems"][3]["from_bank"] = True
    for b in p["rotation_schedule"]["blocks"]:
        if b.get("teach_group") == "progressor":
            b["talking_points"]["you_do_hi"] = "वर्कशीट का अभ्यास करें। मैं ऐप में दिखाए गए बच्चों को एक-एक मिनट सुनूँगा/सुनूँगी।"
    return p


def unit_fluency():
    print("\nreading aloud: a practice sheet (14 Nov)")
    check("the five reading-aloud skills are 'fluency'; they KEEP their passage (not in writing_levels)",
          [W.sheet_kind(c) for c in ("L1.5.1", "L2.5.1", "L2.5.2", "L3.5.1", "L3.5.2")] == ["fluency"] * 5 and W.writing_levels(FL_SKILLS, "r1_literacy") == set())
    sec = W.prompt_section(FL_SKILLS, "r1_literacy")
    check("the prompt: a READING-ALOUD section with warm-up words, three readings, pair reading, at most 3 questions, and no 'every child'",
          "### READING-ALOUD WORKSHEETS" in sec and 'progressor (L2.5.1): sheet_kind "fluency"' in sec and "warmup_words" in sec and "THREE times" in sec
          and "partner follows with a finger" in sec and "at most 3" in sec and "ऐप में दिखाए गए बच्चे" in sec and "Never 'हर बच्चे से'" in sec and "### WRITING WORKSHEETS" not in sec)
    check("...the expression sentences only for L2.5.2 / L3.5.2", "expression_sentences" not in sec and "expression_sentences" in W.prompt_section({"progressor": "L2.5.2"}, "r1_literacy"))
    check("...and a plan with writing AND reading-aloud groups gets both sections", all(h in W.prompt_section({"beginner": "L2.7.1", "progressor": "L2.5.1"}, "r1_literacy")
                                                                                     for h in ("### WRITING WORKSHEETS", "### READING-ALOUD WORKSHEETS")))
    p = fluency_shape(FLUENCY_SAMPLE)
    log = W.apply_writing_sheets(p, FL_SKILLS, "r1_literacy")
    ws = p["worksheets"]["progressor"]
    check("the code: practice, the passage kept, 3 questions with the bank's first, renumbered", ws["sheet_kind"] == "fluency" and ws["practice"] is True and ws.get("passage_block")
          and [x["problem_hi"] for x in ws["problems"]] == ["सवाल 4", "सवाल 1", "सवाल 2"] and [x["number"] for x in ws["problems"]] == [1, 2, 3] and ws["required_count"] == 3, (ws["problems"], log))
    check("...and the new-shape sheet passes the checks", W.check_writing_sheets(p, FL_SKILLS, "r1_literacy") == [], W.check_writing_sheets(p, FL_SKILLS, "r1_literacy"))
    q = copy.deepcopy(p)
    for b in q["rotation_schedule"]["blocks"]:
        if b.get("teach_group") == "progressor":
            b["talking_points"]["you_do_hi"] = "मैं हर बच्चे से अनुच्छेद पढ़वाकर गति जाँचूँगा/जाँचूँगी।"
    q["worksheets"]["progressor"]["warmup_words"] = WORDS[:2]
    iss = W.check_writing_sheets(q, FL_SKILLS, "r1_literacy")
    check("checks: a You Do that says 'हर बच्चे' (every child), and too few warm-up words", any("«हर बच्चे»" in i for i in iss) and any("2 warm-up word(s), not 6-8" in i for i in iss), iss)
    q2 = copy.deepcopy(p)
    q2["worksheets"]["progressor"]["passage_block"] = None
    check("...no passage to read three times", any("no passage to read aloud three times" in i for i in W.check_writing_sheets(q2, FL_SKILLS, "r1_literacy")))
    check("...an expression skill with no sentences to read with the marks", any("no 3-4 sentences" in i for i in W.check_writing_sheets(p, {**FL_SKILLS, "progressor": "L2.5.2"}, "r1_literacy")))
    old = copy.deepcopy(FLUENCY_SAMPLE)
    W.apply_writing_sheets(old, FL_SKILLS, "r1_literacy")
    check("the recorded L2.5.1 plan (old shape): marked as practice, its questions left as they are, and reported", old["worksheets"]["progressor"]["practice"] is True
          and old["worksheets"]["progressor"]["problems"] == FLUENCY_SAMPLE["worksheets"]["progressor"]["problems"]
          and any("no warm-up words" in i for i in W.check_writing_sheets(old, FL_SKILLS, "r1_literacy")))
    check("the photo analysis: a practice sheet, never marked", W.vision_spec(ws) == {"kind": "fluency", "practice": True})
    pe = copy.deepcopy(p)
    pe["worksheets"]["progressor"]["expression_sentences"] = ["क्या तुम आओगे?", "वाह, कितना सुंदर!", "हम घर गए।"]
    html = render_worksheet(pe, "progressor", "L2.5.2", "विराम पर रुककर पढ़ता है", "pauses", "r1_literacy", str(TODAY))
    check("the printed sheet: the practice note, the warm-up words with tick boxes, three reading ticks, pair reading, the expression sentences",
          "यह अभ्यास है; जाँच शिक्षक के साथ एक मिनट पढ़कर होगी" in html and all(w in html for w in WORDS) and html.count('class="reread-tick"') == 3
          and 'data-kind="pair-reading"' in html and "वाह, कितना सुंदर!" in html and html.count('class="tick-box"') == len(WORDS) + 3 + 3)
    html_r = render_worksheet(SAMPLE, "progressor", "L2.7.2", "x", "x", "r1_literacy", str(TODAY))
    check("...and none of it on any other sheet", 'data-kind="fluency-practice"' not in html_r and 'class="reread-tick"' not in html_r)
    check("the plan prompt: a pace for EVERY teach block, not only a re-teach", "Pace of EVERY teach block" in open(os.path.join(HERE, "..", "..", "prompts", "orchestrate.py"), encoding="utf-8").read())


async def flow_orf_sample():
    print("\nreading aloud: 4 children a day, those heard least recently first (14 Nov)")
    from app.services import review_service
    db = await _scratch.connect()
    rolls = list(range(1, 13))
    levels = {r: ("progressor", "progressor") for r in rolls}
    teacher_id, school = await _scratch.make_class(db, levels, grade="grade_2")
    try:
        class Fake:
            async def create(self, **kw):
                return NS(content=[NS(type="text", text=json.dumps(FLUENCY_SAMPLE, ensure_ascii=False))], stop_reason="end_turn", usage=NS(input_tokens=1, output_tokens=1))
        real_client = anthropic.AsyncAnthropic
        anthropic.AsyncAnthropic = lambda **kw: NS(messages=Fake())
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "L2.5.1", "r1_literacy", TODAY)
        finally:
            anthropic.AsyncAnthropic = real_client
        cov = lambda **k: review_service.get_review_coverage(db, teacher_id, TODAY, "r1_literacy", "progressor", channel="orf", **k)
        c0 = await cov()
        skill = c0["competency_id"]
        check("(the fixture: 12 Progressors on a reading-aloud skill)", len(c0["group_rolls"]) == 12 and W.sheet_kind(skill) == "fluency", (c0["group_rolls"], skill))
        s0 = c0["sample"]
        check("nobody heard yet: 4 children, the first by roll number, rotation on, 8 later", s0["size"] == 4 and s0["group_size"] == 12 and s0["rolls"] == [1, 2, 3, 4]
              and s0.get("rotation") is True and s0.get("later") == 8 and s0["mode"] == "sample", s0)
        from datetime import timedelta
        for r in (1, 2, 3, 4):           # heard two days ago
            await review_service.record_orf_assessment(db, teacher_id, TODAY - timedelta(days=2), {"roll_number": r, "cwpm": 40, "error_count": 2, "passage_id": None, "competency_id": skill})
        for r in (5, 6):                 # heard yesterday
            await review_service.record_orf_assessment(db, teacher_id, TODAY - timedelta(days=1), {"roll_number": r, "cwpm": 40, "error_count": 2, "passage_id": None, "competency_id": skill})
        s1 = (await cov())["sample"]
        check("then the never-heard come first (7-10), not those heard yesterday or before", s1["rolls"] == [7, 8, 9, 10], s1)
        s2 = (await cov(absent=[8]))["sample"]
        check("an absent child is skipped and the next in turn is taken", s2["rolls"] == [7, 9, 10, 11], s2)
        await review_service.record_orf_assessment(db, teacher_id, TODAY, {"roll_number": 7, "cwpm": 40, "error_count": 1, "passage_id": None, "competency_id": skill})
        s3 = (await cov())["sample"]
        check("a reading recorded TODAY does not reshuffle today's children (stable all day), and shows as done", s3["rolls"] == [7, 8, 9, 10] and s3["done"] == [7], s3)
        obs = (await review_service.get_review_coverage(db, teacher_id, TODAY, "r1_literacy", "progressor", channel="observed"))["sample"]
        check("observation sampling is unchanged (40%, at least 6, no rotation flag)", obs["size"] == 6 and "rotation" not in obs, obs)
    finally:
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


if __name__ == "__main__":
    unit()
    unit_fluency()
    asyncio.run(flow())
    asyncio.run(flow_orf_sample())
    print(f"\n{'ALL OK' if not failures else str(len(failures)) + ' FAILED'}")
    sys.exit(1 if failures else 0)
