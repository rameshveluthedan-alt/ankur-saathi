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
  observed     every skill checked by WATCHING (assessment_modality 'observed', maths and Hindi; 14 Nov 2026): an "observe" task (a hands-on or spoken
               task, its materials: a kit TLM, else everyday objects; what A / PA / NA look like) and a back-up worksheet that can be drawn on the board,
               with structured items (symbol_grid, compare_boxes, compare_bars) whose answers and board drawings the code computes. Practice.
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

# OBSERVED skills (assessment_modality 'observed', both subjects; 14 Nov 2026): the teacher WATCHES the children do the skill (sort, compare, measure,
# read words aloud, tell the main idea) and marks A / PA / NA. Before, the plan gave these groups an ordinary written sheet ("चित्र: 4 लाल गेंद, 3 पीली
# गेंद। रंग से छाँटें। लाल कितनी?": no picture, the answer in the question), so there was nothing to watch. Now the sheet carries an "observe" task: a
# hands-on or spoken task with materials (a kit TLM, else everyday objects; most schools cannot print), what A / PA / NA look like for it, and a
# back-up worksheet that mirrors the action and can be drawn on the board (structured items whose answers the CODE computes). Practice: never a photo.
# The set is the database's (plan_service.register_observed at each plan); this default is the 14 Nov list, for the tests and a cold start.
OBSERVED = {
    "L0.1.1", "L0.1.2", "L0.1.3", "L0.2.1", "L0.2.2", "L0.2.3", "L0.3.1", "L0.3.2", "L1.2.1", "L1.2.2", "L1.3.1", "L1.3.2", "L1.3.3", "L1.3.4",
    "L1.4.1", "L1.4.2", "L1.6.1", "L1.6.2", "L2.3.1", "L2.3.2", "L2.3.3", "L2.4.1", "L2.4.2", "L2.6.2", "L2.6.3", "L3.3.1", "L3.4.1", "L3.6.3",
    "N0.1.1", "N0.1.2", "N0.1.3", "N0.2.1", "N0.2.2", "N0.2.3", "N0.5.1", "N1.2.1", "N1.2.2", "N1.4.1", "N1.4.2", "N1.5.1", "N1.5.2", "N2.2.4",
    "N2.4.1", "N2.4.2", "N2.4.3", "N3.3.3", "N3.4.2", "N3.4.3",
}
SYMBOLS = "○△□◇★●■▲"
SIZES = {"big": "बड़ा", "small": "छोटा"}
COLOURS = {"red": "लाल", "blue": "नीला", "green": "हरा", "yellow": "पीला", "black": "काला"}
GRID_MIN, GRID_MAX = 4, 20
LOOK_FOR = ("achieved_hi", "partial_hi", "not_yet_hi")
WATCH_SENTENCE = "मैं ऐप में दिखाए गए बच्चों को काम करते हुए देखता/देखती हूँ।"


def register_observed(ids) -> None:
    """The observed skills as the database has them (plan_service calls this before each plan). An empty answer keeps the known list."""
    ids = {str(i) for i in (ids or []) if i}
    if ids:
        OBSERVED.clear()
        OBSERVED.update(ids)


def sheet_kind(competency_id, domain_id="r1_literacy"):
    """'reading' | 'fluency' | 'formation' | 'usage' | 'dictation' | 'composition' | 'observed' for a literacy skill; 'observed' or None for numeracy."""
    if not competency_id:
        return None
    cid = str(competency_id)
    if domain_id != "r1_literacy":
        return "observed" if cid in OBSERVED else None
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
    if cid in OBSERVED:
        return "observed"
    return "reading"


def group_kinds(group_skill_ids, domain_id) -> dict:
    """{level: kind} for the groups whose skill is known."""
    return {lvl: sheet_kind(cid, domain_id) for lvl, cid in (group_skill_ids or {}).items() if cid and sheet_kind(cid, domain_id)}


NOT_WRITING = ("reading", "fluency", "observed")


_STRAND6 = re.compile(r"^L\d+\.6\.\d+$")


def observed_keeps_passage(competency_id) -> bool:
    """An observed COMPREHENSION skill (strand 6: tell the main idea, answer aloud) works on a passage; an observed decoding or word-reading skill
    (L2.3.1 conjuncts, L1.4.2 words) does not: a passage brought the bank's comprehension questions onto its sheet (L2.3.1, 14 Nov)."""
    return bool(_STRAND6.match(str(competency_id or "")))


def writing_levels(group_skill_ids, domain_id) -> set:
    """The groups whose sheet has NO passage: the writing kinds, and an observed literacy skill that is not about comprehension. A fluency group keeps
    its bank passage (it reads it aloud), and so does an observed comprehension skill."""
    out = set()
    for lvl, k in group_kinds(group_skill_ids, domain_id).items():
        if k not in NOT_WRITING or (k == "observed" and domain_id == "r1_literacy" and not observed_keeps_passage(group_skill_ids.get(lvl))):
            out.add(lvl)
    return out


def prompt_section(group_skill_ids, domain_id) -> str:
    """The prompt's rules for the groups on a writing, reading-aloud or observed skill (empty when none is). They OVERRIDE the general worksheet rules for those groups."""
    kinds = group_kinds(group_skill_ids, domain_id)
    writing = {lvl: k for lvl, k in kinds.items() if k not in NOT_WRITING}
    fluency = [lvl for lvl in LEVELS if kinds.get(lvl) == "fluency"]
    observed = [lvl for lvl in LEVELS if kinds.get(lvl) == "observed"]
    if not writing:
        return _fluency_section(group_skill_ids, fluency) + _observed_section(group_skill_ids, observed, domain_id)
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
    return "\n".join(lines) + _fluency_section(group_skill_ids, fluency) + _observed_section(group_skill_ids, observed, domain_id)


def _observed_section(group_skill_ids, observed_levels, domain_id) -> str:
    """The prompt's rules for groups whose skill is checked by WATCHING (empty when none is): a task the teacher can watch, its materials, what A / PA / NA
    look like for it, and a back-up worksheet that can be drawn on the board."""
    if not observed_levels:
        return ""
    lines = ["\n### OBSERVED-SKILL TASKS (these groups' skill is checked by WATCHING the children do it, then marking A / PA / NA: the worksheet is only PRACTICE)"]
    for lvl in observed_levels:
        lines.append(f"- {lvl} ({group_skill_ids[lvl]}): sheet_kind \"observed\"")
    lines += [
        "Most schools cannot print, but many have kits and everyday objects. For each of these groups the worksheet object carries:",
        "- \"observe\": {\"task_hi\", \"task_en\": ONE hands-on or spoken task the teacher can WATCH, that is the skill itself (sort the objects by one rule and say "
        "the rule; put two sticks side by side and say which is longer; read these words aloud to a partner; tell the main idea in one sentence),",
        "  \"kit_materials_hi\": the TLM(s) from the TLM list above that fit this task, by their Hindi name (an empty list when none fits; never invent a kit item),",
        "  \"local_materials_hi\": 2-4 everyday objects the class can collect instead (पत्तियाँ, कंकड़, बटन, बोतल के ढक्कन, तीलियाँ, बीज, ...; for a reading task: "
        "word cards the teacher writes on the board or on paper slips),",
        "  \"look_for\": what the teacher sees for THIS task: {\"achieved_hi\", \"partial_hi\", \"not_yet_hi\", \"achieved_en\", \"partial_en\", \"not_yet_en\"}: A = does it "
        "without help, PA = with help or partly right, NA = not yet; each one short, concrete and visible (for example 'एक ही नियम से सारी चीज़ें छाँटता है और नियम बताता है')}.",
        "- The You Do sets up this task with the materials, in this order: the kit TLM if there is one; else the everyday objects. NAME them in the You Do "
        "itself, as in 'हर जोड़ी को कंकड़, बटन और ढक्कन मिलाकर दें' (never only 'चीज़ें'), so the teacher knows what to hand out; the worksheet only "
        "as a back-up when there are no objects. It ends with exactly this sentence: '" + WATCH_SENTENCE + "' Never 'हर बच्चे' or 'सभी बच्चों से' (there is no "
        "time to watch every child in one lesson), and never a child's name or roll number.",
        "- The back-up worksheet (\"problems\") mirrors the SAME action and can be drawn on the board or copied into a notebook: no pictures are printed. "
        "No item may state its own answer (never '4 लाल गेंद, 3 पीली गेंद … लाल कितनी?').",
    ]
    if domain_id != "r1_literacy":
        lines += [
            "  Use these structured items where they fit (the system computes their answers and the board drawing; leave \"answer\" empty):",
            "  {\"item_type\": \"symbol_grid\", \"grid\": [{\"s\": one of " + " ".join(SYMBOLS) + ", \"size\": \"big\" or \"small\", \"colour\": "
            "\"red\"/\"blue\"/\"green\"/\"yellow\"/\"black\" or null}, ... 8-16 cells], \"target\": {\"s\": \"△\"} or {\"size\": \"big\"} or {\"colour\": \"red\"} or "
            "{\"odd_one_out\": true}, \"problem_hi\": 'सभी △ पर गोला लगाएँ।' or 'जो अलग है उसे काटें।'} for sorting; make the distractors share the other attributes "
            "(big and small △ when the rule is shape), and for odd_one_out exactly one cell differs.",
            "  {\"item_type\": \"compare_boxes\", \"a\": {\"s\": \"★\", \"count\": 6}, \"b\": {\"s\": \"★\", \"count\": 4}, \"ask\": \"more\" or \"less\", \"problem_hi\": "
            "'जिस डिब्बे में ज़्यादा हैं, उस पर ✓ लगाएँ।'} for comparing quantities (counts 1-15, never equal);",
            "  {\"item_type\": \"compare_bars\", \"a\": 7, \"b\": 4, \"ask\": \"longer\" or \"shorter\", \"problem_hi\": 'जो पट्टी लंबी है, उस पर ✓ लगाएँ।'} for comparing "
            "lengths (1-15 units, never equal). Other observed maths skills: short items that ask the child to DO the step (draw, match, show), not to read off an answer.",
        ]
    else:
        lines.append("  For a reading or speaking skill: words or short sentences to read to a partner, and a spoken task (tell, retell, answer aloud); each item "
                     "with one checkable answer where there is one.")
    lines.append("- \"practice\": true. The sheet is never marked from a photo; the teacher marks A / PA / NA by watching (or by looking at a back-up sheet in "
                 "class or after class).\n")
    return "\n".join(lines)


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
        "- The You Do sends the group to this worksheet and ends with exactly this sentence: 'मैं ऐप में दिखाए गए बच्चों को एक-एक मिनट पढ़ते हुए सुनता/सुनती हूँ।' "
        "Never 'हर बच्चे से' or 'सभी बच्चों से' (there is no time to hear every child in one day), and never a child's name or roll number.",
        "- The sheet has at most 3 questions: the You Do names them as 'प्रश्न 1 से 3' (never a higher number) and mentions no extras.\n",
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
        if kind == "observed":
            log += _apply_observed(lvl, ws, group_skill_ids.get(lvl), domain_id)
            continue
        if kind == "fluency":
            log += _apply_fluency(lvl, ws)
            if _words_of(ws):          # the sheet was trimmed to its questions: the You Do must not send the group to questions that are gone
                log += _fit_you_do(plan, lvl, len(ws.get("problems") or []))
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


def _str_list(v) -> list:
    return [_strip(x) for x in (v if isinstance(v, list) else []) if isinstance(x, str) and _strip(x)]


def _observe_of(ws: dict):
    """The sheet's observation task, cleaned; None when the sheet has none (a recorded plan from before 14 Nov)."""
    o = ws.get("observe")
    if not isinstance(o, dict) or not _strip(o.get("task_hi")):
        return None
    lf = o.get("look_for") if isinstance(o.get("look_for"), dict) else {}
    return {"task_hi": _strip(o.get("task_hi")), "task_en": _strip(o.get("task_en")),
            "kit_materials_hi": _str_list(o.get("kit_materials_hi")), "local_materials_hi": _str_list(o.get("local_materials_hi")),
            "look_for": {k: _strip(lf.get(k)) for k in ("achieved_hi", "partial_hi", "not_yet_hi", "achieved_en", "partial_en", "not_yet_en")}}


def _cell(c):
    """One symbol_grid cell, cleaned: {"s", "size", "colour"}; None when it is not a cell the board can draw."""
    if not isinstance(c, dict):
        return None
    s = str(c.get("s") or "").strip()
    if len(s) != 1 or s not in SYMBOLS:
        return None
    size = c.get("size") if c.get("size") in SIZES else "big"
    colour = c.get("colour") if c.get("colour") in COLOURS else None
    return {"s": s, "size": size, "colour": colour}


def _cell_text(c: dict, show_size: bool, show_colour: bool) -> str:
    return " ".join(x for x in ((COLOURS[c["colour"]] if show_colour and c["colour"] else ""), (SIZES[c["size"]] if show_size else ""), c["s"]) if x)


def _odd_one_out(cells: list):
    """The 1-based number of the one cell that differs from all the others in shape, size or colour; None when there is not exactly one such cell."""
    for attr in ("s", "size", "colour"):
        values = [c[attr] for c in cells]
        for v in set(values):
            if values.count(v) == 1 and len(set(values)) == 2 and len(values) >= 3:
                return values.index(v) + 1
    return None


def structure_item(p: dict):
    """A structured back-up item (symbol_grid, compare_boxes, compare_bars) with its answer and its board drawing COMPUTED here, never the model's.
    Returns the item, or None when it is malformed (it is then dropped). An ordinary item is returned unchanged."""
    t = p.get("item_type")
    if t not in ("symbol_grid", "compare_boxes", "compare_bars"):
        return p
    q = dict(p)
    q.update({"row_type": None, "answer_type": "box", "show_letter_grid": False})
    if t == "symbol_grid":
        cells = [_cell(c) for c in p.get("grid") or []]
        if not (GRID_MIN <= len(cells) <= GRID_MAX) or any(c is None for c in cells):
            return None
        target = p.get("target") if isinstance(p.get("target"), dict) else {}
        show_size = len({c["size"] for c in cells}) > 1
        show_colour = any(c["colour"] for c in cells)
        if target.get("odd_one_out"):
            k = _odd_one_out(cells)
            q["answer"] = f"खाना {k}" if k else ""
            q["matches"] = [k] if k else []
        else:
            key = next((a for a in ("s", "size", "colour") if target.get(a)), None)
            if key is None or (key == "s" and target["s"] not in SYMBOLS) or (key == "size" and target["size"] not in SIZES) or (key == "colour" and target["colour"] not in COLOURS):
                return None
            idx = [i for i, c in enumerate(cells, 1) if c[key] == target[key]]
            q["matches"] = idx
            q["answer"] = f"{len(idx)} (खाने {', '.join(str(i) for i in idx)})" if idx else ""
        q["grid"] = cells
        q["target"] = target
        q["board_hi"] = "  ".join(_cell_text(c, show_size, show_colour) for c in cells)
        return q
    if t == "compare_boxes":
        a, b = p.get("a") if isinstance(p.get("a"), dict) else {}, p.get("b") if isinstance(p.get("b"), dict) else {}
        try:
            na, nb = int(a.get("count")), int(b.get("count"))
        except (TypeError, ValueError):
            return None
        sa, sb = str(a.get("s") or "★"), str(b.get("s") or "★")
        if not (1 <= na <= 20 and 1 <= nb <= 20) or na == nb or sa not in SYMBOLS or sb not in SYMBOLS or p.get("ask") not in ("more", "less"):
            return None
        more = "क" if na > nb else "ख"
        q.update({"a": {"s": sa, "count": na}, "b": {"s": sb, "count": nb}, "answer": more if p["ask"] == "more" else ("ख" if more == "क" else "क"),
                  "board_hi": f"क: {sa * na}   |   ख: {sb * nb}"})
        return q
    try:
        la, lb = int(p.get("a")), int(p.get("b"))
    except (TypeError, ValueError):
        return None
    if not (1 <= la <= 15 and 1 <= lb <= 15) or la == lb or p.get("ask") not in ("longer", "shorter"):
        return None
    longer = "क" if la > lb else "ख"
    q.update({"a": la, "b": lb, "answer": longer if p["ask"] == "longer" else ("ख" if longer == "क" else "क"),
              "board_hi": f"क: {'▬' * la}   |   ख: {'▬' * lb}"})
    return q


def _apply_observed(lvl: str, ws: dict, competency_id, domain_id) -> list:
    """An observed group's sheet: practice, its observation task cleaned, structured items computed (malformed ones dropped). A decoding or word-reading
    skill loses a passage and the bank's comprehension questions; a comprehension skill keeps them. A recorded sheet in the old shape (no "observe")
    is only marked practice; check_writing_sheets reports it."""
    ws["sheet_kind"] = "observed"
    ws["practice"] = True
    obs = _observe_of(ws)
    if obs is None:
        return [f"{lvl}: an old-shape observed sheet (no observation task): marked as practice, left as it is"]
    ws["observe"] = obs
    log = []
    probs = [p for p in ws.get("problems") or [] if isinstance(p, dict)]
    if domain_id == "r1_literacy" and not observed_keeps_passage(competency_id):
        if ws.get("passage_block"):
            ws["passage_block"] = None
            log.append(f"{lvl}: passage removed (an observed word-reading skill)")
        bank = [p for p in probs if p.get("from_bank")]
        if bank:
            probs = [p for p in probs if not p.get("from_bank")]
            log.append(f"{lvl}: {len(bank)} bank comprehension question(s) removed")
    kept, dropped = [], 0
    for p in probs:
        q = structure_item(p)
        if q is None:
            dropped += 1
        else:
            kept.append(q)
    kept, flipped = _vary_compare_answers(kept)
    if flipped:
        log.append(f"{lvl}: {flipped} comparison item(s) flipped so the answer is not always the same box")
    for n, p in enumerate(kept, 1):
        p["number"] = n
    ws["problems"] = kept
    rc = ws.get("required_count")
    if not (isinstance(rc, int) and not isinstance(rc, bool) and 1 <= rc <= len(kept)):
        ws["required_count"] = len(kept) or None
    n_struct = sum(1 for p in kept if p.get("item_type"))
    log.append(f"{lvl}: observed task, practice sheet with {len(kept)} item(s) ({n_struct} drawn by the code)" + (f"; {dropped} malformed structured item(s) dropped" if dropped else ""))
    return log


def _vary_compare_answers(items: list):
    """First real N1.4.1 run (14 Nov): all four bar items had the answer "ख", so a child could guess the pattern. When three or more comparison
    items share one answer, every second one has its two sides swapped (and is computed again), so the answers alternate."""
    comp = [i for i, p in enumerate(items) if p.get("item_type") in ("compare_boxes", "compare_bars")]
    if len(comp) < 3 or len({items[i].get("answer") for i in comp}) > 1:
        return items, 0
    flipped = 0
    for k, i in enumerate(comp):
        if k % 2 == 1:
            p = dict(items[i])
            p["a"], p["b"] = p.get("b"), p.get("a")
            q = structure_item(p)
            if q is not None:
                items[i] = q
                flipped += 1
    return items, flipped


_MATERIAL_STOP = {"लिखे", "लिखी", "वाले", "वाली", "चीज़ें", "चीज़ों", "अपना", "अपनी", "जैसे", "पंक्तियाँ"}


def _material_words(materials) -> set:
    """The key words of the materials: 'बोतल के ढक्कन' is named by a You Do that says 'ढक्कन' (the exact phrase was too strict, 14 Nov)."""
    out = set()
    for m in materials:
        for w in re.split(r"[\s,()/।]+", str(m or "")):
            w = w.strip()
            if len(w) >= 3 and w not in _MATERIAL_STOP:
                out.add(w)
    return out


def _gives_answer_away(p: dict) -> bool:
    """An ordinary item whose answer's numbers are all in its own question: 'चित्र: 4 लाल गेंद, 3 पीली गेंद … लाल कितनी? -> लाल 4, पीली 3' (N0.1.1)."""
    if p.get("item_type"):
        return False
    nums = re.findall(r"\d+", str(p.get("answer") or ""))
    if not nums:
        return False
    asked = set(re.findall(r"\d+", str(p.get("problem_hi") or "") + " " + str(p.get("word_problem_text") or "")))
    return all(n in asked for n in nums)


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
# "1 से 6 तक के प्रश्न", "प्रश्न 1-6", and "बाकी (प्रश्न) अतिरिक्त हैं": a range of questions and the extras, in a You Do
_Q_RANGE = re.compile(r"(\d+)\s*(से|-|–)\s*(\d+)(?=[^।]{0,20}(?:सवाल|प्रश्न|समस्या))|(?:(?<=सवाल\s)|(?<=प्रश्न\s))(\d+)\s*(से|-|–)\s*(\d+)")
_EXTRAS = re.compile(r"\s*[;,]?\s*बाकी\s+(?:सवाल\s+|प्रश्न\s+)?अतिरिक्त\s+हैं\s*[।]?")


def _q_range_ends(text) -> list:
    return [int(m.group(3) or m.group(6)) for m in _Q_RANGE.finditer(str(text or ""))]


def _fit_you_do(plan: dict, level: str, n: int) -> list:
    """First real fluency run (14 Nov): the model wrote six questions and a You Do saying '1 से 6 तक के प्रश्न पहले करें; बाकी अतिरिक्त हैं'; the code keeps
    three. The You Do's question range is cut to the sheet, and the extras (there are none) are dropped."""
    log = []
    if n < 1:
        return log
    for b in (plan.get("rotation_schedule") or {}).get("blocks") or []:
        if not (isinstance(b, dict) and b.get("teach_group") == level):
            continue
        tp = b.get("talking_points") or {}
        old = str(tp.get("you_do_hi") or "")
        new = _Q_RANGE.sub(lambda m: (m.group(0).replace(m.group(3) or m.group(6), str(n), 1) if int(m.group(3) or m.group(6)) > n else m.group(0)), old)
        new = _EXTRAS.sub("।", new).replace("।।", "।").replace("। ।", "।")
        if new != old:
            tp["you_do_hi"] = new
            log.append(f"{level}: You Do fitted to the sheet's {n} question(s)")
    return log


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
        if kind == "observed":
            issues += _check_observed(plan, lvl, ws, where)
            continue
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
            n_q = len(ws.get("problems") or [])
            if n_q and any(e > n_q for e in _q_range_ends(you_do)):
                issues.append(f"{where}: the You Do sends the group to questions beyond the sheet's {n_q}")
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


def _check_observed(plan: dict, lvl: str, ws: dict, where: str) -> list:
    issues = []
    obs = _observe_of(ws)
    if obs is None:
        issues.append(f"{where}: no observation task (what the children do while the teacher watches)")
    else:
        missing = [k for k in LOOK_FOR if not obs["look_for"].get(k)]
        if missing:
            issues.append(f"{where}: what to look for is missing for {', '.join(k.replace('_hi', '') for k in missing)}")
        you_do = _norm(_lesson_text(plan, lvl, ("you_do_hi",)))
        materials = obs["kit_materials_hi"] + obs["local_materials_hi"]
        if not materials:
            issues.append(f"{where}: no materials for the task (a kit TLM or everyday objects)")
        elif not any((w[:4] if len(w) > 4 else w) in you_do for w in _material_words(materials)):        # a stem: 'तीलियों' names 'तीलियाँ'
            issues.append(f"{where}: the You Do names none of the task's materials ({', '.join(materials)})")
    m = _EVERY_CHILD.search(_lesson_text(plan, lvl, ("you_do_hi",)))
    if m:
        issues.append(f"{where}: the You Do says the teacher watches «{m.group(0)}»; it should be the children shown in the app")
    for p in ws.get("problems") or []:
        if _gives_answer_away(p):
            issues.append(f"{where} problem {p.get('number')}: the question states its own answer ({_strip(p.get('answer'))})")
        if p.get("item_type") == "symbol_grid" and not p.get("matches"):
            issues.append(f"{where} problem {p.get('number')}: the grid has no cell that matches what it asks")
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
    if kind == "observed":
        return {"kind": "observed", "practice": True}
    return None
