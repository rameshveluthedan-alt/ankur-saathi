"""
Ankur Saathi — alignment of our skills to NIPUN Bharat Annexure I (the coded learning outcomes).

    python scripts/nipun_alignment.py check --pdf NIPUN-annexure.pdf   # every code in the mapping exists in the PDF; all 101 skills covered
    python scripts/nipun_alignment.py sql                              # writes db/seeds/content/05_nipun_alignment.sql
    python scripts/nipun_alignment.py workbook -o review_pack_2.xlsx   # the review workbook for an educator (reads the database)

The proposal lives in scripts/nipun_data.py. It is AI-proposed: an educator confirms or corrects it in the workbook.

Requires: pip install openpyxl asyncpg   (and pdftotext for `check`)
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse
import asyncio
import datetime
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anchor_common as ac
from build_review_pack import (AMBER, BOX, CENTER, GREEN, GREY, HEAD_OURS, HEAD_YOURS, START, START_SKILLS, WRAP, YELLOW,
                               add_list, emphasise, f, grade, write_table)
from nipun_data import MAPPING, STRANDS
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill
from openpyxl.utils import get_column_letter as L

ROOT = Path(__file__).resolve().parent.parent
CODE_RE = re.compile(r"^(IL|ILM|ECL1|HW) ?(\d)\.(\d+)$")
LEVEL_NAME = {1: "Preschool 1", 2: "Preschool 2", 3: "Balvatika", 4: "Class 1", 5: "Class 2", 6: "Class 3"}
OUR_LEVEL = {"balvatika": 3, "grade_1": 4, "grade_2": 5, "grade_3": 6}
DEFAULT_PDF = "/mnt/user-data/uploads/NIPUN-BHARAT-GUIDELINES-EN-268-288.pdf"


def level_of(code: str) -> int:
    return int(CODE_RE.match(code).group(2))


def relation(codes: list, grade_level: str) -> tuple[str, str]:
    """(NIPUN's level for the first code, how it compares with ours)"""
    if not codes:
        return "", ""
    d, ours = level_of(codes[0]), OUR_LEVEL[grade_level]
    return LEVEL_NAME[d], "same level" if d == ours else ("NIPUN earlier" if d < ours else "NIPUN later")


def norm(text: str) -> str:
    return re.sub(r"\b(IL|ILM|ECL1|HW)\s+(\d)", r"\1\2", text)


# ── check ───────────────────────────────────────────────────────────────────

async def cmd_check(args):
    db = await ac.connect(args)
    ids = [r["id"] for r in await db.fetch("SELECT id FROM competencies")]
    await db.close()
    problems = []
    missing, extra = sorted(set(ids) - set(MAPPING)), sorted(set(MAPPING) - set(ids))
    if missing:
        problems.append(f"skills with no mapping row: {missing}")
    if extra:
        problems.append(f"mapping rows for skills that do not exist: {extra}")
    all_codes = set()
    for sid, (codes, match, conf, says, note) in MAPPING.items():
        if match not in ("exact", "finer", "related", "none") or conf not in ("high", "medium", "low"):
            problems.append(f"{sid}: bad match/confidence")
        if (match == "none") != (not codes):
            problems.append(f"{sid}: 'none' must have no codes, and anything else needs at least one")
        if codes and not says:
            problems.append(f"{sid}: no 'what NIPUN says'")
        for c in codes:
            if not CODE_RE.match(c):
                problems.append(f"{sid}: '{c}' is not a valid code")
            else:
                all_codes.add(c)
    for _, levels in STRANDS:
        all_codes |= {c for c, _ in levels.values()}
    text = norm(subprocess.run(["pdftotext", args.pdf, "-"], capture_output=True, text=True, check=True).stdout)
    absent = sorted(c for c in all_codes if norm(c).replace(" ", "") not in text.replace(" ", ""))
    print(f"mapping rows: {len(MAPPING)} for {len(ids)} skills | distinct NIPUN codes used (mapping + strands): {len(all_codes)}")
    print(f"codes NOT found in {Path(args.pdf).name}: {absent or 'none'}")
    by = {}
    for v in MAPPING.values():
        by[v[1]] = by.get(v[1], 0) + 1
    print("match types:", dict(sorted(by.items())))
    for p in problems:
        print("PROBLEM:", p)
    sys.exit(1 if (problems or absent) else 0)


# ── sql ─────────────────────────────────────────────────────────────────────

def q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


async def cmd_sql(args):
    out = ["-- Proposed alignment of each skill to NIPUN Bharat Annexure I. Written by scripts/nipun_alignment.py sql.",
           "-- AI-proposed (nipun_review_status = 'ai_proposed') until an educator confirms it.", ""]
    for sid in sorted(MAPPING):
        codes, match, conf, says, note = MAPPING[sid]
        arr = "ARRAY[" + ", ".join(q(c) for c in codes) + "]::text[]" if codes else "NULL"
        out.append(f"UPDATE competencies SET nipun_codes = {arr}, nipun_match = {q(match)}, nipun_confidence = {q(conf)}, "
                   f"nipun_says = {q(says) if says else 'NULL'}, nipun_note = {q(note) if note else 'NULL'} WHERE id = {q(sid)};")
    path = ROOT / "db" / "seeds" / "content" / "05_nipun_alignment.sql"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}: {len(MAPPING)} updates")


# ── workbook ────────────────────────────────────────────────────────────────

async def cmd_workbook(args):
    db = await ac.connect(args)
    order = ("(c.id LIKE 'L%'), CASE c.grade_level WHEN 'balvatika' THEN 0 WHEN 'grade_1' THEN 1 WHEN 'grade_2' THEN 2 ELSE 3 END, c.sort_order, c.id")
    rows = await db.fetch(f"""SELECT c.id, c.name_en, c.name_hi, c.grade_level, c.nipun_codes, c.nipun_match, c.nipun_confidence,
                                     c.nipun_says, c.nipun_note FROM competencies c ORDER BY {order}""")
    await db.close()
    if any(r["nipun_match"] is None for r in rows):
        sys.exit("Some skills have no alignment yet: run the sql command and load db/seeds/content/05_nipun_alignment.sql first.")
    rows = sorted(rows, key=lambda r: r["id"] not in START_SKILLS)

    wb = Workbook()
    ws_r = wb.active
    ws_r.title = "Read me"
    ws_a = wb.create_sheet("Alignment")
    ws_s = wb.create_sheet("NIPUN strands")

    a_specs = [("start", "Start here?", 9), ("id", "Skill ID", 9), ("skill", "Skill", 34), ("hi", "कौशल (Hindi)", 26), ("grade", "Our grade", 11),
               ("codes", "NIPUN code(s)", 16), ("says", "What NIPUN says (our own words)", 44), ("level", "NIPUN level (first code)", 14),
               ("rel", "Compared with ours", 14), ("match", "Match", 10), ("conf", "Our confidence", 11), ("note", "Note from the team", 40),
               ("right", "Is this match right?", 15), ("better", "Better code, or your comment", 40)]
    a_rows = []
    for r in rows:
        codes = list(r["nipun_codes"] or [])
        lvl, rel = relation(codes, r["grade_level"])
        a_rows.append({"start": "Start here" if r["id"] in START_SKILLS else "", "id": r["id"], "skill": r["name_en"], "hi": r["name_hi"],
                       "grade": grade(r["grade_level"]), "codes": "; ".join(codes) or "none", "says": r["nipun_says"] or "",
                       "level": lvl, "rel": rel, "match": r["nipun_match"], "conf": r["nipun_confidence"], "note": r["nipun_note"] or ""})
    ai, a_last = write_table(ws_a, a_specs, a_rows, reviewer={"right", "better"}, centered={"start", "id", "grade", "codes", "level", "rel", "match", "conf"})
    emphasise(ws_a, ai, a_last)
    for rr in range(2, a_last + 1):                      # notes are routine here, not warnings: regular weight
        ws_a.cell(row=rr, column=ai["note"]).font = f()
    for rr in range(2, a_last + 1):
        if ws_a.cell(row=rr, column=ai["match"]).value == "none":
            ws_a.cell(row=rr, column=ai["match"]).font = f(bold=True, color="9C2F00")
        if ws_a.cell(row=rr, column=ai["rel"]).value in ("NIPUN earlier", "NIPUN later"):
            ws_a.cell(row=rr, column=ai["rel"]).font = f(bold=True, color="9C4A00")
    add_list(ws_a, ai["right"], 2, a_last, ["Right", "Wrong", "Better code"], "Pick from the list", "Choose Right, Wrong or Better code.")
    ws_a.freeze_panes = "D2"
    ws_a.sheet_view.zoomScale = 90

    # strands: which NIPUN rows do our skills cover?
    code_to_skills, kinds = {}, {}
    for r in rows:
        for c in (r["nipun_codes"] or []):
            code_to_skills.setdefault(c, []).append(r["id"])
            kinds.setdefault(c, set()).add(r["nipun_match"])
    s_specs = [("strand", "NIPUN strand (numeracy)", 30), ("bv", "Balvatika", 30), ("c1", "Class 1", 30), ("c2", "Class 2", 30), ("c3", "Class 3", 30),
               ("ours", "Our skills that map here", 24), ("cov", "Do we cover it?", 12), ("gap", "Should we fill this gap?", 15), ("comment", "Your comment", 36)]
    s_rows = []
    for name, levels in STRANDS:
        cell = lambda k: (f"{levels[k][0]}: {levels[k][1]}" if k in levels else "")
        hit = sorted({s for k in levels for s in code_to_skills.get(levels[k][0], [])})
        strong = any(kinds.get(levels[k][0], set()) & {"exact", "finer"} for k in levels)
        weak = any(levels[k][0] in kinds for k in levels)
        s_rows.append({"strand": name, "bv": cell("BV"), "c1": cell("C1"), "c2": cell("C2"), "c3": cell("C3"),
                       "ours": ", ".join(hit) or "none", "cov": "Yes" if strong else ("Partly" if weak else "No")})
    si, s_last = write_table(ws_s, s_specs, s_rows, reviewer={"gap", "comment"}, centered={"cov"})
    for rr in range(2, s_last + 1):
        v = ws_s.cell(row=rr, column=si["cov"]).value
        if v == "No":
            ws_s.cell(row=rr, column=si["cov"]).font = f(bold=True, color="9C2F00")
            ws_s.cell(row=rr, column=si["cov"]).fill = PatternFill("solid", fgColor="FDE2E2")
    add_list(ws_s, si["gap"], 2, s_last, ["Yes, add it", "No", "Not for the pilot"], "Pick from the list", "Choose Yes add it, No or Not for the pilot.")
    ws_s.freeze_panes = "B2"

    # Read me
    ws = ws_r
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 100
    am, rl, cf = L(ai["match"]), L(ai["rel"]), L(ai["right"])
    rng = lambda col: f"Alignment!${col}$2:${col}${a_last}"
    content = [
        ("Ankur Saathi: review pack 2", None, "title"),
        ("Alignment to the national NIPUN Bharat outcomes", "Each of our 101 skills is matched to the coded learning outcomes in Annexure I of the NIPUN Bharat Guidelines for Implementation (2021). The matches were proposed by an AI and have not been checked by an educator. That check is what we need.", "sub"),
        (None, None, None),
        ("YOUR PROGRESS (updates by itself)", None, "head"),
        ("Matches you have answered", f"=COUNTA({rng(cf)})&\" of \"&COUNTA({rng('B')})", "formula"),
        (None, None, None),
        ("HOW THE TEAM'S PROPOSAL LOOKS", None, "head"),
        ("Exact", f"=COUNTIF({rng(am)},\"exact\")&\" skills: the same outcome as ours\"", "formula"),
        ("Finer", f"=COUNTIF({rng(am)},\"finer\")&\" skills: ours is one piece of a broader NIPUN outcome\"", "formula"),
        ("Related", f"=COUNTIF({rng(am)},\"related\")&\" skills: close in topic, but wider, narrower or at a different level\"", "formula"),
        ("None", f"=COUNTIF({rng(am)},\"none\")&\" skills: no counterpart in the annexure\"", "formula"),
        ("Taught earlier or later than NIPUN", f"=COUNTIF({rng(rl)},\"NIPUN later\")&\" skills we teach EARLIER than NIPUN; \"&COUNTIF({rng(rl)},\"NIPUN earlier\")&\" skills we teach LATER than NIPUN\"", "formula"),
        (None, None, None),
        ("WHAT TO DO", None, "head"),
        ("1. Alignment sheet", "For each skill, check that the NIPUN code and the short description (in our own words) really describe the same learning. Pick Right, Wrong or Better code, and write the better code if you have one.", None),
        ("2. NIPUN strands sheet", "This lists the numeracy strands of the annexure, with the outcomes for Balvatika and Classes 1 to 3. Red \"No\" rows are strands where we have no skill. Tell us which gaps matter for the pilot.", None),
        ("3. Short on time?", f"Start with the rows marked \"Start here\" ({sum(1 for r in rows if r['id'] in START_SKILLS)} skills: adding with and without carrying), then the red rows on the strands sheet.", None),
        (None, None, None),
        ("THINGS TO KNOW", None, "head"),
        ("Language outcomes are coarser", "NIPUN's coded language outcomes do not list matras, letter counts or reading speeds (reading-speed targets are in the separate Lakshya). Most of our literacy skills can therefore only be \"related\". We have not forced exact matches.", None),
        ("Level differences", "The \"Compared with ours\" column shows where NIPUN places an outcome in an earlier or later class than we do. Some of these may be deliberate choices on our side; tell us which should change.", None),
        ("Codes", "IL and ILM: cognitive and mathematics outcomes (Goal 3). ECL1: first-language communication (Goal 2). HW: health and wellbeing (Goal 1). The first digit is the level: 3 is Balvatika, 4 to 6 are Classes 1 to 3.", None),
        ("Wording", "The descriptions are our own short paraphrases, not the annexure's wording. The source is the Department of School Education and Literacy, Ministry of Education.", None),
        (None, None, None),
        ("ABOUT THIS FILE", None, "head"),
        ("Built on", f"{datetime.date.today().isoformat()} from the team's database: {len(rows)} skills. Please send the file back with your answers.", None),
    ]
    for r, (a, b, kind) in enumerate(content, start=1):
        ca, cb = ws.cell(row=r, column=1, value=a), ws.cell(row=r, column=2, value=b)
        ca.font, cb.font = f(bold=True), f()
        ca.alignment = cb.alignment = WRAP
        if kind == "title":
            ca.font, ca.alignment = f(bold=True, size=16, color=GREEN), Alignment(wrap_text=False, vertical="top")
        elif kind == "sub":
            ca.font = f(bold=True, size=12, color=GREEN)
        elif kind == "head":
            ca.font = f(bold=True, color="FFFFFF")
            ca.fill = cb.fill = HEAD_OURS
        elif kind == "formula":
            cb.font = f(bold=True, size=11)
            cb.alignment = Alignment(horizontal="left", vertical="top")
    ws.sheet_view.showGridLines = False
    for sh, color in ((ws_r, GREEN), (ws_a, "F4B400"), (ws_s, "F4B400")):
        sh.sheet_properties.tabColor = color
        sh.page_setup.orientation = "landscape"
        sh.page_setup.fitToWidth = 1
        sh.page_setup.fitToHeight = 0
        sh.sheet_properties.pageSetUpPr.fitToPage = True
    ws_a.print_title_rows = ws_s.print_title_rows = "1:1"
    wb.save(args.out)
    print(f"Wrote {args.out}: {len(rows)} skills, {len(STRANDS)} numeracy strands")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["check", "sql", "workbook"])
    ap.add_argument("--pdf", default=DEFAULT_PDF)
    ap.add_argument("-o", "--out", default="review_pack_2.xlsx")
    ac.add_db_args(ap)
    args = ap.parse_args()
    await {"check": cmd_check, "sql": cmd_sql, "workbook": cmd_workbook}[args.command](args)


if __name__ == "__main__":
    asyncio.run(main())
