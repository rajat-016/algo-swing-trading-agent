from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from loguru import logger

from memory.schemas.memory_schemas import RankingBoost, RankingConfig, SearchResult


def _compute_confidence_boost(metadata: dict, weight: float) -> float:
    confidence = metadata.get("confidence")
    if confidence is None:
        return 0.0
    return weight * min(1.0, max(0.0, float(confidence)))


def _compute_recency_boost(
    metadata: dict,
    weight: float,
    half_life_days: float = 30.0,
) -> float:
    ts = metadata.get("timestamp")
    if not ts:
        return 0.0
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo)
        days_old = (now - dt).total_seconds() / 86400.0
        if days_old < 0:
            return weight
        decay = math.exp(-math.log(2) * days_old / half_life_days)
        return weight * decay
    except (ValueError, TypeError):
        return 0.0


def _compute_outcome_boost(
    metadata: dict,
    weight: float,
    priority_order: list[str],
) -> float:
    outcome = metadata.get("outcome")
    if not outcome or outcome not in priority_order:
        return 0.0
    idx = priority_order.index(outcome)
    score = 1.0 - (idx / max(len(priority_order) - 1, 1))
    return weight * score


def rank_results(
    results: list[SearchResult],
    config: RankingConfig,
) -> list[SearchResult]:
    if not config.enabled or not results:
        return results

    for r in results:
        boost_total = 0.0
        for boost_type in config.boosts:
            if boost_type == RankingBoost.CONFIDENCE:
                boost_total += _compute_confidence_boost(r.metadata, config.confidence_weight)
            elif boost_type == RankingBoost.RECENCY:
                boost_total += _compute_recency_boost(r.metadata, config.recency_weight, config.recency_half_life_days)
            elif boost_type == RankingBoost.OUTCOME_PRIORITY:
                boost_total += _compute_outcome_boost(r.metadata, config.outcome_priority_weight, config.outcome_priority_order)

        r.ranked_score = min(1.0, r.relevance_score + boost_total)

    results.sort(key=lambda x: x.ranked_score or x.relevance_score, reverse=True)

    logger.debug(
        f"Ranked {len(results)} results with config: "
        f"boosts={[b.value for b in config.boosts]}"
    )
    return results
