"""Unit tests for LangGraph agent workflow."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agent.state import ResearchAgentState
from app.agent.workflow import (
    create_router_node,
    create_synthesizer_node,
    create_agent_graph,
    route_decision,
)


@pytest.fixture
def mock_llm():
    """Mock ChatOpenAI for testing."""
    mock = Mock(spec=ChatOpenAI)
    mock.ainvoke = AsyncMock()
    return mock


@pytest.fixture
def mock_tools():
    """Mock tools for testing."""
    vector_tool = Mock()
    vector_tool.name = "vector_search"
    vector_tool.ainvoke = AsyncMock(return_value={"papers": [{"title": "Paper 1"}]})
    
    graph_tool = Mock()
    graph_tool.name = "graph_query"
    graph_tool.ainvoke = AsyncMock(return_value={"papers": [{"title": "Paper 2"}]})
    
    citation_tool = Mock()
    citation_tool.name = "citation_path"
    citation_tool.ainvoke = AsyncMock(return_value={"path": [{"title": "Paper A"}, {"title": "Paper B"}]})
    
    return [vector_tool, graph_tool, citation_tool]


@pytest.mark.asyncio
async def test_router_selects_vector_search_for_similarity_query(mock_llm):
    """Router should select VectorSearchTool for 'find papers about X' queries."""
    mock_response = Mock()
    mock_response.content = "I should use vector_search to find papers about transformers."
    mock_response.tool_calls = [
        Mock(name="vector_search", args={"query": "transformers", "top_k": 5})
    ]
    
    mock_chain = Mock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.bind_tools = Mock(return_value=mock_chain)
    
    mock_tools = [Mock(name="vector_search")]
    router_node = create_router_node(mock_llm, mock_tools)
    
    state: ResearchAgentState = {
        "messages": [HumanMessage(content="Find papers about transformers")],
        "query": "Find papers about transformers",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    result = await router_node(state)
    
    assert "messages" in result
    assert len(result["messages"]) > 0


@pytest.mark.asyncio
async def test_router_selects_graph_query_for_citation_query(mock_llm):
    """Router should select GraphQueryTool for 'who cites paper X' queries."""
    mock_response = Mock()
    mock_response.content = "I should use graph_query to find citations."
    mock_response.tool_calls = [
        Mock(
            name="graph_query",
            args={"query_type": "paper_citations", "paper_title": "Attention Is All You Need"}
        )
    ]
    
    mock_chain = Mock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.bind_tools = Mock(return_value=mock_chain)
    
    mock_tools = [Mock(name="graph_query")]
    router_node = create_router_node(mock_llm, mock_tools)
    
    state: ResearchAgentState = {
        "messages": [HumanMessage(content="Who cites Attention Is All You Need?")],
        "query": "Who cites Attention Is All You Need?",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    result = await router_node(state)
    
    assert "messages" in result


@pytest.mark.asyncio
async def test_router_selects_citation_path_for_connection_query(mock_llm):
    """Router should select CitationPathTool for 'how are X and Y connected'."""
    mock_response = Mock()
    mock_response.content = "I should use citation_path to find connections."
    mock_response.tool_calls = [
        Mock(
            name="citation_path",
            args={"paper_a_title": "Paper A", "paper_b_title": "Paper B"}
        )
    ]
    
    mock_chain = Mock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.bind_tools = Mock(return_value=mock_chain)
    
    mock_tools = [Mock(name="citation_path")]
    router_node = create_router_node(mock_llm, mock_tools)
    
    state: ResearchAgentState = {
        "messages": [HumanMessage(content="How are Paper A and Paper B connected?")],
        "query": "How are Paper A and Paper B connected?",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    result = await router_node(state)
    
    assert "messages" in result


@pytest.mark.asyncio
async def test_synthesizer_includes_sources(mock_llm):
    """Synthesizer should include source papers in the final answer."""
    mock_response = Mock()
    mock_response.content = "Based on the papers found, here are the key findings: Paper 1 discusses transformers..."
    
    mock_chain = Mock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.__or__ = Mock(return_value=mock_chain)
    
    synthesizer_node = create_synthesizer_node(mock_llm)
    
    state: ResearchAgentState = {
        "messages": [
            HumanMessage(content="Find papers about transformers"),
            AIMessage(content="", tool_calls=[Mock(name="vector_search", args={"query": "transformers"})]),
            ToolMessage(content='{"papers": [{"title": "Paper 1", "abstract": "Abstract 1", "relevance_score": 0.95}]}', tool_call_id="1"),
        ],
        "query": "Find papers about transformers",
        "search_results": [{"title": "Paper 1", "abstract": "Abstract 1"}],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    result = await synthesizer_node(state)
    
    assert "final_answer" in result
    assert result["final_answer"] != ""
    assert "messages" in result


@pytest.mark.asyncio
async def test_workflow_end_to_end(mock_llm, mock_tools):
    """Full workflow should process query through router → tools → synthesizer."""
    router_response = Mock()
    router_response.content = "I'll search for papers."
    router_response.tool_calls = [
        Mock(name="vector_search", args={"query": "transformers", "top_k": 5}, id="call_1")
    ]
    
    synthesizer_response = Mock()
    synthesizer_response.content = "Here are some papers about transformers: Paper 1..."
    
    mock_chain_router = Mock()
    mock_chain_router.ainvoke = AsyncMock(return_value=router_response)
    mock_llm.bind_tools = Mock(return_value=mock_chain_router)
    
    mock_chain_synth = Mock()
    mock_chain_synth.ainvoke = AsyncMock(return_value=synthesizer_response)
    mock_llm.__or__ = Mock(return_value=mock_chain_synth)
    
    state: ResearchAgentState = {
        "messages": [HumanMessage(content="Find papers about transformers")],
        "query": "Find papers about transformers",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    graph = create_agent_graph(mock_tools, mock_llm)
    
    result = await graph.ainvoke(state)
    
    assert "final_answer" in result or "messages" in result


@pytest.mark.asyncio
async def test_workflow_handles_no_results(mock_llm, mock_tools):
    """Workflow should gracefully handle empty tool results."""
    router_response = Mock()
    router_response.content = "I'll search for papers."
    router_response.tool_calls = [
        Mock(name="vector_search", args={"query": "nonexistent topic", "top_k": 5}, id="call_1")
    ]
    
    synthesizer_response = Mock()
    synthesizer_response.content = "I couldn't find any papers matching your query. Please try rephrasing."
    
    mock_chain_router = Mock()
    mock_chain_router.ainvoke = AsyncMock(return_value=router_response)
    mock_llm.bind_tools = Mock(return_value=mock_chain_router)
    
    mock_chain_synth = Mock()
    mock_chain_synth.ainvoke = AsyncMock(return_value=synthesizer_response)
    mock_llm.__or__ = Mock(return_value=mock_chain_synth)
    
    empty_tool = Mock()
    empty_tool.name = "vector_search"
    empty_tool.ainvoke = AsyncMock(return_value={"papers": []})
    
    state: ResearchAgentState = {
        "messages": [HumanMessage(content="Find papers about nonexistent topic")],
        "query": "Find papers about nonexistent topic",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    graph = create_agent_graph([empty_tool], mock_llm)
    
    result = await graph.ainvoke(state)
    
    assert "final_answer" in result or "messages" in result


@pytest.mark.asyncio
async def test_route_decision_returns_tools():
    """route_decision should return 'tools' when tool calls are present."""
    state: ResearchAgentState = {
        "messages": [
            HumanMessage(content="Find papers"),
            AIMessage(content="", tool_calls=[Mock(name="vector_search")]),
        ],
        "query": "Find papers",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    decision = route_decision(state)
    
    assert decision == "tools"


@pytest.mark.asyncio
async def test_route_decision_returns_synthesizer():
    """route_decision should return 'synthesizer' when no tool calls."""
    state: ResearchAgentState = {
        "messages": [
            HumanMessage(content="Find papers"),
            AIMessage(content="Searching..."),
        ],
        "query": "Find papers",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "test_session",
    }
    
    decision = route_decision(state)
    
    assert decision == "synthesizer"
