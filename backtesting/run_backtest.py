"""
Walk-Forward Backtesting System - Entry Point
AI Algo Swing Trading Agent

Usage:
    python run_backtest.py              # Full pipeline
    python run_backtest.py --dry-run    # Validate without executing
    python run_backtest.py --fetch-only # Only fetch data
    python run_backtest.py --train-only # Only train (uses existing data)
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
        logger.error("BLOCKED: NSE market hours detected (9:15 AM - 3:30 PM IST)")
        logger.error("Backtesting cannot run during live market hours.")
        return False
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


def run_full_pipeline():
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

    feature_pipeline = FeaturePipeline()
    featured_frames = []
    for sym in symbols:
        sym_data = all_data[all_data["symbol"] == sym].copy()
        if sym_data.empty:
            continue
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
        parameters=model_cfg.get("parameters", {}),
    )

    trainer.load_existing_model()

    all_results = []

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
                X_train, y_train = trainer.prepare_data(
                    train_df, feature_names, label_col="signal"
                )

                success = trainer.train(X_train, y_train)
                if not success:
                    logger.warning(f"Window {window_label}: Training failed, skipping")
                    continue

                available = [f for f in feature_names if f in test_df.columns]
                X_test = test_df[available].dropna()
                y_test = test_df.loc[X_test.index, "signal"]

                X_test_values = X_test.values

                predictions = trainer.predict(X_test_values)

                from backtest_engine.trade_simulator import TradeSimulator

                test_with_features = test_df.loc[X_test.index].copy()

                simulator = TradeSimulator(
                    initial_capital=bt_cfg["initial_capital"],
                    position_size_pct=bt_cfg["position_size_pct"],
                    max_positions=bt_cfg["max_positions"],
                    stop_loss_pct=bt_cfg["stop_loss_pct"],
                    target_pct=bt_cfg["target_pct"],
                    slippage_pct=bt_cfg.get("slippage_pct", 0.001),
                )

                sim_result = simulator.run(
                    test_with_features,
                    predictions,
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
        min_accuracy=selection_cfg["min_accuracy"],
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
    model_path = exporter.export_model(
        model_data=model_data,
        metadata={
            "metrics": best,
            "window_index": best_window_idx,
            "total_windows_evaluated": len(splits),
        },
        window_index=best_window_idx,
    )
    logger.info(f"Best model exported: {model_path}")

    # Step 7: Generate reports
    logger.info("STEP 7: Generating reports")
    reporter = ReportGenerator(str(reports_dir))

    reporter.generate_metrics_report(best)
    reporter.generate_trades_csv(
        [r for r in all_results if r.get("window_index") == best_window_idx],
        window_index=best_window_idx,
    )
    reporter.generate_full_report(all_results, best)

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"Best model: {model_path}")
    logger.info(f"Sharpe: {best.get('sharpe_ratio', 0):.2f}")
    logger.info(f"Max DD: {best.get('max_drawdown', 0):.2f}")
    logger.info(f"Accuracy: {best.get('accuracy', 0):.2f}")
    logger.info(f"Total trades: {best.get('total_trades', 0)}")
    logger.info("")
    logger.info("To deploy: copy models/latest_model.pkl to backend/services/ai/model.joblib")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Walk-Forward Backtesting System")
    parser.add_argument("--dry-run", action="store_true", help="Validate pipeline without executing")
    parser.add_argument("--fetch-only", action="store_true", help="Only fetch data from Yahoo Finance")
    parser.add_argument("--force", action="store_true", help="Skip safeguard confirmations")
    args = parser.parse_args()

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

    run_full_pipeline()


if __name__ == "__main__":
    main()
