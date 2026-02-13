"""
Watchtower AI - Data Drift & Quality Monitoring API
Main FastAPI application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from contextlib import asynccontextmanager
from app.database.connection import init_db
from app.routes import auth, get_api, projects, ingest, data_quality, data_validation, drift_detection, llm_monitoring, statistics, project_stats, feature_monitoring, prediction_monitoring

# ... imports ...


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for the FastAPI application.
    Handles startup and shutdown logic.
    """
    # Startup: Initialize database tables
    await init_db()
    yield
    # Shutdown: Clean up resources if needed


app = FastAPI(
    title="Watchtower AI API",
    description="Advanced data drift detection and quality monitoring system",
    version="1.0.0",
    lifespan=lifespan
)

# ... middleware ...

# Include routers
app.include_router(auth.router)
app.include_router(get_api.router)
app.include_router(projects.router)
app.include_router(ingest.router, prefix="/ingest")
app.include_router(data_quality.router)
app.include_router(data_validation.router)
app.include_router(drift_detection.router)
app.include_router(llm_monitoring.router)
app.include_router(statistics.router)
app.include_router(project_stats.router)

# New Project-Type Specific Routers
app.include_router(feature_monitoring.router)
app.include_router(prediction_monitoring.router)

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint for API."""
    return {"message": "Watchtower AI API is running", "status": "healthy"}

# Configure Jinja2 templates
frontend_path = Path(__file__).parent / "frontend"
templates = Jinja2Templates(directory=str(frontend_path / "templates"))

# Mount static files (CSS, JS, assets)
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

# Frontend Routes
@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def landing_page(request: Request):
    """Serve the landing page."""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/documentation", response_class=HTMLResponse, tags=["Frontend"])
async def documentation_page(request: Request):
    """Serve the documentation page."""
    return templates.TemplateResponse("documentation.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse, tags=["Frontend"])
async def dashboard(request: Request):
    """Serve the user dashboard (requires authentication)."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/project/{project_id}", response_class=HTMLResponse, tags=["Frontend"])
async def project_detail(request: Request, project_id: int):
    """Serve the project detail dashboard."""
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project_id": project_id
    })

@app.get("/project/{project_id}/drift/{drift_id}", response_class=HTMLResponse, tags=["Frontend"])
async def drift_detail(request: Request, project_id: int, drift_id: int):
    """Serve the drift run detail page."""
    return templates.TemplateResponse("drift_detail.html", {
        "request": request,
        "project_id": project_id,
        "drift_id": drift_id
    })

@app.get("/project/{project_id}/quality/{check_id}", response_class=HTMLResponse, tags=["Frontend"])
async def quality_detail(request: Request, project_id: int, check_id: int):
    """Serve the quality check detail page."""
    return templates.TemplateResponse("quality_detail.html", {
        "request": request,
        "project_id": project_id,
        "check_id": check_id
    })

@app.get("/project/{project_id}/llm/{query_id}", response_class=HTMLResponse, tags=["Frontend"])
async def llm_detail(request: Request, project_id: int, query_id: int):
    """Serve the LLM query detail page."""
    return templates.TemplateResponse("llm_detail.html", {
        "request": request,
        "project_id": project_id,
        "query_id": query_id
    })

