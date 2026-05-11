from __future__ import annotations

import math
from typing import Optional

from memory.schemas.memory_schemas import SearchResult


def normalize_scores(
    results: list[SearchResult],
    score_attr: str = "relevance_score",
) -> list[SearchResult]:
    if not results:
        return results

    scores = [getattr(r, score_attr) or 0.0 for r in results]
    min_s = min(scores)
    max_s = max(scores)
    diff = max_s - min_s

    if diff < 1e-9:
        for r in results:
            setattr(r, score_attr, 1.0)
        return results

    for r in results:
        raw = getattr(r, score_attr) or 0.0
        setattr(r, score_attr, (raw - min_s) / diff)

    return results


def compute_cross_collection_similarity(
    results: list[SearchResult],
) -> list[SearchResult]:
    if not results:
        return results

    type_groups: dict[str, list[SearchResult]] = {}
    for r in results:
        key = r.memory_type.value
        type_groups.setdefault(key, []).append(r)

    for group in type_groups.values():
        group_scores = [r.relevance_score for r in group]
        avg = sum(group_scores) / len(group_scores) if group_scores else 0.0
        for r in group:
            context_boost = 1.0 + (0.1 if r.relevance_score >= avg else 0.0)
            r.relevance_score = min(1.0, r.relevance_score * context_boost)

    return results


def compute_weighted_score(
    vector_score: float,
    keyword_score: Optional[float] = None,
    ranked_boost: Optional[float] = None,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    ranked_weight: float = 0.2,
) -> float:
    base = vector_score * vector_weight
    if keyword_score is not None:
        base += keyword_score * keyword_weight
    if ranked_boost is not None:
        base += ranked_boost * ranked_weight
    return min(1.0, max(0.0, base))


def clip_relevance(results: list[SearchResult], threshold: float = 0.0) -> list[SearchResult]:
    return [r for r in results if r.relevance_score >= threshold]
