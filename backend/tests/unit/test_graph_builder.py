"""Unit tests for graph builder module."""

import pytest
from app.models.domain import ExtractedEntities, ExtractedAuthor

pytestmark = pytest.mark.unit


def test_build_paper_node_generates_valid_surrealql():
    """Paper node SurrealQL should include title, abstract, year."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Test Paper: Machine Learning Advances",
        authors=[],
        topics=[],
        institutions=[],
        citations=[],
        year=2024,
        venue="ICLR",
    )
    
    statement = builder.build_paper_node(entities)
    
    assert isinstance(statement, str)
    assert "CREATE" in statement.upper()
    assert "paper:" in statement.lower()
    assert "title" in statement.lower()
    assert "Test Paper: Machine Learning Advances" in statement
    assert "year" in statement.lower()
    assert "2024" in statement
    assert "venue" in statement.lower()
    assert "ICLR" in statement


def test_build_paper_node_without_optional_fields():
    """Paper node should handle missing optional fields."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Minimal Paper",
        authors=[],
        topics=[],
        institutions=[],
        citations=[],
    )
    
    statement = builder.build_paper_node(entities)
    
    assert isinstance(statement, str)
    assert "CREATE" in statement.upper()
    assert "title" in statement.lower()
    assert "Minimal Paper" in statement
    # Should not include year or venue if not provided
    assert "year" not in statement.lower() or "NULL" in statement.upper()


def test_build_author_nodes_generates_valid_surrealql():
    """Author node should include name and institution."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[
            ExtractedAuthor(name="Alice Researcher", institution="MIT"),
            ExtractedAuthor(name="Bob Scientist", institution="Stanford"),
        ],
        topics=[],
        institutions=[],
        citations=[],
    )
    
    statements = builder.build_author_nodes(entities)
    
    assert isinstance(statements, list)
    assert len(statements) == 2
    
    for statement in statements:
        assert isinstance(statement, str)
        assert "CREATE" in statement.upper()
        assert "author:" in statement.lower()
        assert "name" in statement.lower()
    
    # Check that both authors are included
    statements_text = " ".join(statements)
    assert "Alice Researcher" in statements_text
    assert "Bob Scientist" in statements_text
    assert "MIT" in statements_text
    assert "Stanford" in statements_text


def test_build_author_nodes_without_institution():
    """Author nodes should handle missing institution."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[
            ExtractedAuthor(name="Independent Researcher"),
        ],
        topics=[],
        institutions=[],
        citations=[],
    )
    
    statements = builder.build_author_nodes(entities)
    
    assert len(statements) == 1
    assert "Independent Researcher" in statements[0]
    assert "name" in statements[0].lower()


def test_build_topic_nodes_generates_valid_surrealql():
    """Topic nodes should be created for each topic."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[],
        topics=["Machine Learning", "Neural Networks"],
        institutions=[],
        citations=[],
    )
    
    statements = builder.build_topic_nodes(entities)
    
    assert isinstance(statements, list)
    assert len(statements) == 2
    
    for statement in statements:
        assert isinstance(statement, str)
        assert "CREATE" in statement.upper()
        assert "topic:" in statement.lower()
        assert "name" in statement.lower()
    
    statements_text = " ".join(statements)
    assert "Machine Learning" in statements_text
    assert "Neural Networks" in statements_text


def test_build_institution_nodes_generates_valid_surrealql():
    """Institution nodes should be created for each institution."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[],
        topics=[],
        institutions=["MIT", "Stanford"],
        citations=[],
    )
    
    statements = builder.build_institution_nodes(entities)
    
    assert isinstance(statements, list)
    assert len(statements) == 2
    
    for statement in statements:
        assert isinstance(statement, str)
        assert "CREATE" in statement.upper()
        assert "institution:" in statement.lower()
        assert "name" in statement.lower()
    
    statements_text = " ".join(statements)
    assert "MIT" in statements_text
    assert "Stanford" in statements_text


def test_build_authored_by_edge():
    """Should generate RELATE paper->authored_by->author."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    paper_id = "paper:test123"
    author_ids = ["author:alice", "author:bob"]
    
    statements = builder.build_authored_by_edges(paper_id, author_ids)
    
    assert isinstance(statements, list)
    assert len(statements) == 2
    
    for statement in statements:
        assert isinstance(statement, str)
        assert "RELATE" in statement.upper()
        assert "authored_by" in statement.lower()
        assert paper_id in statement
    
    # Check both authors are connected
    statements_text = " ".join(statements)
    assert "author:alice" in statements_text
    assert "author:bob" in statements_text


def test_build_cites_edge():
    """Should generate RELATE paper->cites->paper."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    paper_id = "paper:test123"
    cited_paper_ids = ["paper:cited1", "paper:cited2"]
    
    statements = builder.build_cites_edges(paper_id, cited_paper_ids)
    
    assert isinstance(statements, list)
    assert len(statements) == 2
    
    for statement in statements:
        assert isinstance(statement, str)
        assert "RELATE" in statement.upper()
        assert "cites" in statement.lower()
        assert paper_id in statement
    
    statements_text = " ".join(statements)
    assert "paper:cited1" in statements_text
    assert "paper:cited2" in statements_text


def test_build_belongs_to_edge():
    """Should generate RELATE paper->belongs_to->topic."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    paper_id = "paper:test123"
    topic_ids = ["topic:ml", "topic:nn"]
    
    statements = builder.build_belongs_to_edges(paper_id, topic_ids)
    
    assert isinstance(statements, list)
    assert len(statements) == 2
    
    for statement in statements:
        assert isinstance(statement, str)
        assert "RELATE" in statement.upper()
        assert "belongs_to" in statement.lower()
        assert paper_id in statement
    
    statements_text = " ".join(statements)
    assert "topic:ml" in statements_text
    assert "topic:nn" in statements_text


def test_build_affiliated_with_edge():
    """Should generate RELATE author->affiliated_with->institution."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    author_id = "author:alice"
    institution_id = "institution:mit"
    
    statement = builder.build_affiliated_with_edge(author_id, institution_id)
    
    assert isinstance(statement, str)
    assert "RELATE" in statement.upper()
    assert "affiliated_with" in statement.lower()
    assert author_id in statement
    assert institution_id in statement


def test_deduplication_generates_deterministic_ids():
    """Same author name should always produce the same node ID."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    
    # Generate ID for same author multiple times
    author_name = "Alice Researcher"
    id1 = builder._generate_author_id(author_name)
    id2 = builder._generate_author_id(author_name)
    
    assert id1 == id2
    assert id1.startswith("author:")
    
    # Different authors should have different IDs
    id3 = builder._generate_author_id("Bob Scientist")
    assert id1 != id3


def test_deduplication_generates_deterministic_paper_id():
    """Same paper title should always produce the same node ID."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    
    title = "Test Paper: Machine Learning Advances"
    id1 = builder._generate_paper_id(title)
    id2 = builder._generate_paper_id(title)
    
    assert id1 == id2
    assert id1.startswith("paper:")


def test_deduplication_generates_deterministic_topic_id():
    """Same topic name should always produce the same node ID."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    
    topic_name = "Machine Learning"
    id1 = builder._generate_topic_id(topic_name)
    id2 = builder._generate_topic_id(topic_name)
    
    assert id1 == id2
    assert id1.startswith("topic:")


def test_deduplication_generates_deterministic_institution_id():
    """Same institution name should always produce the same node ID."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    
    institution_name = "MIT"
    id1 = builder._generate_institution_id(institution_name)
    id2 = builder._generate_institution_id(institution_name)
    
    assert id1 == id2
    assert id1.startswith("institution:")


def test_build_graph_handles_missing_optional_fields():
    """Builder should handle entities with None year, venue, etc."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Minimal Paper",
        authors=[
            ExtractedAuthor(name="Author Without Institution"),
        ],
        topics=["Topic 1"],
        institutions=[],
        citations=[],
    )
    
    # Should not raise exceptions
    paper_stmt = builder.build_paper_node(entities)
    author_stmts = builder.build_author_nodes(entities)
    topic_stmts = builder.build_topic_nodes(entities)
    institution_stmts = builder.build_institution_nodes(entities)
    
    assert isinstance(paper_stmt, str)
    assert len(author_stmts) == 1
    assert len(topic_stmts) == 1
    assert len(institution_stmts) == 0


def test_build_graph_handles_empty_lists():
    """Builder should handle empty author/topic/institution lists."""
    from app.ingestion.graph_builder import GraphBuilder
    
    builder = GraphBuilder()
    entities = ExtractedEntities(
        title="Paper Without Entities",
        authors=[],
        topics=[],
        institutions=[],
        citations=[],
    )
    
    author_stmts = builder.build_author_nodes(entities)
    topic_stmts = builder.build_topic_nodes(entities)
    institution_stmts = builder.build_institution_nodes(entities)
    
    assert author_stmts == []
    assert topic_stmts == []
    assert institution_stmts == []


def test_normalize_citation_title_preserves_human_readable_titles():
    """Title-like citations should survive normalization."""
    from app.ingestion.graph_builder import GraphBuilder

    builder = GraphBuilder()

    assert (
        builder.normalize_citation_title(" Attention Is All You Need ")
        == "Attention Is All You Need"
    )


def test_normalize_citation_title_rejects_arxiv_identifier_only_values():
    """Identifier-only arXiv placeholders should be rejected."""
    from app.ingestion.graph_builder import GraphBuilder

    builder = GraphBuilder()

    assert builder.normalize_citation_title("arXiv:1706.03762v7 [cs.CL]") is None


def test_normalize_citation_title_rejects_doi_and_url_only_values():
    """DOI-only and URL-only citations should be rejected."""
    from app.ingestion.graph_builder import GraphBuilder

    builder = GraphBuilder()

    assert builder.normalize_citation_title("10.48550/arXiv.1706.03762") is None
    assert builder.normalize_citation_title("https://arxiv.org/abs/1706.03762") is None


def test_normalize_citation_title_rejects_blank_and_symbol_heavy_values():
    """Blank and non-title strings should be rejected."""
    from app.ingestion.graph_builder import GraphBuilder

    builder = GraphBuilder()

    assert builder.normalize_citation_title("   ") is None
    assert builder.normalize_citation_title("[cs.CL]") is None


def test_build_citation_stub_nodes_only_persists_meaningful_citations():
    """Only meaningful citation titles should produce stub paper nodes."""
    from app.ingestion.graph_builder import GraphBuilder

    builder = GraphBuilder()

    statements = builder.build_citation_stub_nodes(
        [
            "Attention Is All You Need",
            "arXiv:1706.03762v7 [cs.CL]",
            "10.48550/arXiv.1706.03762",
            "https://arxiv.org/abs/1706.03762",
            "  ",
        ]
    )

    assert len(statements) == 1
    assert "Attention Is All You Need" in statements[0]
