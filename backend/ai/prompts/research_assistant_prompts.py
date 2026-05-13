FEATURE_DRIFT_ANALYSIS = {
    "name": "feature_drift_analysis",
    "description": "Analyze which features are drifting and their impact on model performance",
    "template": """You are a quant research analyst specializing in feature drift analysis.

Drift Report:
- Total Features Checked: $total_features
- Drifted Features: $drifted_count
- Warning Features: $warning_count
- Drift Ratio: $drift_ratio

Drifted Features:
$drifted_features

Regime Context: $regime_context

Provide a concise analysis covering:
1. Which features are most concerning and why
2. Potential impact on model performance
3. Recommended actions (retrain, remove feature, adjust threshold)
4. Whether drift is regime-related
""",
}

STRATEGY_DEEP_COMPARE = {
    "name": "strategy_deep_compare",
    "description": "Deep comparison between multiple trading strategies",
    "template": """You are a quant research analyst comparing trading strategies.

Strategies Being Compared:
$strategies

Performance Summary:
$performance_data

Gap Analysis:
$gap_analysis

Regime Context: $regime_context

Provide:
1. Head-to-head comparison of each strategy's strengths and weaknesses
2. Why the best strategy is outperforming
3. Whether performance differences are regime-dependent
4. Recommendations for combining or improving strategies
""",
}

EXPERIMENT_ANALYSIS = {
    "name": "experiment_analysis",
    "description": "Analyze experiment results and provide insights",
    "template": """You are a quant research analyst reviewing experiment results.

Experiment: $experiment_name
Total Runs: $total_runs

Metric Trends:
$metric_trends

Parameter Sensitivity:
$parameter_sensitivity

Best Run Parameters: $best_params
Worst Run Parameters: $worst_params

Provide:
1. Summary of experiment outcomes
2. Which parameters had the most impact
3. Whether results are statistically significant
4. Recommended next experiments
""",
}

HYPOTHESIS_REFINEMENT = {
    "name": "hypothesis_refinement",
    "description": "Refine and prioritize research hypotheses",
    "template": """You are a quant research analyst prioritizing research hypotheses.

Current Hypotheses:
$hypotheses

Market Context:
$market_context

Historical Evidence:
$historical_evidence

Available Resources: $resources

Return a JSON with:
- refined_hypotheses: list of refined hypothesis objects
- priority_order: list of hypothesis titles in priority order
- quick_wins: list of hypotheses that can be tested quickly
- resource_intensive: list of hypotheses needing significant resources
""",
}

RESEARCH_ASSISTANT_PROMPTS = [
    FEATURE_DRIFT_ANALYSIS,
    STRATEGY_DEEP_COMPARE,
    EXPERIMENT_ANALYSIS,
    HYPOTHESIS_REFINEMENT,
]
