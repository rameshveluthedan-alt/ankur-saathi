"""
Test-only: add a REVIEWED EXAMPLE section to the plan prompt (the I Do / We Do / You Do of the plan the education lead signed for this skill), to
see whether a smaller model with no thinking comes close to Sonnet when L2 holds reviewed examples. Imported by run_v2_matrix.py when
V2_EXAMPLE=1. No app code is changed: plan_service.build_user_prompt is wrapped for this process only.
"""
import json
from pathlib import Path

SAMPLES = Path(r"C:\dev\Ankur-Saathi-lab\db\seeds\sample_plans")


def example_section(skill: str) -> str:
    f = SAMPLES / f"{skill}.json"
    if not f.is_file():
        return ""
    p = json.loads(f.read_text(encoding="utf-8"))
    who = p.get("_reviewed_by") or "the education lead"
    out = [f"\n## REVIEWED EXAMPLE (from L2: the plan for this same skill that the education lead signed, {who})",
           "Copy its APPROACH and its HINDI STYLE for each group's teach block: the order of the steps, how the teacher speaks, how the materials are used. "
           "Do NOT copy its numbers or sentences: use NEW numbers and new examples. It was written for a 90-minute session and an older 8-problem "
           "worksheet: follow TODAY's PART C (minutes and pace) and the 3 + N sheet, not the example's lengths.\n"]
    for b in (p.get("rotation_schedule") or {}).get("blocks") or []:
        if b.get("type") == "teach":
            tp = b.get("talking_points") or {}
            out.append(f"### {b.get('teach_group')} (the example's {b.get('duration_minutes')} minutes)\n"
                       f"I Do: {tp.get('i_do_hi', '')}\nWe Do: {tp.get('we_do_hi', '')}\nYou Do: {tp.get('you_do_hi', '')}\n")
    return "\n".join(out)


def install(plan_service):
    original = plan_service.build_user_prompt

    def wrapped(ctx):
        return original(ctx) + example_section(ctx.selected_competency.id)

    plan_service.build_user_prompt = wrapped
