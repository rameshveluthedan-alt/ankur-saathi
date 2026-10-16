"""
Ankur Saathi — API Routes
Organized by PWA screen: Plan, Dainik Yojana, Review, Progress.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse, HTMLResponse
import json
from datetime import date
from typing import Optional

from app.core.database import get_db
from app.models.schemas import (
    LoginRequest, LoginResponse,
    GeneratePlanRequest, GeneratePlanResponse,
    AdvanceReteachRequest, ObservedAssessmentRequest, ORFEntryRequest,
    PhotoAnalysisResponse,
    ProgressDashboardResponse,
    StartBaselineRequest, SubmitBaselineRequest,
)
from app.services import plan_service, review_service, progress_service, worksheet_service

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from baseline_assessment import generate_baseline_items, compute_placement, compute_groups

router = APIRouter()


# ============================================================================
# AUTH
# ============================================================================

@router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
async def login(req: LoginRequest):
    """Simple phone-hash login. Returns teacher context."""
    async with get_db() as db:
        teacher = await db.fetchrow("""
            SELECT t.id, t.enrolled_grades, s.school_code,
                   (SELECT count(*) FROM children WHERE teacher_id = t.id AND is_active = TRUE) as child_count
            FROM teachers t
            JOIN schools s ON t.school_id = s.id
            WHERE t.phone_hash = $1
        """, req.phone_hash)
        
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")
        
        return LoginResponse(
            teacher_id=str(teacher['id']),
            school_code=teacher['school_code'],
            enrolled_grades=teacher['enrolled_grades'],
            total_children=teacher['child_count'],
        )


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
                db, teacher_id, req.competency_id, req.domain_id, req.plan_date
            )
            return result
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
        return result


@router.post("/review/analyse-photos", response_model=PhotoAnalysisResponse, tags=["Review"])
async def analyse_photos(
    teacher_id: str = Form(...),
    session_date: date = Form(...),
    domain_id: str = Form(...),
    competency_id: str = Form(...),
    worksheet_level: str = Form(...),
    teacher_pre_judgment: Optional[str] = Form(None),
    photos: list[UploadFile] = File(...),
):
    """
    Channel 1: Photo capture → Claude Vision analysis.
    Accepts multipart form with 1-6 worksheet photos.
    Returns per-child results with misconception diagnosis.
    """
    from app.core.config import get_settings
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
        result = await review_service.analyse_worksheet_photos(
            db, teacher_id, session_date, domain_id, competency_id,
            worksheet_level, photo_bytes_list, teacher_pre_judgment,
        )
        return result


# ============================================================================
# SCREEN 4 — PROGRESS (dashboard + export)
# ============================================================================

@router.get("/progress/dashboard/{teacher_id}", tags=["Progress"])
async def get_progress_dashboard(teacher_id: str):
    """Full progress dashboard: B/P/P summary + per-child tracker + level change recommendations."""
    async with get_db() as db:
        bpp = await progress_service.get_bpp_summary(db, teacher_id)
        children = await progress_service.get_children_progress(db, teacher_id)
        level_changes = await progress_service.get_level_change_recommendations(db, teacher_id)
        
        return {
            "bpp_summary": bpp,
            "children": children,
            "level_change_recommendations": level_changes,
        }


@router.post("/progress/level-change", tags=["Progress"])
async def apply_level_change(teacher_id: str, child_id: str, domain_id: str, new_bpp: str):
    """Teacher approves a level change recommendation."""
    if new_bpp not in ('beginner', 'progressor', 'proficient'):
        raise HTTPException(400, "new_bpp must be beginner, progressor, or proficient")
    
    async with get_db() as db:
        result = await progress_service.apply_level_change(db, teacher_id, child_id, domain_id, new_bpp)
        return result


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
            SELECT plan_content, selected_competency_id FROM daily_plans
            WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3
        """, teacher_id, plan_date, domain_id)
        
        if not row:
            raise HTTPException(404, "No plan found for this date. Generate a plan first.")
        
        plan_data = row['plan_content'] if isinstance(row['plan_content'], dict) else json.loads(row['plan_content'])
        comp_id = row['selected_competency_id']
        
        # Get competency names
        comp = await db.fetchrow(
            "SELECT name_hi, name_en FROM competencies WHERE id = $1", comp_id
        )
        
        html = worksheet_service.render_worksheet(
            plan_data=plan_data,
            level=level,
            competency_id=comp_id,
            competency_name_hi=comp['name_hi'] if comp else comp_id,
            competency_name_en=comp['name_en'] if comp else '',
            domain_id=domain_id,
            plan_date=str(plan_date),
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
