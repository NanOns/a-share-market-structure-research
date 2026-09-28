from __future__ import annotations

"""Capture bounded CNINFO full-text searches as supplemental, non-exhaustive evidence.

This search helps identify official code-change notices; the endpoint does not publish
an exhaustive code-change registry, so these captures must not close index coverage.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.cninfo.com.cn"
QUERY_URL = BASE + "/new/hisAnnouncement/query"
WARMUP_URL = BASE + "/new/index"
START_DATE = "2023-07-04"
END_DATE = "2026-09-24"
PAGE_SIZE = 30
MAX_PAGES_PER_QUERY = 4
MAX_QUERIES = 12
TERMS = (
    "证券代码变更",
    "变更证券代码",
    "代码变更",
    "股票代码变更",
    "变更股票代码",
    "证券代码调整",
)
PLATES = ("sh", "sz")
OUT_ROOT = ROOT / "data/v4/source_evidence/official_code_change_event_index/cninfo_search"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with temp.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def main() -> int:
    if len(TERMS) * len(PLATES) != MAX_QUERIES:
        raise SystemExit("CNINFO_QUERY_BUDGET_CONTRACT_MISMATCH")
    observed = datetime.now(timezone.utc).replace(microsecond=0)
    run_id = observed.strftime("%Y%m%dT%H%M%SZ")
    run_dir = OUT_ROOT / run_id
    session = requests.Session()
    session.headers.update({
        "User-Agent": "V4-R8.3-official-index-audit/1.0",
        "Referer": BASE + "/new/index.jsp",
        "Accept": "application/json, text/plain, */*",
    })
    warmup = session.get(WARMUP_URL, timeout=(8, 20), allow_redirects=True)
    warmup.raise_for_status()
    warmup_capture = run_dir / "warmup_response.bin"
    atomic_write(warmup_capture, warmup.content)
    query_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    failed_query_count = 0
    request_count = 1
    for plate in PLATES:
        for term in TERMS:
            query_id = f"{plate}_{len(query_rows) + 1:02d}"
            params = {
                "tabName": "fulltext",
                "pageSize": str(PAGE_SIZE),
                "pageNum": "1",
                "isHLtitle": "false",
                "searchkey": term,
                "seDate": f"{START_DATE}~{END_DATE}",
                "plate": plate,
            }
            query = {
                "query_id": query_id,
                "plate": plate,
                "search_term": term,
                "window_start": START_DATE,
                "window_end": END_DATE,
                "page_size": PAGE_SIZE,
                "max_pages": MAX_PAGES_PER_QUERY,
                "request_parameters": {
                    "tabName": "fulltext",
                    "pageSize": str(PAGE_SIZE),
                    "isHLtitle": "false",
                    "searchkey": term,
                    "seDate": f"{START_DATE}~{END_DATE}",
                    "plate": plate,
                    "pageNum": "1..MAX_PAGES_PER_QUERY",
                },
                "pages": [],
                "result_count": 0,
                "status": "PASS",
            }
            for page_num in range(1, MAX_PAGES_PER_QUERY + 1):
                params["pageNum"] = str(page_num)
                page_started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                page = {"page_num": page_num, "requested_at_utc": page_started,
                        "request_parameters": dict(params)}
                request_count += 1
                try:
                    response = session.post(QUERY_URL, data=params, timeout=(8, 25))
                    page["http_status"] = response.status_code
                    page["final_url"] = response.url
                    raw = response.content
                    page_path = run_dir / f"{query_id}_page_{page_num:02d}.json"
                    atomic_write(page_path, raw)
                    page["capture_path"] = page_path.relative_to(ROOT).as_posix()
                    page["response_sha256"] = sha256(raw)
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get("announcements") or [], list):
                        raise ValueError("CNINFO_RESPONSE_SCHEMA_INVALID")
                    announcements = payload.get("announcements") or []
                    page["result_count"] = len(announcements)
                    page["has_more"] = bool(payload.get("hasMore"))
                    page["total_announcement"] = payload.get("totalAnnouncement")
                    for row in announcements:
                        if isinstance(row, dict):
                            result_rows.append({
                                "query_id": query_id,
                                "plate": plate,
                                "search_term": term,
                                "announcement_id": row.get("announcementId"),
                                "title": row.get("announcementTitle"),
                                "sec_code": row.get("secCode"),
                                "org_id": row.get("orgId"),
                                "announcement_time": row.get("announcementTime"),
                                "adjunct_url": row.get("adjunctUrl"),
                            })
                    query["result_count"] += len(announcements)
                    query["pages"].append(page)
                    time.sleep(0.15)
                    if not page["has_more"]:
                        break
                except Exception as exc:  # preserve a failed-query receipt, then continue bounded collection
                    page["error"] = type(exc).__name__ + ": " + str(exc)[:300]
                    query["pages"].append(page)
                    query["status"] = "FAILED"
                    failed_query_count += 1
                    break
            if query["pages"] and query["pages"][-1].get("has_more") is True:
                query["truncated_at_page_limit"] = True
                query["status"] = "INCOMPLETE_PAGE_LIMIT"
            else:
                query["truncated_at_page_limit"] = False
            query_rows.append(query)
            time.sleep(0.15)

    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in result_rows:
        key = (str(row.get("announcement_id") or row.get("adjunct_url") or ""),
               str(row.get("title") or ""))
        deduped.setdefault(key, row)
    announcements = [deduped[key] for key in sorted(deduped)]
    excluded = [row for row in announcements if "纳斯达克" in str(row.get("title") or "")]
    likely_code_change = [
        row for row in announcements
        if any(token in str(row.get("title") or "") for token in ("证券代码", "股票代码", "代码变更"))
    ]
    manifest = {
        "contract_id": "CNINFO_CODE_CHANGE_FULLTEXT_SEARCH_CAPTURE_R1",
        "version": "1.0.0",
        "evidence_class": "SUPPLEMENTAL_NON_EXHAUSTIVE_SEARCH",
        "coverage_effect": "DOES_NOT_CLOSE_OFFICIAL_EVENT_INDEX_COVERAGE",
        "observed_at_utc": observed.isoformat(),
        "source": {
            "name": "CNINFO official disclosure search",
            "origin": BASE,
            "query_endpoint": QUERY_URL,
            "method": "POST",
            "search_interface": WARMUP_URL,
        },
        "capture_runner_sha256": sha256(Path(__file__).resolve().read_bytes()),
        "scope": {
            "window_start": START_DATE,
            "window_end": END_DATE,
            "plates": list(PLATES),
            "terms": list(TERMS),
            "query_count": len(query_rows),
            "page_size": PAGE_SIZE,
            "max_pages_per_query": MAX_PAGES_PER_QUERY,
            "request_count_including_warmup": request_count,
            "request_bound": 1 + MAX_QUERIES * MAX_PAGES_PER_QUERY,
        },
        "warmup": {
            "http_status": warmup.status_code,
            "final_url": warmup.url,
            "capture_path": warmup_capture.relative_to(ROOT).as_posix(),
            "response_sha256": sha256(warmup.content),
        },
        "failed_query_count": failed_query_count,
        "queries": query_rows,
        "deduplicated_result_count": len(announcements),
        "candidate_notice_result_count": len(likely_code_change),
        "candidate_notices": likely_code_change,
        "excluded_out_of_scope_results": [{
            **row,
            "exclusion_reason": "Title identifies a Nasdaq ticker change; it does not establish a change to the A-share source security key.",
        } for row in excluded],
        "limitations": [
            "The official full-text announcement search documents successful query execution and returned hits, not an exhaustive registry of all security-code changes.",
            "Search phrase variants are bounded; alternate wording, OCR quality, or announcement indexing can cause false negatives.",
            "CNINFO plate filters are captured as sh/sz search scopes; they do not independently prove complete SH_MAIN, STAR, SZ_MAIN, or CHINEXT event enumeration.",
            "Candidate titles require notice-level review before they can add or resolve an official identity event.",
        ],
        "acceptance": "PASS_CAPTURE_ONLY" if failed_query_count == 0 and all(q["status"] == "PASS" and not q["truncated_at_page_limit"] for q in query_rows) else "BLOCKED_INCOMPLETE_CAPTURE",
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    manifest_path = run_dir / "query_manifest.json"
    atomic_write(manifest_path, manifest_bytes)
    print(json.dumps({
        "status": manifest["acceptance"],
        "query_count": len(query_rows),
        "failed_query_count": failed_query_count,
        "deduplicated_result_count": len(announcements),
        "candidate_notice_result_count": len(likely_code_change),
        "excluded_out_of_scope_count": len(excluded),
        "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": sha256(manifest_bytes),
    }, ensure_ascii=False))
    return 0 if manifest["acceptance"] == "PASS_CAPTURE_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
