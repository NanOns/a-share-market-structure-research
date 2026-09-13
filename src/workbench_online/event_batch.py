"""Bounded in-memory EXT01 event batch reads for the V3 data layer.

The reader keeps only normalized DTOs and redacted page evidence in memory.
It never writes online_payloads, online_batches, event rows, or local runs.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping
from urllib.parse import urlencode

from .base import FetchResult, OnlineFetchPolicy, bounded_get
from .event_models import (
    EVENT_DTO_CONTRACT_VERSION,
    EXT01_EVENT_ADAPTER_VERSION,
    EXT01_DATASET,
    EXT01_SOURCE_ID,
    EventHeader,
    EventPoolRow,
    EventSchemaError,
    adapt_ext01_payload,
)


EVENT_BATCH_CONTRACT_VERSION = "v3-lz-ext01-batch-read-v1.0"
EXT01_BATCH_ENDPOINT = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool"
EXT01_BATCH_FIELDS = (
    "199112", "10", "9001", "330323", "330324", "330325", "9002",
    "330329", "133971", "133970", "1968584", "3475914", "9003",
)
MAX_EVENT_PAGE_SIZE = 200
MAX_EVENT_PAGES = 20
TOTAL_REQUEST_BUDGET_SECONDS = 12.0


class EventBatchReadError(ValueError):
    """Raised for invalid batch-read arguments before any request is made."""


@dataclass(frozen=True)
class BatchPageEvidence:
    page: int
    status: str
    url: str
    http_status: int | None
    content_type: str | None
    byte_count: int | None
    raw_sha256: str | None
    row_count: int
    error_code: str | None

    def to_record(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "status": self.status,
            "url": self.url,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "byte_count": self.byte_count,
            "raw_sha256": self.raw_sha256,
            "row_count": self.row_count,
            "error_code": self.error_code,
        }


@dataclass(frozen=True)
class EventBatchReadResult:
    contract_version: str
    adapter_version: str
    source_id: str
    dataset: str
    trade_date: str
    status: str
    batch_id: str | None
    header: EventHeader | None
    rows: tuple[EventPoolRow, ...]
    pages: tuple[BatchPageEvidence, ...]
    coverage: Mapping[str, Any]
    failure_codes: tuple[str, ...]
    duplicate_count: int
    conflict_count: int
    network_calls: int
    next_stage: str

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "adapter_version": self.adapter_version,
            "source_id": self.source_id,
            "dataset": self.dataset,
            "trade_date": self.trade_date,
            "status": self.status,
            "batch_id": self.batch_id,
            "header": self.header.to_record() if self.header else None,
            "rows": [row.to_record() for row in self.rows],
            "pages": [page.to_record() for page in self.pages],
            "coverage": dict(self.coverage),
            "failure_codes": list(self.failure_codes),
            "duplicate_count": self.duplicate_count,
            "conflict_count": self.conflict_count,
            "network_calls": self.network_calls,
            "next_stage": self.next_stage,
        }


@dataclass(frozen=True)
class _PageMeta:
    current_page: int
    page_size: int | None
    total_pages: int | None
    has_more: bool | None


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None
    return int(number) if math.isfinite(number) and number.is_integer() else None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
    return None


def _first_int(value: Mapping[str, Any], names: tuple[str, ...]) -> int | None:
    for name in names:
        parsed = _as_int(value.get(name))
        if parsed is not None:
            return parsed
    return None


def _page_meta(payload: Mapping[str, Any], row_count: int) -> _PageMeta:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise EventBatchReadError("EXT01_DATA_OBJECT_MISSING")
    raw_page = data.get("page")
    page_object = raw_page if isinstance(raw_page, Mapping) else {}
    current = _first_int(page_object, ("page", "current", "current_page"))
    if current is None:
        current = _as_int(raw_page) or 1
    page_size = _first_int(page_object, ("page_size", "limit", "size"))
    total_pages = _first_int(page_object, ("total_pages", "pages", "page_count"))
    total = _first_int(page_object, ("total", "total_count", "count"))
    if total_pages is None and total is not None and page_size and page_size > 0:
        total_pages = max(1, math.ceil(total / page_size))
    has_more = None
    for name in ("has_more", "hasMore", "more"):
        if name in page_object:
            has_more = _as_bool(page_object.get(name))
            break
    if has_more is None and total_pages is not None:
        has_more = current < total_pages
    return _PageMeta(current, page_size, total_pages, has_more)


def build_ext01_batch_url(*, page: int, page_size: int, trade_date: str) -> str:
    if not isinstance(page, int) or page < 1:
        raise EventBatchReadError("INVALID_PAGE")
    if not isinstance(page_size, int) or not 1 <= page_size <= MAX_EVENT_PAGE_SIZE:
        raise EventBatchReadError("INVALID_EVENT_PAGE_SIZE")
    if not isinstance(trade_date, str) or len(trade_date) != 8 or not trade_date.isdigit():
        raise EventBatchReadError("INVALID_TRADE_DATE")
    params = {
        "page": page,
        "limit": page_size,
        "field": ",".join(EXT01_BATCH_FIELDS),
        "filter": "HS,GEM2STAR",
        "order_field": "330323",
        "order_type": 0,
        "date": trade_date,
    }
    return f"{EXT01_BATCH_ENDPOINT}?{urlencode(params)}"


def _page_failure(page: int, url: str, error_code: str, result: FetchResult | None = None) -> BatchPageEvidence:
    return BatchPageEvidence(
        page=page,
        status="FAILED",
        url=url,
        http_status=result.status_code if result else None,
        content_type=result.content_type if result else None,
        byte_count=result.byte_count if result else None,
        raw_sha256=result.raw_sha256 if result else None,
        row_count=0,
        error_code=error_code,
    )


def _read_page(
    *,
    page: int,
    page_size: int,
    trade_date: str,
    observed_at: str,
    policy: OnlineFetchPolicy,
    fetcher: Callable[..., FetchResult],
) -> tuple[BatchPageEvidence, EventHeader | None, tuple[EventPoolRow, ...], _PageMeta | None, str | None]:
    url = build_ext01_batch_url(page=page, page_size=page_size, trade_date=trade_date)
    result: FetchResult | None = None
    try:
        result = fetcher(url, policy)
        if result.status_code != 200:
            code = f"HTTP_STATUS_{result.status_code}"
            return _page_failure(page, url, code, result), None, (), None, code
        if "json" not in result.content_type.lower():
            code = "CONTENT_TYPE_NOT_JSON"
            return _page_failure(page, url, code, result), None, (), None, code
        payload = json.loads(result.body.decode("utf-8"))
        header, rows = adapt_ext01_payload(payload, trade_date=trade_date, observed_at=observed_at)
        metadata = _page_meta(payload, len(rows))
        if metadata.current_page != page:
            code = f"PAGE_NUMBER_MISMATCH_EXPECTED_{page}_GOT_{metadata.current_page}"
            return _page_failure(page, url, code, result), None, (), metadata, code
        evidence = BatchPageEvidence(
            page=page,
            status="SUCCESS",
            url=url,
            http_status=result.status_code,
            content_type=result.content_type,
            byte_count=result.byte_count,
            raw_sha256=result.raw_sha256,
            row_count=len(rows),
            error_code=None,
        )
        return evidence, header, rows, metadata, None
    except (EventSchemaError, EventBatchReadError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        code = f"{type(exc).__name__}:{exc}"
        return _page_failure(page, url, code, result), None, (), None, code
    except Exception as exc:  # pragma: no cover - live transport failures
        code = f"{type(exc).__name__}:{exc}"
        return _page_failure(page, url, code, result), None, (), None, code


def _row_compare_key(row: EventPoolRow) -> dict[str, Any]:
    record = row.to_record()
    for key in ("observed_at", "source_as_of", "batch_id"):
        record.pop(key, None)
    return record


def _deduplicate(rows: list[EventPoolRow]) -> tuple[tuple[EventPoolRow, ...], int, int]:
    by_key: dict[tuple[str, str], EventPoolRow] = {}
    order: list[tuple[str, str]] = []
    duplicates = 0
    conflicts = 0
    for row in rows:
        key = (row.pool_type, row.source_code)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            order.append(key)
            continue
        if _row_compare_key(existing) == _row_compare_key(row):
            duplicates += 1
            continue
        conflicts += 1
        by_key[key] = replace(existing, quality_codes=tuple(sorted(set(existing.quality_codes) | {"DUPLICATE_CONFLICT"})))
    return tuple(by_key[key] for key in order), duplicates, conflicts


def _batch_id(source_id: str, trade_date: str, pages: tuple[BatchPageEvidence, ...], rows: tuple[EventPoolRow, ...]) -> str:
    material = {
        "source_id": source_id,
        "trade_date": trade_date,
        "pages": [page.to_record() for page in pages],
        "rows": [_row_compare_key(row) for row in rows],
    }
    digest = hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"v3evt-{digest[:24]}"


def read_ext01_batch(
    *,
    trade_date: str,
    page_size: int = MAX_EVENT_PAGE_SIZE,
    max_pages: int = MAX_EVENT_PAGES,
    policy: OnlineFetchPolicy | None = None,
    fetcher: Callable[..., FetchResult] = bounded_get,
    observed_at: str = "2026-09-12T17:28:09+00:00",
    clock: Callable[[], float] = time.monotonic,
) -> EventBatchReadResult:
    """Read a bounded EXT01 batch, dedupe within it, and fail closed on gaps."""
    if not isinstance(max_pages, int) or not 1 <= max_pages <= MAX_EVENT_PAGES:
        raise EventBatchReadError("INVALID_MAX_EVENT_PAGES")
    if not isinstance(trade_date, str) or len(trade_date) != 8 or not trade_date.isdigit():
        raise EventBatchReadError("INVALID_TRADE_DATE")
    policy = policy or OnlineFetchPolicy(timeout_seconds=8, max_response_bytes=2_000_000, retries=0, personal_research_only=True)
    policy.validate()
    if policy.timeout_seconds > 8:
        raise EventBatchReadError("EXT01_SOURCE_TIMEOUT_BUDGET_EXCEEDED")

    pages: list[BatchPageEvidence] = []
    successful_headers: list[EventHeader] = []
    all_rows: list[EventPoolRow] = []
    failures: list[str] = []
    expected_total_pages: int | None = None
    complete = False
    next_page = 1
    started = clock()
    while len(pages) < max_pages:
        if len(pages) > 0 and clock() - started >= TOTAL_REQUEST_BUDGET_SECONDS:
            code = "TOTAL_REQUEST_BUDGET_EXCEEDED"
            failures.append(code)
            pages.append(_page_failure(next_page, build_ext01_batch_url(page=next_page, page_size=page_size, trade_date=trade_date), code))
            break
        evidence, header, rows, metadata, error_code = _read_page(
            page=next_page,
            page_size=page_size,
            trade_date=trade_date,
            observed_at=observed_at,
            policy=policy,
            fetcher=fetcher,
        )
        pages.append(evidence)
        if error_code:
            failures.append(error_code)
            break
        assert header is not None and metadata is not None
        successful_headers.append(header)
        all_rows.extend(rows)
        expected_total_pages = metadata.total_pages or expected_total_pages
        if metadata.has_more is True and expected_total_pages is not None and next_page >= expected_total_pages:
            failures.append("PAGINATION_METADATA_CONFLICT")
            break
        if metadata.has_more is False or (metadata.has_more is None and expected_total_pages is not None and next_page >= expected_total_pages):
            complete = True
            break
        if metadata.has_more is None and expected_total_pages is None:
            failures.append("PAGINATION_METADATA_UNRESOLVED")
            break
        next_page += 1

    page_records = tuple(pages)
    unique_rows, duplicate_count, conflict_count = _deduplicate(all_rows)
    successful_pages = [page.page for page in pages if page.status == "SUCCESS"]
    failed_pages = [page.page for page in pages if page.status == "FAILED"]
    partial_failure = bool(failed_pages)
    if partial_failure and successful_headers:
        failures.append("PARTIAL_PAGE_FAILURE")
    coverage = {
        "requested_pages": [page.page for page in pages],
        "successful_pages": successful_pages,
        "failed_pages": failed_pages,
        "page_size": page_size,
        "max_pages": max_pages,
        "expected_total_pages": expected_total_pages,
        "complete_pagination": complete and not partial_failure,
        "coverage_status": "COMPLETE" if complete and not partial_failure else "PARTIAL_OR_UNVERIFIED",
        "unique_row_count": len(unique_rows),
        "page_row_count": sum(page.row_count for page in pages),
    }
    if not successful_headers:
        return EventBatchReadResult(
            contract_version=EVENT_BATCH_CONTRACT_VERSION,
            adapter_version=EXT01_EVENT_ADAPTER_VERSION,
            source_id=EXT01_SOURCE_ID,
            dataset=EXT01_DATASET,
            trade_date=trade_date,
            status="UNAVAILABLE",
            batch_id=None,
            header=None,
            rows=(),
            pages=page_records,
            coverage=coverage,
            failure_codes=tuple(dict.fromkeys(failures)),
            duplicate_count=0,
            conflict_count=0,
            network_calls=len(pages),
            next_stage="P09-01-B-LZ-EXT03",
        )

    batch_id = _batch_id(EXT01_SOURCE_ID, trade_date, page_records, unique_rows)
    header_quality = set(successful_headers[0].quality_codes)
    if failures:
        header_quality.update({"BATCH_PARTIAL_OR_UNVERIFIED"})
    aggregate_scope = {
        **successful_headers[0].scope,
        **coverage,
        "same_bundle_deduplication": True,
        "duplicate_count": duplicate_count,
        "conflict_count": conflict_count,
    }
    aggregate_header = replace(
        successful_headers[0],
        batch_id=batch_id,
        scope=aggregate_scope,
        quality_codes=tuple(sorted(header_quality)),
    )
    bound_rows = tuple(replace(row, batch_id=batch_id) for row in unique_rows)
    return EventBatchReadResult(
        contract_version=EVENT_BATCH_CONTRACT_VERSION,
        adapter_version=EXT01_EVENT_ADAPTER_VERSION,
        source_id=EXT01_SOURCE_ID,
        dataset=EXT01_DATASET,
        trade_date=trade_date,
        status="AVAILABLE" if complete and not failures and conflict_count == 0 else "DEGRADED",
        batch_id=batch_id,
        header=aggregate_header,
        rows=bound_rows,
        pages=page_records,
        coverage=coverage,
        failure_codes=tuple(dict.fromkeys(failures)),
        duplicate_count=duplicate_count,
        conflict_count=conflict_count,
        network_calls=len(pages),
        next_stage="P09-02-C-EXT01-CLOSE-BATCH-STORE",
    )
