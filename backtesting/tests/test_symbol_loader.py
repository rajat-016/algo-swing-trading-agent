import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

import pytest
import json
from pathlib import Path
from data_pipeline.symbol_loader import SymbolLoader


class TestSymbolLoader:
    @pytest.fixture
    def loader(self):
        return SymbolLoader()

    def test_loads_all_symbols(self, loader):
        symbols = loader.load_symbols()
        assert len(symbols) == 101, f"Expected 101 symbols, got {len(symbols)}"

    def test_nifty_50_only(self, loader):
        symbols = loader.load_symbols(indices="nifty_50")
        assert len(symbols) >= 50, f"Expected >= 50 NIFTY 50 symbols, got {len(symbols)}"

    def test_nifty_next_50_only(self, loader):
        symbols = loader.load_symbols(indices="nifty_next_50")
        assert len(symbols) == 50, f"Expected 50 Next 50 symbols, got {len(symbols)}"

    def test_symbols_have_ns_suffix(self, loader):
        symbols = loader.load_symbols()
        for sym in symbols:
            assert sym.endswith(".NS"), f"Symbol {sym} missing .NS suffix"

    def test_known_nifty_50_symbols(self, loader):
        symbols = loader.load_symbols()
        assert "RELIANCE.NS" in symbols
        assert "TCS.NS" in symbols
        assert "INFY.NS" in symbols
        assert "HDFCBANK.NS" in symbols
        assert "SBIN.NS" in symbols

    def test_known_next_50_symbols(self, loader):
        symbols = loader.load_symbols()
        assert "ABB.NS" in symbols
        assert "HAL.NS" in symbols
        assert "VEDL.NS" in symbols
        assert "DLF.NS" in symbols
        assert "PFC.NS" in symbols

    def test_symbols_sorted(self, loader):
        symbols = loader.load_symbols()
        assert symbols == sorted(symbols), "Symbols should be sorted alphabetically"

    def test_no_duplicates(self, loader):
        symbols = loader.load_symbols()
        assert len(symbols) == len(set(symbols)), "Symbols should have no duplicates"

    def test_get_symbol_info(self, loader):
        info = loader.get_symbol_info("RELIANCE")
        assert info is not None
        assert info["chartink"] == "RELIANCE"
        assert info["kite"] == "RELIANCE"
        assert info["index"] == "nifty_50"
        assert "Reliance" in info["name"]

    def test_get_symbol_info_next_50(self, loader):
        info = loader.get_symbol_info("ABB")
        assert info is not None
        assert info["index"] == "nifty_next_50"

    def test_get_symbol_info_unknown(self, loader):
        info = loader.get_symbol_info("NOTASTOCK")
        assert info is None

    def test_get_available_indices(self, loader):
        indices = loader.get_available_indices()
        assert "nifty_50" in indices
        assert "nifty_next_50" in indices

    def test_get_count(self, loader):
        assert loader.get_count() == 101
        assert loader.get_count("nifty_50") >= 50
        assert loader.get_count("nifty_next_50") == 50

    def test_custom_exchange_suffix(self, loader):
        symbols = loader.load_symbols(exchange_suffix=".BSE")
        assert all(sym.endswith(".BSE") for sym in symbols)

    def test_mapping_file_exists(self):
        mapping_path = Path(__file__).parent.parent.parent / "backend" / "data" / "symbol_mapping.json"
        assert mapping_path.exists(), f"Mapping file not found at {mapping_path}"
        with open(mapping_path) as f:
            data = json.load(f)
        assert "nifty_50" in data
        assert "nifty_next_50" in data

    def test_hyphenated_symbols(self, loader):
        symbols = loader.load_symbols()
        assert "BAJAJ-AUTO.NS" in symbols

    def test_short_symbols(self, loader):
        symbols = loader.load_symbols()
        assert "ITC.NS" in symbols
        assert "TCS.NS" in symbols
        assert "BEL.NS" in symbols
        assert "INFY.NS" in symbols

    def test_m_and_m_symbol(self, loader):
        symbols = loader.load_symbols()
        assert "M&M.NS" in symbols
