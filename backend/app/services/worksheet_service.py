"""
Ankur Saathi — Worksheet Service
Renders Dainik Yojana worksheet data into printable A4 HTML.
Handles numeracy (place-value grids, number lines) and literacy
(passage boxes, letter grids, writing lines).
"""

import json
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "prompts"))        # the same place plan_service finds it
try:
    import hindi_style
except ImportError:                                                           # never stop a sheet from printing for want of the style module
    hindi_style = None

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

def _polite_on() -> bool:
    return bool(hindi_style and hindi_style.POLITE_IN_WORKSHEETS)


def _polite(text):
    """A line printed for the children, in the respectful form (जोड़ें, लिखें, पढ़ें) when the app is set to it. Text inside quotation marks is material the
    child reads and is left alone. Idempotent, so a plan stored in the new style, or an older plan in the old one, both print the same."""
    if not text or not isinstance(text, str) or not _polite_on():
        return text
    return hindi_style.soften_text(text, polite=True, frame=True, protect_quotes=True)[0]


LEVEL_LABELS = {
    "beginner": {"hi": "शुरुआती", "en": "Beginner"},
    "progressor": {"hi": "प्रगतिशील", "en": "Progressor"},
    "proficient": {"hi": "दक्ष", "en": "Proficient"},
}


def _enrich_numeracy_problem(problem: dict, level: str) -> dict:
    """Add visual scaffolding to a numeracy problem based on level and type."""
    enriched = {**problem}
    
    problem_text = (problem.get("problem_hi") or "").lower()
    
    # PV grids: only if explicitly set in the problem data (by Claude or sample)
    # Don't auto-add — keeps worksheets compact for single-page printing
    
    # Carry cell above the tens column on the Progressor's grid problems (scaffold: the sheet's
    # own instructions tell children to write the carry there)
    if level == "progressor" and problem.get("show_pv_grid") and "show_carry_box" not in problem:
        enriched["show_carry_box"] = True

    # Number line for counting and comparison
    if any(kw in problem_text for kw in ["गिनो", "गिनें", "count", "क्रम", "तुलना", "बीच"]):
        enriched["show_number_line"] = True
        enriched["number_line_content"] = "◁ __|__|__|__|__|__|__|__|__|__|__|__|__|__|__ ▷"
    
    # Answer type
    if problem.get("answer_type"):
        pass  # Already set
    elif any(kw in problem_text for kw in ["शाब्दिक", "word problem", "कहानी"]):
        enriched["answer_type"] = "wide"
    else:
        enriched["answer_type"] = "box"
    
    return enriched


def _enrich_literacy_problem(problem: dict, level: str) -> dict:
    """Add visual scaffolding to a literacy problem based on level and type."""
    enriched = {**problem}
    
    problem_text = (problem.get("problem_hi") or "").lower()
    
    # Letter/matra writing grid
    if any(kw in problem_text for kw in ["लिखो", "लिखें", "लिखिए", "write", "अक्षर", "मात्रा"]):
        if level == "beginner":
            enriched["show_letter_grid"] = True
            # Create alternating prefilled + empty cells for tracing
            enriched["letter_grid_cells"] = []
            for i in range(8):
                if i % 2 == 0:
                    enriched["letter_grid_cells"].append({"prefilled": True, "text": problem.get("target_letter", "क")})
                else:
                    enriched["letter_grid_cells"].append({"prefilled": False})
    
    # Reading passage
    if problem.get("passage_text"):
        enriched["show_passage"] = True
    
    # Answer type based on problem type
    if problem.get("answer_type"):
        pass
    elif any(kw in problem_text for kw in ["वाक्य", "sentence", "लिखो", "लिखें", "लिखिए", "write", "पत्र", "letter"]):
        enriched["answer_type"] = "lines"
        enriched["answer_lines"] = 4 if level == "proficient" else 3
    elif any(kw in problem_text for kw in ["पढ़ो", "पढ़ें", "पढ़िए", "read", "सुनो", "सुनें", "बोलो", "बोलें"]):
        enriched["answer_type"] = "box"  # Short answer
    else:
        enriched["answer_type"] = "box"
    
    return enriched


def _build_render_blocks(problems: list[dict]) -> list[dict]:
    """
    Groups a flat, numbered problem list into ordered render blocks,
    preserving question-number order. Consecutive 'row_type' problems
    (grid or plain) are batched into rows of 3; everything else renders
    full-width individually.
    """
    blocks = []
    pending_row = []
    pending_row_type = None  # 'grid' or 'plain'

    def flush():
        nonlocal pending_row, pending_row_type
        if pending_row:
            blocks.append({"kind": f"{pending_row_type}_row", "cells": pending_row})
            pending_row = []
            pending_row_type = None

    for p in problems:
        row_type = p.get("row_type")  # 'grid' or 'plain', set on the problem dict
        if row_type:
            if pending_row_type and pending_row_type != row_type:
                flush()
            pending_row_type = row_type
            pending_row.append(p)
            if len(pending_row) == 3:
                flush()
        else:
            flush()
            blocks.append({"kind": "full", "problem": p})

    flush()
    return blocks


def render_worksheet(
    plan_data: dict,
    level: str,
    competency_id: str,
    competency_name_hi: str,
    competency_name_en: str,
    domain_id: str,
    plan_date: str,
    class_numbers: bool = False,       # the class uses numbers that carry the grade (305 = Grade 3, roll 5)
) -> str:
    """
    Render a printable worksheet HTML from plan data.
    
    Args:
        plan_data: The full Dainik Yojana JSON (from Claude)
        level: 'beginner', 'progressor', or 'proficient'
        competency_id: e.g. 'N2.3.2'
        competency_name_hi: Hindi name
        competency_name_en: English name
        domain_id: 'numeracy' or 'r1_literacy'
        plan_date: Date string
    
    Returns:
        Rendered HTML string ready to serve
    """
    
    # Extract worksheet data from plan
    worksheets = plan_data.get("worksheets", {})
    worksheet = worksheets.get(level, {})
    
    problems_raw = worksheet.get("problems", [])
    instructions_hi = _polite(worksheet.get("instructions_hi", "सभी प्रश्न हल करें। अपना काम दिखाएँ।"))
    instructions_en = worksheet.get("instructions_en", "Solve all problems. Show your work.")
    
    # Enrich problems with visual scaffolding
    enricher = _enrich_numeracy_problem if domain_id == "numeracy" else _enrich_literacy_problem

    # How many problems every child must do. The rest are extras for fast finishers.
    required_count = worksheet.get("required_count")
    try:
        required_count = int(required_count) if required_count is not None else None
    except (TypeError, ValueError):
        required_count = None
    if required_count is not None and not (1 <= required_count < len(problems_raw)):
        required_count = None      # nothing to mark as extra

    problems = []
    for i, p in enumerate(problems_raw):
        p = dict(p)
        for field in ("problem_hi", "word_problem_text"):
            if p.get(field):
                p[field] = _polite(p[field])
        enriched = enricher(p, level)
        # tolerate alternative field names so a slightly different plan still renders
        if "number" not in enriched:
            enriched["number"] = enriched.get("no", i + 1)
        if not enriched.get("problem_hi"):
            enriched["problem_hi"] = enriched.get("problem") or enriched.get("question") or ""
        enriched["extra"] = required_count is not None and (i + 1) > required_count
        # the model often puts the story in both fields: show it once
        if (enriched.get("word_problem_text") or "").strip() == (enriched.get("problem_hi") or "").strip():
            enriched["word_problem_text"] = ""
        problems.append(enriched)
    
    # Extract example/passage blocks (separate from numbered problems)
    example_block = worksheet.get("example_block")
    if domain_id == "numeracy" and level == "progressor" and example_block and example_block.get("show_pv_grid"):
        try:
            ones = int(example_block.get("row1_o") or 0) + int(example_block.get("row2_o") or 0)
        except (TypeError, ValueError):
            ones = 0
        example_block = {**example_block, "show_carry_box": True, "carry_t": "1" if ones >= 10 else ""}
    passage_block = worksheet.get("passage_block")
    
    render_blocks = _build_render_blocks(problems)
    
    # Render template
    template = jinja_env.get_template("worksheet.html")
    html = template.render(
        class_numbers=class_numbers,
        polite=_polite_on(),
        title=f"{competency_id} — {competency_name_hi}",
        competency_id=competency_id,
        competency_name_hi=competency_name_hi,
        competency_name_en=competency_name_en,
        level=level,
        level_hi=LEVEL_LABELS[level]["hi"],
        level_en=LEVEL_LABELS[level]["en"],
        instructions_hi=instructions_hi,
        instructions_en=instructions_en,
        example_block=example_block,
        passage_block=passage_block,
        render_blocks=render_blocks,
        required_count=required_count,
        date=plan_date,
    )
    
    return html


def render_sample_worksheet(
    level: str,
    domain_id: str,
    competency_id: str,
    competency_name_hi: str,
    competency_name_en: str,
) -> str:
    """
    Render a sample worksheet without a generated plan.
    Uses hardcoded sample problems for demo/testing.
    """
    example_block = None
    passage_block = None
    required_count = None
    
    if domain_id == "numeracy":
        if level == "beginner":
            example_block = {
                "problem_hi": "21 + 15 = ___", "answer": "36",
                "show_pv_grid": True, "pv_columns": 2,
                "row1_t": "2", "row1_o": "1",   # 21
                "row2_t": "1", "row2_o": "5",   # 15
                "answer_t": "3", "answer_o": "6",  # 36
            }
            problems = [
                {"number": 1, "problem_hi": "23 + 14", "answer": "37", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 2, "problem_hi": "31 + 25", "answer": "56", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 3, "problem_hi": "42 + 16", "answer": "58", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 4, "problem_hi": "15 + 34", "answer": "49", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 5, "problem_hi": "50 + 23", "answer": "73", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 6, "problem_hi": "24 + 35", "answer": "59", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 7, "problem_hi": "13 + 26", "answer": "39", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 8, "problem_hi": "35 + 21", "answer": "56", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
            ]
            required_count = 5   # first 5 required; 6-8 are extras (board-copy friendly)
            instructions_hi = "दहाई-इकाई चार्ट में अंक भरो और जोड़ करो। ऊपर दिया उदाहरण देखो।"
            instructions_en = "Fill the place-value chart and add. See the worked example above."
        elif level == "progressor":
            required_count = 6   # first 6 required; the word problem is an extra
            example_block = {
                "problem_hi": "27 + 15 = ___ (हासिल के साथ)", "answer": "42",
                "show_pv_grid": True, "pv_columns": 2,
                "row1_t": "2", "row1_o": "7",   # 27
                "row2_t": "1", "row2_o": "5",   # 15
                "answer_t": "4", "answer_o": "2",  # 42 (7+5=12, carry 1)
            }
            problems = [
                # Q1-Q3: grid row (scaffolded)
                {"number": 1, "problem_hi": "34 + 28", "answer": "62", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 2, "problem_hi": "47 + 35", "answer": "82", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                {"number": 3, "problem_hi": "56 + 27", "answer": "83", "row_type": "grid", "show_pv_grid": True, "pv_columns": 2, "pv_row2": True},
                # Q4-Q6: plain row, no grids (scaffolding fades — independent fluency)
                {"number": 4, "problem_hi": "19 + 43 = ___", "answer": "62", "row_type": "plain"},
                {"number": 5, "problem_hi": "65 + 18 = ___", "answer": "83", "row_type": "plain"},
                {"number": 6, "problem_hi": "38 + 44 = ___", "answer": "82", "row_type": "plain"},
                # Q7: word problem, full-width
                {"number": 7, "problem_hi": "राम के पास 36 आम हैं। श्याम ने उसे 27 आम और दिए। कुल कितने आम?",
                 "answer": "63", "word_problem_text": "राम के पास 36 आम हैं। श्याम ने उसे 27 आम और दिए। कुल कितने आम?",
                 "answer_type": "wide"},
            ]
            instructions_hi = "हासिल के साथ जोड़ो। इकाई का योग 9 से ज़्यादा हो तो हासिल दहाई में जाता है।"
            instructions_en = "Add with carry-over. When ones sum exceeds 9, carry to the tens column."
        else:  # proficient
            example_block = None
            problems = [
                {"number": 1, "problem_hi": "57 + 36 = ___", "answer": "93", "row_type": "plain"},
                {"number": 2, "problem_hi": "68 + 45 = ___", "answer": "113", "row_type": "plain"},
                {"number": 3, "problem_hi": "89 + 34 = ___", "answer": "123", "row_type": "plain"},
                {"number": 4, "problem_hi": "44 + ___ = 81", "answer": "37", "row_type": "plain"},
                {"number": 5, "problem_hi": "76 + 58 = ___", "answer": "134", "row_type": "plain"},
                {"number": 6, "problem_hi": "___ + 29 = 74", "answer": "45", "row_type": "plain"},
                {"number": 7, "problem_hi": "दुकान में सुबह 48 और शाम को 37 ग्राहक आए। कुल कितने?",
                 "answer": "85", "word_problem_text": "दुकान में सुबह 48 और शाम को 37 ग्राहक आए। कुल कितने?",
                 "answer_type": "wide"},
                {"number": 8, "problem_hi": "रीना के पास 55 रुपये हैं। माँ ने 38 और दिए। क्या वह 80 रुपये की किताब खरीद सकती है? क्यों?",
                 "answer": "93, हाँ", "word_problem_text": "रीना के पास 55 रुपये हैं। माँ ने 38 और दिए। क्या वह 80 रुपये की किताब खरीद सकती है? क्यों?",
                 "answer_type": "wide"},
            ]
            instructions_hi = "सभी सवाल हल करो। शाब्दिक प्रश्नों में पूरा हल लिखो।"
            instructions_en = "Solve all problems. Show complete working for word problems."
    else:
        # Literacy sample — compact pattern: worked example / passage header
        # separated from numbered questions; short answers grouped in rows of 3.
        if level == "beginner":
            example_block = {
                "problem_hi": "मात्रा जोड़ने का उदाहरण:",
                "example_text": "क + ो = को   (ka + o-mātrā = ko)",
            }
            problems = [
                # Q1: full-width letter tracing (main exercise)
                {"number": 1, "problem_hi": "इन अक्षरों को पढ़ो और लिखो: क, ख, ग, घ",
                 "show_letter_grid": True, "target_letter": "क",
                 "letter_grid_cells": [
                     {"prefilled": True, "text": "क"}, {"prefilled": False},
                     {"prefilled": True, "text": "ख"}, {"prefilled": False},
                     {"prefilled": True, "text": "ग"}, {"prefilled": False},
                     {"prefilled": True, "text": "घ"}, {"prefilled": False},
                 ]},
                # Q2-Q4: short answers, grouped in one row of 3
                {"number": 2, "problem_hi": "पढ़ो: कमल", "answer": "✓", "row_type": "plain"},
                {"number": 3, "problem_hi": "सही मात्रा: क_ला (े/ै)", "answer": "केला", "row_type": "plain"},
                {"number": 4, "problem_hi": "चित्र: 🏠 = ?", "answer": "घर", "row_type": "plain"},
                # Q5: full-width writing lines
                {"number": 5, "problem_hi": "'क' से शुरू होने वाले 3 शब्द लिखो",
                 "answer_type": "lines", "answer_lines": 3},
            ]
            instructions_hi = "पहले पढ़ो, फिर लिखो। अक्षर साफ़ और बड़े लिखो।"
            instructions_en = "Read first, then write. Write letters clearly and large."

        elif level == "progressor":
            passage_block = {
                "title": "किसान और बारिश",
                "text": "रामू एक किसान है। वह रोज़ सुबह खेत में जाता है। इस साल बारिश बहुत कम हुई। रामू की फ़सल सूखने लगी। एक दिन ज़ोर की बारिश हुई। रामू बहुत खुश हुआ।",
            }
            problems = [
                # Q1-Q3: short answers in one row
                {"number": 1, "problem_hi": "रामू क्या काम करता है?", "answer": "किसानी", "row_type": "plain"},
                {"number": 2, "problem_hi": "मात्रा लिखो: द_न (ि/ी)", "answer": "दिन", "row_type": "plain"},
                {"number": 3, "problem_hi": "मात्रा लिखो: स_ल (ा/ू)", "answer": "साल", "row_type": "plain"},
                # Q4-Q5: full-width longer answers
                {"number": 4, "problem_hi": "रामू खुश क्यों हुआ? पूरे वाक्य में लिखो।",
                 "answer_type": "lines", "answer_lines": 2},
                {"number": 5, "problem_hi": "'बारिश' विषय पर 3 वाक्य लिखो।",
                 "answer_type": "lines", "answer_lines": 3},
            ]
            instructions_hi = "पहले अनुच्छेद ध्यान से पढ़ो, फिर प्रश्नों के उत्तर लिखो।"
            instructions_en = "Read the passage carefully first, then answer the questions."

        else:  # proficient
            example_block = None
            passage_block = {
                "title": "मधुमक्खियों का संसार",
                "text": "मधुमक्खियाँ बहुत मेहनती कीड़े हैं। वे छत्ते में रहती हैं। श्रमिक मधुमक्खियाँ फूलों से रस इकट्ठा करती हैं और शहद बनाती हैं। सैनिक मधुमक्खियाँ छत्ते की रक्षा करती हैं। मधुमक्खियाँ परागण भी करती हैं।",
            }
            problems = [
                {"number": 1, "problem_hi": "श्रमिक मधुमक्खियाँ क्या करती हैं?",
                 "answer_type": "lines", "answer_lines": 2},
                {"number": 2, "problem_hi": "मधुमक्खियाँ न हों तो क्या होगा? अपने शब्दों में लिखो।",
                 "answer_type": "lines", "answer_lines": 2},
                {"number": 3, "problem_hi": "'मेहनती' — क्या यह तथ्य है या राय? क्यों?",
                 "answer_type": "lines", "answer_lines": 2},
                {"number": 4, "problem_hi": "मधुमक्खियों के बारे में 5 वाक्यों का अनुच्छेद लिखो।",
                 "answer_type": "lines", "answer_lines": 5},
            ]
            instructions_hi = "अनुच्छेद पढ़ो और प्रश्नों के उत्तर पूरे वाक्यों में लिखो।"
            instructions_en = "Read the passage and answer in complete sentences."
    
    plan_data = {
        "worksheets": {
            level: {
                "problems": problems,
                "instructions_hi": instructions_hi,
                "instructions_en": instructions_en,
                "example_block": example_block,
                "passage_block": passage_block,
                "required_count": required_count,
            }
        }
    }
    
    return render_worksheet(
        plan_data=plan_data,
        level=level,
        competency_id=competency_id,
        competency_name_hi=competency_name_hi,
        competency_name_en=competency_name_en,
        domain_id=domain_id,
        plan_date=str(date.today()),
    )
