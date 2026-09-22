"""Request-time P12-14 turnover enrichment for verified V3.3 candidates."""

from __future__ import annotations

import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import duckdb

from workbench_analysis.turnover_enrichment_v3_3 import (
    CONTRACT_ID,
    LocalDailyFingerprint,
    apply_turnover_enhancement,
    bind_turnover_row,
    select_enrichment_ids,
)
from workbench_analysis.turnover_context_v3_3 import ALGORITHM_CONTRACT_ID, build_turnover_context
from workbench_online.base import OnlineFetchPolicy
from workbench_online.eastmoney_quotes import fetch_eastmoney_quotes
from workbench_online.tencent_quotes import fetch_tencent_quotes
from workbench_online.sohu_quotes import fetch_sohu_quotes
from workbench_online.stcn_quotes import fetch_stcn_quotes
from workbench_service.research_bundle_v3_3 import ResearchBundleError
from workbench_service.today_research_bundle import TodayResearchBundleReader


CACHE_SECONDS = 900


class TurnoverEnrichmentService:
    def __init__(
        self,
        root: str | Path,
        reader: TodayResearchBundleReader,
        *,
        fetcher: Callable = fetch_tencent_quotes,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.root = Path(root).resolve()
        self.reader = reader
        self.fetcher = fetcher
        self.clock = clock
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, dict]] = {}

    def load(self, *, expected_digest: str = "") -> dict:
        try:
            active, candidates = self.reader._load()
        except (ResearchBundleError, OSError, ValueError, KeyError) as exc:
            return self._unavailable("ACTIVE_BUNDLE_UNAVAILABLE", str(exc))
        digest = str(active["output_digest"])
        if expected_digest and expected_digest != digest:
            return self._unavailable("BUNDLE_CONTEXT_CHANGED", "研究包已更新，请刷新候选列表。")
        with self._lock:
            cached = self._cache.get(digest)
            now = self.clock()
            if cached and now - cached[0] < CACHE_SECONDS:
                return {**cached[1], "cached": True}
            response = self._fetch(active, candidates)
            self._cache = {digest: (now, response)}
            return {**response, "cached": False}

    def load_materialized(self, *, expected_digest: str = "") -> dict:
        """Read the enhancement sealed by the V3.3 generation pipeline; never fetch online."""
        try:
            active, candidates = self.reader._load()
        except (ResearchBundleError, OSError, ValueError, KeyError) as exc:
            return self._unavailable("ACTIVE_BUNDLE_UNAVAILABLE", str(exc))
        digest = str(active["output_digest"])
        if expected_digest and expected_digest != digest:
            return self._unavailable("BUNDLE_CONTEXT_CHANGED", "研究包已更新，请刷新候选列表。")
        store = self.root / "data/turnover_shadow_v3_3" / str(active["identity"]["trade_date"])
        observations = []
        if store.exists():
            for path in store.glob("*.json"):
                value = json.loads(path.read_text(encoding="utf-8"))
                if value.get("bundle_digest") == digest:
                    observations.append(value)
        if not observations:
            return self._unavailable("TURNOVER_ENHANCEMENT_NOT_MATERIALIZED", "本次V3.3生成尚无换手率增强产物。")
        observation = max(observations, key=lambda value: (int(value.get("bound_count") or 0), str(value.get("captured_at_utc") or "")))
        evidence = [{
            "contract_id": CONTRACT_ID,
            "security_id": item["security_id"],
            "trade_date": item["trade_date"],
            "turnover_rate": item["turnover_rate"],
            "turnover_basis": item.get("turnover_basis"),
            "source_id": item.get("source_id"),
            "source_identity_sha256": item.get("source_identity_sha256"),
            "observed_at_utc": item.get("observed_at_utc"),
            "source_quote_time": item.get("source_quote_time"),
            "source_contract_id": item.get("source_contract_id"),
            "field_map_version": item.get("field_map_version"),
            "basis_verification": item.get("basis_verification", "UNKNOWN"),
            "session_binding_status": item.get("session_binding_status", "FINGERPRINT_ONLY"),
            "capability_status": "BOUND",
            "reason": "MATERIALIZED_DURING_V3_3_GENERATION",
        } for item in observation.get("items", [])]
        context = build_turnover_context(candidates, evidence, bundle_digest=digest, observation_digest=str(observation.get("observation_digest") or ""))
        enhanced = context["items"]
        return {
            "api_contract": CONTRACT_ID,
            "algorithm_contract": ALGORITHM_CONTRACT_ID,
            "status": "AVAILABLE" if evidence else "UNAVAILABLE",
            "layer_status": context["layer_status"],
            "coverage": context["coverage"],
            "parameter_hash": context["parameter_hash"],
            "source_error": observation.get("source_error"),
            "context": {**active["identity"], "output_digest": digest},
            "request": {"candidate_count": int(observation.get("requested_count") or 0)},
            "counts": {"BOUND": len(evidence)} if evidence else {},
            "items": evidence,
            "enhanced_items": enhanced,
            "enhancement_usage": "CONTEXT_AND_OPTIONAL_LOCKED_SLOT_ORDER",
            "materialized": True,
            "observation_digest": observation.get("observation_digest"),
            "guardrails": {"core_score_or_category_rank_changed": False, "online_request_from_page": False, "raw_payload_persisted": False},
        }

    def _fetch(self, active: dict, candidates: list[dict]) -> dict:
        identity = active["identity"]
        target_date = str(identity["trade_date"])
        security_ids = select_enrichment_ids(row.get("security_id") for row in candidates)
        if not security_ids:
            return self._response(active, candidates, [], {}, "NO_SUPPORTED_CANDIDATES", None)
        placeholders = ",".join("?" for _ in security_ids)
        parquet = self.root / "data/normalized/adjusted_daily.parquet"
        try:
            with duckdb.connect() as connection:
                local_rows = connection.execute(
                    f"""select security_id,cast(date as varchar),raw_close,raw_amount,raw_volume
                    from read_parquet(?) where cast(date as varchar)=? and security_id in ({placeholders})""",
                    [str(parquet), target_date, *security_ids],
                ).fetchall()
        except Exception:
            return self._response(active, candidates, security_ids, {}, "LOCAL_FINGERPRINT_UNAVAILABLE", None)
        local = {
            row[0]: LocalDailyFingerprint(row[0], row[1], float(row[2]), float(row[3]), float(row[4]))
            for row in local_rows
        }
        source_rows: dict[str, dict] = {}
        source_error = None
        observed_at = None
        completed_batches = 0
        for start in range(0, len(security_ids), 50):
            batch = security_ids[start:start + 50]
            try:
                result, rows = self.fetcher(
                    batch,
                    OnlineFetchPolicy(timeout_seconds=8, max_response_bytes=200_000, retries=0, cache_ttl_seconds=0),
                )
                completed_batches += 1
                observed_at = result.received_at_utc
                for row in rows:
                    source_rows[row["security_id"]] = {**row, "source_identity_sha256": result.raw_sha256}
            except Exception as exc:
                if self.fetcher is not fetch_tencent_quotes:
                    source_error = type(exc).__name__
                    break
                failures = [f"TENCENT_{type(exc).__name__}"]
                unresolved = list(batch)
                def one_sohu(sid): return fetch_sohu_quotes([sid], OnlineFetchPolicy(timeout_seconds=3, max_response_bytes=200_000, retries=0, cache_ttl_seconds=0))
                with ThreadPoolExecutor(max_workers=8) as pool:
                    futures = {pool.submit(one_sohu, sid): sid for sid in unresolved}
                    for future in as_completed(futures):
                        try:
                            fallback_result, fallback_rows = future.result()
                            for row in fallback_rows: source_rows[row["security_id"]] = {**row, "source_identity_sha256": fallback_result.raw_sha256}
                        except Exception: pass
                unresolved = [sid for sid in unresolved if sid not in source_rows]
                def one_stcn(sid): return fetch_stcn_quotes([sid], OnlineFetchPolicy(timeout_seconds=3, max_response_bytes=200_000, retries=0, cache_ttl_seconds=0))
                with ThreadPoolExecutor(max_workers=8) as pool:
                    futures = {pool.submit(one_stcn, sid): sid for sid in unresolved}
                    for future in as_completed(futures):
                        try:
                            fallback_result, fallback_rows = future.result()
                            for row in fallback_rows: source_rows[row["security_id"]] = {**row, "source_identity_sha256": fallback_result.raw_sha256}
                        except Exception: pass
                completed_batches += 1
                source_error = "_".join(failures) + "_FALLBACK_PARTIAL"
                continue
        items = []
        for security_id in security_ids:
            if security_id not in local:
                items.append({
                    "contract_id": CONTRACT_ID,
                    "security_id": security_id,
                    "trade_date": target_date,
                    "turnover_rate": None,
                    "turnover_basis": "UNKNOWN",
                    "capability_status": "UNAVAILABLE",
                    "reason": "LOCAL_FINGERPRINT_MISSING",
                    "use_scope": "POST_SELECTION_EVIDENCE_AND_QUALIFIED_UNRANKED_SECONDARY_ORDER",
                })
            else:
                items.append(bind_turnover_row(source_rows.get(security_id), local[security_id]))
        return self._response(active, candidates, security_ids, {item["security_id"]: item for item in items}, source_error, observed_at, completed_batches)

    @staticmethod
    def _response(active: dict, candidates: list[dict], requested: list[str], by_id: dict[str, dict], source_error: str | None, observed_at: str | None, completed_batches: int = 0) -> dict:
        items = [by_id[value] for value in requested if value in by_id]
        counts: dict[str, int] = {}
        for item in items:
            status = item["capability_status"]
            counts[status] = counts.get(status, 0) + 1
        bound = counts.get("BOUND", 0)
        status = "AVAILABLE" if bound == len(items) and items else "PARTIAL" if bound else "UNAVAILABLE"
        context = build_turnover_context(candidates, items, bundle_digest=str(active["output_digest"]))
        enhanced = context["items"]
        return {
            "api_contract": CONTRACT_ID,
            "algorithm_contract": ALGORITHM_CONTRACT_ID,
            "status": status,
            "layer_status": context["layer_status"],
            "source_status": status,
            "coverage": context["coverage"],
            "parameter_hash": context["parameter_hash"],
            "source_error": source_error,
            "context": {**active["identity"], "output_digest": active["output_digest"]},
            "request": {"candidate_count": len(requested), "planned_batch_count": (len(requested) + 49) // 50, "completed_batch_count": completed_batches, "batch_size": 50, "retries": 0},
            "observed_at_utc": observed_at,
            "counts": counts,
            "items": items,
            "enhanced_items": enhanced,
            "enhancement_usage": "CONTEXT_AND_OPTIONAL_LOCKED_SLOT_ORDER",
            "guardrails": {"core_score_or_category_rank_changed": False, "local_pipeline_blocked": False, "raw_payload_persisted": False},
        }

    @staticmethod
    def _unavailable(code: str, message: str) -> dict:
        return {
            "api_contract": CONTRACT_ID,
            "status": "UNAVAILABLE",
            "code": code,
            "message": message,
            "items": [],
            "counts": {},
            "cached": False,
            "enhanced_items": [],
            "enhancement_usage": "SECONDARY_ORDER_FOR_QUALIFIED_UNRANKED",
            "guardrails": {"core_score_or_category_rank_changed": False, "local_pipeline_blocked": False, "raw_payload_persisted": False},
        }


__all__ = ["CACHE_SECONDS", "TurnoverEnrichmentService"]
