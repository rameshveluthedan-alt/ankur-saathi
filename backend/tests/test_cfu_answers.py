"""
Two show-me questions of one group must not share a right answer, and the prompts ask for it.
Found on the second real re-teach block: 56 + 28 and 49 + 35 were both 84, so a child who solved the first knew the second ("wrong, 84") without computing; the lesson repeated 47 + 36 as 36 + 47,
and the You Do wrote three sums of its own beside the worksheet's problems 1 to 6.

    cd backend && AUTH_MODE=off python tests/test_cfu_answers.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import copy
import os
import sys
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]
import _scratch  # noqa: F401  (sets the test environment)
import cfu_prompt
from orchestrate import RETEACH_MAIN_RULES
from app.services import cfu, plan_service

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


KB = {"progressor": {"competency_id": "N2.3.2", "name_en": "Adds two 2-digit numbers with regrouping (carry-over)", "name_hi": "हासिल के साथ दो अंकों का जोड़", "criteria_type": "computation",
                     "mistakes": [{"id": f"N2.3.2-M{i}", "name_hi": f"गलती {i}", "diagnostic_indicator": "d", "severity": "high", "frequency": "high"} for i in (1, 2, 3, 4)]}}
# the two questions of the real block, and a third that is fine
Q1 = {"kind": "compute", "question_hi": "बोर्ड पर देखें: 56 + 28। जवाब अपनी स्लेट पर लिखें।", "expected_hi": "84", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "74"}, {"misconception_id": "N2.3.2-M2", "wrong_answer_hi": "714"}]}
Q2 = {"kind": "spot_error", "question_hi": "बोर्ड पर देखें: 49 + 35 = 74। क्या यह सही है या गलत?", "expected_hi": "गलत, सही जवाब 84", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "सही है, 74"}]}
Q3 = {"kind": "spot_error", "question_hi": "बोर्ड पर देखें: 38 + 47 = 75। क्या यह सही है या गलत?", "expected_hi": "गलत, सही जवाब 85", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "सही है, 75"}]}


def run(items, kb=KB):
    pl = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": copy.deepcopy(items)}]}}
    lines, _ = cfu.clean_plan_cfu(pl, kb)
    return pl["rotation_schedule"]["blocks"][0]["cfu"], lines


async def main():
    print("the right answer of a question, worked out from the question itself")
    ra = lambda q: cfu.right_answer({"question_hi": q})
    check("a sum: 56 + 28 is 84; a difference and a product too", ra("56 + 28 कितना होगा?") == 84 and ra("78 − 35 कितना?") == 43 and ra("6 × 4 कितना?") == 24)
    check("a worked line to judge gives the REAL result, not the wrong one shown: '49 + 35 = 74' is 84, '47 + 25 = 612' is 72", ra("49 + 35 = 74। सही या गलत?") == 84 and ra("47 + 25 = 612: सही या गलत?") == 72)
    check("a question with no arithmetic has none, and nothing that is not a question is an error", ra("इकाई क्या है?") is None and cfu.right_answer(None) is None and cfu.right_answer("x") is None)
    check("Devanagari digits are read", ra("५६ + २८ कितना?") == 84)

    print("\nthe real block: two questions with the same right answer")
    kept, lines = run([Q1, Q2])
    check("the second question (49 + 35 = 74, answer 84) is DROPPED, because the first (56 + 28) is already 84", [k["question_hi"][:16] for k in kept] == [Q1["question_hi"][:16]], [k["question_hi"][:16] for k in kept])
    check("the log says which and why", any("question 2 dropped: its right answer 84 is the same as question 1's" in l for l in lines), lines)
    kept, lines = run([Q1, Q2, Q3])
    check("with a third question that has its own answer (85), the block keeps the first and the third", [k["question_hi"][-30:] for k in kept] == [Q1["question_hi"][-30:], Q3["question_hi"][-30:]] and [cfu.right_answer(k) for k in kept] == [84, 85], [cfu.right_answer(k) for k in kept])
    kept, lines = run([Q1, Q3])
    check("two questions with different answers are both kept, with nothing dropped (no false alarm)", len(kept) == 2 and not any("right answer" in l for l in lines), lines)
    kept, _ = run([Q2, Q1])
    check("it is the LATER question that goes, whichever kind it is", len(kept) == 1 and kept[0]["kind"] == "spot_error")
    wrong_key = {"kind": "compute", "question_hi": "38 + 47 कितना होगा?", "expected_hi": "84", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "75"}]}      # the answer key is wrong (the real result is 85)
    kept, lines = run([wrong_key, Q3])
    check("a question dropped for ANOTHER reason (a wrong answer key, real result 85) does not claim its answer: the next question with answer 85 is kept", [cfu.right_answer(k) for k in kept] == [85] and kept[0]["kind"] == "spot_error" and any("does not give the real result 85" in l for l in lines), (kept, lines))

    print("\nthe top-up is told which answers are taken")
    needs = {"progressor": {"need": 1, "existing": ["56 + 28"], "taken": [84], "avoid": [], "why": []}}
    text = cfu_prompt.render_topup(KB, {}, needs)
    check("the request says the right answers already used and asks for a DIFFERENT one", "The right answers of the questions above are 84" in text and "DIFFERENT right answer" in text, text[-420:])
    check("with no answers taken, nothing is said", "The right answers of the questions above" not in cfu_prompt.render_topup(KB, {}, {"progressor": {"need": 1, "existing": [], "taken": [], "avoid": [], "why": []}}))
    sent = {}

    async def create(**kw):
        sent["prompt"] = kw["messages"][0]["content"]
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="{}")], usage=SimpleNamespace(input_tokens=1, output_tokens=1))

    async def noop(*a, **k):
        return None
    real_budget, plan_service.ai_budget = plan_service.ai_budget, SimpleNamespace(guard=noop, record_ctx=noop)
    try:
        plan_json = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": [cfu_item for cfu_item in copy.deepcopy([Q1])]}]}}
        await plan_service.topup_cfu(SimpleNamespace(messages=SimpleNamespace(create=create)), "m", plan_json, KB, ["progressor"], [], {})
    finally:
        plan_service.ai_budget = real_budget
    check("the planner builds it from the questions it already has (56 + 28 gives 84) and sends it in the request", "The right answers of the questions above are 84" in sent.get("prompt", ""), sent.get("prompt", "")[-300:])

    print("\nthe prompts")
    check("the CFU rules ask for different right answers within one group", "DIFFERENT right answers" in cfu_prompt.CFU_RULES)
    check("the re-teach rules: the You Do writes NO problems of its own and sends the group to the worksheet by number", "do NOT write problems of your own" in RETEACH_MAIN_RULES and "वर्कशीट के सवाल" in RETEACH_MAIN_RULES and "a short try on their own" not in RETEACH_MAIN_RULES)
    check("...and no sum is repeated, the swapped one counts as the same (47 + 36 and 36 + 47)", "Never repeat a sum" in RETEACH_MAIN_RULES and "47 + 36 and 36 + 47 are the SAME sum" in RETEACH_MAIN_RULES)
    check("everything the earlier tests pin is still there", all(w in RETEACH_MAIN_RULES for w in ("show the mistake FIRST", "FIND AND FIX", "Name no child", "कल हमने क्या सीखा था", "NEW numbers", "ERASE it", "recall 2, I Do 6, We Do 7", "quietly", "never call out", "more than a quarter")))

    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: one group's show-me questions never share a right answer, the top-up is told which are taken, and the prompts ask for different sums and for a You Do that points to the worksheet")


if __name__ == "__main__":
    asyncio.run(main())
