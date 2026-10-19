from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping


STAGES = ("V4-00A", "V4-00B", "V4-00C", "V4-00D", "V4-00E", "V4-00F", "V4-00G", "V4-00H")
ACCEPTED = {"FULL_PASS", "DEGRADED_PASS"}
STATUSES = ACCEPTED | {"BLOCKED"}
V4_01_REQUIRED_SCOPES = ("RAW_BOOTSTRAP", "A_STOCK_TDX_SOURCE", "LIFECYCLE_SCHEMA", "PUBLICATION_IDENTITY")
REQUIRED_SCOPE_OWNERS = {
    "A_STOCK_TDX_SOURCE": "V4-00D",
    "LIFECYCLE_SCHEMA": "V4-00B",
    "PUBLICATION_IDENTITY": "V4-00C",
}
RAW_BOOTSTRAP_OWNER = "V4-00E"


def evaluate_phase0(
    stages: Mapping[str, Any],
    core_blockers: list[str] | None = None,
    *,
    required_scopes: tuple[str, ...] = V4_01_REQUIRED_SCOPES,
    nonblocking_limitations: list[str] | None = None,
    future_stage_transfers: list[Mapping[str, str]] | None = None,
    contract_conflicts: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate stage status and capability scopes without conflating degraded with full pass."""
    blockers = list(core_blockers or [])
    normalized: dict[str, dict[str, Any]] = {}
    missing = [stage for stage in STAGES if stage not in stages]
    if missing:
        blockers.extend(f"STAGE_MISSING:{stage}" for stage in missing)

    any_degraded = False
    stage_blockers: list[str] = []
    accepted_scopes: set[str] = set()
    raw_bootstrap_claimed = False
    blocked_scopes: set[str] = set()
    all_blocked_scopes: set[str] = set()
    for stage in STAGES:
        if stage not in stages:
            continue
        raw = stages[stage]
        record = {"status": raw} if isinstance(raw, str) else dict(raw) if isinstance(raw, Mapping) else {"status": "INVALID"}
        status = record.get("status")
        if status not in STATUSES:
            stage_blockers.append(f"STAGE_STATUS_INVALID:{stage}:{status}")
            blocked_scopes.update(required_scopes)
        if status == "BLOCKED":
            stage_blockers.append(f"STAGE_BLOCKED:{stage}")
        capabilities = record.get("allowed_capabilities", [])
        if not isinstance(capabilities, list) or any(not isinstance(scope, str) or not scope for scope in capabilities):
            stage_blockers.append(f"STAGE_CAPABILITY_LIST_INVALID:{stage}")
            capabilities = []
        if status == "FULL_PASS" and record.get("blocked_scopes"):
            stage_blockers.append(f"BLOCKED_SCOPE_REQUIRES_DEGRADED_STAGE:{stage}")

        for scope in capabilities:
            if scope == "RAW_BOOTSTRAP":
                if stage == RAW_BOOTSTRAP_OWNER and status in ACCEPTED:
                    raw_bootstrap_claimed = True
                continue
            required_owner = REQUIRED_SCOPE_OWNERS.get(scope)
            if required_owner is not None and required_owner != stage:
                stage_blockers.append(f"REQUIRED_SCOPE_OWNER_MISMATCH:{scope}:{stage}:EXPECTED:{required_owner}")
                continue
            if status in ACCEPTED and (required_owner == stage or required_owner is None):
                accepted_scopes.add(scope)

        if status == "BLOCKED":
            scopes = set(record.get("blocked_scopes", []))
            all_blocked_scopes.update(scopes)
        elif status == "DEGRADED_PASS":
            any_degraded = True
            scopes = set(record.get("blocked_scopes", []))
            all_blocked_scopes.update(scopes)
            blocks_entry = bool(record.get("blocks_v4_01", False)) or bool(scopes & set(required_scopes))
            if blocks_entry:
                blocked_scopes.update(scopes & set(required_scopes) if scopes else set(required_scopes))
        normalized[stage] = {
            "status": status,
            "degraded_scopes": list(record.get("degraded_scopes", [])),
            "blocked_scopes": list(record.get("blocked_scopes", [])),
            "allowed_capabilities": list(capabilities),
            "capability_claims_effective": [
                scope for scope in capabilities
                if scope == "RAW_BOOTSTRAP" and stage == RAW_BOOTSTRAP_OWNER
                or REQUIRED_SCOPE_OWNERS.get(scope) == stage
                or scope not in REQUIRED_SCOPE_OWNERS and scope != "RAW_BOOTSTRAP"
            ],
            "blocks_v4_01": bool(record.get("blocks_v4_01", status == "BLOCKED")),
            "reason_codes": list(record.get("reason_codes", [])),
            "evidence": list(record.get("evidence", [])),
        }
        if normalized[stage]["degraded_scopes"] or normalized[stage]["blocked_scopes"]:
            any_degraded = True
        if normalized[stage]["blocks_v4_01"]:
            stage_blockers.append(f"V4_01_SCOPE_BLOCKED:{stage}")
            if not normalized[stage]["blocked_scopes"]:
                blocked_scopes.update(required_scopes)
                all_blocked_scopes.update(required_scopes)
            else:
                blocked_scopes.update(set(normalized[stage]["blocked_scopes"]) & set(required_scopes))
                all_blocked_scopes.update(normalized[stage]["blocked_scopes"])

    blockers.extend(stage_blockers)
    conflict_list = list(contract_conflicts or [])
    if conflict_list:
        blockers.extend(f"CONTRACT_CONFLICT:{item}" for item in conflict_list)
    if set(core_blockers or []):
        blocked_scopes.update(required_scopes)
        all_blocked_scopes.update(required_scopes)
    accepted_scopes.difference_update(blocked_scopes)

    unknown_required_owners = set(required_scopes) - set(REQUIRED_SCOPE_OWNERS) - {"RAW_BOOTSTRAP"}
    if unknown_required_owners:
        blockers.extend(f"REQUIRED_SCOPE_OWNER_UNDEFINED:{scope}" for scope in sorted(unknown_required_owners))
    raw_requirements_accepted = (
        raw_bootstrap_claimed
        and all(normalized.get(stage, {}).get("status") in ACCEPTED for stage in STAGES)
        and not blockers
        and not blocked_scopes
        and set(required_scopes) - {"RAW_BOOTSTRAP"} <= accepted_scopes
    )
    if raw_requirements_accepted:
        accepted_scopes.add("RAW_BOOTSTRAP")

    entry_ready = not blockers and not blocked_scopes and set(required_scopes).issubset(accepted_scopes)
    if not entry_ready:
        phase0 = "BLOCKED"
        v4_01 = "BLOCKED"
    elif any_degraded or nonblocking_limitations or future_stage_transfers:
        phase0 = "DEGRADED_PASS"
        v4_01 = "AUTHORIZED"
    else:
        phase0 = "FULL_PASS"
        v4_01 = "AUTHORIZED"

    return {
        "phase0_status": phase0,
        "v4_01_entry_permission": v4_01,
        "raw_bootstrap_permission": "AUTHORIZED" if entry_ready else "BLOCKED",
        "adjusted_bootstrap_permission": "SCOPE_DEPENDENT" if entry_ready else "BLOCKED",
        "supplemental_permission": "OPTIONAL",
        "scanner_permission": "NOT_APPLICABLE_UNTIL_V4_05",
        "production_cutover_permission": "NOT_APPLICABLE_UNTIL_LATER_GATES",
        "stages": normalized,
        "entry_gate": {
            "required_scopes": list(required_scopes),
            "accepted_scopes": sorted(accepted_scopes),
            "blocked_scopes": sorted(all_blocked_scopes),
            "blocked_required_scopes": sorted(blocked_scopes),
            "raw_bootstrap_derivation": {
                "status": "SATISFIED" if raw_requirements_accepted else "NOT_SATISFIED",
                "owner_stage": RAW_BOOTSTRAP_OWNER,
                "requires_all_phase0_stages_accepted": True,
                "required_owner_scopes_accepted": sorted(set(required_scopes) - {"RAW_BOOTSTRAP"}),
            },
        },
        "core_blockers": sorted(set(blockers)),
        "nonblocking_limitations": list(nonblocking_limitations or []),
        "future_stage_transfers": [dict(item) for item in (future_stage_transfers or [])],
        "contract_conflicts": conflict_list,
    }


# Stage00 diagnostic runtime. These names select approved PG rows and contain
# no fallback contract content themselves.
STAGE00_CONTRACTS = {
    "V4_PHASE0_FINAL_ACCEPTANCE_R3": "3.0.0",
    "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1": "1.1.0",
    "PARAMETER_REGISTRY_V1": "1.1.0",
    "CAPABILITY_CUTOVER_AND_ROLLBACK_V1": "1.0.0",
    "V4_PERFORMANCE_MEASUREMENT_CONTRACT_V1": "1.1.0",
}
STAGE00_TABLES = (
    "contract_versions", "contract_approval_events", "source_packages",
    "source_revisions", "security_lifecycle_facts", "security_lifecycle_history",
    "publications", "model_namespaces", "publication_heads",
)
TDX_BOARD_SCOPES = ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")
TDX_SAMPLES = TDX_BOARD_SCOPES


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _source_head_sha() -> str:
    import subprocess
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=_repo_root(), check=True,
            capture_output=True, text=True, timeout=5,
        )
        value = result.stdout.strip()
        return value if re.fullmatch(r"[0-9a-f]{40}", value) else "UNKNOWN"
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def _tdx_root(config_path: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    try:
        import yaml
    except ImportError:
        yaml = None
    config = yaml.safe_load(config_path.read_text(encoding="utf-8-sig")) if yaml is not None else None
    if config is None:
        raw = next((line.split(":", 1)[1].strip().strip(chr(34)).strip(chr(39)) for line in config_path.read_text(encoding="utf-8-sig").splitlines() if re.match(r"^\s+source_root\s*:", line)), None)
        config = {"tdx": {"source_root": raw}}
    raw = (config.get("tdx") or {}).get("source_root")
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("TDX_SOURCE_ROOT_NOT_CONFIGURED")
    path = Path(raw)
    return (path if path.is_absolute() else _repo_root() / path).resolve()


def _read_tdx_samples(root: Path) -> dict[str, Any]:
    from tdx.day_reader import read_edge_records, validate_day_file
    from workbench_analysis.v4_01_required_scope import required_board
    from workbench_analysis.security_entity_identity import bao_source_entity

    if not root.is_dir():
        raise FileNotFoundError("TDX_SOURCE_ROOT_UNAVAILABLE")
    selected = {}
    for market in ("sh", "sz"):
        directory = root / "vipdoc" / market / "lday"
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.glob(f"{market}*.day")):
            symbol = f"{market.upper()}.{candidate.stem[2:]}"
            code = candidate.stem[2:]
            if market == "sh":
                board = "STAR" if code.startswith(("688", "689")) else "SH_MAIN" if code.startswith(("600", "601", "603", "605")) else None
            else:
                board = "CHINEXT" if code.startswith(("300", "301")) else "SZ_MAIN" if code.startswith(("000", "001", "002", "003")) else None
            if board in TDX_BOARD_SCOPES and board not in selected:
                selected[board] = (symbol, candidate)
            if len(selected) == len(TDX_BOARD_SCOPES):
                break
        if len(selected) == len(TDX_BOARD_SCOPES):
            break
    rows = []
    failures = []
    observation_dates = []
    for expected_board in TDX_BOARD_SCOPES:
        selection = selected.get(expected_board)
        if selection is None:
            failures.append(f"TDX_BOARD_SAMPLE_MISSING:{expected_board}")
            rows.append({"board": expected_board, "status": "MISSING"})
            continue
        symbol, path = selection
        exchange, code = symbol.split(".")
        row: dict[str, Any] = {"symbol": symbol, "path_exists": path.is_file()}
        if not path.is_file():
            row["status"] = "MISSING"
            failures.append(f"TDX_SAMPLE_MISSING:{symbol}")
            rows.append(row)
            continue
        try:
            validated = validate_day_file(path, exchange.lower())
            first, last = read_edge_records(path)
            if not validated.get("valid"):
                raise ValueError("TDX_DAY_VALIDATION_FAILED:" + ",".join(validated.get("errors", [])))
            board_exchange = exchange
            board = {"SH_MAIN": "MAIN", "SZ_MAIN": "MAIN", "CHINEXT": "CHINEXT", "STAR": "STAR"}[expected_board]
            identity_facts = bao_source_entity(board_exchange, symbol, None)
            identity_check = required_board({
                "security_type": "A_STOCK", "exchange": board_exchange, "board": board,
            })
            if identity_check is None or identity_facts["identity_anchor_symbol"] != symbol:
                raise ValueError("TDX_SAMPLE_IDENTITY_CLASSIFICATION_FAILED")
            observation_date = str(validated["last_date"])
            observation_dates.append(observation_date)
            st = path.stat()
            rows.append({
                "symbol": symbol, "board": expected_board, "status": "READ_ONLY_SAMPLE_VALID",
                "record_count": validated["record_count"],
                "first_trade_date": str(validated["first_date"]),
                "last_trade_date": observation_date,
                "file_mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                "file_bytes": st.st_size,
                "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "board_scope_check": identity_check,
                "identity_evidence": identity_facts,
                "raw_ohlcva_check": {
                    "status": "PASS", "basis": "TDX_RAW_NATIVE",
                    "price_divisor": 100.0, "raw_price_ohlc_positive": min(
                        first.open, first.high, first.low, first.close,
                        last.open, last.high, last.low, last.close,
                    ) > 0,
                    "first_record_amount_nonnegative": first.amount >= 0,
                    "last_record_amount_nonnegative": last.amount >= 0,
                    "first_record_volume": first.volume, "last_record_volume": last.volume,
                },
                "identity_authority": "PG_IDENTITY_NOT_INFERRED_FROM_LOCAL_TICKER",
            })
        except (OSError, ValueError) as exc:
            row.update(status="DAMAGED", reason=str(exc))
            failures.append(f"TDX_SAMPLE_DAMAGED:{symbol}")
            rows.append(row)
    damaged = [row for row in rows if row.get("status") == "DAMAGED"]
    if damaged:
        raise ValueError("TDX_SAMPLE_DATA_DAMAGED:" + ",".join(
            f"{row['symbol']}:{row.get('reason', 'UNKNOWN')}" for row in damaged
        ))
    return {
        "root": str(root), "sample_count": len(rows), "valid_sample_count": sum(
            row.get("status") == "READ_ONLY_SAMPLE_VALID" for row in rows
        ), "tdx_observation_date": max(observation_dates) if observation_dates else None,
        "samples": rows, "failures": failures,
    }


def _pg_snapshot() -> dict[str, Any]:
    from workbench_db.v4_publication_reader import PgPublicationReader, readonly_connection
    from workbench_analysis.contract_registry_pg_v1 import (
        ContractRegistryError, load_unique_current_approved_contract,
    )

    with readonly_connection() as pg:
        identity = PgPublicationReader._read_database_identity(pg)
        role = PgPublicationReader._attest_read_role(pg)
        if (identity.get("database") != "market_research"
                or str(identity.get("host") or "").split("/")[0] != "127.0.0.1"
                or identity.get("port") != 5432):
            raise RuntimeError("PG_DATABASE_IDENTITY_MISMATCH")
        cursor = pg.cursor()
        catalog = {}
        for table in STAGE00_TABLES:
            row = cursor.execute("SELECT to_regclass(%s)", ("v4." + table,)).fetchone()
            catalog[table] = bool(row and row[0])
        counts = {}
        for key, table, sql in (
            ("source_revision_count", "source_revisions", "SELECT count(*) FROM v4.source_revisions"),
            ("accepted_source_package_count", "source_packages", "SELECT count(*) FROM v4.source_packages WHERE accepted_scope='ACCEPTED_SOURCE_PACKAGE'"),
            ("publication_head_count", "publication_heads", "SELECT count(*) FROM v4.publication_heads"),
            ("model_namespace_count", "model_namespaces", "SELECT count(*) FROM v4.model_namespaces"),
        ):
            counts[key] = int(cursor.execute(sql).fetchone()[0]) if catalog[table] else None
        contracts = {}
        for contract_id, version in STAGE00_CONTRACTS.items():
            entry = {"version": version, "status": "MISSING", "reason": None}
            if not catalog["contract_versions"] or not catalog["contract_approval_events"]:
                entry["reason"] = "PG_CATALOG_RELATION_MISSING"
                contracts[contract_id] = entry
                continue
            try:
                registered = load_unique_current_approved_contract(
                    cursor, contract_id, version, expected_database_identity=identity,
                )
                entry.update(status="APPROVED_READ", raw_sha256=registered.raw_sha256,
                             namespace=registered.namespace, source_revision=registered.approval_source_revision)
            except ContractRegistryError as exc:
                entry["reason"] = str(exc)
            contracts[contract_id] = entry
        raw_receipt = {"status": "NOT_PRESENT", "reason": "NO_STAGE00_RAW_BOOTSTRAP_RECEIPT_RELATION_OR_ACCEPTED_SOURCE"}
        catalog_missing = [name for name, found in catalog.items() if not found]
        return {
            "database_identity": identity, "read_role": role, "catalog": catalog,
            "catalog_missing": catalog_missing, "contracts": contracts,
            "missing_contract_versions": [key for key, value in contracts.items() if value["status"] != "APPROVED_READ"],
            **counts,
            "raw_bootstrap": (raw_receipt if catalog["source_packages"] else
                              {"status": "UNKNOWN", "reason": "SOURCE_PACKAGE_RELATION_MISSING"}),
        }


def run_stage00_diagnostic(*, mode: str = "doctor", tdx_root: str | None = None) -> dict[str, Any]:
    """Run bounded real Stage00 diagnostics without modifying PG or source files."""
    report: dict[str, Any] = {
        "source_head_sha": _source_head_sha(), "sampled_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_mode": mode, "execution_status": "FAILED", "phase0_status": "BLOCKED",
        "v4_01_entry_permission": "BLOCKED", "database_identity": "UNKNOWN",
        "contract_versions_read": [], "missing_contract_versions": list(STAGE00_CONTRACTS),
        "tdx_observation_date": None, "real_source_acceptance": "UNKNOWN",
        "raw_bootstrap": {"status": "UNKNOWN", "reason": "NOT_CHECKED"}, "side_effects": "NONE",
    }
    try:
        pg = _pg_snapshot()
        report["database_identity"] = pg["database_identity"]
        report["pg_read_role"] = pg["read_role"]
        report["pg_catalog"] = pg["catalog"]
        report["pg_catalog_missing"] = pg["catalog_missing"]
        report["contract_registry"] = pg["contracts"]
        report["contract_versions_read"] = [
            {"contract_id": key, **{name: value[name] for name in ("version", "raw_sha256", "namespace") if name in value}}
            for key, value in pg["contracts"].items() if value["status"] == "APPROVED_READ"
        ]
        report["missing_contract_versions"] = pg["missing_contract_versions"]
        report["pg_counts"] = {
            key: pg[key] for key in ("source_revision_count", "accepted_source_package_count", "publication_head_count", "model_namespace_count")
        }
        report["raw_bootstrap"] = pg["raw_bootstrap"]
        report["real_source_acceptance"] = (
            "ACCEPTED_PACKAGE_PRESENT" if pg["accepted_source_package_count"]
            else "NO_ACCEPTED_SOURCE_PACKAGE"
        ) if pg["accepted_source_package_count"] is not None else "UNKNOWN"
        config_path = _repo_root() / "config" / "paths.yaml"
        root = _tdx_root(config_path, tdx_root)
        tdx = _read_tdx_samples(root)
        report["tdx"] = tdx
        report["tdx_observation_date"] = tdx["tdx_observation_date"]
        contract_missing = pg["missing_contract_versions"]
        accepted_source_count = pg["accepted_source_package_count"]
        namespaces_present = bool(pg["model_namespace_count"])
        publication_schema_ready = all(pg["catalog"].get(name, False) for name in ("publications", "model_namespaces", "publication_heads"))
        heads_present = bool(pg["publication_head_count"])
        lifecycle_ready = pg["catalog"]["security_lifecycle_facts"] and pg["catalog"]["security_lifecycle_history"]
        sample_ready = not tdx["failures"] and tdx["valid_sample_count"] == len(TDX_SAMPLES)
        stages = {
            "V4-00A": {"status": "DEGRADED_PASS", "owner": "V4-00A", "source": "PG identity/catalog read", "evidence": ["database identity attested", "repeatable-read transaction is read-only"], "reason_codes": ["BACKUP_RECOVERY_RECEIPT_NOT_CHECKED"]},
            "V4-00B": {"status": "DEGRADED_PASS" if lifecycle_ready else "BLOCKED", "owner": "V4-00B", "scope": "LIFECYCLE_SCHEMA", "source": "PG catalog", "evidence": ["security lifecycle relations present" if lifecycle_ready else "security lifecycle relation missing"], "blocked_scopes": [] if lifecycle_ready else ["LIFECYCLE_SCHEMA"], "allowed_capabilities": ["LIFECYCLE_SCHEMA"] if lifecycle_ready else [], "blocks_v4_01": not lifecycle_ready, "reason_codes": ["LIFECYCLE_DATA_COVERAGE_NOT_PROVEN"]},
            "V4-00C": {"status": "DEGRADED_PASS" if publication_schema_ready else "BLOCKED", "owner": "V4-00C", "scope": "PUBLICATION_IDENTITY", "source": "PG catalog and read-only row counts", "evidence": ["publication identity relations present" if publication_schema_ready else "publication identity relation missing", f"publication_heads={pg['publication_head_count']}"], "blocked_scopes": [] if publication_schema_ready else ["PUBLICATION_IDENTITY"], "allowed_capabilities": ["PUBLICATION_IDENTITY"] if publication_schema_ready else [], "blocks_v4_01": not publication_schema_ready, "reason_codes": ["NO_HEAD_PRESENT" if not heads_present else "HEAD_PRESENT_NOT_SELECTED"]},
            "V4-00D": {"status": "DEGRADED_PASS" if sample_ready else "BLOCKED", "owner": "V4-00D", "scope": "A_STOCK_TDX_SOURCE", "source": "configured read-only TDX .day samples", "evidence": [f"valid_samples={tdx['valid_sample_count']}/{len(TDX_SAMPLES)}", f"observation_date={tdx['tdx_observation_date']}"], "blocked_scopes": ["A_STOCK_TDX_SOURCE"], "blocks_v4_01": True, "reason_codes": ["SAMPLE_VALID_BUT_NO_ACCEPTED_SOURCE_PACKAGE"] if sample_ready and accepted_source_count == 0 else (["ACCEPTED_SOURCE_PACKAGE_COUNT_UNKNOWN"] if accepted_source_count is None else (["ACCEPTED_SOURCE_PACKAGE_PRESENT_REQUIRES_SCOPE_VALIDATION"] if accepted_source_count else tdx["failures"]))},
            "V4-00E": {"status": "BLOCKED", "owner": "V4-00E", "scope": "RAW_BOOTSTRAP", "source": "PG accepted source and RAW receipt state", "evidence": [f"accepted_source_packages={accepted_source_count}", pg["raw_bootstrap"]["status"]], "blocked_scopes": ["RAW_BOOTSTRAP"], "blocks_v4_01": True, "reason_codes": ["RAW_BOOTSTRAP_NOT_DERIVED_FROM_ACCEPTED_INPUT"]},
            "V4-00F": {"status": "DEGRADED_PASS" if pg["source_revision_count"] is not None else "BLOCKED", "owner": "V4-00F", "source": "PG source revision catalog", "evidence": [f"source_revisions={pg['source_revision_count']}"], "reason_codes": ["SOURCE_SCOPE_AND_ACCEPTANCE_INCOMPLETE"]},
            "V4-00G": {"status": "BLOCKED" if contract_missing else "DEGRADED_PASS", "owner": "V4-00G", "source": "PG-only approved contract registry", "evidence": [f"approved_required_contracts={len(STAGE00_CONTRACTS)-len(contract_missing)}/{len(STAGE00_CONTRACTS)}"], "reason_codes": ["APPROVED_STAGE00_CONTRACTS_MISSING"] if contract_missing else ["PARAMETER_EFFECTIVE_STATE_NOT_PROVEN"]},
            "V4-00H": {"status": "BLOCKED" if contract_missing else "DEGRADED_PASS", "owner": "V4-00H", "source": "PG-only final acceptance contract and actual Stage00 evidence", "evidence": [f"missing_contract_versions={len(contract_missing)}"], "reason_codes": ["FINAL_ACCEPTANCE_CONTRACT_OR_EVIDENCE_MISSING"] if contract_missing else ["EXTERNAL_ACCEPTANCE_NOT_COMPLETE"]},
        }
        # Keep the gate's existing scope ownership and required-scope semantics.
        gate = evaluate_phase0(stages)
        report["stages"] = {
            key: {**value, **gate["stages"].get(key, {})} for key, value in stages.items()
        }
        report["entry_gate"] = gate["entry_gate"]
        report["phase0_status"] = gate["phase0_status"]
        report["v4_01_entry_permission"] = gate["v4_01_entry_permission"]
        report["execution_status"] = "OK"
        report["execution_reason"] = "DIAGNOSTICS_COMPLETED; BUSINESS_ACCEPTANCE_GAPS_REPORTED_AS_BLOCKED"
        report["head_present"] = heads_present
        report["namespace_present"] = namespaces_present
    except Exception as exc:
        report["execution_status"] = "FAILED"
        report["execution_reason"] = str(exc) if str(exc) else type(exc).__name__
        report["failure_type"] = type(exc).__name__
    return report


def fixture_test_result() -> dict[str, Any]:
    """Exercise fail-closed aggregation without PG or market data inputs."""
    stages = {stage: {"status": "BLOCKED", "reason_codes": ["FIXTURE_MISSING_REAL_EVIDENCE"]} for stage in STAGES}
    result = evaluate_phase0(stages)
    passed = result["phase0_status"] == "BLOCKED" and result["v4_01_entry_permission"] == "BLOCKED"
    return {"run_mode": "fixture-test", "execution_status": "OK" if passed else "FAILED",
            "fixture_test_status": "PASS" if passed else "FAIL",
            "phase0_status": result["phase0_status"], "v4_01_entry_permission": result["v4_01_entry_permission"],
            "side_effects": "NONE", "scope": "PURE_GATE_RULES_ONLY"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V4 Stage00 real read-only diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("doctor", "acceptance"):
        child = sub.add_parser(command)
        child.add_argument("--json", action="store_true", help="emit structured JSON")
        child.add_argument("--tdx-root", help="read-only source root override for bounded diagnostics")
    fixture = sub.add_parser("fixture-test")
    fixture.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fixture-test":
        result = fixture_test_result()
        exit_code = 0 if result["execution_status"] == "OK" else 1
    else:
        result = run_stage00_diagnostic(mode=args.command, tdx_root=args.tdx_root)
        if result["execution_status"] != "OK":
            exit_code = 1
        elif args.command == "acceptance" and result["phase0_status"] == "BLOCKED":
            exit_code = 2
        else:
            exit_code = 0
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
