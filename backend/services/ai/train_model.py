"""
Model training script for Swing Trading Agent.
Trains the adaptive model using historical data and trade history.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.ai.adaptive_model import AdaptiveModel
from services.ai.strategy_optimizer import StrategyOptimizer
from services.broker.kite import get_broker
from core.database import SessionLocal
from core.config import get_settings
from core.logging import logger
from models.stock import Stock, StockStatus


async def fetch_symbol_data(symbol: str, broker, days: int = 60):
    """Fetch historical data for a symbol."""
    try:
        from_date = datetime.now() - timedelta(days=days)
        to_date = datetime.now()
        
        data = broker.get_historical_data(
            symbol,
            from_date,
            to_date,
            interval="60minute"
        )
        
        if data:
            import pandas as pd
            return pd.DataFrame(data)
        return None
    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        return None


async def main():
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("Starting Model Training Pipeline")
    logger.info("=" * 60)
    
    broker = get_broker()
    if not broker.connect():
        logger.error("Failed to connect to broker")
        return
    
    db = SessionLocal()
    
    try:
        optimizer = StrategyOptimizer()
        
        trades_loaded = optimizer.load_trades_from_db(db)
        logger.info(f"Loaded {trades_loaded} historical trades")
        
        completed_stocks = db.query(Stock).filter(
            Stock.status == StockStatus.EXITED,
            Stock.exit_date.isnot(None),
            Stock.entry_price.isnot(None),
        ).all()
        
        if not completed_stocks:
            logger.warning("No completed trades found. Training will use limited data.")
        
        all_data = []
        for stock in completed_stocks[:50]:
            logger.info(f"Fetching data for {stock.symbol}...")
            df = await fetch_symbol_data(stock.symbol, broker, days=60)
            if df is not None and not df.empty:
                df["symbol"] = stock.symbol
                all_data.append(df)
        
        if not all_data:
            logger.error("No data collected for training")
            return
        
        logger.info(f"Collected {len(all_data)} symbol datasets")
        
        model = AdaptiveModel(
            target_return=settings.target_profit_pct / 100,
            stop_loss=settings.stop_loss_pct / 100,
        )
        
        for trade in optimizer.trade_history:
            model.add_trade_to_history(
                symbol=trade.symbol,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                features={},
                exit_reason=trade.exit_reason,
            )
        
        logger.info("Preparing training data...")
        X_train, X_test, y_train, y_test = model.prepare_data(all_data[0], all_data[1:] if len(all_data) > 1 else None)
        
        logger.info(f"Training data: {len(X_train)} samples")
        logger.info(f"Test data: {len(X_test)} samples")
        
        success = model.train(X_train, y_train, use_trade_history=True)
        
        if success:
            logger.info("Model training complete!")
            
            metrics = model.evaluate(X_test, y_test)
            logger.info(f"Training metrics: {metrics}")
            
            perf = model.get_performance_summary()
            if perf.get("trade_count", 0) > 0:
                logger.info(f"Adaptive performance: {perf['metrics']}")
            
            model_path = settings.model_path or "services/ai/model.joblib"
            if model.save_model(model_path):
                logger.info(f"Model saved to {model_path}")
            else:
                logger.error("Failed to save model")
        else:
            logger.error("Model training failed")
        
        logger.info("=" * 60)
        logger.info("Strategy Optimization Report")
        logger.info("=" * 60)
        
        report = optimizer.get_full_report()
        logger.info(f"Total trades analyzed: {report['metrics']['total_trades']}")
        logger.info(f"Win rate: {report['metrics']['win_rate']:.1f}%")
        logger.info(f"Profit factor: {report['metrics']['profit_factor']:.2f}")
        
        logger.info("\nSuggestions:")
        for suggestion in report['suggestions']:
            logger.info(f"  - {suggestion}")
        
        logger.info(f"\nOptimized parameters:")
        logger.info(f"  Target: {report['optimized_strategy']['target_pct']}%")
        logger.info(f"  Stop Loss: {report['optimized_strategy']['stop_loss_pct']}%")
        logger.info(f"  Max Hold: {report['optimized_strategy']['max_hold_hours']}h")
        
    except Exception as e:
        logger.error(f"Training pipeline error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    logger.info("Training pipeline complete")


if __name__ == "__main__":
    asyncio.run(main())