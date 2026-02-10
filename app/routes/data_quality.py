from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from typing import Optional

from app.database.connection import get_db
from app.database.models import FeatureQualityCheck, Project
from app.services.feature_monitoring.check_data_quality import FeatureQualityChecker
from app.utils.auth import get_current_project

router = APIRouter(
    prefix="/data-quality",
    tags=["Data Quality"]
)


@router.post("/check/{project_id}")
async def run_quality_check(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a data quality check for a project.
    This checks the latest batch of ingested data for missing values and duplicates.
    """
    try:
        # Verify project exists
        result = await db.execute(
            select(Project).where(Project.project_id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        checker = FeatureQualityChecker(project_id)
        
        # Get metadata
        data = await checker.get_data_and_metadata()
        
        # Run missing value check
        missing_result = await checker.check_missing_values()
        
        # Run duplicate check
        duplicate_result = await checker.check_duplicate_rows()
        
        # Store results in database
        quality_check = FeatureQualityCheck(
            project_id=project_id,
            batch_number=data['batch_number'],
            feature_start_row=data['feature_row_range'][0],
            feature_end_row=data['feature_row_range'][1],
            total_rows_checked=len(data['features']) if len(data['features']) > 0 else 0,
            missing_values_summary=missing_result['missing_values'],
            total_duplicate_rows=duplicate_result.get('total_duplicates', 0),
            total_columns_checked=missing_result['total_columns_checked'],
            columns_with_missing=missing_result['columns_with_missing'],
            check_status="completed"
        )
        
        db.add(quality_check)
        await db.commit()
        await db.refresh(quality_check)
        
        return {
            "status": "success",
            "check_id": quality_check.id,
            "batch_number": quality_check.batch_number,
            "total_rows_checked": quality_check.total_rows_checked,
            "total_columns_checked": quality_check.total_columns_checked,
            "columns_with_missing": quality_check.columns_with_missing,
            "missing_values": quality_check.missing_values_summary,
            "total_duplicate_rows": quality_check.total_duplicate_rows,
            "timestamp": quality_check.check_timestamp
        }
        
    except Exception as e:
        # Store failed check
        quality_check = FeatureQualityCheck(
            project_id=project_id,
            batch_number=0,
            check_status="failed",
            error_message=str(e)
        )
        db.add(quality_check)
        await db.commit()
        
        raise HTTPException(status_code=500, detail=f"Quality check failed: {str(e)}")


@router.get("/history/{project_id}")
async def get_quality_history(
    project_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the history of data quality checks for a project.
    Returns the most recent checks first.
    """
    result = await db.execute(
        select(FeatureQualityCheck)
        .where(FeatureQualityCheck.project_id == project_id)
        .order_by(desc(FeatureQualityCheck.check_timestamp))
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


@router.get("/latest/{project_id}")
async def get_latest_check(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the most recent data quality check for a project.
    """
    result = await db.execute(
        select(FeatureQualityCheck)
        .where(FeatureQualityCheck.project_id == project_id)
        .order_by(desc(FeatureQualityCheck.check_timestamp))
        .limit(1)
    )
    check = result.scalar_one_or_none()
    
    if not check:
        raise HTTPException(status_code=404, detail="No quality checks found for this project")
    
    return {
        "check_id": check.id,
        "project_id": check.project_id,
        "batch_number": check.batch_number,
        "timestamp": check.check_timestamp,
        "row_range": (check.feature_start_row, check.feature_end_row),
        "total_rows_checked": check.total_rows_checked,
        "total_columns_checked": check.total_columns_checked,
        "columns_with_missing": check.columns_with_missing,
        "status": check.check_status,
        "missing_values": check.missing_values_summary,
        "error_message": check.error_message
    }


@router.get("/check/{check_id}")
async def get_quality_check(
    check_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific quality check by ID.
    Returns full missing values summary and duplicate info.
    """
    result = await db.execute(
        select(FeatureQualityCheck).where(FeatureQualityCheck.id == check_id)
    )
    check = result.scalar_one_or_none()
    
    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")
    
    return {
        "check_id": check.id,
        "project_id": check.project_id,
        "batch_number": check.batch_number,
        "check_timestamp": check.check_timestamp,
        "feature_start_row": check.feature_start_row,
        "feature_end_row": check.feature_end_row,
        "total_rows_checked": check.total_rows_checked,
        "total_columns_checked": check.total_columns_checked,
        "columns_with_missing": check.columns_with_missing,
        "missing_values_summary": check.missing_values_summary or {},
        "duplicate_percentage": check.duplicate_percentage or 0.0,
        "total_duplicate_rows": check.total_duplicate_rows or 0,
        "check_status": check.check_status,
        "error_message": check.error_message
    }
