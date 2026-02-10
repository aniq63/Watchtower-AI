"""
Authentication utilities for password hashing and session management.
"""
import uuid
import bcrypt
from typing import Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import Company, Project
from app.database.connection import get_db
from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def generate_session_token() -> str:
    """
    Generate a unique session token.
    
    Returns:
        Unique session token string
    """
    return uuid.uuid4().hex


async def get_current_user(
    session_token: Optional[str] = Header(None, alias="session_token"),
    db: AsyncSession = Depends(get_db)
) -> Company:
    """
    Dependency to get current authenticated user from session token.
    
    Args:
        session_token: Session token from header
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is missing, invalid or expired
    """
    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Session token is missing"
        )
    result = await db.execute(
        select(Company).where(Company.session_token == session_token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token"
        )
    
    return user


async def get_current_user_from_query(
    session_token: str,
    db: AsyncSession = Depends(get_db)
) -> Company:
    """
    Get current user from query parameter (for endpoints that use query params).
    
    Args:
        session_token: Session token from query parameter
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid
    """
    result = await db.execute(
        select(Company).where(Company.session_token == session_token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token"
        )
    
    return user


async def verify_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    Dependency to verify API key and return company_id.
    
    Args:
        api_key: API key from header
        db: Database session
        
    Returns:
        Company ID
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is missing. Please provide X-API-Key header."
        )
    
    result = await db.execute(
        select(Company).where(Company.api_key == api_key)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return company.company_id


async def get_current_project(
    access_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    current_user: Company = Depends(get_current_user)
) -> Project:
    """
    Dependency to get current project from access_token header.
    Verifies that the project belongs to the current authenticated user.
    """
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Access token is missing"
        )
    result = await db.execute(
        select(Project).where(
            Project.access_token == access_token,
            Project.company_id == current_user.company_id
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=401,
            detail="Invalid project_id or access_token, or you don't have access to this project"
        )
    
    return project
