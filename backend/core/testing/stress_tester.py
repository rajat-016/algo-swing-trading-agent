import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from core.logging import logger


class StressTester:
    def __init__(self, model, scaler=None, feature_names: List[str] = None):
        self.model = model
        self.scaler = scaler
        self.feature_names = feature_names or []

    def run_historical_stress_test(
        self,
        market_data: Dict[str, np.ndarray],
        scenario_name: str,
        start_date: str,
        end_date: str,
    ) -> Dict:
        if scenario_name not in market_data:
            return {"error": f"Scenario {scenario_name} not found"}

        data = market_data[scenario_name]
        results = {
            "scenario": scenario_name,
            "start_date": start_date,
            "end_date": end_date,
            "predictions": [],
            "accuracy": 0,
            "loss_pct": 0,
        }

        try:
            if self.scaler:
                data_scaled = self.scaler.transform(data)
            else:
                data_scaled = data

            predictions = self.model.predict(data_scaled)
            probs = self.model.predict_proba(data_scaled)

            results["predictions"] = predictions.tolist()
            results["avg_confidence"] = float(np.mean(np.max(probs, axis=1)))
            results["signal_distribution"] = {
                "SELL": int(np.sum(predictions == 0)),
                "HOLD": int(np.sum(predictions == 1)),
                "BUY": int(np.sum(predictions == 2)),
            }

            logger.info(
                f"Stress test '{scenario_name}': "
                f"BUY={results['signal_distribution']['BUY']}, "
                f"HOLD={results['signal_distribution']['HOLD']}, "
                f"SELL={results['signal_distribution']['SELL']}"
            )

        except Exception as e:
            logger.error(f"Stress test failed: {e}")
            results["error"] = str(e)

        return results

    def run_monte_carlo_stress(
        self,
        base_features: np.ndarray,
        n_simulations: int = 1000,
        shock_mean: float = -0.10,
        shock_std: float = 0.05,
    ) -> Dict:
        results = {
            "n_simulations": n_simulations,
            "shock_mean": shock_mean,
            "shock_std": shock_std,
            "predictions_summary": {},
            "confidence_stats": {},
        }

        try:
            all_predictions = []
            all_confidences = []

            for _ in range(n_simulations):
                shock = np.random.normal(shock_mean, shock_std, base_features.shape)
                stressed_features = base_features + shock

                if self.scaler:
                    stressed_features = self.scaler.transform(stressed_features)

                pred = self.model.predict(stressed_features)
                probs = self.model.predict_proba(stressed_features)

                all_predictions.append(pred)
                all_confidences.append(np.max(probs, axis=1))

            all_predictions = np.array(all_predictions)
            all_confidences = np.array(all_confidences)

            results["predictions_summary"] = {
                "avg_buy_pct": float(np.mean(all_predictions == 2) * 100),
                "avg_hold_pct": float(np.mean(all_predictions == 1) * 100),
                "avg_sell_pct": float(np.mean(all_predictions == 0) * 100),
                "std_buy_pct": float(np.std(np.mean(all_predictions == 2, axis=1)) * 100),
            }

            results["confidence_stats"] = {
                "mean": float(np.mean(all_confidences)),
                "std": float(np.std(all_confidences)),
                "min": float(np.min(all_confidences)),
                "max": float(np.max(all_confidences)),
            }

        except Exception as e:
            logger.error(f"Monte Carlo stress test failed: {e}")
            results["error"] = str(e)

        return results

    def stress_test_portfolio(
        self,
        positions: List[Dict],
        market_shock_pct: float,
        volatility_multiplier: float = 2.0,
    ) -> Dict:
        total_loss = 0.0
        total_value = 0.0
        position_results = []

        for pos in positions:
            entry = pos.get("entry_price", 0)
            quantity = pos.get("quantity", 0)
            sl = pos.get("stop_loss", entry * 0.95)

            shocked_price = entry * (1 + market_shock_pct)
            sl_triggered = shocked_price <= sl

            pnl = (shocked_price - entry) * quantity
            total_loss += pnl
            total_value += entry * quantity

            position_results.append({
                "symbol": pos.get("symbol", "unknown"),
                "entry": entry,
                "shocked_price": shocked_price,
                "sl_triggered": sl_triggered,
                "pnl": pnl,
            })

        return {
            "market_shock_pct": market_shock_pct,
            "volatility_multiplier": volatility_multiplier,
            "total_value": total_value,
            "total_loss": total_loss,
            "loss_pct": (total_loss / total_value * 100) if total_value > 0 else 0,
            "positions": position_results,
        }

    def adversarial_feature_perturbation(
        self,
        features: np.ndarray,
        perturbation_pct: float = 0.10,
        n_trials: int = 100,
    ) -> Dict:
        if len(features.shape) == 1:
            features = features.reshape(1, -1)

        base_pred = self.model.predict(features)[0]
        base_probs = self.model.predict_proba(features)[0]
        base_conf = float(np.max(base_probs))

        flipped = 0
        conf_changes = []

        for _ in range(n_trials):
            noise = np.random.normal(0, perturbation_pct, features.shape)
            perturbed = features + noise

            if self.scaler:
                perturbed = self.scaler.transform(perturbed)

            pred = self.model.predict(perturbed)[0]
            probs = self.model.predict_proba(perturbed)[0]
            conf = float(np.max(probs))

            if pred != base_pred:
                flipped += 1
            conf_changes.append(abs(conf - base_conf))

        return {
            "base_prediction": int(base_pred),
            "base_confidence": base_conf,
            "n_trials": n_trials,
            "flip_count": flipped,
            "flip_rate": flipped / n_trials,
            "avg_confidence_change": float(np.mean(conf_changes)),
            "stable": (flipped / n_trials) < 0.05,
        }
