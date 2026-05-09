import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from core.logging import logger


class DriftDetector:
    def __init__(self, baseline_path: str = "core/monitoring/drift_baseline.json"):
        self.baseline_path = Path(baseline_path)
        self.baseline = self._load_baseline()

    def _load_baseline(self) -> Dict:
        if self.baseline_path.exists():
            try:
                with open(self.baseline_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load baseline: {e}")
        return {}

    def save_baseline(self, feature_stats: Dict, model_version: str = "latest") -> bool:
        try:
            self.baseline = {
                "model_version": model_version,
                "created_at": self._now(),
                "features": feature_stats,
            }
            self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.baseline_path, "w") as f:
                json.dump(self.baseline, f, indent=2)
            logger.info(f"Drift baseline saved: {self.baseline_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            return False

    def calculate_psi(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
        buckets: int = 10,
    ) -> float:
        try:
            expected = np.nan_to_num(expected, nan=0.0, posinf=0.0, neginf=0.0)
            actual = np.nan_to_num(actual, nan=0.0, posinf=0.0, neginf=0.0)

            min_val = min(expected.min(), actual.min())
            max_val = max(expected.max(), actual.max())

            if max_val - min_val < 1e-10:
                return 0.0

            breakpoints = np.linspace(min_val, max_val, buckets + 1)

            expected_counts = np.histogram(expected, bins=breakpoints)[0]
            actual_counts = np.histogram(actual, bins=breakpoints)[0]

            expected_pct = expected_counts / len(expected)
            actual_pct = actual_counts / len(actual)

            expected_pct = np.where(expected_pct == 0, 0.0001, expected_pct)
            actual_pct = np.where(actual_pct == 0, 0.0001, actual_pct)

            psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
            return float(psi)
        except Exception as e:
            logger.error(f"PSI calculation failed: {e}")
            return 0.0

    def calculate_ks_test(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
    ) -> Tuple[float, float]:
        try:
            from scipy.stats import ks_2samp
            expected = np.nan_to_num(expected, nan=0.0, posinf=0.0, neginf=0.0)
            actual = np.nan_to_num(actual, nan=0.0, posinf=0.0, neginf=0.0)
            statistic, p_value = ks_2samp(expected, actual)
            return float(statistic), float(p_value)
        except ImportError:
            logger.warning("scipy not available for KS test")
            return 0.0, 1.0
        except Exception as e:
            logger.error(f"KS test failed: {e}")
            return 0.0, 1.0

    def check_feature_drift(
        self,
        feature_name: str,
        train_values: np.ndarray,
        live_values: np.ndarray,
        psi_threshold: float = 0.2,
        ks_pvalue_threshold: float = 0.05,
    ) -> Dict:
        result = {
            "feature": feature_name,
            "psi": None,
            "ks_statistic": None,
            "ks_pvalue": None,
            "psi_drift": False,
            "ks_drift": False,
            "overall_drift": False,
        }

        if feature_name in self.baseline.get("features", {}):
            psi = self.calculate_psi(train_values, live_values)
            result["psi"] = psi
            result["psi_drift"] = psi > psi_threshold

        ks_stat, ks_pval = self.calculate_ks_test(train_values, live_values)
        result["ks_statistic"] = ks_stat
        result["ks_pvalue"] = ks_pval
        result["ks_drift"] = ks_pval < ks_pvalue_threshold

        result["overall_drift"] = result["psi_drift"] or result["ks_drift"]

        if result["overall_drift"]:
            logger.warning(f"Drift detected for {feature_name}: PSI={result['psi']}, KS p-value={result['ks_pvalue']}")

        return result

    def aggregate_drift_report(self, drift_results: List[Dict]) -> Dict:
        total = len(drift_results)
        psi_drifts = sum(1 for r in drift_results if r.get("psi_drift"))
        ks_drifts = sum(1 for r in drift_results if r.get("ks_drift"))
        overall_drifts = sum(1 for r in drift_results if r.get("overall_drift"))

        return {
            "total_features": total,
            "psi_drifts": psi_drifts,
            "ks_drifts": ks_drifts,
            "overall_drifts": overall_drifts,
            "drift_percentage": (overall_drifts / total * 100) if total > 0 else 0,
            "status": "DRIFT" if overall_drifts > 0 else "OK",
            "details": drift_results,
        }

    def build_baseline_from_training(
        self,
        X_train: np.ndarray,
        feature_names: List[str],
    ) -> Dict:
        stats = {}
        for i, name in enumerate(feature_names):
            col = X_train[:, i]
            col = col[~(np.isnan(col) | np.isinf(col))]
            if len(col) > 0:
                stats[name] = {
                    "mean": float(np.mean(col)),
                    "std": float(np.std(col)),
                    "min": float(np.min(col)),
                    "max": float(np.max(col)),
                    "percentiles": {
                        "p10": float(np.percentile(col, 10)),
                        "p25": float(np.percentile(col, 25)),
                        "p50": float(np.percentile(col, 50)),
                        "p75": float(np.percentile(col, 75)),
                        "p90": float(np.percentile(col, 90)),
                    },
                    "sample_count": len(col),
                }
        return stats

    def _now(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()
