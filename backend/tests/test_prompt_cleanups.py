"""
Prompt v2, step 6: the clean-ups. Concrete "HOW TO WRITE THE PLAN" rules in place of generic principles; no roll numbers and no peer monitors in
the request; the observation reminders and the weekly-plan note written by code, not asked of the model; the old unmetered orchestrator and the
unused prompt templates gone. The AI is a fake: no paid call.

    python backend/tests/test_prompt_cleanups.py --env-file backend/.env
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
ROOT = os.path.join(HERE, "..", "..")
import _scratch
import anthropic
from app.services import plan_service
import orchestrate
from orchestrate import build_system_prompt

TODAY = date.today()
SEEDS = os.path.join(ROOT, "db", "seeds", "sample_plans")
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("the system prompt")
num = build_system_prompt("numeracy", cfu=True)
check("concrete rules: HOW TO WRITE THE PLAN, with the modality rule and 'no child named'", all(w in num for w in ("HOW TO WRITE THE PLAN", '"observed" → the teacher watches', "Children are named nowhere")))
check("the generic principles the model could not act on are gone", "Noise-robust" not in num and "Offline-friendly" not in num)
check("no peer monitors and no observation reminders asked for", "peer_monitors" not in num and "observation_reminders_hi" not in num)
check("the model is no longer asked for the content item or the weekly-plan note", "Do NOT write an item about the retrieved content" in num and "representative plan" not in num)

print("from the review of the 12 real plans (20 Nov)")
import hindi_style as hs
check("the rules: no gendered 'मैं' even inside quotes, no self-corrections, plain Hindi words",
      all(w in num for w in ("This holds INSIDE QUOTES too", "'देखिए, अब हम रंग से छाँटते हैं'", "never correct yourself inside a script", "जीभ घुमाने वाला वाक्य")))
check("the rules: no length but PART C's, and a short You Do only STARTS the task",
      "Never write a length other than PART C's" in num and "A You Do of 5 minutes or less STARTS the group's task" in num)
def tw(text, key="i_do_hi"):
    return hs.check_teacher_text({"rotation_schedule": {"blocks": [{"type": "teach", "talking_points": {key: text}}]}})
check("the teacher's own demonstration in quotes is flagged: छाँटूँगा, छाँटूँगी, छाँट रही हूँ, रखता हूँ",
      all(tw(t) for t in ("कहें: 'मैं पहले आकार से छाँटूँगा।'", "'देखें, मैं रंग के आधार पर छाँट रही हूँ।'", "'मैं आकृति से छाँटूँगी।'", "'मैं इसे यहाँ रखता हूँ।'")))
check("a sentence WRITTEN on the board for the children is not flagged", not tw("बोर्ड पर लिखें: 'मैं रोज़ पैदल जाता हूँ।'") and not tw("वाक्य पढ़ें: 'मैं स्कूल जाता हूँ।'"))
check("the reviewed form is not flagged", not tw("'देखिए, अब हम रंग से छाँटते हैं।'"))
check("the teacher's own quoted words are rewritten to the neutral 'हम' form (the model still wrote some after the rule)",
      [hs.neutral_quotes(t)[0] for t in ("कहें: 'अब मैं रंग से छाँटता हूँ, फिर आकृति से।'", "'देखें, मैं छाँट रही हूँ।'", "'मैं आकृति से छाँटूँगी।'")]
      == ["कहें: 'अब हम रंग से छाँटते हैं, फिर आकृति से।'", "'देखें, हम छाँट रहे हैं।'", "'हम आकृति से छाँटेंगे।'"])
check("...but not a sentence written on the board for the children", hs.neutral_quotes("बोर्ड पर लिखें: 'मैं रोज़ पैदल जाता हूँ।'") == ("बोर्ड पर लिखें: 'मैं रोज़ पैदल जाता हूँ।'", 0))
pl = {"rotation_schedule": {"blocks": [{"type": "teach", "talking_points": {"i_do_hi": "कहें: 'मैं रंग से छाँटूँगा।'"}}]}, "worksheets": {"beginner": {"passage_block": {"text": "मैं स्कूल जाता हूँ।"}}}}
check("...in a whole plan: the teacher's lines only, never a passage", hs.neutral_quotes_in_plan(pl) == 1 and "हम रंग से छाँटेंगे" in pl["rotation_schedule"]["blocks"][0]["talking_points"]["i_do_hi"]
      and pl["worksheets"]["beginner"]["passage_block"]["text"] == "मैं स्कूल जाता हूँ।" and not hs.check_teacher_text(pl))
from app.services import writing_sheets as wsx
fl = wsx.prompt_section({"progressor": "L2.5.1"}, "r1_literacy")
check("the fluency section: a short block asks only for the warm-up words and ONE reading, the rest at the group's place next block", "A SHORT block" in fl and "ONE reading" in fl)
plan = {"rotation_schedule": {"blocks": [{"type": "teach", "duration_minutes": 22}, {"type": "transition", "duration_minutes": 0}, {"type": "transition", "duration_minutes": 2}]},
        "classroom_management": {"independent_activities_hi": {"beginner": "a", "proficient": "c", "dakshta": "c"}}}
log = plan_service.tidy_plan_structure(plan)
check("a 0-minute block and an unknown group key ('dakshta') are removed, and logged",
      [b["duration_minutes"] for b in plan["rotation_schedule"]["blocks"]] == [22, 2] and "dakshta" not in plan["classroom_management"]["independent_activities_hi"] and len(log) == 2, log)
check("an odd plan does nothing", plan_service.tidy_plan_structure({}) == [] and plan_service.tidy_plan_structure(None) == [])

print("the observation reminders, by code")
check("one line per observed group, in group order, in the screen's words",
      plan_service.observation_reminders({"progressor": "observed", "beginner": "observed", "proficient": "reading"})
      == ["शुरुआती समूह: स्वतंत्र अभ्यास (तुम करो) के दौरान बच्चों को काम करते हुए देखें, फिर हर बच्चे के लिए A / PA / NA चुनें।",
          "प्रगतिशील समूह: स्वतंत्र अभ्यास (तुम करो) के दौरान बच्चों को काम करते हुए देखें, फिर हर बच्चे के लिए A / PA / NA चुनें।"])
check("none observed: an empty list", plan_service.observation_reminders({"beginner": "reading"}) == [] and plan_service.observation_reminders(None) == [])

print("the old code")
src = open(os.path.join(ROOT, "prompts", "orchestrate.py"), encoding="utf-8").read()
check("the unmetered generate_dainik_yojana (old model hard-coded) is gone from orchestrate.py", "async def generate_dainik_yojana" not in src and "claude-sonnet-4-6" not in src)
check("the unused prompt templates are gone", not os.path.exists(os.path.join(ROOT, "prompts", "templates", "dainik_yojana_system.md")))
check("the unused assessment fields are gone from the context", not hasattr(orchestrate.OrchestrationContext, "orf_roll_numbers"))


class Fake:
    def __init__(self, plan):
        self.prompts, self.plan = [], plan

    async def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(self.plan, ensure_ascii=False))], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=100, output_tokens=100))


async def main():
    db = await _scratch.connect()
    levels = {r: (lv, lv) for r, lv in {11: "beginner", 12: "beginner", 23: "progressor", 24: "progressor", 37: "proficient", 38: "proficient"}.items()}
    teacher_id, school = await _scratch.make_class(db, levels, grade="grade_2")
    real = anthropic.AsyncAnthropic
    try:
        print("\nthe request and the saved plan, with a stand-in model")
        plan = json.load(open(os.path.join(SEEDS, "N2.3.2.json"), encoding="utf-8"))
        plan["review_prompts"]["observation_reminders_hi"] = ["the model's own reminder"]
        fake = Fake(plan)
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY, session_minutes=90)
        user = fake.prompts[-1]
        check("no roll number in the request", "Roll" not in user and not any(f" {r}," in user or f"[{r}" in user for r in (11, 12, 23, 24, 37, 38)), [l for l in user.splitlines() if "Roll" in l][:3])
        check("the group counts are still there", "— 2 children" in user)
        check("PART D asks for no peer monitors; PART E says the system writes the reminders", "peer monitors" not in user and "writes the observation reminders" in user)
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        check("a written maths skill: no observation reminder (the model's own is replaced)", pc["review_prompts"]["observation_reminders_hi"] == [])
        items = pc["explainability"]["items"]
        res = [it for it in items if it.get("id") == "resources"]
        check("the 'Why this plan?' resources item carries the weekly-plan note, written by code", len(res) == 1 and "**Weekly plan:**" in res[0]["body_en"] and "साप्ताहिक योजना" in res[0]["body_hi"])

        plan2 = json.load(open(os.path.join(SEEDS, "N0.1.1.json"), encoding="utf-8"))
        fake2 = Fake(plan2)
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake2)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N0.1.1", "numeracy", TODAY + timedelta(days=1), session_minutes=90)
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=1))
        pc2 = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        rem = pc2["review_prompts"]["observation_reminders_hi"]
        check("an observed skill (N0.1.1): a reminder for each observed group, from code", len(rem) >= 1 and all("A / PA / NA" in r for r in rem), rem)
    finally:
        anthropic.AsyncAnthropic = real
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: concrete rules, no roll numbers, reminders and the weekly-plan note by code, the old code gone")
