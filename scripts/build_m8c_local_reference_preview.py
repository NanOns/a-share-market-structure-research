"""Materialize the locally provable part of M8C from the normalized OHLC file.

This builder deliberately does not invent a limit rule.  The normalized local
artifact proves raw OHLC and therefore the previous raw close when the prior
bar passes the quality gate.  It does not prove a board/risk/date-sensitive
limit ratio, tick, rounding mode, or special-period policy.  Those remain a
separate M8C-02 input audit item until a local, source-referenced rule file is
provided.

The builder writes only workspace DuckDB/report artifacts.  TDX source paths
are read-only inputs and are never opened for writing.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.reference_capability import ReferenceCapabilityError


DB_PATH = ROOT / "data/database/market_research.duckdb"
NORMALIZED_PATH = ROOT / "data/normalized/adjusted_daily.parquet"
REPORT_PATH = ROOT / "reports/upgrade_m8/m8c_local_reference_materialization_20260911.json"
CONTRACT_VERSION = "REFERENCE_CAPABILITY_V1_1"
ARTIFACT_VERSION = "M8C_LOCAL_REFERENCE_PREVIEW_V1_1"
ADJUSTMENT_STATUS_WHITELIST = frozenset(
    {
        "VERIFIED_REPRODUCIBLE_TDX_NATIVE",
        "VERIFIED_REPRODUCIBLE",
        "AUTOMATED_LOCAL_VALIDATION_ONLY",
        "PARTIALLY_VERIFIED_MANUAL_UI_PENDING",
        "EXTERNAL_CROSSCHECK_INCONCLUSIVE",
        "UNRESOLVED_EXTERNAL_QFQ_MISMATCH",
        "STRUCTURE_PARSED_SEMANTICS_UNVERIFIED",
        "UNVERIFIED",
        "UNKNOWN",
        "",
    }
)
DESIGN_BASELINE = [
    "docs/M8C_REFERENCE_CAPABILITY_CONTRACT_V1.md",
    "docs/M8C_LIMIT_RULES_CONTRACT_V1.md",
    "docs/M8C_CAPABILITY_GATE_CONTRACT_V1.md",
    "docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md",
]


def _digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_observed_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def board_for_security_id(security_id: str) -> tuple[str, str]:
    """Return the configured exchange/board identity for an A-share ID.

    The prefixes mirror config/workbench_universe.yaml and are used only for
    identity metadata.  They are not used to infer a limit ratio.
    """
    market, code = str(security_id).upper().split(".", 1)
    if market == "SH":
        return market, "STAR" if code.startswith(("688", "689")) else "MAIN"
    if market == "SZ":
        return market, "GROWTH" if code.startswith(("300", "301", "302")) else "MAIN"
    if market == "BJ":
        return market, "BJ"
    return market, "UNKNOWN"


def _valid_bar(row: dict[str, Any]) -> bool:
    value = row.get("raw_close")
    try:
        close = float(value)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(close) or close <= 0:
        return False
    return (
        row.get("has_actual_bar") is True
        and row.get("data_observed") is True
        and row.get("is_synthetic_fill") is not True
        and str(row.get("missing_state") or "BAR").upper() == "BAR"
    )


def _validate_normalized_input(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the R2 input gate before any previous-close reconstruction."""
    validated: list[dict[str, Any]] = []
    seen: set[tuple[str, Any]] = set()
    for row in rows:
        security_id = str(row.get("security_id") or "")
        trade_date = row.get("date")
        if not security_id or trade_date is None:
            raise ReferenceCapabilityError("REFERENCE_NORMALIZED_ID_OR_DATE_MISSING")
        key = (security_id, trade_date)
        if key in seen:
            raise ReferenceCapabilityError("REFERENCE_NORMALIZED_DUPLICATE_SECURITY_DATE")
        seen.add(key)
        status = str(row.get("adjustment_status") or "").strip().upper()
        if status not in ADJUSTMENT_STATUS_WHITELIST:
            raise ReferenceCapabilityError(f"REFERENCE_ADJUSTMENT_STATUS_NOT_WHITELISTED:{status}")
        for field in ("raw_close", "qfq_mul", "qfq_add"):
            value = row.get(field)
            if value is None:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                raise ReferenceCapabilityError(f"REFERENCE_NON_NUMERIC_{field.upper()}") from None
            if not math.isfinite(numeric):
                raise ReferenceCapabilityError(f"REFERENCE_NON_FINITE_{field.upper()}")
            if field == "qfq_mul" and numeric <= 0:
                raise ReferenceCapabilityError("REFERENCE_INVALID_QFQ_MUL")
        validated.append(row)
    return validated


def build_reference_rows(
    technical_rows: Iterable[dict[str, Any]],
    normalized_rows: Iterable[dict[str, Any]],
    *,
    source_ref: str,
    observed_at: datetime,
) -> list[dict[str, Any]]:
    """Build one capability row per technical security/date.

    Previous close is taken from the prior valid local raw bar for that
    security, not from a natural-date subtraction and not from adjusted data.
    """
    history: dict[str, list[dict[str, Any]]] = {}
    for raw in _validate_normalized_input(normalized_rows):
        security_id = str(raw["security_id"])
        history.setdefault(security_id, []).append(raw)
    for values in history.values():
        values.sort(key=lambda item: item["date"])

    result: list[dict[str, Any]] = []
    seen: set[tuple[str, date]] = set()
    for technical in sorted(technical_rows, key=lambda item: (item["trade_date"], item["security_id"])):
        security_id = str(technical["security_id"])
        trade_date = technical["trade_date"]
        if (security_id, trade_date) in seen:
            raise ReferenceCapabilityError("REFERENCE_DUPLICATE_SECURITY_DATE")
        seen.add((security_id, trade_date))

        previous_bar: dict[str, Any] | None = None
        for bar in history.get(security_id, ()):
            if bar["date"] == trade_date:
                break
            if bar["date"] < trade_date and _valid_bar(bar):
                previous_bar = bar

        previous_close = float(previous_bar["raw_close"]) if previous_bar is not None else None

        quality = ["SHARES_UNAVAILABLE", "RULE_NOT_REGISTERED", "LISTING_PHASE_UNKNOWN", "EX_RIGHTS_REFERENCE_UNKNOWN"]
        if previous_bar is not None:
            quality.append("PREVIOUS_SESSION_ADJACENCY_UNVERIFIED")
            previous_status = str(previous_bar.get("adjustment_status") or "").strip().upper()
            if previous_status != "VERIFIED_REPRODUCIBLE_TDX_NATIVE":
                quality.append("ADJUSTMENT_STATUS_UNVERIFIED")
            if any(previous_bar.get(field) is None for field in ("qfq_mul", "qfq_add", "adjustment_version")):
                quality.append("ADJUSTMENT_FACTORS_INCOMPLETE")
        # Raw OHLC is never sufficient to prove a legally applicable
        # reference price.  A dedicated, source-verified daily reference or
        # corporate-action event feed is required for EXACT.
        quote_capability = "APPROXIMATE" if previous_close is not None else "UNKNOWN"
        if previous_close is None:
            quality.append("QUOTE_PREVIOUS_CLOSE_UNAVAILABLE")
        quality.append("EXACT_REFERENCE_NOT_PROVEN")
        result.append(
            {
                "security_id": security_id,
                "trade_date": trade_date,
                "quote_prev_close": previous_close,
                "float_shares": None,
                "shares_unit": None,
                "shares_basis": None,
                "quote_capability": quote_capability,
                "shares_capability": "UNAVAILABLE",
                "turnover_capability": "UNAVAILABLE",
                "status_known": False,
                "reference_status": "APPROXIMATE" if previous_close is not None else "UNKNOWN",
                "reference_basis": "RAW_PREV_CLOSE_APPROXIMATE",
                "listing_phase": "UNKNOWN",
                "ex_rights_reference_unknown": True,
                "rule_verified": False,
                "rule_id": "UNREGISTERED",
                "rule_registration_status": "NOT_REGISTERED",
                "source_ref": source_ref,
                "observed_at": observed_at,
                "quality_codes": sorted(set(quality)),
                "contract_id": CONTRACT_VERSION,
            }
        )
    return result


def _rows(connection: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor = connection.execute(sql, list(params))
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def build(db_path: str | Path = DB_PATH, normalized_path: str | Path = NORMALIZED_PATH, report_path: str | Path = REPORT_PATH) -> dict[str, Any]:
    db_file = Path(db_path).resolve()
    source_file = Path(normalized_path).resolve()
    if not source_file.is_file():
        raise FileNotFoundError(source_file)

    source_hash = _sha256_file(source_file)
    observed_at = _source_observed_at(source_file)
    connection = duckdb.connect(str(db_file))
    try:
        binding = connection.execute(
            """
            select snapshot_id
              from publication_analysis_snapshots
             where domain='LOCAL_RECONSTRUCTED'
             order by bound_at desc
             limit 1
            """
        ).fetchone()
        if not binding:
            raise RuntimeError("LOCAL_RECONSTRUCTED_BINDING_MISSING")
        source_snapshot_id = str(binding[0])
        snapshot_base = connection.execute(
            "select cutoff_date,query_start,universe_contract,config_hash,manifest_hash from analysis_snapshots where snapshot_id=?",
            [source_snapshot_id],
        ).fetchone()
        if not snapshot_base:
            raise RuntimeError("M8C_SOURCE_SNAPSHOT_MISSING")

        technical_rows = _rows(
            connection,
            """
            select e.trade_date,t.security_id
              from analysis_snapshot_entries e
              join stock_technical_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date
             where e.snapshot_id=? and e.domain='technical'
             order by e.trade_date,t.security_id
            """,
            [source_snapshot_id],
        )
        if not technical_rows:
            raise RuntimeError("M8C_TECHNICAL_INPUT_MISSING")
        target_dates = sorted({row["trade_date"] for row in technical_rows})
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
            [str(source_file), first_date - timedelta(days=31), last_date],
        )

        source_ref = f"LOCAL_NORMALIZED_OHLC:{source_file.as_posix()}#{source_hash}"
        references = build_reference_rows(technical_rows, normalized_rows, source_ref=source_ref, observed_at=observed_at)
        reference_snapshot_id = "m8c-reference-input-" + _digest({"source_snapshot_id": source_snapshot_id, "source_hash": source_hash, "target_dates": [str(day) for day in target_dates]})[:16]

        existing = connection.execute("select 1 from analysis_snapshots where snapshot_id=?", [reference_snapshot_id]).fetchone()
        if existing:
            result = {
                "status": "ALREADY_MATERIALIZED",
                "artifact_version": ARTIFACT_VERSION,
                "contract_id": CONTRACT_VERSION,
                "design_baseline": DESIGN_BASELINE,
                "stage_contract": "M8C-01 local reference capability materialization",
                "source_snapshot_id": source_snapshot_id,
                "reference_snapshot_id": reference_snapshot_id,
                "source_ref": source_ref,
                "target_dates": [str(day) for day in target_dates],
                "reference_rows": int(connection.execute("select count(*) from market_reference_daily where contract_id=?", [CONTRACT_VERSION]).fetchone()[0]),
                "rule_rows_before": int(connection.execute("select count(*) from limit_rule_versions").fetchone()[0]),
                "rule_rows_written": 0,
                "rule_status": "BLOCKED_NO_LOCAL_VERSIONED_RULE_SOURCE",
                "m13_status": "BLOCKED_RULE_INPUT_MISSING",
                "writes": 0,
                "acceptance_result": "M8C-01 input is present; M8C-02 rule gate remains independently blocked",
                "next_stage": "独立补充带来源的日期敏感 limit_rule_versions；不得从 OHLC 走势反推规则",
            }
            _write_json_atomic(Path(report_path).resolve(), result)
            return result

        now = datetime.now(timezone.utc)
        cutoff, query_start, universe_contract, config_hash, manifest_hash = snapshot_base
        technical_slice_map = {row[0]: str(row[1]) for row in connection.execute(
            "select trade_date,slice_id from analysis_snapshot_entries where snapshot_id=? and domain='technical' order by trade_date",
            [source_snapshot_id],
        ).fetchall()}
        reference_by_date: dict[date, list[dict[str, Any]]] = {}
        for row in references:
            reference_by_date.setdefault(row["trade_date"], []).append(row)
        metadata_rows: list[tuple[Any, ...]] = []
        latest_by_security: dict[str, dict[str, Any]] = {}
        for row in normalized_rows:
            if row["date"] == last_date:
                latest_by_security[str(row["security_id"])] = row
        for security_id in sorted({str(row["security_id"]) for row in technical_rows}):
            exchange, board = board_for_security_id(security_id)
            observed = latest_by_security.get(security_id, {})
            status = "ACTIVE" if str(observed.get("universe_status") or "").upper() == "IN_NORMAL_UNIVERSE" else "UNKNOWN"
            kind = str(observed.get("security_type") or "A_STOCK").upper()
            version_id = "M8C_LOCAL_" + _digest({"security_id": security_id, "source_hash": source_hash})[:20]
            metadata_rows.append((security_id, version_id, exchange, board, kind, status, first_date, last_date, observed_at, "LOCAL_NORMALIZED_UNIVERSE", source_ref))

        connection.execute("begin transaction")
        connection.execute(
            "insert into analysis_snapshots values (?,?,?,?,?,?,?,?)",
            [reference_snapshot_id, cutoff, query_start, universe_contract, config_hash, _digest({"source_hash": source_hash, "source_snapshot_id": source_snapshot_id}), "SUCCESS", now],
        )
        for trade_date in target_dates:
            values = reference_by_date[trade_date]
            slice_id = "m8c-reference-" + _digest({"snapshot_id": reference_snapshot_id, "trade_date": str(trade_date)})[:20]
            input_hash = _digest({"source_ref": source_ref, "trade_date": str(trade_date)})
            logical_hash = _digest(values)
            basis = {
                "artifact_version": ARTIFACT_VERSION,
                "contract_id": CONTRACT_VERSION,
                "stage": "M8C-01-LOCAL-REFERENCE",
                "history_basis": "RECONSTRUCTED",
                "source_ref": source_ref,
                "source_snapshot_id": source_snapshot_id,
                "technical_input_slice": technical_slice_map.get(trade_date),
                "trade_date": str(trade_date),
                "rule_status": "UNREGISTERED",
            }
            connection.execute(
                "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
                [slice_id, "market_reference", trade_date, CONTRACT_VERSION, input_hash, _digest({"technical": technical_slice_map.get(trade_date)}), json.dumps(basis, ensure_ascii=False, sort_keys=True), len(values), logical_hash, "DUCKDB", None, now],
            )
            connection.execute(
                "insert into analysis_snapshot_entries values (?,?,?,?)",
                [reference_snapshot_id, "market_reference", trade_date, slice_id],
            )
            storage_rows = []
            for value in values:
                quote = Decimal(str(value["quote_prev_close"])).quantize(Decimal("0.0001")) if value["quote_prev_close"] is not None else None
                storage_rows.append((slice_id, value["security_id"], value["trade_date"], quote, None, None, None, None, value["status_known"], value["rule_id"], value["source_ref"], value["observed_at"], CONTRACT_VERSION, json.dumps(value["quality_codes"], ensure_ascii=False, sort_keys=True)))
            connection.executemany(
                "insert into market_reference_daily (slice_id,security_id,trade_date,quote_prev_close,limit_up_price,limit_down_price,float_shares,shares_basis,status_known,rule_id,source_ref,observed_at,contract_id,quality_codes) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                storage_rows,
            )
        connection.executemany(
            "insert into security_metadata_versions (security_id,version_id,exchange,board,security_kind,listing_status,valid_from,valid_to,observed_at,source_id,source_ref) values (?,?,?,?,?,?,?,?,?,?,?)",
            metadata_rows,
        )
        connection.execute("commit")

        exact_count = sum(row["quote_capability"] == "EXACT" for row in references)
        result = {
            "status": "DEGRADED_PASS",
            "artifact_version": ARTIFACT_VERSION,
            "contract_id": CONTRACT_VERSION,
            "design_baseline": DESIGN_BASELINE,
            "stage_contract": "M8C-01 local reference capability materialization",
            "source_snapshot_id": source_snapshot_id,
            "reference_snapshot_id": reference_snapshot_id,
            "source_ref": source_ref,
            "source_file_sha256": source_hash,
            "target_dates": [str(day) for day in target_dates],
            "reference_rows_written": len(references),
            "quote_prev_close_exact": exact_count,
            "quote_prev_close_unavailable": len(references) - exact_count,
            "security_metadata_rows_written": len(metadata_rows),
            "float_shares_rows_written": 0,
            "limit_price_rows_written": 0,
            "rule_rows_before": 0,
            "rule_rows_written": 0,
            "rule_status": "BLOCKED_NO_LOCAL_VERSIONED_RULE_SOURCE",
            "m13_status": "BLOCKED_RULE_INPUT_MISSING",
            "writes": len(references) + len(metadata_rows),
            "acceptance_result": "M8C-01 input is present; M8C-02 rule gate remains independently blocked",
            "acceptance": {
                "ohlc_source_local": True,
                "raw_close_only_for_reference": True,
                "no_future_rows": True,
                "no_default_10_percent_rule": True,
                "no_tdx_write": True,
                "turnover_capability": "UNAVAILABLE_FLOAT_SHARES_MISSING",
            },
            "next_stage": "独立补充带来源的日期敏感 limit_rule_versions；补齐后重跑 scripts/build_m13_preview.py",
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
