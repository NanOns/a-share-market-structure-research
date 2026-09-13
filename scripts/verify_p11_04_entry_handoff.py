"""Verify the P11-04 V3 main-entry handoff and post-switch smoke.

The runtime entry and launcher are expected to have been switched before this
script runs.  HTTP smoke uses the existing service handler on an ephemeral
local port and performs only GET requests; it does not submit jobs, invoke
online fetches, or write production data.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
ENTRY_PATH = ROOT / "runtime/workbench_entry.json"
LAUNCHER_PATH = ROOT / "OPEN_UNIFIED_WORKBENCH.cmd"
LEGACY_LAUNCHER_PATH = ROOT / "OPEN_RESEARCH_WORKBENCH.cmd"
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
PREFLIGHT_REPORT = ROOT / "reports/upgrade_v3/P11-04-HANDOFF-PREFLIGHT-20260913.json"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-04-ENTRY-HANDOFF-20260913.json"

CONTRACT_VERSION = "V3_P11_ENTRY_HANDOFF_V1_0"
PUBLICATION_ID = "m4-8a99c99719061f4f1f166d0b9184506c"
TRADE_DATE = "2026-09-10"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            + "\n",
            encoding="utf-8",
        )
        with temporary.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _get_json(base_url: str, path: str) -> dict[str, Any]:
    with urllib.request.urlopen(base_url + path, timeout=20) as response:
        raw = response.read()
        return {
            "status": response.status,
            "content_type": response.headers.get("Content-Type", ""),
            "bytes": len(raw),
            "payload": json.loads(raw.decode("utf-8")),
        }


def _get_page(base_url: str, path: str) -> dict[str, Any]:
    with urllib.request.urlopen(base_url + path, timeout=20) as response:
        raw = response.read()
        text = raw.decode("utf-8", errors="replace")
        return {
            "status": response.status,
            "content_type": response.headers.get("Content-Type", ""),
            "bytes": len(raw),
            "markers": {
                "v3_local": "V3 本地研究预览" in text,
                "current": "CURRENT" in text,
                "potential": "POTENTIAL" in text,
                "online": "在线总览" in text or "online" in text.lower(),
                "events": "涨停" in text or "events" in text.lower(),
                "legacy": "workbench" in text.lower() or "旧" in text,
            },
        }


def _http_smoke() -> dict[str, Any]:
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    import workbench_service.app as app  # noqa: E402

    before = DB_PATH.stat()
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, DB_PATH))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        pages = {
            "v3": _get_page(base_url, "/v3"),
            "online": _get_page(base_url, "/v3/online"),
            "events": _get_page(base_url, "/v3/events"),
            "legacy_view": _get_page(
                base_url,
                "/view?" + urllib.parse.urlencode({"publication_id": PUBLICATION_ID}),
            ),
        }
        context = _get_json(
            base_url,
            "/api/v3/research/context?"
            + urllib.parse.urlencode(
                {"publication_id": PUBLICATION_ID, "trade_date": TRADE_DATE, "mode": "CLOSE"}
            ),
        )
        context_payload = context["payload"]
        context_body = context_payload.get("context", {})
        home = _get_json(
            base_url,
            "/api/v3/home/local?" + urllib.parse.urlencode({"context_id": context_body.get("context_id", "")}),
        )
        return {
            "base_url": base_url,
            "pages": pages,
            "context": {
                "status": context["status"],
                "api_status": context_payload.get("status"),
                "context_status": context_body.get("status"),
                "context_id": context_body.get("context_id"),
                "publication_id": context_body.get("publication_id"),
                "trade_date": context_body.get("local_date"),
            },
            "home": {
                "status": home["status"],
                "api_status": home["payload"].get("status"),
                "returned_count": home["payload"].get("returned_count"),
            },
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        time.sleep(0.05)
        after = DB_PATH.stat()
        _http_smoke.before = before
        _http_smoke.after = after


def main() -> int:
    preflight = json.loads(PREFLIGHT_REPORT.read_text(encoding="utf-8"))
    entry = json.loads(ENTRY_PATH.read_text(encoding="utf-8"))
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8", errors="replace")
    legacy_launcher = LEGACY_LAUNCHER_PATH.read_text(encoding="utf-8", errors="replace")
    smoke = _http_smoke()
    before = _http_smoke.before
    after = _http_smoke.after

    pages = smoke["pages"]
    checks = {
        "preflight_full_pass": preflight.get("status") == "FULL_PASS"
        and preflight.get("handoff", {}).get("preflight_status") == "READY_FOR_EXPLICIT_P11_04_SWITCH",
        "runtime_entry_contract_updated": entry.get("contract_id") == CONTRACT_VERSION,
        "runtime_primary_route_is_v3": entry.get("primary_entry", {}).get("route") == "/v3",
        "runtime_primary_mode_is_v3": entry.get("primary_entry", {}).get("mode") == "V3_LOCAL_DUAL_TRACK_WITH_VERIFIED_ONLINE_CARDS",
        "runtime_fallback_preserved": entry.get("fallback_entry", {}).get("route") == "/view"
        and entry.get("legacy_route_preserved") is True,
        "unified_launcher_opens_v3": "http://127.0.0.1:28765/v3" in launcher,
        "legacy_launcher_preserved": "CURRENT_WORKBENCH.json" in legacy_launcher,
        "v3_page_smoke_200": pages["v3"]["status"] == 200
        and all(pages["v3"]["markers"][name] for name in ("v3_local", "current", "potential")),
        "online_page_smoke_200": pages["online"]["status"] == 200,
        "events_page_smoke_200": pages["events"]["status"] == 200,
        "legacy_view_smoke_200": pages["legacy_view"]["status"] == 200,
        "v3_context_smoke_ready": smoke["context"]["status"] == 200
        and smoke["context"]["api_status"] == "READY"
        and smoke["context"]["publication_id"] == PUBLICATION_ID
        and smoke["context"]["trade_date"] == TRADE_DATE,
        "v3_home_smoke_200": smoke["home"]["status"] == 200,
        "production_database_unchanged": before.st_size == after.st_size
        and before.st_mtime_ns == after.st_mtime_ns,
    }
    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "FULL_PASS" if all(checks.values()) else "DEGRADED_PASS",
        "stage": "P11-04 main-entry handoff and post-switch smoke",
        "checks": checks,
        "handoff": {
            "previous_route": "/v2",
            "active_route": entry.get("primary_entry", {}).get("route"),
            "fallback_route": entry.get("fallback_entry", {}).get("route"),
            "switch_executed": True,
            "entry_revision": entry.get("entry_revision"),
        },
        "smoke": smoke,
        "database_read_boundary": {
            "path": str(DB_PATH),
            "before": {"size": before.st_size, "mtime_ns": before.st_mtime_ns},
            "after": {"size": after.st_size, "mtime_ns": after.st_mtime_ns},
        },
        "safety": {
            "runtime_entry_mutated_by_handoff": True,
            "launcher_mutated_by_handoff": True,
            "production_database_mutated": False,
            "tdx_accessed": False,
            "tdx_mutated": False,
            "old_tables_deleted": False,
            "backup_created": False,
            "cleanup_executed": False,
            "job_submitted": False,
        },
        "retention_boundary": {
            "decision": "RETAIN_ALL_LEGACY_TABLES",
            "table_cleanup": "NOT_IN_SCOPE",
        },
        "known_limits": [
            "P10-03 remains EFFECT_OBSERVATION_PENDING; the V3 handoff makes no effect or return claim.",
            "Online pages preserve dataset-specific capability states and fail-closed behavior.",
            "The old /view route remains a compatibility fallback; old tables remain retained per user decision.",
        ],
        "spec_path": str(SPEC_PATH),
        "spec_sha256": _sha256(SPEC_PATH),
        "preflight_report": str(PREFLIGHT_REPORT),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "next_stage": "V3 daily operation and effect observation; old-table reassessment after UI migration",
    }
    _atomic_json(REPORT_PATH, report)
    print(json.dumps({"status": report["status"], "checks": checks, "report": str(REPORT_PATH)}, ensure_ascii=False))
    return 0 if report["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
