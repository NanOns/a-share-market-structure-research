import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from v4.contracts import phase0_gate
from workbench_db import v4_daily_source_ingest_r6 as ingest


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


_DEFAULT_SECURITIES = [
    ("SH.600001", "SH_MAIN"), ("SH.600002", "SH_MAIN"),
    ("SZ.000001", "SZ_MAIN"), ("SZ.000002", "SZ_MAIN"),
    ("SZ.300001", "CHINEXT"), ("SZ.300002", "CHINEXT"),
    ("SH.688001", "STAR"), ("SH.688002", "STAR"),
]


def _universe_document(day, securities):
    rows = []
    for key, board in securities:
        exchange = "SSE" if key.startswith("SH.") else "BSE" if key.startswith("BJ.") else "SZSE"
        code = key.split(".", 1)[1]
        rows.append({
            "security_id": key, "source_security_key": key,
            "asset_class": "COMMON_STOCK", "share_class": "A",
            "exchange": exchange, "status": "ACTIVE", "source_id": "TDX_SECURITY_MASTER",
            "board_scope": board,
        })
    normalized = [{key: row[key] for key in (
        "security_id", "asset_class", "share_class", "exchange", "status", "source_id",
    )} for row in rows]
    digest = hashlib.sha256(_canonical({
        "contract_id": "V4_MARKET_UNIVERSE_COMPLETENESS_R1", "contract_version": "1.0.0",
        "trade_date": day, "universe_id": "fixture-universe",
        "exchange_scope": ["BSE", "SSE", "SZSE"],
        "securities": sorted(normalized, key=lambda row: row["security_id"]),
    })).hexdigest()
    return {
        "contract_id": "V4_MARKET_UNIVERSE_COMPLETENESS_R1", "trade_date": day,
        "universe_id": "fixture-universe", "exchange_scope": ["SSE", "SZSE", "BSE"],
        "securities": rows, "universe_sha256": digest,
    }


def _signed_fixture(tmp_path, monkeypatch, tdx_bars=None, universe_securities=None):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    registry = {"contract_id": "V4_DAILY_SOURCE_ACCEPTANCE_AUTHORITY_REGISTRY_R1", "status": "ACTIVE",
                "issuers": {"fixture-source-issuer": {"status": "ACTIVE", "capabilities": [
                    "ACCEPT_SOURCE_PACKAGE", "AS_RECORDED", "PIT_ELIGIBLE"],
                    "public_key_b64": base64.b64encode(public).decode()}}}
    monkeypatch.setattr(ingest, "_acceptance_authority_registry", lambda pg=None: registry)
    day = "2026-09-11"

    def write(name, value):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = _canonical(value)
        path.write_bytes(raw)
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

    securities = universe_securities or _DEFAULT_SECURITIES
    bars = tdx_bars or [
        {"trade_date": day, "source_security_key": key, "board_scope": board}
        for key, board in securities
    ]
    for row in bars:
        row.setdefault("open", 10.0)
        row.setdefault("high", 11.0)
        row.setdefault("low", 9.0)
        row.setdefault("close", 10.0)
        row.setdefault("amount", 100.0)
        row.setdefault("volume", 10)
        row.setdefault("source_entry", "fixture/" + row["source_security_key"])
        row.setdefault("entry_sha256", hashlib.sha256(row["source_security_key"].encode()).hexdigest())
    tdx_ref = write("inputs/tdx.json", {"target_session": day, "target_bars": bars})
    bao_ref = write("inputs/bao.json", {"target_date": day, "daily_rows": [], "adjustment_factor_rows": []})
    runtime_ref = write("inputs/runtime.json", {"observed": True})
    universe_doc = (universe_securities if isinstance(universe_securities, dict)
                    else _universe_document(day, securities))
    universe_ref = write("inputs/universe.json", universe_doc)
    freeze = {
        "contract_id": "DYNAMIC_DAILY_SOURCE_FREEZE_V1", "target_session": day,
        "canonical_qfq_authority": "TDX_GBBQ_UNCHANGED", "observed_at": day + "T16:00:00+08:00",
        "AS_RECORDED": True, "PIT_ELIGIBLE": True,
        "tdx": tdx_ref, "native_baostock": bao_ref, "runtime_manifest": runtime_ref,
        "security_universe": universe_ref,
        "effective_package": {
            "provider_package_date": day, "source_revision_number": 1,
            "download": {"sha256": "a" * 64, "bytes": 100},
            "source_transport_v2": {"received_at": day + "T14:00:00+08:00"},
            "zip_validation": {"status": "PASS", "crc_integrity": "PASS"},
        },
    }
    freeze_ref = write("inputs/freeze.json", freeze)
    readiness = {
        "contract_id": "V4_DAILY_SOURCE_READINESS_V2", "trade_date": day,
        "source_freeze": {"sha256": freeze_ref["sha256"]},
        "observed_at": day + "T16:01:00+08:00", "source_ready": True,
        "AS_RECORDED": True, "PIT_ELIGIBLE": True,
    }
    readiness_ref = write("inputs/readiness.json", readiness)
    # Build a first diagnostic plan to obtain its producer-computed descriptor,
    # then independently sign that exact descriptor in the test authority.
    diagnostic = ingest.build_source_ingest_plan(
        tmp_path, trade_date=day, source_freeze=freeze_ref, source_readiness=readiness_ref,
    )
    manifest = diagnostic["package_manifest"]
    receipt_body = {
        "contract_id": ingest.ACCEPTANCE_CONTRACT_ID, "acceptance_id": "fixture-acceptance",
        "trade_date": day, "source_freeze_sha256": manifest["source_freeze_sha256"],
        "source_readiness_sha256": manifest["source_readiness_sha256"],
        "source_fact_bindings_sha256": manifest["source_fact_bindings_sha256"],
        "package_sha256": manifest["package_sha256"], "source_ready": True,
        "readiness_observed_at": manifest["source_readiness_observed_at"],
        "as_recorded": True, "pit_eligible": True, "pit_clock_contract_id": ingest.PIT_CLOCK_CONTRACT_ID,
        "accepted_at": day + "T16:02:00+08:00", "signed_at": day + "T16:03:00+08:00",
        "pit_cutoff_at": day + "T16:04:00+08:00", "trading_calendar_sha256": "f" * 64,
        "decision_session": "T0_AFTER_CLOSE", "issuer_id": "fixture-source-issuer",
    }
    receipt = {**receipt_body,
               "receipt_sha256": hashlib.sha256(_canonical(receipt_body)).hexdigest(),
               "signature_ed25519": base64.b64encode(private.sign(_canonical(receipt_body))).decode()}
    plan = ingest.build_source_ingest_plan(
        tmp_path, trade_date=day, source_freeze=freeze_ref, source_readiness=readiness_ref,
        acceptance_receipt=receipt,
    )
    assert plan["status"] == "ACCEPTED", plan["acceptance_status"]
    return plan, private


def _pg_shaped(plan):
    package = {
        "package_id": plan["package_id"], "package_sha256": plan["package_sha256"],
        "target_trade_date": plan["trade_date"], "accepted_scope": "ACCEPTED_SOURCE_PACKAGE",
        "manifest": plan["package_manifest"],
    }
    facts = []
    for index, fact in enumerate(plan["source_facts"]):
        facts.append({
            **fact, "source_revision_id": f"fixture-revision-{index}", "revision_no": 1,
            "digest": fact["fact_digest"], "source_package_id": plan["package_id"],
            "source_package_source_key": fact["source_key"], "source_fact_digest": fact["fact_digest"],
            "observed_at": plan["package_manifest"]["source_observed_at"],
            "ingested_at": "2026-09-11T16:05:00+08:00", "system_available_at": "2026-09-11T16:06:00+08:00",
        })
    return package, facts


def test_real_source_producer_output_flows_into_stage00_d_and_rejects_tamper(tmp_path, monkeypatch):
    plan, _ = _signed_fixture(tmp_path, monkeypatch)
    package, facts = _pg_shaped(plan)
    assert package["manifest"]["accepted_board_coverage"]["counts"] == {
        "SH_MAIN": 2, "SZ_MAIN": 2, "CHINEXT": 2, "STAR": 2,
    }
    assert phase0_gate._package_acceptance_errors(package, facts, acceptance_verified=True) == []

    bad = {**package, "manifest": dict(package["manifest"])}
    bad["manifest"]["accepted_board_coverage"] = dict(bad["manifest"]["accepted_board_coverage"])
    bad["manifest"]["accepted_board_coverage"]["counts"] = {
        **bad["manifest"]["accepted_board_coverage"]["counts"], "STAR": 0,
    }
    assert "FOUR_BOARD_COVERAGE_UNPROVEN" in phase0_gate._package_acceptance_errors(
        bad, facts, acceptance_verified=True,
    )

    changed = dict(plan)
    changed["package_manifest"] = dict(plan["package_manifest"])
    changed["package_manifest"]["source_fact_bindings"] = [dict(row) for row in plan["package_manifest"]["source_fact_bindings"]]
    changed["package_manifest"]["source_fact_bindings"][-1]["source_fact_sha256"] = "0" * 64
    with pytest.raises(ingest.SourceIngestError, match="SOURCE_FACT_BINDINGS_DIGEST_MISMATCH|PACKAGE_DIGEST_MISMATCH"):
        ingest._verify_independent_acceptance_authority(changed)


def test_tdx_suspension_or_missing_board_cannot_release_d(tmp_path, monkeypatch):
    rows = [
        {"trade_date": "2026-09-11", "source_security_key": key, "board_scope": board}
        for key, board in _DEFAULT_SECURITIES if board != "STAR"
    ]
    with pytest.raises(ingest.SourceIngestError, match="TDX_ACTIVE_A_SHARE_MISSING_AT_T0"):
        _signed_fixture(tmp_path / "missing-board", monkeypatch, tdx_bars=rows)

    securities = [(key, board) for key, board in _DEFAULT_SECURITIES]
    bars = [{"trade_date": "2026-09-11", "source_security_key": key, "board_scope": board}
            for key, board in securities if key != "SH.688001"]
    suspended_universe = _universe_document("2026-09-11", securities)
    next(row for row in suspended_universe["securities"] if row["security_id"] == "SH.688001")["status"] = "SUSPENDED"
    normalized = [{key: row[key] for key in (
        "security_id", "asset_class", "share_class", "exchange", "status", "source_id",
    )} for row in suspended_universe["securities"]]
    suspended_universe["universe_sha256"] = hashlib.sha256(_canonical({
        "contract_id": "V4_MARKET_UNIVERSE_COMPLETENESS_R1", "contract_version": "1.0.0",
        "trade_date": "2026-09-11", "universe_id": "fixture-universe",
        "exchange_scope": ["BSE", "SSE", "SZSE"],
        "securities": sorted(normalized, key=lambda row: row["security_id"]),
    })).hexdigest()
    plan, _ = _signed_fixture(tmp_path / "suspended", monkeypatch, tdx_bars=bars,
                              universe_securities=suspended_universe)
    assert plan["package_manifest"]["accepted_board_coverage"]["suspended_row_count"] == 1


@pytest.mark.parametrize("key", ["SH.510050", "SZ.159915", "SH.900901", "SH.000001"])
def test_non_common_equity_tdx_codes_are_rejected(tmp_path, monkeypatch, key):
    bad = [* _DEFAULT_SECURITIES]
    bad.append((key, "SH_MAIN" if key.startswith("SH.") else "SZ_MAIN"))
    bars = [{"trade_date": "2026-09-11", "source_security_key": code, "board_scope": board}
            for code, board in bad]
    with pytest.raises(ingest.SourceIngestError, match="SECURITY_UNIVERSE_(NON_A_SHARE_OR_BOARD_UNKNOWN|A_SHARE_BOARD_UNKNOWN)"):
        _signed_fixture(tmp_path / key.replace(".", "_"), monkeypatch,
                        tdx_bars=bars, universe_securities=bad)


def test_real_tdx_producer_rejects_invalid_raw_ohlcva(tmp_path, monkeypatch):
    bad = [{"trade_date": "2026-09-11", "source_security_key": key, "board_scope": board}
           for key, board in _DEFAULT_SECURITIES]
    bad[0]["high"] = 8.0
    with pytest.raises(ingest.SourceIngestError, match="TDX_RAW_OHLCVA_RANGE_INVALID"):
        _signed_fixture(tmp_path, monkeypatch, tdx_bars=bad)


def test_complete_universe_may_include_bse_outside_the_four_tdx_boards(tmp_path, monkeypatch):
    securities = [*_DEFAULT_SECURITIES, ("BJ.830001", "BSE")]
    bars = [{"trade_date": "2026-09-11", "source_security_key": key, "board_scope": board}
            for key, board in securities]
    plan, _ = _signed_fixture(tmp_path, monkeypatch, tdx_bars=bars, universe_securities=securities)
    coverage = plan["package_manifest"]["accepted_board_coverage"]
    assert coverage["roster_count"] == 9
    assert coverage["scope_roster_count"] == 8


def test_universe_may_classify_etfs_but_tdx_bars_cannot_include_them(tmp_path, monkeypatch):
    universe = _universe_document("2026-09-11", _DEFAULT_SECURITIES)
    universe["securities"].append({
        "security_id": "SH.510050", "source_security_key": "SH.510050",
        "asset_class": "ETF", "share_class": "NOT_APPLICABLE",
        "exchange": "SSE", "status": "ACTIVE", "source_id": "TDX_SECURITY_MASTER",
    })
    normalized = [{key: row[key] for key in (
        "security_id", "asset_class", "share_class", "exchange", "status", "source_id",
    )} for row in universe["securities"]]
    universe["universe_sha256"] = hashlib.sha256(_canonical({
        "contract_id": "V4_MARKET_UNIVERSE_COMPLETENESS_R1", "contract_version": "1.0.0",
        "trade_date": "2026-09-11", "universe_id": "fixture-universe",
        "exchange_scope": ["BSE", "SSE", "SZSE"],
        "securities": sorted(normalized, key=lambda row: row["security_id"]),
    })).hexdigest()
    bars = [{"trade_date": "2026-09-11", "source_security_key": key, "board_scope": board}
            for key, board in _DEFAULT_SECURITIES]
    plan, _ = _signed_fixture(tmp_path / "listed-only", monkeypatch, tdx_bars=bars,
                              universe_securities=universe)
    assert plan["status"] == "ACCEPTED"
    with pytest.raises(ingest.SourceIngestError, match="TDX_TARGET_SECURITY_OUTSIDE_A_SHARE_ROSTER"):
        _signed_fixture(
            tmp_path / "mixed-bars", monkeypatch,
            tdx_bars=[*bars, {"trade_date": "2026-09-11", "source_security_key": "SH.510050",
                              "board_scope": "SH_MAIN"}],
            universe_securities=universe,
        )


def test_accepted_source_persist_path_verifies_before_first_sql_write(tmp_path, monkeypatch):
    plan, _ = _signed_fixture(tmp_path, monkeypatch)
    authority = ingest._acceptance_authority_registry()
    seen_pg = []
    monkeypatch.setattr(ingest, "_acceptance_authority_registry",
                        lambda pg=None: (seen_pg.append(pg), authority)[1])
    class StopAtSavepoint(Exception):
        pass
    class FakePG:
        def __init__(self): self.calls = []
        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            if sql.startswith("SAVEPOINT"):
                raise StopAtSavepoint
            return self
    fake = FakePG()
    with pytest.raises(StopAtSavepoint):
        ingest.persist_source_ingest_plan(
            fake, plan, publication_id="fixture-publication", publication_revision=1,
            ingested_at="2026-09-11T16:05:00+08:00", system_available_at="2026-09-11T16:06:00+08:00",
        )
    assert fake.calls == [("SAVEPOINT v4_source_ingest_r6", None)]
    assert len(seen_pg) == 2 and all(item is fake for item in seen_pg)

    bad = dict(plan)
    bad["acceptance_receipt"] = {**plan["acceptance_receipt"], "signature_ed25519": base64.b64encode(b"x" * 64).decode()}
    fake = FakePG()
    with pytest.raises(ingest.SourceIngestError, match="RECEIPT_DIGEST_MISMATCH|SIGNATURE_INVALID"):
        ingest.persist_source_ingest_plan(
            fake, bad, publication_id="fixture-publication", publication_revision=1,
            ingested_at="2026-09-11T16:05:00+08:00", system_available_at="2026-09-11T16:06:00+08:00",
        )
    assert fake.calls == []


def test_raw_receipt_is_produced_signed_verified_and_consumed_from_reader_shape(tmp_path, monkeypatch):
    plan, _ = _signed_fixture(tmp_path, monkeypatch)
    package, facts = _pg_shaped(plan)
    source = {"accepted": True, "package": package, "facts": facts}
    raw_key = Ed25519PrivateKey.generate()
    public = raw_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    registry = {"contract_id": ingest.RAW_OWNER_AUTHORITY_CONTRACT_ID, "status": "ACTIVE",
                "issuers": {"fixture-raw-owner": {"status": "ACTIVE",
                    "capabilities": ["SIGN_RAW_OWNER_RECEIPT"], "public_key_b64": base64.b64encode(public).decode()}}}
    seen_pg = []
    monkeypatch.setattr(ingest, "_raw_owner_authority_registry",
                        lambda pg=None: (seen_pg.append(pg), registry)[1])
    tdx = next(row for row in facts if row["source_key"] == "tdx")
    signer = {"issuer_id": "fixture-raw-owner", "sign": lambda raw: base64.b64encode(raw_key.sign(raw)).decode()}
    class FakeReceiptPG:
        def __init__(self): self.receipt = None; self.sha = None; self.query = ""
        def execute(self, sql, params=None):
            self.query = sql
            self.params = params
            return self
        def fetchone(self):
            if "current_database()" in self.query:
                return ("market_research", 1, "127.0.0.1/32", 5432)
            if "to_regclass" in self.query:
                return (self.params[0],)
            return (self.sha,)
        def fetchall(self): return [(self.receipt, self.sha)] if self.receipt else []
    fake_pg = FakeReceiptPG()
    owners = ingest._derive_raw_owner_results(
        fake_pg, source, package, tdx, {"database": "market_research", "database_oid": 1,
                                        "host": "127.0.0.1/32", "port": 5432},
    )
    receipt = ingest.produce_raw_owner_receipt(
        source, owners, signed_at="2026-09-11T16:10:00Z", signer=signer, pg=fake_pg,
    )
    assert ingest.verify_raw_owner_receipt(receipt, pg=fake_pg) == "fixture-raw-owner"
    assert seen_pg and all(item is fake_pg for item in seen_pg)

    old_execute = fake_pg.execute
    def receipt_execute(sql, params=None):
        old_execute(sql, params)
        if sql.startswith("INSERT INTO v4.stage00_raw_owner_receipts"):
            fake_pg.receipt = json.loads(params[5]); fake_pg.sha = params[4]
        return fake_pg
    fake_pg.execute = receipt_execute
    ingest.persist_raw_owner_receipt(fake_pg, receipt)
    loaded, verified = ingest.read_raw_owner_receipt(
        fake_pg, trade_date=plan["trade_date"], source_package_id=plan["package_id"],
        source_revision_id=tdx["source_revision_id"],
    )
    assert verified is True and loaded == receipt
    assert phase0_gate._raw_bootstrap_errors(loaded, source, receipt_verified=verified) == []
    bad = {**receipt, "raw_basis": "ADJUSTED"}
    assert "RAW_RECEIPT_BASIS_MISMATCH" in phase0_gate._raw_bootstrap_errors(bad, source, receipt_verified=True)
    bad_signature = {**receipt, "signature_ed25519": base64.b64encode(b"z" * 64).decode()}
    with pytest.raises(ingest.SourceIngestError, match="DIGEST_MISMATCH|SIGNATURE_INVALID"):
        ingest.verify_raw_owner_receipt(bad_signature)

    fake_owner = {key: dict(value) for key, value in owners.items()}
    fake_owner["V4-00D"]["status"] = "DEGRADED_PASS"
    with pytest.raises(ingest.SourceIngestError, match="RAW_OWNER_INPUT_INVALID:V4-00D"):
        ingest.produce_raw_owner_receipt(
            source, fake_owner, signed_at="2026-09-11T16:10:00Z", signer=signer, pg=fake_pg,
        )


def test_source_acceptance_reverification_uses_supplied_pg_snapshot(tmp_path, monkeypatch):
    plan, _ = _signed_fixture(tmp_path, monkeypatch)
    seen = []
    registry = ingest._acceptance_authority_registry()
    monkeypatch.setattr(ingest, "_acceptance_authority_registry",
                        lambda pg=None: (seen.append(pg), registry)[1])
    sentinel_cursor = object()
    proof = ingest.verify_source_package_manifest_authority(
        plan["package_manifest"], pg=sentinel_cursor,
    )
    assert proof["receipt_sha256"] == plan["package_manifest"]["acceptance_proof"]["receipt_sha256"]
    assert seen == [sentinel_cursor]


def test_raw_migration_registry_and_truncate_guard_are_static_and_hash_bound():
    import importlib.util
    from pathlib import Path
    sql_path = Path("src/workbench_db/migrations/v4_postgres/003_stage00_raw_owner_receipts.sql")
    sql = sql_path.read_text(encoding="utf-8")
    assert "BEFORE TRUNCATE ON v4.stage00_raw_owner_receipts" in sql
    assert "REFERENCES v4.source_packages(package_id)" in sql
    assert "REFERENCES v4.source_revisions(source_revision_id)" in sql
    assert "CREATE SCHEMA" not in sql.upper()
    registry_text = Path("scripts/apply_v4_phase0_schema.py").read_text(encoding="utf-8")
    assert "STAGE00_SINGLE_MIGRATION" in registry_text
    assert "USER_AUTHORIZED_STAGE00_DEVELOPMENT_WRITE" in registry_text
    assert "--stage00-raw-receipts" in registry_text
    assert "cryptography>=44,<47" in Path("requirements-windows-package.txt").read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "stage00_migration_registry", "scripts/apply_v4_phase0_schema.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.verify_stage00_single_migration_definition()["status"] == "DEFINED_NOT_APPLIED"


def test_persistence_with_unregistered_issuer_rejects_before_sql(tmp_path, monkeypatch):
    plan, _ = _signed_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(ingest, "_acceptance_authority_registry", lambda pg=None: {
        "contract_id": "V4_DAILY_SOURCE_ACCEPTANCE_AUTHORITY_REGISTRY_R1",
        "status": "ACTIVE", "issuers": {},
    })
    class FakePG:
        def __init__(self): self.calls = []
        def execute(self, sql, params=None): self.calls.append((sql, params)); return self
    fake = FakePG()
    with pytest.raises(ingest.SourceIngestError, match="INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE"):
        ingest.persist_source_ingest_plan(
            fake, plan, publication_id="fixture-publication", publication_revision=1,
            ingested_at="2026-09-11T16:05:00+08:00", system_available_at="2026-09-11T16:06:00+08:00",
        )
    assert fake.calls == []


def test_00f_does_not_infer_baostock_from_generic_revision_count():
    pg = {
        "source_revision_count": 40455,
        "baostock_supplemental_contract": {
            "registry_status": "APPROVED_READ",
            "contract_status": "PUBLIC_ROUTE_B1_OPERATIONAL_FIELD_BINDING_PENDING",
        },
        "source_acceptance": {"status": "BLOCKED", "accepted_evidence": None},
    }
    stage = phase0_gate._supplemental_baostock_stage(pg)
    assert stage["status"] == "DEGRADED_PASS"
    assert stage["allowed_capabilities"] == []
    assert stage["blocked_scopes"] == ["BAOSTOCK_SUPPLEMENTAL"]
    assert "BAOSTOCK_SUPPLEMENTAL_CONTRACT_NOT_OPERATIONALLY_ACCEPTED" in stage["reason_codes"]


def test_acceptance_cli_requires_exact_target_trade_date():
    with pytest.raises(SystemExit) as exc:
        phase0_gate.main(["acceptance", "--json"])
    assert exc.value.code == 2
