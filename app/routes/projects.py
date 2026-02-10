from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import warnings

from app.database.connection import get_db
from app.database import models, schemas
from app.utils.auth import get_current_user, generate_session_token, get_current_project

import secrets

warnings.filterwarnings("ignore")


router = APIRouter(
    prefix= '/projects',
    tags= ['Projects']
)

@router.post('/create_project', response_model=schemas.ProjectResponse)
async def create_project(
    project: schemas.ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Create a new project for the authenticated company."""
    # Check if project already exists for this company
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_name == project.project_name,
            models.Project.company_id == current_user.company_id
        )
    )
    existing_project = result.scalar_one_or_none()

    if existing_project:
        raise HTTPException(
            status_code=400,
            detail="Project with this name already exists for your company"
        )

    # Create new project
    new_project = models.Project(
        project_name=project.project_name,
        project_description=project.project_description,
        project_type=project.project_type,
        company_id=current_user.company_id,
        access_token=generate_session_token()
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return new_project


@router.get('/', response_model=List[schemas.ProjectResponse])
async def get_all_projects(
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get all projects for the authenticated company."""
    result = await db.execute(
        select(models.Project).where(
            models.Project.company_id == current_user.company_id
        ).order_by(models.Project.created_at.desc())
    )
    projects = result.scalars().all()
    return projects


@router.get('/{project_id}', response_model=schemas.ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get a specific project by ID."""
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
    
    return project


@router.put('/{project_id}', response_model=schemas.ProjectResponse)
async def update_project(
    project_id: int,
    project_update: schemas.ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Update a project."""
    # Get the project and verify ownership
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
    
    # Check if new name conflicts with existing project
    if project_update.project_name != project.project_name:
        result = await db.execute(
            select(models.Project).where(
                models.Project.project_name == project_update.project_name,
                models.Project.company_id == current_user.company_id,
                models.Project.project_id != project_id
            )
        )
        existing_project = result.scalar_one_or_none()
        
        if existing_project:
            raise HTTPException(
                status_code=400,
                detail="Another project with this name already exists"
            )
    
    # Update project
    project.project_name = project_update.project_name
    project.project_description = project_update.project_description
    project.project_type = project_update.project_type
    
    await db.commit()
    await db.refresh(project)
    
    return project


@router.delete('/{project_id}', response_model=schemas.MessageResponse)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Delete a project."""
    # Get the project and verify ownership
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
    
    # Delete the project (cascade will handle related records)
    await db.delete(project)
    await db.commit()
    
    return {"message": f"Project '{project.project_name}' deleted successfully"}


@router.post("/monitor_config", response_model=schemas.FeatureConfigResponse)
async def create_monitor_config(
    config: schemas.FeatureConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_project: models.Project = Depends(get_current_project),
):
    """Create feature monitoring configuration for a project."""
    try:
        new_config = models.FeatureConfig(
            project_id=current_project.project_id,
            baseline_batch_size=config.baseline_batch_size,
            monitor_batch_size=config.monitor_batch_size,
            monitoring_stage=config.monitoring_stage
        )

        db.add(new_config)
        await db.commit()
        await db.refresh(new_config)

        return new_config

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error while creating project config"
        )


@router.get("/{project_id}/config", response_model=schemas.FeatureConfigResponse)
async def get_project_config(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get configuration for a specific project."""
    # Verify project ownership
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
        
    # Get config
    result = await db.execute(
        select(models.FeatureConfig).where(
            models.FeatureConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        # Return default config if none exists
        return models.FeatureConfig(
            project_id=project_id,
            baseline_batch_size=1000,
            monitor_batch_size=500,
            monitoring_stage="model_input"
        )
        
    return config


# ========== DRIFT CONFIGURATION ENDPOINTS ==========

@router.get("/{project_id}/drift-config")
async def get_drift_config(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Get drift detection configuration for a project."""
    # Verify project ownership
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get drift config
    result = await db.execute(
        select(models.FeatureDriftConfig).where(
            models.FeatureDriftConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        # Return defaults if no config exists
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
    
    return {
        "project_id": config.project_id,
        "config_id": config.config_id,
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


@router.put("/{project_id}/drift-config")
async def update_drift_config(
    project_id: int,
    config_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: models.Company = Depends(get_current_user)
):
    """Update drift detection configuration for a project."""
    # Verify project ownership
    result = await db.execute(
        select(models.Project).where(
            models.Project.project_id == project_id,
            models.Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get existing config or create new
    result = await db.execute(
        select(models.FeatureDriftConfig).where(
            models.FeatureDriftConfig.project_id == project_id
        )
    )
    config = result.scalar_one_or_none()
    
    if not config:
        # Create new config
        config = models.FeatureDriftConfig(project_id=project_id)
        db.add(config)
    
    # Update fields if provided
    if "mean_threshold" in config_data:
        config.mean_threshold = float(config_data["mean_threshold"])
    if "median_threshold" in config_data:
        config.median_threshold = float(config_data["median_threshold"])
    if "variance_threshold" in config_data:
        config.variance_threshold = float(config_data["variance_threshold"])
    if "ks_pvalue_threshold" in config_data:
        config.ks_pvalue_threshold = float(config_data["ks_pvalue_threshold"])
    if "psi_threshold" in config_data:
        config.psi_threshold = config_data["psi_threshold"]
    if "psi_bins" in config_data:
        config.psi_bins = int(config_data["psi_bins"])
    if "min_samples" in config_data:
        config.min_samples = int(config_data["min_samples"])
    if "alert_threshold" in config_data:
        config.alert_threshold = int(config_data["alert_threshold"])
    if "model_based_drift_threshold" in config_data:
        config.model_based_drift_threshold = float(config_data["model_based_drift_threshold"])
    
    await db.commit()
    await db.refresh(config)
    
    return {"message": "Drift configuration updated successfully", "config_id": config.config_id}
