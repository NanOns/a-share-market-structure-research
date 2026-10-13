"""Versioned identities used only by the V4-05 R4 replay repair."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Iterable, Mapping


def digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), default=str).encode()).hexdigest()


def accepted_universe_snapshot_id(rows: Iterable[Mapping]) -> str:
    """V4-03 identity: security + membership basis + source revision + eligibility."""
    identity = sorted((row["security_id"], row.get("membership_basis"),
                       row.get("source_revision_id"), row.get("eligibility_status"))
                      for row in rows)
    return digest(identity)


def target_market_snapshot_id(target_trade_date: str, rows: Iterable[Mapping]) -> str:
    """Date-qualified R4 target contract; target rows are not V4-01 PIT rows."""
    identity = sorted((row["security_id"], row["source_security_key"],
                       row["membership_basis"], row["source_revision_id"],
                       row["eligibility_status"]) for row in rows)
    return digest({"contract_id": "V4_05_TARGET_MARKET_SNAPSHOT_IDENTITY_V1",
                   "target_trade_date": target_trade_date, "identities": identity})


def adjustment_basis_id(rows: Iterable[tuple[str, str, str, str]]) -> str:
    """Hash evaluable security endpoints and their coordinate/source basis."""
    return digest(sorted((security_id, coordinate_basis, gbbq_identity, raw_package_identity)
                         for security_id, coordinate_basis, gbbq_identity, raw_package_identity in rows))
