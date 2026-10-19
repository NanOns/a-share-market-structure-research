from pathlib import Path

from v4.contracts import phase0_gate


def test_fixture_test_runs_pure_gate_only():
    result = phase0_gate.fixture_test_result()
    assert result == {
        "run_mode": "fixture-test", "execution_status": "OK",
        "fixture_test_status": "PASS", "phase0_status": "BLOCKED",
        "v4_01_entry_permission": "BLOCKED", "side_effects": "NONE",
        "scope": "PURE_GATE_RULES_ONLY",
    }


def test_missing_tdx_root_is_execution_failure(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(phase0_gate, "_pg_snapshot", lambda: {
        "database_identity": {"database": "market_research"}, "read_role": {"role": "test"},
        "catalog": {}, "catalog_missing": ["source_packages"], "contracts": {},
        "missing_contract_versions": list(phase0_gate.STAGE00_CONTRACTS),
        "source_revision_count": None, "accepted_source_package_count": None,
        "publication_head_count": None, "model_namespace_count": None,
        "raw_bootstrap": {"status": "UNKNOWN", "reason": "SOURCE_PACKAGE_RELATION_MISSING"},
    })
    result = phase0_gate.run_stage00_diagnostic(mode="doctor", tdx_root=str(tmp_path / "absent"))
    assert result["execution_status"] == "FAILED"
    assert result["phase0_status"] == "BLOCKED"
    assert result["side_effects"] == "NONE"


def test_diagnostic_execution_and_acceptance_status_are_separate(monkeypatch):
    monkeypatch.setattr(phase0_gate, "_pg_snapshot", lambda: {
        "database_identity": {"database": "market_research"}, "read_role": {"role": "test"},
        "catalog": {name: True for name in phase0_gate.STAGE00_TABLES}, "catalog_missing": [],
        "contracts": {name: {"version": version, "status": "MISSING", "reason": "V4_PG_CONTRACT_VERSION_NOT_FOUND"}
                      for name, version in phase0_gate.STAGE00_CONTRACTS.items()},
        "missing_contract_versions": list(phase0_gate.STAGE00_CONTRACTS),
        "source_revision_count": 3, "accepted_source_package_count": 0,
        "publication_head_count": 0, "model_namespace_count": 1,
        "raw_bootstrap": {"status": "NOT_PRESENT", "reason": "NO_ACCEPTED_SOURCE_PACKAGE"},
    })
    monkeypatch.setattr(phase0_gate, "_tdx_root", lambda *_: Path("G:/unused"))
    monkeypatch.setattr(phase0_gate, "_read_tdx_samples", lambda _: {
        "root": "G:/unused", "sample_count": 4, "valid_sample_count": 4,
        "tdx_observation_date": "20260911", "samples": [], "failures": [],
    })
    result = phase0_gate.run_stage00_diagnostic()
    assert result["execution_status"] == "OK"
    assert result["phase0_status"] == "BLOCKED"
    assert result["v4_01_entry_permission"] == "BLOCKED"
    assert result["stages"]["V4-00C"]["status"] == "DEGRADED_PASS"
    assert result["stages"]["V4-00C"]["reason_codes"] == ["NO_HEAD_PRESENT"]
    assert result["side_effects"] == "NONE"




def test_missing_pg_relation_is_reported_as_acceptance_gap(monkeypatch):
    monkeypatch.setattr(phase0_gate, "_pg_snapshot", lambda: {
        "database_identity": {"database": "market_research"}, "read_role": {"role": "test"},
        "catalog": {name: name != "source_packages" for name in phase0_gate.STAGE00_TABLES},
        "catalog_missing": ["source_packages"], "contracts": {},
        "missing_contract_versions": list(phase0_gate.STAGE00_CONTRACTS),
        "source_revision_count": 3, "accepted_source_package_count": None,
        "publication_head_count": 0, "model_namespace_count": 1,
        "raw_bootstrap": {"status": "UNKNOWN", "reason": "SOURCE_PACKAGE_RELATION_MISSING"},
    })
    monkeypatch.setattr(phase0_gate, "_tdx_root", lambda *_: Path("G:/unused"))
    monkeypatch.setattr(phase0_gate, "_read_tdx_samples", lambda _: {
        "root": "G:/unused", "sample_count": 4, "valid_sample_count": 4,
        "tdx_observation_date": "20260911", "samples": [], "failures": [],
    })
    result = phase0_gate.run_stage00_diagnostic()
    assert result["execution_status"] == "OK"
    assert result["pg_catalog_missing"] == ["source_packages"]
    assert result["real_source_acceptance"] == "UNKNOWN"
    assert result["phase0_status"] == "BLOCKED"
