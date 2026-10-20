import json


def test_special_phase_runner_reads_and_appends_date_bound_pg_stage(monkeypatch, tmp_path, capsys):
    from scripts import build_v4_dm01_special_phase_manifest as module
    from workbench_analysis import dm01_runtime_r4
    from workbench_db import v4_dm01_stage_state_pg_r1 as stage_state

    day = "2026-10-16"
    lifecycle = {"contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1", "trade_date": day,
                 "status": "READY", "active_security_ids": ["sid-1"]}
    binding = {"contract_id": stage_state.CONTRACT, "trade_date": day,
               "stage": "lifecycle_snapshot", "binding": {"path": "stage.pg.json", "sha256": "a" * 64, "bytes": 1}}
    v402_binding = {"contract_id": "V4_DM01_V402_ACCEPTANCE_INGRESS_R1", "trade_date": day,
                    "stage": "v402_acceptance", "binding": {"path": "v402.pg.json", "sha256": "c" * 64, "bytes": 3}}
    appended = []
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(dm01_runtime_r4, "session_gate", lambda *_: {"status": "WAIT_MARKET_CLOSE"})
    def read_stage(_root, _binding, *, stage, **_kwargs):
        return lifecycle if stage == "lifecycle_snapshot" else {
            "contract_id": "V4_DM01_V402_ACCEPTANCE_INGRESS_R1", "trade_date": day,
            "acceptance": {}, "stage_manifest": {}, "acceptance_source_sha256": "d" * 64,
            "stage_manifest_source_sha256": "e" * 64,
        }
    monkeypatch.setattr(stage_state, "read_stage", read_stage)
    monkeypatch.setattr(stage_state, "append_stage", lambda root, date, stage, payload:
                        appended.append((root, date, stage, payload)) or
                        {"contract_id": stage_state.CONTRACT, "trade_date": date, "stage": stage,
                         "binding": {"path": "next.pg.json", "sha256": "b" * 64, "bytes": 2}})
    monkeypatch.setattr("sys.argv", ["build_v4_dm01_special_phase_manifest.py", "--target-date", day,
                                      "--lifecycle-pg-stage-state", json.dumps(binding),
                                      "--v402-pg-stage-state", json.dumps(v402_binding)])

    assert module.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "WAIT_MARKET_CLOSE"
    assert output["pg_stage_state"]["stage"] == "special_phase_manifest"
    assert appended[0][1:3] == (day, "special_phase_manifest")
    assert not list(tmp_path.rglob("reports/v4_dm01/*"))
