from __future__ import annotations

import json
from pathlib import Path


def test_lifecycle_snapshot_selector_uses_configured_baostock_cache(tmp_path, monkeypatch):
    from scripts import build_v4_dm01_lifecycle_snapshot as lifecycle

    cache = tmp_path / "relocated-cache"
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text(
        f'baostock:\n  cache_root: "{cache.as_posix()}"\n', encoding="utf-8"
    )
    monkeypatch.setattr(lifecycle, "ROOT", tmp_path)
    day = "2026-10-16"
    snapshot_id = "sha256-" + "a" * 64
    folder = cache / "baostock" / day.replace("-", "") / snapshot_id
    folder.mkdir(parents=True)
    record = {
        "trade_date": day,
        "provider_date": day,
        "status": "BAOSTOCK_DAILY_SNAPSHOT_READY",
        "daily_rows": [{"code": "sh.600000"}],
        "adjustment_factor_rows": [],
        "snapshot_id": snapshot_id,
    }
    path = folder / "daily_update.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    assert lifecycle.select_baostock_snapshot(day, snapshot_id) == (record, path)


def test_dm01_freeze_and_daily_increment_use_central_baostock_cache_resolver():
    root = Path(__file__).resolve().parents[2]
    freeze = (root / "scripts/freeze_v4_dm01_daily_sources.py").read_text(encoding="utf-8")
    increment = (root / "scripts/run_v4_dm01_daily_increment.py").read_text(encoding="utf-8")
    assert "resolve_baostock_cache_root(ROOT)" in freeze
    assert "resolve_baostock_cache_root(ROOT)" in increment
    assert "data/v4/source_snapshots/baostock" not in freeze
    assert "data/v4/source_snapshots/baostock" not in increment
