"""
Hindi number names, and the checks and repairs that keep number words, digits, answer keys and flash cards
consistent in place-value and number-reading worksheets.

Why code, not the model: models get Hindi number names wrong (उनसठ is 59, not 49) and copy the lesson's examples
onto the worksheet. As with the addition repairs, the code decides: it writes every number word from its digits,
removes answers printed in the question, swaps a repeated number for a fresh one of the same shape, and builds the
flash-card list from the cards the lesson actually shows.

Public entry points (all take the plan dict and return a list of log lines or warnings):
    repair_place_value(plan)       words -> repeats -> answer leak -> flash cards
    find_number_word_errors(plan)  validator warnings
    find_numeric_overlaps(plan)    validator warnings
    name(n) / phrases(text)        the generator and the parser
"""

import random
import re
import unicodedata


def _n(s) -> str:
    """Hindi letters such as ड़ and ज़ have two spellings in Unicode; compare them in one form."""
    return unicodedata.normalize("NFC", str(s))


def _key(s) -> str:
    """For looking words up: NFC, and chandrabindu = anusvara (पाँच = पांच)."""
    return unicodedata.normalize("NFC", str(s)).replace("\u0901", "\u0902")


_NAMES = _n(
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस "
    "इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास "
    "इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर "
    "छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे"
).split()
assert len(_NAMES) == 100

_VAL = {_key(w): i for i, w in enumerate(_NAMES)}
# Accepted spellings. The generator writes the standard form above; the parser also accepts what people commonly write
# (seen in the published lists we checked: Bharat Discovery, the NIT Hamirpur Hindi cell, and what models write).
_VAL.update({_key(k): v for k, v in {
    "छः": 6, "छ:": 6, "पन्द्रह": 15, "अट्ठारह": 18, "उन्निस": 19, "बाइस": 22, "अठाईस": 28, "इकत्तीस": 31, "सैतालीस": 47, "चवालीस": 44, "चौवालीस": 44,
    "चौतालीस": 44, "चौंतालीस": 44, "इक्याबन": 51, "तिरेपन": 53, "चौबन": 54, "अठावन": 58, "तिरेसठ": 63, "सरसठ": 67, "उनासी": 79, "सतासी": 87, "अठासी": 88,
    "इकानवे": 91, "इक्यानबे": 91, "बानबे": 92, "तिरानबे": 93, "चौरानबे": 94, "पचानवे": 95, "पंचानबे": 95, "छियानबे": 96, "सत्तानबे": 97, "अठानवे": 98,
    "अठानबे": 98, "अट्ठानबे": 98, "निन्यानबे": 99}.items()})
_SAU, _HAZAR = _n("सौ"), _n("हज़ार")                      # as written out
_SAU_K, _HAZ_K = _key("सौ"), {_key("हज़ार"), _key("हजार")}   # as looked up
_MULT = {_SAU_K} | _HAZ_K
_TOK = re.compile(r"[\u0900-\u0963]+")                      # Devanagari letters and marks; the danda (।) is not a letter
_NUMERAL = re.compile(r"(?<![\w\-])\d[\d,]*(?![\w\-])")
_FILLER = {_n(w) for w in ("लिखिए", "लिखो", "अंकों", "में", "संख्या")}
_PLACE = {_n("हज़ार"): 3, _n("सैकड़े"): 2, _n("सैकड़ा"): 2, _n("दहाइयाँ"): 1, _n("दहाई"): 1, _n("इकाइयाँ"): 0, _n("इकाई"): 0}
_PV = re.compile(r"(\d)\s*(" + "|".join(sorted(_PLACE, key=len, reverse=True)) + r")")
_PLAIN_ADD = re.compile(r"\s*\d+\s*\+\s*\d+\s*(=\s*_*)?\s*$")
_GROUPS = ("beginner", "progressor", "proficient")
_GROUP_HI = {"beginner": "शुरुआती", "progressor": "प्रगतिशील", "proficient": "दक्ष"}


def name(n):
    """The Hindi name of n (0 to 99,999), or None."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 0 or n > 99999:
        return None
    if n < 100:
        return _NAMES[n]
    parts = []
    th, rest = divmod(n, 1000)
    if th:
        parts.append(f"{_NAMES[th]} {_HAZAR}")
    h, t = divmod(rest, 100)
    if h:
        parts.append(f"{_NAMES[h]} {_SAU}")
    if t:
        parts.append(_NAMES[t])
    return " ".join(parts)


def value_of(tokens) -> int:
    total = cur = 0
    for t in tokens:
        t = _key(t)
        if t in _VAL:
            cur += _VAL[t]
        elif t == _SAU_K:
            cur = (cur or 1) * 100
        elif t in _HAZ_K:
            total += (cur or 1) * 1000
            cur = 0
    return total + cur


def phrases(text) -> list:
    """Runs of number words in the text: [{'start', 'end', 'tokens', 'value', 'text'}]. Positions refer to `text`."""
    text = str(text or "")
    out, run, prev_end = [], [], None

    def close():
        if run and any(t in _VAL for _, _, t in run):
            toks = [t for _, _, t in run]
            out.append({"start": run[0][0], "end": run[-1][1], "tokens": toks, "value": value_of(toks), "text": text[run[0][0]:run[-1][1]]})

    for m in _TOK.finditer(text):
        t = _key(m.group())
        is_num = t in _VAL or t in _MULT
        adjacent = prev_end is not None and re.fullmatch(r"[ \t]+", text[prev_end:m.start()]) is not None
        if is_num and run and adjacent:
            run.append((m.start(), m.end(), t))
        else:
            close()
            run = [(m.start(), m.end(), t)] if is_num else []
        prev_end = m.end()
    close()
    return out


def numerals(text) -> list:
    """[(value, start, end)] for the numerals in text (commas allowed: 3,482). Codes like TLM-007 and ranges are skipped."""
    out = []
    for m in _NUMERAL.finditer(str(text or "")):
        raw = m.group().replace(",", "").rstrip(",")
        if raw.isdigit() and not (len(raw) > 1 and raw.startswith("0")):
            out.append((int(raw), m.start(), m.end()))
    return out


def _is_place_value(n) -> bool:
    """10, 20, ... 90, 100, 200, ... 1000, 2000: the building blocks of place value, and boundaries like "up to 100"."""
    return bool(re.fullmatch(r"[1-9]0+", str(n)))


def _numbers_in(text) -> set:
    """Every number 10 or more that the text mentions, as a numeral or as Hindi words (boundary numbers excluded)."""
    s = {v for v, _, _ in numerals(text) if v >= 10} | {p["value"] for p in phrases(text) if p["value"] >= 10}
    return {v for v in s if not _is_place_value(v)}


def _answer_int(p):
    a = str(p.get("answer", "")).replace(",", "").strip()
    return int(a) if a.isdigit() else None


def _sheets(plan):
    for level in _GROUPS:
        ws = (plan.get("worksheets") or {}).get(level) or {}
        if ws.get("problems"):
            yield level, ws, ws["problems"]


def _teach_blocks(plan):
    return {b.get("teach_group"): b for b in ((plan.get("rotation_schedule") or {}).get("blocks") or []) if b.get("type") == "teach"}


def lesson_numbers(plan, level) -> set:
    """Numbers the group's lesson (I Do, We Do) and the anchor already work through: a worksheet should not repeat them."""
    b = (_teach_blocks(plan).get(level) or {}).get("talking_points") or {}
    a = plan.get("anchor") or {}
    text = " ".join(str(b.get(k) or "") for k in ("i_do_hi", "we_do_hi"))
    text += " " + " ".join(str(a.get(k) or "") for k in ("narration_hi", "opening_question_hi", "closing_question_hi", f"{level}_participation_hi"))
    return _numbers_in(text)


def _headless(ph) -> bool:
    """'हज़ार सात' with nothing before हज़ार: a word we do not know is probably in front of it. Never rewrite such a phrase."""
    return len(ph["tokens"]) > 1 and ph["tokens"][0] in _MULT


def _set_text(pr, old, new):
    for key in ("problem_hi", "word_problem_text"):
        if pr.get(key) and old in pr[key]:
            pr[key] = pr[key].replace(old, new)


# ── 1. number words are written from the digits ─────────────────────────────

def repair_number_words(plan) -> list:
    """
    "उनसठ (49)" means 59, not 49. The digits and the answer key are what the model decided first; its Hindi number name is
    what goes wrong. So the word is rewritten from the answer. Also fixes a digits-to-words answer that names the wrong number.
    """
    log = []
    for level, ws, problems in _sheets(plan):
        for pr in problems:
            text = str(pr.get("problem_hi") or "")
            ans = _answer_int(pr)
            n = pr.get("number")
            # (a) a number word followed by its digits in brackets
            for ph in sorted(phrases(text), key=lambda p: -p["start"]):
                m = re.match(r"\s*\((\d[\d,]*)\)", text[ph["end"]:])
                if not m:
                    continue
                digits = int(m.group(1).replace(",", ""))
                truth = ans if ans is not None else digits
                if ph["value"] != truth and name(truth) and not _headless(ph):
                    new_word = name(truth)
                    log.append(f"{level} problem {n}: the number word «{ph['text']}» means {ph['value']} but the answer is {truth}; rewritten as «{new_word}»")
                    _set_text(pr, ph["text"], new_word)
                    text = str(pr.get("problem_hi") or "")
            # (b) a number word to be written in digits, whose word does not match the answer
            text = str(pr.get("problem_hi") or "")
            if ans is not None and re.search(r"अंकों में|=\s*_+|लिखिए", text) and not re.search(r"[+×÷−]", text) and not re.search(r"\(\d", text):
                ps = phrases(text)
                if ps and not any(p["value"] == ans for p in ps):
                    cand = max(ps, key=lambda p: (len(p["tokens"]), p["value"]))
                    left = _TOK.findall(text[:cand["start"]] + " " + text[cand["end"]:])
                    only_filler = all(_n(t) in _FILLER for t in left)      # embedded in a sentence: warn, never rewrite
                    if only_filler and not _headless(cand) and (len(cand["tokens"]) >= 2 or cand["value"] >= 10) and name(ans):
                        log.append(f"{level} problem {n}: the number word «{cand['text']}» means {cand['value']} but the answer is {ans}; rewritten as «{name(ans)}»")
                        _set_text(pr, cand["text"], name(ans))
            # (c) a number to be written in words, whose answer names a different number
            text = str(pr.get("problem_hi") or "")
            nums = [v for v, _, _ in numerals(text) if v >= 10]
            if len(nums) == 1 and re.search(r"शब्दों में (लिखिए|लिखो)", text) and ans is None:
                aphr = phrases(str(pr.get("answer") or ""))
                if aphr and aphr[0]["value"] != nums[0] and name(nums[0]):
                    log.append(f"{level} problem {n}: the answer «{pr['answer']}» names {aphr[0]['value']} but the question number is {nums[0]}; rewritten as «{name(nums[0])}»")
                    pr["answer"] = name(nums[0])
    return log


# ── 2. the answer is not printed in the question ────────────────────────────

def strip_given_digits(plan) -> list:
    """'छत्तीस (36) लिखिए' hands the child the answer. Remove digits in brackets that are the answer itself."""
    log = []
    for level, ws, problems in _sheets(plan):
        for pr in problems:
            ans = _answer_int(pr)
            text = str(pr.get("problem_hi") or "")
            if ans is None:
                continue
            for ph in phrases(text):
                m = re.match(r"\s*\((\d[\d,]*)\)", text[ph["end"]:])
                if m and int(m.group(1).replace(",", "")) == ans:
                    log.append(f"{level} problem {pr.get('number')}: the answer {ans} was printed beside «{ph['text']}»; removed")
                    for key in ("problem_hi", "word_problem_text"):
                        if pr.get(key):
                            pr[key] = re.sub(r"\s*\(" + re.escape(m.group(1)) + r"\)", "", pr[key], count=1)
                    break
    return log


# ── 3. a worksheet number the lesson already used ───────────────────────────

def _template(pr, ans):
    """Recognise the three problem shapes the code can regenerate safely. Returns (kind, data) or None."""
    text = _n(pr.get("problem_hi") or "")
    ms = list(_PV.finditer(text))
    if ms:
        rest = re.sub(r"और|[\s,।.:=_]", "", _PV.sub("", text))
        if rest == "":
            digs = {_PLACE[m.group(2)]: int(m.group(1)) for m in ms}
            if sum(d * 10 ** p for p, d in digs.items()) == ans and len(digs) == len(ms):
                return "pv", {"text": text, "places": digs}
        return None
    m = re.fullmatch(r"\s*(\d+(?:\s*\+\s*\d+)+)\s*=\s*_*\s*", text)
    if m:
        terms = [int(x) for x in re.findall(r"\d+", m.group(1))]
        ok = all(re.fullmatch(r"[1-9]0*", str(t)) for t in terms)
        if ok and sum(terms) == ans:
            return "exp", {"text": text, "span": m.span(1), "terms": terms}
        return None
    ps = [p for p in phrases(text) if p["value"] == ans and (p["value"] >= 10 or len(p["tokens"]) >= 2)]
    if len(ps) == 1:
        p = ps[0]
        left = _TOK.findall(text[:p["start"]] + " " + text[p["end"]:])
        if all(_n(t) in _FILLER for t in left):
            return "word", {"text": text, "span": (p["start"], p["end"])}
    return None


def _pick(orig, avoid, rng):
    """A fresh number with the same number of digits and the same zeros as orig, not in avoid."""
    s = str(orig)
    for _ in range(400):
        cand = int("".join("0" if ch == "0" else str(rng.randint(1, 9)) for ch in s))
        if cand != orig and cand not in avoid:
            return cand
    return None


def repair_place_value_repeats(plan) -> list:
    log = []
    for level, ws, problems in _sheets(plan):
        lesson = lesson_numbers(plan, level)
        ex = ws.get("example_block") or {}
        avoid = set(lesson) | {a for a in (_answer_int(p) for p in problems) if a is not None}
        exa = str(ex.get("answer", "")).replace(",", "")
        if exa.isdigit():
            avoid.add(int(exa))
        for pr in problems:
            ans = _answer_int(pr)
            if ans is None or ans not in lesson or _PLAIN_ADD.match(str(pr.get("problem_hi") or "")):
                continue
            tpl = _template(pr, ans)
            if not tpl:
                continue
            kind, d = tpl
            new = _pick(ans, avoid, random.Random(f"{level}:{pr.get('number')}:{ans}"))
            if new is None:
                continue
            old_text = pr["problem_hi"]
            if kind == "pv":
                width = max(d["places"]) + 1
                digits = str(new).zfill(width)
                new_text = _PV.sub(lambda m: digits[width - 1 - _PLACE[m.group(2)]] + m.group(0)[len(m.group(1)):], d["text"])
            elif kind == "exp":
                width = max(len(str(t)) for t in d["terms"])
                digits = str(new)
                terms = [int(ch) * 10 ** (len(digits) - 1 - i) for i, ch in enumerate(digits) if ch != "0"]
                new_text = d["text"][:d["span"][0]] + " + ".join(str(t) for t in terms) + d["text"][d["span"][1]:]
            else:
                new_text = d["text"][:d["span"][0]] + name(new) + d["text"][d["span"][1]:]
            pr["problem_hi"], pr["answer"] = new_text, str(new)
            avoid.add(new)
            log.append(f"{level} problem {pr.get('number')}: «{old_text}» (= {ans}) repeats a number the lesson already used; replaced by «{new_text}» (= {new})")
    return log


# ── 4. the flash-card list comes from the lesson ────────────────────────────

_CARD_RUN = re.compile(r"कार्ड\s*(\d[\d,]*(?:\s*(?:,|और)\s*\d[\d,]*)*)")
_THEN_RUN = re.compile(r"^\s*फिर\s*(\d[\d,]*(?:\s*(?:,|और)\s*\d[\d,]*)*)")


def _cards_in(text) -> list:
    """The numbers on the cards a lesson shows: those right after the word 'कार्ड', and after a following 'फिर'.
    A sentence that goes on to explain the card ('इसमें 2 दहाइयाँ और 7 इकाइयाँ हैं') must not add 2 and 7."""
    sentences = re.split(r"[।\n]", str(text or ""))
    cards = []
    for i, s in enumerate(sentences):
        m = _CARD_RUN.search(s)
        if m:
            cards += [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", m.group(1))]
            if i + 1 < len(sentences):
                t = _THEN_RUN.match(sentences[i + 1])
                if t:
                    cards += [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", t.group(1))]
    return cards


def repair_flash_cards(plan) -> list:
    """The prep list must name the cards the lesson shows, or the teacher finds cards missing in the middle of a lesson."""
    by_group = {}
    for g, b in _teach_blocks(plan).items():
        seen = []
        for k in ("i_do_hi", "we_do_hi", "you_do_hi"):
            for c in _cards_in((b.get("talking_points") or {}).get(k)):
                if c not in seen:
                    seen.append(c)
        if seen:
            by_group[g] = seen
    if not by_group:
        return []
    prep = plan.setdefault("prep_hi", [])
    idx = next((i for i, x in enumerate(prep) if "कार्ड" in str(x) and ("फ्लैश" in str(x) or "TLM" in str(x))), None)
    tlm = re.search(r"TLM-\d+", str(prep[idx])) if idx is not None else None
    lists = "; ".join(f"{_GROUP_HI.get(g, g)} समूह के लिए {', '.join(str(c) for c in cards)}" for g, cards in by_group.items() if g in _GROUP_HI)
    total = sum(len(c) for c in by_group.values())
    line = (f"फ्लैश कार्ड{' (' + tlm.group() + ')' if tlm else ''} बनाएँ: मोटे कागज़ को ताश के पत्ते के आकार में काटें। एक तरफ़ अंक लिखें, "
            f"दूसरी तरफ़ उतने बिंदु या दहाई-इकाई के चित्र बनाएँ। पाठ में ये कार्ड दिखाए जाएँगे: {lists}। कुल {total} कार्ड।")
    if idx is not None and prep[idx] == line:
        return []
    if idx is None:
        prep.append(line)
    else:
        prep[idx] = line
    return [f"flash cards listed from the lesson: " + "; ".join(f"{g} {', '.join(str(c) for c in cards)}" for g, cards in by_group.items())]


def repair_place_value(plan) -> list:
    """Words first (so templates are recognised), then repeats, then the answer leak, then the card list."""
    return repair_number_words(plan) + repair_place_value_repeats(plan) + strip_given_digits(plan) + repair_flash_cards(plan)


# ── validator checks (what the repairs could not fix) ───────────────────────

def find_number_word_errors(plan) -> list:
    issues = []
    for level, ws, problems in _sheets(plan):
        for pr in problems:
            text, ans = str(pr.get("problem_hi") or ""), _answer_int(pr)
            for ph in phrases(text):
                m = re.match(r"\s*\((\d[\d,]*)\)", text[ph["end"]:])
                if m and int(m.group(1).replace(",", "")) != ph["value"]:
                    issues.append(f"worksheets.{level} problem {pr.get('number')}: the number word «{ph['text']}» means {ph['value']}, not {m.group(1)}")
    for level, ws, problems in _sheets(plan):
        for pr in problems:
            text, ans = str(pr.get("problem_hi") or ""), _answer_int(pr)
            ps = phrases(text)
            for ph in ps:
                if _headless(ph):
                    issues.append(f"worksheets.{level} problem {pr.get('number')}: «{ph['text']}» has no number before the multiplier: check the spelling of the word in front")
            if ans is not None and ps and re.search(r"अंकों में|=\s*_+", text) and not re.search(r"[+×÷−]|\(\d", text) \
                    and not any(p["value"] == ans for p in ps) and not any(_headless(p) for p in ps):
                big = max(ps, key=lambda p: p["value"])
                if big["value"] >= 10:
                    issues.append(f"worksheets.{level} problem {pr.get('number')}: the number word «{big['text']}» means {big['value']} but the answer is {ans}")
    for g, b in _teach_blocks(plan).items():
        for k, v in ((b.get("talking_points") or {}).items()):
            for sent in re.split(r"[।\n]", str(v or "")):
                nums = {x for x, _, _ in numerals(sent) if x >= 10}
                phs = [p for p in phrases(sent) if p["value"] >= 10]
                if nums and phs and not any(p["value"] in nums for p in phs):
                    issues.append(f"the {g} lesson ({k}) says «{phs[0]['text']}» (= {phs[0]['value']}) beside the number {sorted(nums)[0]}")
    return issues


def find_numeric_overlaps(plan) -> list:
    issues = []
    for level, ws, problems in _sheets(plan):
        lesson = lesson_numbers(plan, level)
        # On a sheet of sums, a word problem may reuse ONE number from the lesson in a new pair: that is not copying, so only
        # repeated answers count there. On a place-value or reading sheet the number in the question IS the example.
        arithmetic_sheet = any(_PLAIN_ADD.match(str(p.get("problem_hi") or "")) for p in problems)
        for pr in problems:
            text = str(pr.get("problem_hi") or "")
            if _PLAIN_ADD.match(text):                    # additions have their own check
                continue
            given = set() if arithmetic_sheet else _numbers_in(text)
            a = _answer_int(pr)
            if a is not None and a >= 10 and not _is_place_value(a):
                given.add(a)
            hit = sorted(given & lesson)
            if hit:
                issues.append(f"worksheets.{level} problem {pr.get('number')} repeats a number the lesson or anchor already used: {hit[0]}")
    return issues
