import json
import sys


def test_lifecycle_entrypoint_appends_stage_payload_to_pg(monkeypatch, tmp_path, capsys):
    from scripts import build_v4_dm01_lifecycle_snapshot as lifecycle
    from workbench_analysis import dm01_runtime_r4
    from workbench_db import v4_dm01_stage_state_pg_r1 as state

    monkeypatch.setattr(lifecycle, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["build_v4_dm01_lifecycle_snapshot", "--target-date", "2026-10-16"])
    monkeypatch.setattr(dm01_runtime_r4, "session_gate", lambda *a, **k: {"status": "WAIT_MARKET_CLOSE"})
    calls = []

    def append(root, day, stage, payload):
        calls.append((root, day, stage, payload))
        return {"contract_id": state.CONTRACT, "trade_date": day, "stage": stage,
                "binding": {"path": "data/v4/lifecycle.pg.json", "sha256": "a" * 64, "bytes": 1}}

    monkeypatch.setattr(state, "append_stage", append)

    assert lifecycle.main() == 0
    output = json.loads(capsys.readouterr().out)

    assert calls[0][1:3] == ("2026-10-16", "lifecycle_snapshot")
    assert calls[0][3]["status"] == "WAIT_MARKET_CLOSE"
    assert output["pg_stage_state"]["stage"] == "lifecycle_snapshot"
