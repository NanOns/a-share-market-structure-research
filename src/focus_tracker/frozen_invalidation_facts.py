"""Immutable V3.3 signal-day operands for Focus invalidation V1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import struct

from .contracts import SOURCE_AUTHORITY_CONTRACT, digest


CONTRACT_ID = "FOCUS_V33_FROZEN_INVALIDATION_FACTS_V1"
FACT_KEYS = ("frozen_phh20", "frozen_pullback_invalid_low",
             "frozen_trend_key_low", "reclaimed_ma_kind")


@dataclass(frozen=True)
class FrozenFact:
    key: str
    value: str | None
    fact_type: str
    source_fact_digest: str
    frozen_at_trade_date: date
    reason: str


def _price(value) -> str | None:
    if isinstance(value, dict) and set(value) == {"$binary64"}:
        try:
            value = struct.unpack(">d", bytes.fromhex(value["$binary64"]))[0]
        except (TypeError, ValueError, struct.error):
            return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return str(number) if number.is_finite() and number > 0 else None


def derive_frozen_facts(row) -> tuple[FrozenFact, ...]:
    """Use only explicit source operands; never substitute another threshold."""
    if row.key.source_family != "V3_3_TODAY_CANDIDATE":
        return ()
    factor = row.source_facts.get("factor_evidence")
    if not isinstance(factor, dict):
        factor = {}
    category = row.source_facts.get("primary_category")
    values = {key: None for key in FACT_KEYS}
    if category == "LAUNCH_CONFIRM":
        values["frozen_phh20"] = _price(factor.get("phh20"))
    elif category == "STRONG_PULLBACK":
        values["frozen_pullback_invalid_low"] = _price(factor.get("pullback_invalid_low"))
    elif category == "TREND_CONTINUE":
        values["frozen_trend_key_low"] = _price(factor.get("trend_key_low"))
    elif category == "RECOVERY_TURN":
        scanner = row.source_facts.get("scanner_evidence") or {}
        recovery = scanner.get("recovery_turn") if isinstance(scanner, dict) else None
        if isinstance(recovery, dict):
            r5, r20 = recovery.get("r5"), recovery.get("r20")
            # Both branches true have no unique signal-day MA identity.
            if r5 is True and r20 is False:
                values["reclaimed_ma_kind"] = "MA5"
            elif r20 is True and r5 is False:
                values["reclaimed_ma_kind"] = "MA20"
    return tuple(FrozenFact(
        key=key, value=value,
        fact_type="MA_IDENTITY" if key == "reclaimed_ma_kind" else "PRICE",
        source_fact_digest=digest({"source_item_digest": row.source_item_digest,
                                   "fact_key": key, "fact_value": value,
                                   "contract_id": CONTRACT_ID}),
        frozen_at_trade_date=row.trade_date,
        reason="SOURCE_OPERAND" if value is not None else "SOURCE_OPERAND_UNAVAILABLE")
        for key, value in values.items())


def insert_episode_facts(cur, *, episode_id: str, row,
                         source_revision: int = 1,
                         insert_legacy: bool = True) -> None:
    if source_revision < 1:
        raise ValueError("invalid frozen fact source revision")
    for fact in derive_frozen_facts(row):
        if insert_legacy:
            cur.execute("""insert into workbench.focus_episode_frozen_facts
                (episode_id,fact_key,fact_value,fact_type,source_fact_digest,
                 frozen_at_trade_date,contract_id,reason)
                values (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (episode_id, fact.key, fact.value, fact.fact_type,
                 fact.source_fact_digest, fact.frozen_at_trade_date,
                 CONTRACT_ID, fact.reason))
        cur.execute("""insert into workbench.focus_episode_frozen_fact_revisions
            (episode_id,source_trade_date,source_revision,fact_key,fact_value,
             fact_type,source_fact_digest,frozen_at_trade_date,contract_id,reason)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (episode_id, row.trade_date, source_revision, fact.key, fact.value,
             fact.fact_type, fact.source_fact_digest, fact.frozen_at_trade_date,
             CONTRACT_ID, fact.reason))


def verify_episode_facts(cur, *, episode_id: str, first_row) -> None:
    expected = {fact.key: fact for fact in derive_frozen_facts(first_row)}
    if not expected:
        return
    cur.execute("""select accepted_revision from workbench.focus_trade_date_heads
        where trade_date=%s and source_authority_contract_id=%s and lineage_state='VALID'""",
        (first_row.trade_date, SOURCE_AUTHORITY_CONTRACT))
    accepted = cur.fetchone()
    if accepted is None:
        raise ValueError("FOCUS_EPISODE_FROZEN_FACT_HEAD_UNAVAILABLE")
    revision = int(accepted[0])
    cur.execute("""select fact_key,fact_value,fact_type,source_fact_digest,
        frozen_at_trade_date,contract_id,reason
        from workbench.focus_episode_frozen_fact_revisions
        where episode_id=%s and source_trade_date=%s and source_revision=%s""",
        (episode_id, first_row.trade_date, revision))
    actual = {r[0]: r[1:] for r in cur.fetchall()}
    if not actual and revision == 1:
        cur.execute("""select fact_key,fact_value,fact_type,source_fact_digest,
            frozen_at_trade_date,contract_id,reason
            from workbench.focus_episode_frozen_facts where episode_id=%s""", (episode_id,))
        actual = {r[0]: r[1:] for r in cur.fetchall()}
    wanted = {key: (fact.value, fact.fact_type, fact.source_fact_digest,
                    fact.frozen_at_trade_date, CONTRACT_ID, fact.reason)
              for key, fact in expected.items()}
    if actual != wanted:
        raise ValueError("FOCUS_EPISODE_FROZEN_FACTS_MISMATCH")


def read_episode_fact_values(repository, *, first_rows) -> dict[str, dict[str, str | None]]:
    """Read durable signal operands and reject drift from accepted first sources."""
    values = {}
    with repository.connection.cursor() as cur:
        for episode, row in first_rows.items():
            if row.key.source_family != "V3_3_TODAY_CANDIDATE":
                continue
            verify_episode_facts(cur, episode_id=episode, first_row=row)
            values[episode] = {fact.key: fact.value for fact in derive_frozen_facts(row)}
    return values
