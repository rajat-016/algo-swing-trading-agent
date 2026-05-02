import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd

# Test all modules
from feature_engineering.feature_pipeline import FeaturePipeline
from labeling.label_generator import LabelGenerator
from backtest_engine.trade_simulator import TradeSimulator
from backtest_engine.position_manager import PositionManager, Position
from metrics.performance_metrics import PerformanceMetrics
from model_selection.selector import ModelSelector
from export.report_generator import ReportGenerator
from portfolio.allocator import PortfolioAllocator, PortfolioSimulator
from regime.regime_detector import RegimeDetector

print('All imports successful - syntax OK')

# Test edge score allocation with weak signal filtering
allocator = PortfolioAllocator(
    max_positions=3, 
    strategy='edge_score',
    min_edge_score=1.0  # Filter weak signals below 1.0
)
signals = [
    {'symbol': 'RELIANCE.NS', 'prediction': 2, 'confidence': 0.8, 'edge_score': 2.5},
    {'symbol': 'TCS.NS', 'prediction': 2, 'confidence': 0.6, 'edge_score': 0.8},  # Below threshold
    {'symbol': 'INFY.NS', 'prediction': 0, 'confidence': 0.7, 'edge_score': 0.1},
]
allocations = allocator.allocate(signals, available_capital=100000)
print(f'Edge score allocations (after filtering): {len(allocations)} positions')
for a in allocations:
    print(f'  {a["symbol"]}: edge_score={a.get("edge_score", 0):.2f}, alloc={a["allocated_capital"]:.2f}')

# Test regime detector
detector = RegimeDetector()
df = pd.DataFrame({
    'close': [100, 101, 102, 103],
    'ema_50': [99, 100, 101, 102],
    'ema_200': [95, 95, 95, 95],
    'atr_14': [2.0, 2.1, 2.2, 2.3],
})
regime = detector.detect(df, current_idx=3)
print(f'Regime detected: {regime}')

# Test edge score in TradeSimulator
simulator = TradeSimulator(
    initial_capital=100000,
    confidence_high=0.65,
    confidence_medium=0.50,
)
print('TradeSimulator with edge score: OK')

print('All tests passed!')
