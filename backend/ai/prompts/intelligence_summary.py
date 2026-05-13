from ai.prompts.base import PromptTemplate


INTELLIGENCE_SUMMARY = PromptTemplate(
    name="intelligence_summary",
    version="1.0.0",
    description="Generate structured periodic intelligence summaries from reflection engine data",
    template="""You are an intelligence summarization engine for an AI-native trading copilot. Generate a structured periodic intelligence summary from the following reflection data.

Summary Period: $period
Analysis Types: $analysis_types

## Reflection Data

### Recurring Patterns
$recurring_patterns

### Strategy Degradation
$strategy_degradation

### Regime Mismatches
$regime_mismatches

### System Instability
$system_instability

### Investigation Recommendations
$investigation_recommendations

Generate a structured JSON output with the following sections:
1. "summary_type": The type of summary (strategy_degradation_report / volatility_failure_report / regime_instability_summary / comprehensive_periodic_summary)
2. "period": The analysis period
3. "executive_summary": 2-3 sentence high-level summary of the most important findings
4. "key_findings": Array of { "area": str, "finding": str, "severity": str (none/low/medium/high/critical), "confidence": float 0-1 }
5. "trends": Array of { "direction": str (improving/stable/deteriorating), "metric": str, "detail": str }
6. "actionable_insights": Array of { "priority": int, "insight": str, "suggested_action": str, "expected_impact": str }
7. "risk_flags": Array of str describing any critical risks identified
8. "generated_at": ISO timestamp

Keep the analysis concise, data-driven, and actionable. Focus on what changed since the last period.
""",
)
