"""
Every route except a few public ones needs a valid session token, and a route that names a teacher needs the token to be THAT
teacher's. Without this a PIN screen would protect nothing, because the teacher ids in the URLs are not secret.
"""
from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.database import get_db
from app.services import auth_service

# reference data and the sign-in routes themselves
PUBLIC = ("/api/auth/login", "/api/auth/register", "/api/register/template", "/api/plan/competencies/", "/api/plan/curriculum-week", "/api/worksheet/sample/")
# a teacher who must choose a new PIN may do only these
PIN_CHANGE_ONLY = ("/api/auth/change-pin", "/api/auth/me")


class Session:
    def __init__(self, teacher_id, role, school_id):
        self.teacher_id, self.role, self.school_id = str(teacher_id), role, school_id


def _fail(e: auth_service.AuthError):
    return HTTPException(e.status, {"message": str(e), "code": e.code}, headers={"WWW-Authenticate": "Bearer"} if e.status == 401 else None)


async def require_auth(request: Request):
    request.state.session = None
    if get_settings().auth_mode == "off":
        return
    path = request.url.path
    if any(path.startswith(p) for p in PUBLIC):
        return
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise _fail(auth_service.AuthError("Please sign in.", 401, "no_token"))
    try:
        claims = auth_service.read_token(header[7:].strip())
        async with get_db() as db:
            row = await auth_service.session_row(db, claims["tid"])
    except auth_service.AuthError as e:
        raise _fail(e)
    if not row or row["pin_version"] != claims.get("pv"):          # a PIN change or reset ends every earlier session
        raise _fail(auth_service.AuthError("Your PIN was changed. Please sign in again.", 401, "pin_changed"))
    if row["must_change_pin"] and path not in PIN_CHANGE_ONLY:
        raise HTTPException(403, {"message": "Choose a new PIN first.", "code": "pin_change_required"})
    session = Session(row["id"], row["role"], row["school_id"])
    request.state.session = session
    if path.startswith("/api/admin/") and session.role != "school_admin":
        raise HTTPException(403, {"message": "Only the school admin can do this.", "code": "not_admin"})
    if path.startswith("/api/admin/"):
        return                                   # admin routes name a TARGET account, and are authorised by role and school in the service
    for source in (request.path_params, request.query_params):
        named = source.get("teacher_id")
        if named and str(named) != session.teacher_id:
            raise HTTPException(403, {"message": "This is not your class.", "code": "not_yours"})


def ensure_owner(request: Request, teacher_id) -> None:
    """For routes that read the teacher id from a form or a body, where the dependency cannot see it."""
    session = getattr(request.state, "session", None)
    if get_settings().auth_mode == "off" or session is None:
        return
    if str(teacher_id) != session.teacher_id:
        raise HTTPException(403, {"message": "This is not your class.", "code": "not_yours"})
