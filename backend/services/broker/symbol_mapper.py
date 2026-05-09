import json
import os
from typing import Optional, List, Dict
from core.logging import logger


class SymbolMapper:
    _instance = None

    def __init__(self):
        self._chartink_to_kite: Dict[str, str] = {}
        self._valid_chartink_symbols: set = set()
        self._valid_kite_symbols: set = set()
        self._metadata: Dict[str, str] = {}
        self._load_mapping()

    @classmethod
    def get_instance(cls) -> "SymbolMapper":
        if cls._instance is None:
            cls._instance = SymbolMapper()
        return cls._instance

    def _load_mapping(self):
        mapping_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "symbol_mapping.json")

        if not os.path.exists(mapping_path):
            logger.error(f"Symbol mapping file not found: {mapping_path}")
            return

        try:
            with open(mapping_path, "r") as f:
                data = json.load(f)

            for index_key in data.values():
                for entry in index_key:
                    chartink = entry["chartink"].upper()
                    kite = entry["kite"].upper()
                    self._chartink_to_kite[chartink] = kite
                    self._valid_chartink_symbols.add(chartink)
                    self._valid_kite_symbols.add(kite)
                    self._metadata[chartink] = entry.get("name", "")

            logger.info(f"SymbolMapper: Loaded {len(self._chartink_to_kite)} symbols")
        except Exception as e:
            logger.error(f"SymbolMapper: Failed to load mapping - {e}")

    def validate_symbol(self, chartink_symbol: str) -> Optional[str]:
        normalized = chartink_symbol.upper().strip()
        if normalized in self._valid_chartink_symbols:
            return self._chartink_to_kite[normalized]
        return None

    def get_kite_symbol(self, chartink_symbol: str) -> Optional[str]:
        return self.validate_symbol(chartink_symbol)

    def is_valid(self, chartink_symbol: str) -> bool:
        return self.validate_symbol(chartink_symbol) is not None

    def get_all_symbols(self) -> List[str]:
        return sorted(self._valid_chartink_symbols)

    def get_metadata(self, chartink_symbol: str) -> Optional[str]:
        normalized = chartink_symbol.upper().strip()
        return self._metadata.get(normalized)
