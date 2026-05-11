import hashlib
import joblib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def _compute_feature_hash(feature_names: List[str]) -> str:
    content = ",".join(sorted(feature_names))
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class ModelExporter:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._feature_version: Optional[str] = None

    def _detect_feature_version(self, feature_names: List[str]) -> str:
        if self._feature_version:
            return self._feature_version
        try:
            from core.pipeline.feature_pipeline import FEATURE_VERSION
            self._feature_version = FEATURE_VERSION
            return FEATURE_VERSION
        except ImportError:
            inferred = _compute_feature_hash(feature_names)
            self._feature_version = f"inferred-{inferred}"
            return self._feature_version

    def export_model(
        self,
        model_data: Dict[str, Any],
        metadata: Dict[str, Any],
        window_index: int = None,
    ) -> str:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")

        if window_index is not None:
            filename = f"model_window_{window_index}_{timestamp}.pkl"
        else:
            filename = f"model_{timestamp}.pkl"

        model_path = self.models_dir / filename

        feature_names = model_data.get("feature_names", [])
        model_data["scaler"] = model_data.get("scaler", None)
        model_data["feature_names"] = feature_names

        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")

        feature_version = self._detect_feature_version(feature_names)

        metadata_path = self.models_dir / filename.replace(".pkl", "_metadata.json")
        metadata["model_file"] = filename
        metadata["saved_at"] = datetime.now().isoformat()
        metadata["feature_version"] = feature_version
        metadata["feature_hash"] = _compute_feature_hash(feature_names)
        metadata["num_features"] = len(feature_names)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadata saved to {metadata_path}")

        latest_path = self.models_dir / "latest_model.pkl"
        joblib.dump(model_data, latest_path)

        latest_meta = self.models_dir / "latest_model_metadata.json"
        with open(latest_meta, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Latest model updated at {latest_path}")

        return str(model_path)
