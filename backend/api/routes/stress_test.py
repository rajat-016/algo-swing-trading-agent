from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from core.testing import StressTester
from core.model.registry import ModelRegistry
from core.logging import logger

router = APIRouter(prefix="/stress", tags=["stress_test"])


@router.post("/run/{scenario_name}")
async def run_stress_test(
    scenario_name: str,
    model_path: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        registry = ModelRegistry()
        if model_path:
            data = registry.load(model_path)
        else:
            data = registry.load()

        model = data["model"]
        scaler = data.get("scaler")
        feature_names = data.get("feature_names", [])

        tester = StressTester(model, scaler, feature_names)

        # Load scenario data
        import yaml
        from pathlib import Path

        scenario_file = Path("core/testing/stress_scenarios.yaml")
        if not scenario_file.exists():
            return {"error": "No scenarios found"}

        with open(scenario_file, "r") as f:
            scenarios = yaml.safe_load(f)

        scenario = None
        for s in scenarios.get("scenarios", []):
            if s["name"] == scenario_name:
                scenario = s
                break

        if not scenario:
            return {"error": f"Scenario {scenario_name} not found"}

        # Run appropriate test
        if scenario.get("type") == "historical":
            # historical test would need market data
            return {"error": "Historical scenarios not yet implemented"}
        else:
            # Synthetic scenario
            import numpy as np

            base_features = np.random.randn(100, len(feature_names))
            if "shock_pct" in scenario:
                result = tester.stress_test_portfolio(
                    positions=[{"entry_price": 100, "quantity": 10, "stop_loss": 95}],
                    market_shock_pct=scenario["shock_pct"],
                    volatility_multiplier=scenario.get("volatility_multiplier", 2.0),
                )
            else:
                result = tester.run_monte_carlo_stress(
                    base_features=base_features,
                    n_simulations=1000,
                    shock_mean=scenario.get("shock_mean", 0),
                    shock_std=scenario.get("shock_std", 0.05),
                )

        return {"scenario": scenario_name, "result": result}

    except Exception as e:
        logger.error(f"Stress test failed: {e}")
        return {"error": str(e)}


@router.post("/monte-carlo")
async def run_monte_carlo(
    n_simulations: int = 1000,
    shock_mean: float = -0.10,
    shock_std: float = 0.05,
    model_path: Optional[str] = None,
):
    try:
        registry = ModelRegistry()
        data = registry.load(model_path) if model_path else registry.load()

        model = data["model"]
        scaler = data.get("scaler")
        feature_names = data.get("feature_names", [])

        import numpy as np

        tester = StressTester(model, scaler, feature_names)
        base_features = np.random.randn(100, len(feature_names))

        result = tester.run_monte_carlo_stress(
            base_features=base_features,
            n_simulations=n_simulations,
            shock_mean=shock_mean,
            shock_std=shock_std,
        )

        return result

    except Exception as e:
        logger.error(f"Monte Carlo test failed: {e}")
        return {"error": str(e)}
