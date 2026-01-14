from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import warnings
import secrets
from app.database.connection import get_db
from app.database import models, schemas
from app.utils.auth import get_current_user


warnings.filterwarnings("ignore")

router = APIRouter(
    prefix="/get_api",
    tags=["Get API"]
)


@router.post('/generate_api_key', response_model=schemas.ApiKeyResponse)
async def generate_api_key(
    current_user : models.Company = Depends(get_current_user),
    db : AsyncSession = Depends(get_db)
):
    # Generate a new random API key
    new_api_key = secrets.token_hex(32)
    
    # Update the current user (Company) with the new API key
    current_user.api_key = new_api_key
    
    await db.commit()
    await db.refresh(current_user)
    
    return {"api_key": new_api_key}
