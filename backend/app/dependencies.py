"""Shared FastAPI dependencies."""

from fastapi import Depends
from app.db.connection import SurrealDBManager
import app.db.manager as db_manager_module


async def get_db() -> SurrealDBManager:
    """Dependency to get SurrealDB manager."""
    if db_manager_module.db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager_module.db_manager
