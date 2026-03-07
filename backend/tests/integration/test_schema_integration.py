"""Integration tests for schema module (requires running SurrealDB)."""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_apply_schema_creates_tables(db_manager):
    """apply_schema should create all required tables."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    # Verify tables exist by querying them
    result = await db_manager.execute("INFO FOR DB")
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_apply_schema_is_idempotent(db_manager):
    """Running apply_schema twice should not error."""
    from app.db.schema import apply_schema
    
    # First application
    await apply_schema(db_manager)
    
    # Second application should not raise
    await apply_schema(db_manager)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schema_supports_paper_creation(db_manager):
    """Should be able to CREATE a paper record after schema is applied."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    # Try to create a paper
    result = await db_manager.execute(
        "CREATE paper SET title = 'Test Paper', abstract = 'Test abstract', year = 2024"
    )
    assert len(result) > 0
    assert result[0]["title"] == "Test Paper"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schema_supports_graph_relations(db_manager):
    """Should be able to RELATE paper->cites->paper after schema is applied."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    # Create two papers
    paper_a = await db_manager.execute(
        "CREATE paper SET title = 'Paper A', abstract = 'Abstract A', year = 2024"
    )
    paper_b = await db_manager.execute(
        "CREATE paper SET title = 'Paper B', abstract = 'Abstract B', year = 2024"
    )
    
    paper_a_id = paper_a[0]["id"]
    paper_b_id = paper_b[0]["id"]
    
    # Create citation relation
    result = await db_manager.execute(
        f"RELATE {paper_a_id}->cites->{paper_b_id}"
    )
    assert len(result) > 0
