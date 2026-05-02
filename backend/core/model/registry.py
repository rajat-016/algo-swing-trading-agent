import joblib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from core.logging import logger


class ModelRegistry:
    def __init__(self, model_dir: str = "services/ai"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        model,
        scaler,
        feature_names: list,
        metrics: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
    ) -> str:
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        path = self.model_dir / f"model_{version}.joblib"

        data = {
            "model": model,
            "scaler": scaler,
            "feature_names": feature_names,
            "metrics": metrics or {},
            "version": version,
            "saved_at": datetime.now().isoformat(),
            "num_features": len(feature_names),
        }

        joblib.dump(data, str(path))
        logger.info(f"Model saved: {path} ({len(feature_names)} features)")

        latest = self.model_dir / "model_latest.joblib"
        joblib.dump(data, str(latest))

        return str(path)

    def load(self, path: Optional[str] = None) -> Dict[str, Any]:
        if path is None:
            path = str(self.model_dir / "model_latest.joblib")

        if not Path(path).exists():
            raise FileNotFoundError(f"Model not found: {path}")

        data = joblib.load(path)
        logger.info(f"Model loaded: {path} (v{data.get('version', 'unknown')})")
        return data

    def list_models(self) -> list:
        models = list(self.model_dir.glob("model_*.joblib"))
        models.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(m) for m in models if "latest" not in m.name]

    def get_latest_path(self) -> Optional[str]:
        latest = self.model_dir / "model_latest.joblib"
        return str(latest) if latest.exists() else None
