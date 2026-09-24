"""Immutable entry-basket writes and accepted-head reads."""
from __future__ import annotations

import json

from psycopg import sql

from .contracts import SOURCE_AUTHORITY_CONTRACT, digest
from .sector_basket import CONTRACT_ID as BASKET_CONTRACT, SectorBasket


STORE_CONTRACT_ID = "FOCUS_EPISODE_BASKET_V1"


def _assert_basket(basket: SectorBasket, publication_id: str) -> None:
    members = basket.security_ids
    if not members or tuple(sorted(set(members))) != members:
        raise ValueError("entry basket members must be sorted and unique")
    expected = digest({"contract": BASKET_CONTRACT,
                       "publication_id": publication_id,
                       "sector_id": basket.sector_id,
                       "source_kind": basket.source_kind,
                       "source_identity": basket.source_identity,
                       "members": members})
    if basket.basket_digest != expected:
        raise ValueError("entry basket digest mismatch")


def insert_entry_basket(repository, *, episode_id: str, focus_run_id: str,
                        publication_id: str, basket: SectorBasket) -> None:
    """Caller owns transaction; same key/content is idempotent, conflict fails."""
    _assert_basket(basket, publication_id)
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select e.entity_type,e.entity_id,e.first_trade_date,r.trade_date,"
            "r.publication_id from {}.focus_episodes e "
            "join {}.focus_runs r on r.focus_run_id=%s "
            "where e.episode_id=%s").format(schema, schema),
            (focus_run_id, episode_id))
        identity = cur.fetchone()
        if (identity is None or identity[0] != "SECTOR" or
                str(identity[1]) != basket.sector_id or identity[2] != identity[3] or
                str(identity[4]) != publication_id):
            raise ValueError("entry basket episode/run/publication mismatch")
        cur.execute(sql.SQL(
            "insert into {}.focus_episode_baskets "
            "(episode_id,focus_run_id,publication_id,source_kind,source_identity,"
            "member_ids,member_count,basket_digest) "
            "values (%s,%s,%s,%s,%s,%s::jsonb,%s,%s) "
            "on conflict (episode_id,focus_run_id) do nothing").format(schema),
            (episode_id, focus_run_id, publication_id, basket.source_kind,
             basket.source_identity, json.dumps(list(basket.security_ids)),
             len(basket.security_ids), basket.basket_digest))
        cur.execute(sql.SQL(
            "select publication_id,source_kind,source_identity,member_ids,"
            "member_count,basket_digest from {}.focus_episode_baskets "
            "where episode_id=%s and focus_run_id=%s").format(schema),
            (episode_id, focus_run_id))
        row = cur.fetchone()
    if row is None or (str(row[0]), str(row[1]), str(row[2]), tuple(row[3]),
                       int(row[4]), str(row[5])) != (
        publication_id, basket.source_kind, basket.source_identity,
        basket.security_ids, len(basket.security_ids), basket.basket_digest
    ):
        raise ValueError("immutable entry basket conflict")


def read_accepted_entry_basket(repository, episode_id: str) -> SectorBasket:
    """Resolve first-day basket via accepted Focus head, including revisions."""
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    schema = sql.Identifier(repository.schema)
    with repository.connection.cursor() as cur:
        cur.execute(sql.SQL(
            "select e.entity_id,h.lineage_state,b.publication_id,b.source_kind,"
            "b.source_identity,b.member_ids,b.member_count,b.basket_digest "
            "from {}.focus_episodes e "
            "join {}.focus_trade_date_heads h on h.trade_date=e.first_trade_date "
            "and h.source_authority_contract_id=%s "
            "join {}.focus_episode_baskets b on b.episode_id=e.episode_id "
            "and b.focus_run_id=h.accepted_focus_run_id "
            "where e.episode_id=%s and e.entity_type='SECTOR'").format(schema, schema, schema),
            (SOURCE_AUTHORITY_CONTRACT, episode_id))
        row = cur.fetchone()
    if row is None:
        raise ValueError("accepted entry basket unavailable")
    sector_id, lineage, publication, source_kind, source_identity, member_ids, count, basket_digest = row
    if lineage != "VALID" or len(member_ids) != count:
        raise ValueError("accepted entry basket lineage or count invalid")
    basket = SectorBasket(str(sector_id), tuple(member_ids), str(source_kind),
                          str(source_identity), str(basket_digest))
    _assert_basket(basket, str(publication))
    return basket
