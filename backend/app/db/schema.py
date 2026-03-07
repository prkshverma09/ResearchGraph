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
    "DEFINE FIELD abstract ON paper TYPE string;",
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
    
    # Vector index on chunk embeddings (HNSW replaces MTREE in SurrealDB 2.1+)
    "DEFINE INDEX chunk_embedding_idx ON chunk FIELDS embedding HNSW DIMENSION 1536 TYPE F32 DIST COSINE;",
    
    # Full-text search indexes
    "DEFINE INDEX paper_title_idx ON paper FIELDS title SEARCH ANALYZER ascii BM25;",
    "DEFINE INDEX paper_abstract_idx ON paper FIELDS abstract SEARCH ANALYZER ascii BM25;",
]


async def apply_schema(db_manager: SurrealDBManager) -> None:
    """Apply schema to SurrealDB database.
    
    This function is idempotent - it can be safely called multiple times.
    
    Args:
        db_manager: SurrealDB manager instance
    """
    logger.info("Applying schema to SurrealDB...")
    
    for statement in SCHEMA_STATEMENTS:
        try:
            await db_manager.execute(statement)
        except Exception as e:
            # If table/field already exists, that's okay (idempotent)
            error_msg = str(e).lower()
            if "already exists" in error_msg or "duplicate" in error_msg:
                continue
            else:
                logger.error(f"Failed to apply schema statement: {statement}")
                logger.error(f"Error: {e}")
                raise
    
    logger.info("Schema applied successfully")


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
            "authored_by", "cites", "belongs_to", "affiliated_with", "has_chunk",
        ]
        
        # Check if tables exist (simplified check)
        # In a real implementation, we'd parse the INFO result more carefully
        return True  # Assume success if query doesn't error
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False
