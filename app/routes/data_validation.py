from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.database.connection import get_db
from app.database import models
from app.services.check_data_quality import DataQualityChecker
from app.services.data_validation import DataValidation

router = APIRouter(
    prefix="/data-validation",
    tags=["Data Validation"]
)

@router.post("/check/{project_id}")
async def run_comprehensive_check(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Run both Data Quality and Schema Validation checks for the latest batch.
    """
    try:
        # 1. Fetch Project
        result = await db.execute(
            select(models.Project).where(models.Project.project_id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2. Setup Checker
        checker = DataQualityChecker(project_id)
        data = await checker.get_data_and_metadata()
        
        if not data or len(data.get('features', [])) == 0:
            return {"status": "skipped", "message": "No data found for validation"}

        batch_number = data.get('batch_number', 0)

        # 3. Run Data Quality Checks (Missing & Duplicates)
        missing_result = await checker.check_missing_values()
        duplicate_result = await checker.check_duplicate_rows()

        # Store Quality Result
        quality_check = models.DataQualityCheck(
            project_id=project_id,
            batch_number=batch_number,
            feature_start_row=data['feature_row_range'][0],
            feature_end_row=data['feature_row_range'][1],
            total_rows_checked=len(data['features']),
            missing_values_summary=missing_result['missing_values'],
            duplicate_percentage=duplicate_result['duplicate_percentage'],
            total_duplicate_rows=duplicate_result['total_duplicates'],
            total_columns_checked=missing_result['total_columns_checked'],
            columns_with_missing=missing_result['columns_with_missing'],
            check_status="completed"
        )
        db.add(quality_check)

        # 4. Run Schema Validation
        # The DataValidation service expects (features, project_id)
        validator = DataValidation(data['features'], project_id)
        validation_status = await validator.check_data_validation(batch_number)

        await db.commit()

        return {
            "status": "success",
            "batch_number": batch_number,
            "quality": {
                "total_rows": len(data['features']),
                "missing_columns": missing_result['columns_with_missing']
            },
            "validation": {
                "status": "valid" if validation_status else "invalid"
            }
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")

@router.get("/status/{project_id}")
async def get_latest_validation_status(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the latest schema validation status.
    """
    result = await db.execute(
        select(models.DataValidation)
        .where(models.DataValidation.project_id == project_id)
        .order_by(desc(models.DataValidation.created_at))
        .limit(1)
    )
    validation = result.scalar_one_or_none()
    
    if not validation:
        raise HTTPException(status_code=404, detail="No validation records found")

    return {
        "project_id": project_id,
        "batch_number": validation.batch_number,
        "timestamp": validation.created_at,
        "validation_status": "valid" if validation.validation_status else "invalid",
        "details": {
            "column_count_match": validation.len_columns_status,
            "column_types_match": validation.columns_type_status
        }
    }
