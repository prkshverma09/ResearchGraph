"""Integration tests for aggregated graph endpoint."""

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
async def test_subgraph_merges_selected_paper_graphs(async_client, db_manager):
    from app.db.schema import apply_schema

    await apply_schema(db_manager)
    await db_manager.execute("CREATE paper:p1 SET title = 'Paper One', abstract = 'A'")
    await db_manager.execute("CREATE paper:p2 SET title = 'Paper Two', abstract = 'B'")
    await db_manager.execute("CREATE author:a1 SET name = 'Alice'")
    await db_manager.execute("RELATE paper:p1->authored_by->author:a1")
    await db_manager.execute("RELATE paper:p2->authored_by->author:a1")

    response = await async_client.get(
        "/api/graph/subgraph",
        params=[("paper_ids", "paper:p1"), ("paper_ids", "paper:p2")],
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["papers"]) == 2
    assert data["counts"]["nodes"] >= 3
    assert data["counts"]["edges"] >= 2
