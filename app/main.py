from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.config import get_settings
from app.api import health, auth, organizations, onboarding, dashboard, agents, workflows
from app.database import engine, Base

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)


def _ensure_columns() -> None:
    """Add columns introduced after a database was first created.

    `create_all` only creates missing tables — it never alters existing
    ones, so a new model column would break every pre-existing database.
    This adds any missing *nullable* column via ALTER TABLE. Limitations:
    no constraints/defaults/FK are carried over (add those via a real
    migration tool if a column ever needs them), and non-nullable columns
    without server defaults are not supported.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing or not col.nullable:
                    continue
                col_type = col.type.compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}')
                )


_ensure_columns()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Agentic Workflow Platform for Enterprise Business Automation",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

def cors_origins(settings) -> list:
    """Explicit browser origins for CORS; a wildcard is dropped.

    `allow_origins=["*"]` with `allow_credentials=True` is invalid: the
    browser is told `Access-Control-Allow-Origin: *` plus
    `Access-Control-Allow-Credentials: true`, a pair it must reject, and
    preflight then echoes *any* origin. Configuring the origins explicitly
    keeps credentialed requests working (bearer-token SPA, cookie flows) while
    an accidental `CORS_ORIGINS=*` fails closed instead of silently allowing
    everyone.
    """
    configured = settings.cors_origin_list
    allowed = [origin for origin in configured if origin != "*"]
    if len(allowed) != len(configured):
        logging.getLogger(__name__).warning(
            "CORS_ORIGINS contained '*', which cannot be combined with "
            "credentials; ignoring it. List explicit origins instead."
        )
    return allowed


# CORS middleware — explicit origins only (see cors_origins above)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(settings),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(organizations.router, prefix="/api/orgs", tags=["Organizations"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])

# Static files - only mount if directory exists
static_path = os.path.join(os.path.dirname(__file__), settings.static_dir)
if os.path.exists(static_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_path, "assets")), name="assets")


@app.get("/")
async def root():
    """Serve the main index.html for the landing page."""
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=404,
        content={"message": "Frontend not built. Run 'npm run build' in webapp directory."}
    )


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "version": settings.app_version}


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Serve index.html for client-side routes so deep links and refresh
    work (React Router has no server-side routes of its own). API paths
    keep their JSON 404."""
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Not found"})
