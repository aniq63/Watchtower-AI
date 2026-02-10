"""
Statistics API endpoints for project metrics and visualizations.
Provides data for charts, graphs, and dashboard displays.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List

from app.database.connection import get_db
from app.database import models
from app.utils.auth import get_current_user
from app.utils.statistics_aggregator import (
    get_project_overview_stats,
    get_test_history,
    get_time_series_stats,
    get_validation_stats,
    get_drift_detection_stats
)

router = APIRouter(
    prefix="/statistics",
    tags=["Statistics"]
)


@router.get("/{project_id}/overview")
async def get_project_statistics(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """
    Get comprehensive statistics for a project.
    Includes overview metrics, validation stats, and drift detection stats.
    """
    # Verify project ownership
    from sqlalchemy import select
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found or you don't have access to it"
        )
    
    # Gather all statistics
    overview = await get_project_overview_stats(db, project_id)
    validation = await get_validation_stats(db, project_id)
    drift = await get_drift_detection_stats(db, project_id)
    
    return {
        "project_id": project_id,
        "project_name": project.project_name,
        "overview": overview,
        "validation": validation,
        "drift": drift
    }


@router.get("/{project_id}/tests")
async def get_project_tests(
    project_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """
    Get test history for a project with pagination.
    """
    # Verify project ownership
    from sqlalchemy import select
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found or you don't have access to it"
        )
    
    tests = await get_test_history(db, project_id, limit, offset)
    
    return {
        "project_id": project_id,
        "tests": tests,
        "limit": limit,
        "offset": offset
    }


@router.get("/{project_id}/timeseries")
async def get_project_timeseries(
    project_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """
    Get time-series statistics for charts (daily aggregation).
    Used for line charts and trend analysis.
    """
    # Verify project ownership
    from sqlalchemy import select
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found or you don't have access to it"
        )
    
    timeseries = await get_time_series_stats(db, project_id, days)
    
    return {
        "project_id": project_id,
        "days": days,
        "data": timeseries
    }
