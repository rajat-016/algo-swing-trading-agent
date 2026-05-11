from __future__ import annotations

from typing import Optional

from loguru import logger

from memory.chromadb.collection_manager import MemoryCollectionManager
from memory.retrieval.scoring import normalize_scores
from memory.schemas.memory_schemas import (
    HybridSearchConfig,
    MemoryFilter,
    MemoryType,
    SearchResult,
)


async def hybrid_search(
    query: str,
    query_embedding: list[float],
    collection_manager: MemoryCollectionManager,
    mem_types: list[MemoryType],
    memory_filter: Optional[MemoryFilter] = None,
    n_results: int = 10,
) -> list[SearchResult]:
    config = memory_filter.hybrid_config if memory_filter and memory_filter.hybrid_config else HybridSearchConfig()
    if not config.enabled:
        return []

    where_clause = memory_filter.to_chroma_where() if memory_filter else None
    kw_n = n_results * config.keyword_n_results_multiplier

    vector_results: dict[str, SearchResult] = {}
    keyword_results: dict[str, SearchResult] = {}

    for mem_type in mem_types:
        try:
            chroma_vec = collection_manager.query(
                mem_type, query_embedding, n_results=kw_n, where=where_clause,
            )
            for r in SearchResult.from_chroma_batch(chroma_vec):
                vector_results[r.id] = r
        except Exception as e:
            logger.error(f"Vector query failed for {mem_type.value}: {e}")

        try:
            chroma_kw = collection_manager.query_by_text(
                mem_type, query, n_results=kw_n, where=where_clause,
            )
            for r in SearchResult.from_chroma_batch(chroma_kw):
                keyword_results[r.id] = r
        except Exception as e:
            logger.error(f"Keyword query failed for {mem_type.value}: {e}")

    if not vector_results and not keyword_results:
        return []

    vector_list = list(normalize_scores(list(vector_results.values()), "relevance_score"))
    keyword_list = list(normalize_scores(list(keyword_results.values()), "relevance_score"))

    vec_scores = {r.id: r.relevance_score for r in vector_list}
    kw_scores = {r.id: r.relevance_score for r in keyword_list}

    all_ids = set(vec_scores.keys()) | set(kw_scores.keys())
    merged = []
    for rid in all_ids:
        v = vec_scores.get(rid, 0.0)
        k = kw_scores.get(rid, 0.0)
        hybrid = (v * config.vector_weight) + (k * config.keyword_weight)
        result = vector_results.get(rid) or keyword_results[rid]
        result.hybrid_score = min(1.0, hybrid)
        result.relevance_score = min(1.0, v + k * config.keyword_weight)
        merged.append(result)

    merged.sort(key=lambda x: x.hybrid_score or x.relevance_score, reverse=True)

    logger.info(
        f"Hybrid search '{query[:50]}' merged "
        f"{len(merged)} results (vec={len(vector_results)}, kw={len(keyword_results)})"
    )
    return merged[:n_results]
