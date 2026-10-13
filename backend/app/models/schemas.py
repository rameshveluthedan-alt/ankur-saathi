"""
Ankur Saathi — Pydantic Models
Request/response schemas for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ============================================================================
# AUTH
# ============================================================================

class LoginRequest(BaseModel):
    phone_hash: str = Field(..., description="SHA-256 hash of phone number")

class LoginResponse(BaseModel):
    teacher_id: str
    school_code: str
    enrolled_grades: list[str]
    total_children: int


# ============================================================================
# PLAN — Competency Selection
# ============================================================================

class CompetencyNode(BaseModel):
    id: str
    name_en: str
    name_hi: str
    grade_level: str
    assessment_modality: str
    subdomain_name: str

class CompetencyTreeResponse(BaseModel):
    domain_id: str
    domain_name_hi: str
    competencies: list[CompetencyNode]

class CurriculumWeekResponse(BaseModel):
    week_number: int
    topic_title_hi: str
    competency_ids: list[str]
    notes: Optional[str] = None


# ============================================================================
# PLAN — Dainik Yojana Generation
# ============================================================================

class GeneratePlanRequest(BaseModel):
    competency_id: str = Field(..., description="Teacher-selected Lakshya competency ID")
    plan_date: date = Field(..., description="Date for this plan")
    domain_id: str = Field(..., description="'numeracy' or 'r1_literacy'")

class GroupSnapshot(BaseModel):
    label: str
    count: int
    roll_numbers: list[int]
    target_competency_id: str
    target_competency_name_hi: str

class GeneratePlanResponse(BaseModel):
    plan_date: str
    domain_id: str
    selected_competency_id: str
    groups: list[GroupSnapshot]
    plan: dict  # The full Dainik Yojana JSON from Claude
    explainability: dict
    generation_time_ms: int


# ============================================================================
# REVIEW — Evidence Capture
# ============================================================================

class AdvanceReteachRequest(BaseModel):
    plan_date: date
    domain_id: str
    decisions: dict = Field(
        ..., 
        description="Per-group decisions: {'beginner': 'advance|reteach|not_sure', ...}"
    )

class ObservedAssessmentItem(BaseModel):
    roll_number: int
    competency_id: str
    status: str = Field(..., pattern="^(achieved|partially_achieved|not_achieved)$")

class ObservedAssessmentRequest(BaseModel):
    session_date: date
    items: list[ObservedAssessmentItem]

class ORFEntryRequest(BaseModel):
    session_date: date
    roll_number: int
    passage_id: str
    cwpm: int = Field(..., ge=0, le=200)
    error_count: int = Field(..., ge=0)
    error_types: Optional[list[str]] = None

class PhotoAnalysisRequest(BaseModel):
    session_date: date
    domain_id: str
    competency_id: str
    worksheet_level: str = Field(..., pattern="^(beginner|progressor|proficient)$")
    # Photos are sent as multipart form data, not in JSON body

class ChildAnalysisResult(BaseModel):
    roll_number: int
    accuracy: float
    status: str
    misconceptions: list[str]

class PhotoAnalysisResponse(BaseModel):
    children_analysed: int
    group_accuracy: float
    ai_recommendation: str  # 'advance' or 'reteach'
    misconceptions_detected: list[dict]
    discrepancy: Optional[dict] = None
    per_child: list[ChildAnalysisResult]


# ============================================================================
# PROGRESS — Dashboard
# ============================================================================

class ChildProgressEntry(BaseModel):
    roll_number: int
    enrolled_grade: str
    numeracy_bpp: Optional[str] = None
    numeracy_competency_id: Optional[str] = None
    numeracy_competency_name_hi: Optional[str] = None
    literacy_bpp: Optional[str] = None
    literacy_competency_id: Optional[str] = None
    literacy_competency_name_hi: Optional[str] = None

class BPPSummary(BaseModel):
    domain_id: str
    beginner_count: int
    progressor_count: int
    proficient_count: int

class ProgressDashboardResponse(BaseModel):
    bpp_summary: list[BPPSummary]
    children: list[ChildProgressEntry]
    level_change_recommendations: list[dict]


# ============================================================================
# BASELINE
# ============================================================================

class StartBaselineRequest(BaseModel):
    domain_id: str
    grade_levels: list[str] = Field(..., description="Which grades to assess")

class BaselineResultItem(BaseModel):
    roll_number: int
    competency_id: str
    status: str = Field(..., pattern="^(achieved|partially_achieved|not_achieved)$")
    channel: str = Field(..., pattern="^(written_photo|observed|oral_reading)$")

class SubmitBaselineRequest(BaseModel):
    domain_id: str
    results: list[BaselineResultItem]
