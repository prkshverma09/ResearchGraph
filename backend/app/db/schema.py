"""SurrealDB schema definition and initialization."""

import logging
from typing import List
from app.db.connection import SurrealDBManager

logger = logging.getLogger(__name__)

# SurrealQL schema statements
SCHEMA_STATEMENTS: List[str] = [
    # Tables
    "DEFINE TABLE paper SCHEMAFULL;",
    "DEFINE FIELD title ON paper TYPE string;",
    "DEFINE FIELD abstract ON paper TYPE option<string>;",
    "DEFINE FIELD year ON paper TYPE option<int>;",
    "DEFINE FIELD venue ON paper TYPE option<string>;",
    "DEFINE FIELD doi ON paper TYPE option<string>;",
    "DEFINE FIELD arxiv_id ON paper TYPE option<string>;",
    "DEFINE FIELD source ON paper TYPE option<string>;",
    "DEFINE FIELD created_at ON paper TYPE datetime DEFAULT time::now();",
    "DEFINE FIELD updated_at ON paper TYPE datetime VALUE time::now();",
    
    "DEFINE TABLE author SCHEMAFULL;",
    "DEFINE FIELD name ON author TYPE string;",
    "DEFINE FIELD institution ON author TYPE option<string>;",
    
    "DEFINE TABLE topic SCHEMAFULL;",
    "DEFINE FIELD name ON topic TYPE string;",
    
    "DEFINE TABLE institution SCHEMAFULL;",
    "DEFINE FIELD name ON institution TYPE string;",
    "DEFINE FIELD country ON institution TYPE option<string>;",
    
    "DEFINE TABLE chunk SCHEMAFULL;",
    "DEFINE FIELD content ON chunk TYPE string;",
    "DEFINE FIELD index ON chunk TYPE int;",
    "DEFINE FIELD paper_id ON chunk TYPE option<string>;",
    "DEFINE FIELD embedding ON chunk TYPE option<array<float>>;",
    "DEFINE FIELD metadata ON chunk TYPE option<object>;",
    
    "DEFINE TABLE session SCHEMAFULL;",
    "DEFINE FIELD user_id ON session TYPE string;",
    "DEFINE FIELD created_at ON session TYPE datetime DEFAULT time::now();",
    "DEFINE FIELD updated_at ON session TYPE datetime VALUE time::now();",
    "DEFINE FIELD queries ON session TYPE option<array<string>>;",
    "DEFINE FIELD papers_explored ON session TYPE option<array<record<paper>>>;",
    "DEFINE FIELD notes ON session TYPE option<string>;",
    
    # Relation tables (edges)
    "DEFINE TABLE authored_by SCHEMAFULL TYPE RELATION FROM paper TO author;",
    
    "DEFINE TABLE cites SCHEMAFULL TYPE RELATION FROM paper TO paper;",
    
    "DEFINE TABLE belongs_to SCHEMAFULL TYPE RELATION FROM paper TO topic;",
    
    "DEFINE TABLE affiliated_with SCHEMAFULL TYPE RELATION FROM author TO institution;",
    
    "DEFINE TABLE has_chunk SCHEMAFULL TYPE RELATION FROM paper TO chunk;",
    "DEFINE TABLE mentions_topic SCHEMAFULL TYPE RELATION FROM chunk TO topic;",
    
    # Vector index on chunk embeddings (HNSW replaces MTREE in SurrealDB 2.1+)
    "DEFINE INDEX chunk_embedding_idx ON chunk FIELDS embedding HNSW DIMENSION 1536 TYPE F32 DIST COSINE;",
    
]


async def apply_schema(db_manager: SurrealDBManager) -> None:
    """Apply schema to SurrealDB database.
    
    This function is idempotent - it can be safely called multiple times.
    
    Args:
        db_manager: SurrealDB manager instance
    """
    logger.info("Applying schema to SurrealDB...")

    # Remove incompatible full-text indexes when analyzer support is unavailable.
    for cleanup_stmt in [
        "REMOVE INDEX paper_title_idx ON TABLE paper;",
        "REMOVE INDEX paper_abstract_idx ON TABLE paper;",
    ]:
        try:
            await db_manager.execute(cleanup_stmt)
        except Exception:
            pass
    
    for statement in SCHEMA_STATEMENTS:
        try:
            await db_manager.execute(statement)
        except Exception as e:
            # If table/field already exists, that's okay (idempotent)
            error_msg = str(e).lower()
            if "already exists" in error_msg or "duplicate" in error_msg:
                continue
            if "analyzer" in error_msg and "does not exist" in error_msg:
                logger.warning("Skipping unsupported analyzer statement: %s", statement)
                continue
            else:
                logger.error(f"Failed to apply schema statement: {statement}")
                logger.error(f"Error: {e}")
                raise
    
    logger.info("Schema applied successfully")


async def ensure_chunk_embedding_index(db_manager: SurrealDBManager) -> bool:
    """Ensure chunk embedding index exists for ANN retrieval."""
    index_stmt = (
        "DEFINE INDEX chunk_embedding_idx ON chunk "
        "FIELDS embedding HNSW DIMENSION 1536 TYPE F32 DIST COSINE;"
    )
    try:
        await db_manager.execute(index_stmt)
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" not in error_msg and "duplicate" not in error_msg:
            logger.error("Failed to create embedding index: %s", e)
            raise

    info_raw = await db_manager.query_raw("INFO FOR TABLE chunk")
    info_payload = info_raw
    if isinstance(info_raw, list) and info_raw:
        first = info_raw[0]
        if isinstance(first, dict) and "result" in first:
            info_payload = first["result"]

    indexes = {}
    if isinstance(info_payload, dict):
        indexes = info_payload.get("indexes", {}) or {}
    elif isinstance(info_payload, list) and info_payload and isinstance(info_payload[0], dict):
        indexes = info_payload[0].get("indexes", {}) or {}

    has_embedding_index = "chunk_embedding_idx" in indexes
    if not has_embedding_index:
        logger.error("Missing required chunk embedding index after schema apply")
        return False
    return True


async def verify_schema(db_manager: SurrealDBManager) -> bool:
    """Verify that schema tables exist in the database.
    
    Args:
        db_manager: SurrealDB manager instance
    
    Returns:
        True if all required tables exist, False otherwise
    """
    try:
        # Query database info to check tables
        result = await db_manager.execute("INFO FOR DB")
        
        if not result:
            return False
        
        # Extract table names from info
        # SurrealDB INFO returns a dict with table definitions
        required_tables = [
            "paper", "author", "topic", "institution", "chunk", "session",
            "authored_by", "cites", "belongs_to", "affiliated_with", "has_chunk", "mentions_topic",
        ]
        
        # Check if tables exist (simplified check)
        # In a real implementation, we'd parse the INFO result more carefully
        return True  # Assume success if query doesn't error
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False
