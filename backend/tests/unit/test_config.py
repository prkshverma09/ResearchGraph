"""Unit tests for configuration module."""

import os
import pytest
from pydantic import ValidationError


def test_settings_loads_defaults():
    """Settings should load with sensible defaults."""
    from app.config import Settings
    
    # Set minimal required env vars
    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ.pop("SURREALDB_URL", None)  # Should use default
    
    settings = Settings()
    assert settings.openai_api_key == "test-key"
    assert settings.surrealdb_url == "ws://localhost:8000/rpc"  # Default
    assert settings.surrealdb_namespace == "researchgraph"  # Default
    assert settings.surrealdb_database == "main"  # Default


def test_settings_requires_openai_key():
    """Settings should require OPENAI_API_KEY."""
    from app.config import Settings
    
    # Remove OPENAI_API_KEY if present
    os.environ.pop("OPENAI_API_KEY", None)
    
    with pytest.raises(ValidationError):
        Settings()


def test_settings_loads_from_env():
    """Settings should load values from environment variables."""
    from app.config import Settings
    
    os.environ["OPENAI_API_KEY"] = "sk-test123"
    os.environ["SURREALDB_URL"] = "ws://custom:9000/rpc"
    os.environ["SURREALDB_USER"] = "admin"
    os.environ["SURREALDB_PASSWORD"] = "secret"
    os.environ["SURREALDB_NAMESPACE"] = "test-ns"
    os.environ["SURREALDB_DATABASE"] = "test-db"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = "ls-test123"
    
    settings = Settings()
    assert settings.openai_api_key == "sk-test123"
    assert settings.surrealdb_url == "ws://custom:9000/rpc"
    assert settings.surrealdb_user == "admin"
    assert settings.surrealdb_password == "secret"
    assert settings.surrealdb_namespace == "test-ns"
    assert settings.surrealdb_database == "test-db"
    assert settings.langchain_tracing_v2 is True
    assert settings.langchain_api_key == "ls-test123"
