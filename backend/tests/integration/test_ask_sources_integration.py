"""Integration tests for /api/ask source canonicalization."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest


@pytest.fixture
async def async_client(db_manager):
    """httpx.AsyncClient bound to FastAPI test app."""
    from app.main import app
    import app.db.manager as db_manager_module

    db_manager_module.db_manager = db_manager

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_ask_hydrates_source_title_from_paper_record(async_client, db_manager):
    from app.db.schema import apply_schema

    await apply_schema(db_manager)
    await db_manager.execute(
        """
        CREATE paper:test_source SET
            title = 'Censored LLMs as a Natural Testbed for Secret Knowledge Elicitation',
            abstract = 'Test abstract',
            arxiv_id = '2603.05494v1'
        """
    )

    with patch("app.api.routes_ask.HybridRetriever") as mock_retriever_cls, patch(
        "app.api.routes_ask.ChatOpenAI"
    ) as mock_llm_cls:
        retriever = Mock()
        retriever.retrieve = AsyncMock(
            return_value={
                "contexts": [
                    {
                        "paper_id": "paper:test_source",
                        "title": "Unknown",
                        "content": "politically sensitive topics",
                        "score": 0.95,
                        "sources": ["vector"],
                    }
                ],
                "debug": {},
            }
        )
        mock_retriever_cls.return_value = retriever

        llm = Mock()
        llm.ainvoke = AsyncMock(return_value=Mock(content="Answer"))
        mock_llm_cls.return_value = llm

        response = await async_client.post(
            "/api/ask",
            json={"question": "llms trained to censor politically sensitive topics"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["sources"]) >= 1
    source = data["sources"][0]
    assert source["title"] == "Censored LLMs as a Natural Testbed for Secret Knowledge Elicitation"
    assert source["paper_id"] == "paper:test_source"
    assert source["external_url"] == "https://arxiv.org/abs/2603.05494v1"
