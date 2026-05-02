# Backtesting Health Report Template

This template is used by `report_analyzer.py` to generate human-readable reports.

## Structure

1. **Executive Summary** - Overall verdict with ✅/❌ for each check
2. **Walk-Forward Validation** - Time split verification
3. **Lookahead Bias Check** - Future data leakage verification
4. **Trade Activity** - Whether trades actually happened
5. **Prediction Distribution** - What the model is predicting
6. **Simulator Signal Handling** - Whether all signals are used
7. **Overfitting Check** - Memorization vs learning
8. **Per-Stock Breakdown** - Results by stock
9. **Recommended Fixes** - Actionable next steps
10. **Summary for Non-Technical Stakeholders** - Plain English conclusion

## Non-Technical Explanations

### Walk-Forward Validation
"Like studying past papers for an exam, never seeing the actual questions until test day."

### Lookahead Bias
"Like a weather forecaster who can't see tomorrow's newspaper today."

### Zero Trades
"Like testing a car that never leaves the garage."

### High Accuracy, Zero Trades
"Like predicting 'normal weather' every day — you'll be right 95% of the time, but you're not a weather forecaster."

### Overfitting
"Like memorizing that 'C' is always the answer — you get 25% right by luck, but haven't learned anything."
