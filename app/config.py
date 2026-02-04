"""
Application configuration using Pydantic Settings.
Loads environment variables and provides centralized config access.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    groq_api_key: str = Field(..., alias="GROQ_API_KEY")
    
    # Supabase Configuration
    # supabase_url: str = Field(..., alias="SUPABASE_URL")
    # supabase_key: str = Field(..., alias="SUPABASE_KEY")
    # supabase_service_key: str = Field(..., alias="SUPABASE_SERVICE_KEY")
    
    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    
    # Application Settings
    app_name: str = "Watchtower AI"
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Session Settings
    session_token_expire_hours: int = Field(default=24 * 7, alias="SESSION_TOKEN_EXPIRE_HOURS")  # 7 days
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()
