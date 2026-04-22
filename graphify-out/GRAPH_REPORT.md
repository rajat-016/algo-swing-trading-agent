# Graph Report - C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent  (2026-04-22)

## Corpus Check
- 27 files · ~7,235 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 139 nodes · 229 edges · 20 communities detected
- Extraction: 67% EXTRACTED · 33% INFERRED · 0% AMBIGUOUS · INFERRED: 75 edges (avg confidence: 0.68)
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

## God Nodes (most connected - your core abstractions)
1. `TradingLoop` - 25 edges
2. `StockAnalyzer` - 19 edges
3. `ZerodhaBroker` - 19 edges
4. `ModelTrainer` - 15 edges
5. `FeatureEngineer` - 14 edges
6. `lifespan()` - 10 edges
7. `Stock` - 9 edges
8. `get_settings()` - 8 edges
9. `OrderSide` - 6 edges
10. `OrderType` - 6 edges

## Surprising Connections (you probably didn't know these)
- `lifespan()` --calls--> `get_chartink_client()`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\api\main.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\broker\chartink.py
- `main()` --calls--> `get_settings()`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\main.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\core\config.py
- `lifespan()` --calls--> `init_db()`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\api\main.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\core\database.py
- `lifespan()` --calls--> `get_broker()`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\api\main.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\broker\zerodha.py
- `lifespan()` --calls--> `StockAnalyzer`  [INFERRED]
  C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\api\main.py → C:\Users\asus\Documents\Projects\trading\algo-swing-trading-agent\backend\services\ai\analyzer.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.13
Nodes (3): TradingLoop, start_trading(), ZerodhaBroker

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (2): FeatureEngineer, ModelTrainer

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (9): get_settings(), init_db(), create_app(), lifespan(), main(), get_trading_status(), set_trading_loop(), stop_trading() (+1 more)

### Community 3 - "Community 3"
Cohesion: 0.2
Nodes (12): Base, BaseModel, ExitReason, Stock, StockStatus, exit_stock(), get_pending_analysis(), get_stock() (+4 more)

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (11): BaseSettings, Config, Settings, TradingMode, ZerodhaConfig, Enum, OrderSide, OrderType (+3 more)

### Community 5 - "Community 5"
Cohesion: 0.23
Nodes (2): StockAnalysis, StockAnalyzer

### Community 6 - "Community 6"
Cohesion: 0.29
Nodes (2): ChartInkClient, get_chartink_client()

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (0): 

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (0): 

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (0): 

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (0): 

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **1 isolated node(s):** `Config`
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 7`** (2 nodes): `App()`, `App.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 8`** (1 nodes): `run.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 9`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `logging.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `index.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `index.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TradingLoop` connect `Community 0` to `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.370) - this node is a cross-community bridge._
- **Why does `StockAnalyzer` connect `Community 5` to `Community 0`, `Community 1`, `Community 2`?**
  _High betweenness centrality (0.239) - this node is a cross-community bridge._
- **Why does `ZerodhaBroker` connect `Community 0` to `Community 2`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `TradingLoop` (e.g. with `ZerodhaBroker` and `ChartInkClient`) actually correct?**
  _`TradingLoop` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `StockAnalyzer` (e.g. with `ZerodhaBroker` and `FeatureEngineer`) actually correct?**
  _`StockAnalyzer` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ZerodhaBroker` (e.g. with `StockAnalysis` and `StockAnalyzer`) actually correct?**
  _`ZerodhaBroker` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ModelTrainer` (e.g. with `StockAnalysis` and `StockAnalyzer`) actually correct?**
  _`ModelTrainer` has 4 INFERRED edges - model-reasoned connections that need verification._