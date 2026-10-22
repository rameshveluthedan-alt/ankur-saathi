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


def _verdict(e: str) -> tuple:
    """(says_right, says_wrong) for a key such as 'गलत', 'सही है', 'सही नहीं है' (NOT right), or 'गलत; सही उत्तर 543'. The phrase 'सही उत्तर' (the correct answer) is not a verdict."""
    t = re.sub(r"सही (उत्तर|जवाब|योग|अंतर|गुणनफल)", " ", e or "")
    negated = "सही नहीं" in t or "ठीक नहीं" in t
    return ("सही" in t and not negated), ("गलत" in t or negated)


def _prep(text: str) -> str:
    """A hyphen between digits with no spaces ('25-25 pencils in each of 4 packets', '10-20') is a pair or a range, NOT subtraction: it is made unmatchable. (The broad run read '25-25' as 25 minus 25 = 0.)
    A real subtraction is written with the minus sign or with spaces around the hyphen."""
    return re.sub(r"(?<=\d)-(?=\d)", "\u2010", text or "")


EXPR_RE = re.compile(rf"(?<![\d.])\d+(?:\s*{_OPCH}\s*\d+)+(?![\d.])")


def _eval_expr(expr: str) -> Optional[int]:
    """The value of a chain such as '2 + 2 + 2 + 2' or '3 x 12 - 10', with multiplication and division first. None if a division is not exact."""
    toks = re.findall(r"\d+|[+\u2212\u2013\-\u00d7x*\u00f7]", expr)
    vals, adds, i = [int(toks[0])], [], 1
    while i + 1 < len(toks):
        op, n = _norm_op(toks[i]), int(toks[i + 1])
        if op in "*/":
            r = apply(vals[-1], op, n)
            if r is None:
                return None
            vals[-1] = r
        else:
            adds.append(op)
            vals.append(n)
        i += 2
    total = vals[0]
    for op, v in zip(adds, vals[1:]):
        total = total + v if op == "+" else total - v
    return total


def _check_expression_choice(exprs: list, vals: list, q: str, e: str) -> Optional[str]:
    """A choice BETWEEN expressions: '5 + 5 + 5 is which product: 3 x 5 or 5 x 5?'. The first expression is the one the question starts from and the others are the options; or, with two expressions, a number the
    question names ('which equals 15?'). The option equal in value is the right one: the answer must not give a wrong option instead."""
    squash = lambda x: re.sub(r"\s+", "", x).replace("\u2212", "-").replace("\u2013", "-").replace("x", "\u00d7").replace("*", "\u00d7")
    es = squash(e)
    if len(exprs) >= 3 and None not in vals:
        target, options = vals[0], list(zip(exprs[1:], vals[1:]))
    else:
        outside = [int(n) for n in NUM_RE.findall(EXPR_RE.sub(" ", q))]
        hits = [v for v in vals if v is not None and v in outside]
        if len(hits) != 1:
            return None
        target, options = hits[0], list(zip(exprs, vals))
    right = [x for x, v in options if v == target]
    if not right:
        return f"no option in the question equals {target}"
    if len(right) > 1:
        return None
    wrong = [x for x, v in options if v != target]
    if squash(right[0]) not in es and any(squash(w) in es for w in wrong):
        return f"the answer gives a wrong option: {right[0]} is the one equal to {target}"
    return None


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
    for a, op, b in OP_RE.findall(_prep(text)):
        o, a, b = _norm_op(op), int(a), int(b)
        out.add((o, *sorted((a, b))) if o in "+*" else (o, a, b))
    return out


def has_number(text: str, n: int) -> bool:
    """The number as digits, or as its Hindi word (चार for 4): multiplication-table answers and some counting answers are written in words."""
    if n is None:
        return False
    if re.search(rf"(?<![\d.]){n}(?![\d.])", text or ""):
        return True
    try:
        from app.services.hindi_numbers import name
        word = name(n)
        return bool(word) and word in (text or "")
    except Exception:
        return False


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


_BIG = ("\u092c\u0921\u093c\u093e", "\u092c\u0921\u093c\u0940", "\u092c\u0921\u093c\u0947", "\u0905\u0927\u093f\u0915")                   # bada, badi, bade, adhik (bigger / more)
_SMALL = ("\u091b\u094b\u091f\u093e", "\u091b\u094b\u091f\u0940", "\u091b\u094b\u091f\u0947")                                       # chhota, chhoti, chhote
_MORE = ("\u091c\u093c\u094d\u092f\u093e\u0926\u093e", "\u091c\u094d\u092f\u093e\u0926\u093e", "\u0905\u0927\u093f\u0915")    # zyada (two spellings), adhik
_FEWER, _EQUAL = "\u0915\u092e", "\u092c\u0930\u093e\u092c\u0930"                                                               # kam, barabar


_ARITH_INTENT = ("जोड़", "घटा", "गुणा", "भाग", "योग", "अंतर", "मिलाकर", "बचे", "बचा", "बची", "बचीं", "बचेंगे", "बचेगा", "कुल कितने")


def _has_arith_intent(q: str) -> bool:
    """Does the question ask for arithmetic (add, subtract, multiply, share, how many are left)? Judged from the words of the question, NOT from the skill's type: patterns and shapes are typed
    'computation' in the knowledge base but contain no arithmetic, and the first broad run dropped good pattern questions for 'needing a worked line'."""
    return any(w in q for w in _ARITH_INTENT)


def _plausible(q: str, e: str) -> Optional[str]:
    """Arithmetic written in WORDS (a word problem: 50 rupees, 20 spent, how many are left?) has no sum to check, but the answer must at least BE a sum, difference or product of numbers
    in the question (two numbers, or three for a two-step problem). It does not prove the answer right: it catches the answers that are not even possible."""
    from itertools import permutations
    nums = []
    for n in NUM_RE.findall(q):
        if int(n) not in nums:
            nums.append(int(n))
    nums = nums[:6]
    if not nums:
        return "arithmetic written in words with no numbers in it cannot be checked"
    m = re.search(r"(?<![\d.])\d+(?![\d.])", e or "")
    if not m:
        return None                                              # an answer in words cannot be judged here
    n, results = int(m.group(0)), set()
    for a, b in permutations(nums, 2):
        results |= {a + b, a - b, a * b}
        if b and a % b == 0:
            results.add(a // b)
    for a, b, c in permutations(nums, 3):
        results |= {a + b + c, a + b - c, a - b - c, a * b + c, a * b - c, a * (b + c), (a + b) * c, (a - b) * c, a + b * c, a - b * c}
    return None if n in results else f"the answer {n} is not a sum, difference or product of the numbers in the question"


def _two_numbers(q: str):
    nums = [int(n) for n in NUM_RE.findall(q)]
    return nums if len(nums) == 2 else None


def _is_comparison(q: str) -> bool:
    return _two_numbers(q) is not None and (any(w in q for w in _BIG + _SMALL) or (any(w in q for w in _MORE) and _FEWER in q and _EQUAL in q))


def _check_comparison(q: str, e: str) -> Optional[str]:
    """A plain comparison of two numbers (no sum): 'which is bigger, 47 or 74?' and 'more, fewer or equal?'. Returns the problem, or None when fine or not a comparison."""
    nums = _two_numbers(q)
    if not nums:
        return None
    a, b = nums
    if any(w in q for w in _MORE) and _FEWER in q and _EQUAL in q:           # the three-way question: only 'equal' can be checked from the numbers alone
        if a == b and _EQUAL not in e:
            return "the two amounts are equal but the expected answer is not 'barabar'"
        if a != b and _EQUAL in e:
            return "the two amounts differ but the expected answer says 'barabar'"
        return None
    if "\u0915\u094c\u0928" not in q:                                          # 'kaun' (which): only a question that really asks WHICH is bigger or smaller is verified
        return None
    asks_big, asks_small = any(w in q for w in _BIG), any(w in q for w in _SMALL)
    if a == b or asks_big == asks_small:
        return None
    want, other = (max(a, b), min(a, b)) if asks_big else (min(a, b), max(a, b))
    if not has_number(e, want) or has_number(e, other):
        return f"the expected answer should be {want}, the {'bigger' if asks_big else 'smaller'} of {a} and {b}"
    return None


_PAUSE_EXPECTED = re.compile(r"^\s*(\d+)\s*\(([^()/]*?)/")


def _check_pause_number(e: str) -> Optional[str]:
    """The expected answer '3 (बच्चे स्कूल से / घर आए)' names a pause by the NUMBER of the word it follows: the number must be the count of words BEFORE the slash. The prompt asks for this format
    (children show a number on their fingers instead of copying a sentence), and the second literacy run wrote '2 (बच्चे स्कूल से / घर आए)': three words before the pause, so the right number was 3."""
    m = _PAUSE_EXPECTED.match(e or "")
    if not m:
        return None
    words = [w for w in re.sub(r"[\u0964,.?!;:'\"\u2018\u2019\u201c\u201d]", " ", m.group(2)).split() if w]
    if words and int(m.group(1)) != len(words):
        return f"the pause number is {m.group(1)} but the words before the slash in the answer are {len(words)}"
    return None


_ORDINAL_WORD = re.compile(r"(पहला|दूसरा|तीसरा|चौथा|पाँचवाँ|पांचवां)\s+शब्द")
_ORDINALS = {"पहला": 1, "दूसरा": 2, "तीसरा": 3, "चौथा": 4, "पाँचवाँ": 5, "पांचवां": 5}
_QUOTED = re.compile(r"['\u2018\u201c]([^'\u2019\u201d]+)['\u2019\u201d]")


def _words(text: str) -> list:
    return [w for w in re.sub(r"[।,.?!;:'\"\u2018\u2019\u201c\u201d()/\-\u2013\u2014]", " ", text or "").split() if w]


def _check_word_counts(q: str, e: str) -> Optional[str]:
    """Counting words is a very common literacy show-me, and the model miscounts: the second literacy run wrote the answer 2 for 'बच्चे स्कूल से / घर आए' (three words before the pause)
    and the third wrote 4 for 'हम सब मिलकर / ...' (three words). Code counts reliably, so three shapes are verified against the sentence in the question:
    'how many words' in a quoted sentence; 'how many words' before the first ' / ' of a split sentence; and 'the third word' of a quoted sentence."""
    if "शब्द" not in q:
        return None
    quoted = _QUOTED.findall(q)
    if "कितने शब्द" in q:
        m = re.match(r"^\s*(\d+)\b", e or "")
        if not m:
            return None
        n = int(m.group(1))
        if " / " in q and any(w in q for w in ("हिस्से", "विराम", "रुक", "ठहर")):
            before = q[:q.find(" / ")]
            cut = max(before.rfind(c) for c in "'\u2018\u201c(:")
            words, where = (_words(before[cut + 1:]) if cut != -1 else []), "before the first slash"
        elif quoted and ("कुल" in q or "में कितने शब्द" in q) and not any(w in q for w in ("वाक्यांश", "हिस्से", "भाग", "पहले", "रुक", "विराम", "ठहर", "एक साथ")):
            words, where = _words(quoted[0]), "in the quoted sentence"
        else:
            return None
        if words and n != len(words):
            return f"the answer says {n} but there are {len(words)} words {where}"
        return None
    m = _ORDINAL_WORD.search(q)
    if m and quoted:
        words, k = _words(quoted[0]), _ORDINALS[m.group(1)]
        if len(words) >= k and words[k - 1] not in (e or ""):
            return f"the answer does not give word number {k} of the sentence, which is {words[k - 1]}"
    return None


def check_item(item, *, valid_ids: set, avoid: set, rules: dict, strict: bool = True, compare: bool = True) -> list:
    """The problems with one question (an empty list = fine).
    strict: a NUMERACY skill. A question that asks for arithmetic (add, subtract, multiply, how many are left) must contain the operation it claims, so it can be checked; arithmetic written in words is checked for
    plausibility (see _plausible). A question that asks for NO arithmetic (a pattern, a shape) is kept as it is, whatever the skill's type.
    compare: False for LITERACY, where the numbers in a question are labels ('sentence 1 and sentence 2'), not quantities."""
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

    qn, en = _prep(q), _prep(e)
    ops = OP_RE.findall(qn)
    stated = [(int(a), _norm_op(op), int(b), int(c)) for a, op, b, c in STATED_RE.findall(qn)]
    exprs = [m.group(0) for m in EXPR_RE.finditer(qn)]
    vals = [_eval_expr(x) for x in exprs]
    if kind == "compute":
        if not exprs:
            if strict and _has_arith_intent(q):
                why = _plausible(qn, e)
                if why:
                    problems.append(why)
        else:
            real = vals[-1]                          # the expression the question ASKS about is the last: '2 + 2 + 2 + 2 as a product: 4 x 2 = ?'
            if real is None or real < 0:
                problems.append("the operation has no whole-number result")
            elif not has_number(e, real):
                problems.append(f"the expected answer does not give the real result {real}")
            if stated:
                problems.append("a compute question must not state its own answer")
    elif kind == "choose":
        if not exprs:
            if strict and not _is_comparison(q) and _has_arith_intent(q):
                why = _plausible(qn, e)
                if why:
                    problems.append(why)
        elif len(exprs) >= 2:
            why = _check_expression_choice(exprs, vals, qn, e)
            if why:
                problems.append(why)
        else:
            real = vals[0]
            nums = [int(n) for n in NUM_RE.findall(qn)]
            for operand in [int(n) for n in NUM_RE.findall(exprs[0])]:
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
            if strict and _has_arith_intent(q):      # a word problem with a child's answer but no equation: the correct answer in the key must at least be possible
                why = _plausible(qn, e)
                if why:
                    problems.append(why)
        elif not wrong:                               # every line is right: a 'right or wrong?' question with a right line is a fair decoy, but the answer must say 'right'
            says_right, says_wrong = _verdict(e)
            if says_wrong and not says_right:
                problems.append("every line in the question is correct, but the answer says it is wrong")
            elif not says_right and not says_wrong:
                problems.append("every line in the question is correct, and the answer does not say it is right")
        else:                                         # a line that IS wrong: the key must say so; the real result is needed only when the question asks the child for the correct answer
            says_right, says_wrong = _verdict(e)
            asks_correct = any(w in q for w in ("सही उत्तर", "सही जवाब", "सही योग", "सही अंतर", "सही गुणनफल"))
            if says_right and not says_wrong:
                problems.append("the line in the question is wrong, but the answer says it is right")
            elif (asks_correct or not says_wrong) and not any(has_number(e, apply(a, op, b)) for a, op, b, _ in wrong if apply(a, op, b) is not None):
                problems.append("the expected answer does not give the real result of the wrong line")
    if not ops and not stated and compare:           # no sum in the question: a plain comparison of quantities can still be verified
        cmp_problem = _check_comparison(q, e)
        if cmp_problem:
            problems.append(cmp_problem)
    for a, op, b, c in ((int(a), op, int(b), int(c)) for a, op, b, c in STATED_RE.findall(en)):
        if apply(a, op, b) != c:
            problems.append(f"a worked line in the expected answer is wrong ({a} {op} {b} = {c})")
    pause = _check_pause_number(e)
    if pause:
        problems.append(pause)
    counted = _check_word_counts(q, e)
    if counted:
        problems.append(counted)

    if kind in ("compute", "choose", "spot_error"):
        used = ops_in(q)
        if used & avoid:
            problems.append("it reuses an example already used in this group's lesson (I Do, We Do or You Do)")
        for a, op, b in ((int(x), o, int(y)) for x, o, y in ops):
            o = _norm_op(op)
            if o == "+" and rules.get("no_carry") and needs_carry(a, b):
                problems.append(f"{a} + {b} needs a carry but the skill is 'without regrouping'")
            if o == "-" and rules.get("no_borrow") and needs_borrow(a, b):
                problems.append(f"{a} - {b} needs a borrow but the skill is 'without borrowing'")
    return problems


def _avoid_for(plan: dict, group: str, block: dict) -> tuple:
    """(operations this group's LESSON uses (I Do, We Do, You Do), operations its WORKSHEET uses). A question repeating a lesson example is dropped: the answer was shown seconds earlier.
    One repeating a worksheet problem is KEPT and noted: a skill with few possible examples (single-digit sums: 45 pairs; multiplication tables) cannot avoid it, and the first broad run lost
    most of a block to it."""
    lesson, worksheet = set(), set()
    for text in (block.get("talking_points") or {}).values():
        lesson |= ops_in(str(text or ""))
    sheet = (plan.get("worksheets") or {}).get(group) or {}
    for p in sheet.get("problems") or []:
        worksheet |= ops_in(str(p.get("problem_hi") or ""))
    worksheet |= ops_in(str(((sheet.get("example_block") or {}).get("problem_hi")) or ""))
    return lesson, worksheet


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
        (avoid, ws_ops), rules = _avoid_for(plan, g, block), skill_rules(kb.get("name_en"))
        strict = kb.get("criteria_type") != "literacy"                       # every numeracy skill: judged by what the question ASKS (arithmetic words), not by the skill's type
        compare = kb.get("criteria_type") != "literacy"                      # numbers in a literacy question are labels, not quantities
        raw = block.get("cfu")
        if not isinstance(raw, list) or not raw:                              # a model that put it among the talking points instead
            tp = block.get("talking_points")
            alt = tp.pop("cfu", None) if isinstance(tp, dict) else None
            if isinstance(alt, list) and alt:
                raw = alt
                lines.append(f"{g}: the questions were under talking_points: moved")
        written = len(raw) if isinstance(raw, list) else 0
        if not written:
            keys_written = ", ".join(sorted(block)[:14])                       # before the code adds its own keys below
            block["cfu"], block["cfu_grounded"] = [], bool(mistakes)
            stats[g] = {"written": 0, "kept": 0, "grounded_items": 0, "skill_has_mistakes": bool(mistakes)}
            lines.append(f"{g}: no CFU written (the model's block has: {keys_written})")
            continue
        kept = []
        for n, item in enumerate(raw, 1):
            problems = check_item(item, valid_ids=set(mistakes), avoid=avoid, rules=rules, strict=strict, compare=compare)
            if problems:
                qs, es = (item.get("question_hi") or "") if isinstance(item, dict) else "", (item.get("expected_hi") or "") if isinstance(item, dict) else ""
                lines.append(f"{g} question {n} dropped: {'; '.join(problems)} | «{str(qs)[:70]}» → «{str(es)[:35]}»")
                continue
            if ops_in(item["question_hi"]) & ws_ops:
                lines.append(f"{g} question {n}: kept, though it repeats a worksheet problem")
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
