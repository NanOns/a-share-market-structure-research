"""Offline Focus observation inputs from a verified local normalized artifact."""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyarrow.compute as pc
import pyarrow.dataset as ds

from .contracts import canonical_bytes, digest
from .price_path import path_metrics, reanchor_from_frozen_coefficients


CONTRACT_ID = "FOCUS_OBSERVATION_INPUT_V1"
COLUMNS = ["security_id", "date", "raw_open", "raw_high", "raw_low", "raw_close",
           "raw_volume", "raw_amount", "qfq_mul", "qfq_add", "adjustment_status",
           "adjustment_version", "has_actual_bar", "is_master_session", "missing_state"]


@dataclass(frozen=True)
class StockFact:
    security_id: str
    trade_date: date
    start_trade_date: date
    quality_status: str
    missing_state: str | None
    close_price: str | None
    return_since_start: str | None
    mfe: str | None
    mae: str | None
    drawdown_current: str | None
    mdd_close: str | None
    adjustment_version: str | None
    input_digest: str


@dataclass(frozen=True, order=True)
class PathRequest:
    security_id: str
    start_trade_date: date

    def __post_init__(self) -> None:
        if not self.security_id:
            raise ValueError("security identity required")


@dataclass(frozen=True)
class VerifiedNormalizedSlice:
    artifact_sha256: str
    calendar: tuple[date, ...]
    by_security: dict[str, dict[date, dict[str, Any]]]


def _master_calendar(dataset: ds.Dataset, minimum: date, maximum: date) -> tuple[date, ...]:
    filter_expr = ((ds.field("date") >= minimum) & (ds.field("date") <= maximum)
                   & (ds.field("is_master_session") == True))
    sessions: set[date] = set()
    for batch in dataset.scanner(columns=["date"], filter=filter_expr,
                                 batch_size=65536).to_batches():
        sessions.update(day for day in pc.unique(batch.column(0)).to_pylist()
                        if day is not None)
    return tuple(sorted(sessions))


def read_full_master_calendar(*, normalized_path: Path,
                              expected_sha256: str,
                              trade_date: date) -> tuple[date, ...]:
    """Read all known primary sessions through t from the verified artifact."""
    source = normalized_path.resolve(strict=True)
    if _sha256(source) != expected_sha256:
        raise ValueError("normalized calendar artifact digest mismatch")
    calendar = _master_calendar(ds.dataset(source, format="parquet"),
                                date(1900, 1, 1), trade_date)
    if not calendar or calendar[-1] != trade_date:
        raise ValueError("full master calendar does not end at observation date")
    return calendar


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def materialize_stock_facts(*, normalized_path: Path, expected_sha256: str,
                            trade_date: date,
                            starts: Mapping[str, date]) -> tuple[StockFact, ...]:
    """Compatibility entrypoint for one anchor per security."""
    return materialize_stock_paths(normalized_path=normalized_path,
                                   expected_sha256=expected_sha256,
                                   trade_date=trade_date,
                                   requests=[PathRequest(sid, start)
                                             for sid, start in starts.items()])


def materialize_stock_paths(*, normalized_path: Path, expected_sha256: str,
                            trade_date: date,
                            requests: Sequence[PathRequest]) -> tuple[StockFact, ...]:
    """Scan shared raw facts once; project each requested anchor separately."""
    if not requests:
        return ()
    if len(set(requests)) != len(requests):
        raise ValueError("duplicate path request")
    if any(request.start_trade_date > trade_date for request in requests):
        raise ValueError("episode starts after observation date")
    normalized = read_verified_slice(
        normalized_path=normalized_path, expected_sha256=expected_sha256,
        minimum_date=min(request.start_trade_date for request in requests),
        trade_date=trade_date,
        security_ids={request.security_id for request in requests})
    return stock_paths_from_slice(normalized=normalized, trade_date=trade_date,
                                  requests=requests)


def read_verified_slice(*, normalized_path: Path, expected_sha256: str,
                        minimum_date: date, trade_date: date,
                        security_ids: set[str]) -> VerifiedNormalizedSlice:
    """One SHA-checked scan for the whole cross-source fact union."""
    source = normalized_path.resolve(strict=True)
    if not expected_sha256 or len(expected_sha256) != 64:
        raise ValueError("verified normalized artifact identity required")
    actual_sha = _sha256(source)
    if actual_sha != expected_sha256:
        raise ValueError("normalized artifact digest mismatch")
    if minimum_date > trade_date or not security_ids:
        raise ValueError("invalid normalized slice bounds")
    dataset = ds.dataset(source, format="parquet")
    securities = sorted(security_ids)
    filter_expr = ((ds.field("date") >= minimum_date) & (ds.field("date") <= trade_date)
                   & (ds.field("is_master_session") == True)
                   & ds.field("security_id").isin(securities))
    rows = dataset.to_table(columns=COLUMNS, filter=filter_expr).to_pylist()
    by_security: dict[str, dict[date, dict[str, Any]]] = {sid: {} for sid in securities}
    calendar = _master_calendar(dataset, minimum_date, trade_date)
    if trade_date not in calendar:
        raise ValueError("trade date absent from frozen source calendar")
    for row in rows:
        sid, day = str(row["security_id"]), row["date"]
        if row.get("is_master_session") is not True:
            raise ValueError("non-master-session normalized row")
        if day in by_security[sid]:
            raise ValueError("duplicate normalized security/date")
        by_security[sid][day] = row
    return VerifiedNormalizedSlice(actual_sha, calendar, by_security)


def stock_paths_from_slice(*, normalized: VerifiedNormalizedSlice, trade_date: date,
                           requests: Sequence[PathRequest]) -> tuple[StockFact, ...]:
    if len(set(requests)) != len(requests):
        raise ValueError("duplicate path request")
    calendar, by_security, actual_sha = (normalized.calendar, normalized.by_security,
                                          normalized.artifact_sha256)
    if trade_date not in calendar:
        raise ValueError("trade date absent from verified slice")
    facts = []
    for request in sorted(requests):
        sid, start = request.security_id, request.start_trade_date
        sessions = [day for day in calendar if start <= day <= trade_date]
        if not sessions or sessions[0] != start:
            raise ValueError("episode start missing from frozen calendar")
        today = by_security[sid].get(trade_date)
        missing_state = str(today.get("missing_state")) if today and today.get("missing_state") is not None else "MISSING_DATA"
        row_input = {"contract": CONTRACT_ID, "security_id": sid,
                     "trade_date": trade_date, "start_trade_date": start,
                     "calendar": sessions, "normalized_sha256": actual_sha,
                     "rows": [by_security[sid].get(day) for day in sessions]}
        row_digest = digest(row_input)
        path = reanchor_from_frozen_coefficients(sessions=sessions, rows=by_security[sid])
        if path is None:
            facts.append(StockFact(sid, trade_date, start, "DATA_UNAVAILABLE",
                                   missing_state, None, None, None, None, None, None,
                                   str(today.get("adjustment_version")) if today else None,
                                   row_digest))
            continue
        metrics = path_metrics(path)
        facts.append(StockFact(sid, trade_date, start, "READY", "BAR",
                               str(path[-1].close), str(metrics["return_close"]),
                               str(metrics["mfe"]), str(metrics["mae"]),
                               str(metrics["drawdown_current"]), str(metrics["mdd_close"]),
                               str(today.get("adjustment_version")), row_digest))
    return tuple(facts)


def write_observation_input(*, output_path: Path, trade_date: date,
                            source_identity_digest: str,
                            normalized_sha256: str,
                            facts: Sequence[StockFact]) -> str:
    """Atomically write one immutable input artifact outside TDX roots."""
    payload = {"contract_id": CONTRACT_ID, "trade_date": trade_date,
               "source_identity_digest": source_identity_digest,
               "normalized_sha256": normalized_sha256,
               "stock_facts": [fact.__dict__ for fact in facts]}
    encoded = canonical_bytes(payload)
    sha = hashlib.sha256(encoded).hexdigest()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if _sha256(output_path) != sha:
            raise ValueError("immutable observation artifact conflict")
        return sha
    fd, temporary = tempfile.mkstemp(prefix="." + output_path.name + ".", suffix=".tmp",
                                      dir=output_path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return sha
