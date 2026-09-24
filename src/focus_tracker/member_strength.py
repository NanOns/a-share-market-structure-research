"""Accepted M9 strong-member facts for Focus sector width."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping

from psycopg import sql

from .contracts import digest
from .sector_basket import SectorBasket


CONTRACT_ID = "FOCUS_ACCEPTED_MEMBER_STRENGTH_V1"
SOURCE_MEMBER_CONTRACT = "SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC"
RESULT_SEMANTIC_CONTRACT = "MEMBER_STATE_RESULT_V3"


@dataclass(frozen=True)
class SectorStrength:
    sector_id: str
    source_snapshot_id: str
    source_result_object_id: str
    source_value_hash: str
    source_member_contract: str
    member_count: int
    evaluable_count: int
    strong_count: int
    width: Decimal | None
    strong_security_ids: tuple[str, ...]
    evaluable_security_ids: tuple[str, ...]
    quality_status: str
    fact_digest: str


def read_accepted_member_strength(repository, *, trade_date: date,
                                  publication_id: str, domain: str,
                                  baskets: Mapping[str, SectorBasket]) -> dict[str, SectorStrength]:
    """Read one accepted snapshot, with exact publication and basket matching."""
    if domain not in {"LOCAL_OBSERVED", "LOCAL_RECONSTRUCTED"}:
        raise ValueError("analysis domain must be explicit")
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    if not baskets:
        return {}
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select h.snapshot_id,s.status,s.cutoff_date,e.slice_id,"
            "b.result_object_id,o.domain,o.semantic_contract,o.value_hash,o.row_count "
            "from {}.analysis_snapshot_heads h "
            "join {}.analysis_snapshots s using(snapshot_id) "
            "join {}.analysis_snapshot_entries e on e.snapshot_id=h.snapshot_id "
            "and e.domain='member_state' and e.trade_date=h.trade_date "
            "join {}.analysis_slice_result_bindings b on b.slice_id=e.slice_id "
            "join {}.analysis_result_objects o on o.result_object_id=b.result_object_id "
            "where h.trade_date=%s and h.publication_id=%s and h.domain=%s"
        ).format(schema, schema, schema, schema, schema),
            (trade_date, publication_id, domain))
        head = cur.fetchall()
        if len(head) != 1:
            raise ValueError("accepted member-state snapshot unavailable or ambiguous")
        snapshot_id, status, cutoff, slice_id, result_id, result_domain, semantic, value_hash, expected_rows = head[0]
        if (status != "SUCCESS" or cutoff != trade_date or
                result_domain != "member_state" or
                semantic != RESULT_SEMANTIC_CONTRACT):
            raise ValueError("member-state snapshot identity mismatch")
        cur.execute(sql.SQL(
            "select count(*) from {}.member_state_result_rows "
            "where result_object_id=%s and trade_date=%s").format(schema),
            (result_id, trade_date))
        if int(cur.fetchone()[0]) != int(expected_rows):
            raise ValueError("accepted member-state result row count mismatch")
        cur.execute(sql.SQL(
            "select sector_id,security_id,member_present,strong_state,contract_id "
            "from {}.member_state_result_rows "
            "where result_object_id=%s and trade_date=%s and sector_id=any(%s) "
            "order by sector_id,security_id").format(schema),
            (result_id, trade_date, sorted({basket.sector_id
                                            for basket in baskets.values()})))
        source_rows = cur.fetchall()
    grouped: dict[str, dict[str, bool | None]] = {
        sector: {} for sector in {basket.sector_id for basket in baskets.values()}}
    for sector, security, present, strong, row_contract in source_rows:
        sector, security = str(sector), str(security)
        if row_contract != SOURCE_MEMBER_CONTRACT:
            raise ValueError("unrecognized strong-member predicate contract")
        if security in grouped[sector]:
            raise ValueError("duplicate accepted member-state key")
        if present:
            grouped[sector][security] = strong
    result = {}
    for basket_key, basket in baskets.items():
        sector = basket.sector_id
        provider_members = grouped[sector]
        expected_members = set(basket.security_ids)
        # The accepted M9 slice can include current entrants that are outside
        # this episode's immutable entry basket. They must not affect its
        # width. A frozen member absent from the current slice remains unknown;
        # the existing coverage threshold decides whether width is usable.
        provider_extras = sorted(set(provider_members) - expected_members)
        missing_members = sorted(expected_members - set(provider_members))
        members = {sid: provider_members.get(sid) for sid in sorted(expected_members)}
        evaluable = sum(value is not None for value in members.values())
        strong_ids = tuple(sorted(sid for sid, value in members.items() if value is True))
        evaluable_ids = tuple(sorted(sid for sid, value in members.items()
                                    if value is not None))
        coverage = Decimal(evaluable) / Decimal(len(basket.security_ids))
        width = (Decimal(len(strong_ids)) / Decimal(evaluable)
                 if evaluable and coverage >= Decimal("0.80") else None)
        quality = "READY" if width is not None else "DATA_UNAVAILABLE"
        evidence = {"contract": CONTRACT_ID, "trade_date": trade_date,
                    "publication_id": publication_id, "snapshot_id": str(snapshot_id),
                    "slice_id": str(slice_id), "result_object_id": str(result_id),
                    "result_value_hash": str(value_hash), "result_semantic_contract": str(semantic),
                    "member_contract": SOURCE_MEMBER_CONTRACT,
                    "sector_id": sector, "basket_digest": basket.basket_digest,
                    "missing_frozen_member_ids": missing_members,
                    "provider_extra_member_ids": provider_extras,
                    "member_states": [(sid, members[sid]) for sid in sorted(members)]}
        result[basket_key] = SectorStrength(
            sector, str(snapshot_id), str(result_id), str(value_hash),
            SOURCE_MEMBER_CONTRACT, len(basket.security_ids), evaluable, len(strong_ids),
            width, strong_ids, evaluable_ids, quality, digest(evidence))
    return result


def strength_retention(*, previous: SectorStrength, current: SectorStrength,
                       previous_basket: SectorBasket,
                       current_basket: SectorBasket) -> Decimal | None:
    """Preserve U when membership or a previously strong member is unknown."""
    if previous.sector_id != current.sector_id or previous_basket.sector_id != current_basket.sector_id:
        raise ValueError("sector identity mismatch")
    prior_members = set(previous_basket.security_ids)
    now_members = set(current_basket.security_ids)
    union = prior_members | now_members
    if not union or Decimal(len(prior_members & now_members)) / Decimal(len(union)) < Decimal("0.90"):
        return None
    if previous.quality_status != "READY" or current.quality_status != "READY":
        return None
    prior_strong = set(previous.strong_security_ids)
    if not prior_strong or not prior_strong <= set(current.evaluable_security_ids):
        return None
    return Decimal(len(prior_strong & set(current.strong_security_ids))) / Decimal(len(prior_strong))
