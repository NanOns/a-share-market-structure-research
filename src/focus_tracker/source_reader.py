"""Read accepted Focus source rows from PostgreSQL runtime heads only."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from psycopg import sql

from src.workbench_db.postgres_repository import PostgresRepository
from .contracts import FocusKey, SOURCE_MEMBERSHIPS, digest, source_item_digest


CONTRACT_ID = "FOCUS_PG_ACCEPTED_SOURCE_READER_V1"


@dataclass(frozen=True)
class SourceRow:
    key: FocusKey
    trade_date: date
    membership: str
    source_item_key: str
    source_item_digest: str
    source_contract_id: str
    source_rank: int | None
    source_focus_class: str | None
    source_facts: dict[str, Any]


@dataclass(frozen=True)
class AcceptedSources:
    trade_date: date
    publication_id: str
    v3_run_id: str | None
    bundle_digest: str | None
    capabilities: dict[str, str]
    rows: tuple[SourceRow, ...]
    source_identity_digest: str


def _add(rows: list[SourceRow], seen: set[tuple[str, str, str]], *,
         key: FocusKey, trade_date: date, membership: str,
         source_item_key: str, source_contract_id: str,
         rank: int | None, focus_class: str | None, facts: dict[str, Any]) -> None:
    if membership not in SOURCE_MEMBERSHIPS[key.source_family]:
        raise ValueError("invalid source membership")
    identity = (key.source_family, key.entity_type, key.entity_id)
    if identity in seen:
        raise ValueError("duplicate source entity")
    seen.add(identity)
    rows.append(SourceRow(key, trade_date, membership, source_item_key,
                          source_item_digest(source_item_key, source_contract_id, facts),
                          source_contract_id, rank, focus_class, facts))


def _assert_no_hot_rank(value: Any) -> None:
    """M14 direct hot-rank evidence must never enter durable Focus rows."""
    if isinstance(value, dict):
        for key, nested in value.items():
            compact = str(key).lower().replace("_", "").replace("-", "")
            if "hotrank" in compact or "heatrank" in compact:
                raise ValueError("request-time hot-rank field in durable source")
            _assert_no_hot_rank(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_hot_rank(nested)


def read_accepted_sources(repository: PostgresRepository, trade_date: date) -> AcceptedSources:
    """Return source rows or fail closed on ambiguous/incomplete authorities."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    rows: list[SourceRow] = []
    seen: set[tuple[str, str, str]] = set()
    capabilities = {family: "UNAVAILABLE" for family in SOURCE_MEMBERSHIPS}
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL("select h.publication_id,p.status from {s}.publication_heads h "
                            "join {s}.publications p using(publication_id) "
                            "where h.trade_date=%s").format(s=schema), (trade_date,))
        head = cur.fetchone()
        if not head or head[1] != "SUCCESS":
            raise ValueError("accepted publication head unavailable")
        publication_id = str(head[0])
        cur.execute(sql.SQL("select run_id,algorithm_version from {s}.research_runs "
                            "where publication_id=%s and trade_date=%s and status='COMPLETE'").format(s=schema),
                    (publication_id, trade_date))
        v3_runs = cur.fetchall()
        if len(v3_runs) > 1:
            raise ValueError("ambiguous V3 research run for accepted publication")
        v3_run_id = str(v3_runs[0][0]) if v3_runs else None
        if v3_run_id:
            v3_contract = str(v3_runs[0][1])
            cur.execute(sql.SQL("select list_type,security_id,rank,primary_sector_id,"
                                "alternative_sector_ids,selection_reason,waiting_for,invalid_if,"
                                "previous_state,change_reason,signal_date "
                                "from {s}.research_shortlist where run_id=%s "
                                "order by list_type,rank,security_id").format(s=schema), (v3_run_id,))
            for (list_type, security_id, rank, primary_sector_id, alternatives,
                 selection_reason, waiting_for, invalid_if, previous_state,
                 change_reason, signal_date) in cur.fetchall():
                family = ("V3_SHORTLIST_INDIVIDUAL" if list_type == "INDIVIDUAL"
                          else "V3_SHORTLIST_STOCK")
                membership = {"CURRENT_FOCUS": "CURRENT", "EARLY_FOCUS": "EARLY",
                              "INDIVIDUAL": "INDIVIDUAL"}.get(str(list_type))
                if membership is None:
                    raise ValueError("unknown shortlist type")
                facts = {"list_type": str(list_type), "rank": int(rank),
                         "primary_sector_id": primary_sector_id,
                         "alternative_sector_ids": alternatives,
                         "selection_reason": selection_reason, "waiting_for": waiting_for,
                         "invalid_if": invalid_if, "previous_state": previous_state,
                         "change_reason": change_reason, "signal_date": signal_date}
                _add(rows, seen, key=FocusKey(family, "STOCK", str(security_id), "V3_SHORTLIST"),
                     trade_date=trade_date, membership=membership,
                     source_item_key=f"{v3_run_id}:{list_type}:{security_id}",
                     source_contract_id=v3_contract, rank=int(rank),
                     focus_class=str(list_type), facts=facts)
            cur.execute(sql.SQL("select sector_id,current_eligible,potential_eligible,"
                                "current_rank,potential_rank,potential_branch,quality,"
                                "member_count,quote_coverage,feature_coverage,reason_codes,evidence,"
                                "input_members_hash,rank_universe_hash "
                                "from {s}.research_sector_states where run_id=%s "
                                "order by sector_id").format(s=schema), (v3_run_id,))
            for (sector_id, current, potential, current_rank, potential_rank,
                 branch, quality, member_count, quote_coverage, feature_coverage,
                 reason_codes, evidence, members_hash, universe_hash) in cur.fetchall():
                membership = "CURRENT" if current is True else "EARLY" if potential is True else None
                if membership is None:
                    continue
                rank = current_rank if membership == "CURRENT" else potential_rank
                facts = {"current_eligible": current, "potential_eligible": potential,
                         "current_rank": current_rank, "potential_rank": potential_rank,
                         "potential_branch": branch, "quality": quality,
                         "member_count": member_count, "quote_coverage": quote_coverage,
                         "feature_coverage": feature_coverage, "reason_codes": reason_codes,
                         "evidence": evidence, "input_members_hash": members_hash,
                         "rank_universe_hash": universe_hash}
                _add(rows, seen, key=FocusKey("V3_SECTOR_TRACK", "SECTOR", str(sector_id), "V3_SECTOR"),
                     trade_date=trade_date, membership=membership,
                     source_item_key=f"{v3_run_id}:{sector_id}", source_contract_id=v3_contract,
                     rank=int(rank) if rank is not None else None,
                     focus_class="CURRENT_SECTOR" if current is True else "EARLY_SECTOR",
                     facts=facts)
            for family in ("V3_SHORTLIST_STOCK", "V3_SHORTLIST_INDIVIDUAL", "V3_SECTOR_TRACK"):
                capabilities[family] = "COMPLETE"
        cur.execute(sql.SQL("select b.bundle_digest,r.bundle_contract_id,r.result_count,r.status "
                            "from {s}.research_bundle_heads b "
                            "join {s}.research_runs_v3_3 r using(bundle_digest) "
                            "where b.trade_date=%s and b.publication_id=%s").format(s=schema),
                    (trade_date, publication_id))
        bundle_heads = cur.fetchall()
        if len(bundle_heads) > 1:
            raise ValueError("ambiguous V3.3 bundle head")
        bundle_digest = None
        if bundle_heads:
            bundle_digest, bundle_contract, expected_count, status = bundle_heads[0]
            if status != "COMPLETE":
                raise ValueError("V3.3 bundle head not complete")
            bundle_digest = str(bundle_digest)
            cur.execute(sql.SQL("select security_id,primary_category,category_rank,"
                                "rank_status,selection_mode,sector_support_status,risk_codes,"
                                "factor_evidence,scanner_evidence,result_payload "
                                "from {s}.research_candidates_v3_3 where bundle_digest=%s "
                                "order by security_id").format(s=schema), (bundle_digest,))
            candidates = cur.fetchall()
            if len(candidates) != int(expected_count):
                raise ValueError("V3.3 candidate count differs from accepted head")
            for (security_id, category, category_rank, rank_status, selection_mode,
                 support, risk_codes, factor_evidence, scanner_evidence, result_payload) in candidates:
                _assert_no_hot_rank(result_payload)
                if not isinstance(result_payload, dict):
                    raise ValueError("V3.3 candidate result payload missing")
                facts = {"primary_category": category, "category_rank": category_rank,
                         "matched_categories": result_payload.get("matched_categories"),
                         "matched_stock_only_categories": result_payload.get("matched_stock_only_categories"),
                         "rank_status": rank_status, "selection_mode": selection_mode,
                         "sector_support_status": support, "risk_codes": risk_codes,
                         "factor_evidence": factor_evidence, "scanner_evidence": scanner_evidence}
                _assert_no_hot_rank(facts)
                _add(rows, seen,
                     key=FocusKey("V3_3_TODAY_CANDIDATE", "STOCK", str(security_id), "V3_3"),
                     trade_date=trade_date, membership="CANDIDATE",
                     source_item_key=f"{bundle_digest}:{security_id}",
                     source_contract_id=str(bundle_contract),
                     rank=int(category_rank) if category_rank is not None else None,
                     focus_class=str(category) if category is not None else None, facts=facts)
            capabilities["V3_3_TODAY_CANDIDATE"] = "COMPLETE"
    identity = {"contract": CONTRACT_ID, "trade_date": trade_date,
                "publication_id": publication_id, "v3_run_id": v3_run_id,
                "bundle_digest": bundle_digest, "capabilities": capabilities,
                "rows": [(row.key.source_family, row.key.entity_type, row.key.entity_id,
                          row.source_item_digest) for row in rows]}
    return AcceptedSources(trade_date, publication_id, v3_run_id, bundle_digest,
                           capabilities, tuple(rows), digest(identity))
