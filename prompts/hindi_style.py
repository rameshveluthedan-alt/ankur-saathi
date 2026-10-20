"""
Hindi style for the words a teacher reads and says (docs/HINDI_STYLE.md).

From Vaishnavi's review of the N2.3.2 plan (Oct 2026). The vocabulary was generally accurate, but the tone should be warmer and more
respectful, and one term was unclear for young children:

  * "फालतू बंडल"            -> "अतिरिक्त बंडल"        (the word reads as "useless")
  * "चुपचाप शुरू करें"       -> "शांति से शुरू करें"    (sounds like a reprimand)
  * "मेरे पास आओ", "अपना काम बंद करो", "छड़ियाँ मॉनिटर को दो"
                              -> "आएँ", "रोक दें", "दें"  (model respectful language: it is a goal of foundational learning)
  * "दहाई | इकाई का खाना"   -> "दहाई-इकाई का बॉक्स"   (खाना is ambiguous for a 6-year-old; बॉक्स matches the printed place-value grids)
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
POLITE_IN_WORKSHEETS = False      # worksheet instructions are printed for the children; the textbook style (जोड़ो, लिखो) is kept until she says otherwise

STYLE_PROMPT = (
    "- When the teacher speaks TO THE CHILDREN (transitions, tasks, questions, instructions for independent work), use respectful plural forms, "
    "never abrupt 'तुम' commands: write 'मेरे पास आएँ', 'अपना काम रोक दें', 'कॉपी बंद करें', 'छड़ियाँ मॉनिटर को दें', 'अपनी जगह जाएँ', 'सुनें', "
    "not 'आओ', 'बंद करो', 'दो', 'जाओ', 'सुनो'. (Worksheet instructions printed for the children keep the textbook style.)\n"
    "- Keep every line warm and positive. Never use 'फालतू' (write 'अतिरिक्त') or 'चुपचाप' (write 'शांति से' or 'बिना शोर किए').\n"
    f"- Call the Tens | Ones frame 'दहाई-इकाई का {FRAME_WORD}' (plural '{FRAME_WORD}'), never 'खाना' or 'खाने'. Keep 'हासिल', 'खुली छड़ियाँ' and "
    "'शब्द-सवाल' as they are, and end the lesson with a praise for the whole class such as 'आज बहुत अच्छा काम हुआ'.\n"
    "- दहाई and इकाई are feminine: write 'कितनी दहाई और कितनी इकाई', not 'कितने दहाई'.\n"
)

_DEV = "\u0900-\u0963\u0966-\u097F"          # letters, vowel signs and digits: NOT the danda ।  (U+0964) or ॥ (U+0965), which are punctuation


def _word(w: str) -> str:
    """The whole word only: 'खाना' must not match inside 'सिखाना' or 'दिखाना'."""
    return rf"(?<![{_DEV}]){w}(?![{_DEV}])"


# word-level swaps that are safe wherever they appear in a teacher's text or a printed instruction
WORD_SWAPS = [
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

# the Tens | Ones frame: only in a sentence about place value, and only the whole word
_PLACE_CUES = ("दहाई", "इकाई", "सैकड़ा", "हज़ार", "हासिल", "कॉलम", "रेखा", "बिंदु")
_FRAME_PHRASE = re.compile(rf"दहाई\s*[|\-]\s*इकाई का {_word('खाना')}")
_FRAME_WORD = re.compile(_word("खाना") + "|" + _word("खाने"))
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


def soften_text(text: str, *, polite: bool = True, frame: bool = True) -> tuple:
    """(new text, list of what changed). Idempotent: running it again changes nothing."""
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
    if frame:
        new = _soften_frame(new, changes)
    return new, changes


# which fields of a plan are what: the teacher's own speech to the class, the teacher's notes, and what is printed for the children
_TEACHER_SPEECH = [r"^\.anchor\.(?!title_hi)\w+_hi$", r"^\.rotation_schedule\.blocks\[\]\.(?:script_hi|other_groups_hi)$",
                   r"^\.rotation_schedule\.blocks\[\]\.talking_points\.\w+$", r"^\.classroom_management\.independent_activities_hi\.\w+$"]
_TEACHER_NOTES = [r"^\.prep_hi\[\]$"]
_PRINTED = [r"^\.worksheets\.\w+\.instructions_hi$"]
_SPEECH_RE = [re.compile(p) for p in _TEACHER_SPEECH]
_NOTES_RE = [re.compile(p) for p in _TEACHER_NOTES]
_PRINTED_RE = [re.compile(p) for p in _PRINTED]


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
        new, changes = soften_text(text, polite=speech or (printed and POLITE_IN_WORKSHEETS), frame=True)
        if new != text:
            container[key] = new
            for c in changes:
                counts[c] = counts.get(c, 0) + 1

    visit(plan)
    return counts
