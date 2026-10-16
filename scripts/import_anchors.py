"""
Ankur Saathi — import anchor activities from the filled-in spreadsheet.

DRY RUN by default: every row is checked, the import is simulated inside a database
transaction, the effect on anchor matching is reported, and everything is rolled back.
Nothing is saved until you add --apply.

    python scripts/import_anchors.py filled_anchors.xlsx --env-file backend/.env
    python scripts/import_anchors.py filled_anchors.xlsx --env-file backend/.env --apply

If any row has an error, nothing is imported (all-or-nothing) so the bank never ends up
half-loaded. Fix the rows named in the report and run again.

Requires: pip install openpyxl asyncpg
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

import anchor_common as ac

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prompts"))
from orchestrate import fetch_anchor_activity  # noqa: E402  (same retrieval the app uses)

DEVANAGARI = re.compile(r"[\u0900-\u097F]")
ID_RE = re.compile(r"^ANC-([NL])-(\d{3})$")
PREFIX = {"numeracy": "N", "r1_literacy": "L"}
GRADE_ORDER = [code for _, _, code in ac.GRADES]
LABEL = {c["key"]: c["label"] for c in ac.COLUMNS}
SUBJECT_NAME = {v: k for k, v in ac.SUBJECTS.items()}


class _DryRun(Exception):
    """Raised on purpose to roll the simulated import back."""


class _Blocked(Exception):
    """Raised to roll back an --apply that would make a skill lose its exact match."""


# lower is better
RANK = {"exact": 0, "semantic": 0, "related": 1, "topic_area": 2, "loose": 3, "none": 4}


def classify(before, after, ids):
    """Split the skills whose match changed into: better, swapped (same quality, different anchor), worse."""
    better, swapped, worse = [], [], []
    for c in sorted(ids):
        b, a = before[c], after[c]
        if b == a:
            continue
        if RANK[a[0]] < RANK[b[0]]:
            better.append(c)
        elif RANK[a[0]] > RANK[b[0]]:
            worse.append(c)
        else:
            swapped.append(c)
    return better, swapped, worse


def s(v):
    """Cell value -> stripped string or None."""
    if v is None:
        return None
    t = str(v).strip()
    return t or None


def is_yes(v):
    return (s(v) or "").lower() in ("y", "yes", "true", "1", "✓")


def read_rows(path):
    wb = load_workbook(path, data_only=True)
    if ac.SHEET_ANCHORS not in wb.sheetnames:
        sys.exit(f"ERROR: no sheet called '{ac.SHEET_ANCHORS}' in {path}")
    ws = wb[ac.SHEET_ANCHORS]
    header = {s(ws.cell(row=ac.HEADER_ROW, column=c).value): c for c in range(1, ws.max_column + 1)}
    missing = [c["label"] for c in ac.COLUMNS if c["label"] not in header]
    if missing:
        sys.exit("ERROR: the header row does not match the template. Missing columns:\n  - "
                 + "\n  - ".join(missing) + "\nPlease use the latest template (build_anchor_template.py).")
    rows, skipped = [], []
    # start right after the header: the example row may have been deleted or overwritten
    for r in range(ac.HEADER_ROW + 1, ws.max_row + 1):
        rec = {c["key"]: ws.cell(row=r, column=header[c["label"]]).value for c in ac.COLUMNS}
        if all(s(v) is None for v in rec.values()):
            continue
        if (s(rec["anchor_id"]) or "").upper().startswith("EXAMPLE"):
            skipped.append(r)
            continue
        rec["_row"] = r
        rows.append(rec)
    return rows, skipped


def build_body(rec):
    parts = ["Story setup (teacher narrates):", s(rec["setup_hi"]) or "", ""]
    if s(rec["whole_class_hi"]):
        parts += [f"Whole-class moment: {s(rec['whole_class_hi'])}", ""]
    parts += ["Differentiated participation:",
              f"- Beginners: {s(rec['beginner_hi'])}",
              f"- Progressors: {s(rec['progressor_hi'])}",
              f"- Proficients: {s(rec['proficient_hi'])}",
              "", f"Closing (whole class): {s(rec['closing_hi'])}"]
    return "\n".join(parts)


def validate(rec, comps, tlms, existing, seen_titles):
    """Returns (errors, warnings, normalized-record-or-None)."""
    errs, warns = [], []
    # required text
    for col in ac.COLUMNS:
        if col["required"] and col["kind"] != "competency" and s(rec[col["key"]]) is None and col["key"] != "subject":
            errs.append(f"'{col['label']}' is empty")
    subject = s(rec["subject"])
    domain = ac.SUBJECTS.get(subject) if subject else None
    if subject is None:
        errs.append("'Subject' is empty")
    elif domain is None:
        errs.append(f"Subject '{subject}' is not one of: {', '.join(ac.SUBJECTS)}")

    grades = [code for key, _, code in ac.GRADES if is_yes(rec[key])]
    if not grades:
        errs.append("no grade is marked Y")

    primary = list(dict.fromkeys(s(rec[f"primary_{i}"]) for i in (1, 2, 3) if s(rec[f"primary_{i}"])))
    secondary = [x for x in dict.fromkeys(s(rec[f"secondary_{i}"]) for i in (1, 2, 3, 4) if s(rec[f"secondary_{i}"]))
                 if x not in primary]
    if not primary:
        errs.append("'Main skill 1' is empty: every anchor needs at least one main skill")
    for cid in primary + secondary:
        if cid not in comps:
            errs.append(f"skill '{cid}' does not exist (pick from the dropdown)")
            continue
        c_domain, c_grade, _ = comps[cid]
        if domain and c_domain != domain:
            errs.append(f"skill {cid} is a {SUBJECT_NAME.get(c_domain, c_domain)} skill but the subject is {subject}")
        elif grades and c_grade not in grades:
            msg = (f"{cid} is a {ac.GRADE_LABEL[c_grade]} skill but {ac.GRADE_LABEL[c_grade]} is not marked Y, so this "
                   f"anchor could never be matched to it")
            (errs if cid in primary else warns).append(("main skill " if cid in primary else "also-practises skill ") + msg)

    tlm_ids = [x for x in dict.fromkeys(s(rec[k]) for k in ("tlm_1", "tlm_2")) if x]
    for t in tlm_ids:
        if t not in tlms:
            errs.append(f"material '{t}' does not exist (pick from the TLMs sheet)")

    dur = rec["duration"]
    try:
        duration = int(float(dur)) if s(dur) else 10
        if not 3 <= duration <= 30:
            errs.append("'Minutes' must be between 3 and 30")
    except ValueError:
        errs.append(f"'Minutes' is not a number: {dur!r}")
        duration = 10

    theme = s(rec["theme"])
    if theme and theme not in ac.THEMES:
        warns.append(f"theme '{theme}' is not in the standard list")
    setting = s(rec["setting"]) or "universal"

    aid = s(rec["anchor_id"])
    if aid:
        m = ID_RE.match(aid)
        if not m:
            errs.append(f"Anchor ID '{aid}' is not in the form ANC-N-001 / ANC-L-001")
        elif domain and m.group(1) != PREFIX[domain]:
            errs.append(f"Anchor ID {aid} does not match the subject {subject}")

    for key in ("title_hi", "setup_hi", "beginner_hi", "progressor_hi", "proficient_hi", "closing_hi"):
        v = s(rec[key])
        if v and not DEVANAGARI.search(v):
            warns.append(f"'{LABEL[key]}' has no Hindi (Devanagari) text")
        elif v and key not in ("title_hi", "closing_hi") and len(v) < 20:
            warns.append(f"'{LABEL[key]}' is very short ({len(v)} characters)")
    if not s(rec["source"]):
        warns.append("no source given")
    if not s(rec["validated_by"]):
        warns.append("skill tags not yet checked by an expert ('Skill tags checked by' is empty)")

    title = (s(rec["title_en"]) or "").lower()
    if title:
        other = existing.get(title)
        if other and other != aid:
            warns.append(f"same English title as existing anchor {other}: possible duplicate")
        if title in seen_titles:
            warns.append(f"same English title as row {seen_titles[title]} of this sheet")
        seen_titles.setdefault(title, rec["_row"])

    if errs:
        return errs, warns, None
    norm = dict(
        id=aid, title_en=s(rec["title_en"]), title_hi=s(rec["title_hi"]), description_en=s(rec["description_en"]),
        template_body=build_body(rec), primary=primary, secondary=secondary, domain_id=domain,
        grades=[g for g in GRADE_ORDER if g in grades], duration=duration, theme=theme or "other",
        setting=setting, requires_print=is_yes(rec["needs_print"]), tlm_ids=tlm_ids,
        source=s(rec["source"]), validated_by=s(rec["validated_by"]), row=rec["_row"])
    return errs, warns, norm


UPSERT = """
INSERT INTO anchor_activities
  (id, title_en, title_hi, description_en, template_body, primary_competency_ids, secondary_competency_ids,
   domain_id, grade_range, duration_minutes, theme, setting, requires_print, requires_tlm, tlm_ids,
   source, validated_by, is_active, imported_at)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,TRUE,NOW())
ON CONFLICT (id) DO UPDATE SET
  title_en=EXCLUDED.title_en, title_hi=EXCLUDED.title_hi, description_en=EXCLUDED.description_en,
  template_body=EXCLUDED.template_body, primary_competency_ids=EXCLUDED.primary_competency_ids,
  secondary_competency_ids=EXCLUDED.secondary_competency_ids, domain_id=EXCLUDED.domain_id,
  grade_range=EXCLUDED.grade_range, duration_minutes=EXCLUDED.duration_minutes, theme=EXCLUDED.theme,
  setting=EXCLUDED.setting, requires_print=EXCLUDED.requires_print, requires_tlm=EXCLUDED.requires_tlm,
  tlm_ids=EXCLUDED.tlm_ids, source=EXCLUDED.source, validated_by=EXCLUDED.validated_by, is_active=TRUE,
  imported_at=NOW()
"""

SEARCH = """
UPDATE anchor_activities SET search_text = to_tsvector('simple',
  coalesce(title_en,'') || ' ' || coalesce(description_en,'') || ' ' || coalesce(theme,'') || ' ' ||
  coalesce(setting,'') || ' ' || array_to_string(primary_competency_ids, ' ') || ' ' ||
  coalesce(array_to_string(secondary_competency_ids, ' '), ''))
WHERE id = ANY($1::text[])
"""


async def match_snapshot(db, comp_ids, comps):
    out = {}
    for cid in sorted(comp_ids):
        domain, grade, _ = comps[cid]
        a = await fetch_anchor_activity(db, domain, grade, cid)
        out[cid] = (a.match_quality, a.id) if a else ("none", "-")
    return out


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="the filled-in .xlsx")
    ap.add_argument("--apply", action="store_true", help="really save (default is a dry run)")
    ap.add_argument("--allow-regressions", action="store_true",
                    help="allow saving even if some skill loses a better match than it has today")
    ac.add_db_args(ap)
    args = ap.parse_args()

    rows, skipped = read_rows(args.file)
    print(f"\nReading {args.file}")
    print(f"  {len(rows)} anchor row(s) found" + (f"; example row {skipped} skipped" if skipped else ""))
    if not rows:
        print("  Nothing to import.")
        return

    db = await ac.connect(args)
    comps = {r["id"]: (r["domain_id"], r["grade_level"], r["name_en"]) for r in await db.fetch(
        "SELECT c.id, s.domain_id, c.grade_level, c.name_en FROM competencies c JOIN subdomains s ON c.subdomain_id = s.id")}
    tlms = {r["id"] for r in await db.fetch("SELECT id FROM tlm_references")}
    ex = await db.fetch("SELECT id, title_en FROM anchor_activities")
    existing_titles = {r["title_en"].lower(): r["id"] for r in ex}
    existing_ids = {r["id"] for r in ex}

    records, n_err, n_warn, seen = [], 0, 0, {}
    print()
    for rec in rows:
        errs, warns, norm = validate(rec, comps, tlms, existing_titles, seen)
        label = s(rec["title_en"]) or "(no title)"
        print(f"Row {rec['_row']}: {label}  ->  {'ERROR' if errs else ('OK, with warnings' if warns else 'OK')}")
        for e in errs:
            print(f"    ERROR   {e}")
        for w in warns:
            print(f"    warning {w}")
        n_err += len(errs)
        n_warn += len(warns)
        if norm:
            records.append(norm)
    print(f"\n{len(records)} of {len(rows)} row(s) valid, {n_err} error(s), {n_warn} warning(s)")
    if n_err:
        print("Nothing was imported. Fix the rows above and run again.")
        await db.close()
        sys.exit(1)

    # assign ids to new anchors
    nums = {"N": 0, "L": 0}
    for i in existing_ids:
        m = ID_RE.match(i)
        if m:
            nums[m.group(1)] = max(nums[m.group(1)], int(m.group(2)))
    for r in records:
        if not r["id"]:
            p = PREFIX[r["domain_id"]]
            nums[p] += 1
            r["id"] = f"ANC-{p}-{nums[p]:03d}"
            r["new"] = True
        else:
            r["new"] = r["id"] not in existing_ids

    affected = {c for r in records for c in r["primary"] + r["secondary"]}
    # an UPDATE can also drop skills the anchor used to list: include those too
    old_tags = await db.fetch(
        "SELECT primary_competency_ids AS p, COALESCE(secondary_competency_ids, '{}') AS s "
        "FROM anchor_activities WHERE id = ANY($1::text[])", [r["id"] for r in records if not r["new"]])
    for row in old_tags:
        affected |= {c for c in list(row["p"]) + list(row["s"]) if c in comps}
    before = await match_snapshot(db, affected, comps)

    after, blocked = {}, False
    try:
        async with db.transaction():
            await db.execute("ALTER TABLE anchor_activities ADD COLUMN IF NOT EXISTS validated_by TEXT")
            await db.execute("ALTER TABLE anchor_activities ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ")
            for r in records:
                await db.execute(UPSERT, r["id"], r["title_en"], r["title_hi"], r["description_en"], r["template_body"],
                                 r["primary"], r["secondary"], r["domain_id"], r["grades"], r["duration"], r["theme"],
                                 r["setting"], r["requires_print"], bool(r["tlm_ids"]), r["tlm_ids"],
                                 r["source"], r["validated_by"])
            await db.execute(SEARCH, [r["id"] for r in records])
            after = await match_snapshot(db, affected, comps)
            if args.apply and classify(before, after, affected)[2] and not args.allow_regressions:
                raise _Blocked()
            if not args.apply:
                raise _DryRun()
    except _DryRun:
        pass
    except _Blocked:
        blocked = True

    print("\nWhat the import does:")
    for r in records:
        print(f"  {'ADD   ' if r['new'] else 'UPDATE'} {r['id']}  {r['title_en']}  "
              f"[{', '.join(ac.GRADE_LABEL[g] for g in r['grades'])}; main skills: {', '.join(r['primary'])}]")
    better, swapped, worse = classify(before, after, affected)
    kept = [c for c in affected if before[c][0] == "exact" and after[c][0] == "exact"]
    print(f"\nEffect on anchor matching ({len(better) + len(swapped) + len(worse)} of {len(affected)} tagged skills change):")

    def show(title, ids):
        if ids:
            print(f"  {title} ({len(ids)}):")
            for c in ids:
                b, a = before[c], after[c]
                print(f"    {c:<7} {comps[c][2][:42]:<43} {b[0]:>10} ({b[1]})  ->  {a[0]} ({a[1]})")
    show("GAIN a better match", better)
    show("Now served by a DIFFERENT anchor of the same quality (the old anchor is no longer used for this skill)", swapped)
    show("WARNING: get a WORSE match", worse)
    if not (better or swapped or worse):
        print("  (no skill gets a different anchor)")
    had_exact = [c for c in affected if before[c][0] == "exact"]
    print(f"  Skills that already had an exact match and still do: {len(kept)} of {len(had_exact)}")
    print()
    if blocked:
        print(f"NOT SAVED: this import would make {len(worse)} skill(s) lose a better match than they have today (listed above).")
        print("  Fix the rows, or add --allow-regressions if you really mean it.")
        await db.close()
        sys.exit(1)
    if worse and not args.apply:
        print(f"NOTE: --apply would be refused because {len(worse)} skill(s) get a worse match. Add --allow-regressions to override.\n")
    if args.apply:
        # write the assigned IDs back, so re-sending the corrected file UPDATES these anchors
        # instead of adding duplicates
        wb = load_workbook(args.file)
        ws = wb[ac.SHEET_ANCHORS]
        id_col = ac.col_index("anchor_id")
        for r in records:
            ws.cell(row=r["row"], column=id_col, value=r["id"])
        out = Path(args.file).with_name(Path(args.file).stem + "_imported.xlsx")
        wb.save(out)
        print(f"DONE: saved to the database.")
        print(f"  A copy with the assigned Anchor IDs filled in: {out}")
        print(f"  Use that copy for any corrections (IDs present = update, not duplicate).")
        print(f"  Re-run build_anchor_template.py to refresh the coverage sheet.")
        print(f"  Run export_anchors.py to write these anchors into db/seeds/content, so setup.sh recreates them.")
    else:
        print("DRY RUN: nothing was saved. Add --apply to save.")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
