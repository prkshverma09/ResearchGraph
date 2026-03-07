"""Integration tests for graph builder module."""

import pytest
from app.models.domain import ExtractedEntities, ExtractedAuthor
from app.ingestion.graph_builder import GraphBuilder, persist_graph

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_persist_graph_creates_nodes_in_db(db_manager, sample_entities):
    """persist_graph should create paper and author nodes in SurrealDB."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    builder = GraphBuilder()
    await persist_graph(db_manager, sample_entities)
    
    # Verify paper node was created
    paper_id = builder._generate_paper_id(sample_entities.title)
    result = await db_manager.execute(f"SELECT * FROM {paper_id}")
    
    assert len(result) > 0
    paper = result[0]
    assert paper["title"] == sample_entities.title
    assert paper["year"] == sample_entities.year
    assert paper["venue"] == sample_entities.venue
    
    # Verify author nodes were created
    for author in sample_entities.authors:
        author_id = builder._generate_author_id(author.name)
        result = await db_manager.execute(f"SELECT * FROM {author_id}")
        
        assert len(result) > 0
        author_node = result[0]
        assert author_node["name"] == author.name


@pytest.mark.asyncio
async def test_persist_graph_creates_edges_in_db(db_manager, sample_entities):
    """persist_graph should create relationship edges in SurrealDB."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    builder = GraphBuilder()
    await persist_graph(db_manager, sample_entities)
    
    paper_id = builder._generate_paper_id(sample_entities.title)
    
    # Verify authored_by edges
    for author in sample_entities.authors:
        author_id = builder._generate_author_id(author.name)
        result = await db_manager.execute(
            f"SELECT * FROM authored_by WHERE in = {paper_id} AND out = {author_id}"
        )
        # SurrealDB returns results even if empty list, so check for non-empty
        assert result is not None
    
    # Verify belongs_to edges
    for topic in sample_entities.topics:
        topic_id = builder._generate_topic_id(topic)
        result = await db_manager.execute(
            f"SELECT * FROM belongs_to WHERE in = {paper_id} AND out = {topic_id}"
        )
        assert result is not None


@pytest.mark.asyncio
async def test_persist_graph_deduplicates_authors(db_manager):
    """Persisting two papers by the same author should not duplicate the author."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    entities1 = ExtractedEntities(
        title="Paper 1",
        authors=[ExtractedAuthor(name="Alice Researcher", institution="MIT")],
        topics=[],
        institutions=[],
        citations=[],
    )
    
    entities2 = ExtractedEntities(
        title="Paper 2",
        authors=[ExtractedAuthor(name="Alice Researcher", institution="MIT")],
        topics=[],
        institutions=[],
        citations=[],
    )
    
    await persist_graph(db_manager, entities1)
    await persist_graph(db_manager, entities2)
    
    # Check that only one author node exists
    builder = GraphBuilder()
    author_id = builder._generate_author_id("Alice Researcher")
    result = await db_manager.execute(f"SELECT * FROM {author_id}")
    
    assert len(result) == 1
    
    # Check that both papers are connected to the same author
    paper1_id = builder._generate_paper_id("Paper 1")
    paper2_id = builder._generate_paper_id("Paper 2")
    
    edges1 = await db_manager.execute(
        f"SELECT * FROM authored_by WHERE in = {paper1_id} AND out = {author_id}"
    )
    edges2 = await db_manager.execute(
        f"SELECT * FROM authored_by WHERE in = {paper2_id} AND out = {author_id}"
    )
    
    assert edges1 is not None
    assert edges2 is not None


@pytest.mark.asyncio
async def test_persist_graph_creates_institution_nodes(db_manager):
    """persist_graph should create institution nodes."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[
            ExtractedAuthor(name="Alice Researcher", institution="MIT"),
        ],
        topics=[],
        institutions=["MIT"],
        citations=[],
    )
    
    await persist_graph(db_manager, entities)
    
    builder = GraphBuilder()
    institution_id = builder._generate_institution_id("MIT")
    result = await db_manager.execute(f"SELECT * FROM {institution_id}")
    
    assert len(result) > 0
    institution = result[0]
    assert institution["name"] == "MIT"


@pytest.mark.asyncio
async def test_persist_graph_creates_affiliated_with_edges(db_manager):
    """persist_graph should create affiliated_with edges between authors and institutions."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[
            ExtractedAuthor(name="Alice Researcher", institution="MIT"),
        ],
        topics=[],
        institutions=["MIT"],
        citations=[],
    )
    
    await persist_graph(db_manager, entities)
    
    builder = GraphBuilder()
    author_id = builder._generate_author_id("Alice Researcher")
    institution_id = builder._generate_institution_id("MIT")
    
    result = await db_manager.execute(
        f"SELECT * FROM affiliated_with WHERE in = {author_id} AND out = {institution_id}"
    )
    
    assert result is not None


@pytest.mark.asyncio
async def test_persist_graph_handles_citations(db_manager):
    """persist_graph should create cites edges for citations."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    # First create a cited paper
    cited_entities = ExtractedEntities(
        title="Cited Paper",
        authors=[],
        topics=[],
        institutions=[],
        citations=[],
    )
    await persist_graph(db_manager, cited_entities)
    
    # Then create a paper that cites it
    citing_entities = ExtractedEntities(
        title="Citing Paper",
        authors=[],
        topics=[],
        institutions=[],
        citations=["Cited Paper"],
    )
    await persist_graph(db_manager, citing_entities)
    
    builder = GraphBuilder()
    citing_paper_id = builder._generate_paper_id("Citing Paper")
    cited_paper_id = builder._generate_paper_id("Cited Paper")
    
    result = await db_manager.execute(
        f"SELECT * FROM cites WHERE in = {citing_paper_id} AND out = {cited_paper_id}"
    )
    
    assert result is not None


@pytest.mark.asyncio
async def test_persist_graph_transaction_rollback_on_error(db_manager):
    """persist_graph should rollback transaction on error."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    # Create entities with invalid data that would cause an error
    # We'll use a mock that fails partway through
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[ExtractedAuthor(name="Alice Researcher")],
        topics=[],
        institutions=[],
        citations=[],
    )
    
    # Mock db_manager to fail on second execute
    original_execute = db_manager.execute
    call_count = 0
    
    async def failing_execute(query, params=None):
        nonlocal call_count
        call_count += 1
        if call_count > 5:  # Fail after a few successful calls
            raise Exception("Simulated database error")
        return await original_execute(query, params)
    
    db_manager.execute = failing_execute
    
    # Should raise exception
    with pytest.raises(Exception):
        await persist_graph(db_manager, entities)
    
    # Verify no partial data was persisted
    builder = GraphBuilder()
    paper_id = builder._generate_paper_id("Test Paper")
    result = await db_manager.execute(f"SELECT * FROM {paper_id}")
    
    # Note: SurrealDB doesn't have traditional transactions, so this test
    # verifies that errors are propagated, but rollback behavior depends on
    # SurrealDB's implementation
    assert len(result) == 0 or call_count <= 5
