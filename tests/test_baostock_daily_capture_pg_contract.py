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
