"""
When the AI provider itself refuses or cannot be reached (its own usage limit, an expired key, an outage), the plan route answers 503 with the code
'ai_unavailable' and a plain message, so the app can offer the quick plan. Before, it answered a bare 500 that the app showed as "the server isn't answering".
No database and no API key needed: the plan service and the database are replaced.

    python backend/tests/test_ai_unavailable.py
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import asyncio
import contextlib
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import anthropic
import httpx
from fastapi import HTTPException
from app.api import routes
from app.models.schemas import GeneratePlanRequest
from app.services import ai_budget, plan_service

failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   {detail}"))
    if not ok:
        failures.append(name)


class FakeDb:
    async def fetchval(self, *a, **k):
        return None                                   # no plan exists for this day


@contextlib.asynccontextmanager
async def fake_get_db():
    yield FakeDb()


routes.get_db = fake_get_db
REQ = GeneratePlanRequest(competency_id="N2.3.2", domain_id="numeracy", plan_date="2026-11-24", session_minutes=60)
RESP = lambda code: httpx.Response(code, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))


def run(exc):
    async def boom(*a, **k):
        raise exc
    plan_service.generate_dainik_yojana = boom
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):       # the route prints the real reason (a traceback) to the server log: not wanted in this test's output
            asyncio.run(routes.generate_plan(REQ, "T1"))
    except HTTPException as e:
        return e
    return None


cases = [
    ("the provider's own usage limit (400, as on 24 Nov)", anthropic.BadRequestError("You have reached your specified workspace API usage limits.", response=RESP(400), body=None)),
    ("an expired or wrong key (401)", anthropic.AuthenticationError("invalid x-api-key", response=RESP(401), body=None)),
    ("a rate limit (429)", anthropic.RateLimitError("rate limited", response=RESP(429), body=None)),
    ("the provider is down (500)", anthropic.InternalServerError("overloaded", response=RESP(500), body=None)),
    ("the provider cannot be reached", anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))),
]
for label, exc in cases:
    e = run(exc)
    d = e.detail if e else None
    check(f"{label}: 503 'ai_unavailable' with the plain message", bool(e) and e.status_code == 503 and isinstance(d, dict) and d.get("code") == "ai_unavailable" and d.get("message") == ai_budget.PROVIDER_UNAVAILABLE, (e.status_code, d) if e else "no error raised")
    check(f"{label}: the provider's own text is NOT sent to the teacher", bool(e) and "usage limit" not in str(d) and "x-api-key" not in str(d), d)

e = run(ValueError("The model's reply was not valid JSON"))
check("any other failure is still a 500 (a real fault is not hidden as 'the AI is unavailable')", bool(e) and e.status_code == 500, e.status_code if e else "no error raised")
e = run(ai_budget.AICapReached("teacher_daily"))
check("our own AI limit still answers 429 'ai_cap' as before", bool(e) and e.status_code == 429 and e.detail["code"] == "ai_cap", e.detail if e else "no error raised")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("ALL PASSED")
