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
MIN_ITEMS, MAX_ITEMS = 2, 2          # two show-me questions per group is what a lesson has time for (the teachers' review: 8 in a block eats 5 to 7 minutes of 27); the model writes 3, the first 2 that pass the checks are used
MAX_QUESTION_CHARS, MAX_EXPECTED_CHARS = 170, 100      # the longest GOOD question seen is about 135 characters; a 210-character verbal description of a table was not one. A key is a verdict and a number, not an explanation: explanations are where mistakes hide
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
            "no_borrow": "without borrowing" in t or ("subtract" in t and "without regrouping" in t),
            # a TWO-DIGIT addition skill never reaches 100 (three-digit numbers are the next skill, the Proficients'): the knowledge base's number range says max 99 and the model read it as a limit on the
            # numbers added, not on the total (found on the second real block: worksheet problem 6 was 79 + 21 = 100)
            "max_result": 99 if t.startswith(("add", "adds")) and ("2-digit" in t or "two-digit" in t) else None}


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


_QUOTED_SPAN = re.compile(r"['\u2018\u201c][^'\u2019\u201d]*['\u2019\u201d]")
_END = r"(?=\s|$|[,\u0964.?!:;])"            # NOT \b: in Devanagari a vowel sign (े, ा) is not a word character, so \b fails after most words
_PERSON = r"(?:बच्चे|बच्ची|पाठक|विद्यार्थी|छात्र|छात्रा|लड़के|लड़की)"
_STORY = re.compile(r"(?:^|\s)(?:(?:एक|किसी)\s+)?" + _PERSON + r"\s+ने" + _END + r"|(?:^|\s)(?:बच्चों|विद्यार्थियों|पाठकों)\s+ने" + _END + r"|(?:^|\s)किसी\s+ने" + _END + r"|(?:^|\s)एक\s+(?:बच्चा|बच्ची|पाठक|विद्यार्थी)" + _END)
_PARAGRAPH_WORDS = ("अनुच्छेद", "पैराग्राफ")
_ABSTRACT = ("परिचय", "निष्कर्ष", "विषय से बाहर", "विषय से अलग", "विषय से हट", "विषय से जुड़", "किस काम", "मुख्य विचार", "सुसंगत", "विषय पर")


def _style_problems(q: str) -> list:
    """What the teachers' review ruled out, whatever the skill: (1) a question TOLD AS A STORY about a child ('एक बच्चे ने ... लिखा'): it adds reading and listening load for Class 1 and 2: write what is ON THE BOARD instead
    ('बोर्ड पर देखो: 34 + 28 = 52 लिखा है। क्या यह सही है?'). Text inside quotes is exempt: it may be a sentence the children read. (2) a question about the STRUCTURE or PURPOSE of a paragraph (introduction, conclusion,
    a sentence out of topic): too abstract for Class 2 and 3: ask about punctuation, what happened first or next, or a missing full stop."""
    out, outside = [], _QUOTED_SPAN.sub(" ", q)
    if _STORY.search(outside):
        out.append("it is told as a story about a child: write what is on the board instead (बोर्ड पर देखो: ...)")
    if any(w in q for w in _ABSTRACT) and (any(w in q for w in _PARAGRAPH_WORDS) or "वाक्य" in q):
        out.append("a question about the structure or purpose of a paragraph is too abstract for Class 2 and 3: ask about punctuation, sequence or a missing full stop")
    return out


def check_item(item, *, valid_ids: set, avoid: set, rules: dict, strict: bool = True, compare: bool = True, lesson_results: frozenset = frozenset()) -> list:
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

    problems.extend(_style_problems(q))
    qn, en = _prep(q), _prep(e)
    ops = OP_RE.findall(qn)
    stated = [(int(a), _norm_op(op), int(b), int(c)) for a, op, b, c in STATED_RE.findall(qn)]
    exprs = [m.group(0) for m in EXPR_RE.finditer(qn)]
    vals = [_eval_expr(x) for x in exprs]
    cap = (rules or {}).get("max_result")
    if cap:                                         # REAL results only: a worked line may deliberately show a wrong result over the cap (a spot_error such as 56 + 28 = 714)
        over = [v for v in vals if v is not None and v > cap]
        if over:
            problems.append(f"its result {over[0]} is over {cap}: three-digit numbers belong to a later skill, and this skill is two-digit")
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
            for _a, _op, _b, c_ in wrong:
                if c_ >= 10 and c_ in lesson_results:
                    problems.append(f"the wrong answer {c_} on the board is a right answer in this group's lesson: children may remember it as right")
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


_STAMPED_BY_CODE = {"affected_rolls", "reteach", "reteach_mistakes"}      # added to a re-teach block by the code BEFORE the questions are cleaned


def _lesson_results(block: dict) -> set:
    """The RIGHT answers the group's lesson works out (its I Do, We Do and You Do): the result of every operation written in them. A wrong answer shown in a spot_error must not be one of them: the first real re-teach run showed
    '176 + 349 = 425' as the wrong line, while the I Do's right answer to 267 + 158 was 425, and a child who remembers 425 as right would call the wrong line right."""
    out = set()
    for text in (block.get("talking_points") or {}).values():
        for a, op, b in OP_RE.findall(_prep(str(text or ""))):
            r = apply(int(a), _norm_op(op), int(b))
            if r is not None:
                out.add(r)
    return out


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


_VAGUE = ("जैसे", "जैसा", "बेतरतीब", "बेमेल")


def _without_vague_listen(item, numeric: bool) -> tuple:
    """(item, how many entries were removed). For a NUMERIC computation question a 'listen for' must be the EXACT wrong answer a child with that mistake gives, and it begins with that answer ('64', '10 या 11 (...)').
    An entry that begins with words and only describes it ('तीन-चार जैसा बेतरतीब उत्तर, जैसे 99 या 79') is of no use to a teacher: removed BEFORE the checks, so that a question left with no valid mistake and no explanation is dropped
    (and the top-up asks again). A behaviour ('उत्तर नहीं लिखा या अंदाज़ से कोई संख्या लिखी') is not an exemplifying description and stays."""
    if not numeric or not isinstance(item, dict) or item.get("kind") not in ("compute", "choose") or not isinstance(item.get("listen_for"), list):
        return item, 0
    keep = []
    for x in item["listen_for"]:
        w = str((x or {}).get("wrong_answer_hi") or "").strip() if isinstance(x, dict) else ""
        if w and not w[0].isdigit() and any(v in w for v in _VAGUE):
            continue
        keep.append(x)
    return ({**item, "listen_for": keep}, len(item["listen_for"]) - len(keep)) if len(keep) != len(item["listen_for"]) else (item, 0)


# ---- the listen-for answers are checked by CODE (found on the first real re-teach block: for 54 + 29 the model listed 613 for "writes the whole ones sum"; the child writes 713, the 613 was copied from the I Do's 46 + 27).
# The validator checked the RIGHT answer, the worked lines and the carry rule, but not what a child with a recorded mistake would write. The knowledge base records the pattern of these mistakes (each with its own worked
# example), so the code computes the wrong answer itself, as it computes the right one.
IMPOSSIBLE = "impossible"            # this recorded mistake cannot happen on these numbers (no carry is needed, so nobody can drop it)


def _two(*xs) -> bool:
    return all(10 <= x <= 99 for x in xs)


def _drop_carry(a, b):                                                  # N2.3.2-M1: 34 + 28 -> 52 (writes 2, forgets the carry)
    o = a % 10 + b % 10
    return None if not _two(a, b) else IMPOSSIBLE if o < 10 else (a // 10 + b // 10) * 10 + o % 10


def _whole_ones(a, b):                                                  # N2.3.2-M2: 34 + 28 -> 512 (writes 12 in the ones place)
    o = a % 10 + b % 10
    return None if not _two(a, b) else IMPOSSIBLE if o < 10 else int(str(a // 10 + b // 10) + str(o))


def _carry_wrong_digit(a, b):                                           # N2.3.2-M3: 34 + 28 -> 72 (carries the ones digit, 2, not the tens digit, 1)
    o = a % 10 + b % 10
    return None if not _two(a, b) else IMPOSSIBLE if o < 10 else (a // 10 + b // 10 + o % 10) * 10 + o % 10


def _second_carry_dropped(a, b):                                        # N3.3.1-M1: 167 + 245 -> 312 (carries ones to tens, forgets tens to hundreds)
    if not (100 <= a <= 999 and 100 <= b <= 999):
        return None
    o = a % 10 + b % 10
    t = (a // 10) % 10 + (b // 10) % 10 + o // 10
    return IMPOSSIBLE if t < 10 else (a // 100 + b // 100) * 100 + (t % 10) * 10 + o % 10


def _smaller_from_larger(a, b):                                         # N2.3.4-M1: 42 - 17 -> 35 (ones: 7 - 2, no borrow)
    if not (_two(a, b) and a >= b):
        return None
    return IMPOSSIBLE if a % 10 >= b % 10 else (a // 10 - b // 10) * 10 + (b % 10 - a % 10)


def _forgot_to_reduce(a, b):                                            # N2.3.4-M2: 42 - 17 -> 35 (ones: 12 - 7, but the tens digit is not reduced)
    if not (_two(a, b) and a >= b):
        return None
    return IMPOSSIBLE if a % 10 >= b % 10 else (a // 10 - b // 10) * 10 + (a % 10 + 10 - b % 10)


def _digitwise_product(a, b):                                           # N3.3.4-M1: 23 x 4 -> 812 (8 and 12 written side by side)
    if not (_two(a) and 2 <= b <= 9):
        return None
    return IMPOSSIBLE if (a % 10) * b < 10 else int(str((a // 10) * b) + str((a % 10) * b))


def _divide_as_subtract(a, b):                                          # N3.3.5-M1: 24 / 6 -> 18 (subtracts)
    return a - b if a > b >= 2 else None


LISTEN_PATTERNS = {"N2.3.2-M1": ("+", _drop_carry), "N2.3.2-M2": ("+", _whole_ones), "N2.3.2-M3": ("+", _carry_wrong_digit), "N3.3.1-M1": ("+", _second_carry_dropped),
                   "N2.3.4-M1": ("-", _smaller_from_larger), "N2.3.4-M2": ("-", _forgot_to_reduce), "N3.3.4-M1": ("*", _digitwise_product), "N3.3.5-M1": ("/", _divide_as_subtract)}


def wrong_answer_for(mid, a: int, op: str, b: int):
    """What a child with the recorded mistake `mid` writes for a op b: an integer; IMPOSSIBLE when the mistake cannot occur on these numbers (or happens to give the right answer);
    None when the code has no pattern for that mistake, or the numbers do not suit it (the entry is then left as the model wrote it)."""
    spec = LISTEN_PATTERNS.get(mid)
    if not spec or _norm_op(op) != spec[0]:
        return None
    out = spec[1](a, b)
    if out is None:
        return None
    return IMPOSSIBLE if out == apply(a, op, b) else out


def _single_operation(q: str):
    """(a, op, b) when the question contains exactly ONE operation between two numbers, else None (a chain such as 2 + 2 + 2, or two sums, is not checked)."""
    qn = _prep(q)
    exprs, ops = [m.group(0) for m in EXPR_RE.finditer(qn)], OP_RE.findall(qn)
    if len(exprs) != 1 or len(ops) != 1 or len(NUM_RE.findall(exprs[0])) != 2:
        return None
    a, op, b = ops[0]
    return int(a), _norm_op(op), int(b)


def verified_listen(item) -> tuple:
    """(item, notes). For a numeric 'compute' question with ONE operation, every listen-for entry whose mistake the code can compute is checked against what that mistake really gives:
    a different number is CORRECTED (when the text holds several numbers and none is right, the entry becomes the right one alone), an entry for a mistake that cannot happen on these numbers is REMOVED,
    and the rest is left alone (a behaviour in words, another kind of question, a mistake the code has no pattern for). Run BEFORE the checks, like the vague-entry cleaner, so that a question left with
    no valid mistake and no explanation is dropped and the top-up asks again."""
    notes = []
    if not isinstance(item, dict) or item.get("kind") != "compute" or not isinstance(item.get("listen_for"), list):
        return item, notes
    expr = _single_operation(str(item.get("question_hi") or ""))
    if not expr:
        return item, notes
    a, op, b = expr
    keep = []
    for x in item["listen_for"]:
        mid = x.get("misconception_id") if isinstance(x, dict) else None
        want = wrong_answer_for(mid, a, op, b) if mid else None
        if want is None:
            keep.append(x)
            continue
        if want == IMPOSSIBLE:
            notes.append(f"removed {mid}: that mistake cannot happen on {a} {op} {b}")
            continue
        text = _prep(str(x.get("wrong_answer_hi") or "")).strip()
        found = [int(n) for n in NUM_RE.findall(text)]
        if not found or want in found:                      # a behaviour in words, or already right
            keep.append(x)
            continue
        fixed = NUM_RE.sub(str(want), text, count=1) if len(found) == 1 else str(want)
        notes.append(f"{mid}: listed {text[:40]!r} but that mistake gives {want} on {a} {op} {b}: corrected to {fixed[:40]!r}")
        keep.append({**x, "wrong_answer_hi": fixed})
    if not notes:
        return item, notes
    return {**item, "listen_for": keep}, notes


def right_answer(item):
    """The right answer of a numeric question, worked out from the question itself: for a worked line to judge ('49 + 35 = 74') the real result of 49 + 35, otherwise the value of the last expression.
    None when the question has no arithmetic. Used to keep the show-me questions of one group from sharing an answer (found on the second real block: 56 + 28 and 49 + 35 were both 84, so a child
    who solved the first knew the second without computing)."""
    if not isinstance(item, dict):
        return None
    qn = _prep(str(item.get("question_hi") or ""))
    stated = STATED_RE.findall(qn)
    if stated:
        a, op, b, _c = stated[-1]
        return apply(int(a), op, int(b))
    exprs = [m.group(0) for m in EXPR_RE.finditer(qn)]
    return _eval_expr(exprs[-1]) if exprs else None


def _is_wrong_line(item) -> bool:
    """A 'right or wrong?' question whose worked line IS wrong (the answer starts with गलत). A child can answer it without working anything out: in a lesson about mistakes, 'wrong' is the safe guess."""
    return isinstance(item, dict) and item.get("kind") == "spot_error" and _prep(str(item.get("expected_hi") or "")).strip().startswith("गलत")


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
        lesson_results = _lesson_results(block)
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
            keys_written = ", ".join([k for k in sorted(block) if k not in _STAMPED_BY_CODE][:14])      # what the MODEL wrote: not the keys the code stamped earlier (the re-teach's), nor those it adds below
            block["cfu"], block["cfu_grounded"] = [], bool(mistakes)
            stats[g] = {"written": 0, "kept": 0, "grounded_items": 0, "skill_has_mistakes": bool(mistakes)}
            lines.append(f"{g}: no CFU written (the model's block has: {keys_written})")
            continue
        kept, answers_kept = [], {}
        for n, item in enumerate(raw, 1):
            item, vague = _without_vague_listen(item, strict)
            if vague:
                lines.append(f"{g} question {n}: removed {vague} vague listen-for entry(ies): it must be the exact wrong answer, not a description")
            if strict:
                item, listen_notes = verified_listen(item)
                for note in listen_notes:
                    lines.append(f"{g} question {n}: listen-for {note}")
            problems = check_item(item, valid_ids=set(mistakes), avoid=avoid, rules=rules, strict=strict, compare=compare, lesson_results=lesson_results)
            if problems:
                qs, es = (item.get("question_hi") or "") if isinstance(item, dict) else "", (item.get("expected_hi") or "") if isinstance(item, dict) else ""
                lines.append(f"{g} question {n} dropped: {'; '.join(problems)} | «{str(qs)[:70]}» → «{str(es)[:35]}»")
                continue
            if strict:                                  # numeracy: two questions of one group must not share a right answer
                ra = right_answer(item)
                if ra is not None and ra in lesson_results:       # WARNING ONLY (a drop would trigger an extra model call): the lesson has put this result on the board
                    lines.append(f"{g} question {n}: warning: its right answer {ra} is already a result in the lesson (on the board): a child could copy it")
                for x in item.get("listen_for") or []:
                    w = _prep(str((x or {}).get("wrong_answer_hi") or "")) if isinstance(x, dict) else ""
                    lead = NUM_RE.findall(w)
                    if lead and w.strip()[:1].isdigit() and int(lead[0]) in lesson_results:
                        lines.append(f"{g} question {n}: warning: the listed wrong answer {lead[0]} for {x.get('misconception_id')} is a right result in the lesson: a child who writes it may have copied it")
                if ra is not None and ra in answers_kept:
                    lines.append(f"{g} question {n} dropped: its right answer {ra} is the same as question {answers_kept[ra]}'s (a child who knows one knows the other) | «{str(item.get('question_hi') or '')[:70]}»")
                    continue
                if _is_wrong_line(item) and kept and len(kept) == MAX_ITEMS - 1 and all(_is_wrong_line(k) for k in kept):
                    # found on the fourth real block: BOTH show-me questions were 'right or wrong?' lines with a WRONG line (answers 'गलत, 83' and 'गलत, 63'): a child guesses 'wrong' twice and passes
                    lines.append(f"{g} question {n} dropped: both show-me questions would be wrong 'right or wrong?' lines, so a child can guess 'wrong'. Write a question where the child WORKS OUT an answer (compute or choose) | «{str(item.get('question_hi') or '')[:70]}»")
                    continue
                if ra is not None:                      # only a question that is KEPT claims its answer (a dropped one claims nothing)
                    answers_kept[ra] = n
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
