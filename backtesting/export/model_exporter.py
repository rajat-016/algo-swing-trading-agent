import joblib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ModelExporter:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

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

        model_data["scaler"] = model_data.get("scaler", None)
        model_data["feature_names"] = model_data.get("feature_names", [])

        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")

        metadata_path = self.models_dir / filename.replace(".pkl", "_metadata.json")
        metadata["model_file"] = filename
        metadata["saved_at"] = datetime.now().isoformat()

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
