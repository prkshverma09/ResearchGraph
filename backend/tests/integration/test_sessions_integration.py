"""Integration tests for session management (requires running SurrealDB)."""

import pytest
from datetime import datetime
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_state_persists_across_invocations(db_manager):
    """Agent should remember previous messages when called with same session_id."""
    from app.agent.sessions import create_session, get_checkpointer
    from langgraph.graph import StateGraph, START, END
    from pydantic import BaseModel, Field
    from typing import Annotated
    import operator
    
    await db_manager.connect()
    
    try:
        session_id = await create_session("test_user", db_manager=db_manager)
        checkpointer = get_checkpointer()
        
        class ThreadState(BaseModel):
            messages: Annotated[list, operator.add] = Field(default_factory=list)
        
        def simple_node(state: ThreadState) -> Dict[str, Any]:
            if not state.messages:
                return {"messages": ["Hello"]}
            last_msg = state.messages[-1] if state.messages else ""
            return {"messages": [f"Echo: {last_msg}"]}
        
        graph_builder = StateGraph(ThreadState)
        graph_builder.add_node("simple", simple_node)
        graph_builder.add_edge(START, "simple")
        graph_builder.add_edge("simple", END)
        
        graph = graph_builder.compile(checkpointer=checkpointer)
        
        config = {"configurable": {"thread_id": session_id}}
        
        result1 = await graph.ainvoke({"messages": ["First message"]}, config=config)
        
        result2 = await graph.ainvoke({"messages": ["Second message"]}, config=config)
        
        assert len(result2["messages"]) >= 2
        assert "First message" in str(result2["messages"])
        assert "Second message" in str(result2["messages"])
    finally:
        await db_manager.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_state_isolated_between_sessions(db_manager):
    """Different session_ids should have independent state."""
    from app.agent.sessions import create_session, get_checkpointer
    from langgraph.graph import StateGraph, START, END
    from pydantic import BaseModel, Field
    from typing import Annotated
    import operator
    
    await db_manager.connect()
    
    try:
        session1_id = await create_session("user1", db_manager=db_manager)
        session2_id = await create_session("user2", db_manager=db_manager)
        checkpointer = get_checkpointer()
        
        class ThreadState(BaseModel):
            messages: Annotated[list, operator.add] = Field(default_factory=list)
        
        def simple_node(state: ThreadState) -> Dict[str, Any]:
            return {"messages": ["Processed"]}
        
        graph_builder = StateGraph(ThreadState)
        graph_builder.add_node("simple", simple_node)
        graph_builder.add_edge(START, "simple")
        graph_builder.add_edge("simple", END)
        
        graph = graph_builder.compile(checkpointer=checkpointer)
        
        config1 = {"configurable": {"thread_id": session1_id}}
        config2 = {"configurable": {"thread_id": session2_id}}
        
        result1 = await graph.ainvoke({"messages": ["Session1 message"]}, config=config1)
        result2 = await graph.ainvoke({"messages": ["Session2 message"]}, config=config2)
        
        state1 = await graph.aget_state(config1)
        state2 = await graph.aget_state(config2)
        
        assert state1.values["messages"] != state2.values["messages"]
        assert "Session1 message" in str(state1.values["messages"])
        assert "Session2 message" in str(state2.values["messages"])
    finally:
        await db_manager.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_stores_explored_papers(db_manager):
    """Session should track which papers the user has explored."""
    from app.agent.sessions import create_session, get_session, update_session_papers
    from app.db.schema import apply_schema
    
    await db_manager.connect()
    
    try:
        await apply_schema(db_manager)
        
        session_id = await create_session("test_user", db_manager=db_manager)
        
        paper_ids = ["paper:1", "paper:2", "paper:3"]
        await update_session_papers(session_id, paper_ids, db_manager=db_manager)
        
        session_data = await get_session(session_id, db_manager=db_manager)
        
        assert "papers_explored" in session_data
        explored_papers = session_data.get("papers_explored", [])
        assert len(explored_papers) == 3
        assert any("paper:1" in str(p) for p in explored_papers)
    finally:
        await db_manager.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_session_creates_valid_record(db_manager):
    """create_session should create a valid session record in SurrealDB."""
    from app.agent.sessions import create_session, get_session
    from app.db.schema import apply_schema
    
    await db_manager.connect()
    
    try:
        await apply_schema(db_manager)
        
        session_id = await create_session("integration_test_user", db_manager=db_manager)
        
        assert session_id.startswith("session:")
        
        session_data = await get_session(session_id, db_manager=db_manager)
        
        assert session_data["id"] == session_id
        assert session_data["user_id"] == "integration_test_user"
        assert "created_at" in session_data
    finally:
        await db_manager.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_sessions_filters_by_user(db_manager):
    """list_sessions should return only sessions for the specified user."""
    from app.agent.sessions import create_session, list_sessions
    from app.db.schema import apply_schema
    
    await db_manager.connect()
    
    try:
        await apply_schema(db_manager)
        
        session1_id = await create_session("user_a", db_manager=db_manager)
        session2_id = await create_session("user_a", db_manager=db_manager)
        session3_id = await create_session("user_b", db_manager=db_manager)
        
        user_a_sessions = await list_sessions("user_a", db_manager=db_manager)
        user_b_sessions = await list_sessions("user_b", db_manager=db_manager)
        
        assert len(user_a_sessions) == 2
        assert len(user_b_sessions) == 1
        assert all(s["user_id"] == "user_a" for s in user_a_sessions)
        assert all(s["user_id"] == "user_b" for s in user_b_sessions)
    finally:
        await db_manager.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_resumption_loads_previous_state(db_manager):
    """Session resumption should load previous agent state."""
    from app.agent.sessions import create_session, get_checkpointer
    from langgraph.graph import StateGraph, START, END
    from pydantic import BaseModel, Field
    from typing import Annotated
    import operator
    
    await db_manager.connect()
    
    try:
        session_id = await create_session("resume_user", db_manager=db_manager)
        checkpointer = get_checkpointer()
        
        class ThreadState(BaseModel):
            counter: int = 0
            messages: Annotated[list, operator.add] = Field(default_factory=list)
        
        def increment_node(state: ThreadState) -> Dict[str, Any]:
            return {"counter": state.counter + 1, "messages": [f"Count: {state.counter + 1}"]}
        
        graph_builder = StateGraph(ThreadState)
        graph_builder.add_node("increment", increment_node)
        graph_builder.add_edge(START, "increment")
        graph_builder.add_edge("increment", END)
        
        graph = graph_builder.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": session_id}}
        
        await graph.ainvoke({"counter": 0, "messages": []}, config=config)
        await graph.ainvoke({"counter": 0, "messages": []}, config=config)
        
        state = await graph.aget_state(config)
        
        assert state.values["counter"] == 2
        assert len(state.values["messages"]) >= 2
    finally:
        await db_manager.disconnect()
