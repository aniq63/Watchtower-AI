from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import warnings

from app.database.connection import get_db
from app.database import models, schemas
from app.utils.auth import hash_password, verify_password, generate_session_token, get_current_user

warnings.filterwarnings("ignore")

router = APIRouter(
    prefix="/User-Authentication",
    tags=["User Authentication"]
)


@router.get('/')
async def home():
    """Welcome endpoint."""
    return {"message": "Welcome to Watchtower AI"}


@router.post("/register_company", response_model=schemas.CompanyResponse)
async def register(
    user: schemas.CompanyCreate,
    db: AsyncSession = Depends(get_db)
):

    # Check if user already exists
    result = await db.execute(
        select(models.Company).where(
            (models.Company.name == user.name) | (models.Company.email == user.email) | (models.Company.company_name == user.company_name)
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Company with this name or email already exists"
        )
    
    # Hash password before storing
    hashed_password = hash_password(user.password)
    
    # Create new user
    new_user = models.Company(
        name=user.name,
        password=hashed_password,
        email=user.email,
        company_name=user.company_name
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.post('/company_login', response_model=schemas.TokenResponse)
async def login(
    user: schemas.LoginUser,
    db: AsyncSession = Depends(get_db)
):
    """
    Login user and generate session token.
    
    Args:
        user: Login credentials
        db: Database session
        
    Returns:
        Session token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by name
    result = await db.execute(
        select(models.Company).where(models.Company.name == user.name)
    )
    user_record = result.scalar_one_or_none()
    
    if not user_record:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Verify password
    if not verify_password(user.password, user_record.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Generate and store session token
    token = generate_session_token()
    user_record.session_token = token
    
    await db.commit()
    await db.refresh(user_record)
    
    return {"access_token": token, "token_type": "simple"}


@router.get("/me", response_model=schemas.CompanyResponse)
async def me(current_user: models.Company = Depends(get_current_user)):
    """
    Get current user information.
    
    Args:
        current_user: Authenticated user from dependency
        
    Returns:
        User data
    """
    return current_user


@router.post("/logout_company", response_model=schemas.MessageResponse)
async def logout(
    current_user: models.Company = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user by clearing session token.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    current_user.session_token = None
    await db.commit()
    
    return {"message": "Logged out successfully"}
