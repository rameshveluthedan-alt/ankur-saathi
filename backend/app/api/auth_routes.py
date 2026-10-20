"""
Sign-in and the school admin's actions. See docs/AUTH.md.
Login and register are public; everything else here needs a session (app/core/security.py).
"""
from fastapi import APIRouter, HTTPException, Request

from app.core.database import get_db
from app.core.security import ensure_owner
from app.models.schemas import ChangePinRequest, LoginRequest, LoginResponse, RegisterTeacherRequest
from app.services import auth_service, register_service

auth_router = APIRouter()


def _raise(e: auth_service.AuthError):
    raise HTTPException(e.status, {"message": str(e), "code": e.code}, headers={"WWW-Authenticate": "Bearer"} if e.status == 401 else None)


@auth_router.post("/auth/login", response_model=LoginResponse, tags=["Auth"])
async def login(req: LoginRequest):
    """Phone number and PIN. Returns the teacher's profile and a signed session token."""
    async with get_db() as db:
        try:
            return await auth_service.login(db, req.phone_hash, req.pin)
        except auth_service.AuthError as e:
            _raise(e)


@auth_router.post("/auth/register", response_model=LoginResponse, tags=["Auth"])
async def register(req: RegisterTeacherRequest):
    """A new teacher: phone, school code, grades and a PIN. A new school code makes this teacher its admin."""
    reason = auth_service.validate_pin(req.pin, req.phone_hash)
    if reason:
        raise HTTPException(400, {"message": reason, "code": "weak_pin"})
    async with get_db() as db:
        try:
            made = await register_service.register_teacher(db, req.phone_hash, req.school_code, req.enrolled_grades,
                                                           pin_hash=auth_service.hash_pin(req.pin), join_code=req.join_code)
        except FileExistsError as e:
            raise HTTPException(409, {"message": str(e), "code": "exists"})
        except PermissionError as e:
            raise HTTPException(403, {"message": str(e), "code": "join_code"})
        except ValueError as e:
            raise HTTPException(400, {"message": str(e), "code": "invalid"})
        await auth_service.log_event(db, made["teacher_id"], "registered", made["role"])
        try:
            session = await auth_service.login(db, req.phone_hash, req.pin)
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


@auth_router.post("/admin/school/join-code", tags=["Admin"])
async def admin_rotate_join_code(request: Request):
    """A new join code (the old one stops working). Teachers already registered are not affected."""
    async with get_db() as db:
        try:
            return await auth_service.admin_rotate_join_code(db, request.state.session.teacher_id)
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
