"""
Sign-in and the school admin's actions. See docs/AUTH.md.
Login and register are public; everything else here needs a session (app/core/security.py).
"""
from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import ensure_owner
from app.models.schemas import ChangePinRequest, ConsentRequest, LoginRequest, LoginResponse, RegisterTeacherRequest
from app.services import auth_service, register_service

auth_router = APIRouter()


def _raise(e: auth_service.AuthError):
    raise HTTPException(e.status, {"message": str(e), "code": e.code}, headers={"WWW-Authenticate": "Bearer"} if e.status == 401 else None)


@auth_router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
async def login(req: LoginRequest):
    """Employee code and password. Returns the teacher's profile and a signed session token."""
    ident = auth_service.normalise_code(req.employee_code) if req.employee_code else (req.phone_hash or "")
    async with get_db() as db:
        try:
            return await auth_service.login(db, ident or "", req.pin)
        except auth_service.AuthError as e:
            _raise(e)


@auth_router.post("/auth/register", response_model=LoginResponse, tags=["Auth"])
async def register(req: RegisterTeacherRequest):
    """Practice databases only (SELF_REGISTRATION=true): a new teacher with a school code, grades and a password. In a real school the leader makes the accounts."""
    if not get_settings().self_registration:
        raise HTTPException(403, {"message": "Accounts are made by your school leader. Ask them to add you.", "code": "registration_closed"})
    reason = auth_service.validate_pin(req.pin, req.phone_hash)
    if reason:
        raise HTTPException(400, {"message": reason, "code": "weak_pin"})
    async with get_db() as db:
        try:
            made = await register_service.register_teacher(db, req.phone_hash, req.school_code, req.enrolled_grades,
                                                           pin_hash=auth_service.hash_pin(req.pin), join_code=req.join_code,
                                                           require_consent=True, consent_version=req.consent_version)
        except register_service.ConsentRequired as e:
            raise HTTPException(400, {"message": str(e), "code": "consent_required"})
        except FileExistsError as e:
            raise HTTPException(409, {"message": str(e), "code": "exists"})
        except PermissionError as e:
            raise HTTPException(403, {"message": str(e), "code": "join_code"})
        except ValueError as e:
            raise HTTPException(400, {"message": str(e), "code": "invalid"})
        await auth_service.log_event(db, made["teacher_id"], "registered", made["role"])
        try:
            session = await auth_service.login(db, auth_service.normalise_code(req.phone_hash) or req.phone_hash, req.pin)          # the code is stored in capitals
        except auth_service.AuthError as e:
            _raise(e)
        return {**session, "join_code": made.get("join_code")}


@auth_router.get("/auth/me", response_model=LoginResponse, tags=["Auth"])
async def me(request: Request):
    async with get_db() as db:
        try:
            return await auth_service.me(db, request.state.session.teacher_id)
        except auth_service.AuthError as e:
            _raise(e)


@auth_router.post("/auth/change-pin", response_model=LoginResponse, tags=["Auth"])
async def change_pin(req: ChangePinRequest, request: Request):
    """Choose a new PIN (also the only thing a teacher can do after an admin reset). Returns a fresh session."""
    async with get_db() as db:
        try:
            return await auth_service.change_pin(db, request.state.session.teacher_id, req.current_pin, req.new_pin)
        except auth_service.AuthError as e:
            _raise(e)


# ── school admin: accounts only, never a child's data ──

@auth_router.get("/admin/school", tags=["Admin"])
async def admin_school(request: Request):
    async with get_db() as db:
        try:
            return await auth_service.admin_school(db, request.state.session.teacher_id)
        except auth_service.AuthError as e:
            _raise(e)


@auth_router.post("/admin/school/consent", tags=["Admin"])
async def admin_record_consent(req: ConsentRequest, request: Request):
    """The school admin confirms the consent statement for a school created before it existed. The wording kept is the server's own for the version named."""
    async with get_db() as db:
        try:
            return await auth_service.admin_record_consent(db, request.state.session.teacher_id, req.version)
        except auth_service.AuthError as e:
            _raise(e)


@auth_router.get("/admin/teachers", tags=["Admin"])
async def admin_teachers(request: Request):
    async with get_db() as db:
        try:
            return {"teachers": await auth_service.admin_teachers(db, request.state.session.teacher_id)}
        except auth_service.AuthError as e:
            _raise(e)


@auth_router.post("/admin/teachers/{target_id}/reset-pin", tags=["Admin"])
async def admin_reset_pin(target_id: str, request: Request):
    """A temporary PIN, shown once. The teacher can only use it to choose a new PIN."""
    async with get_db() as db:
        try:
            return await auth_service.admin_reset_pin(db, request.state.session.teacher_id, target_id)
        except auth_service.AuthError as e:
            _raise(e)


@auth_router.post("/admin/teachers/{target_id}/unlock", tags=["Admin"])
async def admin_unlock(target_id: str, request: Request):
    async with get_db() as db:
        try:
            return await auth_service.admin_unlock(db, request.state.session.teacher_id, target_id)
        except auth_service.AuthError as e:
            _raise(e)
