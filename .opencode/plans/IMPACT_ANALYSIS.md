# System-Wide Impact Analysis: AI-Native Trading Copilot Phase 1

**Date:** 2026-05-09
**Status:** Draft (Analysis Only)
**Priority:** High

---

## 1. Executive Summary

The AI-Native Trading Copilot Phase 1 introduces an intelligence augmentation layer on top of the existing ML-first swing trading system. The current codebase is well-structured for this evolution — it already has modular ML pipelines, walk-forward backtesting, and clean separation between `core/`, `services/`, and `backtesting/`.

**Key findings:**

- **Strong Foundation.** The `backend/core/pipeline/`, `backend/core/model/`, `backend/core/decision/`, and `core/monitoring/` modules already provide the architectural primitives needed. The `backtesting/` system is fully feature-aligned with the live system (60 curated features through `SELECTED_FEATURES`).

- **Three critical architectural gaps:**
  1. **No vector/semantic storage exists** — ChromaDB must be introduced from scratch. The current data layer is SQLite (live) + DuckDB (backtesting, OHLCV only).
  2. **No LLM runtime integration** — Ollama + Qwen2.5 must be integrated. No prompt management, inference pipeline, or AI orchestration exists.
  3. **No AI intelligence modules** — The 8 copilot components (market regime, trade intelligence, portfolio intelligence, trade journal, market memory, explainability, quant research assistant, reflection engine) are entirely new code.

- **Dual-database architecture required.** The live system uses SQLite for operational data. Backtesting uses DuckDB for analytical data. Phase 1 introduces a third database (ChromaDB for vectors) and extends DuckDB into the live system for analytical queries. This creates a **three-database architecture** that needs careful lifecycle management.

- **Infrastructure scale is appropriate.** Local Ollama inference on CPU/GPU is viable for Phase 1 scope. The system is not yet at a scale requiring distributed inference or cloud LLM APIs.

- **No breaking changes to existing flows.** The copilot layer is additive. It does not modify the trading loop, broker integration, feature pipeline, model training, or backtesting system. It reads from existing data stores and adds new intelligence APIs.

- **Estimated new code:** ~3,000-5,000 lines across ~30 new files. Minimal refactoring of existing code (<200 lines changed).

---

## 2. Current System Overview

### 2.1 Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React SPA)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend (Port 8000)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ api/     │  │ services/│  │ core/    │  │ models/    │  │
│  │ routes   │  │ broker   │  │ pipeline │  │ SQLAlchemy │  │
│  │ websocket│  │ trading  │  │ model    │  │ Stock      │  │
│  │          │  │ ai       │  │ decision │  │ Prediction │  │
│  │          │  │ risk     │  │ monitoring│ │ ExitLog    │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Data Stores                               │
│  ┌──────────────────┐  ┌────────────────────────────────┐   │
│  │ SQLite (trading.db)│  │ DuckDB (market_data.duckdb)   │   │
│  └──────────────────┘  └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Existing Strengths Relevant to Phase 1

| Strength | Relevance |
|----------|-----------|
| ML-first architecture with clean `core/` | New AI modules follow same layering pattern |
| Modular feature pipeline (69 curated features) | Feature snapshots for explainability straightforward |
| Prediction logging to SQLite (`PredictionLog`) | Foundation for trade memory and outcome tracking |
| Walk-forward backtesting with full metrics | Historical data available for AI context |
| Feature alignment between backtesting and live | Consistent feature space for SHAP explainability |
| Tiered exit tracking (`ExitLog` model) | Rich exit metadata for trade intelligence |
| Drift detection (PSI + KS tests) | Foundation for degradation monitoring |
| WebSocket broadcast for real-time updates | Architecture for pushing AI insights to frontend |
| Monitoring API routes exist | Pattern to follow for new intelligence APIs |

### 2.3 Technical Debt and Gaps

| Issue | Location | Severity | Phase 1 Impact |
|-------|----------|----------|----------------|
| Frontend Monitoring API imports broken | `frontend/src/api/index.js`, `frontend/src/components/Monitoring.jsx` | Medium | Must fix before adding new AI monitoring routes |
| SQLite for analytical queries — performance degrades | `backend/core/database.py` | Low | DuckDB introduction offloads analytics |
| No feature snapshot storage | `backend/services/ai/analyzer.py:111` | Medium | Need feature persistence for explainability |
| Model registry uses simple joblib files | `backend/core/model/registry.py` | Low | AI copilot needs model version awareness |
| All frontend state in single `App.js` | `frontend/src/App.js` | Low | Becomes a constraint as intelligence dashboards grow |
| No embedding infrastructure | N/A | High | Must build from scratch |
| No LLM inference pipeline | N/A | High | Must build from scratch |
| No prompt management system | N/A | High | Must build from scratch |

---

## 3. Architecture Impact Analysis

### 3.1 Backend Architecture Impact

#### 3.1.1 Impacted Modules

| Module | Impact | Change |
|--------|--------|--------|
| `backend/intelligence/` (new) | **CREATE** | 8 submodules: market_regime, trade_analysis, portfolio_analysis, reflection_engine, explainability, trade_memory, research_assistant |
| `backend/memory/` (new) | **CREATE** | ChromaDB integration, embedding pipeline, retrieval layer |
| `backend/ai/` (new) | **CREATE** | Ollama client, prompt management, inference orchestration |
| `backend/core/pipeline/feature_pipeline.py` | MODIFY | Add feature snapshot export method |
| `backend/api/routes/` | MODIFY | Add 6 new intelligence API routes |
| `backend/api/main.py` | MODIFY | Initialize ChromaDB, Ollama, AI modules on startup |
| `backend/models/` | MODIFY | Add regime, reflection, market_memory tables |
| `backend/core/config.py` | MODIFY | Add ChromaDB, Ollama, embedding config |

#### 3.1.2 Service Boundaries

**Current state:** Monolithic FastAPI process. `TradingLoop`, `StockAnalyzer`, and `KiteBroker` all live in the same process. The graphify knowledge graph confirms `TradingLoop` and `StockAnalyzer` are the top 2 most-connected nodes (25 and 19 edges respectively).

**Phase 1 recommendation:** AI copilot modules remain in-process as a separate `intelligence/` package. No microservices — latency requirements (<5s AI response) and local inference make in-process viable and simpler.

**Future readiness:** Design with adapter interfaces so modules can be extracted into separate services in Phase 2 (agent orchestration).

#### 3.1.3 Synchronous vs Async

| Existing Flow | Current | Phase 1 |
|--------------|---------|---------|
| Trading loop | Async (asyncio) | Unchanged |
| ML prediction | Sync inside async | Unchanged |
| AI copilot queries | N/A | **Async** — wrap LLM calls with timeout |
| Embedding generation | N/A | **Sync** — lightweight, <2s, blocking |
| Semantic retrieval | N/A | **Async** — ChromaDB queries via wrapper |

### 3.2 Feature Pipeline Impact

**Required change in `backend/core/pipeline/feature_pipeline.py`:**
- Add `export_snapshot(features_df, symbol, timestamp)` method
- Store feature vector for SHAP analysis and historical retrieval
- New DuckDB table: `feature_snapshots`

**Feature drift integration:**
`DriftDetector` already exists in `backend/core/monitoring/drift_detector.py`. Phase 1 needs:
- Persistent baseline storage in DuckDB (currently uses JSON file)
- Scheduled drift monitoring (currently checked per-prediction in `StockAnalyzer.analyze()`)
- Integration with `ResearchAssistant` for drift reporting

**Feature versioning:**
`SELECTED_FEATURES` in `backend/core/pipeline/feature_pipeline.py:8-69` is hardcoded. Phase 1 needs:
- Feature set versioning in model registry
- Backward compatibility when feature sets change
- Metadata linking predictions to feature version

### 3.3 Labeling & Prediction Pipeline Impact

`PredictionMonitor` already handles: logging predictions, updating outcomes, querying live accuracy.

**Phase 1 additions:**
- Confidence calibration tracking over time
- Prediction explainability storage (SHAP values linked to prediction_id)
- Historical prediction retrieval for AI context

**New columns on `PredictionLog`:**
```python
shap_values = Column(JSON, nullable=True)
regime_at_prediction = Column(String(20), nullable=True)
feature_snapshot_id = Column(Integer, nullable=True)
reasoning = Column(Text, nullable=True)
```

### 3.4 Backtesting System Impact

**Files impacted in `backtesting/`:**
- `backtesting/export/report_generator.py` — Add intelligence export step
- `backtesting/run_backtest.py` — Add optional AI analysis step (gated by `--analyze-ai`)
- `backtesting/analysis/report_analyzer.py` — Extend with AI summary

**Explainability persistence:**
Backtesting currently evaluates metrics but does not store SHAP explainability. Phase 1 requires SHAP value computation during backtesting (on test predictions) and storing alongside backtest results.

### 3.5 Data Architecture Impact

#### 3.5.1 Structured Storage Evolution (DuckDB + SQLite)

| Database | Purpose | New Tables |
|----------|---------|------------|
| SQLite (`trading.db`) | Operational CRUD (unchanged) | None |
| DuckDB (`data/analytics.duckdb`) | Analytical queries, feature snapshots, SHAP values | `feature_snapshots`, `shap_values`, `regime_history`, `portfolio_states` |
| ChromaDB (`data/chromadb/`) | Vector embeddings for semantic memory | Collections: `trade_memory`, `market_memory`, `research_memory`, `reflections` |

#### 3.5.2 ChromaDB Collections

| Collection | Documents | Metadata Filters | Embedding Model |
|-----------|-----------|-----------------|-----------------|
| `trade_memory` | Trade reasoning, failures, observations | symbol, regime, outcome, date | nomic-embed-text |
| `market_memory` | Regime transitions, volatility events | regime_type, date, severity | nomic-embed-text |
| `research_memory` | Feature observations, experiment findings | category, date, strategy | nomic-embed-text |
| `reflections` | AI-generated patterns, degradation warnings | type, date, severity | nomic-embed-text |

#### 3.5.3 Embedding Volume Projection

Projected ~280 docs/month. At nomic-embed-text (768 dimensions, ~2KB/doc), monthly storage is ~0.5 MB. ChromaDB handles this easily with default configuration. No partitioning needed at Phase 1 scale.

### 3.6 API Layer Impact

#### 3.6.1 New Intelligence Endpoints

| Endpoint | Method | Purpose | Latency SLA | Async |
|----------|--------|---------|-------------|-------|
| `/intelligence/regime/current` | GET | Current market regime | <5s | Yes |
| `/intelligence/trade/explain` | POST | Explain a trade | <3s | Yes |
| `/intelligence/portfolio/risk` | GET | Portfolio risk analysis | <3s | Yes |
| `/intelligence/memory/search` | POST | Semantic search | <4s | Yes |
| `/intelligence/research/query` | POST | Research assistant query | <5s | Yes |
| `/intelligence/reflection/generate` | POST | Generate reflections | <5s | Yes |

**Route file structure:**
```
backend/api/routes/
├── intelligence.py     (NEW) — regime, trade explain, portfolio risk
├── memory.py           (NEW) — semantic search
├── research.py         (NEW) — research assistant
└── reflection.py       (NEW) — reflection engine
```

#### 3.6.2 Response Standardization

Current API responses are ad-hoc dicts. AI copilot requires consistent envelopes:

```python
{
    "status": "success" | "error",
    "data": { ... },
    "metadata": {
        "model": "qwen2.5:7b",
        "latency_ms": 1234,
        "confidence": 0.85,
        "sources_used": ["trade_memory", "market_memory"]
    }
}
```

### 3.7 Frontend & Dashboard Impact

#### 3.7.1 New UI Components

| Component | Type | Complexity |
|-----------|------|------------|
| Market Intelligence Dashboard | New tab | Medium |
| Portfolio Intelligence Dashboard | New tab | Medium |
| Trade Explanation Panel | Modal/drawer | Low |
| Semantic Search UI | Search bar + results | Medium |
| Research Dashboard | New tab | High |

#### 3.7.2 WebSocket Expansion

New events: `ai_insight`, `regime_change`, `drift_alert`

#### 3.7.3 State Management

Current: All state in `App.js` `useState` hooks. Recommend React Context + custom hooks for AI data.

#### 3.7.4 Visualization Additions

- **Regime timeline** — Gantt-style chart showing regime transitions
- **Correlation heatmap** — Portfolio holdings correlation matrix
- **Exposure treemap** — Sector/capital allocation
- **Feature importance** — Horizontal bar chart for SHAP values
- **Confidence calibration** — Reliability diagram

### 3.8 Infrastructure & Runtime Impact

#### 3.8.1 Ollama Integration

**Hardware requirements:**
- **Qwen2.5 7B:** ~4GB RAM, CPU inference at 5-10 tokens/sec. GPU (6GB+ VRAM) recommended for <3s latency
- **nomic-embed-text:** ~0.5GB RAM, CPU inference at <1s per embedding
- **Local inference viable** for Phase 1 (~2-11 AI queries/day projected)

#### 3.8.2 Resource Contention Risks

| Scenario | Risk | Mitigation |
|----------|------|------------|
| LLM inference during trading cycle | Cycle delayed if LLM >5s | Separate thread pool; 10s timeout |
| Embedding generation during backtesting | Pipeline slowed | Embedding is offline task |
| ChromaDB write during prediction | Recording latency | Async write with queue |
| Ollama + Backend on same CPU | CPU contention | Pin Ollama cores; `OMP_NUM_THREADS` |

#### 3.8.3 Docker Compose Update

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 3.9 Monitoring & Observability Impact

#### 3.9.1 New Metrics

| Metric | Type | Prometheus Name |
|--------|------|-----------------|
| Inference latency (LLM) | Histogram | `ai_inference_latency_ms` |
| Embedding generation latency | Histogram | `ai_embedding_latency_ms` |
| ChromaDB query latency | Histogram | `chromadb_query_latency_ms` |
| Semantic retrieval precision | Gauge | `semantic_retrieval_precision` |
| Feature drift count | Gauge | `feature_drift_count` |
| Regime stability | Gauge | `regime_stability` |

#### 3.9.2 Logging Additions

New log categories: `ai/inference.log`, `ai/embedding.log`, `ai/memory.log`, `ai/reflection.log`

### 3.10 Security & Governance Impact

| Concern | Mitigation |
|---------|------------|
| Hallucinated trade reasoning | Structured prompts with actual data; no free-form AI for critical paths |
| Confidence threshold bypass | Enforce minimum confidence (0.50) for AI insights |
| Data leakage between symbols | Separate ChromaDB collections; metadata-scoped retrieval |

**All AI outputs must include:** confidence score, data sources, generation timestamp, warning if below threshold.

---

## 4. Component Impact Matrix

### 4.1 New Modules

| Component | Priority | Complexity | Key Dependencies | Effort |
|-----------|----------|------------|-----------------|--------|
| `memory/chromadb_manager.py` | P0 | Medium | ChromaDB | 1d |
| `memory/embeddings.py` | P0 | Low | nomic-embed-text | 0.5d |
| `memory/retrieval.py` | P0 | Medium | ChromaDB, Embeddings | 1d |
| `ai/inference.py` | P0 | Low | Ollama | 0.5d |
| `ai/prompts/` | P0 | Low | None | 0.5d |
| `ai/orchestration.py` | P1 | Medium | Inference, Memory, Prompts | 1d |
| `intelligence/market_regime/engine.py` | P0 | Medium | Inference, FeaturePipeline | 2d |
| `intelligence/trade_analysis/engine.py` | P0 | Medium | Inference, PredictionLog | 2d |
| `intelligence/portfolio_analysis/engine.py` | P1 | Medium | Inference, Holdings | 1.5d |
| `intelligence/explainability/engine.py` | P0 | Medium | SHAP, FeaturePipeline | 1.5d |
| `intelligence/trade_memory/journal.py` | P0 | Medium | Memory, PredictionLog | 1.5d |
| `intelligence/reflection_engine/engine.py` | P1 | High | Inference, Memory | 2d |
| `intelligence/research_assistant/engine.py` | P2 | High | Inference, Memory, Drift | 2d |
| `api/routes/intelligence.py` | P0 | Low | Intelligence engines | 0.5d |
| `api/routes/memory.py` | P0 | Low | Memory | 0.5d |
| `api/routes/research.py` | P2 | Low | Research assistant | 0.5d |
| `api/routes/reflection.py` | P1 | Low | Reflection engine | 0.5d |
| 5x Frontend components | P0-P2 | Low-High | API, Recharts | 1-2d each |

### 4.2 Modified Modules

| Module | Change | Complexity | Risk |
|--------|--------|------------|------|
| `core/pipeline/feature_pipeline.py` | Add `export_snapshot()` | Low | Low |
| `models/prediction_log.py` | Add nullable columns | Low | Low |
| `core/config.py` | Add AI config | Low | Low |
| `api/main.py` | Add AI module init | Low | Low |
| `core/database.py` | Add DuckDB factory | Low | Low |
| `frontend/src/App.js` | Add new tabs | Medium | Low |
| `frontend/src/api/index.js` | Fix imports + new clients | Medium | Low |
| `docker-compose.yml` | Add Ollama service | Low | Low |

### 4.3 Dependency Graph

```
Sprint 1 (Foundation):
  chromadb_manager.py  ←  embeddings.py
       ↓
  retrieval.py ──────────────┐
  inference.py ──────────────┤
  prompts/     ──────────────┤
       ↓                     │
  orchestration.py ──────────┤
       ↓                     │
  trade_memory/journal.py    │
  explainability/engine.py   │
  market_regime/engine.py    │
       ↓                     │
  API: intelligence.py, memory.py

Sprint 2 (Intelligence):
  trade_analysis/engine.py   ← journal + explainability
  portfolio_analysis/engine.py
  Frontend: RegimeDashboard, TradeExplanation

Sprint 3 (Advanced):
  reflection_engine/engine.py   ← all engines
  research_assistant/engine.py  ← memory + inference
  API: reflection.py, research.py
  Frontend: PortfolioIntelligence, SemanticSearch, ResearchDashboard
```

---

## 5. Risk Assessment

### 5.1 Risk Matrix

| # | Risk | Probability | Impact | Severity | Mitigation |
|---|------|-------------|--------|----------|------------|
| R1 | Ollama not runnable on local hardware | Med | High | **HIGH** | Document HW requirements; cloud LLM fallback |
| R2 | ChromaDB crash/corruption | Low | High | **MED** | DuckDB backups; ChromaDB persistence settings |
| R3 | LLM hallucination in trade analysis | Med | Med | **MED** | Structured prompts; confidence gating; human-in-loop |
| R4 | Embedding blocks trading cycle | Med | Med | **MED** | Async queue; 2s timeout |
| R5 | Schema drift between DuckDB and predictions | Med | Med | **MED** | Schema versioning; feature set hash in metadata |
| R6 | Irrelevant semantic retrieval | Med | Low | **LOW** | Metadata filtering; similarity threshold |
| R7 | ChromaDB volume explosion | Low | Low | **LOW** | 10K doc limit; monthly cleanup |
| R8 | Broken frontend Monitoring imports | High | Med | **MED** | Fix in Sprint 0 |
| R9 | Multiple AI queries OOM | Med | High | **HIGH** | 1 concurrent LLM; 10s timeout; request queue |
| R10 | Prompt injection via symbol names | Low | Med | **LOW** | Input sanitization; parameterized prompts |

### 5.2 Backward Compatibility

| Change | Risk | Safe Fallback |
|--------|------|---------------|
| New columns on `PredictionLog` | Old code queries without new columns | Nullable defaults |
| DuckDB analytical queries | Requires DuckDB installed | Graceful degradation to SQLite |
| Ollama dependency | AI module fails if Ollama offline | AI endpoints return 503 |
| ChromaDB on filesystem | Data loss on unmount | Docker volume persistence |

---

## 6. Technical Recommendations

### R1. Layered Intelligence Architecture

```
backend/
├── intelligence/    # Business logic (models, engines)
├── memory/          # Storage abstraction (ChromaDB, DuckDB)
├── ai/              # AI layer (LLM, prompts, orchestration)
└── api/routes/      # Presentation layer
```

### R2. Prompt Template Architecture

Store prompts as YAML in `backend/ai/prompts/`:

```yaml
# prompts/regime_analysis.yaml
system: |
  You are a market analysis AI. Analyze market data
  and classify the current regime.
  
  Market data: {market_data}
  
  Respond with JSON:
  {"regime": "...", "confidence": 0.0-1.0, "reasoning": "..."}
temperature: 0.2
max_tokens: 512
```

### R3. Async-First AI Layer

```python
async def generate_with_timeout(self, prompt, timeout=10.0):
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(self._thread_pool, self._generate_sync, prompt),
        timeout=timeout
    )
```

### R4. Circuit Breaker for AI

Apply existing `CircuitBreaker` pattern:
```python
ai_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=60, name="AIInference")
```

### R5. DuckDB for Live Analytics

Add DuckDB to live backend. Critical for analytical queries and SHAP storage.

### R6. Feature Snapshot at Prediction Time

Modify `StockAnalyzer.analyze()` to persist feature values to DuckDB.

### R7. Ollama as Docker Service

Add to `docker-compose.yml` with GPU passthrough.

### R8. Thread Pool for AI

Use `ThreadPoolExecutor(max_workers=1)` — multiple concurrent LLM requests on CPU will OOM.

### R9. Graceful Degradation

All AI endpoints must work when Ollama is offline (503), ChromaDB is offline (partial results), DuckDB is offline (SQLite fallback).

---

## 7. Migration Considerations

### 7.1 Database Migration

Phase 1 is fully additive:
1. **SQLite**: Nullable columns on `prediction_logs`
2. **DuckDB**: New `analytics.duckdb` — no migration
3. **ChromaDB**: Fresh collections — no migration

### 7.2 Deployment Sequence

```
Step 1: Infrastructure (Ollama, ChromaDB volume)
Step 2: Backend AI layer (memory/, ai/)
Step 3: Intelligence modules (regime, trade, explainability, trade_memory)
Step 4: API routes + frontend API client fix
Step 5: Advanced intelligence (portfolio, reflection, research)
Step 6: Frontend dashboards
```

### 7.3 Rollback Strategy

| Component | Rollback |
|-----------|----------|
| ChromaDB | Delete directory + remove memory/ package |
| Ollama | Remove from docker-compose |
| DuckDB | Delete analytics.duckdb |
| New API routes | Remove route files |
| Frontend | Revert App.js |

### 7.4 Feature Flags

```python
ai_copilot_enabled: bool = False
chromadb_path: str = "data/chromadb"
ollama_base_url: str = "http://localhost:11434"
feature_snapshot_enabled: bool = False
```

---

## 8. Proposed Refactoring Areas

### 8.1 Immediate (Sprint 0)

| Refactoring | File | Effort |
|-------------|------|--------|
| Fix broken monitoringApi imports | `frontend/src/api/index.js` | 15min |
| Fix broken monitoringApi references | `frontend/src/components/Monitoring.jsx` | 15min |

### 8.2 Short-term (During Phase 1)

| Refactoring | From | To | Effort |
|-------------|------|----|--------|
| Extract DuckDB manager from backtesting | `backtesting/data_pipeline/duckdb_manager.py` | `backend/core/analytics_db.py` | 0.5d |
| Add feature snapshot method | `backend/core/pipeline/feature_pipeline.py` | Same file | 0.25d |
| Add DuckDB factory | `backend/core/database.py` | Same file | 0.25d |
| Add nullable columns | `backend/models/prediction_log.py` | Same file | 0.25d |
| Extract prompt templates to YAML | `backend/ai/prompts/` (new) | New directory | 0.5d |

### 8.3 Medium-term (Post Phase 1)

| Refactoring | Reason | Priority |
|-------------|--------|----------|
| React state management (Context + hooks) | App.js won't scale | Medium |
| Alembic for schema migrations | Schema versioning needed | Medium |
| Standardized API response format | AI needs consistent envelopes | Low |

---

## 9. Implementation Readiness Score

### 9.1 Readiness by Dimension

| Dimension | Score (1-10) |
|-----------|-------------|
| Codebase modularity | 8/10 |
| ML pipeline maturity | 8/10 |
| Data infrastructure | 3/10 |
| AI/LLM readiness | 1/10 |
| API extensibility | 7/10 |
| Frontend extensibility | 5/10 |
| Monitoring/observability | 4/10 |
| Infrastructure | 5/10 |
| Testing coverage | 3/10 |
| **Overall** | **5.8/10** |

### 9.2 Critical Path Items

1. **ChromaDB integration** (foundation for all memory features)
2. **Ollama setup** (foundation for all AI features)
3. **Feature snapshot export** (required for SHAP explainability)
4. **DuckDB analytics** (required for feature storage)
5. **Fix frontend monitoring API** (required before AI dashboard work)

---

## Appendix A: File Change Summary

### New Files (~25-30)

```
backend/memory/
├── chromadb_manager.py, embeddings.py, retrieval.py
backend/ai/
├── inference.py, orchestration.py
├── prompts/{regime_analysis,trade_explanation,portfolio_risk,research_assistant,reflection}.yaml
backend/intelligence/
├── market_regime/engine.py
├── trade_analysis/engine.py
├── portfolio_analysis/engine.py
├── reflection_engine/engine.py
├── explainability/engine.py
├── trade_memory/journal.py
└── research_assistant/engine.py
backend/api/routes/{intelligence,memory,research,reflection}.py
backend/core/analytics_db.py
frontend/src/components/{RegimeDashboard,PortfolioIntelligence,TradeExplanation,SemanticSearch,ResearchDashboard}.jsx
```

### Modified Files (~10)

```
backend/core/pipeline/feature_pipeline.py     # +export_snapshot()
backend/core/database.py                      # +DuckDB factory
backend/core/config.py                        # +AI copilot settings
backend/models/prediction_log.py              # +nullable columns
backend/api/main.py                           # +AI module init
backend/services/ai/analyzer.py               # +feature snapshot call
frontend/src/App.js                           # +new tabs
frontend/src/api/index.js                     # +new API clients, fix broken imports
frontend/src/index.css                        # +new component styles
docker-compose.yml                            # +Ollama service
```

---

## Appendix B: Sprint Mapping

| Sprint | PRD Scope | Dependencies |
|--------|-----------|-------------|
| Sprint 1 | ChromaDB, Embeddings, Trade Memory, Semantic APIs | Foundation: `memory/`, `ai/`, `core/analytics_db.py`, fix frontend API |
| Sprint 2 | Market Regime, Explainability, SHAP, Regime Dashboards | Sprint 1 + feature snapshot + regime detection |
| Sprint 3 | Trade Intelligence, Explanation APIs, Similar Trade Retrieval | Sprint 1 + 2 |
| Sprint 4 | Portfolio Intelligence, Correlation, Exposure Dashboards | Sprint 1 + 3 |
| Sprint 5 | Research Assistant, Reflection Engine, AI Summarization | Sprint 1-4 |

---

*End of Impact Analysis*
