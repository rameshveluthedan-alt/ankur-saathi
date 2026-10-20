"""
Serve the built app (pwa/dist) from the same address as the API.

One address means one HTTPS origin: no cross-origin settings, and no proxy in front of the API with its own time limit (Firebase Hosting's
is 60 seconds, shorter than a plan takes). The API keeps answering under /api.

  * a real file in the build (a script, an icon, the manifest) is sent as it is;
  * any other path is an app screen, so the app's index.html is sent and the app's own router takes over;
  * an unknown /api path is a real 404 in JSON, never the app's page (that would hide mistakes from the app and from monitoring);
  * a missing FILE (a path whose last part has an extension: an icon, a script, a map) is a real 404 too. Answering it with the app's page would
    hand a browser HTML where it asked for an image, and nobody would see an error. Only a path without an extension is an app screen;
  * a path that tries to climb out of the folder (../../etc/passwd) never reaches the file system.

Caching: files with a hash in their name (assets/) are cached for a year; the page itself, the service worker and the manifest are never
cached by the browser, so that a new deployment reaches people the next time they open the app.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

NO_CACHE = {"Cache-Control": "no-cache"}
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}
DAY = {"Cache-Control": "public, max-age=86400"}
NEVER_CACHE_NAMES = ("sw.js", "registerSW.js", "manifest.webmanifest", "index.html")


def default_dist() -> Path:
    # backend/app/static_site.py: parents[0] is app/, parents[1] is backend/, parents[2] is the repository root
    return Path(__file__).resolve().parents[2] / "pwa" / "dist"


def cache_headers_for(relative: str) -> dict:
    name = relative.rsplit("/", 1)[-1]
    if relative.startswith("assets/"):
        return IMMUTABLE
    if name in NEVER_CACHE_NAMES or name.startswith("workbox-"):
        return NO_CACHE
    return DAY


def mount_pwa(app: FastAPI, dist: str = "") -> bool:
    """Add the catch-all that serves the app. It must be added AFTER every API route (the first matching route wins)."""
    folder = Path(dist or os.environ.get("PWA_DIST", "") or default_dist())
    index = folder / "index.html"
    if not index.is_file():
        print(f"   WARNING: no built app at {folder}: only the API is served (build it with `npm run build` in pwa/).")
        return False
    root = folder.resolve()

    async def serve_app(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        if full_path:
            candidate = (root / full_path).resolve()
            if root in candidate.parents and candidate.is_file():           # never outside the build folder
                return FileResponse(candidate, headers=cache_headers_for(full_path))
            if "." in full_path.rstrip("/").rsplit("/", 1)[-1]:              # looks like a file, and it is not there
                return JSONResponse({"detail": "Not found"}, status_code=404)
        return FileResponse(index, headers=NO_CACHE)

    # GET and HEAD: monitors and some browsers ask with HEAD, and FastAPI's get() alone would answer 405
    app.add_api_route("/{full_path:path}", serve_app, methods=["GET", "HEAD"], include_in_schema=False)
    print(f"   Serving the app from {root}")
    return True
