from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
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
        company_id=current_user.company_id,
        access_token=generate_session_token()
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return new_project

@router.post("/monitor_config", response_model=schemas.ProjectConfigResponse)
async def create_monitor_config(
    config: schemas.ProjectConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_project: models.Project = Depends(get_current_project),
):
    try:
        new_config = models.ProjectConfig(
            project_id=current_project.project_id,
            baseline_batch_size=config.baseline_batch_size,
            monitor_batch_size=config.monitor_batch_size,
            monitoring_stage=config.monitoring_stage  # Store monitoring stage
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


