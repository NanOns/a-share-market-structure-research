from pathlib import Path
import hashlib
import json
import pytest

from v4.contracts import phase0_gate


def _accepted_package_fixture():
    package_id, package_sha, fact_digest, revision_id = "fixture-package", "a" * 64, "b" * 64, "fixture-revision"
    target = "2026-09-11"
    coverage = {
        "boards": list(phase0_gate.TDX_BOARD_SCOPES),
        "counts": {board: 1 for board in phase0_gate.TDX_BOARD_SCOPES},
        "target_trade_date": target,
        "digest": fact_digest,
    }
    locator = {"boards": coverage["boards"], "counts": coverage["counts"],
               "target_trade_date": target}
    binding = {
        "source_key": "tdx_board_coverage", "logical_fact_id": "fixture-coverage",
        "fact_digest": fact_digest, "source_fact_sha256": "e" * 64,
        "record_locator": locator, "record_count": 4, "byte_count": 128,
    }
    manifest = {
        "package_id": package_id, "package_sha256": package_sha, "trade_date": target,
        "accepted_scope": "ACCEPTED_SOURCE_PACKAGE", "AS_RECORDED": True,
        "PIT_ELIGIBLE": True, "acceptance_proof": {"issuer_id": "fixture", "receipt_sha256": "c" * 64},
        "source_fact_bindings": [binding], "accepted_board_coverage": coverage,
        "tdx_source_packages": [{
            "source_role": "OFFICIAL_CURRENT_PACKAGE", "T0": target,
            "provider_package_date": target, "first_available_at": "2026-09-11T08:00:00+08:00",
            "package_sha256": "d" * 64, "package_bytes": 100, "source_revision_number": 1,
            "AS_RECORDED": False, "PIT_ELIGIBLE": False,
        }],
    }
    package = {"package_id": package_id, "package_sha256": package_sha,
               "target_trade_date": target, "accepted_scope": "ACCEPTED_SOURCE_PACKAGE",
               "manifest": manifest}
    facts = [{
        **binding, "source_revision_id": revision_id, "revision_no": 1,
        "digest": fact_digest, "source_package_id": package_id,
        "source_package_source_key": "tdx_board_coverage", "source_fact_digest": fact_digest,
        "observed_at": "2026-09-11T08:00:00+08:00", "ingested_at": "2026-09-11T08:01:00+08:00",
        "system_available_at": "2026-09-11T08:02:00+08:00",
    }]
    return package, facts


def _raw_receipt_fixture(package, facts):
    package_id = package["package_id"]
    digest = package["package_sha256"]
    revision = facts[0]
    receipt = {
        "receipt_id": "fixture-raw-receipt", "owner": "V4-00E",
        "status": "ACCEPTED", "scope": "RAW_BOOTSTRAP",
        "trade_date": package["target_trade_date"], "source_package_id": package_id,
        "source_package_sha256": digest, "source_revision_id": revision["source_revision_id"],
        "source_revision_sha256": revision["digest"], "raw_basis": "TDX_RAW_NATIVE",
        "source_identity_status": "RESOLVED", "source_trading_status": "TRADING",
        "source_knowledge_status": "AS_RECORDED",
        "owner_results": {
            owner: {
                "owner": owner, "status": "DEGRADED_PASS", "accepted_scopes": [scope],
                "trade_date": package["target_trade_date"], "source_package_id": package_id,
                "source_package_sha256": digest, "source_revision_id": revision["source_revision_id"],
            }
            for owner, scope in (("V4-00B", "LIFECYCLE_SCHEMA"),
                                 ("V4-00C", "PUBLICATION_IDENTITY"),
                                 ("V4-00D", "A_STOCK_TDX_SOURCE"))
        },
    }
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(
        receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return receipt


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
        "source_acceptance": {"status": "BLOCKED", "candidate_count": 0,
                              "accepted_candidate_count": 0, "candidate_errors": [],
                              "accepted_evidence": None},
        "raw_bootstrap_receipt": None,
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
        "source_acceptance": {"status": "BLOCKED", "candidate_count": 0,
                              "accepted_candidate_count": 0, "candidate_errors": [],
                              "accepted_evidence": None},
        "raw_bootstrap_receipt": None,
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


def test_accepted_source_package_can_release_d_scope_only_with_bound_four_board_evidence():
    package, facts = _accepted_package_fixture()
    assert phase0_gate._package_acceptance_errors(
        package, facts, acceptance_verified=True,
    ) == []
    package["manifest"]["accepted_board_coverage"]["boards"].remove("STAR")
    errors = phase0_gate._package_acceptance_errors(package, facts, acceptance_verified=True)
    assert "FOUR_BOARD_COVERAGE_UNPROVEN" in errors


def test_raw_bootstrap_receipt_can_release_e_scope_and_bad_bindings_are_rejected():
    package, facts = _accepted_package_fixture()
    source = {"accepted": True, "package": package, "facts": facts}
    receipt = _raw_receipt_fixture(package, facts)
    assert phase0_gate._raw_bootstrap_errors(receipt, source, receipt_verified=True) == []
    receipt["raw_basis"] = "ADJUSTED"
    assert "RAW_RECEIPT_BASIS_MISMATCH" in phase0_gate._raw_bootstrap_errors(
        receipt, source, receipt_verified=True,
    )


def test_raw_bootstrap_receipt_requires_owner_t0_and_source_revision_match():
    package, facts = _accepted_package_fixture()
    source = {"accepted": True, "package": package, "facts": facts}
    receipt = _raw_receipt_fixture(package, facts)
    receipt["trade_date"] = "2026-09-10"
    assert "RAW_RECEIPT_T0_OR_PACKAGE_MISMATCH" in phase0_gate._raw_bootstrap_errors(
        receipt, source, receipt_verified=True,
    )
    receipt = _raw_receipt_fixture(package, facts)
    receipt["owner_results"]["V4-00D"]["source_revision_id"] = "wrong-revision"
    assert "RAW_RECEIPT_OWNER_EVIDENCE_INVALID:V4-00D" in phase0_gate._raw_bootstrap_errors(
        receipt, source, receipt_verified=True,
    )


def test_d_rejects_unaccepted_scope_or_unbound_source_revision():
    package, facts = _accepted_package_fixture()
    package["accepted_scope"] = "DIAGNOSTIC_ONLY"
    assert "PACKAGE_SCOPE_NOT_ACCEPTED" in phase0_gate._package_acceptance_errors(
        package, facts, acceptance_verified=True,
    )
    package, facts = _accepted_package_fixture()
    facts[0]["source_package_source_key"] = "wrong-source"
    assert "PACKAGE_SOURCE_REVISION_BINDING_INVALID" in phase0_gate._package_acceptance_errors(
        package, facts, acceptance_verified=True,
    )


@pytest.mark.parametrize(("field", "value", "expected_error"), [
    ("source_identity_status", "UNKNOWN", "RAW_RECEIPT_SOURCE_IDENTITY_UNRESOLVED"),
    ("source_trading_status", "SUSPENDED", "RAW_RECEIPT_SOURCE_NOT_TRADING"),
    ("source_knowledge_status", "POST_EVENT", "RAW_RECEIPT_SOURCE_KNOWLEDGE_NOT_AS_RECORDED"),
    ("owner", "V4-00D", "RAW_RECEIPT_OWNER_OR_STATUS_INVALID"),
    ("source_revision_sha256", "f" * 64, "RAW_RECEIPT_SOURCE_REVISION_MISMATCH"),
])
def test_e_rejects_unknown_suspended_post_event_and_wrong_owner_or_revision(field, value, expected_error):
    package, facts = _accepted_package_fixture()
    receipt = _raw_receipt_fixture(package, facts)
    receipt[field] = value
    errors = phase0_gate._raw_bootstrap_errors(
        receipt, {"accepted": True, "package": package, "facts": facts}, receipt_verified=True,
    )
    assert expected_error in errors


def test_missing_raw_receipt_producer_is_reported_explicitly():
    assert phase0_gate._raw_bootstrap_errors(None, {"accepted": False}) == [
        "MISSING_RUNTIME_RECEIPT_PRODUCER",
    ]


def test_raw_bootstrap_self_hash_does_not_establish_authority():
    package, facts = _accepted_package_fixture()
    receipt = _raw_receipt_fixture(package, facts)
    errors = phase0_gate._raw_bootstrap_errors(
        receipt, {"accepted": True, "package": package, "facts": facts},
    )
    assert "RAW_RECEIPT_AUTHORITY_NOT_VERIFIED" in errors




def test_missing_pg_relation_is_reported_as_acceptance_gap(monkeypatch):
    monkeypatch.setattr(phase0_gate, "_pg_snapshot", lambda: {
        "database_identity": {"database": "market_research"}, "read_role": {"role": "test"},
        "catalog": {name: name != "source_packages" for name in phase0_gate.STAGE00_TABLES},
        "catalog_missing": ["source_packages"], "contracts": {},
        "missing_contract_versions": list(phase0_gate.STAGE00_CONTRACTS),
        "source_revision_count": 3, "accepted_source_package_count": None,
        "publication_head_count": 0, "model_namespace_count": 1,
        "raw_bootstrap": {"status": "UNKNOWN", "reason": "SOURCE_PACKAGE_RELATION_MISSING"},
        "source_acceptance": {"status": "UNKNOWN", "candidate_count": 0, "accepted_candidate_count": 0, "candidate_errors": ["SOURCE_ACCEPTANCE_RELATION_MISSING:source_packages"], "accepted_evidence": None},
        "raw_bootstrap_receipt": None,
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


def test_valid_d_and_e_fixtures_make_gate_authorization_path_reachable():
    package, facts = _accepted_package_fixture()
    source_errors = phase0_gate._package_acceptance_errors(package, facts, acceptance_verified=True)
    source = {"status": "ACCEPTED", "candidate_count": 1, "accepted_candidate_count": 1,
              "candidate_errors": source_errors, "accepted_evidence": {
                  "accepted": True, "package": package, "facts": facts,
              }}
    raw_errors = phase0_gate._raw_bootstrap_errors(
        _raw_receipt_fixture(package, facts), source["accepted_evidence"], receipt_verified=True,
    )
    stages = {stage: {"status": "FULL_PASS"} for stage in phase0_gate.STAGES}
    stages["V4-00B"] = {"status": "FULL_PASS", "allowed_capabilities": ["LIFECYCLE_SCHEMA"]}
    stages["V4-00C"] = {"status": "FULL_PASS", "allowed_capabilities": ["PUBLICATION_IDENTITY"]}
    stages["V4-00D"] = phase0_gate._source_owner_stage(source, True, {"valid_sample_count": 4})
    stages["V4-00E"] = phase0_gate._raw_owner_stage(raw_errors)
    result = phase0_gate.evaluate_phase0(stages)
    assert result["stages"]["V4-00D"]["allowed_capabilities"] == ["A_STOCK_TDX_SOURCE"]
    assert result["stages"]["V4-00E"]["allowed_capabilities"] == ["RAW_BOOTSTRAP"]
    assert result["v4_01_entry_permission"] == "AUTHORIZED"
