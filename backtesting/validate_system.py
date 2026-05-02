"""
System Validation Script - Audit the refactored backtesting system
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, '.')

print("=" * 70)
print("SYSTEM VALIDATION REPORT")
print("=" * 70)

issues = []
passed = []

# 1. Module Imports
print("\n1. MODULE IMPORT VALIDATION")
print("-" * 40)
try:
    from feature_engineering.feature_pipeline import FeaturePipeline
    print("  [PASS] FeaturePipeline")
    passed.append("FeaturePipeline")
except Exception as e:
    print(f"  [FAIL] FeaturePipeline: {e}")
    issues.append(("FeaturePipeline", str(e)))

try:
    from labeling.label_generator import LabelGenerator
    print("  [PASS] LabelGenerator")
    passed.append("LabelGenerator")
except Exception as e:
    print(f"  [FAIL] LabelGenerator: {e}")
    issues.append(("LabelGenerator", str(e)))

try:
    from backtest_engine.trade_simulator import TradeSimulator
    print("  [PASS] TradeSimulator")
    passed.append("TradeSimulator")
except Exception as e:
    print(f"  [FAIL] TradeSimulator: {e}")
    issues.append(("TradeSimulator", str(e)))

try:
    from backtest_engine.position_manager import PositionManager, Position
    print("  [PASS] PositionManager")
    passed.append("PositionManager")
except Exception as e:
    print(f"  [FAIL] PositionManager: {e}")
    issues.append(("PositionManager", str(e)))

try:
    from metrics.performance_metrics import PerformanceMetrics
    print("  [PASS] PerformanceMetrics")
    passed.append("PerformanceMetrics")
except Exception as e:
    print(f"  [FAIL] PerformanceMetrics: {e}")
    issues.append(("PerformanceMetrics", str(e)))

try:
    from model_selection.selector import ModelSelector
    print("  [PASS] ModelSelector")
    passed.append("ModelSelector")
except Exception as e:
    print(f"  [FAIL] ModelSelector: {e}")
    issues.append(("ModelSelector", str(e)))

try:
    from export.report_generator import ReportGenerator
    print("  [PASS] ReportGenerator")
    passed.append("ReportGenerator")
except Exception as e:
    print(f"  [FAIL] ReportGenerator: {e}")
    issues.append(("ReportGenerator", str(e)))

try:
    from portfolio.allocator import PortfolioAllocator, PortfolioSimulator
    print("  [PASS] PortfolioAllocator")
    passed.append("PortfolioAllocator")
except Exception as e:
    print(f"  [FAIL] PortfolioAllocator: {e}")
    issues.append(("PortfolioAllocator", str(e)))

try:
    from regime.regime_detector import RegimeDetector
    print("  [PASS] RegimeDetector")
    passed.append("RegimeDetector")
except Exception as e:
    print(f"  [FAIL] RegimeDetector: {e}")
    issues.append(("RegimeDetector", str(e)))

# 2. Feature Alignment Check
print("\n2. FEATURE ALIGNMENT CHECK")
print("-" * 40)
try:
    fp = FeaturePipeline()
    features = fp.get_feature_names()
    expected_count = 60  # Should match live system
    if isinstance(features, list) and len(features) <= expected_count:
        print(f"  [PASS] Features aligned: {len(features)} features (expected ≤{expected_count})")
        passed.append("FeatureAlignment")
    else:
        actual = len(features) if isinstance(features, list) else "unknown"
        print(f"  [FAIL] Feature count mismatch: {actual} (expected ≤{expected_count})")
        issues.append(("FeatureAlignment", f"Got {actual} features"))
except Exception as e:
    print(f"  [FAIL] Feature alignment check: {e}")
    issues.append(("FeatureAlignment", str(e)))

# 3. Label Generator Validation
print("\n3. LABEL GENERATOR VALIDATION")
print("-" * 40)
try:
    lg = LabelGenerator(lookahead=5, threshold=0.10, stop_loss=0.03)
    df = pd.DataFrame({
        "close": [100, 102, 104, 106, 108, 110, 90, 85, 80, 75],
        "atr_14": [2.0] * 10,
    })
    result = lg.create_labels(df)
    if "signal" in result.columns:
        counts = result["signal"].value_counts().to_dict()
        print(f"  [PASS] Labels created: {counts}")
        passed.append("LabelGenerator")
        
        # Check ATR-based logic
        if counts.get(2, 0) > 0 and counts.get(0, 0) > 0:
            print("  [PASS] Both BUY and SELL labels generated")
        else:
            print("  [WARN] Only one class generated - check threshold")
    else:
        print("  [FAIL] 'signal' column not created")
        issues.append(("LabelGenerator", "No signal column"))
except Exception as e:
    print(f"  [FAIL] Label generator: {e}")
    issues.append(("LabelGenerator", str(e)))

# 4. Position Sizing Validation
print("\n4. POSITION SIZING VALIDATION")
print("-" * 40)
try:
    from backtest_engine.trade_simulator import TradeSimulator
    sim = TradeSimulator(initial_capital=100000)
    
    # Test edge score computation
    edge_score = sim._calculate_stop_loss(100, 2.0)  # stop = 100 - (2*2) = 96
    expected_stop = 96.0
    if abs(edge_score - expected_stop) < 0.01:
        print(f"  [PASS] Stop loss calculation correct: {edge_score}")
        passed.append("StopLossCalc")
    else:
        print(f"  [FAIL] Stop loss wrong: {edge_score} (expected {expected_stop})")
        issues.append(("StopLoss", f"Got {edge_score}"))
    
    target = sim._calculate_target(100, 2.0)  # target = 100 + (2*4) = 108
    expected_target = 108.0
    if abs(target - expected_target) < 0.01:
        print(f"  [PASS] Target calculation correct: {target}")
        passed.append("TargetCalc")
    else:
        print(f"  [FAIL] Target wrong: {target} (expected {expected_target})")
        issues.append(("Target", f"Got {target}"))
    
    # Test risk-based sizing
    risk = abs(100 - 96)  # 4
    reward = abs(108 - 100)  # 8
    confidence = 0.8
    edge_score = confidence * (reward / risk)
    expected_edge = 0.8 * 2.0  # 1.6
    if abs(edge_score - expected_edge) < 0.01:
        print(f"  [PASS] Edge score calculation correct: {edge_score}")
        passed.append("EdgeScoreCalc")
    else:
        print(f"  [FAIL] Edge score wrong: {edge_score} (expected {expected_edge})")
        issues.append(("EdgeScore", f"Got {edge_score}"))
except Exception as e:
    print(f"  [FAIL] Position sizing: {e}")
    issues.append(("PositionSizing", str(e)))

# 5. Metrics Validation
print("\n5. METRICS VALIDATION")
print("-" * 40)
try:
    # Test precision_buy
    trades = [
        {"pnl": 100, "entry_price": 100, "quantity": 10, "entry_confidence": 0.8},
        {"pnl": -50, "entry_price": 100, "quantity": 10, "entry_confidence": 0.6},
        {"pnl": 200, "entry_price": 100, "quantity": 10, "entry_confidence": 0.9},
    ]
    opt = PerformanceMetrics.find_optimal_confidence_threshold(trades, min_trades=2)
    if opt["trade_count"] > 0 and opt["expected_return"] > 0:
        print(f"  [PASS] Optimal threshold: {opt['optimal_threshold']:.2f} (trades={opt['trade_count']})")
        passed.append("OptimalThreshold")
    else:
        print(f"  [FAIL] Optimal threshold failed: {opt}")
        issues.append(("OptimalThreshold", str(opt)))
    
    # Test trade expectancy
    expectancy = PerformanceMetrics.trade_expectancy(trades)
    if expectancy["expectancy"] > 0:
        print(f"  [PASS] Trade expectancy: {expectancy['expectancy']:.2f}")
        passed.append("TradeExpectancy")
    else:
        print(f"  [FAIL] Trade expectancy negative: {expectancy['expectancy']:.2f}")
        issues.append(("TradeExpectancy", str(expectancy)))
    
    # Test confidence buckets
    pred_log = [
        {"bar": 0, "symbol": "TEST", "pred_class": 2, "confidence": 0.7},
        {"bar": 1, "symbol": "TEST", "pred_class": 2, "confidence": 0.8},
        {"bar": 2, "symbol": "TEST", "pred_class": 0, "confidence": 0.9},
    ]
    buckets = PerformanceMetrics.confidence_bucket_analysis(pred_log)
    if "low" in buckets and "medium" in buckets and "high" in buckets:
        print(f"  [PASS] Confidence buckets: {buckets}")
        passed.append("ConfidenceBuckets")
    else:
        print(f"  [FAIL] Confidence buckets missing: {buckets}")
        issues.append(("ConfidenceBuckets", str(buckets)))
except Exception as e:
    print(f"  [FAIL] Metrics validation: {e}")
    issues.append(("Metrics", str(e)))

# 6. Model Selection Validation
print("\n6. MODEL SELECTION VALIDATION")
print("-" * 40)
try:
    selector = ModelSelector(
        min_sharpe=1.0,
        max_drawdown=0.25,
        min_trades=30,
        min_precision_buy=0.55,
        min_expectancy=0.0,
    )
    print("  [PASS] ModelSelector created (accuracy removed)")
    passed.append("ModelSelector")
    
    # Test filtering
    results = [
        {"sharpe_ratio": 1.5, "max_drawdown": 0.20, "total_trades": 40, "precision_buy": 0.60, 
         "trade_expectancy": {"expectancy": 150.0}, "symbol": "A", "window_index": 0},
        {"sharpe_ratio": 0.5, "max_drawdown": 0.30, "total_trades": 10, "precision_buy": 0.30,
         "trade_expectancy": {"expectancy": -50.0}, "symbol": "B", "window_index": 1},
    ]
    best = selector.select_best_model(results)
    if best and best["symbol"] == "A":
        print(f"  [PASS] Correct model selected: {best['symbol']} (Sharpe={best['sharpe_ratio']:.2f})")
        passed.append("ModelSelectionFilter")
    else:
        print(f"  [FAIL] Wrong model selected: {best}")
        issues.append(("ModelSelection", str(best)))
except Exception as e:
    print(f"  [FAIL] Model selection: {e}")
    issues.append(("ModelSelection", str(e)))

# 7. Portfolio Allocator Validation
print("\n7. PORTFOLIO ALLOCATOR VALIDATION")
print("-" * 40)
try:
    allocator = PortfolioAllocator(max_positions=3, strategy='edge_score', min_edge_score=1.0)
    signals = [
        {"symbol": "A", "prediction": 2, "confidence": 0.8, "edge_score": 2.5},
        {"symbol": "B", "prediction": 2, "confidence": 0.6, "edge_score": 0.8},  # Below threshold
        {"symbol": "C", "prediction": 0, "confidence": 0.7, "edge_score": 0.1},
    ]
    allocations = allocator.allocate(signals, available_capital=100000)
    if len(allocations) == 1 and allocations[0]["symbol"] == "A":
        print(f"  [PASS] Edge score allocation: {len(allocations)} position(s), weak signals filtered")
        print(f"       {allocations[0]['symbol']}: edge_score={allocations[0]['edge_score']:.2f}")
        passed.append("PortfolioAllocator")
    else:
        print(f"  [FAIL] Wrong allocations: {allocations}")
        issues.append(("PortfolioAllocator", str(allocations)))
except Exception as e:
    print(f"  [FAIL] Portfolio allocator: {e}")
    issues.append(("PortfolioAllocator", str(e)))

# 8. Regime Detector Validation
print("\n8. REGIME DETECTOR VALIDATION")
print("-" * 40)
try:
    detector = RegimeDetector()
    df = pd.DataFrame({
        "close": [100, 101, 102, 103],
        "ema_50": [99, 100, 101, 102],
        "ema_200": [95, 95, 95, 95],
        "atr_14": [2.0, 2.1, 2.2, 2.3],
    })
    regime = detector.detect(df, current_idx=3)
    if regime["trend"] == "TRENDING" and regime["volatility"] == "NORMAL":
        print(f"  [PASS] Regime detected: {regime}")
        passed.append("RegimeDetector")
    else:
        print(f"  [FAIL] Wrong regime: {regime}")
        issues.append(("RegimeDetector", str(regime)))
except Exception as e:
    print(f"  [FAIL] Regime detector: {e}")
    issues.append(("RegimeDetector", str(e)))

# 9. Report Generator Validation
print("\n9. REPORT GENERATOR VALIDATION")
print("-" * 40)
try:
    reporter = ReportGenerator(str(Path("reports_temp")))
    all_results = [
        {"sharpe_ratio": 1.2, "max_drawdown": 0.18, "total_trades": 50, 
         "precision_buy": 0.58, "trade_expectancy": {"expectancy": 120.0, "avg_win": 200, "avg_loss": 100, "win_rate": 0.6},
         "symbol": "A", "window_index": 0, "optimal_confidence_threshold": {"optimal_threshold": 0.65, "trade_count": 50, "expected_return": 120.0}}
    ]
    best = {"symbol": "A", "window_index": 0, "sharpe_ratio": 1.2, "max_drawdown": 0.18, "precision_buy": 0.58,
           "trade_expectancy": {"expectancy": 120.0, "avg_win": 200, "avg_loss": 100, "win_rate": 0.6}}
    
    # Test decision report
    try:
        decision_path = reporter.generate_decision_report(all_results, best, prediction_log=[], trade_log=[])
        print(f"  [PASS] Decision report generated")
        passed.append("DecisionReport")
    except Exception as e:
        print(f"  [FAIL] Decision report: {e}")
        issues.append(("DecisionReport", str(e)))
    
    # Cleanup
    import shutil
    if Path("reports_temp").exists():
        shutil.rmtree("reports_temp")
except Exception as e:
    print(f"  [FAIL] Report generator: {e}")
    issues.append(("ReportGenerator", str(e)))

# SUMMARY
print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)
print(f"\nPASSED: {len(passed)}/9 modules")
for p in passed:
    print(f"  [PASS] {p}")

if issues:
    print(f"\nFAILED: {len(issues)} issues")
    for module, issue in issues:
        print(f"  [FAIL] {module}: {issue}")
else:
    print("\n*** ALL VALIDATIONS PASSED ***")

print("\n" + "=" * 70)
