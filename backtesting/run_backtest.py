"""
Walk-Forward Backtesting System - Entry Point
AI Algo Swing Trading Agent

Usage:
    python run_backtest.py              # Full pipeline
    python run_backtest.py --dry-run    # Validate without executing
    python run_backtest.py --fetch-only # Only fetch data
    python run_backtest.py --train-only # Only train (uses existing data)
    python run_backtest.py --analyze    # Analyze latest backtest report
    python run_backtest.py --analyze --file reports/full_report_XXX.json  # Analyze specific report
"""

import sys
import os
import argparse
import logging
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

BACKEND_DIR = ROOT_DIR.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def setup_logging(log_dir: str = "logs", level: str = "INFO"):
    log_path = ROOT_DIR / log_dir
    log_path.mkdir(parents=True, exist_ok=True)

    log_file = log_path / "backtest.log"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


def is_market_hours() -> bool:
    import pytz
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    hour = now.hour
    minute = now.minute
    time_val = hour * 60 + minute
    weekday = now.weekday()

    if weekday >= 5:
        return False

    return 555 <= time_val <= 930


def is_live_system_running() -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.lower()
        if "main.py" in output:
            return True
        return False
    except Exception:
        return False


def check_broker_imports() -> list:
    forbidden = ["kiteconnect", "zerodha", "broker"]
    found = []

    for py_file in (ROOT_DIR).rglob("*.py"):
        if py_file.name == "run_backtest.py":
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for imp in forbidden:
                if f"import {imp}" in content or f"from {imp}" in content:
                    found.append(f"{py_file.relative_to(ROOT_DIR)}: {imp}")
        except Exception:
            pass

    return found


def validate_config(config: dict) -> list:
    errors = []

    if not config.get("symbols"):
        errors.append("symbols: must have at least one symbol")

    data_cfg = config.get("data", {})
    if not data_cfg.get("start_date"):
        errors.append("data.start_date: required")
    if not data_cfg.get("end_date"):
        errors.append("data.end_date: required")

    wf = config.get("walk_forward", {})
    if wf.get("train_window_years", 0) < 1:
        errors.append("walk_forward.train_window_years: must be >= 1")
    if wf.get("test_window_months", 0) < 1:
        errors.append("walk_forward.test_window_months: must be >= 1")

    bt = config.get("backtest", {})
    if bt.get("initial_capital", 0) <= 0:
        errors.append("backtest.initial_capital: must be > 0")

    return errors


def load_config() -> dict:
    import yaml
    config_path = ROOT_DIR / "config" / "backtest_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_safeguards(dry_run: bool = False) -> bool:
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("SAFEGUARD CHECKS")
    logger.info("=" * 60)

    if is_market_hours():
        logger.warning("[WARN] NSE market hours detected (9:15 AM - 3:30 PM IST)")
        logger.warning("Backtesting is isolated — safe to proceed, but ensure backend/main.py is not running")
    else:
        logger.info("[PASS] Not market hours")

    if is_live_system_running():
        logger.warning("WARNING: Live trading system (backend/main.py) appears to be running")
        logger.warning("Proceeding is safe (isolated system), but confirm you want to continue")
        if not dry_run:
            try:
                resp = input("Continue? (y/n): ").strip().lower()
                if resp != "y":
                    logger.info("Aborted by user")
                    return False
            except EOFError:
                logger.warning("Non-interactive mode, proceeding")
        logger.info("[WARN] Live system detected, user confirmed")
    else:
        logger.info("[PASS] Live trading system not running")

    broker_imports = check_broker_imports()
    if broker_imports:
        logger.error(f"BLOCKED: Forbidden broker imports found:")
        for item in broker_imports:
            logger.error(f"  - {item}")
        return False
    else:
        logger.info("[PASS] No broker imports found")

    logger.info("[PASS] All safeguard checks passed")
    return True


def run_dry_run():
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("DRY RUN - Pipeline Validation")
    logger.info("=" * 60)

    logger.info("Loading config...")
    config = load_config()
    logger.info("Config loaded successfully")

    logger.info("Validating config...")
    errors = validate_config(config)
    if errors:
        for e in errors:
            logger.error(f"  Config error: {e}")
        return False
    logger.info("Config validation passed")

    logger.info("Checking module imports...")
    try:
        from data_pipeline.yahoo_fetcher import YahooFetcher
        from data_pipeline.duckdb_manager import DuckDBManager
        from feature_engineering.feature_pipeline import FeaturePipeline
        from labeling.label_generator import LabelGenerator
        from training.walkforward_split import WalkForwardSplitter
        from training.model_trainer import ModelTrainer
        from backtest_engine.trade_simulator import TradeSimulator
        from backtest_engine.position_manager import PositionManager
        from metrics.performance_metrics import PerformanceMetrics
        from model_selection.selector import ModelSelector
        from export.model_exporter import ModelExporter
        from export.report_generator import ReportGenerator
        logger.info("All modules importable")
    except ImportError as e:
        logger.error(f"Import failed: {e}")
        return False

    logger.info("Checking FeatureEngineer from backend...")
    try:
        from services.ai.features import FeatureEngineer
        logger.info("Backend FeatureEngineer accessible")
    except ImportError as e:
        logger.error(f"Backend FeatureEngineer import failed: {e}")
        return False

    logger.info("=" * 60)
    logger.info("DRY RUN COMPLETE - All checks passed")
    logger.info("=" * 60)
    return True


def run_full_pipeline(args=None):
    logger = logging.getLogger(__name__)
    config = load_config()

    logger.info("=" * 60)
    logger.info("WALK-FORWARD BACKTESTING PIPELINE")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    symbols = config["symbols"]
    data_cfg = config["data"]
    label_cfg = config["labeling"]
    wf_cfg = config["walk_forward"]
    bt_cfg = config["backtest"]
    model_cfg = config["training"]
    selection_cfg = config["model_selection"]
    output_cfg = config["output"]

    models_dir = ROOT_DIR / output_cfg["models_dir"]
    reports_dir = ROOT_DIR / output_cfg["reports_dir"]
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Fetch data
    logger.info("STEP 1: Fetching OHLCV data from Yahoo Finance")
    from data_pipeline.yahoo_fetcher import YahooFetcher
    from data_pipeline.duckdb_manager import DuckDBManager

    db_path = ROOT_DIR / data_cfg["db_path"]
    db = DuckDBManager(str(db_path))

    fetcher = YahooFetcher()
    for symbol in symbols:
        latest = db.get_latest_date(symbol)
        fetch_start = data_cfg["start_date"]
        if latest:
            fetch_start = (latest - __import__('datetime').timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"{symbol}: Fetching from {fetch_start} (incremental)")

        dfs = fetcher.fetch_multiple_symbols(
            [symbol],
            start_date=fetch_start,
            end_date=data_cfg["end_date"],
            interval=config.get("timeframe", "1h"),
        )
        for df in dfs:
            db.insert_dataframe_upsert(df)

    all_data = db.load_data(
        start_date=data_cfg["start_date"],
        end_date=data_cfg["end_date"],
        symbols=symbols,
    )
    logger.info(f"Loaded {len(all_data)} total rows from DuckDB")

    if all_data.empty:
        logger.error("No data fetched. Cannot proceed.")
        logger.error("Check: symbols have .NS suffix, date range is valid, internet connection")
        return

    # Step 2: Generate features per symbol
    logger.info("STEP 2: Generating features")
    from feature_engineering.feature_pipeline import FeaturePipeline

    # Fetch NIFTY 50 data for relative strength features
    nifty_df = None
    try:
        nifty_data_list = fetcher.fetch_multiple_symbols(
            ["^NSEI"],
            start_date=data_cfg["start_date"],
            end_date=data_cfg["end_date"],
            interval=config.get("timeframe", "1d"),
        )
        if nifty_data_list:
            nifty_df = nifty_data_list[0]
            logger.info(f"NIFTY 50 data loaded: {len(nifty_df)} rows")
    except Exception as e:
        logger.warning(f"Could not fetch NIFTY data: {e}. Relative strength features will use defaults.")

    feature_pipeline = FeaturePipeline()
    featured_frames = []
    for sym in symbols:
        sym_data = all_data[all_data["symbol"] == sym].copy()
        if sym_data.empty:
            continue
        # Set NIFTY data for relative strength calculation
        if nifty_df is not None:
            feature_pipeline.engineer.set_nifty_data(nifty_df)
        featured = feature_pipeline.generate_features(sym_data)
        featured_frames.append(featured)

    featured_data = pd.concat(featured_frames, ignore_index=True)
    all_feature_names = feature_pipeline.get_feature_names()
    feature_names = [f for f in all_feature_names if f in featured_data.columns]
    logger.info(f"Generated {len(feature_names)} features ({len(all_feature_names) - len(feature_names)} unavailable)")

    # Step 3: Create labels
    logger.info("STEP 3: Creating labels")
    from labeling.label_generator import LabelGenerator

    labeler = LabelGenerator(
        lookahead=label_cfg["lookahead_periods"],
        threshold=label_cfg["return_threshold"],
        stop_loss=label_cfg.get("stop_loss", 0.03),
        atr_target_multiplier=label_cfg.get("atr_target_multiplier", 1.5),
        atr_stop_multiplier=label_cfg.get("atr_stop_multiplier", 1.0),
    )
    labeled_data = labeler.create_labels(featured_data)

    critical_cols = ["signal", "close", "open", "high", "low", "volume", "datetime", "symbol"]
    critical_available = [c for c in critical_cols if c in labeled_data.columns]
    labeled_data = labeled_data.dropna(subset=critical_available)

    feature_available = [f for f in feature_names if f in labeled_data.columns]
    nan_counts = labeled_data[feature_available].isna().sum()
    high_nan = nan_counts[nan_counts > len(labeled_data) * 0.5].index.tolist()
    feature_names = [f for f in feature_names if f not in high_nan]

    feature_available = [f for f in feature_names if f in labeled_data.columns]
    labeled_data = labeled_data.dropna(subset=feature_available, how="all")

    logger.info(f"Dropped {len(high_nan)} features with >50% NaN")
    logger.info(f"Dataset after label creation: {len(labeled_data)} rows, {len(feature_names)} features")

    # Step 4: Walk-forward training — per symbol
    logger.info("STEP 4: Walk-forward training")
    from training.walkforward_split import WalkForwardSplitter
    from training.model_trainer import ModelTrainer

    splitter = WalkForwardSplitter(
        train_window_years=wf_cfg["train_window_years"],
        test_window_months=wf_cfg["test_window_months"],
        step_months=wf_cfg["step_months"],
    )

    trainer = ModelTrainer(
        model_path=str(BACKEND_DIR / "services" / "ai" / "model.joblib"),
        parameters={**model_cfg.get("parameters", {}), "num_classes": model_cfg.get("num_classes", 3)},
    )

    trainer.load_existing_model()

    all_results = []

    # Portfolio simulation mode: collect all signals per window across symbols
    run_portfolio_mode = bt_cfg.get("portfolio_mode", False)
    
    if run_portfolio_mode:
        logger.info("PORTFOLIO MODE ENABLED - Allocating capital across symbols")
        from portfolio.allocator import PortfolioAllocator
        
        # Group data by window across all symbols
        window_symbol_data = {}  # (window_key) -> [(sym, test_df, predictions, probabilities, edge_scores)]
        
        for sym in symbols:
            sym_data = labeled_data[labeled_data["symbol"] == sym].copy()
            if len(sym_data) < 200:
                logger.warning(f"{sym}: Insufficient data ({len(sym_data)} rows), skipping")
                continue

            sym_splits = splitter.generate_splits(sym_data)

            for idx, (train_df, test_df) in enumerate(sym_splits):
                window_key = idx  # Using window index as key (simplified)
                
                try:
                    X_train, y_train, sample_weights = trainer.prepare_data(
                        train_df, feature_names, label_col="signal"
                    )
                    success = trainer.train(X_train, y_train, sample_weights=sample_weights)
                    if not success:
                        continue

                    available = [f for f in feature_names if f in test_df.columns]
                    X_test = test_df[available].dropna()
                    
                    predictions = trainer.predict(X_test.values)
                    probabilities = trainer.predict_proba(X_test.values)
                    
                    # NEW: Compute edge scores for BUY signals
                    edge_scores = []
                    has_atr = "atr_14" in test_df.columns
                    for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
                        if int(pred) == 2:  # BUY signal
                            conf = float(np.max(prob))
                            row = test_df.iloc[i] if i < len(test_df) else None
                            if row is not None:
                                entry_price = row["close"]
                                atr_val = row["atr_14"] if has_atr else None
                                # Calculate edge score: confidence * (reward/risk)
                                stop_loss = entry_price - (atr_val * 2.0) if atr_val else entry_price * 0.97
                                target = entry_price + (atr_val * 4.0) if atr_val else entry_price * 1.15
                                risk = abs(entry_price - stop_loss)
                                reward = abs(target - entry_price)
                                edge = conf * (reward / risk) if risk > 0 else conf
                                edge_scores.append(edge)
                            else:
                                edge_scores.append(conf)
                        else:
                            edge_scores.append(0.0)
                    
                    if window_key not in window_symbol_data:
                        window_symbol_data[window_key] = []
                    window_symbol_data[window_key].append({
                        "symbol": sym,
                        "test_df": test_df.loc[X_test.index].copy(),
                        "predictions": predictions,
                        "probabilities": probabilities,
                        "edge_scores": edge_scores,
                    })
                except Exception as e:
                    logger.error(f"{sym}_W{idx} failed: {e}")
                    continue

        # Run portfolio simulation per window
        for window_idx, sym_data_list in window_symbol_data.items():
            logger.info(f"--- Portfolio Window {window_idx} ({len(sym_data_list)} symbols) ---")
            
            allocator = PortfolioAllocator(
                max_positions=bt_cfg["max_positions"],
                strategy=bt_cfg.get("allocation_strategy", "edge_score"),  # NEW default
            )
            
            # Merge all test data for simulation
            all_test_dfs = []
            all_predictions = []
            all_probabilities = []
            all_edge_scores = []
            
            for sym_data in sym_data_list:
                all_test_dfs.append(sym_data["test_df"])
                all_predictions.extend(sym_data["predictions"])
                all_probabilities.extend(sym_data["probabilities"])
                if "edge_scores" in sym_data:
                    all_edge_scores.extend(sym_data["edge_scores"])
            
            merged_test = pd.concat(all_test_dfs).sort_values("datetime").reset_index(drop=True)
            
            simulator = TradeSimulator(
                initial_capital=bt_cfg["initial_capital"],
                max_positions=bt_cfg["max_positions"],
                stop_loss_pct=bt_cfg["stop_loss_pct"],
                target_pct=bt_cfg["target_pct"],
                slippage_pct=bt_cfg.get("slippage_pct", 0.001),
                brokerage_rate=bt_cfg.get("brokerage_rate", 0.0015),
                stt_rate=bt_cfg.get("stt_rate", 0.00025),
                use_atr_sl=bt_cfg.get("use_atr_sl", True),
                atr_sl_multiplier=bt_cfg.get("atr_sl_multiplier", 2.0),
                atr_target_multiplier=bt_cfg.get("atr_target_multiplier", 4.0),
                cooldown_bars=bt_cfg.get("cooldown_bars", 3),
                max_holding_bars=bt_cfg.get("max_holding_bars", 7),
                confidence_high=bt_cfg.get("confidence_high", 0.65),
                confidence_medium=bt_cfg.get("confidence_medium", 0.50),
            )
            
            sim_result = simulator.run(
                merged_test,
                np.array(all_predictions),
                probabilities=np.array(all_probabilities),
                datetime_col="datetime",
            )
            
            # Calculate metrics
            from metrics.performance_metrics import PerformanceMetrics
            import numpy as np
            
            metrics = PerformanceMetrics.calculate_all(
                trade_log=sim_result["trade_log"],
                equity_curve=sim_result["equity_curve"],
                dates=sim_result["dates"],
                predictions=np.array(all_predictions),
                actuals=merged_test["signal"].values,
            )
            
            if "prediction_log" in sim_result:
                metrics["confidence_buckets"] = PerformanceMetrics.confidence_bucket_analysis(
                    sim_result["prediction_log"]
                )
            
            metrics["trade_expectancy"] = PerformanceMetrics.trade_expectancy(sim_result["trade_log"])
            metrics["optimal_confidence_threshold"] = PerformanceMetrics.find_optimal_confidence_threshold(
                sim_result["trade_log"]
            )
            metrics["window_index"] = window_idx
            metrics["symbol"] = "PORTFOLIO"
            all_results.append(metrics)
            
    else:
        # Original per-symbol mode
        for sym in symbols:
            sym_data = labeled_data[labeled_data["symbol"] == sym].copy()
            if len(sym_data) < 200:
                logger.warning(f"{sym}: Insufficient data ({len(sym_data)} rows), skipping")
                continue

            sym_splits = splitter.generate_splits(sym_data)
            logger.info(f"{sym}: {len(sym_splits)} walk-forward windows")

            for idx, (train_df, test_df) in enumerate(sym_splits):
                window_label = f"{sym}_W{idx}"
                logger.info(f"--- Window {window_label} ---")

                try:
                    X_train, y_train, sample_weights = trainer.prepare_data(
                        train_df, feature_names, label_col="signal"
                    )

                    success = trainer.train(X_train, y_train, sample_weights=sample_weights)
                    if not success:
                        logger.warning(f"Window {window_label}: Training failed, skipping")
                        continue

                    available = [f for f in feature_names if f in test_df.columns]
                    X_test = test_df[available].dropna()
                    y_test = test_df.loc[X_test.index, "signal"]

                    X_test_values = X_test.values
                    
                    predictions = trainer.predict(X_test_values)
                    probabilities = trainer.predict_proba(X_test_values)

                    import numpy as np
                    unique, counts = np.unique(predictions, return_counts=True)
                    prediction_counts = dict(zip(unique.tolist(), counts.tolist()))

                    from backtest_engine.trade_simulator import TradeSimulator

                    test_with_features = test_df.loc[X_test.index].copy()

                    simulator = TradeSimulator(
                        initial_capital=bt_cfg["initial_capital"],
                        position_size_pct=bt_cfg["position_size_pct"],
                        max_positions=bt_cfg["max_positions"],
                        stop_loss_pct=bt_cfg["stop_loss_pct"],
                        target_pct=bt_cfg["target_pct"],
                        slippage_pct=bt_cfg.get("slippage_pct", 0.001),
                        brokerage_rate=bt_cfg.get("brokerage_rate", 0.0015),
                        stt_rate=bt_cfg.get("stt_rate", 0.00025),
                        use_atr_sl=bt_cfg.get("use_atr_sl", True),
                        atr_sl_multiplier=bt_cfg.get("atr_sl_multiplier", 2.0),
                        atr_target_multiplier=bt_cfg.get("atr_target_multiplier", 4.0),
                        cooldown_bars=bt_cfg.get("cooldown_bars", 3),
                        max_holding_bars=bt_cfg.get("max_holding_bars", 7),
                        confidence_high=bt_cfg.get("confidence_high", 0.65),
                        confidence_medium=bt_cfg.get("confidence_medium", 0.50),
                    )

                    sim_result = simulator.run(
                        test_with_features,
                        predictions,
                        probabilities=probabilities,
                        datetime_col="datetime",
                    )

                    from metrics.performance_metrics import PerformanceMetrics

                    metrics = PerformanceMetrics.calculate_all(
                        trade_log=sim_result["trade_log"],
                        equity_curve=sim_result["equity_curve"],
                        dates=sim_result["dates"],
                        predictions=predictions,
                        actuals=y_test.values,
                    )

                    if "prediction_log" in sim_result:
                        confidence_buckets = PerformanceMetrics.confidence_bucket_analysis(
                            sim_result["prediction_log"]
                        )
                        metrics["confidence_buckets"] = confidence_buckets

                    trade_expectancy = PerformanceMetrics.trade_expectancy(sim_result["trade_log"])
                    metrics["trade_expectancy"] = trade_expectancy

                    optimal_threshold = PerformanceMetrics.find_optimal_confidence_threshold(
                        sim_result["trade_log"]
                    )
                    metrics["optimal_confidence_threshold"] = optimal_threshold
                    
                    logger.info(
                        f"Window {window_label}: Optimal threshold = {optimal_threshold['optimal_threshold']:.2f} "
                        f"(trades={optimal_threshold['trade_count']}, exp_return={optimal_threshold['expected_return']:.2f})"
                    )
                    if optimal_threshold.get("all_negative_expectancy", False):
                        logger.warning(f"Window {window_label}: All confidence thresholds have negative expectancy")

                    metrics["prediction_counts"] = prediction_counts
                    metrics["window_index"] = idx
                    metrics["symbol"] = sym
                    all_results.append(metrics)

                    logger.info(
                        f"Window {window_label}: Sharpe={metrics.get('sharpe_ratio', 0):.2f}, "
                        f"DD={metrics.get('max_drawdown', 0):.2f}, "
                        f"Acc={metrics.get('accuracy', 0):.2f}, "
                        f"Trades={metrics.get('total_trades', 0)}"
                    )

                except Exception as e:
                    logger.error(f"Window {window_label} failed: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

    if not all_results:
        logger.error("No successful windows. Pipeline failed.")
        return

    # Step 5: Select best model
    logger.info("STEP 5: Selecting best model")
    from model_selection.selector import ModelSelector

    selector = ModelSelector(
        min_sharpe=selection_cfg["min_sharpe"],
        max_drawdown=selection_cfg["max_drawdown"],
        primary_metric=selection_cfg["primary_metric"],
    )

    best = selector.select_best_model(all_results)

    if best is None:
        logger.warning("No model selected. Thresholds not met.")
        return

    # Step 6: Export model
    logger.info("STEP 6: Exporting best model")
    from export.model_exporter import ModelExporter
    from export.report_generator import ReportGenerator

    exporter = ModelExporter(str(models_dir))

    model_data = {
        "model": trainer.model,
        "scaler": trainer.scaler,
        "feature_names": trainer.feature_names,
    }

    best_window_idx = best.get("window_index", 0)
    model_type = type(trainer.model).__name__
    model_path = exporter.export_model(
        model_data=model_data,
        metadata={
            "metrics": best,
            "window_index": best_window_idx,
            "total_windows_evaluated": len(all_results),
            "model_type": model_type,
        },
        window_index=best_window_idx,
    )
    logger.info(f"Best model ({model_type}) exported: {model_path}")

    # Step 7: Generate reports
    logger.info("STEP 7: Generating reports")
    reporter = ReportGenerator(str(reports_dir))

    reporter.generate_metrics_report(best)
    reporter.generate_trades_csv(
        [r for r in all_results if r.get("window_index") == best_window_idx],
        window_index=best_window_idx,
    )
    full_report_path = reporter.generate_full_report(all_results, best)
    
    # NEW: Generate executive summary and alpha validation
    exec_summary_path = reporter.generate_executive_summary(all_results, best)
    alpha_path = reporter.generate_alpha_validation(all_results)
    logger.info(f"Executive summary: {exec_summary_path}")
    logger.info(f"Alpha validation: {alpha_path}")

    # Step 8: Auto-generate health report
    logger.info("STEP 8: Generating health report")
    from analysis.report_analyzer import ReportAnalyzer
    analyzer = ReportAnalyzer(reports_dir=str(reports_dir))
    # Build a minimal report structure for analysis
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "total_windows": len(all_results),
        "windows": all_results,
        "best_model": best,
    }
    analysis = analyzer.analyze_report(report_data, report_path=str(full_report_path))
    health_path = analyzer.save_health_report(analysis)
    logger.info(f"Health report generated: {health_path}")

    # Step 9: Auto-deploy to backend
    deploy_enabled = output_cfg.get("deploy_to_backend", False)
    deploy_skipped = args is not None and getattr(args, "no_deploy", False)
    if deploy_enabled and not deploy_skipped:
        logger.info("STEP 9: Deploying model to backend")
        backend_model = BACKEND_DIR / "services" / "ai" / "model.joblib"
        deploy_path = _deploy_to_backend(model_path, backend_model, logger)
        if deploy_path:
            logger.info(f"Model deployed to {deploy_path}")
        else:
            logger.warning("Model deployment failed - check logs above")
    else:
        logger.info("STEP 9: Skipped (deploy_to_backend disabled or --no-deploy flag set)")

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"Best model ({model_type}): {model_path}")
    logger.info(f"Sharpe: {best.get('sharpe_ratio', 0):.2f}")
    logger.info(f"Max DD: {best.get('max_drawdown', 0):.2f}")
    logger.info(f"Accuracy: {best.get('accuracy', 0):.2f}")
    logger.info(f"Total trades: {best.get('total_trades', 0)}")
    logger.info("=" * 60)


def _deploy_to_backend(source: str, dest: Path, logger) -> str | None:
    import shutil

    source_path = Path(source)
    if not source_path.exists():
        logger.error(f"Deploy failed: source model not found at {source}")
        return None

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing backend model
        if dest.exists():
            backup = dest.with_suffix(f".joblib.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            shutil.copy2(str(dest), str(backup))
            logger.info(f"Existing backend model backed up to {backup}")

        # Copy new model (latest_model.pkl) to backend as model.joblib
        shutil.copy2(str(source_path), str(dest))
        logger.info(f"Model deployed: {source_path.name} -> {dest}")

        # Verify deployment
        if dest.exists():
            logger.info(f"Verification: Deployed model size = {dest.stat().st_size} bytes")
            return str(dest)
        else:
            logger.error("Verification failed: Deployed model not found after copy")
            return None

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Walk-Forward Backtesting System")
    parser.add_argument("--dry-run", action="store_true", help="Validate pipeline without executing")
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch data from Yahoo Finance")
    parser.add_argument("--force", action="store_true", help="Skip safeguard confirmations")
    parser.add_argument("--no-deploy", action="store_true", help="Skip auto-deployment to backend")
    parser.add_argument("--analyze", action="store_true", help="Analyze backtest report and generate health report")
    parser.add_argument("--file", type=str, default=None, help="Specific report file to analyze (with --analyze)")
    args = parser.parse_args()

    if args.analyze:
        from analysis.report_analyzer import ReportAnalyzer
        analyzer = ReportAnalyzer(reports_dir=str(ROOT_DIR / "reports"))
        analysis = analyzer.run_analysis(report_path=args.file)
        if analysis:
            report_text = analyzer.generate_health_report(analysis)
            print(report_text)
            health_path = analyzer.save_health_report(analysis)
            print(f"\nHealth report saved to: {health_path}")
        else:
            print("ERROR: No report found to analyze")
        sys.exit(0)

    import yaml
    try:
        config = load_config()
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}")
        sys.exit(1)

    logger = setup_logging(
        log_dir=config.get("output", {}).get("logs_dir", "logs"),
        level=config.get("logging", {}).get("level", "INFO"),
    )

    logger.info(f"Working directory: {ROOT_DIR}")

    if not run_safeguards(dry_run=args.dry_run):
        logger.error("Safeguard checks failed. Aborting.")
        sys.exit(1)

    if args.dry_run:
        success = run_dry_run()
        sys.exit(0 if success else 1)

    run_full_pipeline(args)


if __name__ == "__main__":
    main()
