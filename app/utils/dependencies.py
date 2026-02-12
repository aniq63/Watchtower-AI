from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.connection import get_db
from app.database import models
from app.utils.auth import get_current_user, verify_api_key

async def get_company_id_hybrid(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session_token: Optional[str] = Header(None, alias="session_token"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    Authenticate utilizing either Session Token, X-API-Key, or Bearer Token.
    Returns: company_id
    """
    # 1. Try Session Token (Frontend)
    if session_token:
        try:
            user = await get_current_user(session_token=session_token, db=db)
            return user.company_id
        except HTTPException:
            pass # Fall through to other methods

    # 2. Try X-API-Key (Legacy SDK)
    if api_key:
        try:
            return await verify_api_key(api_key=api_key, db=db)
        except HTTPException:
            pass

    # 3. Try Bearer Token (New SDK)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        # Treat bearer token as API Key for now (simpler logic than separate oauth)
        # OR verify_api_key logic should be reused.
        # Let's verify it against Company.api_key
        result = await db.execute(
            select(models.Company).where(models.Company.api_key == token)
        )
        company = result.scalar_one_or_none()
        if company:
            return company.company_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (Session Token or API Key)"
    )

def require_project_type(required_type: str):
    """
    Factory for a dependency that checks if the project exists, 
    belongs to the authenticated company, and matches the required project_type.
    """
    async def check_project_type(
        project_id: int,
        db: AsyncSession = Depends(get_db),
        company_id: int = Depends(get_company_id_hybrid)
    ) -> models.Project:
        
        result = await db.execute(
            select(models.Project).where(
                models.Project.project_id == project_id,
                models.Project.company_id == company_id
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
            
        if project.project_type != required_type:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This operation is only available for {required_type} projects (current: {project.project_type})"
            )
            
        return project

    return check_project_type
