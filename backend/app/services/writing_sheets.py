"""
Writing skills get WRITING worksheets (12 Nov 2026, the fix for docs/KNOWN_ISSUES.md "Writing skills: the worksheets test reading, not writing").

Before: the literacy worksheet rules made every Progressor and Proficient sheet a passage with comprehension questions, whatever the group's skill,
and the code put the bank's reading questions first. So a group taught to WRITE was checked on READING, and the photo after class recorded reading
as evidence of a writing skill (docs/drafts/PLAN_REVIEW_L2.7.2.md).

Now each group's sheet follows ITS OWN skill:
  reading      every literacy skill outside strand 7: the passage sheet, as before.
  formation    L0.7.1, L0.7.2, L1.7.1, L1.7.2, L1.7.3 (strokes, letters, words, short sentences): an example and writing items, never a passage.
  usage        L2.7.3 (punctuation), L3.7.2 (grammar): short items on the rule, each with one checkable answer, never a passage.
  dictation    L2.7.1: the teacher dictates; the child's sheet has only numbered blank lines. The sentences are in the teacher's plan only
               (worksheet.dictation_sentences), never on the sheet or the board. The code builds the lines from the sentences.
  composition  L2.7.2, L3.7.1, L3.7.3: ONE writing task on the topic the You Do names (never the teacher's own model topic), lined space, a 3-5 point
               checklist instead of an answer key (printed on the sheet, so the child can tick it too), and 2-3 short items on the parts
               (joining two sentences, ending one with ।, putting sentences in order), each with one checkable answer.
  fluency      L1.5.1, L2.5.1, L2.5.2, L3.5.1, L3.5.2 (reading aloud: pace, accuracy, pauses, expression; 14 Nov 2026): PRACTICE while the teacher listens to
               a few children one minute each: warm-up words to read to a partner, the group's (bank) passage read aloud three times with a tick each
               time, pair reading, at most 3 short questions; for L2.5.2 and L3.5.2 also 3-4 sentences with । ? ! to read with the right pause or
               expression. The passage is KEPT (unlike the writing kinds). Never marked from a photo: the check is the teacher's one-minute reading.
The photo analysis marks a composition against its checklist and a dictation against the dictated sentences (vision_spec, prompts/vision_analysis.py).

PURE (no database, no network): tested in backend/tests/test_writing_sheets.py.
"""
import re

LEVELS = ("beginner", "progressor", "proficient")
_WRITING = re.compile(r"^L\d+\.7\.\d+$")
DICTATION = {"L2.7.1"}
COMPOSITION = {"L2.7.2", "L3.7.1", "L3.7.3"}
USAGE = {"L2.7.3", "L3.7.2"}          # punctuation, and grammar (gender, number, tense): short items with one checkable answer
CHECKLIST_MIN, CHECKLIST_MAX = 3, 5
FLUENCY = {"L1.5.1", "L2.5.1", "L2.5.2", "L3.5.1", "L3.5.2"}      # reading aloud (oral_reading)
EXPRESSION = {"L2.5.2", "L3.5.2"}                                  # pauses at punctuation, expression: also sentences to read with the marks
WARMUP_MIN, WARMUP_MAX = 6, 8
FLUENCY_QUESTIONS_MAX = 3
TASK_ANSWER = "CHECKLIST"          # the writing task's "answer": the photo analysis uses the checklist instead of a key


def sheet_kind(competency_id, domain_id="r1_literacy"):
    """'reading' | 'fluency' | 'formation' | 'usage' | 'dictation' | 'composition' for a literacy skill; None for numeracy."""
    if domain_id != "r1_literacy" or not competency_id:
        return None
    cid = str(competency_id)
    if cid in DICTATION:
        return "dictation"
    if cid in COMPOSITION:
        return "composition"
    if cid in USAGE:
        return "usage"
    if cid in FLUENCY:
        return "fluency"
    if _WRITING.match(cid):
        return "formation"
    return "reading"


def group_kinds(group_skill_ids, domain_id) -> dict:
    """{level: kind} for the groups whose skill is known."""
    return {lvl: sheet_kind(cid, domain_id) for lvl, cid in (group_skill_ids or {}).items() if cid and sheet_kind(cid, domain_id)}


def writing_levels(group_skill_ids, domain_id) -> set:
    """The groups whose sheet has NO passage (the writing kinds). A fluency group keeps its bank passage: it reads it aloud."""
    return {lvl for lvl, k in group_kinds(group_skill_ids, domain_id).items() if k not in ("reading", "fluency")}


def prompt_section(group_skill_ids, domain_id) -> str:
    """The prompt's rules for the groups on a writing skill (empty when no group is). They OVERRIDE the passage rules for those groups."""
    kinds = group_kinds(group_skill_ids, domain_id)
    writing = {lvl: k for lvl, k in kinds.items() if k not in ("reading", "fluency")}
    fluency = [lvl for lvl in LEVELS if kinds.get(lvl) == "fluency"]
    if not writing:
        return _fluency_section(group_skill_ids, fluency)
    lines = ["\n### WRITING WORKSHEETS (these groups are taught a WRITING skill: their worksheet checks WRITING, not reading)"]
    for lvl in LEVELS:
        if lvl in writing:
            lines.append(f"- {lvl} ({group_skill_ids[lvl]}): sheet_kind \"{writing[lvl]}\"")
    lines.append("For these groups the literacy worksheet rules above about passages do NOT apply: passage_block null, no comprehension questions. Set \"sheet_kind\" on the worksheet.")
    if "composition" in writing.values():
        lines += [
            "COMPOSITION sheet (\"composition\"):",
            "- \"writing_task\": {\"topic_hi\": the topic, \"lines\": 6-10}. Problem 1 IS the writing task: problem_hi states the task with its topic and the number of sentences "
            "(for example 'अपने गाँव के मेले पर 3-5 जुड़े हुए वाक्य लिखिए।'), row_type null, answer_type \"lines\", answer \"CHECKLIST\".",
            "- The topic must be the one the group's You Do names, and must NOT be the topic, sentence or example the teacher models in the I Do or We Do.",
            f"- \"checklist\": {CHECKLIST_MIN}-{CHECKLIST_MAX} items [{{\"item_hi\": \"...\", \"item_en\": \"...\"}}], each one thing a teacher can SEE in the writing "
            "(for example: कम से कम 3 वाक्य · सभी वाक्य विषय पर · हर वाक्य के अंत में । · वाक्य 'और / फिर / क्योंकि' से जुड़े). Fit it to the group's skill and grade.",
            "- Problems 2-4: short items on the PARTS of the skill, each with ONE checkable answer (join two given sentences with a joining word, put a full stop "
            "where a sentence ends, put 3 jumbled sentences in order). Never a reading-comprehension question. A fill-in item that offers its options "
            "in brackets ('(और / फिर)') has one of THOSE options as its answer. Never reuse a sentence the teacher models in the I Do or We Do.",
            "- The You Do sends the group to the worksheet's task: it names the sheet's topic (or says 'वर्कशीट पर दिए विषय पर'), never another topic.",
            "- required_count: all of these. An optional extra: a second, shorter writing task (answer \"CHECKLIST\").",
        ]
    if "dictation" in writing.values():
        lines += [
            "DICTATION sheet (\"dictation\"):",
            "- \"dictation_sentences\": 4-6 short sentences at the group's level, using the matras the skill practises. They are for the TEACHER to read aloud: "
            "they must NOT appear in the problems, the instructions, the example, the board work or the I Do / We Do. The system builds the child's sheet "
            "(one numbered blank line per sentence) from them.",
            "- The You Do says the teacher reads each sentence aloud twice and the children write it on line 1, 2, 3...; never that they copy from the board. "
            "A dictation sheet has no extra problems: the You Do does not mention extras.",
        ]
    if "usage" in writing.values():
        lines += [
            "USAGE sheet (\"usage\": punctuation or grammar): short items that apply the rule (put the right mark at the end; change gender, number or tense; "
            "correct the mistake), each with ONE checkable answer; an example_block shows one done item. Never a passage.",
        ]
    if "formation" in writing.values():
        lines += [
            "FORMATION sheet (\"formation\"): an example_block and short writing items (letters, words or short sentences, as the skill asks), never a passage, "
            "even for a progressor or proficient group.",
        ]
    lines.append("For every writing sheet: never reuse a topic, sentence or example from the lesson or the anchor story.\n")
    return "\n".join(lines) + _fluency_section(group_skill_ids, fluency)


def _fluency_section(group_skill_ids, fluency_levels) -> str:
    """The prompt's rules for groups taught to READ ALOUD (empty when none is): a practice sheet, and a You Do that names no child."""
    if not fluency_levels:
        return ""
    lines = ["\n### READING-ALOUD WORKSHEETS (these groups are taught to READ ALOUD: their sheet is PRACTICE; the check is the teacher's one-minute reading)"]
    for lvl in fluency_levels:
        lines.append(f"- {lvl} ({group_skill_ids[lvl]}): sheet_kind \"fluency\"")
    lines += [
        "FLUENCY sheet (\"fluency\"): keep the passage_block (the system puts the bank passage in). Add:",
        f"- \"warmup_words\": {WARMUP_MIN}-{WARMUP_MAX} harder words FROM the passage (long words, conjuncts, matras the group finds hard), to read aloud to a partner before the passage.",
        "- The children read the passage aloud THREE times, softly or to a partner (the sheet prints a tick box for each reading), then read in pairs: one reads, "
        "the partner follows with a finger and marks any word that needed help.",
        f"- problems: at most {FLUENCY_QUESTIONS_MAX} short comprehension questions about the passage (so the reading is for meaning), each with one checkable answer.",
    ]
    if any(group_skill_ids.get(lvl) in EXPRESSION for lvl in fluency_levels):
        lines.append("- For a pauses or expression skill (L2.5.2, L3.5.2): \"expression_sentences\": 3-4 short sentences that end in । ? or ! (a question, an exclamation), "
                     "to read with the right pause or tone.")
    lines += [
        "- The You Do sends the group to this worksheet and says the teacher listens to the children shown in the app ('ऐप में दिखाए गए बच्चे'), one minute each, "
        "while the others practise. Never 'हर बच्चे से' or 'सभी बच्चों से' (there is no time to hear every child in one day), and never a child's name or roll number.\n",
    ]
    return "\n".join(lines)


def _strip(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _sentences_from(ws: dict) -> list:
    s = ws.get("dictation_sentences")
    if isinstance(s, list) and any(_strip(x) for x in s):
        return [_strip(x) for x in s if _strip(x)]
    # the model put them in the problems' answers instead (or printed them in the questions): take the answers
    return [_strip(p.get("answer")) for p in ws.get("problems") or [] if _strip(p.get("answer")) and _strip(p.get("answer")) != TASK_ANSWER]


def _checklist_of(ws: dict) -> list:
    out = []
    for c in ws.get("checklist") or []:
        if isinstance(c, dict) and _strip(c.get("item_hi")):
            out.append({"item_hi": _strip(c["item_hi"]), "item_en": _strip(c.get("item_en"))})
        elif isinstance(c, str) and _strip(c):
            out.append({"item_hi": _strip(c), "item_en": ""})
    return out[:CHECKLIST_MAX]


def apply_writing_sheets(plan: dict, group_skill_ids: dict, domain_id: str) -> list:
    """
    Make each writing group's sheet a writing sheet, in code, whatever the model wrote: no passage and no bank questions; a dictation sheet is rebuilt
    as numbered blank lines from its sentences (so a sentence can never be printed for the child); a composition's task is problem 1 with the checklist
    as its answer. Returns log lines. Never raises on a malformed sheet: it leaves what it cannot fix for check_writing_sheets to report.
    """
    log = []
    for lvl, kind in group_kinds(group_skill_ids, domain_id).items():
        if kind == "reading":
            continue
        ws = (plan.get("worksheets") or {}).get(lvl)
        if not isinstance(ws, dict):
            continue
        if kind == "composition" and not _checklist_of(ws) and not any(_strip(p.get("answer")).upper() == TASK_ANSWER for p in ws.get("problems") or [] if isinstance(p, dict)):
            # a sheet in the OLD shape (a recorded plan from before 12 Nov: comprehension questions on a passage, no task, no checklist): reshaping it would
            # leave questions about a passage that is gone. It is left as it is, and check_writing_sheets reports it until the plan is recorded again.
            log.append(f"{lvl}: an old-shape composition sheet (no writing task, no checklist): left as it is")
            continue
        if kind == "fluency":
            log += _apply_fluency(lvl, ws)
            continue
        ws["sheet_kind"] = kind
        if ws.get("passage_block"):
            ws["passage_block"] = None
            log.append(f"{lvl}: passage removed (a {kind} sheet)")
        probs = [p for p in ws.get("problems") or [] if isinstance(p, dict)]
        bank = [p for p in probs if p.get("from_bank")]
        if bank:
            probs = [p for p in probs if not p.get("from_bank")]
            log.append(f"{lvl}: {len(bank)} bank reading question(s) removed")
        if kind == "dictation":
            sentences = _sentences_from({**ws, "problems": probs})
            ws["dictation_sentences"] = sentences
            ws["problems"] = [{"number": n, "problem_hi": f"वाक्य {n}", "answer": s, "row_type": None, "answer_type": "lines", "answer_lines": 2,
                               "show_letter_grid": False, "diagnostic_for_misconception": None, "dictation": True} for n, s in enumerate(sentences, 1)]
            ws["required_count"] = len(sentences)
            ws["example_block"] = None if ws.get("example_block") and any(s in _strip(ws["example_block"]) for s in sentences) else ws.get("example_block")
            log.append(f"{lvl}: dictation sheet built from {len(sentences)} sentence(s), none printed for the child")
            continue
        if kind == "composition":
            ws["checklist"] = _checklist_of(ws)
            task = next((p for p in probs if _strip(p.get("answer")).upper() == TASK_ANSWER), None)
            if task is None:                                            # no task marked: an item that asks for sentences to be written
                task = next((p for p in probs if p.get("answer_type") == "lines" and re.search(r"वाक्य[^।?]*लिख|लिखिए|लिखें|लिखो", str(p.get("problem_hi") or ""))), None)
            if task is not None:
                probs.remove(task)
                topic = _strip((ws.get("writing_task") or {}).get("topic_hi"))
                lines_n = (ws.get("writing_task") or {}).get("lines")
                task.update({"answer": TASK_ANSWER, "answer_type": "lines", "row_type": None, "writing_task": True,
                             "answer_lines": max(6, min(10, int(lines_n) if isinstance(lines_n, int) and not isinstance(lines_n, bool) else 8))})
                if topic:
                    task["topic_hi"] = topic
                probs.insert(0, task)
            for n, p in enumerate(probs, 1):
                p["number"] = n
            ws["problems"] = probs
            rc = ws.get("required_count")
            if not (isinstance(rc, int) and not isinstance(rc, bool) and 1 <= rc <= len(probs)):
                ws["required_count"] = len(probs)
            continue
        ws["problems"] = probs                                         # formation: the model's items, without any passage or bank question
    return log


def _words_of(ws: dict) -> list:
    return [_strip(w) for w in ws.get("warmup_words") or [] if isinstance(w, str) and _strip(w)][:WARMUP_MAX]


def _apply_fluency(lvl: str, ws: dict) -> list:
    """A reading-aloud group's sheet: practice, its passage kept, at most 3 questions (the bank's first). A recorded sheet in the old shape (no warm-up
    words) keeps its questions: it is only marked as practice, and check_writing_sheets reports it."""
    ws["sheet_kind"] = "fluency"
    ws["practice"] = True
    if not _words_of(ws):
        return [f"{lvl}: an old-shape reading-aloud sheet (no warm-up words): marked as practice, questions left as they are"]
    ws["warmup_words"] = _words_of(ws)
    if isinstance(ws.get("expression_sentences"), list):
        ws["expression_sentences"] = [_strip(x) for x in ws["expression_sentences"] if isinstance(x, str) and _strip(x)][:4]
    probs = [p for p in ws.get("problems") or [] if isinstance(p, dict)]
    keep = ([p for p in probs if p.get("from_bank")] + [p for p in probs if not p.get("from_bank")])[:FLUENCY_QUESTIONS_MAX]
    dropped = len(probs) - len(keep)
    for n, p in enumerate(keep, 1):
        p["number"] = n
    ws["problems"] = keep
    ws["required_count"] = len(keep)
    return [f"{lvl}: reading-aloud practice sheet, {len(ws['warmup_words'])} warm-up words, {len(keep)} question(s)" + (f" ({dropped} dropped)" if dropped else "")]


_EVERY_CHILD = re.compile(r"हर\s+बच्चे|सभी\s+बच्चों\s+से|हर\s+एक\s+बच्चे")


def _lesson_text(plan: dict, level: str, keys=("i_do_hi", "we_do_hi")) -> str:
    out = []
    for b in (plan.get("rotation_schedule") or {}).get("blocks") or []:
        if isinstance(b, dict) and b.get("teach_group") == level:
            tp = b.get("talking_points") or {}
            out += [str(tp.get(k) or "") for k in keys]
    return " ".join(out)


_SENT_SPLIT = re.compile(r"[।?!\n]")


def _sentences(text) -> set:
    """Whole sentences of 3+ words, punctuation and spacing ignored: a short sentence copied from the lesson is still copying."""
    out = set()
    for s in _SENT_SPLIT.split(str(text or "")):
        w = re.sub(r"[\"'‘’“”«»(),:;.\-–—]", " ", s).split()
        if len(w) >= 3:
            out.add(" ".join(w))
    return out


def _norm(text) -> str:
    """Words only, one space apart: punctuation, quotes and line breaks ignored (a dictated sentence inside 'बोर्ड पर लिखें: …' is still found)."""
    return " " + " ".join(re.sub(r"[।?!\"'‘’“”«»(),:;.\-–—]", " ", str(text or "")).split()) + " "


_QUOTED_TOPIC = re.compile(r"['‘“«]([^'’”»]{2,40})['’”»]\s*(?:विषय\s*)?पर\b")
_OPTIONS = re.compile(r"\(([^()]*?/[^()]*?)\)")


def _named_topics(text) -> list:
    """Topics a text names the way a task does: 'मेरा परिवार' पर ..."""
    return [_strip(m.group(1)) for m in _QUOTED_TOPIC.finditer(str(text or ""))]


def _answer_outside_options(problem: dict):
    """A fill-in item that offers its options in brackets ('(और / फिर)'): the answer must be one of them. Returns (answer, options) when it is not."""
    m = _OPTIONS.search(str(problem.get("problem_hi") or ""))
    ans = _strip(problem.get("answer"))
    if not m or not ans or " " in ans:            # a whole-sentence answer is not a choice between options
        return None
    opts = [_strip(o) for o in m.group(1).split("/") if _strip(o)]
    if len(opts) >= 2 and all(len(o.split()) <= 2 for o in opts) and ans.strip("।") not in opts:
        return ans, opts
    return None


def check_writing_sheets(plan: dict, group_skill_ids: dict, domain_id: str) -> list:
    """What is still wrong with a writing sheet after apply_writing_sheets: human-readable warnings (empty = good)."""
    issues = []
    anchor = plan.get("anchor") or {}
    for lvl, kind in group_kinds(group_skill_ids, domain_id).items():
        if kind == "reading":
            continue
        ws = (plan.get("worksheets") or {}).get(lvl) or {}
        where = f"worksheets.{lvl} ({kind})"
        if kind == "fluency":
            words = _words_of(ws)
            if not words:
                issues.append(f"{where}: no warm-up words")
            elif not (WARMUP_MIN <= len(words) <= WARMUP_MAX):
                issues.append(f"{where}: {len(words)} warm-up word(s), not {WARMUP_MIN}-{WARMUP_MAX}")
            if not (ws.get("passage_block") or {}).get("text"):
                issues.append(f"{where}: no passage to read aloud three times")
            if group_skill_ids.get(lvl) in EXPRESSION and not (3 <= len(ws.get("expression_sentences") or []) <= 4):
                issues.append(f"{where}: no 3-4 sentences to read with pauses or expression")
            if len(ws.get("problems") or []) > FLUENCY_QUESTIONS_MAX:
                issues.append(f"{where}: {len(ws.get('problems') or [])} questions, more than {FLUENCY_QUESTIONS_MAX}")
            you_do = _lesson_text(plan, lvl, ("you_do_hi",))
            m = _EVERY_CHILD.search(you_do)
            if m:
                issues.append(f"{where}: the You Do says the teacher hears «{m.group(0)}»; it should be the children shown in the app (3-4 a day)")
            continue
        if ws.get("passage_block"):
            issues.append(f"{where}: has a reading passage")
        probs = ws.get("problems") or []
        lesson = _lesson_text(plan, lvl)
        lesson_all = lesson + " " + " ".join(str(anchor.get(k) or "") for k in ("narration_hi", "opening_question_hi", f"{lvl}_participation_hi"))
        if kind == "composition":
            cl = ws.get("checklist") or []
            if not (CHECKLIST_MIN <= len(cl) <= CHECKLIST_MAX):
                issues.append(f"{where}: the checklist has {len(cl)} item(s), not {CHECKLIST_MIN}-{CHECKLIST_MAX}")
            if not probs or not probs[0].get("writing_task"):
                issues.append(f"{where}: problem 1 is not the writing task")
            topic = _strip((ws.get("writing_task") or {}).get("topic_hi"))
            if topic and topic in _strip(lesson):
                issues.append(f"{where}: the writing topic «{topic}» is the teacher's own model in the I Do / We Do")
            # the You Do may name the sheet's topic or point to it ("दिए विषय पर"); it must never name ANOTHER topic ('हमारा स्कूल' पर ...)
            you_do = _lesson_text(plan, lvl, ("you_do_hi",))
            for other in _named_topics(you_do):
                if topic and other != topic:
                    issues.append(f"{where}: the You Do names the topic «{other}», but the sheet's topic is «{topic}»")
            for p in probs[1:]:
                if not p.get("writing_task") and not _strip(p.get("answer")):
                    issues.append(f"{where} problem {p.get('number')}: no answer to check")
                bad = _answer_outside_options(p)
                if bad:
                    issues.append(f"{where} problem {p.get('number')}: the answer «{bad[0]}» is not one of the options it offers ({' / '.join(bad[1])})")
        if kind == "dictation":
            sentences = ws.get("dictation_sentences") or []
            if not (3 <= len(sentences) <= 8):
                issues.append(f"{where}: {len(sentences)} dictation sentence(s), not 4-6")
            child = " ".join([str(ws.get("instructions_hi") or ""), str(ws.get("example_block") or "")] + [str(p.get("problem_hi") or "") for p in probs])
            board = lesson + " " + _lesson_text(plan, lvl, ("you_do_hi",))
            for s in sentences:
                if _norm(s) and _norm(s) in _norm(child):
                    issues.append(f"{where}: the dictated sentence «{s}» is printed on the child's sheet")
                if _norm(s) and _norm(s) in _norm(board):
                    issues.append(f"{where}: the dictated sentence «{s}» is in the lesson (the board)")
        shown = set()
        for p in probs:
            shown |= _sentences(p.get("problem_hi"))
        for s in sorted(shown & _sentences(lesson_all)):
            issues.append(f"{where}: «{s}» is copied from the lesson or the anchor")
    return issues


def vision_spec(worksheet: dict):
    """What the photo analysis needs to mark a writing sheet: None for any other sheet."""
    kind = (worksheet or {}).get("sheet_kind")
    if kind == "composition":
        tasks = [p.get("number") for p in worksheet.get("problems") or [] if p.get("writing_task") or _strip(p.get("answer")).upper() == TASK_ANSWER]
        return {"kind": "composition", "checklist": [c.get("item_hi") for c in worksheet.get("checklist") or [] if c.get("item_hi")], "task_numbers": tasks}
    if kind == "dictation":
        return {"kind": "dictation", "sentences": list(worksheet.get("dictation_sentences") or [])}
    if kind == "formation":
        return {"kind": "formation"}
    if kind == "fluency":
        return {"kind": "fluency", "practice": True}
    return None
