import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ai.analyzer import StockAnalysis, StockAnalyzer


class TestStockAnalysis:
    def test_prediction_id_field_exists(self):
        analysis = StockAnalysis(
            symbol="TATASTEEL",
            trading_symbol="TATASTEEL",
            should_enter=False,
            confidence=0.0,
            signal="HOLD",
            entry_price=0,
            target_price=0,
            stop_loss=0,
            position_size=0,
            reason="Test",
        )
        assert hasattr(analysis, "prediction_id")
        assert analysis.prediction_id is None

    def test_prediction_id_stores_value(self):
        analysis = StockAnalysis(
            symbol="TATASTEEL",
            trading_symbol="TATASTEEL",
            should_enter=False,
            confidence=0.0,
            signal="HOLD",
            entry_price=0,
            target_price=0,
            stop_loss=0,
            position_size=0,
            reason="Test",
            prediction_id=123,
        )
        assert analysis.prediction_id == 123


class TestNoTradeMethod:
    def test_no_trade_with_prediction_id(self):
        analyzer = StockAnalyzer.__new__(StockAnalyzer)
        
        result = analyzer._no_trade(
            symbol="TATASTEEL",
            trading_symbol="TATASTEEL",
            reason="Test reason",
            confidence=0.5,
            p_buy=0.6,
            p_hold=0.3,
            p_sell=0.1,
            prediction_id=456,
        )
        
        assert result.should_enter is False
        assert result.prediction_id == 456
        assert result.symbol == "TATASTEEL"

    def test_no_trade_without_prediction_id(self):
        analyzer = StockAnalyzer.__new__(StockAnalyzer)
        
        result = analyzer._no_trade(
            symbol="RELIANCE",
            trading_symbol="RELIANCE",
            reason="Insufficient data",
        )
        
        assert result.should_enter is False
        assert result.prediction_id is None
        assert result.reason == "Insufficient data"
