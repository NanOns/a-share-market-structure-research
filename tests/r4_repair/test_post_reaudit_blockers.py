from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import run_live_forward
import run_r3_integrated_seal
from forward.live import latest_revision, publish_observation


ROOT = Path(__file__).resolve().parents[2]


def _copy_seal_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fixture"
    shadow = Path("reports/shadow/v2/20260904")
    shutil.copytree(ROOT / shadow, root / shadow)
    for relative in ("reports/current/CURRENT_RELEASE.json", "reports/phase1/PHASE1_FINAL_RECEIPT.json"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    for relative in run_r3_integrated_seal.FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return root


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_suffix(".audit.tmp")
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), temporary, compression="zstd")
    temporary.replace(path)


def test_integrated_seal_accepts_unmodified_bound_artifacts(tmp_path, monkeypatch):
    root = _copy_seal_fixture(tmp_path)
    monkeypatch.setattr(run_r3_integrated_seal, "ROOT", root)

    result = run_r3_integrated_seal.run()

    assert result["chain_pass"] is True
    assert result["membership"] is True
    assert result["identity"] == "cb3bdd356f01dfaad5990a393a44d10149cf81f9805c533219124d773aad8c94"


def test_forward_cli_block_does_not_overwrite_committed_revision(tmp_path, monkeypatch):
    row = {
        "security_id": "SH.600000", "candidate_state": "NEW",
        "shadow_research_band": "CORE_RESEARCH", "steady_queue_tier": "CORE",
        "pullback_queue_tier": None, "breakout_queue_tier": None,
        "leader_queue_tier": None, "early_queue_tier": None,
    }
    frame = pd.DataFrame([row])
    publish_observation(tmp_path, "20260904", 1, frame, {"observation_id": "sealed"}, {"outcomes": {}})
    receipt = tmp_path / "reports/forward/20260904/revision_1/DAILY_FORWARD_CAPTURE_RECEIPT.json"
    before = receipt.read_bytes()
    monkeypatch.setattr(run_live_forward, "ROOT", tmp_path)
    monkeypatch.setattr(run_live_forward, "run", lambda *_: (1, {"status": "BLOCKED", "stage": "MODEL_IDENTITY_PREFLIGHT", "error": "MODEL_VERSION_CHANGED"}))
    monkeypatch.setattr(sys, "argv", ["run_live_forward.py", "--date", "latest"])

    assert run_live_forward.main() == 1
    assert receipt.read_bytes() == before
    assert latest_revision(tmp_path, "20260904").name == "revision_1"
    assert json.loads((tmp_path / "runtime/forward/LAST_BLOCKED_RUN.json").read_text())["stage"] == "MODEL_IDENTITY_PREFLIGHT"


@pytest.mark.parametrize("mutation", ["swapped_classes", "duplicate_membership"])
def test_integrated_seal_rejects_artifact_or_membership_mutation(tmp_path, monkeypatch, mutation):
    root = _copy_seal_fixture(tmp_path)
    shadow = root / "reports/shadow/v2/20260904"
    if mutation == "swapped_classes":
        path = shadow / "steady_trend/STEADY_TREND_V2_SHADOW.parquet"
        frame = pq.read_table(path).to_pandas()
        left = frame.index[frame.v2_steady_class.eq("STEADY_CORE")][0]
        right = frame.index[frame.v2_steady_class.eq("STEADY_ACCEPTABLE")][0]
        frame.loc[[left, right], "v2_steady_class"] = frame.loc[[right, left], "v2_steady_class"].to_numpy()
    else:
        path = shadow / "priority/V2_QUEUE_MEMBERSHIP.parquet"
        frame = pq.read_table(path).to_pandas()
        frame = pd.concat([frame.iloc[1:], frame.iloc[[1]]], ignore_index=True)
    _write_parquet(path, frame)
    monkeypatch.setattr(run_r3_integrated_seal, "ROOT", root)

    with pytest.raises(RuntimeError, match="R3_INTEGRATED_SEAL_PRECONDITIONS_FAILED"):
        run_r3_integrated_seal.run()
    receipt = json.loads((shadow / "integrated/R3_INTEGRATED_SEAL_RECEIPT.json").read_text())
    assert receipt["final_status"] == "BLOCKED"


def test_entrypoint_threshold_change_is_a_model_change(tmp_path):
    root = _copy_seal_fixture(tmp_path)
    path = root / "run_sector_leader_v2.py"
    source = path.read_text(encoding="utf8")
    assert ">=.70" in source
    path.write_text(source.replace(">=.70", ">=.99"), encoding="utf8")

    with pytest.raises(RuntimeError, match="MODEL_VERSION_CHANGED:run_sector_leader_v2.py"):
        run_live_forward.ProductionServices().model_identity(root)
