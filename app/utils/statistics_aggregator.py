"""
Statistics aggregation utilities for project metrics.
Provides helper functions to calculate and aggregate statistics from database.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.database import models


async def get_project_overview_stats(
    db: AsyncSession,
    project_id: int
) -> Dict:
    """
    Get overview statistics for a project.
    
    Returns:
        Dict with total_tests, pass_rate, fail_rate, avg_response_time
    """
    # Get total quality checks
    result = await db.execute(
        select(func.count(models.FeatureQualityCheck.id))
        .where(models.FeatureQualityCheck.project_id == project_id)
    )
    total_tests = result.scalar() or 0
    
    # Get passed tests
    result = await db.execute(
        select(func.count(models.FeatureQualityCheck.id))
        .where(
            and_(
                models.FeatureQualityCheck.project_id == project_id,
                models.FeatureQualityCheck.status == "passed"
            )
        )
    )
    passed_tests = result.scalar() or 0
    
    # Calculate rates
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    fail_rate = 100 - pass_rate
    
    # Get average response time (placeholder - would need actual timing data)
    avg_response_time = 0.0
    
    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": total_tests - passed_tests,
        "pass_rate": round(pass_rate, 2),
        "fail_rate": round(fail_rate, 2),
        "avg_response_time": avg_response_time
    }


async def get_test_history(
    db: AsyncSession,
    project_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Dict]:
    """
    Get test history for a project with pagination.
    
    Returns:
        List of test records with details
    """
    result = await db.execute(
        select(models.FeatureQualityCheck)
        .where(models.FeatureQualityCheck.project_id == project_id)
        .order_by(models.FeatureQualityCheck.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    tests = result.scalars().all()
    
    return [
        {
            "id": test.id,
            "batch_number": test.batch_number,
            "status": test.status,
            "missing_values": test.missing_values,
            "duplicates": test.duplicates,
            "outliers": test.outliers,
            "error_message": test.error_message,
            "created_at": test.created_at.isoformat() if test.created_at else None
        }
        for test in tests
    ]


async def get_time_series_stats(
    db: AsyncSession,
    project_id: int,
    days: int = 30
) -> List[Dict]:
    """
    Get time-series statistics for charts (daily aggregation).
    
    Returns:
        List of daily statistics with date, total_tests, passed, failed
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all tests within the time range
    result = await db.execute(
        select(models.FeatureQualityCheck)
        .where(
            and_(
                models.FeatureQualityCheck.project_id == project_id,
                models.FeatureQualityCheck.created_at >= cutoff_date
            )
        )
        .order_by(models.FeatureQualityCheck.created_at)
    )
    tests = result.scalars().all()
    
    # Group by date
    daily_stats = {}
    for test in tests:
        if test.created_at:
            date_key = test.created_at.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {"total": 0, "passed": 0, "failed": 0}
            
            daily_stats[date_key]["total"] += 1
            if test.status == "passed":
                daily_stats[date_key]["passed"] += 1
            else:
                daily_stats[date_key]["failed"] += 1
    
    # Convert to list format
    return [
        {
            "date": date,
            "total_tests": stats["total"],
            "passed": stats["passed"],
            "failed": stats["failed"],
            "pass_rate": round((stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0, 2)
        }
        for date, stats in sorted(daily_stats.items())
    ]


async def get_validation_stats(
    db: AsyncSession,
    project_id: int
) -> Dict:
    """
    Get data validation statistics.
    
    Returns:
        Dict with validation metrics
    """
    result = await db.execute(
        select(func.count(models.FeatureValidation.id))
        .where(models.FeatureValidation.project_id == project_id)
    )
    total_validations = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(models.FeatureValidation.id))
        .where(
            and_(
                models.FeatureValidation.project_id == project_id,
                models.FeatureValidation.validation_status == True
            )
        )
    )
    passed_validations = result.scalar() or 0
    
    return {
        "total_validations": total_validations,
        "passed_validations": passed_validations,
        "failed_validations": total_validations - passed_validations,
        "validation_pass_rate": round((passed_validations / total_validations * 100) if total_validations > 0 else 0, 2)
    }


async def get_drift_detection_stats(
    db: AsyncSession,
    project_id: int
) -> Dict:
    """
    Get drift detection statistics.
    
    Returns:
        Dict with drift metrics
    """
    # Get LLM drift stats
    result = await db.execute(
        select(func.count(models.LLMDrift.id))
        .where(models.LLMDrift.project_id == project_id)
    )
    total_drift_checks = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(models.LLMDrift.id))
        .where(
            and_(
                models.LLMDrift.project_id == project_id,
                models.LLMDrift.has_drift == True
            )
        )
    )
    drift_detected = result.scalar() or 0
    
    return {
        "total_drift_checks": total_drift_checks,
        "drift_detected": drift_detected,
        "no_drift": total_drift_checks - drift_detected,
        "drift_rate": round((drift_detected / total_drift_checks * 100) if total_drift_checks > 0 else 0, 2)
    }
