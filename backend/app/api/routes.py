"""
Ankur Saathi — API Routes
Organized by PWA screen: Plan, Dainik Yojana, Review, Progress.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import PlainTextResponse, HTMLResponse, Response
import json
from datetime import date
from typing import Optional

from app.core.database import get_db
from app.core.security import ensure_owner
from app.models.schemas import (
    RegisterCommitRequest,
    GeneratePlanRequest, GeneratePlanResponse,
    AdvanceReteachRequest, ObservedAssessmentRequest, ORFEntryRequest,
    PhotoAnalysisResponse,
    ProgressDashboardResponse,
    StartBaselineRequest, SubmitBaselineRequest,
)
from app.services import ai_budget, plan_service, review_service, progress_service, worksheet_service, register_service, names_service
from app.services import group_skills

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from baseline_assessment import generate_baseline_items, compute_placement, compute_groups

router = APIRouter()


# ============================================================================
# AUTH
# ============================================================================

# ============================================================================
# CLASS REGISTER (bulk enrolment)
# ============================================================================

def _needs_register_sql(e: Exception):
    if e.__class__.__name__ in ("UndefinedColumnError", "UndefinedTableError"):
        raise HTTPException(503, "The class register needs a database update: run db/schema/07_register.sql, then restart the backend.")
    raise e


@router.get("/children/names/{teacher_id}", tags=["Register"])
async def get_child_names(teacher_id: str):
    """The names the teacher entered, for HER OWN screens. Never used for anything sent to the AI."""
    async with get_db() as db:
        return {"names": {str(k): v for k, v in (await names_service.names_for_teacher(db, teacher_id)).items()}}


@router.get("/register/template", tags=["Register"])
async def register_template():
    """The CSV template for a class register: grade, roll_number and optional starting levels. No names."""
    return Response(content="\ufeff" + register_service.TEMPLATE_CSV, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=class_register_template.csv"})


@router.post("/register/preview", tags=["Register"])
async def register_preview(request: Request, teacher_id: str = Form(...), file: UploadFile = File(...)):
    """Read a register file and show what would happen. Nothing is written."""
    ensure_owner(request, teacher_id)
    data = await file.read()
    if len(data) > 1_000_000:
        raise HTTPException(400, "The file is too large for a class register.")
    async with get_db() as db:
        try:
            return await register_service.preview_register(db, teacher_id, data, file.filename or "")
        except LookupError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            _needs_register_sql(e)


@router.post("/register/commit", tags=["Register"])
async def register_commit(req: RegisterCommitRequest, request: Request):
    """Enrol the children from a previewed register. Already-enrolled children are skipped; rows with errors are not added."""
    ensure_owner(request, req.teacher_id)
    async with get_db() as db:
        try:
            return await register_service.commit_register(db, req.teacher_id, req.rows, req.filename or "")
        except LookupError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            _needs_register_sql(e)


# ============================================================================
# SCREEN 1 — PLAN (Lakshya selection)
# ============================================================================

@router.get("/plan/competencies/{domain_id}", tags=["Plan"])
async def get_competency_tree(domain_id: str):
    """Get the competency tree for the Lakshya selector on the Plan screen."""
    if domain_id not in ('numeracy', 'r1_literacy'):
        raise HTTPException(400, "domain_id must be 'numeracy' or 'r1_literacy'")
    
    async with get_db() as db:
        tree = await plan_service.get_competency_tree(db, domain_id)
        return {"domain_id": domain_id, "competencies": tree}


@router.get("/plan/curriculum-week", tags=["Plan"])
async def get_curriculum_week(grade_level: str, domain_id: str, week_number: int):
    """Get the recommended competencies for this week from the state curriculum plan."""
    async with get_db() as db:
        from app.core.config import get_settings
        week = await plan_service.get_curriculum_week(
            db, get_settings().default_state_id, grade_level, domain_id, week_number
        )
        if not week:
            return {"week_number": week_number, "competency_ids": [], "notes": "No curriculum data for this week"}
        return week


@router.get("/plan/ladder/{competency_id}", tags=["Plan"])
async def get_group_ladder(competency_id: str):
    """The skills the plan derives for the Beginners, Progressors and Proficients when this skill is selected (the screen shows them before the plan is generated)."""
    async with get_db() as db:
        out = await group_skills.ladder(db, competency_id)
    if out is None:
        raise HTTPException(404, "No such skill")
    return out


@router.get("/plan/proposal/{teacher_id}/{domain_id}", tags=["Plan"])
async def get_group_proposal(teacher_id: str, domain_id: str, plan_date: date):
    """What each group's skill could be on plan_date, from the teacher's decisions at the last review (advance, re-teach, not sure).
    Declared BEFORE the cached-plan route, which would otherwise read 'proposal' as a teacher id."""
    if domain_id not in ('numeracy', 'r1_literacy'):
        raise HTTPException(400, "domain_id must be 'numeracy' or 'r1_literacy'")
    async with get_db() as db:
        return await group_skills.propose(db, teacher_id, domain_id, plan_date)


@router.get("/plan/groups/{teacher_id}/{domain_id}", tags=["Plan"])
async def get_groups(teacher_id: str, domain_id: str):
    """Get current B/P/P groups for this teacher + domain."""
    async with get_db() as db:
        groups = await plan_service.get_current_groups(db, teacher_id, domain_id)
        return {"domain_id": domain_id, "groups": groups}


# ============================================================================
# SCREEN 2 — DAINIK YOJANA (plan generation)
# ============================================================================

@router.post("/plan/generate", tags=["Dainik Yojana"])
async def generate_plan(req: GeneratePlanRequest, teacher_id: str):
    """
    Generate the Dainik Yojana. This is the core endpoint.
    Queries L1 + L2, builds the orchestration prompt, calls Claude,
    stores the plan, and returns it.
    """
    async with get_db() as db:
        try:
            result = await plan_service.generate_dainik_yojana(
                db, teacher_id, req.competency_id, req.domain_id, req.plan_date, group_skills=req.group_skills, reteach_groups=req.reteach_groups,
                session_minutes=req.session_minutes,
            )
            return result
        except group_skills.GroupSkillError as e:
            raise HTTPException(400, {"message": str(e), "code": "bad_group_skill"})
        except ai_budget.AICapReached as e:
            raise HTTPException(429, {"message": e.message, "code": "ai_cap", "reason": e.reason, "sample_skills": ai_budget.sample_skills()})
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(500, detail=f"Plan generation failed: {str(e)}")


@router.get("/plan/{teacher_id}/{plan_date}/{domain_id}", tags=["Dainik Yojana"])
async def get_cached_plan(teacher_id: str, plan_date: date, domain_id: str):
    """
    Get a previously generated plan (page reloads, offline cache).
    Returns the same shape as POST /plan/generate, so the PWA can use either.
    """
    async with get_db() as db:
        row = await db.fetchrow("""
            SELECT plan_content, groups_snapshot, selected_competency_id, generation_time_ms
            FROM daily_plans
            WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3
        """, teacher_id, plan_date, domain_id)

        if not row:
            raise HTTPException(404, "No plan found for this date")

        # asyncpg returns JSONB columns as JSON text unless a codec is registered
        def as_obj(v):
            return json.loads(v) if isinstance(v, str) else v

        plan = as_obj(row['plan_content']) or {}
        snapshot = as_obj(row['groups_snapshot']) or {}

        target_ids = [g.get('target') for g in snapshot.values() if g.get('target')]
        names = {}
        if target_ids:
            rows = await db.fetch(
                "SELECT id, name_hi FROM competencies WHERE id = ANY($1::text[])", target_ids
            )
            names = {r['id']: r['name_hi'] for r in rows}

        groups = []
        for label in ('beginner', 'progressor', 'proficient'):
            g = snapshot.get(label)
            if g:
                groups.append({
                    "label": label,
                    "count": g.get('count', 0),
                    "roll_numbers": g.get('rolls', []),
                    "target_competency_id": g.get('target'),
                    "target_competency_name_hi": names.get(g.get('target'), ''),
                })

        return {
            "plan_date": str(plan_date),
            "domain_id": domain_id,
            "selected_competency_id": row['selected_competency_id'],
            "groups": groups,
            "plan": plan,
            "explainability": plan.get('explainability', {}),
            "generation_time_ms": row['generation_time_ms'],
            "served_from": plan.get('served_from', 'ai'),
            # what has already been recorded against this plan: the Plan screen warns before it is replaced
            **(await plan_service.plan_evidence(db, teacher_id, plan_date, snapshot)),
        }


# ============================================================================
# SCREEN 3 — REVIEW (evidence capture + analysis)
# ============================================================================

@router.post("/review/decisions", tags=["Review"])
async def record_decisions(req: AdvanceReteachRequest, teacher_id: str):
    """
    Step 1 of Review: Teacher records Advance/Re-teach/Not-sure per group
    BEFORE seeing AI analysis. Captures independent teacher judgment.
    """
    async with get_db() as db:
        result = await review_service.record_teacher_decisions(
            db, teacher_id, req.plan_date, req.domain_id, req.decisions
        )
        return result


@router.post("/review/observed", tags=["Review"])
async def record_observed(req: ObservedAssessmentRequest, teacher_id: str):
    """
    Channel 2: Teacher-observed A/PA/NA assessments.
    Default for Beginner-level oral competencies.
    """
    async with get_db() as db:
        result = await review_service.record_observed_assessments(
            db, teacher_id, req.session_date, [item.model_dump() for item in req.items]
        )
        return result


@router.post("/review/orf", tags=["Review"])
async def record_orf(req: ORFEntryRequest, teacher_id: str):
    """
    Channel 3: Oral reading fluency — teacher stopwatch + manual entry.
    """
    async with get_db() as db:
        result = await review_service.record_orf_assessment(
            db, teacher_id, req.session_date, req.model_dump()
        )
        if result.get("status") == "error":      # an unknown roll number is a failed save, not a success with a message in it
            raise HTTPException(404, result.get("message") or "Roll number not found")
        return result


@router.post("/review/analyse-photos", response_model=PhotoAnalysisResponse, tags=["Review"])
async def analyse_photos(
    request: Request,
    teacher_id: str = Form(...),
    session_date: date = Form(...),
    domain_id: str = Form(...),
    competency_id: str = Form(...),
    worksheet_level: str = Form(...),
    teacher_pre_judgment: Optional[str] = Form(None),
    on_duplicate: str = Form("skip"),               # a child already analysed today: 'skip' keeps the earlier result
    replace_rolls: Optional[str] = Form(None),      # comma-separated roll numbers to overwrite
    photos: list[UploadFile] = File(...),
):
    """
    Channel 1: Photo capture → Claude Vision analysis.
    Accepts multipart form with 1-6 worksheet photos.
    Returns per-child results with misconception diagnosis.
    """
    from app.core.config import get_settings
    ensure_owner(request, teacher_id)
    settings = get_settings()
    
    if len(photos) > settings.max_images_per_batch:
        raise HTTPException(400, f"Maximum {settings.max_images_per_batch} photos per batch")
    
    photo_bytes_list = []
    for photo in photos:
        data = await photo.read()
        if len(data) > settings.max_image_size_bytes:
            raise HTTPException(400, f"Image too large: {len(data)} bytes (max {settings.max_image_size_bytes})")
        photo_bytes_list.append(data)
    
    async with get_db() as db:
        try:
            result = await review_service.analyse_worksheet_photos(
                db, teacher_id, session_date, domain_id, competency_id,
                worksheet_level, photo_bytes_list, teacher_pre_judgment,
                on_duplicate=on_duplicate if on_duplicate in ("skip", "replace") else "skip",
                replace_rolls=[int(x) for x in (replace_rolls or "").split(",") if x.strip().isdigit()],
            )
        except LookupError as e:
            raise HTTPException(404, str(e))
        except review_service.BadImageError as e:
            raise HTTPException(400, f"{e}. Please choose a photo of the worksheet.")
        except ai_budget.AICapReached as e:
            raise HTTPException(429, {"message": e.message, "code": "ai_cap", "reason": e.reason})
        # keep what the teacher is about to see, so Back or a reload does not lose it (a run that found only
        # children already analysed has nothing new to keep, and must not hide the earlier analysis)
        if result.get("children_analysed"):
            await review_service.save_analysis(db, teacher_id, session_date, domain_id, worksheet_level, competency_id,
                                               PhotoAnalysisResponse(**result).model_dump(mode="json"))
        return result


@router.get("/review/channels/{teacher_id}/{session_date}/{domain_id}", tags=["Review"])
async def get_review_channels(teacher_id: str, session_date: date, domain_id: str):
    """Which evidence channel (photo, observed, oral reading) each group's skill needs today."""
    async with get_db() as db:
        return await review_service.get_review_channels(db, teacher_id, session_date, domain_id)


@router.get("/review/coverage/{teacher_id}/{session_date}/{domain_id}/{worksheet_level}", tags=["Review"])
async def get_review_coverage(teacher_id: str, session_date: date, domain_id: str, worksheet_level: str,
                              sample_size: Optional[int] = None, absent: Optional[str] = None, channel: str = "photo"):
    """
    Who in the group has been analysed today and who is still to do (so no one is photographed twice), and, for a large
    group, a suggested sample (systematic sampling). `absent` is a comma-separated list of sampled children who are away.
    """
    async with get_db() as db:
        return await review_service.get_review_coverage(
            db, teacher_id, session_date, domain_id, worksheet_level, sample_size=sample_size,
            absent=[int(x) for x in (absent or "").split(",") if x.strip().isdigit()],
            channel=channel if channel in ("photo", "observed", "orf") else "photo")


@router.get("/review/analyses/{teacher_id}/{session_date}/{domain_id}", tags=["Review"])
async def get_saved_analyses(teacher_id: str, session_date: date, domain_id: str):
    """The latest photo analysis for each worksheet level on a day, to reopen after going back or reloading."""
    async with get_db() as db:
        return {"analyses": await review_service.get_latest_analyses(db, teacher_id, session_date, domain_id)}


# ============================================================================
# SCREEN 4 — PROGRESS (dashboard + export)
# ============================================================================

@router.get("/progress/dashboard/{teacher_id}", tags=["Progress"])
async def get_progress_dashboard(teacher_id: str, on: Optional[date] = None):
    """Full progress dashboard: B/P/P summary, the per-child tracker, 're-assess' flags, and what was recorded TODAY.
    `on` is the phone's own date (the same date Review saved under); without it, the server's date. Levels change only through an assessment."""
    async with get_db() as db:
        bpp = await progress_service.get_bpp_summary(db, teacher_id)
        children = await progress_service.get_children_progress(db, teacher_id)
        flags = await progress_service.get_reassessment_flags(db, teacher_id)
        today = await progress_service.get_today(db, teacher_id, on or date.today())
        for c in children:                       # each child's result today, per subject (None: nothing recorded today)
            t = today["children"].get(str(c["roll_number"]), {})
            c["numeracy_today"], c["literacy_today"] = t.get("numeracy"), t.get("r1_literacy")

        return {
            "bpp_summary": bpp,
            "children": children,
            "reassessment_flags": flags,
            "today": {"date": today["date"], **today["subjects"]},
        }


@router.get("/progress/export/class/{teacher_id}", tags=["Progress"])
async def export_class_csv(teacher_id: str):
    """The teacher's own class report WITH names. The officer (MLO) report below has roll numbers only."""
    async with get_db() as db:
        content = await progress_service.export_class_report_csv(db, teacher_id)
        from app.services import auth_service
        await auth_service.log_event(db, teacher_id, "class_report_export")        # a report with names leaves the app: it is logged
    return Response(content="\ufeff" + content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=class_report.csv"})


@router.get("/progress/export/{teacher_id}", tags=["Progress"])
async def export_mlo_csv(teacher_id: str):
    """Export MLO summary report as CSV."""
    async with get_db() as db:
        csv_content = await progress_service.export_mlo_report_csv(db, teacher_id)
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=ankur_saathi_progress.csv"}
        )


# ============================================================================
# BASELINE
# ============================================================================

@router.post("/baseline/generate", tags=["Baseline"])
async def generate_baseline(req: StartBaselineRequest):
    """Generate baseline assessment items from the L1 competency tree."""
    async with get_db() as db:
        items = await generate_baseline_items(db, req.domain_id, req.grade_levels)
        return items


@router.post("/baseline/submit", tags=["Baseline"])
async def submit_baseline(req: SubmitBaselineRequest, teacher_id: str):
    """
    Submit baseline results and compute B/P/P placement for all children.
    Re-clusters groups from fresh evidence.
    """
    async with get_db() as db:
        # Group results by child (roll number → child_id)
        children_results = {}
        for item in req.results:
            child = await db.fetchrow("""
                SELECT id FROM children 
                WHERE teacher_id = $1 AND roll_number = $2 AND is_active = TRUE
            """, teacher_id, item.roll_number)
            
            if not child:
                continue
            
            cid = str(child['id'])
            if cid not in children_results:
                children_results[cid] = []
            children_results[cid].append({
                "competency_id": item.competency_id,
                "status": item.status,
            })
        
        # Compute placement for each child
        placements = []
        for child_id, results in children_results.items():
            placement = await compute_placement(db, child_id, req.domain_id, results)
            
            if placement['current_competency_id']:
                await db.execute("""
                    INSERT INTO child_lakshya_positions
                        (child_id, domain_id, current_competency_id, bpp_level, 
                         source, evidence_days, last_assessed)
                    VALUES ($1, $2, $3, $4, 'baseline_internal', 0, NOW())
                    ON CONFLICT (child_id, domain_id) DO UPDATE SET
                        current_competency_id = EXCLUDED.current_competency_id,
                        bpp_level = EXCLUDED.bpp_level,
                        source = 'baseline_internal',
                        last_assessed = NOW(),
                        updated_at = NOW()
                """, child_id, req.domain_id, 
                    placement['current_competency_id'], placement['bpp_level'])
            
            placements.append({
                "child_id": child_id,
                "bpp_level": placement['bpp_level'],
                "competency_id": placement['current_competency_id'],
                "evidence": placement['evidence_summary'],
            })
        
        # Recompute groups
        groups = await compute_groups(db, teacher_id, req.domain_id)
        
        return {
            "status": "baseline_complete",
            "children_placed": len(placements),
            "placements": placements,
            "new_groups": groups,
        }


# ============================================================================
# WORKSHEETS
# ============================================================================

@router.get("/worksheet/{teacher_id}/{plan_date}/{domain_id}/{level}", response_class=HTMLResponse, tags=["Worksheet"])
async def get_worksheet(teacher_id: str, plan_date: date, domain_id: str, level: str):
    """
    Render a printable A4 worksheet from the generated plan.
    Opens in browser — teacher prints with Ctrl+P.
    """
    if level not in ('beginner', 'progressor', 'proficient'):
        raise HTTPException(400, "level must be beginner, progressor, or proficient")
    
    async with get_db() as db:
        # Get the stored plan
        row = await db.fetchrow("""
            SELECT plan_content, selected_competency_id, groups_snapshot FROM daily_plans
            WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3
        """, teacher_id, plan_date, domain_id)
        
        if not row:
            raise HTTPException(404, "No plan found for this date. Generate a plan first.")
        
        plan_data = row['plan_content'] if isinstance(row['plan_content'], dict) else json.loads(row['plan_content'])
        # Each level's sheet is titled with that group's own target skill (the Beginner sheet teaches
        # the prerequisite, the Proficient sheet the extension), not the day's main skill for all three.
        snapshot = row['groups_snapshot']
        snapshot = json.loads(snapshot) if isinstance(snapshot, str) else (snapshot or {})
        comp_id = (snapshot.get(level) or {}).get('target') or row['selected_competency_id']
        
        # Get competency names
        comp = await db.fetchrow(
            "SELECT name_hi, name_en FROM competencies WHERE id = $1", comp_id
        )
        
        try:
            class_numbers = bool(await db.fetchval(
                "SELECT EXISTS (SELECT 1 FROM children WHERE teacher_id = $1 AND school_roll IS NOT NULL AND school_roll <> roll_number)", teacher_id))
        except Exception as e:                       # a database that has not loaded db/schema/07_register.sql yet: the worksheet says Roll No.
            if e.__class__.__name__ != "UndefinedColumnError":
                raise
            class_numbers = False
        html = worksheet_service.render_worksheet(
            plan_data=plan_data,
            level=level,
            competency_id=comp_id,
            competency_name_hi=comp['name_hi'] if comp else comp_id,
            competency_name_en=comp['name_en'] if comp else '',
            domain_id=domain_id,
            plan_date=str(plan_date),
            class_numbers=class_numbers,
        )
        return HTMLResponse(content=html)


@router.get("/worksheet/sample/{domain_id}/{level}", response_class=HTMLResponse, tags=["Worksheet"])
async def get_sample_worksheet(domain_id: str, level: str):
    """
    Render a sample worksheet for testing/demo — no plan generation needed.
    """
    if level not in ('beginner', 'progressor', 'proficient'):
        raise HTTPException(400, "level must be beginner, progressor, or proficient")
    if domain_id not in ('numeracy', 'r1_literacy'):
        raise HTTPException(400, "domain_id must be numeracy or r1_literacy")
    
    # Sample competency IDs
    comp_map = {
        'numeracy': {
            'beginner': ('N2.3.1', 'बिना हासिल दो अंकों का जोड़', '2-digit addition without carry'),
            'progressor': ('N2.3.2', 'हासिल के साथ दो अंकों का जोड़', '2-digit addition with carry'),
            'proficient': ('N2.3.5', 'शाब्दिक प्रश्न (जोड़/घटाव)', 'Word problems (addition/subtraction)'),
        },
        'r1_literacy': {
            'beginner': ('L1.3.1', 'व्यंजन पहचान और लेखन', 'Consonant recognition and writing'),
            'progressor': ('L2.5.1', 'पठन प्रवाह', 'Reading fluency'),
            'proficient': ('L3.6.1', 'अनुमान लगाना', 'Making inferences'),
        },
    }
    
    comp_id, name_hi, name_en = comp_map[domain_id][level]
    
    html = worksheet_service.render_sample_worksheet(
        level=level,
        domain_id=domain_id,
        competency_id=comp_id,
        competency_name_hi=name_hi,
        competency_name_en=name_en,
    )
    return HTMLResponse(content=html)
