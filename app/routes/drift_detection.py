from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from typing import Optional
import pandas as pd

from app.database.connection import get_db
from app.database.models import (
    FeatureDrift, 
    ModelBasedDrift, 
    FeatureDriftConfig,
    Project
)
from app.services.feature_monitoring.data_drift import InputDataDriftMonitor
from app.services.feature_monitoring.model_based_data_drift import ModelBasedDriftMonitor
from app.services.feature_monitoring.baseline_manager import BaselineManager

router = APIRouter(
    prefix="/drift-detection",
    tags=["Drift Detection"]
)


@router.post("/run/{project_id}")
async def run_drift_detection(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger drift detection for a project.
    Runs both statistical and model-based drift detection.
    """
    try:
        # Verify project exists
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get baseline and monitor data
        baseline_mgr = BaselineManager(project_id=project_id)
        baseline_data = await baseline_mgr.get_baseline_data()
        monitor_data = await baseline_mgr.get_monitor_data()
        
        if not baseline_data or not monitor_data:
            raise HTTPException(
                status_code=400, 
                detail="Baseline or monitor data not available. Ensure sufficient data has been ingested."
            )
        
        # Convert to DataFrames
        baseline_df = pd.DataFrame(baseline_data['feature_data'])
        monitor_df = pd.DataFrame(monitor_data['feature_data'])
        
        if len(baseline_df) == 0 or len(monitor_df) == 0:
            raise HTTPException(
                status_code=400,
                detail="Insufficient data for drift detection"
            )
        
        # Run statistical drift detection
        stat_monitor = InputDataDriftMonitor(
            project_id=project_id,
            baseline_data=baseline_df,
            current_data=monitor_df
        )
        stat_results = await stat_monitor.run()
        
        # Run model-based drift detection
        model_monitor = ModelBasedDriftMonitor(
            project_id=project_id,
            baseline_data=baseline_df,
            current_data=monitor_df
        )
        model_results = await model_monitor.run()
        
        return {
            "status": "success",
            "message": "Drift detection completed",
            "statistical_drift": {
                "alerts": stat_results.get("alerts", []),
                "alert_count": len(stat_results.get("alerts", []))
            },
            "model_based_drift": {
                "drift_score": model_results.get("drift_score"),
                "alert": model_results.get("alert"),
                "threshold": model_results.get("alert_threshold")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift detection failed: {str(e)}")


@router.get("/statistical/{project_id}")
async def get_statistical_drift_results(
    project_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest statistical drift detection results for a project.
    """
    result = await db.execute(
        select(FeatureDrift)
        .where(FeatureDrift.project_id == project_id)
        .order_by(desc(FeatureDrift.test_happened_at_time))
        .limit(limit)
    )
    drift_records = result.scalars().all()
    
    if not drift_records:
        return {
            "project_id": project_id,
            "results": [],
            "message": "No drift detection results found"
        }
    
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


@router.get("/model-based/{project_id}")
async def get_model_based_drift_results(
    project_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest model-based drift detection results for a project.
    """
    result = await db.execute(
        select(ModelBasedDrift)
        .where(ModelBasedDrift.project_id == project_id)
        .order_by(desc(ModelBasedDrift.test_happened_at_time))
        .limit(limit)
    )
    drift_records = result.scalars().all()
    
    if not drift_records:
        return {
            "project_id": project_id,
            "results": [],
            "message": "No model-based drift results found"
        }
    
    return {
        "project_id": project_id,
        "results": [
            {
                "drift_id": record.drift_id,
                "drift_score": record.drift_score,
                "alert_triggered": record.alert_triggered,
                "alert_threshold": record.alert_threshold,
                "baseline_samples": record.baseline_samples,
                "current_samples": record.current_samples,
                "model_type": record.model_type,
                "test_accuracy": record.test_accuracy,
                "timestamp": record.test_happened_at_time
            }
            for record in drift_records
        ]
    }


@router.get("/summary/{project_id}")
async def get_drift_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a summary of the latest drift detection results.
    """
    # Get latest statistical drift
    stat_result = await db.execute(
        select(FeatureDrift)
        .where(FeatureDrift.project_id == project_id)
        .order_by(desc(FeatureDrift.test_happened_at_time))
        .limit(1)
    )
    latest_stat = stat_result.scalar_one_or_none()
    
    # Get latest model-based drift
    model_result = await db.execute(
        select(ModelBasedDrift)
        .where(ModelBasedDrift.project_id == project_id)
        .order_by(desc(ModelBasedDrift.test_happened_at_time))
        .limit(1)
    )
    latest_model = model_result.scalar_one_or_none()
    
    return {
        "project_id": project_id,
        "statistical_drift": {
            "available": latest_stat is not None,
            "overall_drift": latest_stat.overall_drift if latest_stat else False,
            "drift_score": latest_stat.drift_score if latest_stat else 0.0,
            "alerted_features": latest_stat.alerts if latest_stat else [],
            "timestamp": latest_stat.test_happened_at_time if latest_stat else None
        },
        "model_based_drift": {
            "available": latest_model is not None,
            "drift_score": latest_model.drift_score if latest_model else None,
            "alert_triggered": latest_model.alert_triggered if latest_model else False,
            "alert_threshold": latest_model.alert_threshold if latest_model else None,
            "timestamp": latest_model.test_happened_at_time if latest_model else None
        }
    }


@router.get("/config/{project_id}")
async def get_drift_config(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get drift detection configuration for a project.
    """
    result = await db.execute(
        select(FeatureDriftConfig).where(FeatureDriftConfig.project_id == project_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Drift config not found")
    
    return {
        "project_id": project_id,
        "mean_threshold": config.mean_threshold,
        "median_threshold": config.median_threshold,
        "variance_threshold": config.variance_threshold,
        "ks_pvalue_threshold": config.ks_pvalue_threshold,
        "psi_threshold": config.psi_threshold,
        "psi_bins": config.psi_bins,
        "min_samples": config.min_samples,
        "alert_threshold": config.alert_threshold,
        "model_based_drift_threshold": config.model_based_drift_threshold
    }
