"""Unit tests for agent state schema."""

import pytest
from typing import List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.agent.state import ResearchAgentState, add_messages


def test_agent_state_initializes():
    """ResearchAgentState should initialize with required fields."""
    state: ResearchAgentState = {
        "messages": [],
        "query": "",
        "search_results": [],
        "graph_results": [],
        "citation_path": [],
        "final_answer": "",
        "session_id": "",
    }
    
    assert state["messages"] == []
    assert state["query"] == ""
    assert state["search_results"] == []
    assert state["graph_results"] == []
    assert state["citation_path"] == []
    assert state["final_answer"] == ""
    assert state["session_id"] == ""


def test_agent_state_accumulates_messages():
    """Messages should be appended via add_messages reducer."""
    existing_messages: List[BaseMessage] = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
    ]
    
    new_messages: List[BaseMessage] = [
        HumanMessage(content="How are you?"),
    ]
    
    result = add_messages(existing_messages, new_messages)
    
    assert len(result) == 3
    assert result[0].content == "Hello"
    assert result[1].content == "Hi there!"
    assert result[2].content == "How are you?"


def test_add_messages_handles_empty_existing():
    """add_messages should work when existing messages list is empty."""
    existing_messages: List[BaseMessage] = []
    new_messages: List[BaseMessage] = [HumanMessage(content="First message")]
    
    result = add_messages(existing_messages, new_messages)
    
    assert len(result) == 1
    assert result[0].content == "First message"


def test_add_messages_handles_empty_new():
    """add_messages should return existing messages when new list is empty."""
    existing_messages: List[BaseMessage] = [HumanMessage(content="Existing")]
    new_messages: List[BaseMessage] = []
    
    result = add_messages(existing_messages, new_messages)
    
    assert len(result) == 1
    assert result[0].content == "Existing"


def test_agent_state_with_data():
    """ResearchAgentState should support all field types."""
    state: ResearchAgentState = {
        "messages": [HumanMessage(content="Test query")],
        "query": "Find papers about transformers",
        "search_results": [
            {"title": "Paper 1", "abstract": "Abstract 1", "relevance_score": 0.95}
        ],
        "graph_results": [
            {"type": "author_papers", "papers": [{"title": "Paper 2"}]}
        ],
        "citation_path": [
            {"title": "Paper A"},
            {"title": "Paper B"},
        ],
        "final_answer": "Here are some papers about transformers...",
        "session_id": "session_123",
    }
    
    assert state["query"] == "Find papers about transformers"
    assert len(state["search_results"]) == 1
    assert len(state["graph_results"]) == 1
    assert len(state["citation_path"]) == 2
    assert state["final_answer"] != ""
    assert state["session_id"] == "session_123"
