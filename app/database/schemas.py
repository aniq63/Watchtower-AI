from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime


# ===== User Schemas =====

class CompanyCreate(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6)
    company_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr


class LoginUser(BaseModel):
    """Schema for user login."""
    name: str
    password: str


class CompanyResponse(BaseModel):
    """Response model for user data."""
    company_id: int
    name: str
    email: str
    company_name: str

    model_config = ConfigDict(from_attributes=True)


# ===== Token Schemas =====

class TokenResponse(BaseModel):
    """Response model for authentication token."""
    access_token: str
    token_type: str = "simple"


# ===== Message Schemas =====

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str

# ===== API Key Schemas =====

class ApiKeyResponse(BaseModel):
    """Response model for API key."""
    api_key: str

# ===== Project Schemas =====

class ProjectCreate(BaseModel):
    """Schema for project creation."""
    project_name: str = Field(..., min_length=1, max_length=100)
    project_description: str = Field(..., min_length=1, max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)

class ProjectResponse(BaseModel):
    """Response model for project data."""
    project_id: int
    project_name: str
    project_description: str
    access_token: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ===== Project Config Schemas =====
class ProjectConfigCreate(BaseModel):
    """Schema for project configuration."""
    baseline_batch_size: int = Field(..., ge=1)
    monitor_batch_size: int = Field(..., ge=1)

    model_config = ConfigDict(from_attributes=True)

class ProjectConfigResponse(BaseModel):
    """Response model for project configuration."""
    project_id: int
    baseline_batch_size: int
    monitor_batch_size: int
