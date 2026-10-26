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
    phone_hash: str = Field(..., description="'hash_' + the phone number: an identifier, not a secret. The PIN is the secret.")
    pin: str = Field(..., description="4 to 6 digits")


class RegisterTeacherRequest(BaseModel):
    phone_hash: str
    school_code: str
    enrolled_grades: list[str]
    pin: str
    join_code: Optional[str] = None      # required when the school already exists: the admin shares it
    consent_version: Optional[str] = None   # required when the school is NEW: the version of the consent statement the person confirmed (pwa/src/services/consent.js)


class ConsentRequest(BaseModel):
    version: str                         # the version of the consent statement the admin read and confirmed


class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str


class RegisterCommitRequest(BaseModel):
    teacher_id: str
    filename: Optional[str] = None
    rows: list[dict]


class LoginResponse(BaseModel):
    teacher_id: str
    school_code: str
    enrolled_grades: list[str]
    total_children: int
    token: Optional[str] = None
    role: str = "teacher"
    must_change_pin: bool = False
    is_demo: bool = False
    pin_fixed: bool = False
    join_code: Optional[str] = None       # only when this registration created a new school (so its admin sees it once)
    expires_in_hours: Optional[float] = None


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
    group_skills: Optional[dict[str, str]] = Field(None, description="Skills the teacher chose for the 'beginner' and 'proficient' groups; the Progressors' skill is competency_id. Without it each is derived from competency_id.")
    reteach_groups: Optional[list[str]] = Field(None, description="Groups the teacher chose to re-teach: their MAIN block is a focused re-teach and there is no separate re-teach block. An empty list means move on with every group. Omitted: the old way (a separate 5-minute block when yesterday's photos found mistakes).")

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
    accuracy: Optional[float] = None         # None when nothing could be scored (every problem copied differently or blank)
    status: str
    misconceptions: list[str]
    assessed_problems: Optional[int] = None  # how many problems the accuracy is out of
    copy_errors: list[dict] = []             # problems the child copied differently: shown to the teacher, not scored
    needs_check: list[int] = []              # problems the AI was not sure it read: check them in the notebook

class PhotoAnalysisResponse(BaseModel):
    children_analysed: int
    group_accuracy: float
    ai_recommendation: str  # 'advance' or 'reteach'
    misconceptions_detected: list[dict]
    discrepancy: Optional[dict] = None
    per_child: list[ChildAnalysisResult]
    skipped_duplicates: list[dict] = []      # children already analysed today: the earlier result was kept
    duplicates_in_batch: list[int] = []      # a child photographed twice in one batch: the clearer photo was used
    unknown_rolls: list[int] = []            # roll numbers that are not in this class
    outside_group_rolls: list[int] = []      # a sheet from another group than the one selected
    not_assessed: list[int] = []             # nothing on the sheet could be scored
    unreadable_sheets: int = 0               # sheets whose roll number could not be read
    copy_errors_excluded: int = 0            # problems left out of the scores because they were copied differently


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
    numeracy_level_as_of: Optional[str] = None
    numeracy_level_source: Optional[str] = None
    literacy_level_as_of: Optional[str] = None
    literacy_level_source: Optional[str] = None

class BPPSummary(BaseModel):
    domain_id: str
    beginner_count: int
    progressor_count: int
    proficient_count: int

class ProgressDashboardResponse(BaseModel):
    bpp_summary: list[BPPSummary]
    children: list[ChildProgressEntry]
    reassessment_flags: dict


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
