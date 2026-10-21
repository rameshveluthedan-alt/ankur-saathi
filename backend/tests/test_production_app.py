"""
The production entry point (app/production.py): the app and the API at one address, the rate limits, the security headers, the hidden API
documentation, and the Cloud SQL socket connection string. No database needed.

    cd backend && python tests/test_production_app.py
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import json
import os
import sys
import tempfile

# a build folder like the real one, and the environment of a Cloud Run container
DIST = tempfile.mkdtemp()
os.makedirs(os.path.join(DIST, "assets"))
for rel, text in {"index.html": "<html><body><div id=root></div>APP</body></html>", "assets/app.abc123.js": "console.log(1)", "sw.js": "// service worker",
                  "registerSW.js": "// register", "manifest.webmanifest": "{}", "ankur-saathi-icon.svg": "<svg/>", "workbox-1a2b.js": "// workbox"}.items():
    open(os.path.join(DIST, rel), "w", encoding="utf-8").write(text)
SECRET_FILE = os.path.join(os.path.dirname(DIST), "outside_secret.txt")
open(SECRET_FILE, "w").write("TOP SECRET OUTSIDE THE BUILD")
os.environ["AUTH_MODE"] = "enforce"          # this test is about sign-in being required: it must not inherit AUTH_MODE=off from the shell
os.environ.update(PWA_DIST=DIST, DB_HOST="/cloudsql/proj:asia-south1:inst", DB_USER="ankur", DB_PASSWORD="p@ss:w/rd#1", DB_NAME="ankur_saathi", DEBUG="true")
os.environ.pop("DATABASE_URL", None)

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prompts")]
from fastapi.testclient import TestClient
from app import production
from app.rate_limit import RateLimitMiddleware, client_address

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


c = TestClient(production.app, raise_server_exceptions=False)

print("the app is served from the same address as the API")
r = c.get("/")
check("/ is the app's page, never cached by the browser", r.status_code == 200 and "APP" in r.text and r.headers["cache-control"] == "no-cache")
r = c.get("/yojana")
check("an app screen (/yojana) gets the same page, so a reload or a shared link works", r.status_code == 200 and "APP" in r.text)
r = c.get("/assets/app.abc123.js")
check("a hashed file is sent as it is and cached for a year", r.status_code == 200 and "console.log" in r.text and "immutable" in r.headers["cache-control"])
check("the service worker, its helpers and the manifest are never cached (a new version must reach people)",
      all(c.get(p).headers["cache-control"] == "no-cache" for p in ("/sw.js", "/registerSW.js", "/manifest.webmanifest", "/workbox-1a2b.js")))
check("a MISSING file is a real 404, not the app's page (a missing icon must not look like a web page)",
      all(c.get(p).status_code == 404 and "APP" not in c.get(p).text for p in ("/ankur-saathi-icon-192.png", "/assets/nope.js", "/missing.map", "/a/b/c.css")))
check("...while a path without an extension is still an app screen", all(c.get(p).status_code == 200 and "APP" in c.get(p).text for p in ("/yojana", "/account", "/review/today", "/plan/2026-10-20")))
check("other files (the icon) are cached for a day", c.get("/ankur-saathi-icon.svg").headers["cache-control"] == "public, max-age=86400")

r = c.head("/sw.js")
check("a HEAD request (uptime monitors, some browsers) is answered with the same headers, not 405", r.status_code == 200 and r.headers["cache-control"] == "no-cache" and r.text == "")
check("HEAD on an app screen works too", c.head("/yojana").status_code == 200)

print("the API still answers, and a wrong API path is a real 404")
r = c.get("/health")
check("/health is the API's JSON, not the app's page", r.status_code == 200 and r.json().get("status") == "ok")
r = c.get("/api/not-a-route")
check("an unknown /api path is a JSON 404, never the app's page", r.status_code == 404 and "APP" not in r.text and r.json() == {"detail": "Not found"})
r = c.get("/api/children/names/abc")
check("an API route that needs sign-in answers 401 in JSON without a token", r.status_code == 401 and "APP" not in r.text)

print("nothing outside the build folder can be read")
for path in ("/../outside_secret.txt", "/%2e%2e/outside_secret.txt", "/..%2foutside_secret.txt", "/assets/../../outside_secret.txt", "//etc/passwd", "/%2fetc/passwd"):
    r = c.get(path)
    check(f"{path} does not leak a file", "TOP SECRET" not in r.text and "root:" not in r.text)

print("the API documentation is not public")
for path in ("/docs", "/redoc", "/openapi.json"):
    r = c.get(path)
    check(f"{path} is not the API documentation", "swagger" not in r.text.lower() and '"openapi"' not in r.text and "paths" not in r.text[:300])

print("security headers")
r = c.get("/")
check("on the app page", r.headers.get("x-content-type-options") == "nosniff" and r.headers.get("x-frame-options") == "DENY" and r.headers.get("referrer-policy") == "no-referrer" and "max-age" in r.headers.get("strict-transport-security", ""))
check("on an API answer too", c.get("/health").headers.get("x-content-type-options") == "nosniff")

print("the rate limit (the real app: 20 sign-ins a minute per address)")
ip = {"x-forwarded-for": "203.0.113.7"}
codes = [c.post("/api/auth/login", json={}, headers=ip).status_code for _ in range(22)]
check("the first 20 attempts reach the app (422: the body is empty); the 21st and 22nd are refused with 429", codes[:20] == [422] * 20 and codes[20:] == [429, 429], codes)
r = c.post("/api/auth/login", json={}, headers=ip)
msg = r.json()["detail"]
check("the refusal says why, in Hindi and English, and when to try again", r.status_code == 429 and msg["code"] == "rate_limited" and "कोशिश" in msg["message"] and "Too many" in msg["message"] and int(r.headers["retry-after"]) > 0)
check("another address is not affected", c.post("/api/auth/login", json={}, headers={"x-forwarded-for": "198.51.100.9"}).status_code == 422)
spoof = [c.post("/api/auth/login", json={}, headers={"x-forwarded-for": f"1.2.3.{i}, 203.0.113.7"}).status_code for i in range(3)]
check("writing a different address at the START of X-Forwarded-For does not escape the limit (only the last entry is trusted)", spoof == [429, 429, 429], spoof)
check("other routes are not limited", all(c.get("/health").status_code == 200 for _ in range(40)))
check("a GET on the sign-in path is not counted", c.get("/api/auth/login", headers=ip).status_code != 429)

print("the limiter on its own, with a controllable clock")
now = [0.0]
hits = []
async def echo(scope, receive, send):
    hits.append(1)
    await send({"type": "http.response.start", "status": 200, "headers": []}); await send({"type": "http.response.body", "body": b"ok"})
async def call(mw, method, path, xff="9.9.9.9"):
    out = []
    async def send(m): out.append(m)
    await mw({"type": "http", "method": method, "path": path, "headers": [(b"x-forwarded-for", xff.encode())], "client": ("10.0.0.1", 1)}, None, send)
    return out[0]["status"]
mw = RateLimitMiddleware(echo, rules=[("POST", "/api/auth/register", 5, 3600, "registration")], clock=lambda: now[0])
s = [asyncio.run(call(mw, "POST", "/api/auth/register")) for _ in range(6)]
check("registration: 5 an hour per address, the sixth is refused", s == [200] * 5 + [429], s)
now[0] = 3599
check("...still refused just before the hour is over", asyncio.run(call(mw, "POST", "/api/auth/register")) == 429)
now[0] = 3601
check("...and allowed again after it", asyncio.run(call(mw, "POST", "/api/auth/register")) == 200)
check("a trailing slash does not escape the limit", [asyncio.run(call(mw, "POST", "/api/auth/register/", "8.8.8.8")) for _ in range(6)][-1] == 429)
check("the address comes from the LAST entry (two proxies: the second from the right)", client_address({"headers": [(b"x-forwarded-for", b"evil, 5.5.5.5, 6.6.6.6")]}, hops=2) == "5.5.5.5"
      and client_address({"headers": [(b"x-forwarded-for", b"evil, 5.5.5.5")]}) == "5.5.5.5" and client_address({"headers": [], "client": ("10.1.1.1", 9)}) == "10.1.1.1")

print("a settings mistake that only shows up in the cloud is named in the log (each case starts the app fresh, in its own process)")
import subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
def start_log(**env):
    e = dict(os.environ); e.pop("CLAUDE_MAX_TOKENS", None); e.pop("ANTHROPIC_API_KEY", None); e.pop("SESSION_SECRET", None); e.update(env)
    code = f"import sys; sys.path[:0] = [{os.path.join(HERE, '..')!r}, {os.path.join(HERE, '..', '..', 'prompts')!r}]; import app.production"
    return subprocess.run([sys.executable, "-c", code], env=e, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
log = start_log(CLAUDE_MAX_TOKENS="8000", ANTHROPIC_API_KEY="k")
check("with the default 8000, the startup log says plans will be cut off", "CLAUDE_MAX_TOKENS is 8000" in log and "CUT OFF" in log, log[-200:])
check("with 24000 and a key, there is no such warning", "WARNING: CLAUDE_MAX_TOKENS" not in start_log(CLAUDE_MAX_TOKENS="24000", ANTHROPIC_API_KEY="k"))
check("a missing AI key is named", "ANTHROPIC_API_KEY is not set" in start_log(CLAUDE_MAX_TOKENS="24000") and "ANTHROPIC_API_KEY is not set" not in start_log(CLAUDE_MAX_TOKENS="24000", ANTHROPIC_API_KEY="k"))
check("a missing session secret is named when not in debug mode", "SESSION_SECRET is not set" in start_log(CLAUDE_MAX_TOKENS="24000", ANTHROPIC_API_KEY="k", DEBUG="false", SESSION_SECRET=""))
check("the cloud template sets all three model settings", all(f'{k}: "' in open(os.path.join(HERE, "..", "..", "deploy", "cloudrun-env.yaml"), encoding="utf-8").read() for k in ("CLAUDE_MAX_TOKENS", "CLAUDE_MODEL", "CLAUDE_VISION_MODEL")))

print("the database connection through Cloud SQL's socket")
url = os.environ.get("DATABASE_URL", "")
from urllib.parse import quote
check("a connection URL is made from the DB_* settings, with the password percent-encoded",
      url == "postgresql://ankur:" + quote(os.environ["DB_PASSWORD"], safe="") + "@/ankur_saathi?host=/cloudsql/proj:asia-south1:inst" and "@" not in url.split("@", 1)[0][len("postgresql://ankur:"):], url)
try:
    import inspect
    from asyncpg import connect_utils
    fn = connect_utils._parse_connect_dsn_and_args
    kw = {name: None for name in inspect.signature(fn).parameters}          # every keyword it wants, whichever asyncpg version is installed
    kw["dsn"] = url
    addrs, params = fn(**kw)
    check("asyncpg reads it as a unix socket directory in /cloudsql/..., not as a host name", any("/cloudsql/proj:asia-south1:inst" in str(a) for a in addrs), addrs)
    check("...with the right user, database and the password intact", params.password == "p@ss:w/rd#1" and params.user == "ankur" and params.database == "ankur_saathi", (params.user, params.database))
except Exception as e:                                                      # an asyncpg whose internals changed: say so loudly, do not pass silently
    failures.append(f"asyncpg's parser could not be exercised: {type(e).__name__}: {e}")
    print(f"  FAIL asyncpg's parser could not be exercised: {type(e).__name__}: {e}")
os.environ["DATABASE_URL"] = "postgresql://explicit@host/db"
production._prepare_database_environment()
check("an explicit DATABASE_URL is never overwritten", os.environ["DATABASE_URL"] == "postgresql://explicit@host/db")

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the app and API share one address, the limits and headers work, the docs are hidden, and the Cloud SQL connection string is right")
