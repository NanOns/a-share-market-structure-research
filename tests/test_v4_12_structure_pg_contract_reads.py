import hashlib
import json


def test_frozen_structure_contracts_read_exact_pg_bytes_only(monkeypatch, tmp_path):
    from workbench_analysis.v4_12_structure_io import FrozenContracts, _ENTRY_SOURCE_ID

    def binding(path, value):
        raw = json.dumps(value, sort_keys=True).encode()
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw)}, raw

    config_ref, config_raw = binding(
        "config/v4_12_time_counter_contract_v2.json",
        {"contract_id": "V4_12_SESSION_COUNTER_V2"},
    )
    frozen = [config_ref]
    acceptance_ref, acceptance_raw = binding(
        "reports/v4_12/V4_12_CONTRACT_FREEZE_EXTERNAL_ACCEPTANCE_R1.json",
        {"external_audit_status": "PASS_V4_12_CONTRACT_FREEZE",
         "frozen_contracts": frozen},
    )
    entry = {
        "scope": "V4_12_D1_ENGINEERING_RUNTIME_R1",
        "scoped_engineering_implementation_permission": True,
        "contract_freeze_acceptance": acceptance_ref,
        "frozen_contracts": frozen,
        "production_permission": False,
        "shadow_production_permission": False,
        "focus_cutover_permission": False,
        "global_mandatory_adoption": False,
        "D2_integration_permission": False,
        "DB_migration_permission": False,
    }
    entry_raw = json.dumps(entry, sort_keys=True).encode()
    entry_record = {
        "source_path": "reports/v4_12/V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json",
        "source_sha256": hashlib.sha256(entry_raw).hexdigest(),
        "source_bytes": len(entry_raw),
    }
    sources = {
        config_ref["path"]: config_raw,
        acceptance_ref["path"]: acceptance_raw,
    }

    def read_source(root, source_id):
        assert source_id == _ENTRY_SOURCE_ID
        return {"record": entry_record, "raw": entry_raw}

    def read_bound(root, path, sha):
        raw = sources[path]
        assert hashlib.sha256(raw).hexdigest() == sha
        return {"raw": raw}

    monkeypatch.setattr(
        "workbench_db.v4_historical_source_ingress_pg_r1.read_source", read_source
    )
    monkeypatch.setattr(
        "workbench_db.v4_historical_source_ingress_pg_r1.read_bound", read_bound
    )
    monkeypatch.setattr(
        "pathlib.Path.read_bytes",
        lambda _path: (_ for _ in ()).throw(AssertionError("workspace read")),
    )

    contracts = FrozenContracts(tmp_path)
    assert contracts.config["time_counter_contract"]["contract_id"] == "V4_12_SESSION_COUNTER_V2"
    assert contracts.entry_ref["sha256"] == entry_record["source_sha256"]
