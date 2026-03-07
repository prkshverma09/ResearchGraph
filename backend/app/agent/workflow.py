"""LangGraph agent workflow for research queries."""

import logging
from typing import List, Dict, Any, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
try:
    import langsmith as ls
except ImportError:
    ls = None

from app.agent.state import ResearchAgentState
from app.config import settings

logger = logging.getLogger(__name__)


def create_router_node(llm: ChatOpenAI, tools: List[Any]):
    """Create a router node function bound to LLM and tools.
    
    Args:
        llm: ChatOpenAI instance
        tools: List of tools available to the agent
        
    Returns:
        Router node function
    """
    async def router_node(state: ResearchAgentState) -> Dict[str, Any]:
        """Router node that analyzes the query and decides which tools to use."""
        messages = state["messages"]
        query = state.get("query", "")
        session_id = state.get("session_id", "")
        
        if not query and messages:
            last_message = messages[-1]
            if isinstance(last_message, HumanMessage):
                query = last_message.content
        
        router_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research assistant that helps users explore academic papers.
            
Available tools:
- vector_search: Use for finding papers by topic, concept, or research area (e.g., "find papers about transformers", "papers on neural networks")
- graph_query: Use for finding relationships (e.g., "who cites paper X", "what papers did author Y write", "papers on topic Z")
- citation_path: Use for finding connections between two papers (e.g., "how are paper A and paper B connected")

Analyze the user's query and decide which tool(s) to use. Respond with tool calls."""),
            ("user", "{query}"),
        ])
        
        chain = router_prompt | llm.bind_tools(tools)
        
        try:
            if ls:
                metadata = {}
                if session_id:
                    metadata["session_id"] = session_id
                if query:
                    metadata["query"] = query
                
                with ls.tracing_context(metadata=metadata):
                    response = await chain.ainvoke({"query": query})
            else:
                response = await chain.ainvoke({"query": query})
            
            updated_messages = list(messages)
            updated_messages.append(response)
            
            return {
                "messages": updated_messages,
            }
        except Exception as e:
            logger.error(f"Router node error: {e}")
            error_message = AIMessage(content=f"I encountered an error: {str(e)}")
            return {
                "messages": list(messages) + [error_message],
            }
    
    return router_node


def route_decision(state: ResearchAgentState) -> Literal["tools", "synthesizer"]:
    """Conditional routing function based on state.
    
    Args:
        state: Current agent state
        
    Returns:
        "tools" if tool calls are present, "synthesizer" otherwise
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "synthesizer"
    
    last_message = messages[-1]
    
    if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    return "synthesizer"


def create_synthesizer_node(llm: ChatOpenAI):
    """Create a synthesizer node function bound to LLM.
    
    Args:
        llm: ChatOpenAI instance
        
    Returns:
        Synthesizer node function
    """
    async def synthesizer_node(state: ResearchAgentState) -> Dict[str, Any]:
        """Synthesizer node that combines tool results into a coherent answer."""
        messages = state["messages"]
        query = state.get("query", "")
        session_id = state.get("session_id", "")
        
        if not query and messages:
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    query = msg.content
                    break
        
        tool_results = []
        search_results = []
        graph_results = []
        citation_path = []
        paper_ids = []
        
        for msg in messages:
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "name", "unknown")
                tool_results.append(f"Tool: {tool_name}\nResult: {msg.content}")
                
                try:
                    import json
                    result_data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    
                    if isinstance(result_data, dict):
                        if "papers" in result_data:
                            papers = result_data.get("papers", [])
                            if papers and isinstance(papers[0], dict) and "relevance_score" in papers[0]:
                                search_results.extend(papers)
                                for paper in papers:
                                    if "paper_id" in paper and paper["paper_id"]:
                                        paper_ids.append(paper["paper_id"])
                            else:
                                graph_results.extend(papers)
                                for paper in papers:
                                    if "id" in paper and paper["id"]:
                                        paper_ids.append(paper["id"])
                        
                        if "path" in result_data:
                            citation_path.extend(result_data.get("path", []))
                            for path_item in result_data.get("path", []):
                                if isinstance(path_item, dict) and "id" in path_item:
                                    paper_ids.append(path_item["id"])
                            
                        if "citations" in result_data:
                            graph_results.extend(result_data.get("citations", []))
                            for citation in result_data.get("citations", []):
                                if isinstance(citation, dict) and "id" in citation:
                                    paper_ids.append(citation["id"])
                except Exception:
                    pass
        
        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research assistant. Synthesize the tool results into a clear, 
            comprehensive answer to the user's query. Include specific paper titles and authors when 
            available. Cite sources appropriately."""),
            ("user", """User query: {query}

Tool results:
{tool_results}

Provide a comprehensive answer based on these results.""")
        ])
        
        tool_results_text = "\n\n".join(tool_results) if tool_results else "No results found."
        
        chain = synthesis_prompt | llm
        
        try:
            if ls:
                metadata = {}
                if session_id:
                    metadata["session_id"] = session_id
                if query:
                    metadata["query"] = query
                if paper_ids:
                    metadata["paper_ids"] = list(set(paper_ids))
                
                with ls.tracing_context(metadata=metadata):
                    response = await chain.ainvoke({
                        "query": query,
                        "tool_results": tool_results_text,
                    })
            else:
                response = await chain.ainvoke({
                    "query": query,
                    "tool_results": tool_results_text,
                })
            
            final_answer = response.content if hasattr(response, "content") else str(response)
            
            updated_messages = list(messages)
            updated_messages.append(AIMessage(content=final_answer))
            
            return {
                "messages": updated_messages,
                "final_answer": final_answer,
                "search_results": search_results,
                "graph_results": graph_results,
                "citation_path": citation_path,
            }
        except Exception as e:
            logger.error(f"Synthesizer node error: {e}")
            error_answer = f"I encountered an error while synthesizing the answer: {str(e)}"
            return {
                "messages": list(messages) + [AIMessage(content=error_answer)],
                "final_answer": error_answer,
                "search_results": search_results,
                "graph_results": graph_results,
                "citation_path": citation_path,
            }
    
    return synthesizer_node


def create_agent_graph(
    tools: List[Any],
    llm: ChatOpenAI,
    checkpointer: Any = None,
) -> StateGraph:
    """Create the LangGraph agent workflow graph.
    
    Args:
        tools: List of LangChain tools (must have ainvoke method)
        llm: ChatOpenAI instance
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Compiled StateGraph
    """
    router = create_router_node(llm, tools)
    synthesizer = create_synthesizer_node(llm)
    
    builder = StateGraph(ResearchAgentState)
    
    builder.add_node("router", router)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("synthesizer", synthesizer)
    
    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        route_decision,
        {
            "tools": "tools",
            "synthesizer": "synthesizer",
        }
    )
    builder.add_edge("tools", "synthesizer")
    builder.add_edge("synthesizer", END)
    
    if checkpointer:
        return builder.compile(checkpointer=checkpointer)
    else:
        return builder.compile()


async def stream_agent_response(
    graph: StateGraph,
    state: ResearchAgentState,
    config: Optional[Dict[str, Any]] = None,
):
    """Stream agent response as it progresses through the workflow.
    
    Args:
        graph: Compiled StateGraph
        state: Initial agent state
        config: Optional configuration (e.g., thread_id for persistence)
        
    Yields:
        Intermediate state updates
    """
    async for event in graph.astream(state, config=config):
        yield event
