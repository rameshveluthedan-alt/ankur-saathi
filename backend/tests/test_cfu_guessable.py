"""
A show-me that can be passed by guessing is not a check. Found on the fourth real block: BOTH questions were 'right or wrong?' lines with a WRONG line ('गलत, 83' and 'गलत, 63'): after a lesson about
mistakes a child can say 'wrong' twice without working anything out, and neither question made the child produce an answer.

    cd backend && AUTH_MODE=off python tests/test_cfu_guessable.py --env-file .env
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
import _scratch  # noqa: F401
import cfu_prompt
from app.services import cfu, plan_service

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


KB = {"progressor": {"competency_id": "N2.3.2", "name_en": "Adds two 2-digit numbers with regrouping (carry-over)", "name_hi": "x", "criteria_type": "computation",
                     "mistakes": [{"id": f"N2.3.2-M{i}", "name_hi": f"गलती {i}", "diagnostic_indicator": "d", "severity": "high", "frequency": "high"} for i in (1, 2, 3, 4)]}}
# the two questions of the real block (both lines wrong), a question that makes the child compute, and a correct line (a fair decoy)
W1 = {"kind": "spot_error", "question_hi": "बोर्ड पर देखें: 37 + 46 = 73। यह सही है या गलत?", "expected_hi": "गलत, 83", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "सही है, 73"}]}
W2 = {"kind": "spot_error", "question_hi": "बोर्ड पर देखें: 28 + 35 = 513। यह सही है या गलत?", "expected_hi": "गलत, 63", "listen_for": [{"misconception_id": "N2.3.2-M2", "wrong_answer_hi": "सही है, 513"}]}
CMP = {"kind": "compute", "question_hi": "बोर्ड पर देखें: 56 + 28। जवाब अपनी स्लेट पर लिखें।", "expected_hi": "84", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "74"}, {"misconception_id": "N2.3.2-M2", "wrong_answer_hi": "714"}]}
RIGHT = {"kind": "spot_error", "question_hi": "बोर्ड पर देखें: 49 + 35 = 84। यह सही है या गलत?", "expected_hi": "सही", "listen_for": [], "shows_hi": "बच्चा हासिल के साथ किया गया सही जोड़ पहचानता है"}


def run(items, kb=KB):
    pl = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": copy.deepcopy(items)}]}}
    lines, _ = cfu.clean_plan_cfu(pl, kb)
    return pl["rotation_schedule"]["blocks"][0]["cfu"], lines


async def main():
    print("what counts as a wrong line")
    check("a 'right or wrong?' question whose answer starts with गलत is a WRONG line; a correct line (सही), a compute question and junk are not", cfu._is_wrong_line(W1) and cfu._is_wrong_line(W2) and not cfu._is_wrong_line(RIGHT) and not cfu._is_wrong_line(CMP) and not cfu._is_wrong_line(None) and not cfu._is_wrong_line("x"))

    print("\nthe real block: two wrong lines")
    kept, lines = run([W1, W2])
    check("the second question is DROPPED: only the first is left, so the top-up will ask for another", [k["question_hi"][:16] for k in kept] == [W1["question_hi"][:16]], kept)
    check("the log says why, and what to write instead", any("question 2 dropped: both show-me questions would be wrong" in l and "WORKS OUT" in l for l in lines), lines)
    check("(the log line is short enough for the top-up to quote: it keeps the first 200 characters)", all(len(l.split(" | ")[0]) < 260 for l in lines if "dropped" in l))
    kept, _ = run([W1, W2, CMP])
    check("a compute question later in the list takes the second place: the block keeps the first line and the compute", [k["kind"] for k in kept] == ["spot_error", "compute"], [k["kind"] for k in kept])
    kept, _ = run([W2, W1, CMP])
    check("...whichever wrong line comes first", [k["kind"] for k in kept] == ["spot_error", "compute"] and kept[0]["question_hi"].startswith("बोर्ड पर देखें: 28"))

    C63 = {"kind": "compute", "question_hi": "बोर्ड पर देखें: 28 + 35। जवाब अपनी स्लेट पर लिखें।", "expected_hi": "63", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "53"}, {"misconception_id": "N2.3.2-M2", "wrong_answer_hi": "513"}]}
    kept, lines = run([W1, W2, C63])
    check("a question dropped for being the second wrong line claims NOTHING: a later question with the same right answer (63) is kept", [k["kind"] for k in kept] == ["spot_error", "compute"] and not any("same as question" in l for l in lines), (kept, lines))

    print("\nwhat is still allowed")
    kept, lines = run([CMP, W1])
    check("a compute question and a wrong line (the shape of the first three real blocks): both kept, nothing dropped", [k["kind"] for k in kept] == ["compute", "spot_error"] and not any("both show-me" in l for l in lines), lines)
    kept, lines = run([W1, RIGHT])
    check("a wrong line and a CORRECT line (a fair decoy): both kept, since 'wrong' is no longer a safe guess", [k["kind"] for k in kept] == ["spot_error", "spot_error"] and not any("both show-me" in l for l in lines), (kept, lines))
    kept, lines = run([RIGHT, W2])
    check("...in either order", len(kept) == 2 and not any("both show-me" in l for l in lines), lines)
    kept, _ = run([W1])
    check("a block with a single wrong line is left alone here (the 'fewer than two' logic asks for more)", len(kept) == 1)

    print("\nthe top-up is told why")
    sent = {}

    async def create(**kw):
        sent["prompt"] = kw["messages"][0]["content"]
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="{}")], usage=SimpleNamespace(input_tokens=1, output_tokens=1))

    async def noop(*a, **k):
        return None
    pl = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": [copy.deepcopy(W1), copy.deepcopy(W2)]}]}}
    lines, _ = cfu.clean_plan_cfu(pl, KB)
    real, plan_service.ai_budget = plan_service.ai_budget, SimpleNamespace(guard=noop, record_ctx=noop)
    try:
        await plan_service.topup_cfu(SimpleNamespace(messages=SimpleNamespace(create=create)), "m", pl, KB, ["progressor"], lines, {})
    finally:
        plan_service.ai_budget = real
    check("the request names the reason ('would be wrong right-or-wrong lines ... WORKS OUT an answer') and the answer already taken (83)", "both show-me questions would be wrong" in sent.get("prompt", "") and "WORKS OUT" in sent.get("prompt", "") and "The right answers of the questions above are 83" in sent.get("prompt", ""), sent.get("prompt", "")[-700:])

    print("\nthe prompt")
    check("the CFU rules ask for one question where the child works out an answer, and for a correct line if there are two right-or-wrong questions", "WORK OUT an answer" in cfu_prompt.CFU_RULES and "must be CORRECT (a fair decoy)" in cfu_prompt.CFU_RULES)
    check("the earlier CFU rules are still there", all(w in cfu_prompt.CFU_RULES for w in ("DIFFERENT right answers", "already written on the board", "Use NEW numbers")))

    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: a show-me cannot be passed by guessing 'wrong' twice: the second wrong line is dropped, the top-up asks for a question that makes the child work out an answer, and the prompt says so")


if __name__ == "__main__":
    asyncio.run(main())
