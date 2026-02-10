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
    api_key: Optional[str] = None

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
    project_type: str = Field(default="feature_monitoring", pattern="^(feature_monitoring|llm_monitoring|prediction_monitoring)$")
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(from_attributes=True)

class ProjectResponse(BaseModel):
    """Response model for project data."""
    project_id: int
    project_name: str
    project_description: str
    project_type: str
    total_batches: int
    access_token: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ===== Project Config Schemas =====
# ---------- FEATURE CONFIG SCHEMAS ----------

class FeatureConfigCreate(BaseModel):
    """Schema for creating feature monitoring configuration."""
    baseline_batch_size: int = Field(default=1000, ge=1)
    monitor_batch_size: int = Field(default=500, ge=1)
    monitoring_stage: str = Field(default="model_input")

    model_config = ConfigDict(from_attributes=True)

class FeatureConfigResponse(BaseModel):
    """Response model for feature monitoring configuration."""
    project_id: int
    baseline_batch_size: int
    monitor_batch_size: int
    monitoring_stage: str

    model_config = ConfigDict(from_attributes=True)


# ---------- PREDICTION CONFIG SCHEMAS ----------

class PredictionConfigCreate(BaseModel):
    """Schema for creating prediction monitoring configuration."""
    baseline_batch_size: int = Field(default=1000, ge=1)
    monitor_batch_size: int = Field(default=500, ge=1)

    model_config = ConfigDict(from_attributes=True)

class PredictionConfigResponse(BaseModel):
    """Response model for prediction monitoring configuration."""
    project_id: int
    baseline_batch_size: int
    monitor_batch_size: int

    model_config = ConfigDict(from_attributes=True)


# ===== LLM Monitoring Schemas =====

class LLMConfigCreate(BaseModel):
    """Schema for LLM monitoring configuration."""
    baseline_batch_size: int = Field(default=500, ge=1)
    monitor_batch_size: int = Field(default=250, ge=1)
    toxicity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    token_drift_threshold: float = Field(default=0.15, ge=0.0, le=1.0)

    model_config = ConfigDict(from_attributes=True)


class LLMConfigResponse(BaseModel):
    """Response model for LLM monitoring configuration."""
    project_id: int
    baseline_batch_size: int
    monitor_batch_size: int
    toxicity_threshold: float
    token_drift_threshold: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMInteractionCreate(BaseModel):
    """Schema for logging LLM interaction."""
    project_name: str = Field(..., min_length=1)
    input_text: str = Field(..., min_length=1)
    response_text: str = Field(..., min_length=1)
    metadata: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class LLMInteractionResponse(BaseModel):
    """Response model for logged LLM interaction."""
    id: int
    project_id: int
    row_id: int
    response_token_length: int
    is_toxic: bool
    judge_metrics: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMBaselineInfoResponse(BaseModel):
    """Response model for LLM baseline information."""
    baseline_start_row: int
    baseline_end_row: int
    avg_response_token_length: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMMonitorInfoResponse(BaseModel):
    """Response model for LLM monitor information."""
    monitor_start_row: int
    monitor_end_row: int
    current_avg_token_length: Optional[float] = None
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMDriftResponse(BaseModel):
    """Response model for LLM drift detection result."""
    id: int
    baseline_window: str
    monitor_window: str
    baseline_avg_tokens: float
    monitor_avg_tokens: float
    token_length_change: float
    has_drift: bool
    drift_interpretation: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

