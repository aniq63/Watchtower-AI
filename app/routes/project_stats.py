from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import warnings
import json

from app.database.connection import get_db
from app.database import models, schemas
from app.utils.auth import get_current_user, get_current_project

warnings.filterwarnings("ignore")

router = APIRouter(
    prefix='/projects',
    tags=['Project Statistics']
)


@router.get('/{project_id}/overview')
async def get_project_overview(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get project overview statistics."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get total data points (feature inputs)
    feature_count = await db.execute(
        select(func.count(models.FeatureInput.id)).where(
            models.FeatureInput.project_id == project_id
        )
    )
    total_data_points = feature_count.scalar() or 0
    
    # Get drift runs count
    drift_count = await db.execute(
        select(func.count(models.FeatureDrift.id)).where(
            models.FeatureDrift.project_id == project_id
        )
    )
    drift_runs = drift_count.scalar() or 0
    
    # Get quality check runs count
    quality_count = await db.execute(
        select(func.count(models.FeatureQualityCheck.id)).where(
            models.FeatureQualityCheck.project_id == project_id
        )
    )
    quality_runs = quality_count.scalar() or 0
    
    # Get LLM queries count
    llm_count = await db.execute(
        select(func.count(models.LLMMonitor.id)).where(
            models.LLMMonitor.project_id == project_id
        )
    )
    llm_queries = llm_count.scalar() or 0
    
    # Get last updated timestamp
    last_feature = await db.execute(
        select(models.FeatureInput.created_at)
        .where(models.FeatureInput.project_id == project_id)
        .order_by(models.FeatureInput.created_at.desc())
        .limit(1)
    )
    last_updated = last_feature.scalar()
    
    return {
        "project_id": project_id,
        "project_name": project.project_name,
        "total_data_points": total_data_points,
        "drift_runs": drift_runs,
        "quality_runs": quality_runs,
        "llm_queries": llm_queries,
        "last_updated": last_updated.isoformat() if last_updated else None,
        "status": "active" if total_data_points > 0 else "inactive"
    }


@router.get('/{project_id}/drift-runs')
async def get_drift_runs(
    project_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get list of all drift detection runs for a project."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get drift runs
    drift_results = await db.execute(
        select(models.FeatureDrift)
        .where(models.FeatureDrift.project_id == project_id)
        .order_by(models.FeatureDrift.created_at.desc())
        .limit(limit)
    )
    drifts = drift_results.scalars().all()
    
    return [
        {
            "drift_id": drift.id,
            "baseline_window": drift.baseline_window,
            "current_window": drift.current_window,
            "overall_drift": drift.overall_drift,
            "drift_score": drift.drift_score,
            "alerts_count": len(drift.alerts) if drift.alerts else 0,
            "alerted_features": drift.alerts if drift.alerts else [],
            "created_at": drift.created_at.isoformat() if drift.created_at else None
        }
        for drift in drifts
    ]


@router.get('/{project_id}/drift-runs/{drift_id}')
async def get_drift_run_detail(
    project_id: int,
    drift_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get detailed information for a specific drift run."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get specific drift run
    drift_result = await db.execute(
        select(models.FeatureDrift).where(
            and_(
                models.FeatureDrift.id == drift_id,
                models.FeatureDrift.project_id == project_id
            )
        )
    )
    drift = drift_result.scalar_one_or_none()
    
    if not drift:
        raise HTTPException(status_code=404, detail="Drift run not found")
    
    # Get corresponding model-based drift (closest in time)
    # Since they run together, timestamps should be very close
    model_drift_result = await db.execute(
        select(models.ModelBasedDrift).where(
            and_(
                models.ModelBasedDrift.project_id == project_id,
                models.ModelBasedDrift.test_happened_at_time >= drift.test_happened_at_time - timedelta(seconds=30),
                models.ModelBasedDrift.test_happened_at_time <= drift.test_happened_at_time + timedelta(seconds=30)
            )
        ).order_by(desc(models.ModelBasedDrift.test_happened_at_time))
        .limit(1)
    )
    model_drift = model_drift_result.scalar_one_or_none()
    
    # Helper to ensure JSON is parsed
    def parse_json_field(field):
        if isinstance(field, str):
            try:
                return json.loads(field)
            except:
                return field
        return field

    return {
        "drift_id": drift.id,
        "baseline_window": drift.baseline_window,
        "current_window": drift.current_window,
        "baseline_timestamp": drift.baseline_source_timestamp.isoformat() if drift.baseline_source_timestamp else None,
        "current_timestamp": drift.current_source_timestamp.isoformat() if drift.current_source_timestamp else None,
        "feature_stats": parse_json_field(drift.feature_stats),
        "drift_tests": parse_json_field(drift.drift_tests),
        "alerts": parse_json_field(drift.alerts),
        "overall_drift": drift.overall_drift,
        "drift_score": drift.drift_score,
        "drift_score": drift.drift_score,
        "llm_interpretation": drift.llm_interpretation,
        "created_at": drift.created_at.isoformat() if drift.created_at else None,
        "model_based_drift": {
            "drift_score": model_drift.drift_score,
            "alert_triggered": model_drift.alert_triggered,
            "alert_threshold": model_drift.alert_threshold,
            "model_type": model_drift.model_type,
            "test_accuracy": model_drift.test_accuracy
        } if model_drift else None
    }


@router.get('/{project_id}/quality-runs')
async def get_quality_runs(
    project_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get list of all quality check runs for a project."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get quality check runs
    quality_results = await db.execute(
        select(models.FeatureQualityCheck)
        .where(models.FeatureQualityCheck.project_id == project_id)
        .order_by(models.FeatureQualityCheck.check_timestamp.desc())
        .limit(limit)
    )
    checks = quality_results.scalars().all()
    
    return [
        {
            "check_id": check.id,
            "batch_number": check.batch_number,
            "feature_start_row": check.feature_start_row,
            "feature_end_row": check.feature_end_row,
            "total_rows_checked": check.total_rows_checked,
            "total_columns_checked": check.total_columns_checked,
            "columns_with_missing": check.columns_with_missing,
            "duplicate_percentage": check.duplicate_percentage,
            "total_duplicate_rows": check.total_duplicate_rows,
            "check_status": check.check_status,
            "check_timestamp": check.check_timestamp.isoformat() if check.check_timestamp else None
        }
        for check in checks
    ]


@router.get('/{project_id}/quality-runs/{check_id}')
async def get_quality_run_detail(
    project_id: int,
    check_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get detailed information for a specific quality check run."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get specific quality check
    check_result = await db.execute(
        select(models.FeatureQualityCheck).where(
            and_(
                models.FeatureQualityCheck.id == check_id,
                models.FeatureQualityCheck.project_id == project_id
            )
        )
    )
    check = check_result.scalar_one_or_none()
    
    if not check:
        raise HTTPException(status_code=404, detail="Quality check not found")
    
    return {
        "check_id": check.id,
        "batch_number": check.batch_number,
        "feature_start_row": check.feature_start_row,
        "feature_end_row": check.feature_end_row,
        "total_rows_checked": check.total_rows_checked,
        "missing_values_summary": check.missing_values_summary,  # Full JSON
        "duplicate_percentage": check.duplicate_percentage,
        "total_duplicate_rows": check.total_duplicate_rows,
        "total_columns_checked": check.total_columns_checked,
        "columns_with_missing": check.columns_with_missing,
        "check_status": check.check_status,
        "error_message": check.error_message,
        "check_timestamp": check.check_timestamp.isoformat() if check.check_timestamp else None
    }


@router.get('/{project_id}/llm-queries')
async def get_llm_queries(
    project_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get list of LLM monitoring queries for a project."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get LLM monitoring results
    llm_results = await db.execute(
        select(models.LLMMonitor)
        .where(models.LLMMonitor.project_id == project_id)
        .order_by(models.LLMMonitor.created_at.desc())
        .limit(limit)
    )
    llm_data = llm_results.scalars().all()
    
    return [
        {
            "query_id": llm.id,
            "row_id": llm.row_id,
            "input_text": llm.input_text[:200] if llm.input_text else "",  # Truncated
            "response_text": llm.response_text[:200] if llm.response_text else "",  # Truncated
            "response_token_length": llm.response_token_length,
            "toxicity_score": llm.detoxify.get("toxicity", 0) if llm.detoxify else 0,
            "is_toxic": llm.is_toxic,
            "created_at": llm.created_at.isoformat() if llm.created_at else None
        }
        for llm in llm_data
    ]


@router.get('/{project_id}/llm-queries/{query_id}')
async def get_llm_query_detail(
    project_id: int,
    query_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get detailed information for a specific LLM query."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get specific LLM query
    llm_result = await db.execute(
        select(models.LLMMonitor).where(
            and_(
                models.LLMMonitor.id == query_id,
                models.LLMMonitor.project_id == project_id
            )
        )
    )
    llm = llm_result.scalar_one_or_none()
    
    if not llm:
        raise HTTPException(status_code=404, detail="LLM query not found")
    
    return {
        "query_id": llm.id,
        "row_id": llm.row_id,
        "input_text": llm.input_text,  # Full text
        "response_text": llm.response_text,  # Full text
        "response_token_length": llm.response_token_length,
        "detoxify": llm.detoxify,  # Full JSON with all scores
        "is_toxic": llm.is_toxic,
        "llm_judge_metrics": llm.llm_judge_metrics,  # Full JSON
        "created_at": llm.created_at.isoformat() if llm.created_at else None
    }


@router.get('/{project_id}/llm-trend')
async def get_llm_trend(
    project_id: int,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get LLM toxicity trend data for charts."""
    # Verify project belongs to user
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get LLM data from last N days
    since_date = datetime.utcnow() - timedelta(days=days)
    llm_results = await db.execute(
        select(models.LLMMonitor)
        .where(
            and_(
                models.LLMMonitor.project_id == project_id,
                models.LLMMonitor.created_at >= since_date
            )
        )
        .order_by(models.LLMMonitor.created_at.asc())
    )
    llm_data = llm_results.scalars().all()
    
    return {
        "labels": [llm.created_at.isoformat() if llm.created_at else "" for llm in llm_data],
        "toxicity_scores": [llm.detoxify.get("toxicity", 0) if llm.detoxify else 0 for llm in llm_data],
        "token_lengths": [llm.response_token_length for llm in llm_data]
    }


@router.get('/{project_id}/drift-runs/{drift_id}/visualizations/{test_type}')
async def get_drift_test_visualization(
    project_id: int,
    drift_id: int,
    test_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Generate visualization for a specific drift test type."""
    from fastapi.responses import Response
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    import io
    import base64
    
    # Get drift run
    result = await db.execute(
        select(models.FeatureDrift).where(
            models.FeatureDrift.id == drift_id,
            models.FeatureDrift.project_id == project_id
        )
    )
    drift_run = result.scalar_one_or_none()
    
    if not drift_run:
        raise HTTPException(status_code=404, detail="Drift run not found")
    
    drift_tests = drift_run.drift_tests or {}
    
    # Collect test values for all columns
    test_values = []
    column_names = []
    drift_status = []
    
    for column, tests in drift_tests.items():
        if test_type in tests:
            test_data = tests[test_type]
            
            if test_type == 'ks_test':
                test_values.append(test_data.get('statistic', 0))
                drift_status.append(test_data.get('drift_detected', False))
            elif test_type == 'psi':
                test_values.append(test_data.get('value', 0))
                drift_status.append(test_data.get('severity') == 'high')
            else:  # mean_shift, median_shift, variance_shift
                test_values.append(test_data.get('value', 0))
                drift_status.append(test_data.get('drift_detected', False))
            
            column_names.append(column)
    
    if not test_values:
        raise HTTPException(status_code=404, detail=f"No data for test type: {test_type}")
    
    # Create visualization
    plt.figure(figsize=(12, 6))
    sns.set_style("whitegrid")
    
    # Create bar plot
    colors = ['#ef4444' if drift else '#3b82f6' for drift in drift_status]
    bars = plt.bar(range(len(test_values)), test_values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    
    # Customize plot
    plt.xlabel('Columns', fontsize=12, fontweight='bold')
    
    if test_type == 'ks_test':
        plt.ylabel('KS Statistic', fontsize=12, fontweight='bold')
        plt.title('Kolmogorov-Smirnov Test Results Across Columns', fontsize=14, fontweight='bold')
    elif test_type == 'psi':
        plt.ylabel('PSI Value', fontsize=12, fontweight='bold')
        plt.title('Population Stability Index Across Columns', fontsize=14, fontweight='bold')
    elif test_type == 'mean_shift':
        plt.ylabel('Relative Change (%)', fontsize=12, fontweight='bold')
        plt.title('Mean Shift Test Results Across Columns', fontsize=14, fontweight='bold')
    elif test_type == 'median_shift':
        plt.ylabel('Relative Change (%)', fontsize=12, fontweight='bold')
        plt.title('Median Shift Test Results Across Columns', fontsize=14, fontweight='bold')
    elif test_type == 'variance_shift':
        plt.ylabel('Relative Change (%)', fontsize=12, fontweight='bold')
        plt.title('Variance Shift Test Results Across Columns', fontsize=14, fontweight='bold')
    
    plt.xticks(range(len(column_names)), column_names, rotation=45, ha='right')
    plt.tight_layout()
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#ef4444', alpha=0.7, label='Drift Detected'),
        Patch(facecolor='#3b82f6', alpha=0.7, label='Normal')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    # Save to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    # Return as base64 encoded image
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return {"image": f"data:image/png;base64,{img_base64}"}



