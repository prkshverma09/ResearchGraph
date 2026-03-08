"""Unit tests for ask source hydration/canonicalization."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.api.routes_ask import _build_sources_from_contexts


@pytest.mark.asyncio
async def test_build_sources_prefers_canonical_db_title_and_builds_external_url():
    mock_db = Mock()
    mock_db.execute = AsyncMock(
        return_value=[
            {
                "id": "paper:1",
                "title": "Censored LLMs as a Natural Testbed",
                "arxiv_id": "2603.05494v1",
                "doi": None,
            }
        ]
    )
    contexts = [
        {
            "paper_id": "paper:1",
            "title": "Unknown",
            "score": 0.93,
            "content": "chunk",
        }
    ]

    sources = await _build_sources_from_contexts(contexts, mock_db)

    assert len(sources) == 1
    assert sources[0]["title"] == "Censored LLMs as a Natural Testbed"
    assert sources[0]["paper_id"] == "paper:1"
    assert sources[0]["external_url"] == "https://arxiv.org/abs/2603.05494v1"
    assert sources[0]["title"].lower() != "unknown"


@pytest.mark.asyncio
async def test_build_sources_falls_back_to_paper_id_when_title_missing():
    mock_db = Mock()
    mock_db.execute = AsyncMock(return_value=[])
    contexts = [
        {
            "paper_id": "paper:missing",
            "title": "Unknown",
            "score": 0.5,
            "content": "chunk",
        }
    ]

    sources = await _build_sources_from_contexts(contexts, mock_db)

    assert len(sources) == 1
    assert sources[0]["title"] == "paper:missing"
    assert sources[0]["paper_id"] == "paper:missing"
