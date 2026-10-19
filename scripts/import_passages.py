"""
Ankur Saathi — import openly licensed reading passages (for example StoryWeaver stories) into the content bank.

    python scripts/import_passages.py docs/passages_manifest.csv            # dry run: checks everything, writes nothing
    python scripts/import_passages.py docs/passages_manifest.csv --apply    # imports (INACTIVE until a person has reviewed)
    python scripts/import_passages.py docs/passages_manifest.csv --apply --activate   # imports and makes usable in plans

How it works
  1. For each story you want, open it on StoryWeaver, check the licence shown on the page, and save its Hindi text
     into a .txt file next to the manifest (the text is the story's own; the licence lets you do this with credit).
  2. Fill one row per story in the manifest (see docs/passages_manifest_template.csv).
  3. Run a dry run, fix what it reports, then --apply.

What it refuses (each row is reported separately, and nothing is written for a row with a problem)
  - a licence that is not CC BY 4.0, CC BY-SA 4.0 or CC0 (Non-commercial and No-derivatives are refused by name)
  - a source address that is not on the allowed list, or a missing author, publisher or title
  - text that is not mainly Devanagari, or an unknown competency ID, or a grade/difficulty that does not exist
  - an ID that is already in the bank
Imported passages are stored as source='storyweaver', review_status='external_unreviewed', and the credit line
the licence requires is built for you and printed under the passage on the worksheet.

Requires: pip install asyncpg
"""

import argparse
import asyncio
import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anchor_common as ac

ALLOWED_HOSTS = {"storyweaver.org.in", "www.storyweaver.org.in", "prathambooks.org", "www.prathambooks.org"}
LICENCES = {"cc by 4.0": "CC BY 4.0", "cc-by-4.0": "CC BY 4.0", "cc by": "CC BY 4.0",
            "cc by-sa 4.0": "CC BY-SA 4.0", "cc-by-sa-4.0": "CC BY-SA 4.0", "cc by-sa": "CC BY-SA 4.0",
            "cc0": "CC0", "cc0 1.0": "CC0"}
GRADES = {"grade_1", "grade_2", "grade_3"}
DIFFICULTIES = {"easy", "medium", "hard"}
WORD_RANGE = {"grade_1": (20, 60), "grade_2": (40, 100), "grade_3": (60, 140)}   # a sanity range, a warning only
REQUIRED = ["story_id", "title_hi", "author", "publisher", "source_url", "license", "original_level",
            "target_grade", "difficulty", "fluency_competency_id", "text_file"]
SENTENCE_END = "।?!."


def devanagari_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(1 for c in letters if "\u0900" <= c <= "\u097F") / len(letters) if letters else 0.0


def excerpt(text: str, n_words: int) -> str:
    """The first n words, finished at the end of a sentence when one is within 25% more words."""
    words = text.split()
    if len(words) <= n_words:
        return text
    limit = int(n_words * 1.25)
    for i in range(n_words, min(limit, len(words)) + 1):
        if words[i - 1][-1] in SENTENCE_END:
            return " ".join(words[:i])
    return " ".join(words[:n_words])


def check_row(row: dict, base: Path, comp_ids: set, existing: set, prefix: str) -> tuple[dict | None, list[str], list[str]]:
    errors, warnings = [], []
    g = lambda k: (row.get(k) or "").strip()
    for k in REQUIRED:
        if not g(k):
            errors.append(f"'{k}' is empty")
    if errors:
        return None, errors, warnings
    if g("story_id").upper().startswith("EXAMPLE"):
        return None, ["this is the example row from the template: delete it"], warnings
    if not re.fullmatch(r"[A-Za-z0-9_-]+", g("story_id")):
        errors.append("story_id may only contain letters, digits, - and _")
    pid = f"{prefix}-{g('story_id')}"
    if pid in existing:
        errors.append(f"{pid} is already in the content bank")

    lic_raw = g("license")
    lic = LICENCES.get(lic_raw.lower())
    if not lic:
        low = lic_raw.lower()
        why = ("non-commercial licences are not allowed: they would block use in a product" if "nc" in low.replace("-", " ").split()
               else "no-derivatives licences are not allowed: we have to adapt the text" if "nd" in low.replace("-", " ").split()
               else "only CC BY 4.0, CC BY-SA 4.0 and CC0 are accepted")
        errors.append(f"licence '{lic_raw}' refused ({why})")
    host = (urlparse(g("source_url")).hostname or "").lower()
    if urlparse(g("source_url")).scheme != "https" or host not in ALLOWED_HOSTS:
        errors.append(f"source_url must be an https address on {', '.join(sorted(ALLOWED_HOSTS - {'www.storyweaver.org.in', 'www.prathambooks.org'}))}")

    try:
        level = int(g("original_level"))
        if not 1 <= level <= 4:
            raise ValueError
    except ValueError:
        errors.append("original_level must be 1 to 4 (StoryWeaver's own level)")
        level = None
    if g("target_grade") not in GRADES:
        errors.append(f"target_grade must be one of {sorted(GRADES)}")
    if g("difficulty") not in DIFFICULTIES:
        errors.append(f"difficulty must be one of {sorted(DIFFICULTIES)}")
    flu = g("fluency_competency_id")
    comp = [c.strip() for c in g("comprehension_competency_ids").replace(",", ";").split(";") if c.strip()]
    for c in [flu] + comp:
        if c not in comp_ids:
            errors.append(f"competency '{c}' does not exist (literacy skills only: L...)")

    path = base / g("text_file")
    text = ""
    if not path.is_file():
        errors.append(f"text file not found: {path}")
    else:
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8")).strip()
        if devanagari_ratio(text) < 0.6:
            errors.append(f"the text is only {devanagari_ratio(text):.0%} Devanagari: is this the Hindi version?")
        n = g("excerpt_words")
        if n:
            try:
                text = excerpt(text, int(n))
            except ValueError:
                errors.append("excerpt_words must be a number")
    if errors:
        return None, errors, warnings

    wc = len(text.split())
    lo, hi = WORD_RANGE[g("target_grade")]
    if not lo <= wc <= hi:
        warnings.append(f"{wc} words is outside the usual {lo}-{hi} for {g('target_grade')}: use excerpt_words to shorten it")
    illus = g("illustrator")
    credit = (f"“{g('title_hi')}” by {g('author')}" + (f", illustrated by {illus}" if illus else "") +
              f". {g('publisher')}. Via StoryWeaver ({host.removeprefix('www.')}), {lic}." + (" Adapted: shortened." if g("excerpt_words") else ""))
    return ({"id": pid, "title_hi": g("title_hi"), "passage_hi": text, "word_count": wc, "target_grade": g("target_grade"),
             "difficulty": g("difficulty"), "fluency": flu, "comp": comp, "theme": g("theme") or None,
             "setting": g("setting") or "rural", "genre": g("genre") or "narrative", "source_url": g("source_url"),
             "license": lic, "attribution": credit, "author": g("author"), "level": level}, errors, warnings)


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", help="CSV file, one row per story")
    ap.add_argument("--apply", action="store_true", help="write to the database (default: dry run)")
    ap.add_argument("--activate", action="store_true", help="make imported passages usable in plans (default: inactive until reviewed)")
    ap.add_argument("--id-prefix", default="SW")
    ac.add_db_args(ap)
    args = ap.parse_args()

    manifest = Path(args.manifest)
    with manifest.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit("The manifest has no rows.")
    db = await ac.connect(args)
    comp_ids = {r["id"] for r in await db.fetch("SELECT id FROM competencies WHERE id LIKE 'L%'")}
    existing = {r["id"] for r in await db.fetch("SELECT id FROM reading_passages")}

    good, bad = [], 0
    for n, row in enumerate(rows, start=2):
        rec, errors, warnings = check_row(row, manifest.parent, comp_ids, existing, args.id_prefix)
        label = f"row {n} ({(row.get('story_id') or '?').strip()})"
        if errors:
            bad += 1
            print(f"  REFUSED  {label}")
            for e in errors:
                print(f"           - {e}")
            continue
        existing.add(rec["id"])
        good.append(rec)
        print(f"  ok       {label}: {rec['id']}, {rec['word_count']} words, {rec['license']}")
        for w in warnings:
            print(f"           ! {w}")

    print(f"\n{len(good)} ready, {bad} refused.")
    if not args.apply:
        print("Dry run: nothing was written. Add --apply to import.")
    elif good:
        async with db.transaction():
            for r in good:
                await db.execute("""
                    INSERT INTO reading_passages
                        (id, title_hi, passage_hi, word_count, target_grade, difficulty, decoding_features, theme, setting, genre,
                         fluency_competency_id, comprehension_competency_ids, source, source_url, license, attribution, author,
                         original_level, review_status, is_active)
                    VALUES ($1,$2,$3,$4,$5,$6,'{}',$7,$8,$9,$10,$11,'storyweaver',$12,$13,$14,$15,$16,'external_unreviewed',$17)
                """, r["id"], r["title_hi"], r["passage_hi"], r["word_count"], r["target_grade"], r["difficulty"], r["theme"],
                    r["setting"], r["genre"], r["fluency"], r["comp"] or None, r["source_url"], r["license"], r["attribution"],
                    r["author"], r["level"], args.activate)
        state = "ACTIVE and will be used in plans" if args.activate else "INACTIVE: have the Hindi level checked, then re-run with --activate or set is_active = true"
        print(f"Imported {len(good)} passages, {state}.")
    await db.close()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    asyncio.run(main())
