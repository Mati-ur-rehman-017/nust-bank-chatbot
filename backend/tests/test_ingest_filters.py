"""Tests for ingestion file filtering rules."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ollama_base_url", "http://localhost:11434")
os.environ.setdefault("ollama_model", "dummy-model")
os.environ.setdefault("chroma_path", "./chroma_db")
os.environ.setdefault("embedding_model", "dummy-embedding")
os.environ.setdefault("api_host", "127.0.0.1")
os.environ.setdefault("api_port", "8000")
os.environ.setdefault("log_level", "INFO")
os.environ.setdefault("max_input_length", "1024")
os.environ.setdefault("rate_limit_per_minute", "60")

from scripts.ingest_data import should_ingest_file


def test_should_skip_libreoffice_lock_file() -> None:
    assert should_ingest_file(Path(".~lock.NUST Bank-Product-Knowledge.xlsx#")) is False


def test_should_skip_hidden_files() -> None:
    assert should_ingest_file(Path(".DS_Store")) is False


def test_should_allow_supported_extensions() -> None:
    assert should_ingest_file(Path("qa.json")) is True
    assert should_ingest_file(Path("NUST Bank-Product-Knowledge.xlsx")) is True
    assert should_ingest_file(Path("notes.txt")) is True
