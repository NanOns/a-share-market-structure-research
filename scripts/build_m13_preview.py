"""Materialize the M13 preview domains from one bound local snapshot.

The builder is deliberately local-only.  It consumes the immutable technical
snapshot plus audited M8C reference/rule rows, creates a new reconstructed
snapshot, and atomically binds it to the publication.  Empty M8C inputs are a
hard, non-writing block; no percentage or name based limit inference is used.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.limit_ladder import CONTRACT_VERSION as LADDER_CONTRACT, derive_limit_ladder_rows
from workbench_analysis.limit_promotion import CONTRACT_VERSION as PROMOTION_CONTRACT, annotate_promotion_states, build_promotion_points
from workbench_analysis.limit_rules import LimitRuleVersion, LimitStateService
from workbench_analysis.market_cycle import CONTRACT_ID as MARKET_CONTRACT, aggregate_market_point, group_queue_counts, group_sector_state_counts
from workbench_service.universe import is_workbench_statistical_security_id


DB_PATH = ROOT / "data/database/market_research.duckdb"
ARTIFACT_VERSION = "M13_PREVIEW_ARTIFACT_V1"
SLICE_GRANULARITY = "DOMAIN_DATE_BASIS_V1"


def _digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _date_key(value: Any) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _rows(connection: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor = connection.execute(sql, list(params))
    names = [item[0] for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _latest_binding(connection: duckdb.DuckDBPyConnection) -> tuple[str, str]:
    row = connection.execute(
        """
        select b.publication_id,b.snapshot_id
          from publication_analysis_snapshots b
          join publications p on p.publication_id=b.publication_id
         where b.domain='LOCAL_RECONSTRUCTED' and p.status='SUCCESS'
         order by b.bound_at desc
         limit 1
        """
    ).fetchone()
    if not row:
        raise RuntimeError("LOCAL_RECONSTRUCTED_BINDING_MISSING")
    return str(row[0]), str(row[1])


def _slice_map(connection: duckdb.DuckDBPyConnection, snapshot_id: str, domain: str) -> dict[Any, str]:
    return {row[0]: str(row[1]) for row in connection.execute(
        "select trade_date,slice_id from analysis_snapshot_entries where snapshot_id=? and domain=? order by trade_date",
        [snapshot_id, domain],
    ).fetchall()}


def _hierarchy_binding(connection: duckdb.DuckDBPyConnection, snapshot_id: str) -> tuple[str, str, str]:
    """Resolve hierarchy from this snapshot or exact shared-slice lineage."""
    direct = connection.execute(
        "select hierarchy_version,source_hash from analysis_snapshot_hierarchy where snapshot_id=?",
        [snapshot_id],
    ).fetchone()
    if direct:
        return snapshot_id, str(direct[0]), str(direct[1])
    lineage = connection.execute(
        """
        select e2.snapshot_id, h.hierarchy_version, h.source_hash
          from analysis_snapshot_entries e1
          join analysis_snapshot_entries e2 on e2.slice_id=e1.slice_id
          join analysis_snapshot_hierarchy h on h.snapshot_id=e2.snapshot_id
         where e1.snapshot_id=? and e2.snapshot_id<>?
         order by h.bound_at desc, e2.snapshot_id desc
         limit 1
        """,
        [snapshot_id, snapshot_id],
    ).fetchone()
    if not lineage:
        # Minimal isolated fixtures may not have the hierarchy subsystem at all.
        # Production databases with hierarchy versions must fail closed instead.
        hierarchy_versions = connection.execute("select count(*) from tdx_sector_hierarchy_versions").fetchone()[0]
        if not hierarchy_versions:
            return "", "", ""
        raise RuntimeError("M13_HIERARCHY_BINDING_MISSING")
    return str(lineage[0]), str(lineage[1]), str(lineage[2])


def _metadata(connection: duckdb.DuckDBPyConnection, security_id: str, trade_date: Any, registry_snapshot_id: str) -> dict[str, Any] | None:
    rows = _rows(
        connection,
        """
        select security_id,version_id,exchange,board,security_kind,listing_status,risk_status,listing_phase,metadata_confidence
          from security_metadata_versions
         where security_id=? and (valid_from is null or valid_from<=?)
           and (valid_to is null or valid_to>=?)
           and source_snapshot_id=?
         order by valid_from desc nulls last,observed_at desc,version_id desc
         limit 1
        """,
        [security_id, trade_date, trade_date, registry_snapshot_id],
    )
    return rows[0] if rows else None


def _reference_map(connection: duckdb.DuckDBPyConnection, registry_snapshot_id: str) -> dict[tuple[str, Any], dict[str, Any]]:
    """Read only reference rows explicitly bound to one registry snapshot."""
    values = _rows(connection, """
        select m.*
          from market_reference_daily m
          join analysis_snapshot_entries e
            on e.snapshot_id=? and e.domain='market_reference'
           and e.trade_date=m.trade_date and e.slice_id=m.slice_id
         where m.contract_id='REFERENCE_CAPABILITY_V1_1'
        order by m.trade_date,m.security_id,m.slice_id
    """, [registry_snapshot_id])
    if not values:
        return {}
    result: dict[tuple[str, Any], dict[str, Any]] = {}
    for row in values:
        key = (str(row["security_id"]), row["trade_date"])
        if key in result:
            raise RuntimeError(f"M13_REFERENCE_REGISTRY_DUPLICATE:{registry_snapshot_id}:{key[0]}:{key[1]}")
        result[key] = row
    return result


def _rule_map(connection: duckdb.DuckDBPyConnection, registry_snapshot_id: str, references: dict[tuple[str, Any], dict[str, Any]]) -> dict[str, LimitRuleVersion]:
    rule_ids = sorted({str(row.get("rule_id")) for row in references.values() if row.get("rule_id") and str(row.get("rule_id")) != "UNREGISTERED"})
    if not rule_ids:
        return {}
    placeholders = ",".join("?" for _ in rule_ids)
    rows = _rows(connection, f"select * from limit_rule_versions where contract_id='LIMIT_RULES_V1_1' and rule_id in ({placeholders})", rule_ids)
    if len(rows) != len(rule_ids):
        raise RuntimeError(f"M13_REFERENCE_RULE_BINDING_INCOMPLETE:{registry_snapshot_id}")
    return {str(row["rule_id"]): LimitRuleVersion.from_mapping(row) for row in rows}


def _technical_by_date(connection: duckdb.DuckDBPyConnection, snapshot_id: str) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = {}
    rows = _rows(
        connection,
        """
        select e.trade_date,t.security_id,t.raw_close,t.adj_close,t.quote_ret1,t.raw_amount,t.ma20,t.ma60
          from analysis_snapshot_entries e
          join stock_technical_daily t on t.slice_id=e.slice_id and t.trade_date=e.trade_date
         where e.snapshot_id=? and e.domain='technical'
         order by e.trade_date,t.security_id
        """,
        [snapshot_id],
    )
    for row in rows:
        if is_workbench_statistical_security_id(row["security_id"], ROOT):
            result.setdefault(row["trade_date"], []).append(row)
    return result


def _market_supporting_rows(connection: duckdb.DuckDBPyConnection, snapshot_id: str, dates: list[Any]) -> tuple[dict[Any, dict[str, dict[str, int]]], dict[Any, list[dict[str, Any]]], dict[Any, list[dict[str, Any]]]]:
    high: dict[Any, dict[str, dict[str, int]]] = {}
    queues: dict[Any, list[dict[str, Any]]] = {}
    sectors: dict[Any, list[dict[str, Any]]] = {}
    date_set = set(dates)
    if connection.execute("select count(*) from information_schema.tables where table_name='stock_high_daily'").fetchone()[0]:
        for row in _rows(connection, """
            select e.trade_date,h.window,h.new_high
              from analysis_snapshot_entries e join stock_high_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date
             where e.snapshot_id=? and e.domain='high'
        """, [snapshot_id]):
            if row["trade_date"] not in date_set:
                continue
            bucket = high.setdefault(row["trade_date"], {}).setdefault(str(row["window"]), {"valid_count": 0, "hit_count": 0})
            bucket["valid_count"] += int(row["new_high"] is not None)
            bucket["hit_count"] += int(row["new_high"] is True)
    if connection.execute("select count(*) from information_schema.tables where table_name='historical_structure_daily'").fetchone()[0]:
        for row in _rows(connection, """
            select e.trade_date,h.security_id,h.queue_name,h.hit
              from analysis_snapshot_entries e join historical_structure_daily h on h.slice_id=e.slice_id and h.trade_date=e.trade_date
             where e.snapshot_id=? and e.domain='structure'
        """, [snapshot_id]):
            if row["trade_date"] in date_set:
                queues.setdefault(row["trade_date"], []).append(row)
    if connection.execute("select count(*) from information_schema.tables where table_name='sector_cycle_daily'").fetchone()[0]:
        for row in _rows(connection, """
            select e.trade_date,s.sector_id,s.diffusion_state
              from analysis_snapshot_entries e join sector_cycle_daily s on s.slice_id=e.slice_id and s.trade_date=e.trade_date
             where e.snapshot_id=? and e.domain='sector_cycle'
        """, [snapshot_id]):
            if row["trade_date"] in date_set:
                sectors.setdefault(row["trade_date"], []).append(row)
    return high, queues, sectors


def _limit_inputs(connection: duckdb.DuckDBPyConnection, technical: dict[Any, list[dict[str, Any]]], references: dict[tuple[str, Any], dict[str, Any]], rules: dict[str, LimitRuleVersion], registry_snapshot_id: str) -> list[dict[str, Any]]:
    service = LimitStateService(tuple(rules.values()))
    inputs: list[dict[str, Any]] = []
    for trade_date in sorted(technical):
        for technical_row in technical[trade_date]:
            security_id = str(technical_row["security_id"])
            reference = references.get((security_id, trade_date))
            metadata = _metadata(connection, security_id, trade_date, registry_snapshot_id)
            rule = rules.get(str(reference.get("rule_id"))) if reference and reference.get("rule_id") else None
            active = str(metadata.get("listing_status") or "").upper() == "ACTIVE" if metadata else False
            suspended = str(metadata.get("listing_status") or "").upper() in {"SUSPENDED", "HALTED"} if metadata else None
            reference_known = bool(reference and str(reference.get("quote_capability") or "").upper() == "EXACT" and str(reference.get("reference_status") or "").upper() == "KNOWN" and not bool(reference.get("ex_rights_reference_unknown")) and reference.get("quote_prev_close") and metadata and active and rule)
            evaluated = service.evaluate({
                "security_id": security_id,
                "trade_date": trade_date,
                "close": technical_row.get("raw_close"),
                "quote_prev_close": reference.get("quote_prev_close") if reference else None,
                "reference_status": "KNOWN" if reference_known else str(reference.get("reference_status") if reference else "UNKNOWN"),
                "exchange": metadata.get("exchange") if metadata else None,
                "board": metadata.get("board") if metadata else None,
                "risk_status": metadata.get("risk_status") if metadata else None,
                "suspended": suspended,
                "listing_phase": metadata.get("listing_phase") if metadata else None,
                "ex_rights_reference_unknown": reference.get("ex_rights_reference_unknown") if reference else None,
            })
            inputs.append({
                "security_id": security_id,
                "trade_date": trade_date,
                "limit_state": evaluated["limit_state"],
                "quote_present": technical_row.get("raw_close") is not None,
                "has_actual_bar": True,
                "suspended": suspended,
                "reference_basis": evaluated["reference_basis"],
                "rule_id": evaluated["rule_id"],
                "limit_up_price": evaluated["limit_up_price"],
                "limit_down_price": evaluated["limit_down_price"],
                "reason": evaluated.get("reason"),
                "association_ref": None,
            })
    return inputs


def _insert_basis(connection: duckdb.DuckDBPyConnection, slice_id: str, membership_snapshot_id: str | None, coverage: float | None, capabilities: dict[str, Any], now: datetime) -> None:
    connection.execute(
        "insert into analysis_daily_basis values (?,?,?,?,?,?,?,?)",
        [slice_id, "LOCAL_RECONSTRUCTED", membership_snapshot_id, "RAW", None, now, coverage, json.dumps(capabilities, ensure_ascii=False, sort_keys=True)],
    )


def _insert_slice(connection: duckdb.DuckDBPyConnection, slice_id: str, domain: str, trade_date: Any, contract_id: str, input_hash: str, dependency_hash: str, basis: dict[str, Any], row_count: int, logical_hash: str, now: datetime) -> None:
    connection.execute(
        "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
        [slice_id, domain, trade_date, contract_id, input_hash, dependency_hash, json.dumps(basis, ensure_ascii=False, sort_keys=True), row_count, logical_hash, "DUCKDB", None, now],
    )


def _insert_dependencies(connection: duckdb.DuckDBPyConnection, slice_id: str, trade_date: Any, inputs: dict[str, str]) -> None:
    for domain, input_slice in sorted(inputs.items()):
        connection.execute("insert into analysis_slice_dependencies values (?,?,?,?)", [slice_id, domain, trade_date, input_slice])


def build(db_path: str | Path = DB_PATH, reference_registry_snapshot_id: str | None = None) -> dict[str, Any]:
    connection = duckdb.connect(str(db_path))
    try:
        publication_id, previous_snapshot_id = _latest_binding(connection)
        registry_snapshot_id = reference_registry_snapshot_id or os.environ.get("M13_REFERENCE_REGISTRY_SNAPSHOT_ID")
        if not registry_snapshot_id:
            return {"status": "BLOCKED_REFERENCE_REGISTRY_ID_REQUIRED", "publication_id": publication_id, "snapshot_id": previous_snapshot_id, "writes": 0}
        hierarchy_source_snapshot_id, hierarchy_version, hierarchy_source_hash = _hierarchy_binding(connection, previous_snapshot_id)
        existing_domains = {row[0] for row in connection.execute("select distinct domain from analysis_snapshot_entries where snapshot_id=?", [previous_snapshot_id]).fetchall()}
        active_registry_row = connection.execute(
            """
            select json_extract_string(s.basis_json, '$.reference_registry_snapshot_id')
              from analysis_snapshot_entries e
              join analysis_slices s on s.slice_id=e.slice_id
             where e.snapshot_id=? and e.domain='limit_ladder'
             order by e.trade_date
             limit 1
            """,
            [previous_snapshot_id],
        ).fetchone()
        active_registry_id = str(active_registry_row[0]) if active_registry_row and active_registry_row[0] else None
        audit_status_row = connection.execute("select audit_status from analysis_snapshot_audit_status where snapshot_id=?", [previous_snapshot_id]).fetchone()
        source_audit_status = str(audit_status_row[0]) if audit_status_row else "ACTIVE"
        if {"market_cycle", "limit_ladder", "limit_promotion"}.issubset(existing_domains) and source_audit_status not in {"BLOCKED", "PENDING_REVIEW"} and active_registry_id == registry_snapshot_id and (not hierarchy_version or hierarchy_source_snapshot_id == previous_snapshot_id):
            return {"status": "ALREADY_BUILT", "publication_id": publication_id, "snapshot_id": previous_snapshot_id}

        technical = _technical_by_date(connection, previous_snapshot_id)
        dates = sorted(_slice_map(connection, previous_snapshot_id, "technical"))
        if not dates:
            return {"status": "BLOCKED_TECHNICAL_INPUT_MISSING", "publication_id": publication_id, "snapshot_id": previous_snapshot_id, "writes": 0}
        references = _reference_map(connection, registry_snapshot_id)
        rules = _rule_map(connection, registry_snapshot_id, references)
        reference_count = len(references)
        rule_count = len(rules)
        if not reference_count:
            return {"status": "BLOCKED_INPUTS_MISSING", "publication_id": publication_id, "snapshot_id": previous_snapshot_id, "reference_registry_snapshot_id": registry_snapshot_id, "market_reference_rows": reference_count, "limit_rule_rows": rule_count, "writes": 0}
        limit_inputs = _limit_inputs(connection, technical, references, rules, registry_snapshot_id)
        limit_by_date: dict[Any, list[dict[str, Any]]] = {}
        for row in limit_inputs:
            limit_by_date.setdefault(_date_key(row["trade_date"]), []).append(row)
        ladder_rows = annotate_promotion_states(derive_limit_ladder_rows(limit_inputs, dates), dates)
        promotion_points = build_promotion_points(ladder_rows, dates)
        high, queues, sectors = _market_supporting_rows(connection, previous_snapshot_id, dates)
        market_points = []
        for trade_date in dates:
            queue_counts, queue_unique = group_queue_counts(queues[trade_date]) if trade_date in queues else ({}, None)
            sector_counts = group_sector_state_counts(sectors[trade_date]) if trade_date in sectors else None
            market_points.append(aggregate_market_point(
                str(trade_date), technical.get(trade_date, []), high_counts=high.get(trade_date, {}),
                queue_counts=queue_counts if trade_date in queues else None,
                queue_unique_count=queue_unique,
                sector_state_counts=sector_counts,
                limit_rows=limit_by_date.get(trade_date, []),
            ))

        output_hash = _digest({"market": market_points, "ladder": ladder_rows, "promotion": promotion_points})
        snapshot_id = "m13-preview-" + _digest({"source_snapshot_id": previous_snapshot_id, "reference_registry_snapshot_id": registry_snapshot_id, "hierarchy_version": hierarchy_version, "hierarchy_source_hash": hierarchy_source_hash, "artifact_version": ARTIFACT_VERSION, "output_hash": output_hash})[:16]
        if connection.execute("select 1 from analysis_snapshots where snapshot_id=?", [snapshot_id]).fetchone():
            return {"status": "ALREADY_BUILT", "publication_id": publication_id, "snapshot_id": snapshot_id, "output_hash": output_hash}

        base = connection.execute("select cutoff_date,query_start,universe_contract,config_hash,manifest_hash from analysis_snapshots where snapshot_id=?", [previous_snapshot_id]).fetchone()
        if not base:
            raise RuntimeError("M13_BASE_SNAPSHOT_MISSING")
        cutoff, query_start, universe_contract, config_hash, previous_manifest_hash = base
        technical_slices = _slice_map(connection, previous_snapshot_id, "technical")
        source_inputs = {"technical": technical_slices[day] for day in dates if day in technical_slices}
        now = datetime.now(timezone.utc)
        input_hash = _digest({"source_snapshot_id": previous_snapshot_id, "reference_registry_snapshot_id": registry_snapshot_id, "source_inputs": source_inputs})
        manifest_hash = _digest({"previous_manifest_hash": previous_manifest_hash, "output_hash": output_hash, "hierarchy_version": hierarchy_version, "hierarchy_source_hash": hierarchy_source_hash})
        connection.execute("begin transaction")
        connection.execute("insert into analysis_snapshots values (?,?,?,?,?,?,?,?)", [snapshot_id, cutoff, query_start, universe_contract, config_hash, manifest_hash, "SUCCESS", now])
        if hierarchy_version:
            connection.execute("insert into analysis_snapshot_hierarchy values (?,?,?,?)", [snapshot_id, hierarchy_version, hierarchy_source_hash, now])
        connection.execute(
            "insert into analysis_snapshot_entries select ?,domain,trade_date,slice_id from analysis_snapshot_entries where snapshot_id=? and domain not in ('market_cycle','limit_ladder','limit_promotion')",
            [snapshot_id, previous_snapshot_id],
        )
        inserted = {"market_cycle": 0, "limit_ladder": 0, "limit_promotion": 0}
        ladder_by_date: dict[Any, list[dict[str, Any]]] = {}
        for row in ladder_rows:
            ladder_by_date.setdefault(_date_key(row["trade_date"]), []).append(row)
        promotion_by_date: dict[Any, list[dict[str, Any]]] = {}
        for row in promotion_points:
            promotion_by_date.setdefault(_date_key(row["trade_date"]), []).append(row)

        for trade_date, point in zip(dates, market_points):
            inputs = {"technical": technical_slices[trade_date]} if trade_date in technical_slices else {}
            slice_id = f"{snapshot_id}-market-cycle-{trade_date:%Y%m%d}"
            basis = {"artifact_version": ARTIFACT_VERSION, "stage": "M13A-MATERIALIZE", "contract_id": MARKET_CONTRACT, "history_basis": "RECONSTRUCTED", "source_snapshot_id": previous_snapshot_id, "reference_registry_snapshot_id": registry_snapshot_id, "input_slices": inputs, "slice_granularity": SLICE_GRANULARITY, "trade_date": str(trade_date)}
            _insert_slice(connection, slice_id, "market_cycle", trade_date, MARKET_CONTRACT, input_hash, _digest(inputs), basis, 1, _digest(point), now)
            connection.execute("insert into market_cycle_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [slice_id, universe_contract, trade_date, MARKET_CONTRACT, point["display_count"], point["quote_valid_count"], point["up_count"], point["down_count"], point["flat_count"], point["amount_sum"], point["amount_valid_count"], point["ma20_above_count"], point["ma20_valid_count"], point["ma60_above_count"], point["ma60_valid_count"], json.dumps(point["new_high_counts"], ensure_ascii=False, sort_keys=True), json.dumps(point["queue_counts"], ensure_ascii=False, sort_keys=True), point["queue_unique_count"], json.dumps(point["sector_state_counts"], ensure_ascii=False, sort_keys=True) if point["sector_state_counts"] is not None else None, point["limit_up_count"], point["limit_down_count"], point["unknown_limit_count"], json.dumps(point["field_coverage"], ensure_ascii=False, sort_keys=True), json.dumps(point["capabilities"], ensure_ascii=False, sort_keys=True)])
            _insert_dependencies(connection, slice_id, trade_date, inputs)
            _insert_basis(connection, slice_id, None, min((value for value in point["field_coverage"].values() if value is not None), default=None), {"stage": "M13A-MATERIALIZE", "contract_id": MARKET_CONTRACT, "history_basis": "RECONSTRUCTED", "input_slices": inputs}, now)
            connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, "market_cycle", trade_date, slice_id])
            inserted["market_cycle"] += 1

        ladder_slices: dict[Any, str] = {}
        for trade_date in dates:
            rows = ladder_by_date.get(trade_date, [])
            inputs = {"technical": technical_slices[trade_date]} if trade_date in technical_slices else {}
            ref_slices = sorted({str(reference["slice_id"]) for key, reference in references.items() if key[1] == trade_date})
            for index, ref_slice in enumerate(ref_slices):
                inputs[f"market_reference_{index}"] = ref_slice
            slice_id = f"{snapshot_id}-limit-ladder-{trade_date:%Y%m%d}"
            ladder_slices[trade_date] = slice_id
            basis = {"artifact_version": ARTIFACT_VERSION, "stage": "M13B-01-MATERIALIZE", "contract_id": LADDER_CONTRACT, "history_basis": "RECONSTRUCTED", "source_snapshot_id": previous_snapshot_id, "reference_registry_snapshot_id": registry_snapshot_id, "input_slices": inputs, "m8c_reference_rows": reference_count, "m8c_rule_rows": rule_count, "slice_granularity": SLICE_GRANULARITY, "trade_date": str(trade_date)}
            _insert_slice(connection, slice_id, "limit_ladder", trade_date, LADDER_CONTRACT, input_hash, _digest(inputs), basis, len(rows), _digest(rows), now)
            for row in rows:
                connection.execute("insert into limit_ladder_daily (slice_id,security_id,trade_date,limit_state,reference_basis,rule_id,limit_up_price,limit_down_price,streak,streak_known,streak_min_known,previous_state,previous_streak,ladder_level,promotion_state,denominator_eligible,exclusion_reason,association_ref,contract_id) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [slice_id, row["security_id"], trade_date, row["limit_state"], row["reference_basis"], row["rule_id"], row["limit_up_price"], row["limit_down_price"], row["streak"], row["streak_known"], row["streak_min_known"], row["previous_state"], row["previous_streak"], row["ladder_level"], row["promotion_state"], row["denominator_eligible"], row["exclusion_reason"], row["association_ref"], LADDER_CONTRACT])
            _insert_dependencies(connection, slice_id, trade_date, inputs)
            _insert_basis(connection, slice_id, None, 1.0 if rows else None, {"stage": "M13B-01-MATERIALIZE", "contract_id": LADDER_CONTRACT, "history_basis": "RECONSTRUCTED", "input_slices": inputs, "m8c_reference_rows": reference_count, "m8c_rule_rows": rule_count}, now)
            connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, "limit_ladder", trade_date, slice_id])
            inserted["limit_ladder"] += len(rows)

        for trade_date in sorted(promotion_by_date):
            rows = promotion_by_date[trade_date]
            inputs = {"limit_ladder_previous": ladder_slices.get(next(day for day in dates if day < trade_date)), "limit_ladder_current": ladder_slices.get(trade_date)}
            inputs = {key: value for key, value in inputs.items() if value}
            slice_id = f"{snapshot_id}-limit-promotion-{trade_date:%Y%m%d}"
            basis = {"artifact_version": ARTIFACT_VERSION, "stage": "M13B-02-MATERIALIZE", "contract_id": PROMOTION_CONTRACT, "history_basis": "RECONSTRUCTED", "source_snapshot_id": previous_snapshot_id, "input_slices": inputs, "slice_granularity": SLICE_GRANULARITY, "trade_date": str(trade_date)}
            _insert_slice(connection, slice_id, "limit_promotion", trade_date, PROMOTION_CONTRACT, input_hash, _digest(inputs), basis, len(rows), _digest(rows), now)
            for row in rows:
                connection.execute("insert into limit_promotion_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?)", [slice_id, row["previous_trade_date"], trade_date, row["previous_level"], row["previous_up_count"], row["previous_unconfirmed_count"], row["success_count"], row["eligible_count"], row["excluded_unknown"], row["excluded_suspended"], row["excluded_no_limit"], row["rate"], PROMOTION_CONTRACT])
            _insert_dependencies(connection, slice_id, trade_date, inputs)
            _insert_basis(connection, slice_id, None, 1.0 if rows else None, {"stage": "M13B-02-MATERIALIZE", "contract_id": PROMOTION_CONTRACT, "history_basis": "RECONSTRUCTED", "input_slices": inputs}, now)
            connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, "limit_promotion", trade_date, slice_id])
            inserted["limit_promotion"] += len(rows)

        connection.execute("delete from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id])
        connection.execute("insert into publication_analysis_snapshots values (?,?,?,?)", [publication_id, "LOCAL_RECONSTRUCTED", snapshot_id, now])
        connection.execute("commit")
        return {"status": "BUILT", "publication_id": publication_id, "snapshot_id": snapshot_id, "source_snapshot_id": previous_snapshot_id, "hierarchy_source_snapshot_id": hierarchy_source_snapshot_id, "hierarchy_version": hierarchy_version, "reference_registry_snapshot_id": registry_snapshot_id, "inserted": inserted, "dates": [str(day) for day in dates], "output_hash": output_hash, "history_basis": "RECONSTRUCTED"}
    except Exception:
        try:
            connection.execute("rollback")
        except Exception:
            pass
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    print(json.dumps(build(reference_registry_snapshot_id=os.environ.get("M13_REFERENCE_REGISTRY_SNAPSHOT_ID")), ensure_ascii=False, indent=2, default=str))
