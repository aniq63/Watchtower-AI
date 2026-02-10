# app/routes/ingest.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database.connection import get_db
from app.database import models
from app.services.feature_monitoring.ingestion_service import IngestionService

router = APIRouter(tags=["Ingest"])

async def get_current_project_by_key(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate project using Bearer token (API key or access token).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.split(" ")[1]
    
    # Check if it's a project access token
    result = await db.execute(
        select(models.Project).where(models.Project.access_token == token)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        # Check if it's a company API key
        result = await db.execute(
            select(models.Company).where(models.Company.api_key == token)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=401, detail="Invalid API key or access token")
            
        # If it's a company API key, we still need the project_name from payload to identify the project
        # This will be handled in the route if project is None
        return {"company_id": company.company_id, "project": None}
        
    return {"company_id": project.company_id, "project": project}

@router.post("")
async def ingest_data(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_project_by_key)
):
    payload = await request.json()

    project_name = payload.get("project_name")
    features = payload.get("features")
    event_time_str = payload.get("event_time")
    stage = payload.get("stage", "model_input")  # Extract stage from payload
    metadata = payload.get("metadata", {})

    if not features:
        raise HTTPException(status_code=400, detail="features are required")

    project = auth["project"]
    if not project:
        if not project_name:
            raise HTTPException(status_code=400, detail="project_name is required when using company API key")
            
        result = await db.execute(
            select(models.Project).where(
                models.Project.project_name == project_name,
                models.Project.company_id == auth["company_id"]
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    # Validate stage against project config
    from app.database.models import FeatureConfig
    config_result = await db.execute(
        select(FeatureConfig).where(FeatureConfig.project_id == project.project_id)
    )
    project_config = config_result.scalar_one_or_none()
    
    if project_config:
        if stage != project_config.monitoring_stage:
            raise HTTPException(
                status_code=400,
                detail=f"Stage mismatch: Project '{project.project_name}' is configured for '{project_config.monitoring_stage}' stage, but received '{stage}'"
            )

    # Parse event_time
    event_time = datetime.utcnow()
    if event_time_str:
        try:
            event_time = datetime.fromisoformat(event_time_str)
        except ValueError:
            pass


    # Call ingestion service
    ingestion = IngestionService(db)
    result = await ingestion.ingest(project.project_id, features, stage, event_time, metadata)

    return {"status": "success", "ingested_rows": result.get("rows_ingested")}


@router.post("/predictions")
async def ingest_predictions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(get_current_project_by_key)
):
    payload = await request.json()
    
    project_name = payload.get("project_name")
    predictions = payload.get("predictions")
    metrics = payload.get("metrics")
    model_type = payload.get("model_type")
    event_time_str = payload.get("event_time")
    metadata = payload.get("metadata", {})

    if not predictions:
        raise HTTPException(status_code=400, detail="predictions are required")

    project = auth["project"]
    if not project:
        # Same logic as above for looking up project by name if using company key
        if not project_name:
            raise HTTPException(status_code=400, detail="project_name is required when using company API key")
            
        result = await db.execute(
            select(models.Project).where(
                models.Project.project_name == project_name,
                models.Project.company_id == auth["company_id"]
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    # Parse event_time
    event_time = datetime.utcnow()
    if event_time_str:
        try:
            event_time = datetime.fromisoformat(event_time_str)
        except ValueError:
            pass

    # Call ingestion service
    ingestion = IngestionService(db)
    result = await ingestion.ingest_predictions(
        project_id=project.project_id,
        predictions=predictions,
        metrics=metrics,
        model_type=model_type,
        event_time=event_time,
        metadata=metadata
    )
    
    return {"status": "success", "result": result}


