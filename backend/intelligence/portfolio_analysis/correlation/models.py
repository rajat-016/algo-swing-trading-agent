from __future__ import annotations
from typing import Any
from dataclasses import dataclass, field


@dataclass
class RollingWindowSnapshot:
    end_date: str
    window_start: str
    window_end: str
    avg_correlation: float
    min_correlation: float
    max_correlation: float
    pair_count: int
    high_corr_count: int


@dataclass
class RollingCorrelationResult:
    windows: list[RollingWindowSnapshot]
    correlation_timeseries: list[dict[str, Any]]
    current_avg_correlation: float
    trend: str
    stability_score: float
    window_size_days: int
    step_days: int


@dataclass
class SectorCluster:
    sector: str
    symbols: list[str]
    intra_sector_avg_corr: float
    intra_sector_min_corr: float
    intra_sector_max_corr: float
    inter_sector_avg_corr: float
    concentration_pct: float
    is_diversified: bool


@dataclass
class SectorClusteringReport:
    clusters: list[SectorCluster]
    inter_sector_matrix: list[list[float]]
    sectors: list[str]
    cross_sector_pairs: list[dict[str, Any]]
    overall_inter_sector_avg: float


@dataclass
class InstabilityAlert:
    symbol_a: str
    symbol_b: str
    sector_a: str | None
    sector_b: str | None
    corr_change: float
    prev_corr: float
    curr_corr: float
    direction: str
    severity: str
    description: str


@dataclass
class InstabilityReport:
    alerts: list[InstabilityAlert]
    correlation_regime: str
    avg_correlation_now: float
    avg_correlation_before: float
    avg_correlation_change: float
    regime_transitions: list[dict[str, Any]]


@dataclass
class DiversificationBreakdown:
    component: str
    value: float
    score: float
    weight: float
    status: str


@dataclass
class DiversificationScore:
    effective_n: float
    avg_pairwise_correlation: float
    sector_diversification_score: float
    concentration_penalty: float
    regime_context_score: float
    overall_score: float
    breakdown: list[DiversificationBreakdown]
    total_holdings: int
    num_sectors: int
