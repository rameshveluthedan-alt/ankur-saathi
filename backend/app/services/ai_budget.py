"""
The AI budget (docs/AI_BUDGET.md).

The hackathon credits are a fixed pool that expires on 20 Nov 2026 and must still be there when evaluators arrive. So every call to
the AI is METERED (tokens, per teacher and school) and CAPPED:

  * the reserve rule: until AI_RESERVE_FROM, development cannot spend into the amount kept for evaluators; after it the reserve is
    released, down to a small final margin;
  * daily caps (in India time): all users together (the kill switch), per school, per teacher, and a higher one for shared demo accounts;
  * AI_ENABLED=false stops every call; after AI_CREDIT_EXPIRES nothing is called.

When a cap is reached the app does not just fail. For a PLAN, a recorded plan for the same skill (db/seeds/sample_plans) goes through
the same checks and repairs as a fresh one and is clearly labelled as a sample. A PHOTO analysis cannot be faked, so it says why it
cannot run.

Tokens are the ground truth; money is computed from them with the CURRENT prices in the settings, so correcting a price corrects every
past estimate. If the meter table is missing (a database that has not loaded db/schema/10_ai_usage.sql) calls are NOT blocked, but a
warning is printed: check `scripts/ai_usage.py status`.
"""

import contextvars
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings

KINDS = ("plan", "plan_repair", "vision")

MESSAGES = {
    "disabled": "AI अभी बंद है। (The AI is switched off for now.)",
    "expired": "AI क्रेडिट की अवधि समाप्त हो गई है। (The AI credits have expired.)",
    "exhausted": "AI क्रेडिट समाप्त हो गए हैं। (The AI credits are used up.)",
    "reserve": "बचे हुए AI क्रेडिट मूल्यांकन अवधि के लिए सुरक्षित हैं। (The remaining AI credits are kept for the evaluation period.)",
    "global_daily": "आज के लिए डेमो की AI सीमा पूरी हो गई, कल फिर चलेगा। (The demo has reached its AI limit for today. It resets tomorrow.)",
    "school_daily": "आज के लिए आपके स्कूल की AI सीमा पूरी हो गई। (Your school has reached today's AI limit.)",
    "teacher_daily": "आज के लिए आपकी AI सीमा पूरी हो गई, कल फिर कोशिश करें। (You have reached today's AI limit. Please try again tomorrow.)",
}


class AICapReached(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        self.message = MESSAGES[reason]
        super().__init__(self.message)


_operator = contextvars.ContextVar("ai_operator", default=False)
_ctx = contextvars.ContextVar("ai_ctx", default=None)
_warned = False
NOW_OVERRIDE = None          # tests set this to a datetime to move "now"


def operator_mode(on: bool = True):
    """For the team's own scripts (the batch run): the daily caps do not apply, but the reserve rule and the total still do."""
    _operator.set(on)


def bind(db, teacher_id):
    """Remember who is paying, so a helper that has no database handle (the repair call) can meter and be capped too."""
    return _ctx.set((db, teacher_id))


# ── money ───────────────────────────────────────────────────────────────────

def tokens_of(usage) -> tuple:
    """(input, output) from an SDK usage object or a dict; anything else counts as zero rather than breaking a request."""
    def get(name):
        v = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
        return int(v) if isinstance(v, (int, float)) else 0
    return get("input_tokens"), get("output_tokens")


def cost_usd(tokens_in: int, tokens_out: int) -> float:
    s = get_settings()
    return (tokens_in * s.ai_price_input_per_mtok + tokens_out * s.ai_price_output_per_mtok) / 1_000_000


_IST = timezone(timedelta(hours=5, minutes=30), "IST")        # India has no daylight saving, so a fixed offset is exact
_tz_warned = False


def _tz():
    """The time zone that decides what 'today' means. Windows has no time zone database unless the `tzdata` package is installed, and the
    name would then not be found; India's offset is fixed, so we fall back to it. Any other missing zone falls back to UTC, with a warning."""
    global _tz_warned
    name = get_settings().ai_timezone
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        if name in ("Asia/Kolkata", "Asia/Calcutta", "IST"):
            return _IST
        if not _tz_warned:
            print(f"   WARNING: time zone {name!r} not found (pip install tzdata): using UTC for the AI budget's daily caps.")
            _tz_warned = True
        return timezone.utc


def now() -> datetime:
    return NOW_OVERRIDE or datetime.now(_tz())


def day_start() -> datetime:
    """The start of today, in India time, as an aware datetime."""
    return datetime.combine(now().astimezone(_tz()).date(), time.min, tzinfo=_tz())


def available_usd(spent_total: float, today: date) -> float:
    """What can still be spent NOW: the allocation, less what is spent, less what must be held back (the reserve, then the margin)."""
    s = get_settings()
    remaining = s.ai_allocation_usd - s.ai_spend_offset_usd - spent_total
    hold = s.ai_reserve_usd if today < date.fromisoformat(s.ai_reserve_from) else s.ai_final_margin_usd
    return remaining - hold


# ── the meter ───────────────────────────────────────────────────────────────

async def _spent(db, where: str = "TRUE", *args) -> float:
    row = await db.fetchrow(f"SELECT COALESCE(sum(input_tokens), 0) AS i, COALESCE(sum(output_tokens), 0) AS o FROM ai_usage WHERE {where}", *args)
    return cost_usd(row["i"], row["o"])


def _warn_missing():
    global _warned
    if not _warned:
        print("   WARNING: the AI meter table is missing (db/schema/10_ai_usage.sql): calls are NOT being metered or capped.")
        _warned = True


async def check(db, teacher_id, kind: str = "plan"):
    """Raises AICapReached if this call must not be made. Called BEFORE every paid call."""
    s = get_settings()
    if not s.ai_enabled:
        raise AICapReached("disabled")
    today = now().astimezone(_tz()).date()
    if today > date.fromisoformat(s.ai_credit_expires):
        raise AICapReached("expired")
    try:
        spent_total = await _spent(db)
        if s.ai_allocation_usd - s.ai_spend_offset_usd - spent_total <= 1e-6:      # a tolerance: float arithmetic leaves ~1e-16 where 0 is meant
            raise AICapReached("exhausted")
        if available_usd(spent_total, today) <= 0:
            raise AICapReached("reserve" if today < date.fromisoformat(s.ai_reserve_from) else "exhausted")
        if _operator.get():
            return
        since = day_start()
        if await _spent(db, "created_at >= $1", since) >= s.ai_cap_global_daily_usd:
            raise AICapReached("global_daily")
        who = await db.fetchrow("SELECT school_id, pin_fixed FROM teachers WHERE id = $1", teacher_id) if teacher_id else None
        if who:
            if await _spent(db, "school_id = $1 AND created_at >= $2", who["school_id"], since) >= s.ai_cap_school_daily_usd:
                raise AICapReached("school_daily")
            cap = s.ai_cap_shared_demo_daily_usd if who["pin_fixed"] else s.ai_cap_teacher_daily_usd
            if await _spent(db, "teacher_id = $1 AND created_at >= $2", teacher_id, since) >= cap:
                raise AICapReached("teacher_daily")
    except AICapReached:
        raise
    except Exception as e:
        if e.__class__.__name__ in ("UndefinedTableError", "UndefinedColumnError"):
            _warn_missing()
            return
        raise


async def record(db, teacher_id, kind: str, model: str, usage):
    """Meter a call that was made. Never lets a metering problem break the request that was already paid for."""
    tin, tout = tokens_of(usage)
    try:
        school_id = await db.fetchval("SELECT school_id FROM teachers WHERE id = $1", teacher_id) if teacher_id else None
        await db.execute("INSERT INTO ai_usage (teacher_id, school_id, kind, model, input_tokens, output_tokens, est_cost_usd) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                         teacher_id, school_id, kind, model, tin, tout, round(cost_usd(tin, tout), 4))
    except Exception as e:
        if e.__class__.__name__ in ("UndefinedTableError", "UndefinedColumnError"):
            _warn_missing()
        else:
            print(f"   (AI usage not recorded: {type(e).__name__})")


async def guard(kind: str):
    """check() for a helper that has no database handle: uses whoever bind() named."""
    ctx = _ctx.get()
    if ctx:
        await check(ctx[0], ctx[1], kind)


async def record_ctx(kind: str, model: str, usage):
    ctx = _ctx.get()
    if ctx:
        await record(ctx[0], ctx[1], kind, model, usage)


# ── recorded plans ──────────────────────────────────────────────────────────

def sample_dir() -> Path:
    custom = get_settings().sample_plans_dir
    return Path(custom) if custom else Path(__file__).resolve().parents[3] / "db" / "seeds" / "sample_plans"


def should_keep_sample(*, save_samples: bool, stub: bool, served_from: str, warnings: list, accept_warnings: bool) -> bool:
    """The batch tool's rule for keeping a generated plan as a recorded sample: only a plan from the REAL model, and only a clean one unless a person has chosen to keep plans with warnings."""
    return bool(save_samples and not stub and served_from == "ai" and (not warnings or accept_warnings))


def raw_plan_record(plan: dict, warnings: list, stub: bool = False) -> dict:
    """What the batch tool writes for EVERY plan it generates (docs/batch/plans/<skill>.json), kept or not as a recorded sample: the plan, its warnings, and no reviewer yet. A plan paid for is never lost.
    A plan made by the fake model is marked `_stub`, so it can never be mistaken for a real one."""
    out = mark_for_review(plan, warnings or [])
    out.setdefault("_reviewed_by", None)
    if stub:
        out["_stub"] = True
    return out


def strip_private(plan):
    """Keys that begin with an underscore are notes for the people who review a recorded plan (_recorded_warnings, _reviewed_by). They never reach a teacher."""
    return {k: v for k, v in plan.items() if not str(k).startswith("_")} if isinstance(plan, dict) else plan


def mark_for_review(plan: dict, warnings: list) -> dict:
    """A recorded plan that still carries warnings (a worksheet question that echoes the lesson, say) is kept only with those warnings written inside the file and nobody's name against them yet:
    `_reviewed_by` is filled in by the person who read it (the gate refuses to pass until it is). A plan with no warnings is saved as it is."""
    out = dict(plan)
    if warnings:
        out["_recorded_warnings"] = [str(w) for w in warnings]
        out["_reviewed_by"] = None
    return out


def sample_plan_for(competency_id: str):
    """A recorded plan for this skill (a real earlier output), or None. It is replayed through the same checks and repairs."""
    path = sample_dir() / f"{competency_id}.json"
    if not path.is_file():
        return None
    try:
        return strip_private(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None


def sample_skills() -> list:
    d = sample_dir()
    return sorted(p.stem for p in d.glob("*.json")) if d.is_dir() else []


# ── reporting ───────────────────────────────────────────────────────────────

async def status(db) -> dict:
    s = get_settings()
    today = now().astimezone(_tz()).date()
    metered = await _spent(db)
    spent = s.ai_spend_offset_usd + metered
    since = day_start()
    by_kind = {r["kind"]: (r["n"], cost_usd(r["i"], r["o"])) for r in await db.fetch(
        "SELECT kind, count(*) AS n, COALESCE(sum(input_tokens), 0) AS i, COALESCE(sum(output_tokens), 0) AS o FROM ai_usage GROUP BY kind")}
    days = [(r["d"], r["n"], cost_usd(r["i"], r["o"])) for r in await db.fetch(
        """SELECT (created_at AT TIME ZONE $1)::date AS d, count(*) AS n, sum(input_tokens) AS i, sum(output_tokens) AS o
           FROM ai_usage GROUP BY 1 ORDER BY 1 DESC LIMIT 10""", s.ai_timezone)]
    top = [(str(r["teacher_id"])[:8], r["n"], cost_usd(r["i"], r["o"])) for r in await db.fetch(
        """SELECT teacher_id, count(*) AS n, sum(input_tokens) AS i, sum(output_tokens) AS o FROM ai_usage WHERE created_at >= $1
           GROUP BY teacher_id ORDER BY sum(input_tokens) * $2 + sum(output_tokens) * $3 DESC LIMIT 5""", since, s.ai_price_input_per_mtok, s.ai_price_output_per_mtok)]
    return {"allocation": s.ai_allocation_usd, "offset": s.ai_spend_offset_usd, "metered": metered, "spent": spent, "remaining": s.ai_allocation_usd - spent,
            "pct": 100 * spent / s.ai_allocation_usd if s.ai_allocation_usd else 0, "available_now": available_usd(metered, today),
            "reserve_active": today < date.fromisoformat(s.ai_reserve_from), "today": await _spent(db, "created_at >= $1", since),
            "by_kind": by_kind, "days": days, "top_today": top, "calls": sum(n for n, _ in by_kind.values())}
