"""
Watchtower AI - Data Drift & Quality Monitoring API
Main FastAPI application entry point
"""
from fastapi import FastAPI
from app.routes import auth, get_api, projects, ingest, data_quality, data_validation, drift_detection
from app.database.connection import init_db

app = FastAPI(
    title="Watchtower AI API",
    description="Advanced data drift detection and quality monitoring system",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()

# Include routers
app.include_router(auth.router)
app.include_router(get_api.router)
app.include_router(projects.router)
app.include_router(ingest.router, prefix="/ingest")
app.include_router(data_quality.router)
app.include_router(data_validation.router)
app.include_router(drift_detection.router)

@app.on_event("startup")
async def startup_debugger():
    """Log registered routes on startup."""
    print("\n" + "="*60)
    print("Registered Routes:")
    print("="*60)
    for route in app.routes:
        methods = ','.join(route.methods) if hasattr(route, 'methods') else 'N/A'
        print(f"  {route.path:<40} [{methods}]")
    print("="*60 + "\n")

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"message": "Watchtower AI API is running", "status": "healthy"}
