from __future__ import annotations


def test_baostock_daily_capture_uses_pg_registered_source_contract(monkeypatch):
    from scripts import capture_baostock_daily_update as capture
    from workbench_analysis import operational_daily_executor_v1 as executor

    calls = []
    expected = {"contract_id": "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", "contract_version": "1.1.0",
                "dm01_daily_updates": {"runtime_acceptance_contract": "BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1"}}

    def registered(root, contract_id, version, path):
        calls.append((root, contract_id, version, path))
        return expected

    monkeypatch.setattr(executor, "_daily_runtime_contract", registered)
    assert capture.load_source_contract("project-root") == expected
    assert calls == [("project-root", "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", "1.1.0",
                      "config/baostock_supplemental_contract_v1.json")]


def test_dm01_daily_orchestrator_calls_pg_appending_runtime_acceptor(monkeypatch, tmp_path):
    import json
    from scripts import run_v4_dm01_daily_increment as daily

    monkeypatch.setattr(daily, "ROOT", tmp_path)
    observed = []

    def run_cli(*args):
        observed.append(args)
        if args[0] == "scripts/accept_dynamic_daily_baostock_v2.py":
            return 0, {"status": "ACCEPTED", "pg_acceptance": {"contract_id": "V4_BAOSTOCK_RUNTIME_ACCEPTANCE_PG_R1"}}
        if args[0] == "scripts/capture_baostock_daily_update.py":
            return 0, {"status": "BAOSTOCK_DAILY_SNAPSHOT_READY", "snapshot_id": "sha256-capture"}
        raise AssertionError(args)

    monkeypatch.setattr(daily, "_run_json_cli", run_cli)
    monkeypatch.setattr(daily, "_runtime_acceptance", lambda day: ({"status": "ACCEPTED"}, None))
    snapshot = tmp_path / "data/v4/source_snapshots/baostock/20261016/sha256-capture/daily_update.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(json.dumps({"trade_date": "2026-10-16"}), encoding="utf-8")

    rows, smoke, error = daily._run_baostock_daily_capture("2026-10-16")

    assert error is None
    assert rows["trade_date"] == "2026-10-16"
    assert smoke["pg_acceptance"]["contract_id"] == "V4_BAOSTOCK_RUNTIME_ACCEPTANCE_PG_R1"
    assert observed[0] == ("scripts/accept_dynamic_daily_baostock_v2.py", "--target-date", "2026-10-16")
