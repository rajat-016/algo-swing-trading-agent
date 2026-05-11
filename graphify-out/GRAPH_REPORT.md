# Graph Report - C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent  (2026-05-11)

## Corpus Check
- 127 files · ~151,741 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 974 nodes · 2120 edges · 63 communities detected
- Extraction: 56% EXTRACTED · 44% INFERRED · 0% AMBIGUOUS · INFERRED: 931 edges (avg confidence: 0.68)
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

## God Nodes (most connected - your core abstractions)
1. `FeatureEngineer` - 52 edges
2. `KiteBroker` - 48 edges
3. `run_full_pipeline()` - 46 edges
4. `TradingLoop` - 44 edges
5. `Stock` - 39 edges
6. `OllamaClient` - 32 edges
7. `StockAnalyzer` - 27 edges
8. `InferenceService` - 26 edges
9. `ZerodhaError` - 26 edges
10. `AdaptiveModel` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Get performance summary.` --uses--> `FeatureEngineer`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\adaptive_model.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\features.py
- `StockAnalyzer` --calls--> `analyzer()`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\analyzer.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\trading\loop.py
- `ChromaDBClient` --uses--> `Settings`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\ai\inference\chromadb_client.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\core\config.py
- `ChromaDBClient` --uses--> `InferenceService`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\ai\inference\chromadb_client.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\ai\inference\service.py
- `DuckDBAnalytics` --uses--> `InferenceService`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\ai\inference\duckdb_setup.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\ai\inference\service.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (57): DuckDBManager, DuckDBAnalytics, migrate(), Database migration for tiered exit system. Adds new columns to stocks table and, ModelExporter, check_overfitting(), generate_non_tech_output(), Detect overfitting by comparing metrics across windows.     - High accuracy but (+49 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (29): AdaptiveModel, Create labels based on future returns with dynamic thresholds and confidence lev, Enhanced ML model with adaptive learning from trade history.          Features:, Train ensemble model with option to include trade history., Perform time-series cross-validation (no data leakage)., Get feature importance from all models in ensemble., Create training samples from historical trades., Add completed trade to learning history. (+21 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (62): CircuitState, Enum, OrderSide, OrderType, ProductType, Exception, AuthenticationError, BrokerError (+54 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (29): PortfolioAllocator, PortfolioSimulator, Portfolio Allocation Module  Allocates capital across multiple signals using con, Allocate proportional to edge_score, capped at max per trade. Filters weak signa, Allocates capital across trading signals.          Strategies:     - equal: Equa, Allocate proportional to confidence scores, capped at max per trade., Simulates portfolio-level trading with allocation.     Wraps the existing TradeS, Run simulation with portfolio-level allocation.                  Note: This is a (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (34): Base, BaseModel, ChartInkClient, get_chartink_client(), get_settings(), get_db(), get_engine(), get_engine_property() (+26 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (10): Extract baseline feature values from drift detector., StockAnalysis, StockAnalyzer, DecisionEngine, DriftDetector, create_drift_baseline(), get_drift_status(), Create drift baseline from current model and recent data. (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (7): PromptTemplate, AICircuitBreaker, OrchestrationEngine, WorkflowResult, WorkflowStep, PromptRegistry, InferenceService

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (12): ChromaDBClient, get_live_accuracy(), get_predictions(), PredictionMonitor, exit_stock(), get_analytics_summary(), get_pending_analysis(), get_portfolio_summary() (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (11): OllamaClient, extract_json(), InferenceMetricsSummary, InferenceRecord, LLMModel, ModelConfig, parse_as(), Extract structured content from LLM text responses. (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.12
Nodes (21): Get performance summary., Stock, Load historical trades from database., Add a completed trade for analysis., Calculate performance metrics from trade history., Analyze performance by exit reason., Analyze which entry conditions perform best., Suggest optimizations based on trade analysis. (+13 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (5): EmbeddingCache, EmbeddingService, broadcast_update(), ConnectionManager, websocket_endpoint()

### Community 11 - "Community 11"
Cohesion: 0.09
Nodes (4): Calibrator, LSTMPredictor, TradingModel, ModelTrainer

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (9): Symbol Loader - Loads NIFTY symbols from backend/data/symbol_mapping.json Provid, Get list of available index keys in mapping file., Get total symbol count for given indices., Load NIFTY symbols from mapping JSON file., Load symbols from mapping file.          Args:             indices: "all" for NI, Get metadata for a specific symbol., SymbolLoader, loader() (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (17): CircuitBreaker, Circuit breaker pattern implementation to prevent cascading failures. Useful for, Record a failed call., Call a function with circuit breaker protection.                  Args:, Async version of call method., Circuit breaker states., Manually reset the circuit breaker to closed state., Circuit breaker to prevent cascading failures.          States:     - CLOSED: No (+9 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (16): BaseSettings, check_ai_settings(), check_chromadb(), check_duckdb(), check_imports(), check_ollama(), main(), pull_models() (+8 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (7): Validate stop loss price is reasonable.                  Returns:, Risk Manager for trading.          Enforces:     - Circuit breaker (emergency, Comprehensive order validation against all risk rules., RiskCheckResult, RiskManager, RiskMetrics, RiskRejection

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (10): get_scrapling_chartink_client(), Scrapling-based Chartink scraper - Alternative to Playwright implementation. Per, Chartink scraper using Scrapling (StealthyFetcher).          Advantages over Pla, Get last fetched symbols., Get stocks with data for compatibility., Get the Scrapling-based Chartink client singleton., Fetch stock symbols from Chartink screener using Scrapling., # NOTE: `wait=3000` tells the browser to wait 3s AFTER page stability (+2 more)

### Community 17 - "Community 17"
Cohesion: 0.2
Nodes (2): App(), formatCurrency()

### Community 18 - "Community 18"
Cohesion: 0.4
Nodes (1): TradeExecutor

### Community 19 - "Community 19"
Cohesion: 0.5
Nodes (2): check_lookahead_bias(), Verify no lookahead bias exists:     1. Labels use shift(-lookahead) but only on

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
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
Nodes (1): Analyze performance by confidence buckets.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Calculate trade expectancy: E = (WinRate * AvgWin) - (LossRate * AvgLoss).

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Find optimal confidence threshold by iterating through buckets.         Returns

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

## Knowledge Gaps
- **69 isolated node(s):** `Database migration for tiered exit system. Adds new columns to stocks table and`, `LLMModel`, `Extract structured content from LLM text responses.`, `Get current circuit state.`, `Check if circuit is closed (normal operation).` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 20`** (2 nodes): `Monitoring.jsx`, `Monitoring()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `run.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `logging.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `__init__.py`
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
- **Thin community `Community 39`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `__init__.py`
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
- **Thin community `Community 46`** (1 nodes): `check_db.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `test_edge_score.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `test_final.py`
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
- **Thin community `Community 56`** (1 nodes): `Analyze performance by confidence buckets.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Calculate trade expectancy: E = (WinRate * AvgWin) - (LossRate * AvgLoss).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Find optimal confidence threshold by iterating through buckets.         Returns`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `index.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_full_pipeline()` connect `Community 0` to `Community 11`, `Community 1`, `Community 3`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `TradingLoop` connect `Community 4` to `Community 2`, `Community 5`, `Community 9`, `Community 13`, `Community 16`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `FeatureEngineer` connect `Community 1` to `Community 9`, `Community 3`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 50 inferred relationships involving `str` (e.g. with `chromadb_persist_directory()` and `duckdb_absolute_path()`) actually correct?**
  _`str` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `FeatureEngineer` (e.g. with `FeaturePipeline` and `AdaptiveModel`) actually correct?**
  _`FeatureEngineer` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `KiteBroker` (e.g. with `Create drift baseline from current model and recent data.` and `StockAnalysis`) actually correct?**
  _`KiteBroker` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `run_full_pipeline()` (e.g. with `DuckDBManager` and `str`) actually correct?**
  _`run_full_pipeline()` has 42 INFERRED edges - model-reasoned connections that need verification._