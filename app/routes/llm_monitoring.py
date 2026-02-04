"""
LLM Monitoring Routes - Handles LLM interaction ingestion and monitoring endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.database import models
from app.database.connection import get_db
from app.database.schemas import ProjectResponse
from app.services.llm_monitor_service import LLMMonitorService
from app.utils.auth import verify_api_key

router = APIRouter(prefix="/ingest", tags=["llm_monitoring"])


class LLMInteractionRequest:
    """Request model for LLM interaction logging"""
    def __init__(self, project_name: str, input_text: str, response_text: str, metadata: dict = None):
        self.project_name = project_name
        self.input_text = input_text
        self.response_text = response_text
        self.metadata = metadata or {}


@router.post("/llm", status_code=201)
async def ingest_llm_interaction(
    project_name: str,
    input_text: str,
    response_text: str,
    metadata: dict = None,
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(verify_api_key)
):
    """
    Ingest and process an LLM interaction.
    
    Args:
        project_name: Name of the project
        input_text: Input text to LLM
        response_text: Response from LLM
        metadata: Optional metadata
        db: Database session
        company_id: Authenticated company ID (from API key)
        
    Returns:
        dict: Logged interaction details
    """
    if not project_name or not input_text or not response_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_name, input_text, and response_text are required"
        )

    try:
        # 1. Get project ID from project name
        project_result = await db.execute(
            select(models.Project).where(
                models.Project.project_name == project_name,
                models.Project.company_id == company_id
            )
        )
        project = project_result.scalars().first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_name}' not found"
            )

        project_id = project.project_id

        # 2. Ensure LLM config exists, create if not
        config_result = await db.execute(
            select(models.LLMConfig).where(
                models.LLMConfig.project_id == project_id
            )
        )
        config = config_result.scalars().first()

        if not config:
            # Create default config
            new_config = models.LLMConfig(
                project_id=project_id,
                baseline_batch_size=500,
                monitor_batch_size=250,
                toxicity_threshold=0.5,
                token_drift_threshold=0.15
            )
            db.add(new_config)
            await db.commit()
            print(f"✓ Created default LLM config for project {project_id}")

        # 3. Log interaction using service
        service = LLMMonitorService()
        result = await service.log_interaction(
            project_id=project_id,
            input_text=input_text,
            response_text=response_text,
            metadata=metadata
        )

        return {
            "status": "success",
            "message": "LLM interaction logged successfully",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error ingesting LLM interaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest LLM interaction: {str(e)}"
        )


@router.get("/llm/drift/{project_id}")
async def get_llm_drift_history(
    project_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(verify_api_key)
):
    """
    Get LLM drift detection history for a project.
    
    Args:
        project_id: Project ID
        limit: Number of records to return
        db: Database session
        company_id: Authenticated company ID
        
    Returns:
        dict: List of drift records
    """
    try:
        # Verify project ownership
        project_result = await db.execute(
            select(models.Project).where(
                models.Project.project_id == project_id,
                models.Project.company_id == company_id
            )
        )
        project = project_result.scalars().first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Get drift history
        drift_result = await db.execute(
            select(models.LLMDrift).where(
                models.LLMDrift.project_id == project_id
            ).order_by(models.LLMDrift.created_at.desc()).limit(limit)
        )
        drifts = drift_result.scalars().all()

        return {
            "status": "success",
            "project_id": project_id,
            "drift_records": [
                {
                    "id": d.id,
                    "baseline_window": d.baseline_window,
                    "monitor_window": d.monitor_window,
                    "baseline_avg_tokens": d.baseline_avg_tokens,
                    "monitor_avg_tokens": d.monitor_avg_tokens,
                    "token_length_change": d.token_length_change,
                    "has_drift": d.has_drift,
                    "interpretation": d.drift_interpretation,
                    "created_at": d.created_at
                }
                for d in drifts
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve drift history: {str(e)}"
        )


@router.get("/llm/baseline/{project_id}")
async def get_llm_baseline_info(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(verify_api_key)
):
    """
    Get current LLM baseline information for a project.
    
    Args:
        project_id: Project ID
        db: Database session
        company_id: Authenticated company ID
        
    Returns:
        dict: Baseline information
    """
    try:
        # Verify project ownership
        project_result = await db.execute(
            select(models.Project).where(
                models.Project.project_id == project_id,
                models.Project.company_id == company_id
            )
        )
        project = project_result.scalars().first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Get baseline info
        baseline_result = await db.execute(
            select(models.LLMBaselineInfo).where(
                models.LLMBaselineInfo.project_id == project_id
            )
        )
        baseline = baseline_result.scalars().first()

        if not baseline:
            return {
                "status": "success",
                "project_id": project_id,
                "baseline": None,
                "message": "No baseline created yet"
            }

        # Get monitor info
        monitor_result = await db.execute(
            select(models.LLMMonitorInfo).where(
                models.LLMMonitorInfo.project_id == project_id
            )
        )
        monitor = monitor_result.scalars().first()

        return {
            "status": "success",
            "project_id": project_id,
            "baseline": {
                "baseline_start_row": baseline.baseline_start_row,
                "baseline_end_row": baseline.baseline_end_row,
                "avg_response_token_length": baseline.avg_response_token_length,
                "created_at": baseline.created_at
            },
            "monitor": {
                "monitor_start_row": monitor.monitor_start_row if monitor else None,
                "monitor_end_row": monitor.monitor_end_row if monitor else None,
                "current_avg_token_length": monitor.current_avg_token_length if monitor else None
            } if monitor else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve baseline info: {str(e)}"
        )


@router.get("/llm/config/{project_id}")
async def get_llm_config(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    company_id: int = Depends(verify_api_key)
):
    """
    Get LLM monitoring configuration for a project.
    
    Args:
        project_id: Project ID
        db: Database session
        company_id: Authenticated company ID
        
    Returns:
        dict: Configuration details
    """
    try:
        # Verify project ownership
        project_result = await db.execute(
            select(models.Project).where(
                models.Project.project_id == project_id,
                models.Project.company_id == company_id
            )
        )
        project = project_result.scalars().first()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Get config
        config_result = await db.execute(
            select(models.LLMConfig).where(
                models.LLMConfig.project_id == project_id
            )
        )
        config = config_result.scalars().first()

        if not config:
            return {
                "status": "success",
                "project_id": project_id,
                "config": None,
                "message": "No configuration found"
            }

        return {
            "status": "success",
            "project_id": project_id,
            "config": {
                "baseline_batch_size": config.baseline_batch_size,
                "monitor_batch_size": config.monitor_batch_size,
                "toxicity_threshold": config.toxicity_threshold,
                "token_drift_threshold": config.token_drift_threshold,
                "created_at": config.created_at
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve config: {str(e)}"
        )
