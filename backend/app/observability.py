"""LangSmith observability configuration."""

import os
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def setup_langsmith() -> None:
    """Configure LangSmith tracing if enabled."""
    if settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        
        if settings.langchain_api_key:
            os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        
        logger.info(
            f"LangSmith tracing enabled for project: {settings.langchain_project}"
        )
    else:
        logger.debug("LangSmith tracing is disabled")


# Initialize on module import
setup_langsmith()
