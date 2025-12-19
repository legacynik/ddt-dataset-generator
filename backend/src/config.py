"""Configuration settings for DDT Dataset Generator Backend.

This module uses pydantic-settings to load and validate environment variables
from the .env file located in the project root.
"""

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are loaded from the .env file in the project root directory.
    See .env.example for required variables.
    """

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # =================== DATALAB ===================
    DATALAB_API_KEY: str = Field(..., description="Datalab API key for PDF to markdown conversion")
    DATALAB_API_URL: str = Field(
        default="https://www.datalab.to/api/v1/marker",
        description="Datalab API endpoint URL"
    )

    # =================== AZURE DOCUMENT INTELLIGENCE ===================
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str = Field(
        ...,
        description="Azure Document Intelligence service endpoint"
    )
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str = Field(
        ...,
        description="Azure Document Intelligence API key"
    )

    # =================== GOOGLE GEMINI ===================
    GOOGLE_API_KEY: str = Field(..., description="Google API key for Gemini models")
    GEMINI_MODEL: str = Field(
        default="gemini-2.0-flash-exp",
        description="Gemini model to use for extraction"
    )

    # =================== OPENROUTER (Optional - for multi-LLM) ===================
    OPENROUTER_API_KEY: str = Field(
        default="",
        description="OpenRouter API key for Claude, GPT-4, etc. (optional)"
    )
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )

    # =================== OLLAMA (Optional - for local models) ===================
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL for local models"
    )

    # =================== SUPABASE ===================
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous/public key")
    SUPABASE_SERVICE_KEY: str = Field(..., description="Supabase service role key (for backend)")
    SUPABASE_BUCKET: str = Field(
        default="dataset-pdfs",
        description="Supabase storage bucket name for PDFs"
    )

    # =================== APP CONFIG ===================
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    MAX_PARALLEL_PDFS: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum number of PDFs to process in parallel"
    )

    # =================== API CONFIG ===================
    API_TITLE: str = Field(
        default="DDT Dataset Generator API",
        description="FastAPI application title"
    )
    API_VERSION: str = Field(
        default="1.0.0",
        description="API version"
    )
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )

    @field_validator("DATALAB_API_KEY", "AZURE_DOCUMENT_INTELLIGENCE_KEY", "GOOGLE_API_KEY", "SUPABASE_SERVICE_KEY")
    @classmethod
    def validate_api_keys(cls, v: str) -> str:
        """Ensure API keys are not empty."""
        if not v or v.strip() == "":
            raise ValueError("API key cannot be empty")
        return v.strip()

    @field_validator("SUPABASE_URL", "DATALAB_API_URL", "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    @classmethod
    def validate_urls(cls, v: str) -> str:
        """Ensure URLs are properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")


# Global settings instance
settings = Settings()
