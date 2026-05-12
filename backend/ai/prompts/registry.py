from loguru import logger
from typing import Optional
from ai.prompts.base import PromptTemplate


MARKET_REGIME = PromptTemplate(
    name="market_regime",
    description="Classify current market regime from technical indicators",
    template="""You are a market regime analyst. Based on the following market data, classify the current regime.

Market Data:
- Trend Status: $trend_status
- Volatility (ATR%): $volatility
- Volume Trend: $volume_trend
- Breadth: $breadth
- VIX Level: $vix_level
- Sector Rotation: $sector_rotation

Return a JSON response with:
- regime: one of [bull_trend, bear_trend, sideways, high_volatility, low_volatility, event_driven, mean_reversion, breakout]
- confidence: float 0-1
- stability: str [stable, moderate, unstable]
- risk_level: str [low, medium, high]
- suggested_behavior: list[str]
""",
)

TRADE_EXPLANATION = PromptTemplate(
    name="trade_explanation",
    description="Explain why a trade was taken and its outcome",
    template="""You are a trade intelligence analyst. Explain the following trade decision.

Trade Details:
- Symbol: $symbol
- Entry Price: $entry_price
- Exit Price: $exit_price
- Direction: $direction
- Confidence: $confidence
- Market Regime: $regime
- Top Features: $top_features
- Feature Values: $feature_values
- Outcome: $outcome
- P&L: $pnl

Provide a concise explanation covering:
1. Why the trade was taken
2. Strongest supporting factors
3. Why it succeeded or failed
4. Key lessons for future trades
""",
)

PORTFOLIO_RISK = PromptTemplate(
    name="portfolio_risk",
    description="Analyze portfolio exposure and risk",
    template="""You are a portfolio risk analyst. Analyze the current portfolio.

Portfolio State:
$portfolio_data

Risk Metrics:
- Correlation Clusters: $correlation_clusters
- Sector Concentrations: $sector_exposure
- Volatility Exposure: $volatility_exposure
- Directional Bias: $directional_bias
- Max Drawdown: $max_drawdown

Identify:
1. Biggest portfolio risks
2. Overexposure issues
3. Correlated positions
4. Recommendations
""",
)

SEMANTIC_SEARCH = PromptTemplate(
    name="semantic_search",
    description="Generate search query for semantic memory retrieval",
    template="""Given the user's question, generate a concise search query for retrieving relevant trade and market memories.

User Question: $question

Return a JSON:
- search_query: str (concise search phrase)
- memory_types: list[str] (relevant memory categories)
- filters: dict (optional metadata filters)
""",
)

REFLECTION = PromptTemplate(
    name="reflection",
    description="Generate reflection on trading patterns and performance",
    template="""You are a trading reflection engine. Analyze the following performance data and identify patterns.

Period: $period
Total Trades: $total_trades
Win Rate: $win_rate
Profit Factor: $profit_factor
Avg Win: $avg_win
Avg Loss: $avg_loss
Max Drawdown: $max_drawdown
Regime Breakdown: $regime_breakdown
Feature Stability: $feature_stability
Failure Patterns: $failure_patterns

Generate a reflection covering:
1. Recurring failure patterns
2. Strategy degradation signals
3. Feature instability
4. Regime mismatches
5. Recommended investigation areas
""",
)

POST_TRADE_REFLECTION = PromptTemplate(
    name="post_trade_reflection",
    description="Generate structured per-trade post-trade reflection",
    template="""You are a post-trade reflection analyst. Review the following completed trade and produce a structured JSON reflection.

Trade Details:
- Symbol: $symbol
- Trade ID: $trade_id
- Entry Price: $entry_price
- Exit Price: $exit_price
- Direction: $direction
- Confidence: $confidence
- Market Regime: $regime
- Outcome: $outcome
- P&L: $pnl
- P&L%: $pnl_pct
- Exit Reason: $exit_reason
- Feature Snapshot: $feature_snapshot
- Portfolio State: $portfolio_state

Evaluate the trade across these dimensions and return a JSON object with the following structure:
{
    "setup_quality": "Assessment of entry setup technical soundness. Was the risk/reward favorable? Were entry conditions met? Rate as excellent/good/fair/poor with brief explanation.",
    "execution_quality": "Assessment of execution. Was the entry price good? Was sizing appropriate? Was the exit timely? Rate as excellent/good/fair/poor with brief explanation.",
    "regime_alignment": "How well the trade aligned with the prevailing market regime. Did the regime support this direction? Rate as aligned/neutral/misaligned with brief explanation.",
    "volatility_context": "How volatility was factored in. Was volatility favorable for this trade? Were stops appropriately placed? Rate as well-handled/adequate/poorly-handled with brief explanation.",
    "feature_confirmation_quality": "Whether the ML model features confirmed the trade direction. Did the top features support the decision? Were there contradictory signals? Rate as strong/mixed/weak with brief explanation.",
    "overall_assessment": "One-paragraph summary of what happened, why, and what could be improved.",
    "lessons_learned": ["List of 2-4 actionable lessons for future trading"]
}

Be honest and constructive. Focus on actionable insights.
""",
)

RESEARCH_QUERY = PromptTemplate(
    name="research_query",
    description="Answer quant research questions about strategy performance",
    template="""You are a quant research assistant. Answer the following research question using the provided data.

Research Question: $question

Available Data:
$context_data

Provide:
1. Direct answer with supporting evidence
2. Statistical confidence
3. Related insights
4. Suggested follow-up experiments
""",
)


class PromptRegistry:
    def __init__(self):
        self._prompts: dict[str, PromptTemplate] = {}

    def register(self, prompt: PromptTemplate):
        self._prompts[prompt.name] = prompt
        logger.debug(f"Registered prompt: {prompt.name} v{prompt.version}")

    def get(self, name: str) -> Optional[PromptTemplate]:
        return self._prompts.get(name)

    def list_prompts(self) -> list[dict]:
        return [p.to_dict() for p in self._prompts.values()]

    def render(self, name: str, **kwargs) -> str:
        prompt = self.get(name)
        if prompt is None:
            raise KeyError(f"Prompt not found: {name}")
        return prompt.render(**kwargs)


registry = PromptRegistry()
registry.register(MARKET_REGIME)
registry.register(TRADE_EXPLANATION)
registry.register(PORTFOLIO_RISK)
registry.register(SEMANTIC_SEARCH)
registry.register(REFLECTION)
registry.register(POST_TRADE_REFLECTION)
registry.register(RESEARCH_QUERY)
