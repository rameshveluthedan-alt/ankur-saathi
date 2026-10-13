"""
Ankur Saathi — FastAPI Application
Entry point. Configures lifespan (DB pool), CORS, and mounts the API router.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_pool, close_pool
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB pool. Shutdown: close it."""
    settings = get_settings()
    print(f"🌱 {settings.app_name} v{settings.app_version} starting...")
    print(f"   Database: {settings.database_url.split('@')[-1]}")  # Don't log credentials
    print(f"   Claude model: {settings.claude_model}")
    
    await create_pool()
    print("   Database pool ready.")
    
    yield  # App is running
    
    await close_pool()
    print("🌱 Ankur Saathi shut down.")


app = FastAPI(
    title="Ankur Saathi API",
    description="AI-powered daily differentiated instruction for FLN classrooms",
    version=get_settings().app_version,
    lifespan=lifespan,
)

# CORS — allow PWA and dev servers
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes under /api
app.include_router(router, prefix="/api")


# Health check (no auth, no DB — for monitoring)
@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }
