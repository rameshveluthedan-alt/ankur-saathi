"""
Check for understanding (CFU): the model writes the questions, the CODE decides which ones a teacher may use.

A teacher acts on a CFU in front of the class (re-teaches, calls children to the table), so a wrong "right answer", a made-up mistake or an example the lesson already used would do harm.
Everything is therefore checked here and anything wrong is DROPPED, never repaired by guessing. What is checked, per question:

  * shape: a question, a short expected answer, a known kind, a sensible length;
  * arithmetic, by kind: compute (the expected answer is the real result), choose (the real result is one of the two offered and is the expected answer),
    spot_error (the worked line really IS wrong, and the expected answer gives the real result), and any worked line written in an expected answer is right;
  * mistake IDs: only IDs the knowledge base lists for THAT group's skill; the mistake's Hindi name is added from the knowledge base, not from the model;
  * no reuse: no operation (58 + 27) that a talking point or a worksheet problem of the same group already uses;
  * the skill's own rule: a skill "without regrouping" gets no question that needs a carry, "without borrowing" none that needs a borrow.

A question with no valid mistake ID is allowed only if it says what a right answer shows (shows_hi): that is how skills with no recorded mistakes are covered, and the screen says so.
See docs/CFU.md. Pure functions, no database, no AI.
"""
import re
from typing import Optional

KINDS = ("compute", "choose", "spot_error", "answer")
MIN_ITEMS, MAX_ITEMS = 2, 4
MAX_QUESTION_CHARS, MAX_EXPECTED_CHARS = 260, 160
NOTE_NO_MISTAKES_HI = "इस कौशल की सामान्य गलतियाँ ज्ञान-आधार में दर्ज नहीं हैं; ये प्रश्न कौशल का मुख्य विचार जाँचते हैं।"
NOTE_NO_MISTAKES_EN = "No common mistakes are recorded for this skill; these questions test its key idea."

_OPCH = r"[+\u2212\u2013\-\u00d7x*\u00f7]"                                    # + minus en-dash hyphen times x * divide
OP_RE = re.compile(rf"(?<![\d.])(\d+)\s*({_OPCH})\s*(\d+)(?![\d.])")
STATED_RE = re.compile(rf"(?<![\d.])(\d+)\s*({_OPCH})\s*(\d+)\s*=\s*(\d+)(?![\d.])")
NUM_RE = re.compile(r"(?<![\d.])\d+(?![\d.])")


def _norm_op(op: str) -> str:
    return {"\u2212": "-", "\u2013": "-", "-": "-", "\u00d7": "*", "x": "*", "*": "*", "\u00f7": "/", "+": "+"}.get(op, op)


def apply(a: int, op: str, b: int) -> Optional[int]:
    op = _norm_op(op)
    if op == "+": return a + b
    if op == "-": return a - b
    if op == "*": return a * b
    if op == "/": return a // b if b and a % b == 0 else None
    return None


def ops_in(text: str) -> set:
    """The operations a text uses, as (op, a, b); + and x ignore the order of the operands."""
    out = set()
    for a, op, b in OP_RE.findall(text or ""):
        o, a, b = _norm_op(op), int(a), int(b)
        out.add((o, *sorted((a, b))) if o in "+*" else (o, a, b))
    return out


def has_number(text: str, n: int) -> bool:
    return n is not None and re.search(rf"(?<![\d.]){n}(?![\d.])", text or "") is not None


def skill_rules(name_en: str) -> dict:
    t = (name_en or "").lower()
    return {"no_carry": any(w in t for w in ("without regrouping", "without carry", "without carrying")),
            "no_borrow": "without borrowing" in t or ("subtract" in t and "without regrouping" in t)}


def _digits(n: int) -> list:
    return [int(c) for c in str(n)][::-1]


def needs_carry(a: int, b: int) -> bool:
    return any(x + y >= 10 for x, y in zip(_digits(a), _digits(b)))


def needs_borrow(a: int, b: int) -> bool:
    da, db = _digits(a), _digits(b)
    return any(x < y for x, y in zip(da, db + [0] * (len(da) - len(db))))


def check_item(item, *, valid_ids: set, avoid: set, rules: dict) -> list:
    """The problems with one question (an empty list = fine)."""
    if not isinstance(item, dict):
        return ["not an object"]
    q, e, kind = (item.get("question_hi") or "").strip(), (item.get("expected_hi") or "").strip(), item.get("kind")
    problems = []
    if not q: problems.append("no question")
    if not e: problems.append("no expected answer")
    if kind not in KINDS: problems.append(f"unknown kind {kind!r}")
    if len(q) > MAX_QUESTION_CHARS: problems.append("question too long for a show-me")
    if len(e) > MAX_EXPECTED_CHARS: problems.append("expected answer too long to write on a slate")
    if problems:
        return problems
    lf = item.get("listen_for")
    if lf is not None and not isinstance(lf, list):
        return ["listen_for is not a list"]
    has_valid_mistake = any(isinstance(x, dict) and x.get("misconception_id") in valid_ids and str(x.get("wrong_answer_hi") or "").strip() for x in (lf or []))
    if not has_valid_mistake and not str(item.get("shows_hi") or "").strip():
        problems.append("it names no recorded mistake and does not say what a right answer shows")

    ops = OP_RE.findall(q)
    stated = [(int(a), _norm_op(op), int(b), int(c)) for a, op, b, c in STATED_RE.findall(q)]
    if kind == "compute":
        if not ops:
            problems.append("a compute question needs an operation such as 58 + 27")
        else:
            a, op, b = int(ops[0][0]), ops[0][1], int(ops[0][2])
            real = apply(a, op, b)
            if real is None or real < 0:
                problems.append("the operation has no whole-number result")
            elif not has_number(e, real):
                problems.append(f"the expected answer does not give the real result {real}")
            if stated:
                problems.append("a compute question must not state its own answer")
    elif kind == "choose":
        if not ops:
            problems.append("a choose question needs an operation such as 58 + 27")
        else:
            a, op, b = int(ops[0][0]), ops[0][1], int(ops[0][2])
            real = apply(a, op, b)
            nums = [int(n) for n in NUM_RE.findall(q)]
            for operand in (a, b):
                if operand in nums: nums.remove(operand)
            if real is None:
                problems.append("the operation has no whole-number result")
            elif real not in nums:
                problems.append(f"the real result {real} is not one of the offered answers")
            elif len(set(nums)) < 2:
                problems.append("a choose question offers two different answers")
            elif not has_number(e, real):
                problems.append(f"the expected answer does not give the real result {real}")
    elif kind == "spot_error":
        wrong = [(a, op, b, c) for a, op, b, c in stated if apply(a, op, b) != c]
        if not stated:
            problems.append("a spot_error question needs a worked line such as 47 + 25 = 612")
        elif not wrong:
            problems.append("a spot_error question states only correct lines: there is no mistake to find")
        elif not any(has_number(e, apply(a, op, b)) for a, op, b, _ in wrong if apply(a, op, b) is not None):
            problems.append("the expected answer does not give the real result of the wrong line")
    for a, op, b, c in ((int(a), op, int(b), int(c)) for a, op, b, c in STATED_RE.findall(e)):
        if apply(a, op, b) != c:
            problems.append(f"a worked line in the expected answer is wrong ({a} {op} {b} = {c})")

    if kind in ("compute", "choose", "spot_error"):
        used = ops_in(q)
        if used & avoid:
            problems.append("it reuses an example already used in this group's lesson or worksheet")
        for a, op, b in ((int(x), o, int(y)) for x, o, y in ops):
            o = _norm_op(op)
            if o == "+" and rules.get("no_carry") and needs_carry(a, b):
                problems.append(f"{a} + {b} needs a carry but the skill is 'without regrouping'")
            if o == "-" and rules.get("no_borrow") and needs_borrow(a, b):
                problems.append(f"{a} - {b} needs a borrow but the skill is 'without borrowing'")
    return problems


def _avoid_for(plan: dict, group: str, block: dict) -> set:
    """Operations this group's lesson and worksheet already use."""
    avoid = set()
    for text in (block.get("talking_points") or {}).values():
        avoid |= ops_in(str(text or ""))
    sheet = (plan.get("worksheets") or {}).get(group) or {}
    for p in sheet.get("problems") or []:
        avoid |= ops_in(str(p.get("problem_hi") or ""))
    avoid |= ops_in(str(((sheet.get("example_block") or {}).get("problem_hi")) or ""))
    return avoid


def clean_plan_cfu(plan: dict, cfu_kb: dict) -> tuple:
    """Keep only valid CFU questions in every teach block, add what the code knows (the mistakes' Hindi names, whether the skill has recorded mistakes), and say what was dropped.
    Returns (log lines, stats per group). Never raises for bad model output: a block with nothing valid simply gets an empty list."""
    lines, stats = [], {}
    for block in (plan.get("rotation_schedule") or {}).get("blocks") or []:
        if block.get("type") != "teach":
            block.pop("cfu", None)
            continue
        g = block.get("teach_group")
        kb = (cfu_kb or {}).get(g) or {}
        mistakes = {m["id"]: m for m in kb.get("mistakes") or []}
        avoid, rules = _avoid_for(plan, g, block), skill_rules(kb.get("name_en"))
        raw = block.get("cfu")
        written = len(raw) if isinstance(raw, list) else 0
        if not written:
            block["cfu"], block["cfu_grounded"] = [], bool(mistakes)
            stats[g] = {"written": 0, "kept": 0, "grounded_items": 0, "skill_has_mistakes": bool(mistakes)}
            lines.append(f"{g}: no CFU written")
            continue
        kept = []
        for n, item in enumerate(raw, 1):
            problems = check_item(item, valid_ids=set(mistakes), avoid=avoid, rules=rules)
            if problems:
                lines.append(f"{g} question {n} dropped: {'; '.join(problems)}")
                continue
            listen = []
            for x in item.get("listen_for") or []:
                mid, wrong = (x or {}).get("misconception_id"), str((x or {}).get("wrong_answer_hi") or "").strip()
                if mid in mistakes and wrong:
                    listen.append({"misconception_id": mid, "misconception_name_hi": mistakes[mid]["name_hi"], "detect_en": mistakes[mid]["diagnostic_indicator"], "wrong_answer_hi": wrong})
                else:
                    lines.append(f"{g} question {n}: removed a listen-for entry ({mid!r}: not a mistake listed for this skill, or no wrong answer given)")
            kept.append({"kind": item["kind"], "question_hi": item["question_hi"].strip(), "expected_hi": item["expected_hi"].strip(), "listen_for": listen,
                         "shows_hi": str(item.get("shows_hi") or "").strip(), "grounded": bool(listen)})
        if len(kept) > MAX_ITEMS:
            lines.append(f"{g}: {len(kept) - MAX_ITEMS} question(s) beyond the {MAX_ITEMS} allowed were left out")
        block["cfu"], block["cfu_grounded"] = kept[:MAX_ITEMS], bool(mistakes)
        if not mistakes:
            block["cfu_note_hi"], block["cfu_note_en"] = NOTE_NO_MISTAKES_HI, NOTE_NO_MISTAKES_EN
        if len(block["cfu"]) < MIN_ITEMS:
            lines.append(f"{g}: only {len(block['cfu'])} valid question(s) (wanted {MIN_ITEMS} or more)")
        stats[g] = {"written": written, "kept": len(block["cfu"]), "grounded_items": sum(1 for i in block["cfu"] if i["grounded"]), "skill_has_mistakes": bool(mistakes)}
    return lines, stats


def strip_cfu(plan: dict) -> None:
    """Remove every unchecked CFU (used if the check itself failed: nothing unchecked may reach a teacher)."""
    for block in (plan.get("rotation_schedule") or {}).get("blocks") or []:
        for k in ("cfu", "cfu_grounded", "cfu_note_hi", "cfu_note_en"):
            block.pop(k, None)
