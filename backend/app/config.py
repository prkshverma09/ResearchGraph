"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI
    openai_api_key: str
    
    # SurrealDB
    surrealdb_url: str = "ws://localhost:8000/rpc"
    surrealdb_user: str = "root"
    surrealdb_password: str = "root"
    surrealdb_namespace: str = "researchgraph"
    surrealdb_database: str = "main"
    
    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "researchgraph-assistant"
    
    # App
    app_env: str = "development"
    log_level: str = "INFO"
    
    # Checkpointing (workaround for Issue 2: langgraph-checkpoint-surrealdb bug)
    enable_checkpointing: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
