from __future__ import annotations

"""Generic point-in-time alias and board resolution from versioned identity facts."""

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Iterable, Mapping


def _day(value: object | None, field: str, *, nullable: bool = False) -> date | None:
    if value is None or str(value).strip() == "":
        if nullable:
            return None
        raise ValueError(f"DATED_ALIAS_{field.upper()}_REQUIRED")
    try:
        return date.fromisoformat(str(value).replace("/", "-"))
    except ValueError as exc:
        raise ValueError(f"DATED_ALIAS_{field.upper()}_INVALID") from exc


@dataclass(frozen=True)
class DatedAliasRecord:
    security_id: str
    source_security_key: str
    effective_from: date
    effective_to: date | None
    exchange: str
    board: str
    alias_role: str
    source_revision: str
    evidence_ref: str
    evidence_hash: str

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "DatedAliasRecord":
        start = row.get("effective_from", row.get("symbol_effective_from"))
        end = row.get("effective_to", row.get("symbol_effective_to"))
        record = cls(
            security_id=str(row.get("security_id") or ""),
            source_security_key=str(row.get("source_security_key") or row.get("symbol") or ""),
            effective_from=_day(start, "effective_from"),
            effective_to=_day(end, "effective_to", nullable=True),
            exchange=str(row.get("exchange") or ""), board=str(row.get("board") or ""),
            alias_role=str(row.get("alias_role") or ""),
            source_revision=str(row.get("source_revision") or row.get("source_revision_id") or ""),
            evidence_ref=str(row.get("evidence_ref") or row.get("source_ref") or ""),
            evidence_hash=str(row.get("evidence_hash") or row.get("evidence_sha256") or row.get("source_capture_sha256") or ""),
        )
        if not all((record.security_id, record.source_security_key, record.exchange, record.board,
                    record.alias_role, record.source_revision, record.evidence_ref)):
            raise ValueError("DATED_ALIAS_IDENTITY_AND_EVIDENCE_REQUIRED")
        if len(record.evidence_hash) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in record.evidence_hash):
            raise ValueError("DATED_ALIAS_EVIDENCE_HASH_INVALID")
        if record.effective_to is not None and record.effective_to < record.effective_from:
            raise ValueError("DATED_ALIAS_EFFECTIVE_INTERVAL_INVALID")
        return record

    def includes(self, target: date) -> bool:
        return self.effective_from <= target and (self.effective_to is None or target <= self.effective_to)


class DatedSecurityAliasResolver:
    """Resolve an alias or board for a stable identity at an explicit date."""

    def __init__(self, records: Iterable[Mapping[str, object] | DatedAliasRecord]):
        self.records = tuple(row if isinstance(row, DatedAliasRecord) else DatedAliasRecord.from_mapping(row) for row in records)
        if not self.records:
            raise ValueError("DATED_ALIAS_RECORDS_EMPTY")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "DatedSecurityAliasResolver":
        with Path(path).open("r", encoding="utf-8") as stream:
            return cls(json.loads(line) for line in stream if line.strip())

    def records_for(self, security_id: str, trade_date: str) -> tuple[DatedAliasRecord, ...]:
        target = _day(trade_date, "trade_date")
        matches = tuple(record for record in self.records if record.security_id == security_id and record.includes(target))
        return matches

    def resolve_alias(self, security_id: str, trade_date: str) -> str | None:
        matches = self.records_for(security_id, trade_date)
        aliases = {record.source_security_key for record in matches}
        if len(aliases) > 1:
            raise ValueError("DATED_ALIAS_AMBIGUOUS_AT_DATE")
        return next(iter(aliases), None)

    def resolve_board(self, security_id: str, trade_date: str) -> str | None:
        matches = self.records_for(security_id, trade_date)
        boards = {record.board for record in matches}
        if len(boards) > 1:
            raise ValueError("DATED_BOARD_AMBIGUOUS_AT_DATE")
        return next(iter(boards), None)

    def resolve_exchange(self, security_id: str, trade_date: str) -> str | None:
        matches = self.records_for(security_id, trade_date)
        exchanges = {record.exchange for record in matches}
        if len(exchanges) > 1:
            raise ValueError("DATED_EXCHANGE_AMBIGUOUS_AT_DATE")
        return next(iter(exchanges), None)
