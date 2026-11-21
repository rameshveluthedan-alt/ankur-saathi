"""
Prompt v2, step 7: the real-model check. 4 skill shapes x session lengths, through the app's own pipeline (plan_service.generate_dainik_yojana),
on a scratch class in the LAB database (removed afterwards). Every request and reply is kept under this folder; nothing is written to the repo.
Stops when the metered spend for the scratch school reaches --max-usd.

    cd C:\\dev\\Ankur-Saathi-lab\\backend
    AI_ENABLED=true AI_CREDIT_EXPIRES=2026-11-30 venv/Scripts/python.exe C:/dev/ankur-scratch/v2_run/run_v2_matrix.py --env-file .env --minutes 60,90
"""
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
import argparse
import asyncio
import contextlib
import io
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

LAB = Path(r"C:\dev\Ankur-Saathi-lab")
sys.path[:0] = [str(LAB / "backend" / "tests"), str(LAB / "backend"), str(LAB / "prompts"), str(LAB / "scripts")]
import os as _os
OUT = Path(__file__).resolve().parent / _os.environ.get("V2_OUT", "out")

ap = argparse.ArgumentParser()
ap.add_argument("--minutes", default="60,90")
ap.add_argument("--skills", default="N2.3.2,L2.7.2,L2.5.1,N0.1.1")
ap.add_argument("--max-usd", type=float, default=5.0)
ap.add_argument("--env-file")
args, rest = ap.parse_known_args()
sys.argv = [sys.argv[0]] + (["--env-file", args.env_file] if args.env_file else []) + rest

import _scratch            # noqa: E402  (sets SKILL_BRIDGES / SEMANTIC_RETRIEVAL off, as the tests do)
os.environ["CFU_TOPUP"] = os.environ.get("CFU_TOPUP_RUN", "1")    # the app's real behaviour: the top-up call is on
import anthropic           # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services import ai_budget, plan_service  # noqa: E402
if os.environ.get("V2_EXAMPLE") == "1":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import example_hook
    example_hook.install(plan_service)
    print("(test hook: a REVIEWED EXAMPLE section is added to the prompt)")

DOMAIN = {"N": "numeracy", "L": "r1_literacy"}
GRADE = {"N0.1.1": "grade_1"}
REAL = anthropic.AsyncAnthropic
CALLS = []


class Capture:
    """The real client, with every request and its usage kept."""
    def __init__(self, **kw):
        self._c = REAL(**kw)
        self.messages = self

    async def create(self, **kw):
        t = time.time()
        r = await self._c.messages.create(**kw)
        u = r.usage
        CALLS.append({"system": kw.get("system"), "user": (kw.get("messages") or [{}])[0].get("content"), "seconds": round(time.time() - t, 1),
                      "usage": {k: getattr(u, k, None) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")},
                      "stop_reason": r.stop_reason})
        return r


async def main():
    s = get_settings()
    assert s.anthropic_api_key and not s.anthropic_api_key.startswith("sk-dummy"), "no real key in this environment"
    OUT.mkdir(exist_ok=True)
    db = await _scratch.connect()
    ai_budget.operator_mode(True)
    classes = {}
    anthropic.AsyncAnthropic = Capture
    day = date(2031, 1, 6)
    try:
        for grade in sorted({GRADE.get(k, "grade_2") for k in args.skills.split(",")}):
            levels = {}
            for r in range(1, 31):
                lv = "beginner" if r <= 8 else ("progressor" if r <= 20 else "proficient")
                levels[r] = (lv, lv)
            classes[grade] = await _scratch.make_class(db, levels, grade=grade)
        for m in [int(x) for x in args.minutes.split(",")]:
            for skill in args.skills.split(","):
                teacher_id, school = classes[GRADE.get(skill, "grade_2")]
                spent = await ai_budget._spent(db, "school_id IN (SELECT id FROM schools WHERE school_code = ANY($1::text[]))", [c[1] for c in classes.values()])
                if spent >= args.max_usd:
                    print(f"STOP: ${spent:.2f} spent, the limit is ${args.max_usd}")
                    return
                n0, t = len(CALLS), time.time()
                buf = io.StringIO()
                err = None
                try:
                    with contextlib.redirect_stdout(buf):
                        reply = await plan_service.generate_dainik_yojana(db, teacher_id, skill, DOMAIN[skill[0]], day, session_minutes=m)
                except Exception as e:
                    err, reply = f"{type(e).__name__}: {e}", None
                row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, day)
                plan = (json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]) if row else None
                name = f"{skill}_{m}"
                (OUT / f"{name}.plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
                (OUT / f"{name}.log.txt").write_text(buf.getvalue(), encoding="utf-8")
                (OUT / f"{name}.calls.json").write_text(json.dumps(CALLS[n0:], ensure_ascii=False, indent=1, default=str), encoding="utf-8")
                (OUT / f"{name}.reply.json").write_text(json.dumps({k: v for k, v in (reply or {}).items() if k != "plan"}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
                us = [c["usage"] for c in CALLS[n0:]]
                print(f"{name}: {round(time.time() - t)} s, {len(us)} call(s), usage {us}, {'ERROR ' + err if err else 'ok'}", flush=True)
                day += timedelta(days=1)
        spent = await ai_budget._spent(db, "school_id IN (SELECT id FROM schools WHERE school_code = ANY($1::text[]))", [c[1] for c in classes.values()])
        print(f"TOTAL metered for the run: ${spent:.3f}")
    finally:
        anthropic.AsyncAnthropic = REAL
        for teacher_id, school in classes.values():
            await _scratch.remove_class(db, teacher_id, school)
        await db.close()


asyncio.run(main())
