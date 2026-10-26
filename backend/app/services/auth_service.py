"""
Sign-in: a PIN, a signed session token, and a school admin who can reset a forgotten PIN. (docs/AUTH.md)

  * The PIN is stored only as a PBKDF2 hash. 4 to 6 digits, no trivial ones (1234, 0000, the end of the phone number).
  * 5 wrong PINs lock the account for 15 minutes; a school admin can unlock it.
  * Login returns a signed token (HMAC-SHA256, expires in SESSION_HOURS). Every route except a few public ones requires it, and a
    route that names a teacher requires the token to be THAT teacher's (app/core/security.py).
  * A token carries the PIN version: changing or resetting a PIN ends every session signed before it.
  * A school admin resets a teacher's PIN to a temporary one, shown once. The teacher can only use it to choose a new PIN.
    An admin sees account details only (never a child's data), and only for their own school.
  * Shared demo accounts (pin_fixed) cannot have their PIN changed or reset, so one tester cannot lock out the others.
"""

import base64
import hashlib
import hmac
import json
import re
from pathlib import Path
import secrets
import time
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15
_WEAK = {"1111", "1234", "0000", "1122", "2580", "1212", "4321", "5555", "6969", "7777", "8888", "9999", "123456", "654321", "000000", "111111", "121212", "112233"}
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"          # no 0/O or 1/I/L, so a join code can be read aloud


class AuthError(Exception):
    """status: the HTTP status to answer with; code: a short machine-readable reason the app can act on."""
    def __init__(self, message, status=401, code="auth"):
        super().__init__(message)
        self.status, self.code = status, code


# ── PINs ────────────────────────────────────────────────────────────────────

def validate_pin(pin: str, phone_hash: str = None):
    """Returns a reason the PIN is not allowed, or None."""
    pin = str(pin or "")
    if not re.fullmatch(r"\d{4,6}", pin):
        return "The PIN must be 4 to 6 digits."
    if len(set(pin)) == 1:
        return "The PIN cannot be one digit repeated."
    d = [int(c) for c in pin]
    steps = {b - a for a, b in zip(d, d[1:])}
    if steps <= {1} or steps <= {-1}:
        return "The PIN cannot be a run of digits like 1234 or 4321."
    if pin in _WEAK:
        return "That PIN is too common. Choose another."
    tail = re.sub(r"\D", "", phone_hash or "")[-len(pin):]
    if tail and pin == tail:
        return "The PIN cannot be the last digits of your phone number."
    return None


def hash_pin(pin: str, iterations: int = None) -> str:
    n = iterations or get_settings().pin_hash_iterations
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", str(pin).encode(), salt, n)
    return f"pbkdf2_sha256${n}${salt.hex()}${dk.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        _, n, salt, want = stored.split("$")
        got = hashlib.pbkdf2_hmac("sha256", str(pin).encode(), bytes.fromhex(salt), int(n))
        return hmac.compare_digest(got.hex(), want)
    except (ValueError, AttributeError):
        return False


def temporary_pin() -> str:
    while True:
        pin = f"{secrets.randbelow(900000) + 100000}"
        if validate_pin(pin) is None:
            return pin


def new_join_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(6))


# ── tokens ──────────────────────────────────────────────────────────────────

_ephemeral = secrets.token_hex(32)
_warned = False


def _secret() -> bytes:
    global _warned
    s = get_settings()
    if s.session_secret:
        return s.session_secret.encode()
    if not s.debug:
        raise RuntimeError("SESSION_SECRET is not set. It is required unless DEBUG is true (docs/AUTH.md).")
    if not _warned:
        print("   WARNING: SESSION_SECRET is not set: using a temporary one, so every restart signs everyone out. Set it before hosting.")
        _warned = True
    return _ephemeral.encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(claims: dict, hours: float = None) -> str:
    payload = {**claims, "exp": int(time.time() + 3600 * (hours if hours is not None else get_settings().session_hours))}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())}"


def read_token(token: str) -> dict:
    try:
        body, sig = token.split(".")
        if not hmac.compare_digest(_b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest()), sig):
            raise ValueError
        claims = json.loads(_unb64(body))
    except (ValueError, AttributeError, json.JSONDecodeError):
        raise AuthError("Please sign in again.", 401, "invalid_token")
    if claims.get("exp", 0) < time.time():
        raise AuthError("Your session has ended. Please sign in again.", 401, "expired")
    return claims


# ── events ──────────────────────────────────────────────────────────────────

async def log_event(db, teacher_id, event: str, detail: str = None):
    try:
        await db.execute("INSERT INTO auth_events (teacher_id, event, detail) VALUES ($1, $2, $3)", teacher_id, event, detail)
    except Exception as e:                       # a database without db/schema/09_auth.sql: never let logging break sign-in
        if e.__class__.__name__ not in ("UndefinedTableError", "UndefinedColumnError"):
            raise


# ── login ───────────────────────────────────────────────────────────────────

_DUMMY = None


async def _profile(db, row) -> dict:
    children = await db.fetchval("SELECT count(*) FROM children WHERE teacher_id = $1 AND is_active = TRUE", row["id"])
    return {"teacher_id": str(row["id"]), "school_code": row["school_code"], "enrolled_grades": row["enrolled_grades"], "total_children": children,
            "role": row["role"], "must_change_pin": row["must_change_pin"], "is_demo": row["is_demo"], "pin_fixed": row["pin_fixed"]}


def _issue(row) -> str:
    return make_token({"tid": str(row["id"]), "role": row["role"], "pv": row["pin_version"], "mcp": row["must_change_pin"]})


_SESSION_SQL = """SELECT t.id, t.role, t.school_id, t.enrolled_grades, t.pin_hash, t.pin_version, t.must_change_pin, t.failed_pin_attempts, t.locked_until,
                         t.is_demo, t.pin_fixed, s.school_code
                  FROM teachers t JOIN schools s ON s.id = t.school_id"""


async def login(db, phone_hash: str, pin: str) -> dict:
    global _DUMMY
    row = await db.fetchrow(_SESSION_SQL + " WHERE t.phone_hash = $1", phone_hash)
    if not row:
        _DUMMY = _DUMMY or hash_pin("482916")
        verify_pin(pin, _DUMMY)                  # the same work as a real check, so timing does not reveal which phone numbers exist
        raise AuthError("The phone number or PIN is not right.", 401, "bad_login")
    now = datetime.now(timezone.utc)
    if row["locked_until"] and row["locked_until"] > now:
        mins = int((row["locked_until"] - now).total_seconds() // 60) + 1
        raise AuthError(f"Too many wrong PINs. Try again in {mins} minutes, or ask your school admin to unlock you.", 429, "locked")
    if not row["pin_hash"]:
        raise AuthError("No PIN has been set for this account. Ask your school admin.", 403, "pin_not_set")
    if not verify_pin(pin, row["pin_hash"]):
        failed = row["failed_pin_attempts"] + 1
        if failed >= MAX_ATTEMPTS:
            await db.execute("UPDATE teachers SET failed_pin_attempts = 0, locked_until = $2 WHERE id = $1", row["id"], now + timedelta(minutes=LOCK_MINUTES))
            await log_event(db, row["id"], "locked", f"{MAX_ATTEMPTS} wrong PINs")
            raise AuthError(f"Too many wrong PINs. Try again in {LOCK_MINUTES} minutes, or ask your school admin to unlock you.", 429, "locked")
        await db.execute("UPDATE teachers SET failed_pin_attempts = $2 WHERE id = $1", row["id"], failed)
        await log_event(db, row["id"], "login_failed")
        raise AuthError("The phone number or PIN is not right.", 401, "bad_login")
    await db.execute("UPDATE teachers SET failed_pin_attempts = 0, locked_until = NULL, last_active_at = now() WHERE id = $1", row["id"])
    await log_event(db, row["id"], "login_ok")
    return {**await _profile(db, row), "token": _issue(row), "expires_in_hours": get_settings().session_hours}


async def session_row(db, teacher_id):
    return await db.fetchrow(_SESSION_SQL + " WHERE t.id = $1", teacher_id)


async def me(db, teacher_id) -> dict:
    row = await session_row(db, teacher_id)
    if not row:
        raise AuthError("Please sign in again.", 401, "invalid_token")
    return await _profile(db, row)


async def change_pin(db, teacher_id, current_pin: str, new_pin: str) -> dict:
    row = await session_row(db, teacher_id)
    if not row:
        raise AuthError("Please sign in again.", 401, "invalid_token")
    if row["pin_fixed"]:
        raise AuthError("This is a shared demo account: its PIN cannot be changed. Use the 'Change PIN' account to try it.", 403, "pin_fixed")
    if not row["pin_hash"] or not verify_pin(current_pin, row["pin_hash"]):
        raise AuthError("The current PIN is not right.", 401, "bad_pin")
    reason = validate_pin(new_pin) or ("Choose a PIN different from the current one." if verify_pin(new_pin, row["pin_hash"]) else None)
    if reason:
        raise AuthError(reason, 400, "weak_pin")
    await db.execute("UPDATE teachers SET pin_hash = $2, pin_version = pin_version + 1, must_change_pin = FALSE, pin_changed_at = now(), failed_pin_attempts = 0, locked_until = NULL WHERE id = $1",
                     teacher_id, hash_pin(new_pin))
    await log_event(db, teacher_id, "pin_changed")
    fresh = await session_row(db, teacher_id)
    return {**await _profile(db, fresh), "token": _issue(fresh), "expires_in_hours": get_settings().session_hours}


# ── the school's consent confirmation ───────────────────────────────────────

# What a school confirms when it is created, and the wording is kept with every confirmation. pwa/src/services/consent.js holds the SAME words: backend/tests/test_consent.py compares them.
CONSENT_VERSION = "v1"
CONSENT_TEXT = {
    "en": "The school has told the children’s parents or guardians that the children’s classwork will be read in this app, and has their permission. "
          "Photos are read by an AI and are not kept. Children’s names are never sent to the AI.",
    "hi": "स्कूल ने बच्चों के अभिभावकों को बता दिया है कि बच्चों का कक्षा-कार्य इस ऐप में पढ़ा जाएगा, और उनकी अनुमति ले ली है। "
          "फ़ोटो AI द्वारा पढ़ी जाती हैं और सहेजी नहीं जातीं। बच्चों के नाम AI को कभी नहीं भेजे जाते।",
}
DEMO_CONSENT = {"version": "demo", "statement": "Demonstration school: every child and every record in it is fictional. No real child's data is held here."}
_CONSENT_DDL = Path(__file__).resolve().parents[3] / "db" / "schema" / "13_school_consent.sql"
_consent_table_ready = False


def consent_statement() -> str:
    """The wording as it is stored with a confirmation: English, then Hindi."""
    return CONSENT_TEXT["en"] + "\n" + CONSENT_TEXT["hi"]


async def ensure_consent_table(db):
    """Create the table on first use (idempotent), once per process. Called BEFORE a transaction starts, so a failure here cannot abort one."""
    global _consent_table_ready
    if not _consent_table_ready:
        await db.execute(_CONSENT_DDL.read_text(encoding="utf-8"))
        _consent_table_ready = True


async def record_consent(db, school_id, teacher_id, version: str = None, statement: str = None) -> dict:
    """Keep one confirmation. The wording stored is the server's own for that version, never text sent by a browser. Run inside the caller's transaction if there is one."""
    version = version or CONSENT_VERSION
    if version == CONSENT_VERSION and statement is None:
        statement = consent_statement()
    if not statement:
        raise ValueError("A confirmation needs its wording.")
    row = await db.fetchrow("INSERT INTO school_consents (school_id, attested_by, version, statement) VALUES ($1, $2, $3, $4) RETURNING attested_at", school_id, teacher_id, version, statement)
    return {"version": version, "attested_at": row["attested_at"].isoformat()}


async def latest_consent(db, school_id):
    """The school's latest confirmation as the admin screen shows it (who: only the end of the phone number), or None."""
    await ensure_consent_table(db)
    r = await db.fetchrow("""SELECT c.version, c.attested_at, t.phone_hash FROM school_consents c LEFT JOIN teachers t ON t.id = c.attested_by
                             WHERE c.school_id = $1 ORDER BY c.attested_at DESC LIMIT 1""", school_id)
    if not r:
        return None
    return {"version": r["version"], "attested_at": r["attested_at"].isoformat(), "by": ("••••" + re.sub(r"\D", "", r["phone_hash"])[-4:]) if r["phone_hash"] else None, "demo": r["version"] == "demo"}


async def ensure_demo_consent(db, school_code: str):
    """A demonstration school (the demo school, the test school) carries the statement that everything in it is fictional, so its admin screen never shows 'not recorded'. Idempotent."""
    await ensure_consent_table(db)
    sid = await db.fetchval("SELECT id FROM schools WHERE school_code = $1", school_code)
    if not sid or await db.fetchval("SELECT 1 FROM school_consents WHERE school_id = $1", sid):
        return False
    await record_consent(db, sid, None, DEMO_CONSENT["version"], DEMO_CONSENT["statement"])
    return True


# ── the school admin ────────────────────────────────────────────────────────

def _admin_only(admin):
    if not admin or admin["role"] != "school_admin":
        raise AuthError("Only the school admin can do this.", 403, "not_admin")


async def admin_school(db, admin_id) -> dict:
    admin = await session_row(db, admin_id)
    _admin_only(admin)
    out = dict(await db.fetchrow("SELECT school_code, join_code FROM schools WHERE id = $1", admin["school_id"]))
    out["consent"] = await latest_consent(db, admin["school_id"])          # None: nothing recorded yet
    out["consent_text"] = {"version": CONSENT_VERSION, **CONSENT_TEXT}
    return out


async def admin_record_consent(db, admin_id, version: str) -> dict:
    """A school created before this existed (or one that skipped it) confirms now. Only its admin can."""
    admin = await session_row(db, admin_id)
    _admin_only(admin)
    if version != CONSENT_VERSION:
        raise AuthError("The wording has changed. Reload the page and read it again.", 409, "consent_stale")
    await ensure_consent_table(db)
    async with db.transaction():
        done = await record_consent(db, admin["school_id"], admin_id)
    await log_event(db, admin_id, "consent_recorded", CONSENT_VERSION)
    return {"consent": await latest_consent(db, admin["school_id"]), **done}


async def admin_rotate_join_code(db, admin_id) -> dict:
    admin = await session_row(db, admin_id)
    _admin_only(admin)
    code = new_join_code()
    await db.execute("UPDATE schools SET join_code = $2 WHERE id = $1", admin["school_id"], code)
    return {"join_code": code}


async def admin_teachers(db, admin_id) -> list:
    """The school's accounts, with no child data and only the end of each phone number."""
    admin = await session_row(db, admin_id)
    _admin_only(admin)
    now = datetime.now(timezone.utc)
    rows = await db.fetch("""SELECT t.id, t.phone_hash, t.role, t.pin_hash IS NOT NULL AS has_pin, t.must_change_pin, t.locked_until, t.last_active_at, t.is_demo, t.pin_fixed,
                                    (SELECT count(*) FROM children c WHERE c.teacher_id = t.id AND c.is_active) AS children
                             FROM teachers t WHERE t.school_id = $1 ORDER BY t.created_at""", admin["school_id"])
    return [{"teacher_id": str(r["id"]), "phone_end": "••••" + re.sub(r"\D", "", r["phone_hash"])[-4:], "role": r["role"], "children": r["children"], "has_pin": r["has_pin"],
             "must_change_pin": r["must_change_pin"], "locked": bool(r["locked_until"] and r["locked_until"] > now), "pin_fixed": r["pin_fixed"], "is_demo": r["is_demo"],
             "last_active_at": r["last_active_at"].isoformat() if r["last_active_at"] else None, "is_you": str(r["id"]) == str(admin_id)} for r in rows]


async def _target(db, admin_id, teacher_id):
    admin = await session_row(db, admin_id)
    _admin_only(admin)
    target = await session_row(db, teacher_id)
    if not target or target["school_id"] != admin["school_id"]:      # another school's teachers do not exist, as far as this admin can tell
        raise AuthError("No such teacher in your school.", 404, "not_found")
    return admin, target


async def admin_reset_pin(db, admin_id, teacher_id) -> dict:
    admin, target = await _target(db, admin_id, teacher_id)
    if str(admin["id"]) == str(target["id"]):
        raise AuthError("Change your own PIN from your account. If you have forgotten it, the operator can reset it.", 400, "self_reset")
    if target["pin_fixed"]:
        raise AuthError("This is a shared demo account: its PIN is fixed and cannot be reset.", 403, "pin_fixed")
    temp = temporary_pin()
    await db.execute("UPDATE teachers SET pin_hash = $2, pin_version = pin_version + 1, must_change_pin = TRUE, failed_pin_attempts = 0, locked_until = NULL WHERE id = $1",
                     target["id"], hash_pin(temp))
    await log_event(db, target["id"], "pin_reset_by_admin", f"by {admin['id']}")
    return {"temporary_pin": temp, "note": "Shown once. Give it to the teacher: it only lets them choose a new PIN."}


async def admin_unlock(db, admin_id, teacher_id) -> dict:
    admin, target = await _target(db, admin_id, teacher_id)
    await db.execute("UPDATE teachers SET failed_pin_attempts = 0, locked_until = NULL WHERE id = $1", target["id"])
    await log_event(db, target["id"], "unlocked", f"by {admin['id']}")
    return {"unlocked": True}
