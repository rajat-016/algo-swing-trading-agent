#!/usr/bin/env python3
"""
AI Infrastructure Bootstrap Script.

Verifies and initializes:
  1. Ollama runtime (checks health, pulls models if missing)
  2. ChromaDB (creates persist directory, verifies import)
  3. DuckDB (creates analytics database with schemas)
  4. AI module imports (verifies the package structure)

Usage:
    python scripts/bootstrap_ai.py
    python scripts/bootstrap_ai.py --pull-models   # Also pulls Ollama models
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_ollama() -> bool:
    print("\n[1/5] Checking Ollama runtime...")
    try:
        import httpx
        from ai.config.settings import ai_settings

        base = ai_settings.ollama_host
        resp = httpx.get(f"{base}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            print(f"  OK: Ollama running at {base}")
            print(f"  Available models: {len(models)}")
            for m in models:
                print(f"    - {m['name']}")
            return True
        else:
            print(f"  WARN: Ollama returned status {resp.status_code}")
            return False
    except ImportError:
        print("  SKIP: httpx not installed")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        print("  HINT: Is Ollama installed and running? https://ollama.ai")
        return False


def pull_models(models: list[str]) -> bool:
    print(f"\n[1b] Pulling models: {', '.join(models)}...")
    try:
        import httpx
        from ai.config.settings import ai_settings

        base = ai_settings.ollama_host
        for model in models:
            print(f"  Pulling {model}...")
            resp = httpx.post(
                f"{base}/api/pull",
                json={"name": model, "stream": False},
                timeout=600,
            )
            if resp.status_code == 200:
                print(f"  OK: {model} pulled")
            else:
                print(f"  FAIL: {model} pull failed: {resp.text}")
                return False
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def check_chromadb() -> bool:
    print("\n[2/5] Checking ChromaDB...")
    try:
        import chromadb
        from chromadb.config import Settings
        from ai.config.settings import ai_settings

        persist_dir = ai_settings.chromadb_persist_directory
        os.makedirs(persist_dir, exist_ok=True)

        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        collections = client.list_collections()
        print(f"  OK: ChromaDB initialized at {persist_dir}")
        print(f"  Existing collections: {len(collections)}")
        for c in collections:
            print(f"    - {c.name}")
        return True
    except ImportError:
        print("  SKIP: chromadb not installed")
        print("  RUN: pip install chromadb")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def check_duckdb() -> bool:
    print("\n[3/5] Checking DuckDB...")
    try:
        import duckdb
        from ai.config.settings import ai_settings

        db_path = ai_settings.duckdb_absolute_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = duckdb.connect(db_path)
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        print(f"  OK: DuckDB initialized at {db_path}")
        print(f"  Existing tables: {len(tables)}")
        for t in tables:
            print(f"    - {t[0]}")
        conn.close()
        return True
    except ImportError:
        print("  SKIP: duckdb not installed")
        print("  RUN: pip install duckdb")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def check_imports() -> bool:
    print("\n[4/5] Checking AI module imports...")
    modules = [
        "ai",
        "ai.config",
        "ai.config.settings",
        "ai.llm",
        "ai.llm.client",
        "ai.llm.models",
        "ai.prompts",
        "ai.prompts.base",
        "ai.prompts.registry",
        "ai.inference",
        "ai.inference.embedding_service",
        "ai.inference.chromadb_client",
        "ai.inference.duckdb_setup",
        "ai.inference.service",
        "ai.orchestration",
        "ai.orchestration.engine",
        "ai.orchestration.circuit_breaker",
    ]
    all_ok = True
    for mod in modules:
        try:
            __import__(mod)
            print(f"  OK: {mod}")
        except ImportError as e:
            print(f"  FAIL: {mod} -> {e}")
            all_ok = False
    return all_ok


def check_ai_settings() -> bool:
    print("\n[5/5] Checking AI settings...")
    try:
        from ai.config.settings import ai_settings, get_ai_settings

        s = get_ai_settings()
        print(f"  OK: AI settings loaded")
        print(f"  ai_copilot_enabled: {s.ai_copilot_enabled}")
        print(f"  ollama_host: {s.ollama_host}")
        print(f"  llm_model: {s.llm_model}")
        print(f"  embedding_model: {s.embedding_model}")
        print(f"  chromadb_persist_path: {s.chromadb_persist_path}")
        print(f"  duckdb_path: {s.duckdb_path}")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Bootstrap AI Infrastructure")
    parser.add_argument(
        "--pull-models",
        action="store_true",
        help="Pull required Ollama models (qwen2.5:7b, nomic-embed-text)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("AI Infrastructure Bootstrap")
    print("=" * 50)

    results = [
        ("Ollama Runtime", check_ollama()),
        ("ChromaDB", check_chromadb()),
        ("DuckDB", check_duckdb()),
        ("AI Imports", check_imports()),
        ("AI Settings", check_ai_settings()),
    ]

    if args.pull_models:
        pull_models(["qwen2.5:7b", "nomic-embed-text"])

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    all_pass = True
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {name}")

    if all_pass:
        print("\nAll checks passed. AI infrastructure is ready.")
    else:
        print("\nSome checks failed. See messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
