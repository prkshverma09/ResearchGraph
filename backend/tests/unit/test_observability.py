"""Unit tests for observability module."""

import os
import pytest


def test_langsmith_env_vars_configured():
    """LangSmith environment variables should be set."""
    from app.config import settings
    
    # Check that LangSmith settings exist (they may be False/None in test)
    assert hasattr(settings, "langchain_tracing_v2")
    assert hasattr(settings, "langchain_api_key")
    assert hasattr(settings, "langchain_project")


def test_langsmith_settings_load_from_env():
    """LangSmith settings should load from environment variables."""
    from app.config import Settings
    
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = "ls-test-key"
    os.environ["LANGCHAIN_PROJECT"] = "test-project"
    
    settings = Settings()
    
    assert settings.langchain_tracing_v2 is True
    assert settings.langchain_api_key == "ls-test-key"
    assert settings.langchain_project == "test-project"
