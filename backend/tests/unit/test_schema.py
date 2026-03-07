"""Unit tests for schema module."""

import pytest


def test_schema_statements_are_valid_surrealql():
    """All schema statements should be syntactically valid."""
    from app.db.schema import SCHEMA_STATEMENTS
    
    # Basic validation - check that statements are strings and non-empty
    assert isinstance(SCHEMA_STATEMENTS, list)
    assert len(SCHEMA_STATEMENTS) > 0
    
    for statement in SCHEMA_STATEMENTS:
        assert isinstance(statement, str)
        assert len(statement.strip()) > 0
        # Check for common SurrealQL keywords
        assert any(keyword in statement.upper() for keyword in ["DEFINE", "CREATE", "RELATE"])


def test_schema_includes_all_tables():
    """Schema should define all required tables."""
    from app.db.schema import SCHEMA_STATEMENTS
    
    schema_text = " ".join(SCHEMA_STATEMENTS).upper()
    
    required_tables = ["PAPER", "AUTHOR", "TOPIC", "INSTITUTION", "CHUNK", "SESSION"]
    for table in required_tables:
        assert f"TABLE {table}" in schema_text or f"DEFINE TABLE {table}" in schema_text


def test_schema_includes_all_relations():
    """Schema should define all required relation tables."""
    from app.db.schema import SCHEMA_STATEMENTS
    
    schema_text = " ".join(SCHEMA_STATEMENTS).upper()
    
    required_relations = [
        "AUTHORED_BY",
        "CITES",
        "BELONGS_TO",
        "AFFILIATED_WITH",
        "HAS_CHUNK",
    ]
    for relation in required_relations:
        assert f"TABLE {relation}" in schema_text or f"DEFINE TABLE {relation}" in schema_text


def test_schema_includes_vector_index():
    """Schema should define vector index on chunk embeddings."""
    from app.db.schema import SCHEMA_STATEMENTS
    
    schema_text = " ".join(SCHEMA_STATEMENTS).upper()
    assert "INDEX" in schema_text
    assert "CHUNK" in schema_text
    assert "EMBEDDING" in schema_text
