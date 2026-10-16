from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db import v4_native


def test_reader_reuses_existing_workbench_dsn_without_new_config(monkeypatch):
    monkeypatch.delenv("V4_NATIVE_PG_READER_DSN", raising=False)
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://reader@example.invalid/market_research"
    with pytest.raises(RuntimeError, match="V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK"):
        v4_native.configured_dsn()


def test_explicit_reader_and_native_dsn_take_precedence(monkeypatch):
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://default@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://native@example.invalid/market_research")
    monkeypatch.setenv("V4_NATIVE_PG_READER_DSN", "postgresql://readonly@example.invalid/market_research")

    assert v4_native.configured_reader_dsn() == "postgresql://readonly@example.invalid/market_research"
    monkeypatch.delenv("V4_NATIVE_PG_READER_DSN")
    assert v4_native.configured_reader_dsn() == "postgresql://native@example.invalid/market_research"


def test_writer_dsn_does_not_fall_back_to_workbench_reader_source(monkeypatch):
    monkeypatch.delenv("V4_NATIVE_PG_DSN", raising=False)
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")

    with pytest.raises(RuntimeError, match="V4_NATIVE_PG_DSN_REQUIRED_NO_FALLBACK"):
        v4_native.configured_dsn()
