"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import SurrealDBManager
from app.db.manager import db_manager
from app.config import settings
from app.models.schemas import HealthResponse
from app.observability import setup_langsmith
from app.db.schema import apply_schema, ensure_chunk_embedding_index
from app.api import (
    routes_ingest,
    routes_search,
    routes_ask,
    routes_graph,
    routes_citation,
    routes_sessions,
)
import logging

logger = logging.getLogger(__name__)
vector_index_ready = False

# Setup LangSmith observability
setup_langsmith()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler for startup/shutdown."""
    import app.db.manager as db_manager_module
    
    # Startup
    logger.info("Starting ResearchGraph Assistant...")
    db_manager_instance = SurrealDBManager(
        url=settings.surrealdb_url,
        user=settings.surrealdb_user,
        password=settings.surrealdb_password,
        namespace=settings.surrealdb_namespace,
        database=settings.surrealdb_database,
    )
    # Update the module-level db_manager
    db_manager_module.db_manager = db_manager_instance
    
    global vector_index_ready
    try:
        await db_manager_instance.connect()
        await apply_schema(db_manager_instance)
        vector_index_ready = await ensure_chunk_embedding_index(db_manager_instance)
        if not vector_index_ready:
            raise RuntimeError("chunk embedding index is not ready")
        logger.info("SurrealDB connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to SurrealDB: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ResearchGraph Assistant...")
    if db_manager_instance:
        await db_manager_instance.disconnect()
    db_manager_module.db_manager = None
    logger.info("Shutdown complete")


app = FastAPI(
    title="ResearchGraph Assistant",
    description="AI-powered research exploration platform with knowledge graphs",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(routes_ingest.router)
app.include_router(routes_search.router)
app.include_router(routes_ask.router)
app.include_router(routes_graph.router)
app.include_router(routes_citation.router)
app.include_router(routes_sessions.router)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import app.db.manager as db_manager_module
    db_connected = False
    if db_manager_module.db_manager:
        db_connected = await db_manager_module.db_manager.health_check()
    
    return HealthResponse(
        status="ok" if (db_connected and vector_index_ready) else "error",
        db_connected=db_connected,
        vector_index_ready=vector_index_ready,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
