"""Project-local API37 reader for captured M14 hot-rank batches."""

from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from workbench_online.hot_rank_view import _batch_time, build_hot_rank_view
from workbench_online.base import OnlineFetchPolicy
from workbench_online.eastmoney_hot_rank import fetch_eastmoney_hot_rank
from workbench_online.eastmoney_quotes import fetch_eastmoney_quotes
from workbench_online.ths_hot_rank import fetch_ths_hot_rank


CONTRACT_ID = "M14_HOT_RANK_API_V2_0"
LEGACY_CONTRACT_ID = "M14_HOT_RANK_API_V1_0"
MAX_PAGE_SIZE = 100
ONLINE_TOTAL_TIMEOUT_SECONDS = 12.0
SOURCE_IDS = ("EASTMONEY_HOT_RANK", "TONGHUASHUN_HOT_RANK")
DIRECT_FETCHERS = {
    "EASTMONEY_HOT_RANK": fetch_eastmoney_hot_rank,
    "TONGHUASHUN_HOT_RANK": fetch_ths_hot_rank,
}


def _validate_direct_capability(root: str | Path | None) -> None:
    if root is None:
        return
    path = Path(root) / "config/m14_runtime_capabilities_v1.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        capability = payload["capabilities"]["HOT_RANKINGS"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("HOT_RANK_CAPABILITY_GATE_UNAVAILABLE") from exc
    if capability.get("status") != "ENABLED" or capability.get("mode") != "DIRECT_EPHEMERAL_LATEST":
        raise ValueError("HOT_RANK_CAPABILITY_DISABLED")
    if any(capability.get(key) is not False for key in ("persist_payload", "persist_rows", "persist_batches")):
        raise ValueError("HOT_RANK_PERSISTENCE_POLICY_INVALID")


def _parse_as_of(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("HOT_RANK_AS_OF_INVALID") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def load_hot_rank_batches(root: str | Path) -> list[dict]:
    batch_root = Path(root) / "data/online/m14_personal/batches"
    if not batch_root.is_dir():
        return []
    batches = []
    for path in sorted(batch_root.glob("*.json")):
        try:
            batch = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("HOT_RANK_BATCH_READ_FAILED") from exc
        if batch.get("batch_id") != path.stem:
            raise ValueError("HOT_RANK_BATCH_ID_MISMATCH")
        batches.append(batch)
    return batches


def _select_candidates(batches: list[dict], source_id: str, list_type: str | None, mode: str, as_of: str | None) -> list[dict]:
    if source_id not in SOURCE_IDS:
        raise ValueError("HOT_RANK_SOURCE_UNSUPPORTED")
    if mode not in {"LATEST", "AS_OF"}:
        raise ValueError("HOT_RANK_MODE_INVALID")
    anchor = _parse_as_of(as_of)
    if mode == "AS_OF" and anchor is None:
        raise ValueError("HOT_RANK_AS_OF_REQUIRED")
    candidates = [
        batch
        for batch in batches
        if batch.get("source_id") == source_id
        and (list_type is None or batch.get("list_type") == list_type)
        and (anchor is None or _batch_time(batch) <= anchor)
    ]
    if not candidates:
        raise ValueError("HOT_RANK_BATCH_UNAVAILABLE")
    return candidates


def _view_for_source(batches: list[dict], source_id: str, *, list_type: str | None, mode: str, as_of: str | None, batch_id: str | None) -> dict:
    candidates = _select_candidates(batches, source_id, list_type, mode, as_of)
    if batch_id:
        if not any(batch.get("batch_id") == batch_id for batch in candidates):
            raise ValueError("HOT_RANK_BATCH_NOT_FOUND")
    return build_hot_rank_view(candidates, source_id=source_id, list_type=list_type, batch_id=batch_id)


def _page_view(view: dict, page: int, page_size: int) -> dict:
    if page < 1 or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValueError("HOT_RANK_PAGE_INVALID")
    rows = view["rows"]
    start = (page - 1) * page_size
    items = rows[start : start + page_size]
    return {
        "api_contract": LEGACY_CONTRACT_ID,
        "storage_scope": "LOCAL_PROJECT",
        "dataset": "HOT_RANKINGS",
        "source_id": view["source_id"],
        "list_type": view["list_type"],
        "mode": view.get("mode", "LATEST"),
        "batch_id": view["batch_id"],
        "source_as_of": view["source_as_of"],
        "observed_at_utc": view["observed_at_utc"],
        "time_semantics": view["time_semantics"],
        "comparison_status": view["comparison_status"],
        "comparison_batch_id": view["comparison_batch_id"],
        "rank_change_basis": view["rank_change_basis"],
        "page": page,
        "page_size": page_size,
        "total": len(rows),
        "items": items,
        "capability_status": "AVAILABLE",
        "local_snapshot_mutated": False,
    }


def build_hot_rank_api_response(
    root: str | Path,
    *,
    source: str = "EASTMONEY_HOT_RANK",
    list_type: str | None = None,
    mode: str = "LATEST",
    as_of: str | None = None,
    batch_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
    co_listed: bool = False,
) -> dict:
    batches = load_hot_rank_batches(root)
    if not batches:
        raise ValueError("HOT_RANK_BATCH_UNAVAILABLE")
    sources = list(SOURCE_IDS) if source.upper() == "ALL" or co_listed else [source]
    views = []
    for source_id in sources:
        view = _view_for_source(batches, source_id, list_type=list_type, mode=mode, as_of=as_of, batch_id=batch_id)
        view["mode"] = mode
        views.append(_page_view(view, page, page_size))
    if len(views) == 1:
        return views[0]
    batch_set_material = [(item["source_id"], item["batch_id"]) for item in views]
    batch_set_id = "m14bs-" + hashlib.sha256(json.dumps(batch_set_material, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    return {
        "api_contract": LEGACY_CONTRACT_ID,
        "storage_scope": "LOCAL_PROJECT",
        "dataset": "HOT_RANKINGS",
        "mode": mode,
        "co_listed": True,
        "batch_set_id": batch_set_id,
        "source_views": views,
        "local_snapshot_mutated": False,
    }


def _direct_rows(normalized: dict, name_lookup: Callable[[list[str]], dict[str, str]] | None) -> list[dict]:
    rows = normalized.get("rows") or []
    ids = [row.get("security_id") for row in rows if row.get("security_id")]
    names = name_lookup(ids) if name_lookup else {}
    output = []
    for row in rows:
        security_id = row.get("security_id")
        local_name = names.get(security_id) if security_id else None
        source_name = row.get("security_name")
        output.append(
            {
                "source_code": row.get("source_code"),
                "security_id": security_id,
                "security_name": local_name or source_name,
                "mapping_status": "MAPPED" if security_id and (local_name or source_name) else "UNMAPPED",
                "platform_rank": row.get("platform_rank"),
                "source_rank_change": row.get("rank_change"),
                "source_row_order": row.get("source_row_order"),
                "source_exact_time": row.get("source_exact_time"),
                "source_quote_fields": {
                    key: row[key]
                    for key in ("rise_and_fall", "rate")
                    if key in row
                },
                "source_tags": row.get("tag") if "tag" in row else None,
            }
        )
    return output


def _direct_source_view(
    source_id: str,
    *,
    page: int,
    page_size: int,
    policy: OnlineFetchPolicy,
    name_lookup: Callable[[list[str]], dict[str, str]] | None,
    fetchers: dict[str, Callable] | None,
    quote_fetcher: Callable | None,
) -> dict:
    fetcher = (fetchers or DIRECT_FETCHERS).get(source_id)
    if fetcher is None:
        raise ValueError("HOT_RANK_SOURCE_UNSUPPORTED")
    result, normalized = fetcher(policy, **({"page": page} if source_id == "EASTMONEY_HOT_RANK" else {}))
    raw_rows = list(normalized.get("rows") or [])
    upstream_paged = bool(normalized.get("upstream_paged", source_id == "EASTMONEY_HOT_RANK"))
    if upstream_paged:
        # The source already selected page N.  Do not apply a second page
        # offset, which would turn a valid upstream page into an empty page.
        selected_rows = raw_rows[:page_size]
        total = normalized.get("upstream_total")
        has_more = normalized.get("upstream_has_more")
    else:
        start = (page - 1) * page_size
        selected_rows = raw_rows[start : start + page_size]
        total = normalized.get("upstream_total", len(raw_rows))
        has_more = start + len(selected_rows) < total if isinstance(total, int) else None
    selected_normalized = {**normalized, "rows": selected_rows}
    rows = _direct_rows(selected_normalized, name_lookup)
    quote_status = "NOT_REQUESTED"
    if quote_fetcher:
        quote_ids = [row["security_id"] for row in rows if row.get("security_id")]
        try:
            _, quote_items = quote_fetcher(quote_ids, policy)
            quotes = {item["security_id"]: item for item in quote_items}
            for row in rows:
                row["quote"] = quotes.get(row.get("security_id"))
            quote_status = "AVAILABLE" if quotes else "EMPTY"
        except Exception as exc:
            for row in rows:
                row["quote"] = None
            quote_status = f"UNAVAILABLE:{type(exc).__name__}"
    return {
        "api_contract": CONTRACT_ID,
        "storage_scope": "EPHEMERAL_ONLINE",
        "dataset": "HOT_RANKINGS",
        "source_id": source_id,
        "list_type": normalized.get("list_type"),
        "mode": "LATEST",
        "source_as_of": normalized.get("source_as_of"),
        "observed_at_utc": result.received_at_utc,
        "time_semantics": normalized.get("time_semantics"),
        "page": page,
        "page_size": page_size,
        "total": total if isinstance(total, int) and total >= 0 else None,
        "upstream_total": total if isinstance(total, int) and total >= 0 else None,
        "returned_count": len(rows),
        "has_more": has_more if isinstance(has_more, bool) else None,
        "items": rows,
        "status": "READY",
        "capability_status": "AVAILABLE",
        "quote_status": quote_status,
        "reason_status": "UNAVAILABLE_NO_VERIFIED_REASON_SOURCE",
        "local_snapshot_mutated": False,
    }


def _source_error_code(exc: Exception) -> str:
    value = str(exc).strip()
    if value and len(value) <= 80 and "\n" not in value and "\r" not in value:
        return value
    return type(exc).__name__


def _unavailable_source_view(source_id: str, page: int, page_size: int, exc: Exception) -> dict:
    return {
        "api_contract": CONTRACT_ID,
        "storage_scope": "EPHEMERAL_ONLINE",
        "dataset": "HOT_RANKINGS",
        "source_id": source_id,
        "list_type": None,
        "mode": "LATEST",
        "source_as_of": None,
        "observed_at_utc": None,
        "time_semantics": "UNAVAILABLE",
        "page": page,
        "page_size": page_size,
        "total": None,
        "upstream_total": None,
        "returned_count": 0,
        "has_more": None,
        "items": [],
        "status": "UNAVAILABLE",
        "error_code": _source_error_code(exc),
        "capability_status": "UNAVAILABLE",
        "quote_status": "NOT_REQUESTED",
        "reason_status": "UNAVAILABLE_NO_VERIFIED_REASON_SOURCE",
        "local_snapshot_mutated": False,
    }


def _direct_source_view_safe(
    source_id: str,
    *,
    page: int,
    page_size: int,
    policy: OnlineFetchPolicy,
    name_lookup: Callable[[list[str]], dict[str, str]] | None,
    fetchers: dict[str, Callable] | None,
    quote_fetcher: Callable | None,
) -> dict:
    try:
        return _direct_source_view(
            source_id,
            page=page,
            page_size=page_size,
            policy=policy,
            name_lookup=name_lookup,
            fetchers=fetchers,
            quote_fetcher=quote_fetcher,
        )
    except Exception as exc:
        return _unavailable_source_view(source_id, page, page_size, exc)


def build_hot_rank_direct_response(
    *,
    root: str | Path | None = None,
    source: str = "EASTMONEY_HOT_RANK",
    page: int = 1,
    page_size: int = 50,
    co_listed: bool = False,
    policy: OnlineFetchPolicy | None = None,
    name_lookup: Callable[[list[str]], dict[str, str]] | None = None,
    fetchers: dict[str, Callable] | None = None,
    quote_fetcher: Callable | None = None,
) -> dict:
    _validate_direct_capability(root)
    if page < 1 or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValueError("HOT_RANK_PAGE_INVALID")
    source_key = source.upper()
    if source_key != "ALL" and source_key not in SOURCE_IDS:
        raise ValueError("HOT_RANK_SOURCE_UNSUPPORTED")
    sources = list(SOURCE_IDS) if source_key == "ALL" or co_listed else [source_key]
    effective_policy = policy or OnlineFetchPolicy(cache_ttl_seconds=0, personal_research_only=True)
    executor = ThreadPoolExecutor(max_workers=len(sources), thread_name_prefix="hot-rank")
    futures = [
        executor.submit(
            _direct_source_view_safe,
            source_id,
            page=page,
            page_size=page_size,
            policy=effective_policy,
            name_lookup=name_lookup,
            fetchers=fetchers,
            quote_fetcher=quote_fetcher,
        )
        for source_id in sources
    ]
    deadline = time.monotonic() + ONLINE_TOTAL_TIMEOUT_SECONDS
    views = []
    try:
        for source_id, future in zip(sources, futures):
            remaining = max(0.0, deadline - time.monotonic())
            try:
                views.append(future.result(timeout=remaining))
            except FutureTimeoutError:
                future.cancel()
                views.append(_unavailable_source_view(source_id, page, page_size, TimeoutError("UPSTREAM_TIMEOUT")))
            except Exception as exc:
                views.append(_unavailable_source_view(source_id, page, page_size, exc))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    if len(views) == 1:
        return views[0]
    statuses = {view.get("status") for view in views}
    overall_status = "READY" if statuses == {"READY"} else "PARTIAL" if "READY" in statuses else "UNAVAILABLE"
    return {
        "api_contract": CONTRACT_ID,
        "storage_scope": "EPHEMERAL_ONLINE",
        "dataset": "HOT_RANKINGS",
        "mode": "LATEST",
        "co_listed": True,
        "status": overall_status,
        "source_views": views,
        "local_snapshot_mutated": False,
    }
