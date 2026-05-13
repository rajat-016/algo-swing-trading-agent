# Graph Report - C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent  (2026-05-13)

## Corpus Check
- 240 files · ~292,804 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2163 nodes · 5560 edges · 88 communities detected
- Extraction: 53% EXTRACTED · 47% INFERRED · 0% AMBIGUOUS · INFERRED: 2607 edges (avg confidence: 0.7)
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

## God Nodes (most connected - your core abstractions)
1. `AnalyticsDB` - 67 edges
2. `KiteBroker` - 55 edges
3. `Stock` - 53 edges
4. `FeatureEngineer` - 52 edges
5. `run_full_pipeline()` - 50 edges
6. `SemanticRetriever` - 49 edges
7. `ReflectionService` - 48 edges
8. `TradingLoop` - 46 edges
9. `TradeJournalService` - 44 edges
10. `DriftDetectionService` - 40 edges

## Surprising Connections (you probably didn't know these)
- `Stock` --uses--> `Strategy optimizer that learns from trade history.          Responsibilities:`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\models\stock.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\strategy_optimizer.py
- `Stock` --uses--> `Initialize default trading strategies.`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\models\stock.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\strategy_optimizer.py
- `Stock` --uses--> `Load historical trades from database.`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\models\stock.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\strategy_optimizer.py
- `Stock` --uses--> `Add a completed trade for analysis.`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\models\stock.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\strategy_optimizer.py
- `Stock` --uses--> `Calculate performance metrics from trade history.`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\models\stock.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\strategy_optimizer.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (118): Extract baseline feature values from drift detector., StockAnalysis, StockAnalyzer, Base, Chartink scraper using Scrapling (StealthyFetcher).          Advantages over Pla, Get last fetched symbols., Get stocks with data for compatibility., ScraplingChartinkClient (+110 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (48): AlertRule, DriftAlert, DriftAlertManager, DriftSeverity, DriftType, BaselineManager, BaseModel, DistributionShiftAnalyzer (+40 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (80): PortfolioAllocator, PortfolioSimulator, Portfolio Allocation Module  Allocates capital across multiple signals using con, Allocate proportional to edge_score, capped at max per trade. Filters weak signa, Allocates capital across trading signals.          Strategies:     - equal: Equa, Allocate proportional to confidence scores, capped at max per trade., Simulates portfolio-level trading with allocation.     Wraps the existing TradeS, Allocate capital across signals.                  Args:             signals: Lis (+72 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (36): AdaptiveModel, Create labels based on future returns with dynamic thresholds and confidence lev, Enhanced ML model with adaptive learning from trade history.          Features:, Train ensemble model with option to include trade history., Perform time-series cross-validation (no data leakage)., Get feature importance from all models in ensemble., Create training samples from historical trades., Add completed trade to learning history. (+28 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (24): PromptTemplate, AICircuitBreaker, OllamaClient, EmbeddingCache, EmbeddingService, OrchestrationEngine, WorkflowResult, WorkflowStep (+16 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (28): AnalyticsDB, check_ai_settings(), check_chromadb(), check_duckdb(), check_imports(), check_ollama(), main(), pull_models() (+20 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (59): Run simulation with portfolio-level allocation.                  Note: This is a, RetrievalAuditor, FailurePatternAnalyzer, hybrid_search(), _build_memory_filter(), _get_semantic_retriever(), memory_health(), memory_search() (+51 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (51): BatchReflector, analyze_correlations(), correlation_health(), get_correlation_history(), _get_correlation_service(), get_diversification_score(), get_instability_alerts(), get_latest_correlation_snapshot() (+43 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (34): PortfolioConfig, RegimeConfig, DirectionalBiasAnalyzer, DirectionalBiasReport, CapitalConcentration, ExposureAnalyzer, ExposureReport, SectorExposure (+26 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (32): RegimeClassifier, ConfidenceAnalyzer, FailureAnalyzer, FeatureAttribution, _compute_adx(), _compute_atr(), _compute_bb_width(), compute_breadth_indicators() (+24 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (32): ChromaDBClient, MemoryCollectionManager, batch_generate_explanations(), cache_stats(), clear_cache(), explain_live_prediction(), explain_prediction(), explainability_health() (+24 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (19): ConfidenceScorer, from_dict(), CorrelationAnalyzer, CorrelationCluster, CorrelationPair, CorrelationReport, ExplanationCache, Symbol Loader - Loads NIFTY symbols from backend/data/symbol_mapping.json Provid (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (27): DriftAnalyzer, DriftedFeature, DriftReport, ExperimentRun, ExperimentSummarizer, ExperimentSummary, Hypothesis, HypothesisGenerator (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (29): DriftDetector, get_health_aggregator(), HealthComponent, SystemHealthAggregator, get_broker(), get_metrics_collector(), LatencyRecord, MetricsCollector (+21 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (17): SectorClusteringEngine, DiversificationScorer, InstabilityAnalyzer, InstabilityReport, DiversificationBreakdown, DiversificationScore, InstabilityAlert, InstabilityReport (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (23): BaseSettings, ChartInkClient, get_chartink_client(), Fetch stock symbols from Chartink screener using Scrapling., Extract stock symbols from HTML content using multiple strategies., get_settings(), get_strategy_target(), Settings (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (34): compute_breadth_analytics(), _below_ma(), compute_market_stress(), _consecutive_losses(), _max_drawdown(), _realized_vol(), _skew_estimate(), _volume_spike() (+26 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (14): Add a completed trade for analysis., Calculate performance metrics from trade history., Analyze performance by exit reason., Analyze which entry conditions perform best., Suggest optimizations based on trade analysis., Optimize strategy based on historical performance., Get best performing strategy based on metrics., Get complete strategy analysis report. (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (7): Validate stop loss price is reasonable.                  Returns:, Risk Manager for trading.          Enforces:     - Circuit breaker (emergency, Comprehensive order validation against all risk rules., RiskCheckResult, RiskManager, RiskMetrics, RiskRejection

### Community 19 - "Community 19"
Cohesion: 0.2
Nodes (2): App(), formatCurrency()

### Community 20 - "Community 20"
Cohesion: 0.33
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.4
Nodes (1): TradeExecutor

### Community 22 - "Community 22"
Cohesion: 0.4
Nodes (4): get_scrapling_chartink_client(), Scrapling-based Chartink scraper - Alternative to Playwright implementation. Per, Get the Scrapling-based Chartink client singleton., # NOTE: `wait=3000` tells the browser to wait 3s AFTER page stability

### Community 23 - "Community 23"
Cohesion: 0.5
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
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
Nodes (1): Analyze performance by confidence buckets.

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Calculate trade expectancy: E = (WinRate * AvgWin) - (LossRate * AvgLoss).

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Find optimal confidence threshold by iterating through buckets.         Returns

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

## Knowledge Gaps
- **70 isolated node(s):** `Database migration for tiered exit system. Adds new columns to stocks table and`, `LLMModel`, `Extract structured content from LLM text responses.`, `Get current circuit state.`, `Check if circuit is closed (normal operation).` (+65 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 25`** (2 nodes): `Monitoring.jsx`, `Monitoring()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `PortfolioIntelligence.jsx`, `PortfolioIntelligence()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (2 nodes): `ResearchIntelligence.jsx`, `ResearchIntelligence()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `run.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `intelligence_summary.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `research_assistant_prompts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `logging.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `__init__.py`
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
- **Thin community `Community 71`** (1 nodes): `check_db.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `test_edge_score.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `test_final.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `Analyze performance by confidence buckets.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `Calculate trade expectancy: E = (WinRate * AvgWin) - (LossRate * AvgLoss).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `Find optimal confidence threshold by iterating through buckets.         Returns`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `index.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_full_pipeline()` connect `Community 2` to `Community 1`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 9`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `AnalyticsDB` connect `Community 5` to `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 12`, `Community 14`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `FeatureEngineer` connect `Community 3` to `Community 0`, `Community 2`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 157 inferred relationships involving `str` (e.g. with `chromadb_persist_directory()` and `duckdb_absolute_path()`) actually correct?**
  _`str` has 157 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `AnalyticsDB` (e.g. with `TradeJournalService` and `PortfolioIntelligenceService`) actually correct?**
  _`AnalyticsDB` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `KiteBroker` (e.g. with `Create drift baseline from current model and recent data.` and `Aggregated system health dashboard across all services.`) actually correct?**
  _`KiteBroker` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `Stock` (e.g. with `TradeJournalService` and `_NumpyEncoder`) actually correct?**
  _`Stock` has 49 INFERRED edges - model-reasoned connections that need verification._