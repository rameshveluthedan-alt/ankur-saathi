"""
Load the prompt-v2 test plans (out/*.plan.json) into the LAB database for a person to read on screen: one review teacher per session length and
skill pair, each with a class of 30 (rolls 1-8 Beginners, 9-20 Progressors, 21-30 Proficients: the class the plans were made for), each plan dated
TODAY so the Teach screen shows it. No AI call. Re-run on another day to move the plans to that day (it replaces them).

    cd C:\\dev\\Ankur-Saathi-lab\\backend
    venv/Scripts/python.exe C:/dev/ankur-scratch/v2_run/load_for_review.py --env-file .env
"""
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

LAB = Path(r"C:\dev\Ankur-Saathi-lab")
sys.path[:0] = [str(LAB / "backend" / "tests"), str(LAB / "backend"), str(LAB / "prompts"), str(LAB / "scripts")]
OUT = Path(__file__).resolve().parent.parent      # the plans folder this tool sits in (docs/drafts/prompt_v2_runs); the scratch copy used ./out
import _scratch                                           # noqa: E402
from app.services import auth_service, register_service as rs   # noqa: E402

PIN = "4826"
SCHOOL = "V2REVIEW"
ACCOUNTS = {     # code: (minutes, the two plans: a maths one and a Hindi one)
    "V245NA": (45, ("N2.3.2", "L2.7.2")), "V245NB": (45, ("N0.1.1", "L2.5.1")),
    "V260NA": (60, ("N2.3.2", "L2.7.2")), "V260NB": (60, ("N0.1.1", "L2.5.1")),
    "V290NA": (90, ("N2.3.2", "L2.7.2")), "V290NB": (90, ("N0.1.1", "L2.5.1")),
}


async def main():
    db = await _scratch.connect()
    today = date.today()
    try:
        for code, (m, skills) in ACCOUNTS.items():
            tid = await db.fetchval("SELECT id FROM teachers WHERE phone_hash = $1", code)
            if not tid:
                me = await rs.register_teacher(db, code, SCHOOL, ["grade_2"], pin_hash=auth_service.hash_pin(PIN), enforce_join=False)
                tid = me["teacher_id"]
                rows = [{"row": r + 1, "grade": "grade_2", "roll": str(r), "name": "",
                         "numeracy": lv, "literacy": lv} for r in range(1, 31)
                        for lv in ["beginner" if r <= 8 else ("progressor" if r <= 20 else "proficient")]]
                await rs.commit_register(db, tid, rows, "v2_review.csv")
            for skill in skills:
                plan = json.loads((OUT / f"{skill}_{m}.plan.json").read_text(encoding="utf-8"))
                domain = "numeracy" if skill.startswith("N") else "r1_literacy"
                await db.execute("""
                    INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot, generation_time_ms, claude_model)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, '{}'::jsonb, 0, 'prompt-v2-review')
                    ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET plan_content = EXCLUDED.plan_content, explainability = EXCLUDED.explainability,
                        selected_competency_id = EXCLUDED.selected_competency_id, claude_model = EXCLUDED.claude_model""",
                    tid, today, domain, skill, json.dumps(plan, ensure_ascii=False), json.dumps(plan.get("explainability") or {}, ensure_ascii=False))
            print(f"{code}: {m} min, {' + '.join(skills)} for {today}")
    finally:
        await db.close()
    print(f"\nSign in on the lab app with any code above and the password {PIN}. Each code holds a maths and a Hindi plan for today.")


asyncio.run(main())
