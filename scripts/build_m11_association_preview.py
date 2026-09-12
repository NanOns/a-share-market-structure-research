"""Build the M11-03 association domain from one bound local snapshot.

The builder creates a new reconstructed preview snapshot, reuses all prior
domain slices, and adds one immutable association slice per trade date.  It
does not read or modify any TDX source directory.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_service.association import CONTRACT_ID, evaluate_relation, rank_associations
from workbench_service.universe import is_a_share_security_id


DB_PATH = ROOT / "data/database/market_research.duckdb"
ARTIFACT_VERSION = "M11_ASSOCIATION_PREVIEW_V1"
SLICE_GRANULARITY = "DOMAIN_DATE_BASIS_V1"


def _digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _rows(connection: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor = connection.execute(sql, params)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _latest_binding(connection: duckdb.DuckDBPyConnection) -> tuple[str, str]:
    row = connection.execute(
        """
        with current_publication as (
            select pas.publication_id
              from publication_analysis_snapshots pas
              join publications p on p.publication_id=pas.publication_id
             where pas.domain='LOCAL_RECONSTRUCTED' and p.status='SUCCESS'
             order by pas.bound_at desc
             limit 1
        )
        select current_publication.publication_id, s.snapshot_id
          from current_publication
          cross join analysis_snapshots s
         where s.status='SUCCESS'
           and not exists (
               select 1
                 from analysis_snapshot_entries existing_association
                where existing_association.snapshot_id=s.snapshot_id
                  and existing_association.domain='association'
           )
           and exists (select 1 from analysis_snapshot_entries e where e.snapshot_id=s.snapshot_id and e.domain='sector_base')
           and exists (select 1 from analysis_snapshot_entries e where e.snapshot_id=s.snapshot_id and e.domain='member_state')
           and exists (select 1 from analysis_snapshot_entries e where e.snapshot_id=s.snapshot_id and e.domain='technical')
           and exists (select 1 from analysis_snapshot_entries e where e.snapshot_id=s.snapshot_id and e.domain='mainline')
         order by s.created_at desc
         limit 1
        """
    ).fetchone()
    if not row:
        raise RuntimeError("LOCAL_RECONSTRUCTED_BINDING_MISSING")
    return str(row[0]), str(row[1])


def _slice_for_date(connection: duckdb.DuckDBPyConnection, snapshot_id: str, domain: str, trade_date: object) -> str:
    row = connection.execute(
        """
        select slice_id
          from analysis_snapshot_entries
         where snapshot_id=? and domain=? and trade_date=?
        """,
        [snapshot_id, domain, trade_date],
    ).fetchone()
    if not row:
        raise RuntimeError(f"M11_INPUT_SLICE_MISSING:{domain}:{trade_date}")
    return str(row[0])


def _build_daily_rows(connection: duckdb.DuckDBPyConnection, snapshot_id: str, trade_date: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    base_slice = _slice_for_date(connection, snapshot_id, "sector_base", trade_date)
    member_slice = _slice_for_date(connection, snapshot_id, "member_state", trade_date)
    technical_slice = _slice_for_date(connection, snapshot_id, "technical", trade_date)
    mainline_slice = _slice_for_date(connection, snapshot_id, "mainline", trade_date)
    membership_snapshot_row = connection.execute(
        "select membership_snapshot_id from analysis_daily_basis where slice_id=?",
        [member_slice],
    ).fetchone()
    membership_snapshot_id = str(membership_snapshot_row[0]) if membership_snapshot_row and membership_snapshot_row[0] else ""
    base_rows = _rows(
        connection,
        """
        select sector_id,sector_name,sector_type,sector_role,bucket,sector_valid,
               coverage,sector_rs5_pct,sector_rs20_pct
          from sector_base_daily
         where slice_id=? and trade_date=?
        """,
        [base_slice, trade_date],
    )
    mainline_rows = _rows(
        connection,
        "select sector_id,mainline_class from mainline_daily where slice_id=? and trade_date=?",
        [mainline_slice, trade_date],
    )
    mainline_by_sector = {str(row["sector_id"]): row["mainline_class"] for row in mainline_rows}
    member_rows = _rows(
        connection,
        """
        select sector_id,security_id,member_rank,rank_valid_count,member_present
          from sector_member_state_daily
         where slice_id=? and trade_date=? and member_present=true
        """,
        [member_slice, trade_date],
    )
    security_ids = sorted({str(row["security_id"]) for row in member_rows if is_a_share_security_id(row["security_id"])})
    technical_by_security: dict[str, dict[str, Any]] = {}
    if security_ids:
        placeholders = ",".join("?" for _ in security_ids)
        technical_rows = _rows(
            connection,
            f"""
            select security_id,ret5,ret20,rs5,rs20,validity,quality_codes
              from technical_result_daily
             where slice_id=? and trade_date=? and security_id in ({placeholders})
            """,
            [technical_slice, trade_date, *security_ids],
        )
        technical_by_security = {str(row["security_id"]): row for row in technical_rows}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in member_rows:
        security_id = str(row["security_id"])
        if is_a_share_security_id(security_id):
            tech = technical_by_security.get(security_id, {})
            grouped.setdefault(str(row["sector_id"]), []).append(
                {
                    "security_id": security_id,
                    "member_rank": row["member_rank"],
                    "rank_valid_count": row["rank_valid_count"],
                    "ret5": tech.get("ret5"),
                    "ret20": tech.get("ret20"),
                    "quality_codes": tech.get("quality_codes"),
                }
            )
    evaluated: list[dict[str, Any]] = []
    for sector in base_rows:
        sector_id = str(sector["sector_id"])
        sector["semantic_bucket"] = sector.get("bucket")
        sector["mainline_class"] = mainline_by_sector.get(sector_id)
        for security_id in sorted({str(row["security_id"]) for row in grouped.get(sector_id, [])}):
            result = evaluate_relation(sector, security_id, grouped.get(sector_id, []))
            result["trade_date"] = trade_date
            result["history_basis"] = "RECONSTRUCTED"
            result["membership_snapshot_id"] = membership_snapshot_id
            evaluated.append(result)
    return rank_associations(evaluated), {
        "sector_base": base_slice,
        "member_state": member_slice,
        "technical": technical_slice,
        "mainline": mainline_slice,
    }


def _insert_association_rows(connection: duckdb.DuckDBPyConnection, slice_id: str, rows: list[dict[str, Any]]) -> int:
    for row in rows:
        connection.execute(
            """
            insert into stock_sector_associations_daily
                (slice_id,security_id,sector_id,trade_date,sector_name,sector_type,
                 semantic_bucket,association_rank,eligible,rejection_reasons,pattern,
                 member_rank,member_rank_valid_count,member_percentile,sector_coverage,
                 sector_rs5_pct,sector_rs20_pct,loo_ret20_median,loo_breadth20,
                 loo_ret5_median,loo_breadth5,evidence_json,contract_id,history_basis,
                 membership_snapshot_id)
            values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                slice_id,
                row["security_id"],
                row["sector_id"],
                row["trade_date"],
                row["sector_name"],
                row["sector_type"],
                row["semantic_bucket"],
                row.get("association_rank"),
                bool(row["eligible"]),
                json.dumps(row["rejection_reasons"], ensure_ascii=False, sort_keys=True),
                row.get("pattern"),
                row.get("member_rank"),
                row.get("member_rank_valid_count", 0),
                row.get("member_percentile"),
                row.get("sector_coverage"),
                row.get("sector_rs5_pct"),
                row.get("sector_rs20_pct"),
                row.get("loo_ret20_median"),
                row.get("loo_breadth20"),
                row.get("loo_ret5_median"),
                row.get("loo_breadth5"),
                json.dumps(row["evidence"], ensure_ascii=False, sort_keys=True),
                CONTRACT_ID,
                row["history_basis"],
                row["membership_snapshot_id"],
            ],
        )
    return len(rows)


def build() -> dict[str, Any]:
    connection = duckdb.connect(str(DB_PATH))
    try:
        publication_id, previous_snapshot_id = _latest_binding(connection)
        dates = [row[0] for row in connection.execute(
            "select trade_date from analysis_snapshot_entries where snapshot_id=? and domain='member_state' order by trade_date",
            [previous_snapshot_id],
        ).fetchall()]
        if not dates:
            raise RuntimeError("M11_MEMBER_STATE_DATES_MISSING")
        daily: dict[object, tuple[list[dict[str, Any]], dict[str, str]]] = {}
        all_rows: list[dict[str, Any]] = []
        for trade_date in dates:
            rows, inputs = _build_daily_rows(connection, previous_snapshot_id, trade_date)
            daily[trade_date] = (rows, inputs)
            all_rows.extend(rows)
        frame_hash = _digest(
            [
                {
                    key: value
                    for key, value in row.items()
                    if key not in {"evidence"}
                }
                for row in sorted(all_rows, key=lambda item: (str(item["trade_date"]), item["security_id"], item["sector_id"]))
            ]
        )
        snapshot_id = "m11-association-preview-" + _digest({"previous_snapshot_id": previous_snapshot_id, "frame_hash": frame_hash})[:16]
        if connection.execute("select 1 from analysis_snapshots where snapshot_id=?", [snapshot_id]).fetchone():
            return {"status": "ALREADY_BUILT", "publication_id": publication_id, "snapshot_id": snapshot_id, "rows": len(all_rows)}
        base = connection.execute(
            "select cutoff_date,query_start,universe_contract,config_hash,manifest_hash from analysis_snapshots where snapshot_id=?",
            [previous_snapshot_id],
        ).fetchone()
        if not base:
            raise RuntimeError("M11_BASE_SNAPSHOT_MISSING")
        cutoff, query_start, universe_contract, previous_config_hash, previous_manifest_hash = base
        now = datetime.now(timezone.utc)
        manifest_hash = _digest({"previous_manifest_hash": previous_manifest_hash, "association_frame_hash": frame_hash})
        input_hash = _digest({"previous_snapshot_id": previous_snapshot_id, "association_frame_hash": frame_hash})

        connection.execute("begin transaction")
        connection.execute(
            "insert into analysis_snapshots values (?,?,?,?,?,?,?,?)",
            [snapshot_id, cutoff, query_start, universe_contract, previous_config_hash, manifest_hash, "SUCCESS", now],
        )
        connection.execute(
            "insert into analysis_snapshot_entries select ?,domain,trade_date,slice_id from analysis_snapshot_entries where snapshot_id=?",
            [snapshot_id, previous_snapshot_id],
        )
        if connection.execute("select count(*) from information_schema.tables where table_name='analysis_snapshot_hierarchy'").fetchone()[0]:
            connection.execute(
                "insert into analysis_snapshot_hierarchy select ?,hierarchy_version,source_hash,bound_at from analysis_snapshot_hierarchy where snapshot_id=?",
                [snapshot_id, previous_snapshot_id],
            )
        inserted = 0
        for trade_date, (rows, inputs) in daily.items():
            slice_id = f"{snapshot_id}-association-{trade_date.strftime('%Y%m%d')}"
            basis = {
                "artifact_version": ARTIFACT_VERSION,
                "stage": "M11-03",
                "contract_id": CONTRACT_ID,
                "history_basis": "RECONSTRUCTED",
                "source": "LOCAL_DUCKDB_ANALYSIS_SLICES",
                "tdx_source_modified": False,
                "source_snapshot_id": previous_snapshot_id,
                "input_slices": inputs,
                "slice_granularity": SLICE_GRANULARITY,
                "trade_date": str(trade_date),
                "frame_hash": _digest(rows),
            }
            dependency_hash = _digest(sorted(inputs.items()))
            connection.execute(
                "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
                [slice_id, "association", trade_date, CONTRACT_ID, input_hash, dependency_hash, json.dumps(basis, ensure_ascii=False, sort_keys=True), len(rows), _digest(rows), "DUCKDB", None, now],
            )
            inserted += _insert_association_rows(connection, slice_id, rows)
            for domain, input_slice in sorted(inputs.items()):
                connection.execute("insert into analysis_slice_dependencies values (?,?,?,?)", [slice_id, domain, trade_date, input_slice])
            connection.execute(
                "insert into analysis_daily_basis values (?,?,?,?,?,?,?,?)",
                [slice_id, "LOCAL_RECONSTRUCTED", rows[0]["membership_snapshot_id"] if rows else None, "TDX_NATIVE_QFQ", trade_date, now, 1.0, json.dumps({"stage": "M11-03", "contract_id": CONTRACT_ID, "history_basis": "RECONSTRUCTED", "source_snapshot_id": previous_snapshot_id, "input_slices": inputs}, ensure_ascii=False, sort_keys=True)],
            )
            connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", [snapshot_id, "association", trade_date, slice_id])
        connection.execute("delete from publication_analysis_snapshots where publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id])
        connection.execute("insert into publication_analysis_snapshots values (?,?,?,?)", [publication_id, "LOCAL_RECONSTRUCTED", snapshot_id, now])
        connection.execute("commit")
        eligible = sum(1 for row in all_rows if row["eligible"])
        return {"status": "BUILT", "stage": "M11-03", "publication_id": publication_id, "snapshot_id": snapshot_id, "source_snapshot_id": previous_snapshot_id, "rows": inserted, "eligible_rows": eligible, "rejected_rows": inserted - eligible, "dates": [str(value) for value in dates], "history_basis": "RECONSTRUCTED"}
    except Exception:
        try:
            connection.execute("rollback")
        except Exception:
            pass
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, default=str))
