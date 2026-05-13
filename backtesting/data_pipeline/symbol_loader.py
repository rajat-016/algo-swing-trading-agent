"""
Symbol Loader - Loads NIFTY symbols from backend/data/symbol_mapping.json
Provides Yahoo Finance-ready symbols with .NS suffix for backtesting.
"""

import json
import os
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SymbolLoader:
    """Load NIFTY symbols from mapping JSON file."""

    def __init__(self, mapping_path: Optional[str] = None):
        if mapping_path is None:
            backend_dir = Path(__file__).parent.parent.parent / "backend"
            mapping_path = backend_dir / "data" / "symbol_mapping.json"

        self.mapping_path = Path(mapping_path)
        self._data = None
        self._load()

    def _load(self):
        if not self.mapping_path.exists():
            raise FileNotFoundError(f"Symbol mapping file not found: {self.mapping_path}")

        try:
            with open(self.mapping_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info(f"SymbolLoader: Loaded mapping from {self.mapping_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in mapping file: {e}")

    def load_symbols(self, indices: str = "all", exchange_suffix: str = ".NS") -> List[str]:
        """
        Load symbols from mapping file.

        Args:
            indices: "all" for NIFTY 50 + Next 50, or specific index key
                    ("nifty_50", "nifty_next_50")
            exchange_suffix: Suffix for Yahoo Finance (default: ".NS")

        Returns:
            List of symbols with exchange suffix (e.g., ["RELIANCE.NS", ...])
        """
        if self._data is None:
            raise RuntimeError("Mapping data not loaded")

        symbols = []

        if indices == "all":
            for index_key, entries in self._data.items():
                for entry in entries:
                    chartink = entry.get("chartink", "").strip()
                    if chartink:
                        symbols.append(f"{chartink}{exchange_suffix}")
        else:
            if isinstance(indices, str):
                indices = [indices]

            for index_key in indices:
                entries = self._data.get(index_key, [])
                if not entries:
                    logger.warning(f"Index '{index_key}' not found in mapping file")
                for entry in entries:
                    chartink = entry.get("chartink", "").strip()
                    if chartink:
                        symbols.append(f"{chartink}{exchange_suffix}")

        seen = set()
        unique_symbols = []
        for sym in symbols:
            if sym not in seen:
                seen.add(sym)
                unique_symbols.append(sym)

        unique_symbols.sort()
        logger.info(f"SymbolLoader: Loaded {len(unique_symbols)} symbols (indices={indices})")
        return unique_symbols

    def get_symbol_info(self, chartink_symbol: str) -> Optional[dict]:
        """Get metadata for a specific symbol."""
        chartink = chartink_symbol.upper().replace(".NS", "").strip()

        for index_key, entries in self._data.items():
            for entry in entries:
                if entry.get("chartink", "").upper() == chartink:
                    return {
                        "chartink": entry["chartink"],
                        "kite": entry.get("kite", entry["chartink"]),
                        "name": entry.get("name", ""),
                        "index": index_key,
                    }
        return None

    def get_available_indices(self) -> List[str]:
        """Get list of available index keys in mapping file."""
        return list(self._data.keys()) if self._data else []

    def get_count(self, indices: str = "all") -> int:
        """Get total symbol count for given indices."""
        return len(self.load_symbols(indices))
