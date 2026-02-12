from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database.connection import get_db
from app.database import models, schemas
from app.utils.auth import verify_api_key
from app.utils.dependencies import require_project_type
from typing import List

router = APIRouter(
    prefix="/prediction",
    tags=["Prediction Monitoring"]
)

# Dependency Factory
require_prediction_project = require_project_type("prediction_monitoring")

# =============================================================================
# CONFIGURATION
# =============================================================================

@router.get("/config/{project_id}", response_model=schemas.PredictionConfigResponse)
async def get_prediction_config(
    project_id: int,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Get prediction monitoring configuration."""
    result = await db.execute(
        select(models.PredictionConfig).where(
            models.PredictionConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        return models.PredictionConfig(
            project_id=project_id,
            baseline_batch_size=1000,
            monitor_batch_size=500
        )
        
    return config

@router.put("/config/{project_id}", response_model=schemas.PredictionConfigResponse)
async def update_prediction_config(
    project_id: int,
    config_update: schemas.PredictionConfigCreate,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Update prediction monitoring configuration."""
    result = await db.execute(
        select(models.PredictionConfig).where(
            models.PredictionConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.PredictionConfig(project_id=project_id)
        db.add(config)
    
    config.baseline_batch_size = config_update.baseline_batch_size
    config.monitor_batch_size = config_update.monitor_batch_size
    
    await db.commit()
    await db.refresh(config)
    return config

@router.get("/drift-config/{project_id}")
async def get_drift_config(
    project_id: int,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Get prediction drift configuration."""
    result = await db.execute(
        select(models.PredictionDriftConfig).where(
            models.PredictionDriftConfig.config_id == project_id # Assuming project_id mapping or separate lookup
        )
    )
    # Re-check models.py, PredictionDriftConfig has project_id foreign key
    result = await db.execute(
        select(models.PredictionDriftConfig).where(
            models.PredictionDriftConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        # Defaults
        return {
            "project_id": project_id,
            "mean_threshold": 0.1,
            "median_threshold": 0.1,
            "variance_threshold": 0.2,
            "ks_pvalue_threshold": 0.05,
            "psi_threshold": [0.1, 0.25],
            "psi_bins": 10,
            "min_samples": 50,
            "alert_threshold": 2,
            "model_based_drift_threshold": 0.50
        }
    
    return config

@router.put("/drift-config/{project_id}")
async def update_drift_config(
    project_id: int,
    config_update: schemas.PredictionDriftConfigCreate,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Update prediction drift configuration."""
    result = await db.execute(
        select(models.PredictionDriftConfig).where(
            models.PredictionDriftConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.PredictionDriftConfig(project_id=project_id)
        db.add(config)
    
    # Update fields from pydantic model
    config_data = config_update.model_dump(exclude_unset=True)
    for key, value in config_data.items():
        if hasattr(config, key):
             setattr(config, key, value)

    await db.commit()
    await db.refresh(config)
    return {"message": "Prediction drift configuration updated successfully", "config_id": config.config_id}


@router.get("/evaluation-config/{project_id}")
async def get_evaluation_config(
    project_id: int,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Get prediction evaluation configuration."""
    result = await db.execute(
        select(models.PredictionEvaluationConfig).where(
            models.PredictionEvaluationConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
         return {
            "project_id": project_id,
            "metric_thresholds": {},
            "min_samples": 50
        }
    
    return config

@router.put("/evaluation-config/{project_id}")
async def update_evaluation_config(
    project_id: int,
    config_update: schemas.PredictionEvaluationConfigCreate,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Update prediction evaluation configuration."""
    result = await db.execute(
        select(models.PredictionEvaluationConfig).where(
            models.PredictionEvaluationConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.PredictionEvaluationConfig(project_id=project_id)
        db.add(config)
    
    config.metric_thresholds = config_update.metric_thresholds
    config.min_samples = config_update.min_samples

    await db.commit()
    await db.refresh(config)
    return {"message": "Evaluation configuration updated successfully", "config_id": config.config_id}

# =============================================================================
# RESULTS
# =============================================================================

@router.get("/drift/{project_id}")
async def get_prediction_drift(
    project_id: int,
    limit: int = 10,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Get prediction drift history."""
    result = await db.execute(
        select(models.PredictionDrift)
        .where(models.PredictionDrift.project_id == project_id)
        .order_by(desc(models.PredictionDrift.timestamp))
        .limit(limit)
    )
    records = result.scalars().all()
    
    return {
        "project_id": project_id,
        "results": records
    }

@router.get("/evaluation/{project_id}")
async def get_prediction_evaluation(
    project_id: int,
    limit: int = 10,
    project: models.Project = Depends(require_prediction_project),
    db: AsyncSession = Depends(get_db)
):
    """Get prediction evaluation metrics history."""
    result = await db.execute(
        select(models.PredictionMetrics)
        .where(models.PredictionMetrics.project_id == project_id)
        .order_by(desc(models.PredictionMetrics.timestamp))
        .limit(limit)
    )
    records = result.scalars().all()
    
    return {
        "project_id": project_id,
        "results": records
    }
