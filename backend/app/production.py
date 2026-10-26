"""
The production entry point:   uvicorn app.production:app --host 0.0.0.0 --port $PORT

It wraps the application in app/main.py WITHOUT changing it, so nothing hand-edited there is touched. It adds:
  * the database connection through Cloud SQL's socket (DB_HOST=/cloudsql/PROJECT:REGION:INSTANCE);
  * the rate limit on sign-in, registration and PIN change (app/rate_limit.py);
  * a few security headers;
  * no public API documentation pages (/docs, /redoc, /openapi.json);
  * the built app, served from the same address as the API (app/static_site.py).

See deploy/DEPLOY.md.
"""

import os
from urllib.parse import quote


def _prepare_database_environment():
    """On Cloud Run the database is a unix socket directory, not a host and port. Code that wants one connection URL gets one with the
    password percent-encoded; code that reads DB_HOST, DB_USER and the rest separately (asyncpg treats a host starting with / as a socket
    directory) works as it is."""
    host = os.environ.get("DB_HOST", "")
    if host.startswith("/") and not os.environ.get("DATABASE_URL"):
        user = quote(os.environ.get("DB_USER", "postgres"), safe="")
        password = os.environ.get("DB_PASSWORD", "")
        auth = user + (":" + quote(password, safe="") if password else "")
        os.environ["DATABASE_URL"] = f"postgresql://{auth}@/{os.environ.get('DB_NAME', 'ankur_saathi')}?host={host}"


_prepare_database_environment()

from app.main import app                                       # noqa: E402  (after the environment is prepared: the settings are read on import)
from app.rate_limit import RateLimitMiddleware, SecurityHeadersMiddleware   # noqa: E402
from starlette.middleware.gzip import GZipMiddleware                         # noqa: E402
from app.static_site import mount_pwa                          # noqa: E402

# A settings mistake that only shows up in the cloud: say so at startup, in the log, where it is easy to see
from app.core.config import get_settings                       # noqa: E402
_s = get_settings()
if _s.claude_max_tokens < 16000:
    print(f"   WARNING: CLAUDE_MAX_TOKENS is {_s.claude_max_tokens}. A plan needs about 13,000 output tokens, so plans will be CUT OFF and fail. "
          f"Set CLAUDE_MAX_TOKENS (your backend/.env has it) in deploy/cloudrun-env.generated.yaml.")
if not (os.environ.get("ANTHROPIC_API_KEY") or _s.anthropic_api_key):         # the key may come from the environment (the cloud) or from backend/.env (a local run)
    print("   WARNING: ANTHROPIC_API_KEY is not set (neither in the environment nor in .env): plan generation and photo analysis will fail.")
if not _s.debug and not os.environ.get("SESSION_SECRET"):
    print("   WARNING: SESSION_SECRET is not set.")

DOC_PATHS = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) not in DOC_PATHS]

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)                         # added last, so it runs first
app.add_middleware(GZipMiddleware, minimum_size=1000)           # outermost: everything above is compressed for a browser that asks for it (a phone on a slow connection sends a third of the bytes)
mount_pwa(app)                                                  # after every API route: the first matching route wins
