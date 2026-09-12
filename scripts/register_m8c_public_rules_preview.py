"""Register a checked-in public-rule snapshot and bind it to local OHLC rows.

The rule values live in config/m8c_limit_rules_public_20260911.json and are
never fetched at runtime.  This preview uses local security names only to
recognize an explicit ST/*ST prefix; missing or ambiguous risk status remains
UNREGISTERED.  New-listing and delisting special phases are not guessed from
OHLC and are called out in the receipt.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_m8c_local_reference_preview import (
    _digest,
    _rows,
    _sha256_file,
    _source_observed_at,
    _valid_bar,
    board_for_security_id,
    build_reference_rows,
)
from workbench_analysis.limit_rules import validate_rule_versions


DB_PATH = ROOT / "data/database/market_research.duckdb"
NORMALIZED_PATH = ROOT / "data/normalized/adjusted_daily.parquet"
RULE_CONFIG_PATH = ROOT / "config/m8c_limit_rules_public_20260911.json"
RULE_EVIDENCE_PATH = ROOT / "config/m8c_rule_source_evidence_v11.json"
REPORT_PATH = ROOT / "reports/upgrade_m8/m8c_public_rule_registration_20260911.json"
ARTIFACT_VERSION = "M8C_PUBLIC_RULE_REGISTRY_V1_1_AUDIT_R1"
CONTRACT_VERSION = "REFERENCE_CAPABILITY_V1_1"
RULE_CONTRACT_VERSION = "LIMIT_RULES_V1_1"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _risk_status_map(connection: duckdb.DuckDBPyConnection, trade_date: date) -> dict[str, str]:
    rows = connection.execute(
        """
        select security_id, security_name
          from stock_daily
         where trade_date=?
        """,
        [trade_date],
    ).fetchall()
    candidates: dict[str, set[str]] = {}
    for security_id, security_name in rows:
        name = str(security_name or "").strip().upper()
        if not name:
            continue
        # A name is a candidate clue, not a verified historical legal state.
        # Keep it out of the rule key until an effective-dated status source
        # is independently accepted.
        if name.startswith("*ST") or name.startswith("ST"):
            candidates.setdefault(str(security_id), set()).add("RISK_WARNING_CANDIDATE")
    # Candidate clues are intentionally not returned as rule states.
    return {}


def _storage_reference_row_v11(slice_id: str, value: dict[str, Any], source_ref: str, rule_id: str, rule_verified: bool, source_rule_sha256: str) -> tuple[Any, ...]:
    quality = set(value.get("quality_codes") or [])
    if rule_id == "UNREGISTERED":
        quality.add("RULE_NOT_REGISTERED")
    if value.get("risk_status") in (None, "UNKNOWN"):
        quality.add("RISK_STATUS_UNKNOWN")
    if value.get("listing_phase") in (None, "UNKNOWN"):
        quality.add("LISTING_PHASE_UNKNOWN")
    if value.get("ex_rights_reference_unknown"):
        quality.add("EX_RIGHTS_REFERENCE_UNKNOWN")
    quote = Decimal(str(value["quote_prev_close"])).quantize(Decimal("0.0001")) if value["quote_prev_close"] is not None else None
    return (
        slice_id,
        value["security_id"],
        value["trade_date"],
        quote,
        None,
        None,
        None,
        None,
        value["status_known"],
        rule_id,
        source_ref,
        value["observed_at"],
        CONTRACT_VERSION,
        json.dumps(sorted(quality), ensure_ascii=False),
        value.get("source_snapshot_id"),
        value.get("quote_capability", "UNKNOWN"),
        value.get("reference_status", "UNKNOWN"),
        value.get("reference_basis", "RAW_PREV_CLOSE_APPROXIMATE"),
        value.get("exchange"),
        value.get("board"),
        value.get("risk_status", "UNKNOWN"),
        value.get("listing_phase", "UNKNOWN"),
        bool(value.get("ex_rights_reference_unknown", True)),
        bool(rule_verified),
        source_rule_sha256 or None,
    )


def build(db_path: str | Path = DB_PATH, normalized_path: str | Path = NORMALIZED_PATH, rule_config_path: str | Path = RULE_CONFIG_PATH, report_path: str | Path = REPORT_PATH) -> dict[str, Any]:
    db_file = Path(db_path).resolve()
    source_file = Path(normalized_path).resolve()
    config_file = Path(rule_config_path).resolve()
    config = json.loads(config_file.read_text(encoding="utf-8"))
    evidence_file = Path(RULE_EVIDENCE_PATH).resolve()
    evidence_hash = _sha256_file(evidence_file)
    rule_rows = list(config.get("rules") or [])
    validate_rule_versions(rule_rows)
    if config.get("contract_id") != RULE_CONTRACT_VERSION:
        raise RuntimeError("M8C_RULE_CONTRACT_V11_REQUIRED")
    if any(str(row.get("source_sha256") or "") != evidence_hash for row in rule_rows):
        raise RuntimeError("M8C_RULE_SOURCE_EVIDENCE_HASH_MISMATCH")
    source_hash = _sha256_file(source_file)
    config_hash = _sha256_file(config_file)
    observed_at = _source_observed_at(source_file)
    connection = duckdb.connect(str(db_file))
    try:
        binding = connection.execute(
            "select snapshot_id from publication_analysis_snapshots where domain='LOCAL_RECONSTRUCTED' order by bound_at desc limit 1"
        ).fetchone()
        if not binding:
            raise RuntimeError("LOCAL_RECONSTRUCTED_BINDING_MISSING")
        source_snapshot_id = str(binding[0])
        base = connection.execute(
            "select cutoff_date,query_start,universe_contract,config_hash,manifest_hash from analysis_snapshots where snapshot_id=?",
            [source_snapshot_id],
        ).fetchone()
        if not base:
            raise RuntimeError("M8C_SOURCE_SNAPSHOT_MISSING")
        technical_rows = _rows(
            connection,
            """
            select e.trade_date,t.security_id
              from analysis_snapshot_entries e
              join technical_result_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date
             where e.snapshot_id=? and e.domain='technical'
             order by e.trade_date,t.security_id
            """,
            [source_snapshot_id],
        )
        target_dates = sorted({row["trade_date"] for row in technical_rows})
        if not target_dates:
            raise RuntimeError("M8C_TECHNICAL_INPUT_MISSING")
        first_date, last_date = target_dates[0], target_dates[-1]
        normalized_rows = _rows(
            connection,
            """
            select security_id,date,raw_close,tradable,has_actual_bar,data_observed,
                   is_synthetic_fill,missing_state,security_type,universe_status
                   ,qfq_mul,qfq_add,adjustment_status,adjustment_version,is_master_session
              from read_parquet(?)
             where date between ? and ?
            """,
            [str(source_file), first_date - timedelta(days=420), last_date],
        )
        source_ref = f"LOCAL_NORMALIZED_OHLC:{source_file.as_posix()}#{source_hash}|LOCAL_PUBLIC_RULE_CONFIG:{config_file.as_posix()}#{config_hash}|LOCAL_RULE_EVIDENCE:{evidence_file.as_posix()}#{evidence_hash}"
        references = build_reference_rows(technical_rows, normalized_rows, source_ref=source_ref, observed_at=observed_at)
        risk_status_by_date = {day: _risk_status_map(connection, day) for day in target_dates}
        rule_by_key = {(str(row["exchange"]), str(row["board"]), str(row["risk_status"])): row for row in rule_rows}
        registry_snapshot_id = "m8c-public-rules-" + _digest({"source_snapshot_id": source_snapshot_id, "source_hash": source_hash, "config_hash": config_hash, "artifact_version": ARTIFACT_VERSION, "target_dates": [str(day) for day in target_dates]})[:16]
        registered = 0
        unregistered = 0
        enriched: list[tuple[dict[str, Any], str]] = []
        for value in references:
            exchange, board = board_for_security_id(value["security_id"])
            risk_status = risk_status_by_date.get(value["trade_date"], {}).get(value["security_id"], "UNKNOWN")
            rule = rule_by_key.get((exchange, board, risk_status))
            rule_id = str(rule["rule_id"]) if rule else "UNREGISTERED"
            # The registry identity, not the upstream technical snapshot, is
            # the source binding for the stored reference row.  Keeping the
            # upstream id only in the slice basis prevents M13 from silently
            # accepting a same-shaped row from another registry.
            value.update({"source_snapshot_id": registry_snapshot_id, "exchange": exchange, "board": board, "risk_status": risk_status, "listing_phase": "UNKNOWN", "ex_rights_reference_unknown": True})
            if rule_id == "UNREGISTERED":
                unregistered += 1
            else:
                registered += 1
            enriched.append((value, rule_id))

        if connection.execute("select 1 from analysis_snapshots where snapshot_id=?", [registry_snapshot_id]).fetchone():
            result = {
                "status": "ALREADY_REGISTERED",
                "artifact_version": ARTIFACT_VERSION,
                "rule_config": str(config_file),
                "rule_config_sha256": config_hash,
                "source_snapshot_id": source_snapshot_id,
                "registry_snapshot_id": registry_snapshot_id,
                "rule_rows": len(rule_rows),
                "registered_reference_rows": registered,
                "unregistered_reference_rows": unregistered,
                "m13_status": "READY_TO_BUILD",
                "writes": 0,
            }
            _write_json_atomic(Path(report_path).resolve(), result)
            return result

        technical_slice_map = {row[0]: str(row[1]) for row in connection.execute(
            "select trade_date,slice_id from analysis_snapshot_entries where snapshot_id=? and domain='technical' order by trade_date",
            [source_snapshot_id],
        ).fetchall()}
        latest_by_security: dict[str, dict[str, Any]] = {}
        valid_history_count: dict[str, int] = {}
        for row in normalized_rows:
            security_id = str(row["security_id"])
            if row["date"] == last_date:
                latest_by_security[security_id] = row
            if row["date"] < first_date and _valid_bar(row):
                valid_history_count[security_id] = valid_history_count.get(security_id, 0) + 1

        metadata_rows: list[tuple[Any, ...]] = []
        for security_id in sorted({str(row["security_id"]) for row in technical_rows}):
            exchange, board = board_for_security_id(security_id)
            observed = latest_by_security.get(security_id, {})
            listing_status = "UNKNOWN"
            security_kind = str(observed.get("security_type") or "A_STOCK").upper()
            version_id = "M8C_PUBLIC_META_" + _digest({"security_id": security_id, "source_hash": source_hash, "config_hash": config_hash, "artifact_version": ARTIFACT_VERSION, "source_snapshot_id": source_snapshot_id, "registry_snapshot_id": registry_snapshot_id})[:20]
            risk_status = risk_status_by_date.get(last_date, {}).get(security_id, "UNKNOWN")
            metadata_rows.append((security_id, version_id, exchange, board, security_kind, listing_status, first_date, last_date, datetime.now(timezone.utc), "LOCAL_PUBLIC_RULE_REGISTRY", source_ref, risk_status, "UNKNOWN", "UNKNOWN", registry_snapshot_id))

        now = datetime.now(timezone.utc)
        cutoff, query_start, universe_contract, config_hash_base, manifest_hash = base
        connection.execute("begin transaction")
        existing_rules = {str(row[0]): row for row in connection.execute("select rule_id,contract_id,source_sha256,limit_ratio,tick,rounding_mode,special_period_policy,source_ref from limit_rule_versions").fetchall()}
        rule_rows_written = 0
        for rule in rule_rows:
            rule_id = str(rule["rule_id"])
            if rule_id in existing_rules:
                existing = existing_rules[rule_id]
                if str(existing[1] or "") != RULE_CONTRACT_VERSION or str(existing[2] or "") != str(rule.get("source_sha256") or "") or float(existing[3] or -1) != float(rule.get("limit_ratio") or -1):
                    raise RuntimeError(f"RULE_ID_CONTENT_CONFLICT:{rule_id}")
                continue
            connection.execute(
                "insert into limit_rule_versions (rule_id,exchange,board,risk_status,valid_from,valid_to,limit_ratio,tick,rounding_mode,special_period_policy,source_ref,contract_id,rule_verified,source_sha256,audit_status,audit_reason,audited_at) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [rule_id, rule["exchange"], rule["board"], rule["risk_status"], rule["valid_from"], rule.get("valid_to"), rule.get("limit_ratio"), rule["tick"], rule["rounding_mode"], json.dumps(rule["special_period_policy"], ensure_ascii=False, sort_keys=True), rule["source_ref"], RULE_CONTRACT_VERSION, bool(rule.get("rule_verified")), rule.get("source_sha256"), rule.get("audit_status", "PENDING_REVIEW"), rule.get("audit_reason", ""), now],
            )
            connection.execute("insert into m8c_rule_audit_events values (?,?,?,?,?,?,?)", [rule_id, rule.get("source_sha256"), RULE_CONTRACT_VERSION, rule.get("audit_status", "PENDING_REVIEW"), rule.get("audit_reason", ""), rule["source_ref"], now])
            rule_rows_written += 1
        connection.execute(
            "insert into analysis_snapshots values (?,?,?,?,?,?,?,?)",
            [registry_snapshot_id, cutoff, query_start, universe_contract, config_hash_base, _digest({"source_snapshot_id": source_snapshot_id, "config_hash": config_hash}), "SUCCESS", now],
        )
        enriched_by_date: dict[date, list[tuple[dict[str, Any], str]]] = {}
        for value, rule_id in enriched:
            enriched_by_date.setdefault(value["trade_date"], []).append((value, rule_id))
        for trade_date in target_dates:
            values = enriched_by_date[trade_date]
            slice_id = "m8c-public-reference-" + _digest({"snapshot_id": registry_snapshot_id, "trade_date": str(trade_date)})[:20]
            logical_values = [{**value, "rule_id": rule_id} for value, rule_id in values]
            basis = {
                "artifact_version": ARTIFACT_VERSION,
                "contract_id": CONTRACT_VERSION,
                "stage": "M8C-02-PUBLIC-RULE-BINDING",
                "history_basis": "RECONSTRUCTED",
                "source_ref": source_ref,
                "source_snapshot_id": source_snapshot_id,
                "technical_input_slice": technical_slice_map.get(trade_date),
                "trade_date": str(trade_date),
                "rule_config_sha256": config_hash,
                "unknown_risk_policy": "UNREGISTERED",
                "listing_phase_policy": "UNKNOWN_WHEN_NOT_PROVEN",
            }
            connection.execute(
                "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
                [slice_id, "market_reference", trade_date, CONTRACT_VERSION, _digest({"source_ref": source_ref, "trade_date": str(trade_date)}), _digest({"technical": technical_slice_map.get(trade_date)}), json.dumps(basis, ensure_ascii=False, sort_keys=True), len(values), _digest(logical_values), "DUCKDB", None, now],
            )
            connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [registry_snapshot_id, "market_reference", trade_date, slice_id])
            connection.executemany(
                "insert into market_reference_daily (slice_id,security_id,trade_date,quote_prev_close,limit_up_price,limit_down_price,float_shares,shares_basis,status_known,rule_id,source_ref,observed_at,contract_id,quality_codes,source_snapshot_id,quote_capability,reference_status,reference_basis,exchange,board,risk_status,listing_phase,ex_rights_reference_unknown,rule_verified,source_rule_sha256) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [_storage_reference_row_v11(slice_id, value, source_ref, rule_id, bool(rule_by_key.get((value.get("exchange"), value.get("board"), value.get("risk_status")), {}).get("rule_verified", False)) if rule_id != "UNREGISTERED" else False, str(rule_by_key.get((value.get("exchange"), value.get("board"), value.get("risk_status")), {}).get("source_sha256") or "")) for value, rule_id in values],
            )
        connection.executemany(
            "insert into security_metadata_versions (security_id,version_id,exchange,board,security_kind,listing_status,valid_from,valid_to,observed_at,source_id,source_ref,risk_status,listing_phase,metadata_confidence,source_snapshot_id) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            metadata_rows,
        )
        connection.execute("commit")

        result = {
            "status": "DEGRADED_PASS",
            "artifact_version": ARTIFACT_VERSION,
            "stage_contract": "M8C-02 public, effective-dated limit rules",
            "design_baseline": ["docs/M8C_LIMIT_RULES_CONTRACT_V1.md", "docs/M8C_CAPABILITY_GATE_CONTRACT_V1.md", "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md"],
            "rule_config": str(config_file),
            "rule_config_sha256": config_hash,
            "source_snapshot_id": source_snapshot_id,
            "registry_snapshot_id": registry_snapshot_id,
            "target_dates": [str(day) for day in target_dates],
            "rule_rows_written": rule_rows_written,
            "registered_reference_rows": registered,
            "unregistered_reference_rows": unregistered,
            "metadata_rows_written": len(metadata_rows),
            "new_listing_phase_unknown_metadata_rows": len(metadata_rows),
            "reference_capability_counts": {
                status: sum(1 for value, _ in enriched if str(value.get("quote_capability")) == status)
                for status in ("EXACT", "APPROXIMATE", "UNKNOWN")
            },
            "risk_status_counts": {
                status: sum(1 for value, _ in enriched if str(value.get("risk_status")) == status)
                for status in ("NORMAL", "RISK_WARNING", "UNKNOWN")
            },
            "m13_status": "READY_TO_BUILD",
            "writes": len(rule_rows) + len(enriched) + len(metadata_rows),
            "uncertainties_for_audit": [
                "本地没有上市日期、上市阶段或复牌事件证据；所有 listing_phase 保持 UNKNOWN，不用五根 OHLC 推断普通期。",
                "风险状态按每个目标日读取；非明确 ST/*ST 不再倒推 NORMAL，保持 UNKNOWN。",
                "北交所风险警示规则未核验，配置保留未验证分支，不能产生 EXACT。",
                "原始 OHLC 前收默认 APPROXIMATE；没有逐日除权除息证据时 ex_rights_reference_unknown=true。",
                "旧 V1.0 规则/参考价快照保留但已标记待复核，不作为新 V1.1 能力证据。",
            ],
            "runtime_network_used": False,
        }
        _write_json_atomic(Path(report_path).resolve(), result)
        return result
    except Exception:
        try:
            connection.execute("rollback")
        except Exception:
            pass
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2, default=str))
