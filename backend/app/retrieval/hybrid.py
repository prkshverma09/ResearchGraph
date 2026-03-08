"""Deterministic hybrid retrieval over SurrealDB vector + graph data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.db.connection import SurrealDBManager
from app.ingestion.embeddings import VectorStoreService


@dataclass
class RetrievalCandidate:
    """Unified retrieval candidate used for fusion."""

    source: str
    score: float
    content: str
    metadata: Dict[str, Any]

    @property
    def paper_id(self) -> str:
        value = self.metadata.get("paper_id") or self.metadata.get("id") or ""
        if isinstance(value, dict) and "tb" in value and "id" in value:
            return f"{value['tb']}:{value['id']}"
        return str(value)


class HybridRetriever:
    """Runs deterministic vector + lexical + graph-assisted retrieval."""

    def __init__(self, db_manager: SurrealDBManager):
        self.db_manager = db_manager
        self.vector_store = VectorStoreService(db_manager=db_manager)

    def _keywords(self, query: str) -> List[str]:
        words = [w.lower() for w in re.findall(r"[a-zA-Z0-9]{3,}", query)]
        seen = set()
        keywords: List[str] = []
        for word in words:
            if word in seen:
                continue
            seen.add(word)
            keywords.append(word)
            if len(keywords) >= 8:
                break
        return keywords

    def _query_variants(self, query: str, keywords: List[str]) -> List[str]:
        """Build deterministic query rewrites for better recall."""
        variants: List[str] = [query.strip()]
        if keywords:
            variants.append(" ".join(keywords[:8]))
        if len(keywords) >= 2:
            variants.append(" ".join(keywords[:4]))
        seen = set()
        deduped: List[str] = []
        for value in variants:
            key = value.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(value.strip())
        return deduped[:3]

    async def _vector_candidates(
        self,
        query: str,
        selected_paper_ids: Optional[List[str]],
        k: int,
    ) -> List[RetrievalCandidate]:
        vector_hits = await self.vector_store.similarity_search_with_scores(
            query=query,
            k=k,
            paper_ids=selected_paper_ids,
        )
        candidates: List[RetrievalCandidate] = []
        for doc, score in vector_hits:
            candidates.append(
                RetrievalCandidate(
                    source="vector",
                    score=float(score),
                    content=doc.page_content,
                    metadata=doc.metadata or {},
                )
            )
        return candidates

    async def _multi_query_vector_candidates(
        self,
        query_variants: List[str],
        selected_paper_ids: Optional[List[str]],
        k: int,
    ) -> List[RetrievalCandidate]:
        candidates: List[RetrievalCandidate] = []
        for idx, variant in enumerate(query_variants):
            hits = await self._vector_candidates(variant, selected_paper_ids, k=k)
            for candidate in hits:
                metadata = candidate.metadata.copy()
                metadata["query_variant"] = variant
                candidates.append(
                    RetrievalCandidate(
                        source=f"vector_q{idx}",
                        score=candidate.score,
                        content=candidate.content,
                        metadata=metadata,
                    )
                )
        return candidates

    async def _chunk_lexical_candidates(
        self,
        query: str,
        keywords: List[str],
        selected_paper_ids: Optional[List[str]],
        k: int,
    ) -> List[RetrievalCandidate]:
        if not keywords:
            return []

        query_sql = """
            SELECT
                content,
                metadata,
                array::len(array::filter($terms, |$term| string::lowercase(content) CONTAINS $term)) AS term_hits,
                IF string::lowercase(content) CONTAINS $full_query THEN 3 ELSE 0 END AS phrase_bonus,
                array::len(array::filter($terms, |$term|
                    string::lowercase(metadata.title ?? '') CONTAINS $term
                    OR string::lowercase(metadata.paper_title ?? '') CONTAINS $term
                    OR string::lowercase(string::join(metadata.topics ?? [], ' ')) CONTAINS $term
                )) AS metadata_hits,
                (
                    array::len(array::filter($terms, |$term| string::lowercase(content) CONTAINS $term))
                    + IF string::lowercase(content) CONTAINS $full_query THEN 3 ELSE 0 END
                    + array::len(array::filter($terms, |$term|
                        string::lowercase(metadata.title ?? '') CONTAINS $term
                        OR string::lowercase(metadata.paper_title ?? '') CONTAINS $term
                        OR string::lowercase(string::join(metadata.topics ?? [], ' ')) CONTAINS $term
                    ))
                ) AS lexical_score
            FROM chunk
            WHERE embedding != NONE
        """
        params: Dict[str, Any] = {
            "terms": keywords,
            "limit": k,
            "full_query": query.lower(),
        }
        if selected_paper_ids is not None:
            query_sql += "\n  AND (paper_id IN $paper_ids OR metadata.paper_id IN $paper_ids)"
            params["paper_ids"] = selected_paper_ids

        query_sql += """
            ORDER BY lexical_score DESC
            LIMIT $limit
        """
        rows = await self.db_manager.execute(query_sql, params)
        candidates: List[RetrievalCandidate] = []
        for row in rows:
            score = float(row.get("lexical_score", 0.0))
            if score <= 0:
                continue
            candidates.append(
                RetrievalCandidate(
                    source="lexical_chunk",
                    score=score,
                    content=row.get("content", ""),
                    metadata=row.get("metadata", {}) or {},
                )
            )
        return candidates

    async def _paper_lexical_candidates(
        self,
        query: str,
        keywords: List[str],
        selected_paper_ids: Optional[List[str]],
        k: int,
    ) -> List[RetrievalCandidate]:
        if not keywords:
            return []

        query_sql = """
            SELECT
                id,
                title,
                abstract,
                array::len(
                    array::filter(
                        $terms,
                        |$term| string::lowercase(title) CONTAINS $term
                             OR string::lowercase(string::concat(abstract ?? '')) CONTAINS $term
                    )
                ) AS term_hits,
                IF string::lowercase(title) CONTAINS $full_query THEN 3 ELSE 0 END AS title_phrase_bonus,
                IF string::lowercase(string::concat(abstract ?? '')) CONTAINS $full_query THEN 2 ELSE 0 END AS abstract_phrase_bonus,
                (
                    array::len(
                        array::filter(
                            $terms,
                            |$term| string::lowercase(title) CONTAINS $term
                                 OR string::lowercase(string::concat(abstract ?? '')) CONTAINS $term
                        )
                    )
                    + IF string::lowercase(title) CONTAINS $full_query THEN 3 ELSE 0 END
                    + IF string::lowercase(string::concat(abstract ?? '')) CONTAINS $full_query THEN 2 ELSE 0 END
                ) AS lexical_score
            FROM paper
            WHERE true
        """
        params: Dict[str, Any] = {
            "terms": keywords,
            "limit": k,
            "full_query": query.lower(),
        }
        if selected_paper_ids is not None:
            query_sql += "\n  AND id IN $paper_ids"
            params["paper_ids"] = selected_paper_ids

        query_sql += """
            ORDER BY lexical_score DESC
            LIMIT $limit
        """
        rows = await self.db_manager.execute(query_sql, params)
        candidates: List[RetrievalCandidate] = []
        for row in rows:
            score = float(row.get("lexical_score", 0.0))
            if score <= 0:
                continue
            paper_id = row.get("id")
            if isinstance(paper_id, dict) and "tb" in paper_id and "id" in paper_id:
                paper_id = f"{paper_id['tb']}:{paper_id['id']}"
            title = row.get("title", "Unknown")
            abstract = row.get("abstract", "") or ""
            candidates.append(
                RetrievalCandidate(
                    source="lexical_paper",
                    score=score,
                    content=abstract if abstract else title,
                    metadata={"paper_id": str(paper_id or ""), "title": title},
                )
            )
        return candidates

    async def _topic_graph_expansion(
        self,
        keywords: List[str],
        selected_paper_ids: Optional[List[str]],
        k: int,
    ) -> List[RetrievalCandidate]:
        if not keywords:
            return []

        topic_rows = await self.db_manager.execute(
            """
            SELECT id, name
            FROM topic
            WHERE array::len(array::filter($terms, |$term| string::lowercase(name) CONTAINS $term)) > 0
            LIMIT $limit
            """,
            {"terms": keywords, "limit": k},
        )
        if not topic_rows:
            return []

        topic_ids = []
        for topic in topic_rows:
            topic_id = topic.get("id")
            if isinstance(topic_id, dict) and "tb" in topic_id and "id" in topic_id:
                topic_id = f"{topic_id['tb']}:{topic_id['id']}"
            if topic_id:
                topic_ids.append(str(topic_id))
        if not topic_ids:
            return []

        paper_query = """
            SELECT
                paper.id AS paper_id,
                paper.title AS title
            FROM paper
            WHERE id IN (
                SELECT <-belongs_to<-paper.id
                FROM topic
                WHERE id IN $topic_ids
            )
            LIMIT $limit
        """
        params: Dict[str, Any] = {"topic_ids": topic_ids, "limit": k}
        if selected_paper_ids is not None:
            paper_query = """
                SELECT
                    paper.id AS paper_id,
                    paper.title AS title
                FROM paper
                WHERE id IN (
                    SELECT <-belongs_to<-paper.id
                    FROM topic
                    WHERE id IN $topic_ids
                )
                AND id IN $paper_ids
                LIMIT $limit
            """
            params["paper_ids"] = selected_paper_ids

        rows = await self.db_manager.execute(paper_query, params)
        candidates: List[RetrievalCandidate] = []
        for row in rows:
            paper_id = row.get("paper_id")
            if isinstance(paper_id, dict) and "tb" in paper_id and "id" in paper_id:
                paper_id = f"{paper_id['tb']}:{paper_id['id']}"
            candidates.append(
                RetrievalCandidate(
                    source="graph_topic",
                    score=1.0,
                    content=row.get("title", ""),
                    metadata={"paper_id": str(paper_id or ""), "title": row.get("title", "Unknown")},
                )
            )
        return candidates

    async def _citation_graph_expansion(
        self,
        seed_paper_ids: List[str],
        selected_paper_ids: Optional[List[str]],
        k: int,
    ) -> List[RetrievalCandidate]:
        if not seed_paper_ids:
            return []

        edge_rows = await self.db_manager.execute(
            """
            SELECT in, out
            FROM cites
            WHERE in IN $paper_ids OR out IN $paper_ids
            LIMIT $limit
            """,
            {"paper_ids": seed_paper_ids, "limit": max(k * 4, 20)},
        )
        neighbor_ids: List[str] = []
        for row in edge_rows:
            for key in ("in", "out"):
                value = row.get(key)
                if isinstance(value, dict) and "tb" in value and "id" in value:
                    value = f"{value['tb']}:{value['id']}"
                value_str = str(value or "")
                if value_str and value_str not in seed_paper_ids:
                    neighbor_ids.append(value_str)

        if selected_paper_ids is not None:
            selected = set(selected_paper_ids)
            neighbor_ids = [paper_id for paper_id in neighbor_ids if paper_id in selected]

        deduped = list(dict.fromkeys(neighbor_ids))[: max(k, 10)]
        if not deduped:
            return []

        papers = await self.db_manager.execute(
            """
            SELECT id, title, abstract
            FROM paper
            WHERE id IN $paper_ids
            LIMIT $limit
            """,
            {"paper_ids": deduped, "limit": k},
        )
        candidates: List[RetrievalCandidate] = []
        for row in papers:
            paper_id = row.get("id")
            if isinstance(paper_id, dict) and "tb" in paper_id and "id" in paper_id:
                paper_id = f"{paper_id['tb']}:{paper_id['id']}"
            title = row.get("title", "Unknown")
            abstract = row.get("abstract", "") or ""
            content = abstract if abstract else title
            candidates.append(
                RetrievalCandidate(
                    source="graph_citation",
                    score=1.0,
                    content=content,
                    metadata={"paper_id": str(paper_id or ""), "title": title},
                )
            )
        return candidates

    def _fuse(self, groups: Dict[str, List[RetrievalCandidate]], k: int) -> List[RetrievalCandidate]:
        """Reciprocal rank fusion across retrieval branches."""
        fused: Dict[str, Dict[str, Any]] = {}
        rrf_k = 60.0

        for source_name, candidates in groups.items():
            for rank, candidate in enumerate(candidates, start=1):
                key = f"{candidate.paper_id}::{candidate.content[:120]}"
                existing = fused.get(key)
                add_score = 1.0 / (rrf_k + rank)
                if existing is None:
                    fused[key] = {
                        "candidate": candidate,
                        "score": add_score,
                        "sources": {source_name},
                    }
                    continue
                existing["score"] += add_score
                existing["sources"].add(source_name)

        ordered = sorted(fused.values(), key=lambda item: item["score"], reverse=True)[:k]
        results: List[RetrievalCandidate] = []
        for item in ordered:
            candidate = item["candidate"]
            merged_metadata = candidate.metadata.copy()
            merged_metadata["fusion_score"] = item["score"]
            merged_metadata["sources"] = sorted(item["sources"])
            results.append(
                RetrievalCandidate(
                    source="fused",
                    score=float(item["score"]),
                    content=candidate.content,
                    metadata=merged_metadata,
                )
            )
        return results

    def _token_overlap(self, query_tokens: List[str], text: str) -> float:
        if not query_tokens:
            return 0.0
        haystack = text.lower()
        hits = sum(1 for token in query_tokens if token in haystack)
        return float(hits) / float(len(query_tokens))

    def _rerank_contexts(
        self,
        query: str,
        candidates: List[RetrievalCandidate],
        k: int,
    ) -> List[Tuple[RetrievalCandidate, float]]:
        query_tokens = self._keywords(query)
        reranked: List[Tuple[RetrievalCandidate, float]] = []
        for candidate in candidates:
            title = str(candidate.metadata.get("title", ""))
            overlap_content = self._token_overlap(query_tokens, candidate.content)
            overlap_title = self._token_overlap(query_tokens, title)
            phrase_bonus = 1.0 if query.lower() in candidate.content.lower() else 0.0
            composite = (
                candidate.score
                + (0.45 * overlap_content)
                + (0.25 * overlap_title)
                + (0.35 * phrase_bonus)
            )
            reranked.append((candidate, composite))

        reranked.sort(key=lambda item: item[1], reverse=True)
        return reranked[:k]

    async def retrieve(
        self,
        query: str,
        selected_paper_ids: Optional[List[str]] = None,
        k: int = 8,
    ) -> Dict[str, Any]:
        """Run deterministic hybrid retrieval and return fused contexts."""
        keywords = self._keywords(query)
        variants = self._query_variants(query, keywords)

        vector = await self._multi_query_vector_candidates(variants, selected_paper_ids, k=max(k * 2, 8))
        lexical_chunk = await self._chunk_lexical_candidates(query, keywords, selected_paper_ids, k=max(k * 2, 8))
        lexical_paper = await self._paper_lexical_candidates(query, keywords, selected_paper_ids, k=max(k, 5))
        graph_topic = await self._topic_graph_expansion(keywords, selected_paper_ids, k=max(k, 5))

        seed_papers = [candidate.paper_id for candidate in (vector[:k] + lexical_paper[:k]) if candidate.paper_id]
        graph_citation = await self._citation_graph_expansion(seed_papers, selected_paper_ids, k=max(k, 5))

        fused = self._fuse(
            {
                "vector": vector,
                "lexical_chunk": lexical_chunk,
                "lexical_paper": lexical_paper,
                "graph_topic": graph_topic,
                "graph_citation": graph_citation,
            },
            k=max(k * 2, 12),
        )
        reranked = self._rerank_contexts(query, fused, k=k)

        contexts = [
            {
                "paper_id": candidate.paper_id,
                "title": candidate.metadata.get("title", "Unknown"),
                "content": candidate.content,
                "score": score,
                "sources": candidate.metadata.get("sources", [candidate.source]),
            }
            for candidate, score in reranked
        ]

        return {
            "contexts": contexts,
            "debug": {
                "keywords": keywords,
                "query_variants": variants,
                "vector_hits": len(vector),
                "lexical_chunk_hits": len(lexical_chunk),
                "lexical_paper_hits": len(lexical_paper),
                "graph_topic_hits": len(graph_topic),
                "graph_citation_hits": len(graph_citation),
                "fused_hits": len(fused),
                "reranked_hits": len(reranked),
                "selected_scope_applied": bool(selected_paper_ids),
            },
        }
