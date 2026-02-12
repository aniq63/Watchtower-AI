from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database.connection import get_db
from app.database import models, schemas
from app.utils.auth import verify_api_key
from app.utils.dependencies import require_project_type
from app.services.feature_monitoring.data_drift import InputDataDriftMonitor
from app.services.feature_monitoring.model_based_data_drift import ModelBasedDriftMonitor
from app.services.feature_monitoring.baseline_manager import BaselineManager
from app.services.feature_monitoring.check_data_quality import FeatureQualityChecker
import pandas as pd

router = APIRouter(
    prefix="/feature",
    tags=["Feature Monitoring"]
)

# Dependency Factory
require_feature_project = require_project_type("feature_monitoring")

# =============================================================================
# CONFIGURATION
# =============================================================================

@router.get("/config/{project_id}", response_model=schemas.FeatureConfigResponse)
async def get_feature_config(
    project_id: int,
    project: models.Project = Depends(require_feature_project),
    db: AsyncSession = Depends(get_db)
):
    """Get feature monitoring configuration."""
    result = await db.execute(
        select(models.FeatureConfig).where(
            models.FeatureConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        return models.FeatureConfig(
            project_id=project_id,
            baseline_batch_size=1000,
            monitor_batch_size=500,
            monitoring_stage="model_input"
        )
        
    return config

@router.put("/config/{project_id}", response_model=schemas.FeatureConfigResponse)
async def update_feature_config(
    project_id: int,
    config_update: schemas.FeatureConfigCreate,
    project: models.Project = Depends(require_feature_project),
    db: AsyncSession = Depends(get_db)
):
    """Update feature monitoring configuration."""
    result = await db.execute(
        select(models.FeatureConfig).where(
            models.FeatureConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.FeatureConfig(project_id=project_id)
        db.add(config)
    
    config.baseline_batch_size = config_update.baseline_batch_size
    config.monitor_batch_size = config_update.monitor_batch_size
    config.monitoring_stage = config_update.monitoring_stage
    
    await db.commit()
    await db.refresh(config)
    return config

@router.get("/drift-config/{project_id}")
async def get_drift_config(
    project_id: int,
    project: models.Project = Depends(require_feature_project),
    db: AsyncSession = Depends(get_db)
):
    """Get drift detection configuration."""
    result = await db.execute(
        select(models.FeatureDriftConfig).where(
            models.FeatureDriftConfig.project_id == project_id
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
    config_data: dict,
    project: models.Project = Depends(require_feature_project),
    db: AsyncSession = Depends(get_db)
):
    """Update drift detection configuration."""
    result = await db.execute(
        select(models.FeatureDriftConfig).where(
            models.FeatureDriftConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        config = models.FeatureDriftConfig(project_id=project_id)
        db.add(config)
    
    # Simple mapping
    fields = [
        "mean_threshold", "median_threshold", "variance_threshold",
        "ks_pvalue_threshold", "psi_threshold", "psi_bins",
        "min_samples", "alert_threshold", "model_based_drift_threshold"
    ]
    
    for field in fields:
        if field in config_data:
            setattr(config, field, config_data[field])
    
    await db.commit()
    await db.refresh(config)
    return {"message": "Drift configuration updated successfully", "config_id": config.config_id}

# =============================================================================
# DRIFT DETECTION & QUALITY (Adapted from existing routes)
# =============================================================================

@router.get("/drift/statistical/{project_id}")
async def get_statistical_drift(
    project_id: int,
    limit: int = 10,
    project: models.Project = Depends(require_feature_project),
    db: AsyncSession = Depends(get_db)
):
    """Get feature drift history."""
    result = await db.execute(
        select(models.FeatureDrift)
        .where(models.FeatureDrift.project_id == project_id)
        .order_by(desc(models.FeatureDrift.test_happened_at_time))
        .limit(limit)
    )
    drift_records = result.scalars().all()
    
    return {
        "project_id": project_id,
        "results": [
            {
                "id": record.id,
                "baseline_window": record.baseline_window,
                "current_window": record.current_window,
                "overall_drift": record.overall_drift,
                "drift_score": record.drift_score,
                "alerts": record.alerts,
                "timestamp": record.test_happened_at_time
            }
            for record in drift_records
        ]
    }

@router.get("/quality/history/{project_id}")
async def get_quality_history(
    project_id: int,
    limit: int = 10,
    project: models.Project = Depends(require_feature_project),
    db: AsyncSession = Depends(get_db)
):
    """Get data quality check history."""
    result = await db.execute(
        select(models.FeatureQualityCheck)
        .where(models.FeatureQualityCheck.project_id == project_id)
        .order_by(desc(models.FeatureQualityCheck.check_timestamp))
        .limit(limit)
    )
    checks = result.scalars().all()
    
    return {
        "project_id": project_id,
        "total_checks": len(checks),
        "checks": [
            {
                "check_id": check.id,
                "batch_number": check.batch_number,
                "timestamp": check.check_timestamp,
                "rows_checked": check.total_rows_checked,
                "columns_with_missing": check.columns_with_missing,
                "status": check.check_status,
                "missing_values": check.missing_values_summary,
                "error": check.error_message
            }
            for check in checks
        ]
    }
@router.get("/validation/history/{project_id}")
async def get_validation_history(
    project_id: int,
    limit: int = 10,
    project: models.Project = Depends(require_feature_project),
    db: AsyncSession = Depends(get_db)
):
    """Get data validation history for feature monitoring."""
    result = await db.execute(
        select(models.FeatureValidation)
        .where(models.FeatureValidation.project_id == project_id)
        .order_by(desc(models.FeatureValidation.created_at))
        .limit(limit)
    )
    validations = result.scalars().all()
    
    return {
        "project_id": project_id,
        "results": [
            {
                "id": v.id,
                "batch_number": v.batch_number,
                "timestamp": v.created_at,
                "status": "Valid" if v.validation_status else "Invalid",
                "column_check": "Passed" if v.len_columns_status else "Failed",
                "type_check": "Passed" if v.columns_type_status else "Failed",
                "null_check": "N/A" # null_values_status not available in model
            }
            for v in validations
        ]
    }
