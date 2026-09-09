import json
from pathlib import Path

import duckdb
import pytest

from workbench_ops import ConfigConflict, ConfigValidationError, OperationsConfig


def setup(root: Path):
    (root / "config").mkdir(parents=True)
    (root / "config/paths.yaml").write_text('tdx:\n  root: "D:/new_tdx"\n', encoding="utf-8")
    db = root / "data/database/market_research.duckdb"
    db.parent.mkdir(parents=True)
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE config_versions (config_revision VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
    return OperationsConfig(root, db)


def test_draft_validate_apply_and_version_conflict(tmp_path):
    config = setup(tmp_path)
    assert config.validate({"query_page_size": 100})["valid"]
    applied = config.apply({"query_page_size": 100}, expected_revision=None)
    assert applied["config"]["query_page_size"] == 100
    assert json.loads((tmp_path / "runtime/operations_config.json").read_text("utf-8"))["revision"] == applied["revision"]
    with pytest.raises(ConfigConflict, match="CONFIG_REVISION_CONFLICT"):
        config.apply({"query_page_size": 101}, expected_revision=None)


def test_config_file_rolls_back_when_version_persistence_fails(tmp_path, monkeypatch):
    config=setup(tmp_path)
    first=config.apply({"query_page_size":100},expected_revision=None)
    before=(tmp_path/"runtime/operations_config.json").read_bytes()
    def fail_connect(*args,**kwargs): raise RuntimeError("DB_WRITE_FAILED")
    monkeypatch.setattr("workbench_ops.config.duckdb.connect",fail_connect)
    with pytest.raises(RuntimeError,match="DB_WRITE_FAILED"):
        config.apply({"query_page_size":101},expected_revision=first["revision"])
    assert (tmp_path/"runtime/operations_config.json").read_bytes()==before


@pytest.mark.parametrize("draft,code", [
    ({"retention_successful_days": 2}, "CONFIG_RETENTION_MINIMUM_THREE_DAYS"),
    ({"managed_write_roots": ["D:/new_tdx/cache"]}, "CONFIG_TDX_WRITE_FORBIDDEN"),
    ({"managed_write_roots": ["C:/" ]}, "CONFIG_PROTECTED_ROOT"),
    ({"unknown": 1}, "CONFIG_UNKNOWN_KEYS"),
])
def test_invalid_or_unsafe_drafts_are_blocked(tmp_path, draft, code):
    with pytest.raises(ConfigValidationError, match=code):
        setup(tmp_path).validate(draft)
