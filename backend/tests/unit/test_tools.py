"""Unit tests for agent tools module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from app.agent.tools import (
    VectorSearchTool,
    GraphQueryTool,
    CitationPathTool,
    PaperSummarizerTool,
    TopicExplorerTool,
)


@pytest.fixture
def mock_vector_store():
    """Mock VectorStoreService for testing."""
    mock = Mock()
    mock.similarity_search_with_scores = AsyncMock(return_value=[
        (
            Document(
                page_content="Paper about transformers",
                metadata={"paper_id": "paper:1", "title": "Transformer Paper"}
            ),
            0.95
        ),
        (
            Document(
                page_content="Paper about attention mechanisms",
                metadata={"paper_id": "paper:2", "title": "Attention Paper"}
            ),
            0.88
        ),
    ])
    return mock


@pytest.fixture
def mock_db():
    """Mock SurrealDBManager for testing."""
    mock = Mock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def mock_llm():
    """Mock ChatOpenAI for testing."""
    mock = Mock()
    mock.ainvoke = AsyncMock(return_value=AIMessage(content="This is a summary of the paper."))
    return mock


@pytest.mark.asyncio
async def test_vector_search_tool_returns_papers(mock_vector_store):
    """VectorSearchTool should return paper results from similarity search."""
    tool = VectorSearchTool(vector_store_service=mock_vector_store)
    
    result = await tool.ainvoke({"query": "transformers", "top_k": 5})
    
    assert "papers" in result
    assert len(result["papers"]) == 2
    assert result["papers"][0]["title"] == "Transformer Paper"
    assert result["papers"][0]["relevance_score"] == 0.95
    mock_vector_store.similarity_search_with_scores.assert_called_once_with("transformers", k=5)


@pytest.mark.asyncio
async def test_vector_search_tool_respects_top_k(mock_vector_store):
    """VectorSearchTool should limit results to top_k."""
    mock_vector_store.similarity_search_with_scores = AsyncMock(return_value=[
        (Document(page_content=f"Content {i}", metadata={"paper_id": f"paper:{i}", "title": f"Paper {i}"}), 0.9 - i * 0.1)
        for i in range(10)
    ])
    
    tool = VectorSearchTool(vector_store_service=mock_vector_store)
    
    result = await tool.ainvoke({"query": "test", "top_k": 3})
    
    assert len(result["papers"]) == 3
    mock_vector_store.similarity_search_with_scores.assert_called_once_with("test", k=3)


@pytest.mark.asyncio
async def test_graph_query_tool_author_papers(mock_db):
    """GraphQueryTool should return papers by a given author."""
    mock_db.execute = AsyncMock(return_value=[
        {"id": "paper:1", "title": "Paper 1", "year": 2024},
        {"id": "paper:2", "title": "Paper 2", "year": 2023},
    ])
    
    tool = GraphQueryTool(db_manager=mock_db)
    
    result = await tool.ainvoke({
        "query_type": "author_papers",
        "author_name": "Alice Researcher"
    })
    
    assert "papers" in result
    assert len(result["papers"]) == 2
    assert result["papers"][0]["title"] == "Paper 1"
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_graph_query_tool_paper_citations(mock_db):
    """GraphQueryTool should return papers cited by a given paper."""
    mock_db.execute = AsyncMock(return_value=[
        {"id": "paper:3", "title": "Cited Paper 1"},
        {"id": "paper:4", "title": "Cited Paper 2"},
    ])
    
    tool = GraphQueryTool(db_manager=mock_db)
    
    result = await tool.ainvoke({
        "query_type": "paper_citations",
        "paper_title": "Transformer Paper"
    })
    
    assert "citations" in result
    assert len(result["citations"]) == 2
    assert result["citations"][0]["title"] == "Cited Paper 1"
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_graph_query_tool_topic_papers(mock_db):
    """GraphQueryTool should return papers for a given topic."""
    mock_db.execute = AsyncMock(return_value=[
        {"id": "paper:5", "title": "Topic Paper 1"},
        {"id": "paper:6", "title": "Topic Paper 2"},
    ])
    
    tool = GraphQueryTool(db_manager=mock_db)
    
    result = await tool.ainvoke({
        "query_type": "topic_papers",
        "topic": "Machine Learning"
    })
    
    assert "papers" in result
    assert len(result["papers"]) == 2
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_graph_query_tool_coauthors(mock_db):
    """GraphQueryTool should return coauthors for a given author."""
    mock_db.execute = AsyncMock(return_value=[
        {"id": "author:2", "name": "Bob Scientist"},
        {"id": "author:3", "name": "Charlie Researcher"},
    ])
    
    tool = GraphQueryTool(db_manager=mock_db)
    
    result = await tool.ainvoke({
        "query_type": "coauthors",
        "author_name": "Alice Researcher"
    })
    
    assert "coauthors" in result
    assert len(result["coauthors"]) == 2
    assert result["coauthors"][0]["name"] == "Bob Scientist"
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_citation_path_tool_finds_path(mock_db):
    """CitationPathTool should find a path between two connected papers."""
    mock_db.execute = AsyncMock(return_value=[
        {"id": "paper:a", "title": "Paper A"},
        {"id": "paper:b", "title": "Paper B"},
        {"id": "paper:c", "title": "Paper C"},
    ])
    
    tool = CitationPathTool(db_manager=mock_db)
    
    result = await tool.ainvoke({
        "paper_a_title": "Paper A",
        "paper_b_title": "Paper C"
    })
    
    assert "path" in result
    assert len(result["path"]) == 3
    assert result["path"][0]["title"] == "Paper A"
    assert result["path"][-1]["title"] == "Paper C"
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_citation_path_tool_no_path(mock_db):
    """CitationPathTool should return empty when papers are not connected."""
    mock_db.execute = AsyncMock(return_value=[])
    
    tool = CitationPathTool(db_manager=mock_db)
    
    result = await tool.ainvoke({
        "paper_a_title": "Paper X",
        "paper_b_title": "Paper Y"
    })
    
    assert "path" in result
    assert len(result["path"]) == 0
    assert "message" in result
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_paper_summarizer_tool(mock_db, mock_llm):
    """PaperSummarizerTool should return a summary string."""
    mock_db.execute = AsyncMock(return_value=[
        {"content": "Chunk 1 content", "index": 0},
        {"content": "Chunk 2 content", "index": 1},
    ])
    
    tool = PaperSummarizerTool(db_manager=mock_db, llm=mock_llm)
    
    result = await tool.ainvoke({"paper_id": "paper:123"})
    
    assert "summary" in result
    assert result["summary"] == "This is a summary of the paper."
    assert mock_db.execute.call_count >= 1
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_topic_explorer_tool(mock_db, mock_vector_store):
    """TopicExplorerTool should return papers and authors for a topic."""
    mock_vector_store.similarity_search_with_scores = AsyncMock(return_value=[
        (
            Document(
                page_content="Paper about machine learning",
                metadata={"paper_id": "paper:1", "title": "ML Paper 1"}
            ),
            0.92
        ),
    ])
    
    mock_db.execute = AsyncMock(return_value=[
        {"id": "author:1", "name": "Alice Researcher"},
        {"id": "author:2", "name": "Bob Scientist"},
    ])
    
    tool = TopicExplorerTool(
        vector_store_service=mock_vector_store,
        db_manager=mock_db
    )
    
    result = await tool.ainvoke({"topic": "Machine Learning"})
    
    assert "papers" in result
    assert "authors" in result
    assert len(result["papers"]) == 1
    assert len(result["authors"]) == 2
    mock_vector_store.similarity_search_with_scores.assert_called_once()
    mock_db.execute.assert_called_once()


def test_all_tools_have_name_and_description():
    """All tools should have LangChain-compatible name and description."""
    from app.agent.tools import (
        VectorSearchTool,
        GraphQueryTool,
        CitationPathTool,
        PaperSummarizerTool,
        TopicExplorerTool,
    )
    
    mock_vs = Mock()
    mock_db = Mock()
    mock_llm = Mock()
    
    tools = [
        VectorSearchTool(vector_store_service=mock_vs),
        GraphQueryTool(db_manager=mock_db),
        CitationPathTool(db_manager=mock_db),
        PaperSummarizerTool(db_manager=mock_db, llm=mock_llm),
        TopicExplorerTool(vector_store_service=mock_vs, db_manager=mock_db),
    ]
    
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert tool.name is not None
        assert tool.description is not None
        assert len(tool.name) > 0
        assert len(tool.description) > 0


def test_all_tools_have_input_schema():
    """All tools should define their input schema for the agent."""
    from app.agent.tools import (
        VectorSearchTool,
        GraphQueryTool,
        CitationPathTool,
        PaperSummarizerTool,
        TopicExplorerTool,
    )
    
    mock_vs = Mock()
    mock_db = Mock()
    mock_llm = Mock()
    
    tools = [
        VectorSearchTool(vector_store_service=mock_vs),
        GraphQueryTool(db_manager=mock_db),
        CitationPathTool(db_manager=mock_db),
        PaperSummarizerTool(db_manager=mock_db, llm=mock_llm),
        TopicExplorerTool(vector_store_service=mock_vs, db_manager=mock_db),
    ]
    
    for tool in tools:
        assert hasattr(tool, "args_schema")
        assert tool.args_schema is not None
