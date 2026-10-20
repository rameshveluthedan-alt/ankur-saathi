"""
Names must never reach the AI, and names the AI reads off a photo must not be kept.

Registers a scratch class in which every child has a recognisable CANARY name, runs a photo through the real analysis code
with a stand-in for the AI, and checks:
  1. the request sent to the AI does not contain any canary name;
  2. when the AI's reply repeats a name (as it could after reading a notebook page), the stored evidence does not keep it;
  3. the officer (MLO) report has no names, while the teacher's own class report does;
  4. the teacher's screens can still get the names.

    python backend/tests/test_names_never_reach_ai.py --env-file backend/.env

Needs the database with db/schema/07_register.sql and 08_child_names.sql loaded. It cleans up after itself.
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import argparse
import asyncio
import io
import json
import os
import sys
import uuid
from datetime import date
from types import SimpleNamespace

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path[:0] = [os.path.join(ROOT, "backend"), os.path.join(ROOT, "prompts"), os.path.join(ROOT, "scripts")]
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")

import anchor_common as ac
from PIL import Image
from app.services import progress_service, register_service as rs, review_service, names_service

CANARY = "ZQXCANARY"


async def main():
    ap = argparse.ArgumentParser()
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    tag = uuid.uuid4().hex[:6]
    phone_hash, school = f"hash_canary_{tag}", f"CANARY-{tag}".upper()
    teacher_id = None
    failures = []
    try:
        me = await rs.register_teacher(db, phone_hash, school, ["grade_1", "grade_2"])
        teacher_id = me["teacher_id"]
        rows = [{"row": i + 2, "grade": "grade_1" if i < 6 else "grade_2", "roll": str(i % 6 + 1), "name": f"{CANARY}{i} Kumar", "numeracy": "progressor", "literacy": "progressor"} for i in range(10)]
        res = await rs.commit_register(db, teacher_id, rows, "canary.csv")
        assert res["added"] == 10 and res["names_saved"] == 10, res
        names = await names_service.names_for_teacher(db, teacher_id)
        assert len(names) == 10 and all(CANARY in n for n in names.values()), names
        roll = sorted(names)[0]                                  # the first child's class number (101 in a multi-grade class)

        problems = [{"number": 1, "problem_hi": "12 + 13", "answer": "25"}, {"number": 2, "problem_hi": "20 + 21", "answer": "41"}]
        plan = {"worksheets": {"progressor": {"required_count": 2, "problems": problems}}}
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
                            VALUES ($1, $2, 'numeracy', 'N2.3.2', $3::jsonb, '{}'::jsonb, '{}'::jsonb)""", teacher_id, date.today(), json.dumps(plan))

        sent = []
        reply = [{"roll_number": roll, "roll_number_confidence": "high",
                  "problems": [{"number": 1, "extracted_answer": "25", "correct_answer": "25", "is_correct": True, "confidence": "high"},
                               {"number": 2, "extracted_answer": "40", "correct_answer": "41", "is_correct": False, "confidence": "high",
                                "diagnosis_reasoning": f"{names[roll]} wrote 40; the name at the top of the page, {names[roll].split()[0]}, is not a roll number"}],
                  "summary": {"needs_verification": [], "detected_misconceptions": [], "notes": f"page signed {names[roll]}"}}]

        class FakeMessages:
            async def create(self, **kw):
                sent.append(json.dumps(kw, default=str, ensure_ascii=False))
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(reply, ensure_ascii=False))], stop_reason="end_turn",
                                       usage=SimpleNamespace(input_tokens=1, output_tokens=1))

        class FakeClient:
            def __init__(self, **kw):
                self.messages = FakeMessages()

        real = review_service.anthropic.AsyncAnthropic
        review_service.anthropic.AsyncAnthropic = FakeClient
        try:
            buf = io.BytesIO()
            Image.new("RGB", (120, 90), "white").save(buf, "JPEG")
            await review_service.analyse_worksheet_photos(db, teacher_id, date.today(), "numeracy", "N2.3.2", "progressor", [buf.getvalue()], None)
        finally:
            review_service.anthropic.AsyncAnthropic = real

        if not sent:
            failures.append("the AI was never called, so the test checked nothing")
        for s in sent:
            if CANARY in s or "Kumar" in s:
                failures.append("a child's name was in the request sent to the AI")
        stored = await db.fetchval("SELECT string_agg(evidence_data::text, ' ') FROM assessment_evidence e JOIN children c ON c.id = e.child_id WHERE c.teacher_id = $1", teacher_id) or ""
        if CANARY in stored or "Kumar" in stored:
            failures.append("a name the AI repeated was kept in the stored evidence")
        if names_service.PLACEHOLDER not in stored:
            failures.append("the scrub did not run (no placeholder in the stored evidence)")
        mlo = await progress_service.export_mlo_report_csv(db, teacher_id)
        if CANARY in mlo or "Kumar" in mlo:
            failures.append("the officer (MLO) report contains a name")
        klass = await progress_service.export_class_report_csv(db, teacher_id)
        if CANARY not in klass:
            failures.append("the teacher's own class report is missing the names")
        if names.get(roll) is None:
            failures.append("the teacher's screens cannot get the names")
        # the sheet a child writes on has no name field (a photo of it goes to the AI)
        tpl = open(os.path.join(ROOT, "backend", "app", "templates", "worksheet.html"), encoding="utf-8").read()
        if "नाम" in tpl:
            failures.append("the worksheet template has a name field")
        print(f"  requests to the AI: {len(sent)} | canary names set: {len(names)} | stored evidence scrubbed: {names_service.PLACEHOLDER in stored}")
    finally:
        if teacher_id:
            await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
            await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = $1)", teacher_id)
            await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
            await db.execute("DELETE FROM teachers WHERE id = $1", teacher_id)
            await db.execute("DELETE FROM schools WHERE school_code = $1", school)
        await db.close()
    if failures:
        print("FAILED")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("OK: no name reached the AI, names the AI repeated were not kept, the officer report has no names")


if __name__ == "__main__":
    asyncio.run(main())
