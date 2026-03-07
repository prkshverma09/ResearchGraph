"""Agent state schema for LangGraph workflow."""

from typing import TypedDict, Annotated, List, NotRequired
from langchain_core.messages import BaseMessage


def add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    """Reducer function to accumulate messages in state.
    
    Args:
        left: Existing messages
        right: New messages to add
        
    Returns:
        Combined list of messages
    """
    return left + right


class ResearchAgentState(TypedDict):
    """State schema for the research agent workflow.
    
    Attributes:
        messages: Conversation history (accumulated via add_messages reducer)
        query: Current user query
        search_results: Results from vector search tool
        graph_results: Results from graph query tool
        citation_path: Citation path between papers
        final_answer: Generated answer to the user's query
        session_id: Session identifier for persistence
    """
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    search_results: List[dict]
    graph_results: List[dict]
    citation_path: List[dict]
    final_answer: str
    session_id: str
    filter_selected_only: NotRequired[bool]
    selected_paper_ids: NotRequired[List[str]]
