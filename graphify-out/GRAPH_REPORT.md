# Graph Report - C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent  (2026-05-15)

## Corpus Check
- 267 files · ~380,694 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2431 nodes · 6621 edges · 95 communities detected
- Extraction: 51% EXTRACTED · 49% INFERRED · 0% AMBIGUOUS · INFERRED: 3275 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]

## God Nodes (most connected - your core abstractions)
1. `error()` - 165 edges
2. `AnalyticsDB` - 67 edges
3. `Stock` - 60 edges
4. `KiteBroker` - 56 edges
5. `run_full_pipeline()` - 56 edges
6. `SemanticRetriever` - 55 edges
7. `FeatureEngineer` - 52 edges
8. `ReflectionService` - 48 edges
9. `TradingLoop` - 46 edges
10. `TradeJournalService` - 45 edges

## Surprising Connections (you probably didn't know these)
- `Stock` --uses--> `Load historical trades from database.`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\models\stock.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\strategy_optimizer.py
- `Load model with trade history.` --uses--> `FeatureEngineer`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\adaptive_model.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\features.py
- `StockAnalyzer` --calls--> `analyzer()`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\analyzer.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\trading\loop.py
- `TradeSimulator` --uses--> `Run simulation with portfolio-level allocation.                  Note: This is a`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backtesting\backtest_engine\trade_simulator.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backtesting\portfolio\allocator.py
- `get_ai_settings()` --calls--> `check_ai_settings()`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\ai\config\settings.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\scripts\bootstrap_ai.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (129): Extract baseline feature values from drift detector., StockAnalysis, StockAnalyzer, Base, Chartink scraper using Scrapling (StealthyFetcher).          Advantages over Pla, Get last fetched symbols., Get stocks with data for compatibility., ScraplingChartinkClient (+121 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (92): PortfolioAllocator, PortfolioSimulator, Portfolio Allocation Module  Allocates capital across multiple signals using con, Allocate proportional to edge_score, capped at max per trade. Filters weak signa, Allocates capital across trading signals.          Strategies:     - equal: Equa, Allocate proportional to confidence scores, capped at max per trade., Simulates portfolio-level trading with allocation.     Wraps the existing TradeS, Allocate capital across signals.                  Args:             signals: Lis (+84 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (48): AlertRule, DriftAlert, DriftAlertManager, DriftSeverity, DriftType, BaselineManager, BaseModel, DistributionShiftAnalyzer (+40 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (40): PromptTemplate, PortfolioConfig, ContextBundle, ContextInjector, OrchestrationEngine, WorkflowResult, WorkflowStep, InvestigationRecommendation (+32 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (30): AdaptiveModel, Create labels based on future returns with dynamic thresholds and confidence lev, Enhanced ML model with adaptive learning from trade history.          Features:, Train ensemble model with option to include trade history., Perform time-series cross-validation (no data leakage)., Get feature importance from all models in ensemble., Create training samples from historical trades., Add completed trade to learning history. (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (22): AnalyticsDB, check_ai_settings(), check_chromadb(), check_duckdb(), check_imports(), check_ollama(), main(), pull_models() (+14 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (45): AiAuditLogger, AuditEntry, _sanitize_details(), ConfidenceThresholdEnforcer, GovernanceConfig, DriftAnalyzer, DriftedFeature, DriftReport (+37 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (32): RetrievalAuditor, MemoryCollectionManager, EmbeddingService, hybrid_search(), _build_memory_filter(), MemoryEmbedder, _get_semantic_retriever(), memory_health() (+24 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (30): BaseEvaluator, BenchmarkConfig, EvalMetric, EvaluationResult, MetricType, BaseEvaluator, BenchmarkRunner, BenchmarkSuite (+22 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (34): RegimeClassifier, ConfidenceScorer, DirectionalBiasAnalyzer, DirectionalBiasReport, ExperimentSummarizer, FailureAnalyzer, _compute_adx(), _compute_atr() (+26 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (46): ChartInkClient, Fetch stock symbols from Chartink screener using Scrapling., analyze_correlations(), correlation_health(), get_correlation_history(), _get_correlation_service(), get_diversification_score(), get_instability_alerts() (+38 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (23): Load model with trade history., CorrelationAnalyzer, CorrelationCluster, CorrelationPair, CorrelationReport, EmbeddingCache, Find the most recent full_report_*.json file., Load a backtest report JSON file. (+15 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (12): BatchReflector, IntelligenceSummary, IntelligenceSummaryGenerator, IntelligenceSummaryReport, Extract structured content from LLM text responses., ResponseParser, PostTradeReflection, PostTradeReflector (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (26): Run simulation with portfolio-level allocation.                  Note: This is a, FailurePatternAnalyzer, MemoryFilter, ReasoningEngine, TradeIntelligenceService, _compute_composite(), EnhancedSimilarityResult, _get_feature_overlap() (+18 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (26): ChromaDBClient, _broadcast_ws(), get_live_accuracy(), get_predictions(), ContextRequest, enriched_llm_call(), EnrichedLLMRequest, get_context() (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (21): from_dict(), RegimeConfig, analyze_regime(), get_current_regime(), get_regime_distribution(), get_regime_history(), _get_regime_service(), get_regime_stats() (+13 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (27): ConfidenceAnalyzer, batch_generate_explanations(), cache_stats(), clear_cache(), explain_live_prediction(), explain_prediction(), explainability_health(), explanation_coverage() (+19 more)

### Community 17 - "Community 17"
Cohesion: 0.07
Nodes (20): SectorClusteringEngine, DiversificationScorer, CapitalConcentration, ExposureAnalyzer, ExposureReport, SectorExposure, InstabilityAnalyzer, InstabilityReport (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.06
Nodes (24): BaseSettings, get_chartink_client(), get_settings(), get_strategy_target(), Settings, TradingMode, ZerodhaConfig, get_db() (+16 more)

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (34): compute_breadth_analytics(), _below_ma(), compute_market_stress(), _consecutive_losses(), _max_drawdown(), _realized_vol(), _skew_estimate(), _volume_spike() (+26 more)

### Community 20 - "Community 20"
Cohesion: 0.1
Nodes (22): get_health_aggregator(), HealthComponent, SystemHealthAggregator, get_metrics_collector(), LatencyRecord, MetricsCollector, ServiceMetrics, _check_ai_health() (+14 more)

### Community 21 - "Community 21"
Cohesion: 0.12
Nodes (7): Validate stop loss price is reasonable.                  Returns:, Risk Manager for trading.          Enforces:     - Circuit breaker (emergency, Comprehensive order validation against all risk rules., RiskCheckResult, RiskManager, RiskMetrics, RiskRejection

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (5): App(), formatCurrency(), formatCurrency(), formatPercent(), TierOverview()

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (1): LSTMPredictor

### Community 24 - "Community 24"
Cohesion: 0.33
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 0.4
Nodes (1): TradeExecutor

### Community 26 - "Community 26"
Cohesion: 0.4
Nodes (4): get_scrapling_chartink_client(), Scrapling-based Chartink scraper - Alternative to Playwright implementation. Per, Get the Scrapling-based Chartink client singleton., # NOTE: `wait=3000` tells the browser to wait 3s AFTER page stability

### Community 27 - "Community 27"
Cohesion: 0.5
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 0.67
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (0): 

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (0): 

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (0): 

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (0): 

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (0): 

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (0): 

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (0): 

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (0): 

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (0): 

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (0): 

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (0): 

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Analyze performance by confidence buckets.

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Calculate trade expectancy: E = (WinRate * AvgWin) - (LossRate * AvgLoss).

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Find optimal confidence threshold by iterating through buckets.         Returns

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (0): 

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (0): 

### Community 93 - "Community 93"
Cohesion: 1.0
Nodes (0): 

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **70 isolated node(s):** `Database migration for tiered exit system. Adds new columns to stocks table and`, `LLMModel`, `Extract structured content from LLM text responses.`, `Get current circuit state.`, `Check if circuit is closed (normal operation).` (+65 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 29`** (2 nodes): `Monitoring.jsx`, `Monitoring()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `PortfolioIntelligence.jsx`, `PortfolioIntelligence()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `ResearchIntelligence.jsx`, `ResearchIntelligence()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `run.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `intelligence_summary.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `research_assistant_prompts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `logging.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `check_db.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `test_edge_score.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `test_final.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Analyze performance by confidence buckets.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Calculate trade expectancy: E = (WinRate * AvgWin) - (LossRate * AvgLoss).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Find optimal confidence threshold by iterating through buckets.         Returns`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (1 nodes): `index.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `error()` connect `Community 10` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 15`, `Community 16`, `Community 17`, `Community 18`, `Community 23`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `FeatureEngineer` connect `Community 4` to `Community 0`, `Community 1`, `Community 11`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `AnalyticsDB` connect `Community 5` to `Community 3`, `Community 6`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 15`, `Community 17`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 202 inferred relationships involving `str` (e.g. with `chromadb_persist_directory()` and `duckdb_absolute_path()`) actually correct?**
  _`str` has 202 INFERRED edges - model-reasoned connections that need verification._
- **Are the 163 inferred relationships involving `error()` (e.g. with `.initialize()` and `.initialize()`) actually correct?**
  _`error()` has 163 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `AnalyticsDB` (e.g. with `TradeJournalService` and `PortfolioIntelligenceService`) actually correct?**
  _`AnalyticsDB` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 56 inferred relationships involving `Stock` (e.g. with `TradeJournalService` and `_NumpyEncoder`) actually correct?**
  _`Stock` has 56 INFERRED edges - model-reasoned connections that need verification._