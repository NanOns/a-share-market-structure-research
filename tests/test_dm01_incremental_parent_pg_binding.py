from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis import dm01_incremental_component_builders as builders
from workbench_db import dm01_data_accepted_head_pg_r1 as data_head


def test_real_incremental_parent_binds_to_current_pg_head(monkeypatch, tmp_path):
    current = {
        "candidate": {"contract_id": "V4_DATA_ACCEPTED_HEAD_V2", "accepted_trade_date": "2026-09-30"},
        "head_sha256": "a" * 64,
    }
    monkeypatch.setattr(data_head, "read_current", lambda root: current)
    parent = {
        "head": current["candidate"],
        "binding": {
            "path": "data/v4/V4_DATA_ACCEPTED_HEAD.json",
            "sha256": current["head_sha256"],
        },
    }

    assert builders._require_current_pg_data_parent(tmp_path, parent) is current


@pytest.mark.parametrize("field,value", [
    ("sha256", "b" * 64),
    ("path", "data/v4/archived_head.json"),
])
def test_real_incremental_parent_rejects_stale_or_wrong_pg_binding(monkeypatch, tmp_path, field, value):
    current = {
        "candidate": {"contract_id": "V4_DATA_ACCEPTED_HEAD_V2", "accepted_trade_date": "2026-09-30"},
        "head_sha256": "a" * 64,
    }
    monkeypatch.setattr(data_head, "read_current", lambda root: current)
    parent = {
        "head": current["candidate"],
        "binding": {
            "path": "data/v4/V4_DATA_ACCEPTED_HEAD.json",
            "sha256": current["head_sha256"],
        },
    }
    parent["binding"][field] = value

    with pytest.raises(builders.ComponentBuildError, match="REAL_PARENT_MUST_BE_CURRENT_ACCEPTED_HEAD"):
        builders._require_current_pg_data_parent(tmp_path, parent)
