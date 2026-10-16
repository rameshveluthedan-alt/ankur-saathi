"""
Ankur Saathi — build the anchor-bank spreadsheet template.

Reads the current competencies, anchors and TLMs from the database and writes an Excel
workbook that FLN experts and teachers can fill in. Re-run it any time the bank changes so
the reference lists and the gap tracker stay current.

    python scripts/build_anchor_template.py --env-file backend/.env -o anchor_template.xlsx

Requires: pip install openpyxl asyncpg
"""

import argparse
import asyncio
import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

import anchor_common as ac

FONT = "Arial"
GREEN = "2D6A4F"
BAND = "D8F3DC"
INPUT_FILL = PatternFill("solid", fgColor="FFF8DC")     # soft yellow = fill me in
EXAMPLE_FILL = PatternFill("solid", fgColor="E7E6E6")   # grey = example, delete or overwrite
HEAD_FILL = PatternFill("solid", fgColor=GREEN)
BAND_FILL = PatternFill("solid", fgColor=BAND)
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def f(bold=False, italic=False, size=10, color="000000"):
    return Font(name=FONT, bold=bold, italic=italic, size=size, color=color)


WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

# ── The worked example (a real anchor from the bank, restructured into the template's columns) ──
EXAMPLE = {
    "anchor_id": "EXAMPLE — delete this row",
    "subject": "Numeracy",
    "title_en": "Place Value Treasure Hunt",
    "title_hi": "स्थानीय मान खज़ाना खोज",
    "description_en": "Children decode a secret number from tens-and-ones clues, building it with bundling sticks.",
    "theme": "school", "setting": "universal", "duration": 10,
    "gr_balvatika": None, "gr_1": "Y", "gr_2": "Y", "gr_3": "Y",
    "primary_1": "N1.2.4", "primary_2": "N2.2.2", "primary_3": None,
    "secondary_1": "N1.2.3", "secondary_2": "N2.2.1", "secondary_3": "N3.2.2", "secondary_4": None,
    "setup_hi": "बोर्ड पर लिखें: 'मेरे पास एक गुप्त संख्या है! इसमें 3 दहाइयाँ और 4 इकाइयाँ हैं।'",
    "whole_class_hi": "सब मिलकर संख्या बताएँ: 34। फिर पूछें: 'दहाई का अंक कौन सा है? इकाई का?'",
    "beginner_hi": "बंडल की छड़ियों से 34 बनाओ: 3 बंडल और 4 खुली छड़ियाँ। गिनकर देखो।",
    "progressor_hi": "नई गुप्त संख्या: 5 दहाइयाँ, 2 इकाइयाँ। संख्या लिखो और विस्तारित रूप लिखो: 52 = 50 + 2।",
    "proficient_hi": "3 सैकड़े, 4 दहाइयाँ, 5 इकाइयाँ — संख्या क्या है? उससे 10 ज़्यादा क्या होगा? 100 ज़्यादा?",
    "closing_hi": "हर बच्चा अपने साथी के लिए एक गुप्त संख्या का सुराग बनाए।",
    "needs_print": "N", "tlm_1": "TLM-001", "tlm_2": "TLM-005",
    "source": "original", "validated_by": "(name of the expert who checked the skill tags)",
}


async def load_data(args):
    db = await ac.connect(args)
    comps = await db.fetch("""
        SELECT c.id, s.domain_id, c.grade_level, c.name_en, c.name_hi, s.name_en AS topic, c.sort_order
        FROM competencies c JOIN subdomains s ON c.subdomain_id = s.id
        WHERE c.is_active = TRUE ORDER BY c.id""")
    anchors = await db.fetch("""
        SELECT id, title_en, title_hi, domain_id, grade_range, primary_competency_ids,
               COALESCE(secondary_competency_ids, '{}') AS secondary_competency_ids
        FROM anchor_activities WHERE is_active = TRUE ORDER BY id""")
    tlms = await db.fetch("SELECT id, name_en, name_hi, availability FROM tlm_references WHERE is_active = TRUE ORDER BY id")
    await db.close()
    return comps, anchors, tlms


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = f(bold=True, color="FFFFFF")
        cell.fill = HEAD_FILL
        cell.alignment = CENTER
        cell.border = BOX


def build(comps, anchors, tlms, out_path):
    wb = Workbook()
    ws_readme = wb.active
    ws_readme.title = "Read me"
    ws_a = wb.create_sheet(ac.SHEET_ANCHORS)
    ws_c = wb.create_sheet("Competencies")
    ws_cur = wb.create_sheet("Current anchors")
    ws_t = wb.create_sheet("TLMs")

    ncomp = len(comps)
    comp_grade = {c["id"]: c["grade_level"] for c in comps}
    last_comp_row = ncomp + 1

    # ── Current anchors (reference) ──────────────────────────────────────────
    max_p = max([3] + [len(a["primary_competency_ids"]) for a in anchors])
    max_s = max([5] + [len(a["secondary_competency_ids"]) for a in anchors])
    cur_heads = ["Anchor ID", "Title (English)", "शीर्षक (Hindi)", "Subject", "Grades"]
    cur_heads += [f"Main skill {i}" for i in range(1, max_p + 1)] + [f"Also practises {i}" for i in range(1, max_s + 1)]
    cur_heads += ["Note"]
    ws_cur.append(cur_heads)
    style_header(ws_cur, 1, len(cur_heads))
    first_tag_col, last_tag_col = 6, 5 + max_p + max_s
    for a in anchors:
        grades = a["grade_range"]
        eff = lambda ids: [i for i in ids if comp_grade.get(i) in grades]
        ignored = [i for i in list(a["primary_competency_ids"]) + list(a["secondary_competency_ids"])
                   if comp_grade.get(i) not in grades]
        prim = (eff(a["primary_competency_ids"]) + [None] * max_p)[:max_p]
        sec = (eff(a["secondary_competency_ids"]) + [None] * max_s)[:max_s]
        note = ("Tag ignored (grade not in this anchor's grades): " + ", ".join(ignored)) if ignored else None
        ws_cur.append([a["id"], a["title_en"], a["title_hi"],
                       "Numeracy" if a["domain_id"] == "numeracy" else "Literacy",
                       ", ".join(ac.GRADE_LABEL[g] for g in grades)] + prim + sec + [note])
    for row in ws_cur.iter_rows(min_row=2):
        for cell in row:
            cell.font = f()
            cell.alignment = WRAP
            cell.border = BOX
    for i, w in enumerate([11, 28, 26, 11, 26] + [10] * (max_p + max_s) + [44], start=1):
        ws_cur.column_dimensions[L(i)].width = w
    ws_cur.freeze_panes = "B2"
    cur_last_row = 60
    cur_range = f"'Current anchors'!${L(first_tag_col)}$2:${L(last_tag_col)}${cur_last_row}"

    # ── Anchors (the sheet people fill in) ───────────────────────────────────
    ncols = len(ac.COLUMNS)
    # group bands (row 1)
    start = 1
    for i, col in enumerate(ac.COLUMNS, start=1):
        last = i == ncols or ac.COLUMNS[i]["group"] != col["group"]
        if last:
            ws_a.cell(row=ac.BAND_ROW, column=start, value=col["group"])
            if i > start:
                ws_a.merge_cells(start_row=ac.BAND_ROW, start_column=start, end_row=ac.BAND_ROW, end_column=i)
            c = ws_a.cell(row=ac.BAND_ROW, column=start)
            c.font = f(bold=True, color="1B4332")
            c.fill = BAND_FILL
            c.alignment = CENTER
            for k in range(start, i + 1):
                ws_a.cell(row=ac.BAND_ROW, column=k).fill = BAND_FILL
                ws_a.cell(row=ac.BAND_ROW, column=k).border = BOX
            start = i + 1
    for i, col in enumerate(ac.COLUMNS, start=1):
        ws_a.cell(row=ac.HEADER_ROW, column=i, value=col["label"])
        ws_a.column_dimensions[L(i)].width = col["width"]
    style_header(ws_a, ac.HEADER_ROW, ncols)
    ws_a.row_dimensions[ac.HEADER_ROW].height = 58
    # example row (row 3)
    for i, col in enumerate(ac.COLUMNS, start=1):
        cell = ws_a.cell(row=ac.EXAMPLE_ROW, column=i, value=EXAMPLE.get(col["key"]))
        cell.font = f(italic=True, color="595959")
        cell.fill = EXAMPLE_FILL
        cell.alignment = WRAP
        cell.border = BOX
    ws_a.row_dimensions[ac.EXAMPLE_ROW].height = 110
    # input rows
    for r in range(ac.FIRST_INPUT_ROW, ac.LAST_INPUT_ROW + 1):
        for i, col in enumerate(ac.COLUMNS, start=1):
            cell = ws_a.cell(row=r, column=i)
            cell.font = f()
            cell.fill = INPUT_FILL
            cell.alignment = CENTER if col["kind"] in ("grade", "number", "yn", "competency", "tlm", "subject", "theme", "setting") else WRAP
            cell.border = BOX
    ws_a.freeze_panes = ws_a.cell(row=ac.EXAMPLE_ROW, column=3)

    # dropdowns
    def add_dv(key, dv):
        ci = ac.col_index(key)
        dv.showErrorMessage = True
        dv.allow_blank = True
        dv.add(f"{L(ci)}{ac.FIRST_INPUT_ROW}:{L(ci)}{ac.LAST_INPUT_ROW}")
        ws_a.add_data_validation(dv)

    pick_err = dict(errorTitle="Pick from the list", error="Please choose a value from the dropdown list.")
    add_dv("subject", DataValidation(type="list", formula1='"Numeracy,Literacy"', **pick_err))
    add_dv("theme", DataValidation(type="list", formula1='"' + ",".join(ac.THEMES) + '"', **pick_err))
    add_dv("setting", DataValidation(type="list", formula1='"' + ",".join(ac.SETTINGS) + '"', **pick_err))
    add_dv("needs_print", DataValidation(type="list", formula1='"Y,N"', **pick_err))
    for key, _, _ in ac.GRADES:
        add_dv(key, DataValidation(type="list", formula1='"Y"', errorTitle="Type Y or leave empty",
                                   error="Mark Y if children of this grade can do the activity; otherwise leave empty."))
    add_dv("duration", DataValidation(type="whole", operator="between", formula1="3", formula2="30",
                                      errorTitle="Minutes", error="Enter a whole number of minutes between 3 and 30."))
    for col in ac.COLUMNS:
        if col["kind"] == "competency":
            add_dv(col["key"], DataValidation(type="list", formula1=f"=Competencies!$A$2:$A${last_comp_row}",
                                              errorTitle="Unknown skill ID",
                                              error="Pick a skill ID from the list (see the Competencies sheet)."))
        if col["kind"] == "tlm":
            add_dv(col["key"], DataValidation(type="list", formula1=f"=TLMs!$A$2:$A${len(tlms) + 1}",
                                              errorTitle="Unknown material", error="Pick a material ID from the TLMs sheet."))

    # ── Competencies (reference + live gap tracker) ──────────────────────────
    heads = ["Skill ID", "Subject", "Grade", "Skill (English)", "कौशल (Hindi)", "Topic area",
             "Anchors for this skill", "Status"]
    ws_c.append(heads)
    style_header(ws_c, 1, len(heads))
    p1, s4 = ac.col_index("primary_1"), ac.col_index("secondary_4")
    anchors_tags = f"{ac.SHEET_ANCHORS}!${L(p1)}${ac.FIRST_INPUT_ROW}:${L(s4)}${ac.LAST_INPUT_ROW}"
    # tag counts as the importer/retrieval sees them (grade must match), for sorting only
    eff_count = {c["id"]: 0 for c in comps}
    for a in anchors:
        for cid in set(list(a["primary_competency_ids"]) + list(a["secondary_competency_ids"])):
            if comp_grade.get(cid) in a["grade_range"]:
                eff_count[cid] += 1
    grade_order = {"balvatika": 0, "grade_1": 1, "grade_2": 2, "grade_3": 3}
    ordered = sorted(comps, key=lambda c: (eff_count[c["id"]] > 0, c["domain_id"], grade_order[c["grade_level"]], c["sort_order"]))
    for r, c in enumerate(ordered, start=2):
        ws_c.append([c["id"], "Numeracy" if c["domain_id"] == "numeracy" else "Literacy",
                     ac.GRADE_LABEL[c["grade_level"]], c["name_en"], c["name_hi"], c["topic"],
                     f"=COUNTIF({cur_range},$A{r})+COUNTIF({anchors_tags},$A{r})",
                     f'=IF(G{r}>0,"Covered","Needs an anchor")'])
    for row in ws_c.iter_rows(min_row=2):
        for cell in row:
            cell.font = f()
            cell.alignment = WRAP
            cell.border = BOX
        row[6].alignment = CENTER
        row[7].alignment = CENTER
    for i, w in enumerate([10, 11, 11, 52, 40, 24, 12, 17], start=1):
        ws_c.column_dimensions[L(i)].width = w
    ws_c.freeze_panes = "B2"
    ws_c.auto_filter.ref = f"A1:H{last_comp_row}"
    rng = f"H2:H{last_comp_row}"
    ws_c.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Needs an anchor"'],
                                                    fill=PatternFill("solid", bgColor="FCE4D6"), font=Font(name=FONT, color="9C2F00")))
    ws_c.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"Covered"'],
                                                    fill=PatternFill("solid", bgColor="D8F3DC"), font=Font(name=FONT, color="1B4332")))

    # ── TLMs (reference) ─────────────────────────────────────────────────────
    ws_t.append(["Material ID", "Name (English)", "नाम (Hindi)", "Availability"])
    style_header(ws_t, 1, 4)
    for t in tlms:
        ws_t.append([t["id"], t["name_en"], t["name_hi"], t["availability"]])
    for row in ws_t.iter_rows(min_row=2):
        for cell in row:
            cell.font = f()
            cell.border = BOX
    for i, w in enumerate([12, 30, 30, 14], start=1):
        ws_t.column_dimensions[L(i)].width = w

    # ── Read me ──────────────────────────────────────────────────────────────
    ws = ws_readme
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 100
    rows = [
        ("Ankur Saathi — Anchor Activity Bank", None, "title"),
        ("अंकुर साथी — एंकर गतिविधि बैंक", "An anchor is a 10-minute whole-class activity (a story or situation) in which Beginner, Progressor and Proficient children each get a task at their own level.", "sub"),
        (None, None, None),
        ("PROGRESS (updates by itself)", None, "head"),
        ("Skills with at least one anchor", f'=COUNTIF(Competencies!$H$2:$H${last_comp_row},"Covered")', "formula"),
        ("Skills still needing an anchor", f'=COUNTIF(Competencies!$H$2:$H${last_comp_row},"Needs an anchor")', "formula"),
        ("Total skills", f"=COUNTA(Competencies!$A$2:$A${last_comp_row})", "formula"),
        (None, None, None),
        ("HOW TO FILL IN  /  कैसे भरें", None, "head"),
        ("1. Pick skills to cover", "Open the 'Competencies' sheet. Skills marked 'Needs an anchor' are the priority. Filter the Status column to see them.", None),
        ("2. Add one anchor per row", "Go to the 'Anchors' sheet and fill the yellow cells, starting at row 4. The grey row 3 is only an example: you may delete or overwrite it. 'Anchors' शीट के पीले खाने भरें।", None),
        ("3. Tag the skills", "Main skill = what the activity directly teaches. Also practises = other skills children use along the way. Pick IDs from the dropdowns.", None),
        ("4. Mark the grades", "Put Y under each grade whose children can do the activity. IMPORTANT: the grade of every skill you tag must be marked, otherwise the anchor can never be matched to that skill and the import will stop with an error.", None),
        ("5. Write the activity in Hindi", "Write a concrete example with real numbers or words. You may use {{double braces}} for a part that should change every day, for example {{number}}. Each of the three levels needs its own task. हिंदी में लिखें।", None),
        ("6. Source and review", "Say where the idea comes from. If it is adapted from a published programme, note that permission is needed and obtained. Write the name of the person who checked the skill tags.", None),
        ("7. Send the file back", "Save as .xlsx and send it back. We check it with a dry run first, which also shows which skills will gain a matching anchor, and then load it.", None),
        (None, None, None),
        ("COLOUR GUIDE", None, "head"),
        ("Yellow cells", "Fill these in.", "yellowkey"),
        ("Grey italic row", "Worked example (a real anchor from the current bank). Delete or overwrite it.", "greykey"),
        ("Green headers", "Do not change the header text, because the importer finds columns by these names.", None),
        (None, None, None),
        ("NOTES AND ASSUMPTIONS", None, "head"),
        ("Counting rule", "'Anchors for this skill' counts anchors that list the skill as a main OR an also-practises skill, in the current bank plus the rows you add. The importer additionally requires that the skill's grade is marked.", None),
        ("Current bank", f"Built on {datetime.date.today().isoformat()} from the database: {len(anchors)} anchors, {ncomp} skills, {len(tlms)} materials. The 'Current anchors' sheet shows tags the system actually uses; tags it ignores are noted there.", None),
        ("Skill IDs", "Skill IDs are the project's own codes and follow the NIPUN Bharat learning ladder. Whether they are right is for the FLN experts to judge; please correct names or placements you disagree with and tell us.", None),
    ]
    for r, (a, b, kind) in enumerate(rows, start=1):
        ca, cb = ws.cell(row=r, column=1, value=a), ws.cell(row=r, column=2, value=b)
        ca.font, cb.font = f(bold=True), f()
        ca.alignment, cb.alignment = WRAP, WRAP
        if kind == "title":
            ca.font = f(bold=True, size=16, color=GREEN)
            ca.alignment = Alignment(wrap_text=False, vertical="top")   # let it run across into column B
        elif kind == "sub":
            ca.font = f(bold=True, size=13, color=GREEN)
        elif kind == "head":
            ca.font = f(bold=True, color="FFFFFF")
            ca.fill = HEAD_FILL
            cb.fill = HEAD_FILL
        elif kind == "formula":
            cb.alignment = Alignment(horizontal="left", vertical="top")
            cb.font = f(bold=True, size=12)
        elif kind == "yellowkey":
            ca.fill = INPUT_FILL
        elif kind == "greykey":
            ca.fill = EXAMPLE_FILL
            ca.font = f(bold=True, italic=True, color="595959")
    ws.sheet_view.showGridLines = False
    for sh, color in ((ws_readme, GREEN), (ws_a, "F4B400"), (ws_c, "40916C"), (ws_cur, "95D5B2"), (ws_t, "95D5B2")):
        sh.sheet_properties.tabColor = color

    # print setup: landscape, one page wide
    ws_a.page_setup.orientation = "landscape"      # 30 columns: print at normal size across pages
    for sh in (ws_readme, ws_c, ws_cur, ws_t):
        sh.page_setup.orientation = "landscape"
        sh.page_setup.fitToWidth = 1
        sh.page_setup.fitToHeight = 0
        sh.sheet_properties.pageSetUpPr.fitToPage = True
    ws_a.print_title_rows = f"{ac.BAND_ROW}:{ac.HEADER_ROW}"
    ws_c.print_title_rows = "1:1"

    wb.save(out_path)


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default="anchor_template.xlsx")
    ac.add_db_args(ap)
    args = ap.parse_args()
    comps, anchors, tlms = await load_data(args)
    build(comps, anchors, tlms, args.out)
    print(f"Wrote {args.out}: {len(comps)} skills, {len(anchors)} current anchors, {len(tlms)} materials")


if __name__ == "__main__":
    asyncio.run(main())
