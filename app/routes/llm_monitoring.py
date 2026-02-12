"""
LLM Monitoring Routes - Handles LLM interaction ingestion and monitoring endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from app.database import models, schemas
from app.database.connection import get_db
from app.services.llm_monitoring.llm_monitor_service import LLMMonitorService
from app.utils.auth import verify_api_key
from app.utils.dependencies import require_project_type
from pydantic import BaseModel, Field

router = APIRouter(prefix="/llm", tags=["llm_monitoring"])

# Dependency Factory
require_llm_project = require_project_type("llm_monitoring")

class LLMInteractionRequest(BaseModel):
    project_name: str
    input_text: str
    response_text: str
    metadata: dict = None

class LLMConfigUpdate(BaseModel):
    baseline_batch_size: int = Field(..., gt=0)
    monitor_batch_size: int = Field(..., gt=0)
    toxicity_threshold: float = Field(..., ge=0.0, le=1.0)
    token_drift_threshold: float = Field(..., ge=0.0)

# Note: Ingest endpoint uses POST /ingest/llm in original. 
# Providing backward comp or moving? User asked for /llm/...
# I will keep a separate route for ingest if needed or just put it here.
# The user request listed `/llm/config`, `/llm/evaluation`, `/llm/usage`.
# I will expose ingest at `/ingest` (legacy) inside main.py? 
# Or just here as `/ingest` (so `/llm/ingest`? No, original was `/ingest/llm`).
# I will keep the ingest logic but maybe adjust path or keeping it compatible.
# For now, I'll put it at `/ingest` (relative to router `/llm` -> `/llm/ingest`).
# The original was `prefix="/ingest"` -> `/ingest/llm`.
# I'll use `/ingest` here so it becomes `/llm/ingest`. 
# Wait, this breaks `/ingest/llm` if I mount this router at /llm.
# I will handle ingest separately or just accept the path change. 
# User request "backend routes: /llm/config...".
# I'll keep the ingest endpoint compatible-ish or just `/ingest` here.

@router.post("/ingest", status_code=201)
async def ingest_llm_interaction(
    request: LLMInteractionRequest,
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(verify_api_key)
):
    """Ingest LLM interaction."""
    # (Same logic as before, but ensure project type check?)
    # Since we look up by name, we can check type after lookup.
    
    project_result = await db.execute(
        select(models.Project).where(
            models.Project.project_name == request.project_name,
            models.Project.company_id == company_id
        )
    )
    project = project_result.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{request.project_name}' not found"
        )
        
    if project.project_type != "llm_monitoring":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project is not an LLM monitoring project"
        )

    # Ensure config exists
    config_result = await db.execute(
        select(models.LLMConfig).where(models.LLMConfig.project_id == project.project_id)
    )
    config = config_result.scalars().first()

    if not config:
        new_config = models.LLMConfig(
            project_id=project.project_id,
            baseline_batch_size=500,
            monitor_batch_size=250,
            toxicity_threshold=0.5,
            token_drift_threshold=0.15
        )
        db.add(new_config)
        await db.commit()

    service = LLMMonitorService()
    result = await service.log_interaction(
        project_id=project.project_id,
        input_text=request.input_text,
        response_text=request.response_text,
        metadata=request.metadata
    )

    return {
        "status": "success",
        "message": "LLM interaction logged successfully",
        "data": result
    }

@router.get("/interactions/{project_id}")
async def get_llm_interactions(
    project_id: int,
    limit: int = 50,
    offset: int = 0,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Get recent LLM interactions."""
    result = await db.execute(
        select(models.LLMMonitor)
        .where(models.LLMMonitor.project_id == project_id)
        .order_by(models.LLMMonitor.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    interactions = result.scalars().all()
    
    return {
        "project_id": project_id,
        "interactions": interactions,
        "count": len(interactions)
    }

@router.get("/drift/{project_id}")
async def get_llm_drift_history(
    project_id: int,
    limit: int = 10,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Get LLM drift detection history."""
    drift_result = await db.execute(
        select(models.LLMDrift).where(
            models.LLMDrift.project_id == project_id
        ).order_by(models.LLMDrift.created_at.desc()).limit(limit)
    )
    drifts = drift_result.scalars().all()

    return {
        "status": "success",
        "project_id": project_id,
        "drift_records": drifts
    }

@router.get("/baseline/{project_id}")
async def get_llm_baseline_info(
    project_id: int,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Get current LLM baseline information."""
    baseline_result = await db.execute(
        select(models.LLMBaseline).where(
            models.LLMBaseline.project_id == project_id
        )
    )
    baseline = baseline_result.scalars().first()

    monitor_result = await db.execute(
        select(models.LLMMonitorInfo).where(
            models.LLMMonitorInfo.project_id == project_id
        )
    )
    monitor = monitor_result.scalars().first()

    return {
        "status": "success",
        "project_id": project_id,
        "baseline": baseline,
        "monitor": monitor
    }

@router.get("/config/{project_id}")
async def get_llm_config(
    project_id: int,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Get LLM monitoring configuration."""
    result = await db.execute(
        select(models.LLMConfig).where(
            models.LLMConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        return {
            "status": "success",
            "project_id": project_id,
            "config": None,
            "message": "No configuration found"
        }
        
    return {
        "status": "success",
        "project_id": project_id,
        "config": config
    }

@router.put("/config/{project_id}")
async def update_llm_config(
    project_id: int,
    config_update: LLMConfigUpdate,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Update LLM monitoring configuration."""
    result = await db.execute(
        select(models.LLMConfig).where(
            models.LLMConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.LLMConfig(project_id=project_id)
        db.add(config)

    config.baseline_batch_size = config_update.baseline_batch_size
    config.monitor_batch_size = config_update.monitor_batch_size
    config.toxicity_threshold = config_update.toxicity_threshold
    config.token_drift_threshold = config_update.token_drift_threshold
    
    await db.commit()
    await db.refresh(config)

    return {
        "status": "success",
        "message": "LLM configuration updated successfully",
        "config": config
    }

# NEW CONFIG ENDPOINTS

@router.get("/config/drift/{project_id}")
async def get_llm_drift_config(
    project_id: int,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Get LLM drift configuration."""
    result = await db.execute(
        select(models.LLMDriftConfig).where(
            models.LLMDriftConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        return {
            "token_drift_threshold": 0.15,
            "embedding_drift_threshold": 0.2
        }
    return config

@router.put("/config/drift/{project_id}")
async def update_llm_drift_config(
    project_id: int,
    config_update: schemas.LLMDriftConfigCreate,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Update LLM drift configuration."""
    result = await db.execute(
        select(models.LLMDriftConfig).where(
            models.LLMDriftConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.LLMDriftConfig(project_id=project_id)
        db.add(config)
        
    config.token_drift_threshold = config_update.token_drift_threshold
    config.embedding_drift_threshold = config_update.embedding_drift_threshold
    
    await db.commit()
    await db.refresh(config)
    return config

@router.get("/config/evaluation/{project_id}")
async def get_llm_eval_config(
    project_id: int,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Get LLM evaluation configuration."""
    result = await db.execute(
        select(models.LLMEvaluationConfig).where(
            models.LLMEvaluationConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        return {
            "toxicity_threshold": 0.5,
            "hallucination_threshold": 0.5,
            "relevance_threshold": 0.7
        }
    return config

@router.put("/config/evaluation/{project_id}")
async def update_llm_eval_config(
    project_id: int,
    config_update: schemas.LLMEvaluationConfigCreate,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Update LLM evaluation configuration."""
    result = await db.execute(
        select(models.LLMEvaluationConfig).where(
            models.LLMEvaluationConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.LLMEvaluationConfig(project_id=project_id)
        db.add(config)
        
    config.toxicity_threshold = config_update.toxicity_threshold
    config.hallucination_threshold = config_update.hallucination_threshold
    config.relevance_threshold = config_update.relevance_threshold
    
    await db.commit()
    await db.refresh(config)
    return config

@router.get("/evaluation/{project_id}")
async def get_llm_evaluation(
    project_id: int,
    limit: int = 50,
    project: models.Project = Depends(require_llm_project),
    db: AsyncSession = Depends(get_db)
):
    """Get LLM evaluation metrics (via interactions)."""
    # Return interactions that have evaluation metrics
    result = await db.execute(
        select(models.LLMMonitor)
        .where(
            models.LLMMonitor.project_id == project_id
            # Assuming we want all, or filter where llm_judge_metrics is not null if we had sql filter
        )
        .order_by(models.LLMMonitor.created_at.desc())
        .limit(limit)
    )
    interactions = result.scalars().all()
    
    return {
        "project_id": project_id,
        "evaluations": [
            {
                "id": i.id,
                "created_at": i.created_at,
                "is_toxic": i.is_toxic,
                "metrics": i.llm_judge_metrics,
                "response_length": i.response_token_length
            }
            for i in interactions
        ]
    }
