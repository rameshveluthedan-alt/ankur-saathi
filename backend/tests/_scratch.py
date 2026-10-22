"""Shared helper for the database tests: a scratch teacher with a small class, removed afterwards."""
import os
import sys
import uuid

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path[:0] = [os.path.join(ROOT, "backend"), os.path.join(ROOT, "prompts"), os.path.join(ROOT, "scripts")]
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.setdefault("CFU_TOPUP", "0")          # tests count model calls and metered rows exactly, so the CFU top-up call is OFF unless a test turns it on (test_cfu.py does)

import anchor_common as ac
from app.services import register_service as rs


async def connect():
    import argparse
    ap = argparse.ArgumentParser()
    ac.add_db_args(ap)
    return await ac.connect(ap.parse_args())


async def make_class(db, levels, grade="grade_1"):
    """levels: {roll: (numeracy_level, literacy_level)}. Returns (teacher_id, school_code)."""
    tag = uuid.uuid4().hex[:6]
    school = f"TST-{tag}".upper()
    me = await rs.register_teacher(db, f"hash_tst_{tag}", school, [grade])
    rows = [{"row": i + 2, "grade": grade, "roll": str(r), "name": "", "numeracy": n, "literacy": l} for i, (r, (n, l)) in enumerate(sorted(levels.items()))]
    await rs.commit_register(db, me["teacher_id"], rows, "scratch.csv")
    return me["teacher_id"], school


async def remove_class(db, teacher_id, school):
    # a scratch school's metering rows would otherwise stay behind with no teacher and count towards the real daily totals
    try:
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
    except Exception:
        pass
    if teacher_id:
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = $1)", teacher_id)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM teachers WHERE id = $1", teacher_id)
    await db.execute("DELETE FROM schools WHERE school_code = $1", school)
