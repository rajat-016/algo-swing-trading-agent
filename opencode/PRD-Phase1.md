# Product Requirements Document (PRD)

# AI-Native Trading Copilot

## Project

Enhancement of: urlalgo-swing-trading-agent GitHub Repository[https://github.com/rajat-016/algo-swing-trading-agent](https://github.com/rajat-016/algo-swing-trading-agent)

---

# 1. Executive Summary

The current algo-swing-trading-agent project has evolved from a rule-based trading system toward an ML-first swing trading architecture with modular feature pipelines, labeling systems, orchestration, ETF selection, and walk-forward backtesting.

The next strategic evolution is to transform the system into an AI-native trading intelligence platform.

Phase 1 focuses on building an AI-Native Trading Copilot — an intelligent analytical layer that assists the trader by:

* Understanding market regimes
* Explaining trade decisions
* Analyzing portfolio risks
* Remembering historical trade behavior
* Detecting model degradation
* Assisting quant research
* Generating actionable insights
* Acting as a trading intelligence assistant

This phase does NOT introduce autonomous trading.

Instead, it introduces:

* Intelligence
* Memory
* Explainability
* Reflection
* Context-aware AI reasoning

The output of this phase becomes the foundation for:

1. Autonomous Trading Agent Framework
2. Personal AI Hedge Fund Infrastructure

---

# 2. Vision

Build an AI-native trading intelligence layer capable of:

* Understanding the market
* Understanding portfolio behavior
* Understanding historical trade patterns
* Understanding strategy performance
* Explaining decisions
* Providing contextual recommendations
* Learning from historical memory

The system should behave like:

> A quant research analyst + portfolio analyst + market strategist working alongside the trader.

---

# 3. Product Goals

## Primary Goals

### G1. Create Market Intelligence Layer

Enable the system to reason about market conditions and trading outcomes.

### G2. Introduce Semantic Memory

Allow the system to remember and retrieve historical observations, trade reasoning, and market patterns.

### G3. Enable Explainable Trading

Provide transparent explanations behind predictions, trades, and portfolio decisions.

### G4. Improve Decision Support

Assist the trader with contextual market intelligence and portfolio insights.

### G5. Build AI Infrastructure Foundation

Prepare the architecture for future agentic and autonomous trading systems.

---

# 4. Non-Goals

The following are explicitly OUT OF SCOPE for Phase 1:

* Fully autonomous trading
* Self-executing AI agents
* Reinforcement learning trading
* Portfolio auto-allocation
* AI-generated trade signals
* LLM-based market prediction
* Multi-agent orchestration
* Self-modifying strategies
* AI-generated order execution

Phase 1 is an intelligence augmentation layer only.

---

# 5. Current System Assessment

## Existing Strengths

The current project already includes:

* ML-first architecture
* Modular feature engineering pipeline
* Label generation pipeline
* Walk-forward backtesting
* Backtesting separation from production
* ETF selection architecture
* Production/live alignment thinking
* Curated feature set
* Orchestration workflows

These components provide a strong foundation for introducing AI-native intelligence.

---

# 6. Proposed Architecture Evolution

## Current Architecture

```text
Market Data
    ↓
Feature Engineering
    ↓
Model Prediction
    ↓
Signal Generation
    ↓
Execution
```

---

## Phase 1 Enhanced Architecture

```text
Market Data
    ↓
Feature Engineering
    ↓
ML Prediction Engine
    ↓
Trade Intelligence Layer
    ↓
AI Copilot Layer
    ↓
Portfolio Intelligence
    ↓
Trader Decision Support
```

---

# 7. High-Level Phase 1 Components

| Component                     | Purpose                                          |
| ----------------------------- | ------------------------------------------------ |
| Market Regime Engine          | Detect current market conditions                 |
| Trade Intelligence Engine     | Explain trade decisions and failures             |
| Portfolio Intelligence Engine | Analyze exposure and portfolio risk              |
| AI Trade Journal              | Store and analyze trade history                  |
| Market Memory System          | Semantic retrieval of historical market behavior |
| Explainability Engine         | Generate feature-level explanations              |
| Quant Research Assistant      | AI-assisted experimentation and analysis         |
| Reflection Engine             | Detect recurring patterns and degradation        |

---

# 8. Core System Modules

# 8.1 Market Regime Engine

## Objective

Enable the system to identify and classify market environments.

---

## Functional Requirements

### Regime Detection

The system must classify:

* Bull Trend
* Bear Trend
* Sideways Market
* High Volatility
* Low Volatility
* Event-Driven Market
* Mean Reversion Regime
* Breakout Regime

---

### Regime Confidence

Each regime output must include:

* regime type
* confidence score
* regime stability
* volatility context
* suggested behavior

---

## Example Output

```json
{
  "regime": "high_volatility_trend",
  "confidence": 0.84,
  "risk_level": "high",
  "recommended_behavior": [
    "reduce position sizing",
    "avoid aggressive breakouts"
  ]
}
```

---

## Inputs

* Market breadth
* VIX
* Sector rotation
* Volatility indicators
* Trend strength
* Volume expansion
* Macro indicators

---

## Success Metrics

| Metric                         | Target     |
| ------------------------------ | ---------- |
| Regime classification accuracy | >75%       |
| False regime transitions       | <15%       |
| Regime update latency          | <5 seconds |

---

# 8.2 Trade Intelligence Engine

## Objective

Explain why trades are generated and why trades succeed or fail.

---

## Functional Requirements

### Trade Explanation

System must explain:

* why trade was taken
* strongest supporting features
* regime context
* confidence score
* risk factors

---

### Trade Failure Analysis

System must analyze:

* stop-loss causes
* regime mismatch
* volatility expansion
* weak feature confirmation
* execution inefficiencies

---

## Example Query

```text
Why did the RELIANCE breakout fail yesterday?
```

---

## Example Output

```text
The trade failed due to rapid volatility expansion after RBI commentary.
Momentum confirmation weakened during the final breakout candle.
Historical win rate for similar setups in high-volatility environments is 42%.
```

---

## Inputs

* Feature snapshots
* Prediction outputs
* SHAP values
* Trade metadata
* Regime data
* Historical similar trades

---

## Success Metrics

| Metric                           | Target     |
| -------------------------------- | ---------- |
| Explanation generation latency   | <3 seconds |
| Trade explanation coverage       | 100%       |
| Similar trade retrieval accuracy | >80%       |

---

# 8.3 Portfolio Intelligence Engine

## Objective

Analyze portfolio exposure, concentration, and systemic risk.

---

## Functional Requirements

### Exposure Analysis

Analyze:

* sector concentration
* correlation clusters
* volatility exposure
* directional bias
* capital concentration

---

### Portfolio Risk Insights

System must identify:

* overexposure risks
* correlated positions
* excessive leverage
* portfolio instability

---

## Example Queries

```text
What is the biggest portfolio risk right now?
```

```text
Which holdings are highly correlated?
```

---

## Visual Outputs

* Correlation heatmaps
* Exposure summaries
* Portfolio volatility dashboards
* Sector concentration reports

---

## Inputs

* Current positions
* Sector data
* Historical returns
* Correlation matrices
* Portfolio allocations

---

## Success Metrics

| Metric                         | Target     |
| ------------------------------ | ---------- |
| Correlation detection accuracy | >85%       |
| Exposure refresh frequency     | Real-time  |
| Risk alert generation          | <2 seconds |

---

# 8.4 AI Trade Journal

## Objective

Create persistent trade memory for future intelligence and reflection.

---

## Functional Requirements

Each trade entry must store:

* trade ID
* ticker
* timestamp
* market regime
* feature snapshot
* confidence score
* trade reasoning
* portfolio state
* outcome
* post-trade analysis

---

## Example Trade Memory

```json
{
  "trade_id": "T-0193",
  "ticker": "RELIANCE",
  "market_regime": "bull_trend",
  "confidence": 0.81,
  "reasoning": "Breakout supported by sector momentum and volatility compression",
  "outcome": "stop_loss_hit"
}
```

---

## AI Capabilities

System must answer:

* Which setups work best?
* Which regimes cause failures?
* Which features degrade performance?
* Which trade types perform poorly?

---

## Success Metrics

| Metric                          | Target |
| ------------------------------- | ------ |
| Trade logging coverage          | 100%   |
| Trade memory retrieval accuracy | >85%   |
| Trade context completeness      | >90%   |

---

# 8.5 Market Memory System

## Objective

Introduce semantic memory architecture using vector storage.

---

## Proposed Technology

| Layer           | Technology       |
| --------------- | ---------------- |
| Structured Data | DuckDB           |
| Semantic Memory | ChromaDB         |
| Embeddings      | nomic-embed-text |
| LLM Runtime     | Ollama           |

---

## Memory Categories

### Trade Memory

Store:

* trade reasoning
* trade failures
* trade observations

---

### Market Memory

Store:

* regime transitions
* volatility events
* market anomalies

---

### Research Memory

Store:

* feature observations
* experiment findings
* strategy insights

---

## Semantic Query Examples

```text
Find similar failed breakout trades during volatile markets
```

```text
Retrieve market conditions similar to current environment
```

---

## Success Metrics

| Metric                       | Target     |
| ---------------------------- | ---------- |
| Semantic retrieval precision | >80%       |
| Embedding generation latency | <2 seconds |
| Query response latency       | <4 seconds |

---

# 8.6 Explainability Engine

## Objective

Provide transparent explanations for predictions and trade decisions.

---

## Functional Requirements

### Feature Attribution

Show:

* top positive features
* top negative features
* confidence drivers
* feature contributions

---

### Model Explainability

Integrate:

* SHAP
* permutation importance
* confidence scoring

---

## Example Output

```json
{
  "prediction": "BUY",
  "confidence": 0.81,
  "top_features": [
    "sector_momentum",
    "relative_strength",
    "volatility_compression"
  ]
}
```

---

## Success Metrics

| Metric                          | Target     |
| ------------------------------- | ---------- |
| Explainability coverage         | 100%       |
| Explanation generation latency  | <3 seconds |
| Feature attribution consistency | >85%       |

---

# 8.7 Quant Research Assistant

## Objective

Enable AI-assisted quantitative research and experimentation.

---

## Functional Requirements

### Research Assistance

AI must assist with:

* feature analysis
* experiment summarization
* strategy comparison
* drift detection
* hypothesis generation

---

## Example Queries

```text
Which features became unstable over the last 3 months?
```

```text
Which strategies degrade during volatile regimes?
```

---

## Success Metrics

| Metric                            | Target     |
| --------------------------------- | ---------- |
| Research query response time      | <5 seconds |
| Feature drift detection accuracy  | >80%       |
| Experiment summarization coverage | 100%       |

---

# 8.8 Reflection Engine

## Objective

Allow the system to learn from historical failures and behavioral patterns.

---

## Functional Requirements

### Reflection Capabilities

System must:

* identify recurring failures
* detect strategy degradation
* detect feature instability
* identify regime mismatches
* recommend investigation areas

---

## Example Reflection

```text
Breakout strategies show 28% degradation during earnings-heavy weeks.
Recommend reducing breakout allocation during event-heavy periods.
```

---

## Success Metrics

| Metric                        | Target     |
| ----------------------------- | ---------- |
| Reflection accuracy           | >75%       |
| Pattern detection coverage    | >80%       |
| Reflection generation latency | <5 seconds |

---

# 9. Proposed Technical Architecture

# 9.1 High-Level Architecture

```text
                         ┌──────────────────┐
                         │     Ollama       │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │                           │
                    ▼                           ▼

          ┌────────────────┐        ┌──────────────────┐
          │     DuckDB     │        │     ChromaDB     │
          └────────────────┘        └──────────────────┘

          Structured Data           Semantic Memory
          - Features                - Trade reasoning
          - Backtests               - Market memory
          - Predictions             - Reflections
          - Metrics                 - Research notes
```

---

# 9.2 Proposed Directory Structure

```text
backend/
│
├── intelligence/
│   ├── market_regime/
│   ├── trade_analysis/
│   ├── portfolio_analysis/
│   ├── reflection_engine/
│   ├── explainability/
│   ├── trade_memory/
│   └── research_assistant/
│
├── memory/
│   ├── chromadb/
│   ├── embeddings/
│   └── retrieval/
│
├── ai/
│   ├── prompts/
│   ├── llm/
│   ├── inference/
│   └── orchestration/
│
└── monitoring/
```

---

# 10. Technology Stack

| Layer                   | Technology           |
| ----------------------- | -------------------- |
| LLM Runtime             | Ollama               |
| Primary Model           | Qwen2.5              |
| Embeddings              | nomic-embed-text     |
| Vector Database         | ChromaDB             |
| Structured Analytics    | DuckDB               |
| Backend                 | FastAPI              |
| Experiment Tracking     | MLflow               |
| Explainability          | SHAP                 |
| Agent Graph Preparation | LangGraph            |
| Monitoring              | Grafana + Prometheus |

---

# 11. Data Architecture

# 11.1 Structured Storage (DuckDB)

## Stores

* OHLCV
* features
* predictions
* backtests
* metrics
* portfolio states
* signals
* performance data

---

# 11.2 Semantic Storage (ChromaDB)

## Stores

* trade reasoning
* market observations
* AI reflections
* experiment findings
* portfolio insights
* strategy observations

---

# 12. API Requirements

# 12.1 Intelligence APIs

| Endpoint             | Purpose               |
| -------------------- | --------------------- |
| /regime/current      | Current market regime |
| /trade/explain       | Explain trade         |
| /portfolio/risk      | Portfolio analysis    |
| /memory/search       | Semantic search       |
| /research/query      | Research assistant    |
| /reflection/generate | Generate reflections  |

---

# 13. UI/UX Requirements

## Core Dashboards

### Market Intelligence Dashboard

Display:

* current regime
* regime confidence
* market volatility
* breadth indicators

---

### Portfolio Intelligence Dashboard

Display:

* exposure heatmap
* correlation matrix
* concentration risk
* volatility exposure

---

### Trade Explanation Dashboard

Display:

* trade reasoning
* top features
* confidence score
* similar historical trades

---

### Research Dashboard

Display:

* feature drift
* model stability
* experiment comparisons
* strategy degradation

---

# 14. Monitoring Requirements

## System Monitoring

Track:

* inference latency
* memory retrieval latency
* embedding generation latency
* API failures
* model drift
* feature drift

---

# 15. Security & Risk Considerations

## Requirements

* No autonomous execution authority
* Human approval required for decisions
* Model confidence thresholds
* Memory integrity validation
* Semantic retrieval safeguards
* Audit logging for AI-generated insights

---

# 16. Performance Requirements

| Component             | SLA        |
| --------------------- | ---------- |
| Trade explanation     | <3 seconds |
| Regime detection      | <5 seconds |
| Semantic retrieval    | <4 seconds |
| Portfolio analysis    | <3 seconds |
| Reflection generation | <5 seconds |

---

# 17. Success Metrics

# Business Metrics

| Metric                          | Target         |
| ------------------------------- | -------------- |
| Reduction in unexplained trades | >90%           |
| Faster research iteration       | 2x improvement |
| Reduction in repeated failures  | >30%           |
| Increased trader confidence     | High           |

---

# Technical Metrics

| Metric                      | Target     |
| --------------------------- | ---------- |
| AI response latency         | <5 seconds |
| Memory retrieval precision  | >80%       |
| Explainability coverage     | 100%       |
| Drift detection reliability | >80%       |

---

# 18. Risks

| Risk                      | Mitigation                             |
| ------------------------- | -------------------------------------- |
| Hallucinated AI reasoning | Structured prompts + validations       |
| Poor semantic retrieval   | Better embeddings + metadata filtering |
| Model latency             | Local inference optimization           |
| Excessive AI complexity   | Scope control                          |
| Data inconsistency        | Unified schema management              |

---

# 19. Future Evolution Alignment

Phase 1 directly enables:

---

## Phase 2 — Autonomous Trading Agent Framework

Future additions:

* agent orchestration
* inter-agent communication
* reflection loops
* autonomous coordination
* distributed intelligence

---

## Phase 3 — Personal AI Hedge Fund Infrastructure

Future additions:

* portfolio allocation engine
* institutional risk engine
* strategy marketplace
* model registry
* feature store
* self-improving research systems

---

# 20. Recommended Implementation Order

# Sprint 1

* ChromaDB integration
* Embedding pipeline
* Trade memory schema
* Semantic retrieval APIs

---

# Sprint 2

* Market regime engine
* Explainability engine
* SHAP integration
* Regime dashboards

---

# Sprint 3

* Trade intelligence engine
* Trade explanation APIs
* Similar trade retrieval

---

# Sprint 4

* Portfolio intelligence engine
* Correlation analysis
* Exposure dashboards

---

# Sprint 5

* Quant research assistant
* Reflection engine
* AI summarization workflows

---

# 21. Final Recommendation

The project should evolve gradually from:

```text
ML-based trading system
```

into:

```text
AI-native market intelligence platform
```

Phase 1 must prioritize:

* intelligence
* explainability
* memory
* reasoning
* reflection

instead of:

* autonomous execution
* excessive agents
* overly complex AI systems

The strongest long-term moat for this project will not be prediction accuracy.

It will be:

> accumulated market intelligence and contextual memory.
