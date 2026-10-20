"""
Ankur Saathi — build expert review packs.

Review pack 1: the list of common mistakes (misconceptions) and the prerequisite links between skills.
One item per row, the team's content on the left (read-only in spirit), blank yellow columns for the
expert's answers, plus a sheet where the expert can add links we are missing.

    python scripts/build_review_pack.py --env-file backend/.env -o review_pack_1.xlsx

Requires: pip install openpyxl asyncpg
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse
import asyncio
import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

import anchor_common as ac

FONT = "Arial"
GREEN, AMBER = "2D6A4F", "B7791F"
HEAD_OURS = PatternFill("solid", fgColor=GREEN)
HEAD_YOURS = PatternFill("solid", fgColor=AMBER)
YELLOW = PatternFill("solid", fgColor="FFF8DC")
GREY = PatternFill("solid", fgColor="E7E6E6")
START = PatternFill("solid", fgColor="FFE8CC")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
GRADE_ORDER = {"balvatika": 0, "grade_1": 1, "grade_2": 2, "grade_3": 3}
START_SKILLS = ("N2.3.1", "N2.3.2", "N3.3.1")      # the lesson we demo: rows about these come first

# the team's own notes on specific rows, shown to the expert in a "Note from the team" column
TEAM_NOTES = {
    "N2.3.2-M3": ("Known issue: the description says the child carries the ones digit (2 instead of 1 from a sum of 12), "
                  "but how we spot it says the tens column is exactly 1 too high. These agree only when the ones sum is 12; "
                  "for a ones sum of 14 the ones digit carried would be 4, so the tens are 3 too high. Which definition is right?"),
}
LINK_NOTES = {
    ("N2.3.2", "N2.3.1"): "Question: carrying relies on place value. Today N2.3.2 reaches place value only through N2.3.1. Is that enough, or should N2.3.2 also need N1.2.4 directly?",
}


def f(bold=False, italic=False, size=10, color="000000"):
    return Font(name=FONT, bold=bold, italic=italic, size=size, color=color)


def grade(code):
    return ac.GRADE_LABEL.get(code, code)


def plain(code):
    """'very_common' -> 'Very common'"""
    return (code or "").replace("_", " ").capitalize()


async def load(args):
    db = await ac.connect(args)
    order = "(s.domain_id <> 'numeracy'), CASE c.grade_level WHEN 'balvatika' THEN 0 WHEN 'grade_1' THEN 1 WHEN 'grade_2' THEN 2 ELSE 3 END, c.sort_order"
    mistakes = await db.fetch(f"""
        SELECT m.id, m.competency_id, c.name_en AS skill_en, c.name_hi AS skill_hi, c.grade_level,
               m.name_en, m.name_hi, m.error_pattern, m.diagnostic_indicator, m.example_correct, m.example_incorrect,
               m.intervention_strategy, m.severity, m.frequency,
               COALESCE(array_length(m.intervention_template_ids, 1), 0) AS n_routines
        FROM misconceptions m JOIN competencies c ON c.id = m.competency_id JOIN subdomains s ON s.id = c.subdomain_id
        ORDER BY {order}, m.sort_order, m.id""")
    links = await db.fetch(f"""
        SELECT p.competency_id, c.name_en AS skill_en, c.name_hi AS skill_hi, c.grade_level,
               p.prerequisite_id, q.name_en AS pre_en, q.name_hi AS pre_hi, q.grade_level AS pre_grade, p.prerequisite_type
        FROM competency_prerequisites p
        JOIN competencies c ON c.id = p.competency_id JOIN competencies q ON q.id = p.prerequisite_id
        JOIN subdomains s ON s.id = c.subdomain_id
        ORDER BY {order}, c.id, p.prerequisite_type, p.prerequisite_id""")
    skills = await db.fetch(f"""
        SELECT c.id, c.name_en, c.name_hi, c.grade_level, s.name_en AS topic, s.domain_id
        FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id ORDER BY {order}, c.id""")
    await db.close()
    mistakes = sorted(mistakes, key=lambda m: m["competency_id"] not in START_SKILLS)
    links = sorted(links, key=lambda k: not (k["competency_id"] in START_SKILLS or k["prerequisite_id"] in START_SKILLS))
    return mistakes, links, skills


def write_table(ws, specs, rows, reviewer, centered=()):
    """specs = [(key, label, width)]; rows = list of dicts keyed like the specs. Returns ({key: column number}, last row)."""
    idx = {k: i for i, (k, _, _) in enumerate(specs, start=1)}
    for r, row in enumerate(rows, start=2):
        for k, i in idx.items():
            ws.cell(row=r, column=i, value=row.get(k))
    last = len(rows) + 1
    for k, label, w in specs:
        i = idx[k]
        c = ws.cell(row=1, column=i, value=label)
        yours = k in reviewer
        c.font = f(bold=True, color="3B2A00" if yours else "FFFFFF")
        c.fill = HEAD_YOURS if yours else HEAD_OURS
        c.alignment, c.border = CENTER, BOX
        ws.column_dimensions[L(i)].width = w
    ws.row_dimensions[1].height = 48
    for r in range(2, last + 1):
        for k, i in idx.items():
            cell = ws.cell(row=r, column=i)
            cell.font, cell.border = f(), BOX
            cell.alignment = CENTER if k in centered else WRAP
            if k in reviewer:
                cell.fill = YELLOW
    ws.auto_filter.ref = f"A1:{L(len(specs))}{last}"
    return idx, last


def emphasise(ws, idx, last):
    for r in range(2, last + 1):
        c = ws.cell(row=r, column=idx["start"])
        if c.value:
            c.fill, c.font = START, f(bold=True, color="9C4A00")
        if "note" in idx and ws.cell(row=r, column=idx["note"]).value:
            ws.cell(row=r, column=idx["note"]).font = f(bold=True, color="9C2F00")


def add_list(ws, col, first, last, options, title, msg):
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True,
                        showErrorMessage=True, errorTitle=title, error=msg)
    dv.add(f"{L(col)}{first}:{L(col)}{last}")
    ws.add_data_validation(dv)


def build(mistakes, links, skills, out_path):
    wb = Workbook()
    ws_r = wb.active
    ws_r.title = "Read me"
    ws_m = wb.create_sheet("Mistakes")
    ws_p = wb.create_sheet("Prerequisites")
    ws_x = wb.create_sheet("Missing links")
    ws_s = wb.create_sheet("Skills")

    # ── Mistakes: what she judges first, her yellow cells next, reference columns last ─────
    m_specs = [("start", "Start here?", 9), ("id", "Mistake ID", 12), ("skill", "Skill", 22), ("grade", "Grade", 10),
               ("name_en", "Mistake (English)", 20), ("name_hi", "गलती (Hindi)", 18), ("does", "What the child does", 30),
               ("right", "Correct example", 22), ("wrong", "Wrong example", 22), ("fix", "Suggested fix for the teacher", 32),
               ("note", "Note from the team", 28),
               ("often", "How often do you see this mistake?", 15), ("ok", "Are the description, example and fix right?", 17),
               ("comment", "Your comment or correction", 40),
               ("spot", "How we spot it", 32), ("freq", "Our guess: how common", 12), ("sev", "Our guess: how serious", 12),
               ("routine", "Re-teaching routine ready?", 11), ("skill_hi", "कौशल (Hindi)", 24)]
    m_rows = [{"start": "Start here" if m["competency_id"] in START_SKILLS else "", "id": m["id"],
               "skill": f"{m['competency_id']} {m['skill_en']}", "grade": grade(m["grade_level"]), "name_en": m["name_en"],
               "name_hi": m["name_hi"], "does": m["error_pattern"], "right": m["example_correct"], "wrong": m["example_incorrect"],
               "fix": m["intervention_strategy"], "note": TEAM_NOTES.get(m["id"], ""), "spot": m["diagnostic_indicator"],
               "freq": plain(m["frequency"]), "sev": plain(m["severity"]), "routine": "Yes" if m["n_routines"] else "No", "skill_hi": m["skill_hi"]}
              for m in mistakes]
    mi, m_last = write_table(ws_m, m_specs, m_rows, reviewer={"often", "ok", "comment"}, centered={"start", "grade", "freq", "sev", "routine"})
    emphasise(ws_m, mi, m_last)
    add_list(ws_m, mi["often"], 2, m_last, ["Often", "Sometimes", "Rarely", "Never seen"], "Pick from the list", "Choose Often, Sometimes, Rarely or Never seen.")
    add_list(ws_m, mi["ok"], 2, m_last, ["Yes", "Needs change"], "Pick from the list", "Choose Yes or Needs change.")
    ws_m.freeze_panes = "C2"
    ws_m.sheet_view.zoomScale = 85

    # ── Prerequisites ───────────────────────────────────────────────────────
    p_specs = [("start", "Start here?", 9), ("sid", "Skill ID", 9), ("skill", "Skill", 34), ("pid", "Needs: ID", 9),
               ("pre", "Needs: skill", 34), ("type", "Link type (ours)", 11), ("note", "Note from the team", 34),
               ("right", "Is this link right?", 13), ("typeok", "Is hard or soft right?", 17), ("comment", "Your comment", 36),
               ("skill_hi", "कौशल (Hindi)", 26), ("pre_hi", "आवश्यक कौशल (Hindi)", 26), ("sgrade", "Skill grade", 11), ("pgrade", "Needs: grade", 11)]
    p_rows = [{"start": "Start here" if (k["competency_id"] in START_SKILLS or k["prerequisite_id"] in START_SKILLS) else "",
               "sid": k["competency_id"], "skill": k["skill_en"], "pid": k["prerequisite_id"], "pre": k["pre_en"],
               "type": k["prerequisite_type"], "note": LINK_NOTES.get((k["competency_id"], k["prerequisite_id"]), ""),
               "skill_hi": k["skill_hi"], "pre_hi": k["pre_hi"], "sgrade": grade(k["grade_level"]), "pgrade": grade(k["pre_grade"])}
              for k in links]
    pi, p_last = write_table(ws_p, p_specs, p_rows, reviewer={"right", "typeok", "comment"}, centered={"start", "sid", "pid", "type", "sgrade", "pgrade"})
    emphasise(ws_p, pi, p_last)
    add_list(ws_p, pi["right"], 2, p_last, ["Right", "Wrong", "Not sure"], "Pick from the list", "Choose Right, Wrong or Not sure.")
    add_list(ws_p, pi["typeok"], 2, p_last, ["Right", "Should be hard", "Should be soft"], "Pick from the list", "Choose Right, Should be hard or Should be soft.")
    ws_p.freeze_panes = "D2"
    ws_p.sheet_view.zoomScale = 90

    # ── Skills (reference) ──────────────────────────────────────────────────
    s_specs = [("id", "Skill ID", 10), ("en", "Skill (English)", 56), ("hi", "कौशल (Hindi)", 44), ("grade", "Grade", 11),
               ("subject", "Subject", 11), ("topic", "Topic area", 26)]
    s_rows = [{"id": s["id"], "en": s["name_en"], "hi": s["name_hi"], "grade": grade(s["grade_level"]),
               "subject": "Numeracy" if s["domain_id"] == "numeracy" else "Literacy", "topic": s["topic"]} for s in skills]
    _, s_last = write_table(ws_s, s_specs, s_rows, reviewer=set())
    ws_s.freeze_panes = "B2"

    # ── Missing links (the expert adds what we left out) ────────────────────
    x_labels = ["Skill ID", "Needs: skill ID", "Link type", "Why (your words)", "Skill name", "Needs: skill name"]
    x_widths = [12, 14, 11, 60, 44, 44]
    for i, (lab, w) in enumerate(zip(x_labels, x_widths), start=1):
        c = ws_x.cell(row=1, column=i, value=lab)
        c.font = f(bold=True, color="FFFFFF" if i >= 5 else "3B2A00")
        c.fill = HEAD_OURS if i >= 5 else HEAD_YOURS
        c.alignment = CENTER
        c.border = BOX
        ws_x.column_dimensions[L(i)].width = w
    ws_x.row_dimensions[1].height = 34
    example = ["N2.3.2", "N1.2.4", "soft", "EXAMPLE, delete this row: carrying relies on knowing that 10 ones make 1 ten."]
    first_in, last_in = 3, 32
    for r in range(2, last_in + 1):
        for c in range(1, 7):
            cell = ws_x.cell(row=r, column=c)
            cell.border = BOX
            cell.alignment = WRAP if c in (4, 5, 6) else CENTER
            cell.font = f(italic=(r == 2), color="595959" if r == 2 else "000000")
            cell.fill = GREY if r == 2 else (YELLOW if c <= 4 else PatternFill())
        if r == 2:
            for c, v in enumerate(example, start=1):
                ws_x.cell(row=r, column=c, value=v)
        for c, col in ((5, "A"), (6, "B")):
            ws_x.cell(row=r, column=c, value=f'=IFERROR(INDEX(Skills!$B$2:$B${s_last},MATCH({col}{r},Skills!$A$2:$A${s_last},0)),"")')
    for col in ("A", "B"):
        dv = DataValidation(type="list", formula1=f"=Skills!$A$2:$A${s_last}", allow_blank=True, showErrorMessage=True,
                            errorTitle="Unknown skill", error="Pick a skill ID from the list (see the Skills sheet).")
        dv.add(f"{col}{first_in}:{col}{last_in}")
        ws_x.add_data_validation(dv)
    add_list(ws_x, 3, first_in, last_in, ["hard", "soft"], "Pick from the list", "Choose hard or soft.")
    ws_x.freeze_panes = "A2"

    # ── Read me ─────────────────────────────────────────────────────────────
    ws = ws_r
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 100
    n_start_m = sum(1 for m in mistakes if m["competency_id"] in START_SKILLS)
    n_start_p = sum(1 for k in links if k["competency_id"] in START_SKILLS or k["prerequisite_id"] in START_SKILLS)
    rows = [
        ("Ankur Saathi: review pack 1", None, "title"),
        ("Common mistakes and skill prerequisites", "Two lists the teaching plans are built on. Your judgement as an educator is what we need: please correct anything that does not match what you see in real classrooms.", "sub"),
        (None, None, None),
        ("YOUR PROGRESS (updates by itself)", None, "head"),
        ("Mistakes you have answered", f"=COUNTA(Mistakes!${L(mi['ok'])}$2:${L(mi['ok'])}${m_last})&\" of \"&COUNTA(Mistakes!${L(mi['id'])}$2:${L(mi['id'])}${m_last})", "formula"),
        ("Links you have answered", f"=COUNTA(Prerequisites!${L(pi['right'])}$2:${L(pi['right'])}${p_last})&\" of \"&COUNTA(Prerequisites!${L(pi['sid'])}$2:${L(pi['sid'])}${p_last})", "formula"),
        ("Missing links you have added", f"=COUNTA(\'Missing links\'!$A$3:$A${last_in})", "formula"),
        (None, None, None),
        ("WHAT TO DO", None, "head"),
        ("1. Mistakes sheet", "For each common mistake (for example, a child forgetting the carry), say how often you see it, whether our description, example and suggested fix are right, and write a correction if not.", None),
        ("2. Prerequisites sheet", "Each row says: to learn this skill, a child needs that skill first. Say whether the link is right, and whether it is correctly marked hard or soft.", None),
        ("3. Missing links sheet", "If a skill needs another skill that we have not linked, add it there. Pick the skill IDs from the dropdown; the names fill in by themselves.", None),
        ("4. Short on time?", f"Start with the rows marked \"Start here\" ({n_start_m} mistakes and {n_start_p} links). They belong to the lesson in the plan we sent you: adding two numbers with and without carrying. You can skip the Skills sheet; it is only a reference list.", None),
        (None, None, None),
        ("WORDS WE USE", None, "head"),
        ("Hard link", "The child cannot do the skill without the other skill. The plan uses hard links to decide what the weakest group works on.", None),
        ("Soft link", "The other skill helps but is not essential.", None),
        ("Our guess", "How common and how serious we think a mistake is. These are the team's own estimates, not measured. Please overrule them.", None),
        (None, None, None),
        ("COLOUR GUIDE", None, "head"),
        ("Yellow cells", "Yours to fill in. Everything else is ours.", "yellowkey"),
        ("Orange \"Start here\"", "The rows we most need answered if time is short.", "startkey"),
        ("Grey italic row", "An example (on the Missing links sheet). Delete or overwrite it.", "greykey"),
        (None, None, None),
        ("A FILLED ROW LOOKS LIKE", None, "head"),
        ("Mistakes sheet", "Mistake N2.3.2-M1 (forgets the carry): How often = Often; Right? = Needs change; Comment = \"In my class this mostly happens when the ones sum is 12 or more, not for 10.\"", None),
        ("Prerequisites sheet", "N2.3.2 needs N2.3.1 (hard): Is this link right? = Right; Is hard or soft right? = Right; Comment left empty.", None),
        (None, None, None),
        ("ABOUT THIS FILE", None, "head"),
        ("Built on", f"{datetime.date.today().isoformat()} from the team's database: {len(mistakes)} mistakes, {len(links)} prerequisite links, {len(skills)} skills. Please send the file back with your answers; we will update the database from it.", None),
    ]
    for r, (a, b, kind) in enumerate(rows, start=1):
        ca, cb = ws.cell(row=r, column=1, value=a), ws.cell(row=r, column=2, value=b)
        ca.font, cb.font = f(bold=True), f()
        ca.alignment = cb.alignment = WRAP
        if kind == "title":
            ca.font = f(bold=True, size=16, color=GREEN)
            ca.alignment = Alignment(wrap_text=False, vertical="top")
        elif kind == "sub":
            ca.font = f(bold=True, size=12, color=GREEN)
        elif kind == "head":
            ca.font = f(bold=True, color="FFFFFF")
            ca.fill = cb.fill = HEAD_OURS
        elif kind == "formula":
            cb.font = f(bold=True, size=12)
            cb.alignment = Alignment(horizontal="left", vertical="top")
        elif kind == "yellowkey":
            ca.fill = YELLOW
        elif kind == "startkey":
            ca.fill = START
        elif kind == "greykey":
            ca.fill = GREY
            ca.font = f(bold=True, italic=True, color="595959")
    ws.sheet_view.showGridLines = False
    for sh, color in ((ws_r, GREEN), (ws_m, "F4B400"), (ws_p, "F4B400"), (ws_x, "F4B400"), (ws_s, "95D5B2")):
        sh.sheet_properties.tabColor = color
    for sh in (ws_r, ws_m, ws_p, ws_x, ws_s):
        sh.page_setup.orientation = "landscape"
        sh.page_setup.fitToWidth = 1
        sh.page_setup.fitToHeight = 0
        sh.sheet_properties.pageSetUpPr.fitToPage = True
    ws_m.print_title_rows = ws_p.print_title_rows = ws_s.print_title_rows = "1:1"
    wb.save(out_path)
    return m_last, p_last


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default="review_pack_1.xlsx")
    ac.add_db_args(ap)
    args = ap.parse_args()
    mistakes, links, skills = await load(args)
    build(mistakes, links, skills, args.out)
    print(f"Wrote {args.out}: {len(mistakes)} mistakes, {len(links)} prerequisite links, {len(skills)} skills")


if __name__ == "__main__":
    asyncio.run(main())
