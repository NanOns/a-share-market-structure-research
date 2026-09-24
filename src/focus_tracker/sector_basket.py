"""Publication-bound sector basket identity for offline Focus facts."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from psycopg import sql

from .contracts import digest


CONTRACT_ID = "FOCUS_SECTOR_BASKET_SOURCE_V1"


@dataclass(frozen=True)
class SectorBasket:
    sector_id: str
    security_ids: tuple[str, ...]
    source_kind: str
    source_identity: str
    basket_digest: str


@dataclass(frozen=True)
class SectorOneDay:
    sector_id: str
    basket_digest: str
    member_count: int
    evaluable_count: int
    coverage: Decimal
    median_return: Decimal | None
    quality_status: str


def one_day_sector_return(basket: SectorBasket,
                          member_returns: Mapping[str, Decimal | None],
                          *, minimum_coverage: Decimal = Decimal("0.80")) -> SectorOneDay:
    """Equal-member median; no synthetic price for missing members."""
    members = basket.security_ids
    if not members or len(set(members)) != len(members):
        raise ValueError("invalid frozen sector basket")
    returns = []
    for security in members:
        value = member_returns.get(security)
        if value is not None:
            if not value.is_finite() or value <= -1:
                raise ValueError("invalid actual member return")
            returns.append(value)
    count = len(returns)
    coverage = Decimal(count) / Decimal(len(members))
    if coverage < minimum_coverage or not count:
        return SectorOneDay(basket.sector_id, basket.basket_digest, len(members),
                            count, coverage, None, "DATA_UNAVAILABLE")
    returns.sort()
    midpoint = count // 2
    median = (returns[midpoint] if count % 2 else
              (returns[midpoint - 1] + returns[midpoint]) / Decimal(2))
    return SectorOneDay(basket.sector_id, basket.basket_digest, len(members),
                        count, coverage, median, "READY")


def baskets_from_accepted_publication(repository, publication_id: str,
                                      sector_ids: set[str]) -> tuple[SectorBasket, ...]:
    """Use the publication's snapshot, or its bound relation revision when empty.

    The fallback matches the existing research reader's relation binding and
    never resolves a mutable latest relation revision by time.
    """
    if repository.connection is None:
        raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
    edges = repository.relation_edges_for_publication(publication_id)
    if edges:
        bindings = {(str(scope), int(rev)) for _, scope, rev, *_ in edges}
        if len(bindings) != 1:
            raise ValueError("ambiguous relation publication binding")
        scope, revision = next(iter(bindings))
        source_kind, source_identity = "BOUND_RELATION_REVISION", f"{scope}:{revision}"
        pairs = [(str(sector), str(security)) for _, _, _, sector, security, *_ in edges]
    else:
        with repository.connection.cursor() as cur:
            cur.execute(sql.SQL("select membership_snapshot_id from {}.publication_memberships "
                                "where publication_id=%s").format(sql.Identifier(repository.schema)),
                        (publication_id,))
            row = cur.fetchone()
        if row is None:
            raise ValueError("accepted publication has no sector relation binding")
        snapshot_id = str(row[0])
        entries = repository.membership_entry_rows(snapshot_id)
        if not entries:
            raise ValueError("bound membership snapshot has no entries")
        source_kind, source_identity = "MEMBERSHIP_SNAPSHOT", snapshot_id
        pairs = [(str(sector), str(security)) for _, sector, security, _ in entries]
    by_sector: dict[str, set[str]] = {sector: set() for sector in sector_ids}
    for sector, security in pairs:
        if sector in by_sector:
            by_sector[sector].add(security)
    result = []
    for sector in sorted(by_sector):
        members = tuple(sorted(by_sector[sector]))
        if not members:
            raise ValueError(f"selected sector has no bound members: {sector}")
        basket_digest = digest({"contract": CONTRACT_ID, "publication_id": publication_id,
                                "sector_id": sector, "source_kind": source_kind,
                                "source_identity": source_identity, "members": members})
        result.append(SectorBasket(sector, members, source_kind, source_identity, basket_digest))
    return tuple(result)
