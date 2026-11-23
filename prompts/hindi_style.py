"""
Hindi style for the words a teacher reads and says (docs/HINDI_STYLE.md).

From Vaishnavi's review of the N2.3.2 plan (Oct 2026). The vocabulary was generally accurate, but the tone should be warmer and more
respectful, and one term was unclear for young children:

  * "फालतू बंडल"            -> "अतिरिक्त बंडल"        (the word reads as "useless")
  * "चुपचाप शुरू करें"       -> "शांति से शुरू करें"    (sounds like a reprimand)
  * "मेरे पास आओ", "अपना काम बंद करो", "छड़ियाँ मॉनिटर को दो"
                              -> "आएँ", "रोक दें", "दें"  (model respectful language: it is a goal of foundational learning)
  * "दहाई | इकाई का खाना"   -> "दहाई-इकाई का बॉक्स"   (खाना is ambiguous for a 6-year-old; बॉक्स matches the printed place-value grids)
  * "ग्रिड से हल करें"        -> "बॉक्स से हल करें"     (in a place-value sentence only: a letter grid in a literacy plan is left alone)
  * "कितने दहाई, कितने इकाई" -> "कितनी दहाई, कितनी इकाई"  (not in her review: found on a careful read; both words are feminine)

Kept as they are, by her review: हासिल, खुली छड़ियाँ, शब्द-सवाल, and the collective praise "आज बहुत अच्छा काम हुआ".

Two layers, because each is good at something different:
  1. STYLE_PROMPT is put in the model's instructions: the model writes this way in the first place, which is the real fix.
  2. soften_plan() is a SAFETY NET on the generated plan: whole-word swaps for the cases that are unambiguous, so a missed instruction does not
     reach a teacher. It never touches a word problem, a passage, an answer or a name, and it is idempotent.

Decided: FRAME_WORD is बॉक्स (घर was the other option). Still open for Vaishnavi (one constant, not the code): POLITE_IN_WORKSHEETS (should the printed
worksheet instructions to children also use the respectful forms, or keep the textbook "जोड़ो, लिखो" style?).
"""

import re

FRAME_WORD = "बॉक्स"             # decided 20 Oct: it matches the place-value grids the app prints ("घर" only works if children were taught that way)
POLITE_IN_WORKSHEETS = True       # decided 21 Oct: respectful forms on the printed sheets too (जोड़ें, लिखें, पढ़ें), consistent with what the teacher says

STYLE_PROMPT = (
    "- When the teacher speaks TO THE CHILDREN (transitions, tasks, questions, instructions for independent work), use respectful plural forms, "
    "never abrupt 'तुम' commands: write 'मेरे पास आएँ', 'अपना काम रोक दें', 'कॉपी बंद करें', 'छड़ियाँ मॉनिटर को दें', 'अपनी जगह जाएँ', 'सुनें', "
    "not 'आओ', 'बंद करो', 'दो', 'जाओ', 'सुनो'. The same on the printed worksheets: 'जोड़ें', 'लिखें', 'पढ़ें', not 'जोड़ो', 'लिखो', 'पढ़ो'.\n"
    "- Say 'वर्कशीट' for a worksheet, never 'कार्यपत्रक'.\n"
    "- Keep every line warm and positive. Never use 'फालतू' (write 'अतिरिक्त') or 'चुपचाप' (write 'शांति से' or 'बिना शोर किए').\n"
    f"- Call the Tens | Ones frame 'दहाई-इकाई का {FRAME_WORD}' (plural '{FRAME_WORD}'), never 'खाना', 'खाने' or 'ग्रिड'. Keep 'हासिल', 'खुली छड़ियाँ' and "
    "'शब्द-सवाल' as they are, and end the lesson with a praise for the whole class such as 'आज बहुत अच्छा काम हुआ'.\n"
    "- दहाई and इकाई are feminine: write 'कितनी दहाई और कितनी इकाई', not 'कितने दहाई'.\n"
)

_DEV = "\u0900-\u0963\u0966-\u097F"          # letters, vowel signs and digits: NOT the danda ।  (U+0964) or ॥ (U+0965), which are punctuation


def _word(w: str) -> str:
    """The whole word only: 'खाना' must not match inside 'सिखाना' or 'दिखाना'."""
    return rf"(?<![{_DEV}]){w}(?![{_DEV}])"


# word-level swaps that are safe wherever they appear in a teacher's text or a printed instruction
WORD_SWAPS = [
    (re.compile(_word("कार्यपत्रकों")), "वर्कशीटों"),                 # one word for a worksheet, the one the app uses (decided 21 Oct)
    (re.compile(_word("कार्यपत्रक")), "वर्कशीट"),
    (re.compile(_word("कार्यपत्र")), "वर्कशीट"),
    (re.compile(_word("फालतू")), "अतिरिक्त"),
    (re.compile(_word("चुपचाप")), "शांति से"),
]

# grammar: दहाई and इकाई are feminine, so it is "कितनी दहाई, कितनी इकाई" (the model sometimes writes "कितने")
GENDER_FIXES = [(re.compile(rf"कितने(\s+)(दहाई|इकाई)(?![{_DEV}])"), r"कितनी\1\2")]

# 'तुम' commands to the class -> respectful plural. The specific phrase first; then the verbs that are unambiguous in a classroom.
POLITE_PHRASES = [
    (re.compile(_word("अपना काम बंद करो")), "अपना काम रोक दें"),
]
POLITE_VERBS = {
    "आओ": "आएँ", "जाओ": "जाएँ", "बैठो": "बैठें", "उठो": "उठें", "सुनो": "सुनें", "देखो": "देखें", "बोलो": "बोलें", "लिखो": "लिखें",
    "पढ़ो": "पढ़ें", "गिनो": "गिनें", "जोड़ो": "जोड़ें", "घटाओ": "घटाएँ", "बनाओ": "बनाएँ", "करो": "करें", "रखो": "रखें", "लाओ": "लाएँ",
    "दिखाओ": "दिखाएँ", "बताओ": "बताएँ", "समझाओ": "समझाएँ", "चलो": "चलें", "चुनो": "चुनें", "मिलाओ": "मिलाएँ", "घेरो": "घेरें",
    "काटो": "काटें", "खींचो": "खींचें", "पूछो": "पूछें", "सोचो": "सोचें", "रुको": "रुकें", "ठहरो": "ठहरें", "बाँटो": "बाँटें",
    "खोलो": "खोलें", "दोहराओ": "दोहराएँ", "जाँचो": "जाँचें", "भरो": "भरें", "मिटाओ": "मिटाएँ", "उतारो": "उतारें", "पहचानो": "पहचानें",
    "लगाओ": "लगाएँ",
}
_POLITE_VERB_RE = re.compile(_word("(" + "|".join(re.escape(k) for k in sorted(POLITE_VERBS, key=len, reverse=True)) + ")"))
# 'दो' is also the number two ('दो अंकों के जोड़'), so it is changed ONLY as the verb 'give', after the words that go with it, at the end of a clause
_GIVE_RE = re.compile(rf"(?<![{_DEV}])((?:को|वापस|इसे|उसे|उन्हें|दे) )दो(?=\s*(?:[।,?!.;:]|$)|\s+(?:और|फिर)(?![{_DEV}]))")

# a group addressed in an instruction takes the respectful plural, like everything else said to the class (22 Nov, the third review of the v2
# plans: "शुरुआती समूह अपनी जगह पर वर्कशीट लेकर जाए। प्रगतिशील समूह मेरे पास आएँ।" mixed the two in one script). Only a verb that ends its clause
# (before । ; ! ? , or 'और') in a clause that names a समूह, so 'बच्चे', a story's 'बादल आए' or 'जाएगा' are never touched.
GROUP_VERBS = {
    "जाए": "जाएँ", "आए": "आएँ", "करे": "करें", "रखे": "रखें", "बैठे": "बैठें", "लौटे": "लौटें", "बताए": "बताएँ", "छाँटे": "छाँटें",
    "पढ़े": "पढ़ें", "लिखे": "लिखें", "बनाए": "बनाएँ", "दिखाए": "दिखाएँ", "सुनाए": "सुनाएँ", "खोले": "खोलें", "गिने": "गिनें", "जोड़े": "जोड़ें",
}
# समूह must be the SUBJECT: not 'समूह को / से / के / में / पर / ने' (the group is then an object: 'हर बच्चा ... समूह को सुनाए' is right), not a
# relative 'जो समूह ... करे, वह ...', not 'हर समूह ... बताए' (each group: the singular, like 'हर बच्चा लिखे'), and no other subject ('हर बच्चा', 'एक बच्चा', 'मॉनिटर', 'वह') between it and the verb.
_GROUP_VERB_RE = re.compile(rf"((?<!जो )(?<!हर )समूह(?![{_DEV}])(?!\s+(?:को|से|के|की|का|में|पर|ने)(?![{_DEV}]))[^।;!?\n'‘\"“«]{{0,90}}?\s)("
                            + "|".join(sorted(GROUP_VERBS, key=len, reverse=True)) + rf")(?![{_DEV}])(?=\s*(?:[।;!?,]|और(?![{_DEV}])|$))")
_OTHER_SUBJECT = re.compile(rf"(?<![{_DEV}])(?:हर बच्चा|एक बच्चा|मॉनिटर|वह|वे|बच्चे)(?![{_DEV}])")


def polite_group_verbs(text: str) -> tuple:
    """(text, n): 'प्रगतिशील समूह ... छाँटे और ... बताए।' -> '... छाँटें और ... बताएँ।'. Idempotent."""
    total = 0

    def fix(m):
        nonlocal total
        if _OTHER_SUBJECT.search(m.group(1)):
            return m.group(0)
        total += 1
        return m.group(1) + GROUP_VERBS[m.group(2)]

    for _ in range(6):                     # one verb per pass in each clause; a clause rarely has more than two
        new = _GROUP_VERB_RE.sub(fix, text)
        if new == text:
            break
        text = new
    return text, total


# the Tens | Ones frame: only in a sentence about place value, and only the whole word
_PLACE_CUES = ("दहाई", "इकाई", "सैकड़ा", "हज़ार", "हासिल", "कॉलम", "रेखा", "बिंदु")
_FRAME_PHRASE = re.compile(rf"दहाई\s*[|\-]\s*इकाई का {_word('खाना')}")
_FRAME_WORD = re.compile(_word("खाना") + "|" + _word("खाने") + "|" + _word("ग्रिड"))       # "ग्रिड" too: the model sometimes calls the frame a grid
_FRAME_IN = re.compile(_word("खाने") + " में")            # "खाने में हासिल लिखकर": with nothing before it that says which frame, say it in full
_SENTENCE = re.compile(r"[^।?!]*[।?!]?\s*")


def _soften_frame(text: str, changes: list) -> str:
    out = []
    for part in _SENTENCE.findall(text):
        if part and any(c in part for c in _PLACE_CUES):
            new = _FRAME_PHRASE.sub(f"दहाई-इकाई का {FRAME_WORD}", part)
            new = _FRAME_IN.sub(lambda m: (f"{FRAME_WORD} में" if re.search("(?:दहाई|इकाई|हासिल|सैकड़ा)[^।]{0,14}$", new[:m.start()]) else f"दहाई-इकाई के {FRAME_WORD} में"), new)
            new = _FRAME_WORD.sub(FRAME_WORD, new)
            if new != part:
                changes.append("frame")
            part = new
        out.append(part)
    return "".join(out)


_QUOTED = re.compile(r"""(["“«'‘])(.*?)(["”»'’])""", re.S)


def soften_text(text: str, *, polite: bool = True, frame: bool = True, protect_quotes: bool = False) -> tuple:
    """(new text, list of what changed). Idempotent: running it again changes nothing.
    protect_quotes: on a worksheet, text inside quotation marks is material the child reads ('रानी, यहाँ आओ'), so only the text OUTSIDE quotes is softened.
    (A teacher's quoted speech is the opposite: it is addressed to the children and must be softened, so teacher fields do not use it.)"""
    if protect_quotes and _QUOTED.search(text):
        out, last, changes = [], 0, []
        for m in _QUOTED.finditer(text):
            part, ch = soften_text(text[last:m.start()], polite=polite, frame=frame)
            out.append(part); changes += ch; out.append(m.group(0)); last = m.end()
        part, ch = soften_text(text[last:], polite=polite, frame=frame)
        return "".join(out) + part, changes + ch
    changes = []
    new = text
    for pat, rep in GENDER_FIXES:
        new, n = pat.subn(rep, new)
        changes += ["grammar"] * n
    for pat, rep in WORD_SWAPS:
        new, n = pat.subn(rep, new)
        changes += ["wording"] * n
    if polite:
        for pat, rep in POLITE_PHRASES:
            new, n = pat.subn(rep, new)
            changes += ["respectful"] * n
        new, n = _POLITE_VERB_RE.subn(lambda m: POLITE_VERBS[m.group(1)], new)
        changes += ["respectful"] * n
        new, n = _GIVE_RE.subn(r"\1दें", new)
        changes += ["respectful"] * n
        new, n = polite_group_verbs(new)
        changes += ["respectful"] * n
    if frame:
        new = _soften_frame(new, changes)
    return new, changes


# which fields of a plan are what: the teacher's own speech to the class, the teacher's notes, and what is printed for the children
_TEACHER_SPEECH = [r"^\.anchor\.(?!title_hi)\w+_hi$", r"^\.rotation_schedule\.blocks\[\]\.(?:script_hi|other_groups_hi)$",
                   r"^\.rotation_schedule\.blocks\[\]\.talking_points\.\w+$", r"^\.classroom_management\.independent_activities_hi\.\w+$"]
_TEACHER_NOTES = [r"^\.prep_hi\[\]$"]
_PRINTED = [r"^\.worksheets\.\w+\.instructions_hi$", r"^\.worksheets\.\w+\.problems\[\]\.(?:problem_hi|word_problem_text)$",
            r"^\.rotation_schedule\.blocks\[\]\.cfu\[\]\.(?:question_hi|shows_hi)$"]        # CFU: only the teacher's QUESTION is softened, and quote-safe. expected_hi and wrong_answer_hi are material (a right or wrong answer), never changed
_SPEECH_RE = [re.compile(p) for p in _TEACHER_SPEECH]
_NOTES_RE = [re.compile(p) for p in _TEACHER_NOTES]
_PRINTED_RE = [re.compile(p) for p in _PRINTED]


# The teacher's lines as short polite instructions, the way NCERT's teacher notes write them ("बोर्ड पर लिखें", "बच्चों से पूछें"), never the
# teacher's first person. Until 15 Nov the app wrote "मैं बोर्ड पर लिखता/लिखती हूँ" (the app cannot know the teacher's gender), and the user found
# the paired forms slow to read in a busy classroom. Quoted words (what is said to the children, a dictation sentence, a letter) are never changed:
# the old code also paired a girl's words inside a quoted letter ("मैं गाँव में रहता/रहती हूँ"). Idempotent.
_D = "ऀ-ॣॱ-ॿ"          # Devanagari letters and marks: not । ॥ (a word before a full stop still ends there), not the digits
_QUOTE_SPAN = re.compile(r"'[^']*'|‘[^’]*’|\"[^\"]*\"|“[^”]*”|«[^»]*»")
_IMP_SPECIAL = {"दे": "दें", "ले": "लें", "कर": "करें", "हो": "हों", "पी": "पिएँ", "द": "दें", "ल": "लें"}
# a clause spoken TO the children ("मैं आपको तीन सुराग दूँगी"): an instruction to the teacher would not fit, so it is left (and reported by the check)
_ADDRESS = re.compile(rf"(?<![{_D}])(?:आप|आपको|आपके|आपकी|तुम|तुम्हें|तुम्हारे|तुम्हारी|बच्चो)(?![{_D}])")
_ME = re.compile(rf"(?<![{_D}])मैं(?![{_D}])\s*")


def _imperative(stem: str) -> str:
    if stem in _IMP_SPECIAL:
        return _IMP_SPECIAL[stem]
    return stem + ("एँ" if stem.endswith(("ा", "ो", "आ")) else "ें")


_SAKNA = re.compile(rf"(?<![{_D}/])सक(?:ता/सकती|ती/सकता) हूँ")                                       # "छाँट सकता/सकती हूँ" -> "छाँट सकते हैं"
_RAHA = re.compile(rf"(?<![{_D}/])([{_D}]+) रह(?:ा/रही|ी/रहा) हूँ")                                   # "पढ़ा रहा/रही हूँ" -> "पढ़ाएँ"
_PAIR_NOW = re.compile(rf"(?<![{_D}/])([{_D}]+?)(?:ता/\1ती|ती/\1ता) हूँ")                            # "लिखता/लिखती हूँ" -> "लिखें"
_PAIR_FUT = re.compile(rf"(?<![{_D}/])([{_D}]+?)(ूँ|ऊँ)(?:गा/\1\2गी|गी/\1\2गा)(?![{_D}])")           # "बोलूँगा/बोलूँगी" -> "बोलें", "दिखाऊँगा/दिखाऊँगी" -> "दिखाएँ"
# one gender only: changed only when "मैं" is in the same clause (a line of a story without "मैं" is left alone)
_ONE_SAKNA = re.compile(rf"(?<![{_D}/])सक(?:ता|ती) हूँ")
_ONE_RAHA = re.compile(rf"(?<![{_D}/])([{_D}]+) रह(?:ा|ी) हूँ")
_ONE_NOW = re.compile(rf"(?<![{_D}/])([{_D}]+?)(?:ता|ती) हूँ")
_ONE_FUT = re.compile(rf"(?<![{_D}/])([{_D}]+?)(ूँ|ऊँ)(?:गा|गी)(?![{_D}/])")


def _fut(m) -> str:
    return _imperative(m.group(1))


def _clause_to_instruction(c: str) -> tuple:
    if _ADDRESS.search(c):
        return c, 0
    n = 0
    for pat, rep in ((_SAKNA, "सकते हैं"), (_RAHA, lambda m: _imperative(m.group(1))), (_PAIR_NOW, lambda m: _imperative(m.group(1))), (_PAIR_FUT, _fut)):
        c, k = pat.subn(rep, c)
        n += k
    if _ME.search(c):
        for pat, rep in ((_ONE_SAKNA, "सकते हैं"), (_ONE_RAHA, lambda m: _imperative(m.group(1))), (_ONE_NOW, lambda m: _imperative(m.group(1))), (_ONE_FUT, _fut)):
            c, k = pat.subn(rep, c)
            n += k
    return c, n


_SENTENCE_SPLIT = re.compile(r"([।?!:;\n])")
_COMMA_SPLIT = re.compile(r"(,)")
_OTHER_ME_VERB = re.compile(rf"[{_D}](?:ूँ|ऊँ)(?![{_D}])|(?<![{_D}])हूँ")           # "अगर मैं जूते छाँटूँ": that "मैं" stays


def _drop_me(c: str) -> str:
    if not _ME.search(c) or _OTHER_ME_VERB.search(c):
        return c
    lead = c[:len(c) - len(c.lstrip())]
    return lead + _ME.sub("", c.lstrip())


def _sentence_to_instruction(s: str) -> tuple:
    """Converted clause by clause (a comma may separate a clause spoken to the children); "मैं" goes from every clause of a sentence that had a
    verb converted ("मैं बीज, कंकड़ और बटन मिलाकर दिखाऊँगा/दिखाऊँगी" -> "बीज, कंकड़ और बटन मिलाकर दिखाएँ")."""
    parts = _COMMA_SPLIT.split(s)
    n = 0
    for i in range(0, len(parts), 2):
        parts[i], k = _clause_to_instruction(parts[i])
        n += k
    if n:
        parts = [p if i % 2 else _drop_me(p) for i, p in enumerate(parts)]
    return "".join(parts), n


def teacher_instructions(text: str) -> tuple:
    """(new text, changes): the teacher's first person outside quotes as a polite instruction. "मैं बोर्ड पर 'पुल' लिखता/लिखती हूँ।" ->
    "बोर्ड पर 'पुल' लिखें।"; "फिर मैं पूछूँगा/पूछूँगी:" -> "फिर पूछें:". Quoted text is kept exactly."""
    spans = []

    def mask(m):
        spans.append(m.group(0))
        return f"\x00{len(spans) - 1}\x01"

    masked = _QUOTE_SPAN.sub(mask, text)
    parts = _SENTENCE_SPLIT.split(masked)
    n = 0
    for i in range(0, len(parts), 2):
        parts[i], k = _sentence_to_instruction(parts[i])
        n += k
    new = re.sub(r"\x00(\d+)\x01", lambda m: spans[int(m.group(1))], "".join(parts))
    return new, ["instruction"] * n


# the gendered first person that teacher_instructions leaves (a clause spoken to the children), for the plan check
_GENDERED_ME = re.compile(rf"(?<![{_D}])(?:[{_D}]+(?:ता|ती)(?:/[{_D}]+)? हूँ|(?:रहा|रही|चुका|चुकी) हूँ|[{_D}]+(?:ूँ|ऊँ)(?:गा|गी))(?![{_D}])")
# the teacher's own words in quotes ('देखें, मैं रंग से छाँट रही हूँ', found in the v2 review, 20 Nov): a quote with मैं and a gendered verb, unless it
# is text WRITTEN for the children (बोर्ड पर लिखें: 'मैं स्कूल जाता हूँ।' is a sentence to read, and is fine)
_QUOTED = re.compile(r"(['‘\"“])(.+?)(['’\"”])")
_WRITTEN_BEFORE = re.compile(r"(लिख|बोर्ड|वाक्य|पढ़|उदाहरण|कॉपी)[^'‘\"“]{0,25}$")


def _gendered_in_quotes(text: str):
    for m in _QUOTED.finditer(text):
        inner = m.group(2)
        if ("मैं" in inner or _ME_HOON.search(inner)) and _GENDERED_ME.search(inner) and not _WRITTEN_BEFORE.search(text[:m.start()]):
            return _GENDERED_ME.search(inner).group(0)
    return None
# Hindi marks named wrongly (15 Nov, a live plan: "'है' पर ऊपर दो बिंदी वाला ै"): ै is the ऐ की मात्रा (two strokes); a बिंदी is ं
# (the mark ै or े written on its own, not inside a word; "दो बिंदु वाला विसर्ग ः" is right and is not flagged)
_WRONG_MARK = re.compile(rf"(?:बिंदी|बिंदियों|बिंदु|बिन्दी|बिन्दु)(?:\s*(?:वाला|वाली|वाले|का|की))?\s*['‘(]?(?<![{_D}])[ैे](?!ं)")


_ME_VERBS = [(re.compile(rf"([{_D}]+)(?:ता|ती) हूँ(?![{_D}])"), r"\1ते हैं"),         # छाँटता/छाँटती हूँ -> छाँटते हैं
             (re.compile(rf"([{_D}]+)(?:ूँगा|ूँगी)(?![{_D}])"), r"\1ेंगे"),            # छाँटूँगा/छाँटूँगी -> छाँटेंगे
             (re.compile(rf"([{_D}]+)ऊँ(?:गा|गी)(?![{_D}])"), r"\1एँगे"),              # दिखाऊँगा/दिखाऊँगी -> दिखाएँगे
             (re.compile(r"(?:रहा|रही) हूँ"), "रहे हैं"), (re.compile(r"(?:चुका|चुकी) हूँ"), "चुके हैं")]
# a paired form in a quote ('मैं छाँट रहा/रही हूँ') is first made one form, so the plural is not left half-done ('रहा/रहे हैं', found 22 Nov)
_SLASH_PAIR = re.compile(rf"(?<![{_D}/])([{_D}]+)/([{_D}]+)(?![{_D}/])")


def _one_form(m) -> str:
    a, b = m.group(1), m.group(2)
    return a if len(a) == len(b) and a[:-1] == b[:-1] and {a[-1], b[-1]} == {"ा", "ी"} else m.group(0)


# 'मैं' with a verb that is ALREADY plural ('देखिए, मैं रंग देखकर छाँट रहे हैं।', the v2 review, 22 Nov): the model kept 'मैं' and made only the
# verb neutral. The check above looks for a gendered verb, so this got through; such a sentence becomes 'हम ...'.
_PLURAL_VERB = re.compile(rf"(?:(?<![{_D}])(?:रहे|चुके) हैं|[{_D}]+ते हैं|[{_D}]+(?:ेंगे|एँगे))(?![{_D}])")
_ME_WORD = re.compile(rf"(?<![{_D}])मैं(?![{_D}])")
_ME_HOON = re.compile(rf"(?<![{_D}])(?:[{_D}]+(?:ता|ती)|रहा|रही|चुका|चुकी) हूँ(?![{_D}])")       # a gendered verb with 'हूँ': only 'मैं' takes it
_SENT_PARTS = re.compile(r"[^।?!]*[।?!]?")


def neutral_quotes(text: str) -> tuple:
    """(text, n): in the teacher's own quoted speech (not text written for the children), a gendered 'मैं' sentence becomes the neutral 'हम'
    form: 'मैं रंग से छाँटूँगी' -> 'हम रंग से छाँटेंगे', 'मैं छाँट रही हूँ' -> 'हम छाँट रहे हैं'. Only a quote that has 'मैं' and a gendered
    verb is touched (20 Nov, the v2 review: the model still wrote some after the rule)."""
    n = 0

    def fix(m):
        nonlocal n
        inner = m.group(2)
        if _WRITTEN_BEFORE.search(m.string[:m.start()]):
            return m.group(0)
        if "मैं" not in inner:
            # the subject left out ('देखिए, यह लाल है, इसे यहाँ रखता हूँ', the fourth review, 22 Nov): a 'हूँ' verb is still the teacher's own
            # first person, so its gendered form becomes the neutral plural ('रखते हैं'); a verb with no 'हूँ' is not first person and is left
            one = _SLASH_PAIR.sub(_one_form, inner)
            if not _ME_HOON.search(one):
                return m.group(0)
            new = one
            for pat, rep in _ME_VERBS:
                new = pat.sub(rep, new)
            if new != inner:
                n += 1
            return m.group(1) + new + m.group(3)
        if not _GENDERED_ME.search(_SLASH_PAIR.sub(_one_form, inner)):
            # no gendered verb: only a sentence whose verb is already plural changes its 'मैं' (a 'मैं' with no verb of its own is left)
            new = "".join(_ME_WORD.sub("हम", s) if _ME_WORD.search(s) and _PLURAL_VERB.search(s) else s for s in _SENT_PARTS.findall(inner))
            if new != inner:
                n += 1
            return m.group(1) + new + m.group(3)
        new = _ME_WORD.sub("हम", _SLASH_PAIR.sub(_one_form, inner))
        for pat, rep in _ME_VERBS:
            new = pat.sub(rep, new)
        if new != inner:
            n += 1
        return m.group(1) + new + m.group(3)

    return _QUOTED.sub(fix, text), n


def neutral_quotes_in_plan(plan: dict) -> int:
    """neutral_quotes on every teacher-speech field of a plan, in place. Returns how many quotes were changed."""
    total = 0

    def visit(o, path=""):
        nonlocal total
        if isinstance(o, dict):
            for k in list(o):
                v = o[k]
                p = f"{path}.{k}"
                if isinstance(v, str) and (any(r.match(p) for r in _SPEECH_RE) or p.endswith(".question_hi")):
                    o[k], n = neutral_quotes(v)
                    total += n
                else:
                    visit(v, p)
        elif isinstance(o, list):
            for v in o:
                visit(v, f"{path}[]")

    visit(plan)
    return total


# आकार is SIZE (बड़ा/छोटा) and आकृति is SHAPE (गोल, तिकोना, चौकोर) where a skill sorts by both (N0.1.1: "रंग, आकार, आकृति"). The third review of the
# v2 plans (22 Nov) found "गोल एक तरफ़, चौकोर दूसरी तरफ़ ... मेरा नियम है आकार" and a show-me question "आकार के नियम से" whose expected answer was
# the shape pair. Only those skills: in geometry 'किस आकार का है: गोला या घन' is ordinary Hindi. A check for the review, not a repair (the
# meaning, not a word, is wrong). Flagged: आकार, no आकृति, and either two different shapes or a shape with no size word.
SIZE_SHAPE_SKILLS = {"N0.1.1"}
_AAKAAR = re.compile(rf"(?<![{_D}])आकार(?![{_D}])")
_SHAPES = re.compile(rf"(?<![{_D}])(गोल|गोला|गोले|गोली|चौकोर|तिकोन[ाीे]|त्रिभुज|वर्ग|वृत्त|आयत|तारा|तारे|तारों)(?![{_D}])")
_SIZES = re.compile(rf"(?<![{_D}])(?:बड़[ाीे]|छोट[ाीे]|बड़े-छोटे|लंब[ाीे]|मोट[ाीे]|पतल[ाीे])(?![{_D}])")
_SHAPE_STEM = {"गोला": "गोल", "गोले": "गोल", "गोली": "गोल", "तिकोना": "तिकोन", "तिकोनी": "तिकोन", "तिकोने": "तिकोन", "तारे": "तारा", "तारों": "तारा"}


def _size_shape_mixed(text: str) -> bool:
    if not _AAKAAR.search(text) or "आकृति" in text:
        return False
    shapes = {_SHAPE_STEM.get(s, s) for s in _SHAPES.findall(text)}
    return len(shapes) >= 2 or (len(shapes) == 1 and not _SIZES.search(text))


def check_size_shape(plan: dict, skill_ids) -> list:
    """Warnings where a sorting skill's teacher text calls a SHAPE rule 'आकार'. A show-me question is read with its answer and what it shows."""
    if not SIZE_SHAPE_SKILLS & {s for s in (skill_ids or []) if s}:
        return []
    out = []
    for i, b in enumerate((plan.get("rotation_schedule") or {}).get("blocks") or []):
        for k, v in (b.get("talking_points") or {}).items():
            if isinstance(v, str) and _size_shape_mixed(v):
                out.append(f"blocks[{i}].talking_points.{k}: 'आकार' used with shapes («{_AAKAAR.search(v).group(0)}»): आकार is size (बड़ा/छोटा), आकृति is shape (गोल, चौकोर)")
        for k in ("script_hi", "other_groups_hi"):
            if isinstance(b.get(k), str) and _size_shape_mixed(b[k]):
                out.append(f"blocks[{i}].{k}: 'आकार' used with shapes: आकार is size (बड़ा/छोटा), आकृति is shape (गोल, चौकोर)")
        for j, q in enumerate(b.get("cfu") or []):
            if not isinstance(q, dict):
                continue
            asked = " ".join(str(q.get(k) or "") for k in ("question_hi", "expected_hi"))
            shows = str(q.get("shows_hi") or "")
            # the question names one rule and what it shows names the other ('आकार के नियम से' / 'आकृति के नियम से जोड़ी'): flagged too
            crossed = bool(_AAKAAR.search(asked)) and "आकृति" not in asked and "आकृति" in shows
            if _size_shape_mixed(asked + " " + shows) or _size_shape_mixed(asked) or crossed:
                out.append(f"blocks[{i}].cfu[{j}]: a show-me question names 'आकार' with shapes: check that the expected answer sorts by SIZE (आकार), not shape (आकृति)")
    return out


# the model correcting itself in the text (22 Nov, the review of the recorded-plan drafts: "जैसे आम 24 और दूध 36 के बजाय सब्ज़ी 35 और केला 18
# नहीं, बल्कि आम 24 और चावल 45"; "'हम एक संख्या बोलते हैं' के बजाय शिक्षक बोले 'सत्रह'"; in the library "28 सेमी के बजाय चौड़ाई 2 सेमी रखें").
# 'के बजाय' (instead of) is also ordinary Hindi ("शब्द बोलने के बजाय चित्र बनाए"), so this FLAGS for a reader, like 'यानी'; it repairs nothing.
_SELF_CORRECTION = re.compile(rf"(?<![{_D}])(?:यानी|नहीं,\s*बल्कि|के बजाय)(?![{_D}])")


def check_self_corrections(plan: dict) -> list:
    """Warnings for a possible self-correction left in the teacher's lines or a printed sheet: to be read, not repaired."""
    out = []

    def visit(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if not str(k).startswith("_"):
                    visit(v, f"{path}.{k}")
        elif isinstance(o, list):
            for v in o:
                visit(v, f"{path}[]")
        elif isinstance(o, str) and (any(r.match(path) for r in _SPEECH_RE + _NOTES_RE + _PRINTED_RE) or path.endswith(".question_hi")):
            m = _SELF_CORRECTION.search(o)
            if m:
                out.append(f"{path}: a possible self-correction («…{o[max(0, m.start() - 40):m.end() + 30]}…»): read it; write only the final form")

    visit(plan)
    return out


def check_teacher_text(plan: dict) -> list:
    """Warnings for the plan check: a gendered first person left in the teacher's lines (outside quotes), and a Hindi mark named wrongly."""
    out = []

    def visit(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                visit(v, f"{path}.{k}")
        elif isinstance(o, list):
            for v in o:
                visit(v, f"{path}[]")
        elif isinstance(o, str):
            teacher = any(r.match(path) for r in _SPEECH_RE) or path.endswith(".question_hi")
            if teacher and _GENDERED_ME.search(_QUOTE_SPAN.sub("", o)):
                out.append(f"{path}: the teacher's first person with a gender («{_GENDERED_ME.search(_QUOTE_SPAN.sub('', o)).group(0)}»); write it as an instruction (बोलें, लिखें)")
            elif teacher and _gendered_in_quotes(o):
                out.append(f"{path}: the teacher's own words in quotes have a gendered first person («{_gendered_in_quotes(o)}»); write 'देखिए, अब हम ... करते हैं'")
            if (teacher or any(r.match(path) for r in _PRINTED_RE)) and _WRONG_MARK.search(o):
                out.append(f"{path}: a Hindi mark named wrongly («{_WRONG_MARK.search(o).group(0)}»): ै is the ऐ की मात्रा, े the ए की मात्रा, ं a बिंदी, ँ a चंद्रबिंदु")

    visit(plan)
    return out


def soften_plan(plan: dict) -> dict:
    """Apply the style to a generated plan, in place. Returns how many changes of each kind were made. Word problems, passages,
    answers, names and the explanations are never touched."""
    counts = {}

    def visit(o, path=""):
        if isinstance(o, dict):
            for k in list(o):
                v = o[k]
                if isinstance(v, str):
                    handle(o, k, v, f"{path}.{k}")
                else:
                    visit(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, str):
                    handle(o, i, v, f"{path}[]")
                else:
                    visit(v, f"{path}[]")

    def handle(container, key, text, path):
        speech = any(r.match(path) for r in _SPEECH_RE)
        notes = any(r.match(path) for r in _NOTES_RE)
        printed = any(r.match(path) for r in _PRINTED_RE)
        if not (speech or notes or printed):
            return
        new, changes = soften_text(text, polite=speech or (printed and POLITE_IN_WORKSHEETS), frame=True, protect_quotes=printed)
        if speech or path.endswith(".cfu[].question_hi"):
            new, ch = teacher_instructions(new)
            changes += ch
        if new != text:
            container[key] = new
            for c in changes:
                counts[c] = counts.get(c, 0) + 1

    visit(plan)
    return counts
