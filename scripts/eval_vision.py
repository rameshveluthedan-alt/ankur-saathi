"""
Ankur Saathi — score the photo analysis on real worksheet photos.

    python scripts/eval_vision.py --plan plan_n232.json --competency N2.3.2 --level progressor \
        --photos photos/numeracy --truth truth_numeracy.csv
    python scripts/eval_vision.py --plan plan_l261_1.json --competency L2.6.1 --level progressor --domain r1_literacy \
        --photos photos/literacy --truth truth_literacy.csv
    python scripts/eval_vision.py ... --stub        # a dry run with a FAKE model: checks the scoring itself, costs nothing

It uses the SAME prompt builder, photo shrinking and model call that the app uses (review_service.call_vision), so the numbers
describe what a juror will get. It spends YOUR Anthropic credits (about 3 to 6 cents a photo). Folder of photos + one truth file in,
a scored report out. See docs/VISION_PHOTO_TEST.md for how to prepare the sheets and the truth file.

Truth file columns (see docs/vision_truth_template.csv):
    photo_file, roll_number, problem_number, child_wrote, judged, carry_digit_visible, expected_pattern, notes
  child_wrote          exactly what the child wrote, even if wrong; empty if left blank
  judged               what a teacher would say: correct | partial | incorrect | blank (numeric answers: filled in for you if empty)
  carry_digit_visible  yes | no | na          (numeracy only)
  expected_pattern     a mistake id such as N2.3.2-M1, or "slip" for a careless error, or empty

Requires: pip install pillow asyncpg   (asyncpg only if you want the misconception list from the database)
"""

import argparse
import asyncio
import csv
import difflib
import io
import json
import os
import random
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


# ── comparing what the child wrote with what the AI read ────────────────────

def norm(text) -> str:
    """Lenient: ignore spaces, punctuation, zero-width marks and case; keep letters, matras and digits."""
    t = unicodedata.normalize("NFC", str(text or ""))
    t = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", t)
    return "".join(ch for ch in t if unicodedata.category(ch)[0] in ("L", "M", "N")).lower()


def is_numeric(s) -> bool:
    return bool(re.fullmatch(r"[\d\s,.]+", str(s or "").strip())) and bool(str(s).strip())


def similarity(a, b) -> float:
    a, b = norm(a), norm(b)
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def truth_correct(row: dict, key: str) -> str:
    """The teacher's judgement for a row: correct | partial | incorrect | blank."""
    j = (row.get("judged") or "").strip().lower()
    if j in ("correct", "partial", "incorrect", "blank"):
        return j
    wrote = (row.get("child_wrote") or "").strip()
    if not wrote:
        return "blank"
    return "correct" if is_numeric(key) and norm(wrote) == norm(key) else ("incorrect" if is_numeric(key) else "")


# ── a fake model, so the scoring itself can be tested for free ──────────────

def install_stub(review_service, truth_by_photo, state, seed=7):
    rng = random.Random(seed)
    class FM:
        async def create(self, **kw):
            rows = truth_by_photo[state["photo"]]
            probs = []
            for r in rows:
                wrote = r["child_wrote"].strip()
                read = wrote
                if wrote and rng.random() < 0.08:                      # the fake model misreads 8% of answers
                    read = wrote[:-1] if len(wrote) > 1 else "?"
                j = truth_correct(r, state["key"][int(r["problem_number"])])
                pred = {"correct": True, "incorrect": False, "partial": False, "blank": False}.get(j)
                if pred is not None and rng.random() < 0.06:           # and flips 6% of judgements
                    pred = not pred
                probs.append({"number": int(r["problem_number"]), "extracted_answer": read or None, "correct_answer": state["key"][int(r["problem_number"])],
                              "is_correct": pred, "partially_correct": j == "partial", "carry_written": {"yes": True, "no": False}.get((r.get("carry_digit_visible") or "").lower()),
                              "confidence": "high"})
            body = [{"roll_number": int(rows[0]["roll_number"]), "roll_number_confidence": "high", "problems": probs,
                     "summary": {"total_problems": len(probs), "correct": sum(1 for p in probs if p["is_correct"]), "overall_status": "partially_achieved",
                                 "detected_misconceptions": [], "needs_verification": []}}]
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(body, ensure_ascii=False))], stop_reason="end_turn",
                                   usage=SimpleNamespace(input_tokens=5200, output_tokens=1400))
    class FC:
        def __init__(self, **kw): self.messages = FM()
    review_service.anthropic.AsyncAnthropic = FC


def client_compress(data: bytes, max_side=1600, quality=80) -> bytes:
    """What the app does on the phone before upload."""
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    if max(img.size) > max_side:
        s = max_side / max(img.size)
        img = img.resize((round(img.width * s), round(img.height * s)))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=quality)
    return buf.getvalue() if buf.tell() < len(data) else data


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True, help="an exported plan JSON (for the worksheet's problems and answer key)")
    ap.add_argument("--competency", required=True, help="the skill this sheet is for, e.g. N2.3.2")
    ap.add_argument("--level", default="progressor", choices=["beginner", "progressor", "proficient"])
    ap.add_argument("--domain", choices=["numeracy", "r1_literacy"], help="default: guessed from the skill id")
    ap.add_argument("--photos", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--out", default=str(ROOT / "docs" / "vision"))
    ap.add_argument("--no-db", action="store_true", help="do not read the misconception list from the database")
    ap.add_argument("--no-client-compress", action="store_true", help="send the original photos (the server still shrinks them)")
    ap.add_argument("--price-in", type=float, default=2.0)
    ap.add_argument("--price-out", type=float, default=10.0)
    ap.add_argument("--stub", action="store_true", help="a FAKE model: tests the scoring, costs nothing")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    domain = args.domain or ("numeracy" if args.competency.startswith("N") else "r1_literacy")

    os.chdir(BACKEND)
    sys.path[:0] = [str(BACKEND), str(ROOT / "prompts")]
    if args.stub:
        os.environ.setdefault("ANTHROPIC_API_KEY", "stub")
    from app.core.config import get_settings
    from app.services import review_service
    from vision_analysis import build_vision_prompt
    if not args.stub and not get_settings().anthropic_api_key:
        sys.exit("ANTHROPIC_API_KEY is not set in backend/.env. Use --stub for a dry run.")

    plan = json.load(open(args.plan, encoding="utf-8"))
    ws = plan["worksheets"][args.level]
    problems, required = ws["problems"], ws.get("required_count")
    key = {int(p["number"]): str(p.get("answer", "")) for p in problems}

    truth = defaultdict(list)
    for r in csv.DictReader(open(args.truth, encoding="utf-8-sig")):
        if r["photo_file"].upper().startswith("EXAMPLE"):
            continue
        truth[r["photo_file"]].append(r)
    photos_dir = Path(args.photos)
    files = sorted(f for f in photos_dir.iterdir() if f.suffix.lower() in IMG_EXT and f.name in truth)
    missing = sorted(set(truth) - {f.name for f in files})
    if missing:
        print(f"Truth rows exist for photos that are not in {photos_dir}: {missing}")
    if not files:
        sys.exit("No photo matches a row in the truth file.")
    rolls = sorted({int(r["roll_number"]) for rows in truth.values() for r in rows})

    # misconceptions + competency name from the database (optional)
    misconceptions, name_hi = [], args.competency
    if not args.no_db:
        try:
            import asyncpg
            conn = await asyncpg.connect(get_settings().database_url)
            misconceptions = [dict(r) for r in await conn.fetch(
                "SELECT id, name_en, name_hi, error_pattern, diagnostic_indicator, example_correct, example_incorrect, severity, frequency FROM misconceptions WHERE competency_id=$1 ORDER BY sort_order", args.competency)]
            name_hi = (await conn.fetchval("SELECT name_hi FROM competencies WHERE id=$1", args.competency)) or args.competency
            await conn.close()
        except Exception as e:
            print(f"(no database: scoring without the misconception list: {type(e).__name__})")

    state = {"photo": None, "key": key}
    if args.stub:
        install_stub(review_service, truth, state)
    elif not args.yes:
        print(f"{len(files)} photo(s) will be sent to the real model: about ${len(files) * 0.05:.2f} of your credits.")
        if input("Type yes to start: ").strip().lower() != "yes":
            sys.exit("Cancelled.")

    prompt = build_vision_prompt(worksheet_level=args.level, competency_id=args.competency, competency_name_hi=name_hi, problems=problems,
                                 misconceptions=misconceptions, group_roll_numbers=rolls, photo_count=1, required_count=required, domain_id=domain)
    rows_out, photo_log = [], []
    for f in files:
        state["photo"] = f.name
        data = f.read_bytes()
        if not args.no_client_compress:
            data = client_compress(data)
        t0 = time.time()
        try:
            results, usage = await review_service.call_vision([data], prompt)
            err = ""
        except Exception as e:
            results, usage, err = [], {"input_tokens": 0, "output_tokens": 0}, f"{type(e).__name__}: {e}"[:200]
        secs = round(time.time() - t0, 1)
        t_rows = truth[f.name]
        want_roll = int(t_rows[0]["roll_number"])
        child = next((c for c in results if str(c.get("roll_number")) == str(want_roll)), results[0] if results else None)
        pred_roll = child.get("roll_number") if child else None
        photo_log.append({"photo": f.name, "truth_roll": want_roll, "pred_roll": pred_roll, "roll_ok": str(pred_roll) == str(want_roll), "seconds": secs,
                          "in": usage["input_tokens"], "out": usage["output_tokens"], "error": err, "children_found": len(results)})
        by_n = {int(p.get("number", 0)): p for p in (child or {}).get("problems", [])}
        diagnosed = sorted({p.get("diagnosed_misconception") for p in by_n.values() if p.get("diagnosed_misconception")})
        for r in t_rows:
            n = int(r["problem_number"]); p = by_n.get(n, {})
            wrote, read = (r.get("child_wrote") or "").strip(), p.get("extracted_answer")
            read = "" if read is None else str(read)
            tj = truth_correct(r, key.get(n, ""))
            pj = p.get("is_correct")
            rows_out.append({"photo": f.name, "roll": want_roll, "problem": n, "kind": "numeric" if is_numeric(key.get(n, "")) else "text",
                             "truth_wrote": wrote, "ai_read": read, "exact": norm(wrote) == norm(read), "similarity": round(similarity(wrote, read), 3),
                             "truth_judged": tj, "ai_is_correct": "" if pj is None else pj, "ai_partial": bool(p.get("partially_correct")),
                             "truth_carry": (r.get("carry_digit_visible") or "").lower(), "ai_carry": p.get("carry_written"),
                             "expected_pattern": (r.get("expected_pattern") or "").strip(), "ai_diagnosed": ";".join(diagnosed), "confidence": p.get("confidence", ""),
                             "found_by_ai": bool(p)})

    # ── scoring ──
    def pct(a, b): return f"{100 * a / b:.0f}%" if b else "n/a"
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    with (out / "eval_problems.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)
    md = [f"# Photo analysis: scored on real worksheets", "", f"{len(files)} photos, {len(rows_out)} answers. Skill {args.competency}, {args.level} sheet, {domain}. "
          f"Model call: the production code path{' (FAKE MODEL: this is a dry run)' if args.stub else ''}.", ""]
    roll_ok = sum(1 for p in photo_log if p["roll_ok"]); errs = [p for p in photo_log if p["error"]]
    md += ["## Roll number and failures", "", f"- Roll number read correctly: {roll_ok} of {len(photo_log)} ({pct(roll_ok, len(photo_log))})",
           f"- Photos that failed (API or format error): {len(errs)}", ""]
    for kind in ("numeric", "text"):
        k = [r for r in rows_out if r["kind"] == kind]
        if not k:
            continue
        ex = sum(r["exact"] for r in k); close = sum(1 for r in k if r["similarity"] >= 0.8)
        judged = [r for r in k if r["truth_judged"] in ("correct", "incorrect", "partial", "blank")]
        agree = sum(1 for r in judged if (r["ai_is_correct"] is True) == (r["truth_judged"] == "correct") and r["ai_is_correct"] != "")
        fa = sum(1 for r in judged if r["ai_is_correct"] is True and r["truth_judged"] != "correct")
        frj = sum(1 for r in judged if r["ai_is_correct"] is False and r["truth_judged"] == "correct")
        unread = sum(1 for r in judged if r["ai_is_correct"] == "")
        md += [f"## {kind.capitalize()} answers ({len(k)})", "",
               f"- Read exactly as written: {ex} ({pct(ex, len(k))}); close enough (similarity 0.8 or more): {close} ({pct(close, len(k))}); mean similarity {sum(r['similarity'] for r in k) / len(k):.2f}",
               f"- Right/wrong judged the same as the teacher: {agree} of {len(judged)} ({pct(agree, len(judged))})",
               f"- Wrongly accepted (AI said correct, teacher did not): {fa}; wrongly rejected (AI said wrong, teacher said correct): {frj}; unreadable: {unread}", ""]
        part = [r for r in judged if r["truth_judged"] == "partial"]
        if part:
            md.append(f"- Partly-correct answers flagged as partial: {sum(r['ai_partial'] for r in part)} of {len(part)}\n")
    carry = [r for r in rows_out if r["truth_carry"] in ("yes", "no")]
    if carry:
        ok = sum(1 for r in carry if (r["ai_carry"] is True) == (r["truth_carry"] == "yes") and r["ai_carry"] is not None)
        md += ["## Carry digit (numeracy)", "", f"- Seen or not seen correctly: {ok} of {len(carry)} ({pct(ok, len(carry))}); not reported: {sum(1 for r in carry if r['ai_carry'] is None)}", ""]
    pat = {r["photo"]: r["expected_pattern"] for r in rows_out if r["expected_pattern"]}
    if pat:
        diag = {r["photo"]: r["ai_diagnosed"] for r in rows_out}
        right = sum(1 for ph, ex in pat.items() if (ex != "slip" and ex in diag[ph].split(";")) or (ex == "slip" and not diag[ph]))
        md += ["## Mistake patterns", "", f"- Expected pattern named correctly (or no pattern for a slip): {right} of {len(pat)} photos ({pct(right, len(pat))})", ""]
    tin, tout = sum(p["in"] for p in photo_log), sum(p["out"] for p in photo_log)
    cost = tin * args.price_in / 1e6 + tout * args.price_out / 1e6
    md += ["## Cost and time", "", f"- Average {sum(p['seconds'] for p in photo_log) / len(photo_log):.1f} s and about ${cost / len(photo_log):.3f} per photo (estimate at ${args.price_in}/${args.price_out} per million tokens)", ""]
    worst = sorted((r for r in rows_out if not r["exact"]), key=lambda r: r["similarity"])[:12]
    if worst:
        md += ["## Worst misreadings", "", "| photo | problem | child wrote | AI read | similarity |", "| --- | --- | --- | --- | ---: |"]
        md += [f"| {r['photo']} | {r['problem']} | {r['truth_wrote'] or '(blank)'} | {r['ai_read'] or '(nothing)'} | {r['similarity']} |" for r in worst] + [""]
    if errs:
        md += ["## Failed photos", ""] + [f"- {p['photo']}: {p['error']}" for p in errs] + [""]
    (out / "eval_summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\nWrote {out / 'eval_summary.md'} and {out / 'eval_problems.csv'}")


if __name__ == "__main__":
    asyncio.run(main())
