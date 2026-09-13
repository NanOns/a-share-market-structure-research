"""Run a non-mutating P11-04 main-entry handoff preflight.

The preflight proves that the V3 route, fallback route and completed gates are
present.  It deliberately does not edit ``runtime/workbench_entry.json`` or
the launcher: the actual default-entry switch is a separate user-visible
action.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
ENTRY_PATH = ROOT / "runtime/workbench_entry.json"
UNIFIED_LAUNCHER = ROOT / "OPEN_UNIFIED_WORKBENCH.cmd"
LEGACY_LAUNCHER = ROOT / "OPEN_RESEARCH_WORKBENCH.cmd"
APP_PATH = ROOT / "src/workbench_service/app.py"
V3_PAGE = ROOT / "src/workbench_service/static/research-v3.html"
ONLINE_PAGE = ROOT / "src/workbench_service/static/online-p09-v3.html"
EVENT_PAGE = ROOT / "src/workbench_service/static/online-events-v3.html"
REPORT_PATH = ROOT / "reports/upgrade_v3/P11-04-HANDOFF-PREFLIGHT-20260913.json"

GATE_REPORT = ROOT / "reports/upgrade_v3/P11-01-STORAGE-STOP-GROWTH-GATE-20260913.json"
P10_01_REPORT = ROOT / "reports/upgrade_v3/P10-01-LEGACY-MATRIX.json"
P10_02_REPORT = ROOT / "reports/upgrade_v3/P10-02-SECTOR-SET-LINKAGE.json"
P10_03_REPORT = ROOT / "reports/upgrade_v3/P10-03-SIGNAL-EVALUATION.json"
P09_REPORT = ROOT / "reports/upgrade_v3/P09-G09-CURRENT-CLOSE-OUT-20260913.json"

CONTRACT_VERSION = "V3_P11_HANDOFF_PREFLIGHT_V1_0"


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


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object JSON: {path}")
    return value


def main() -> int:
    gate = _read_json(GATE_REPORT)
    p10_01 = _read_json(P10_01_REPORT)
    p10_02 = _read_json(P10_02_REPORT)
    p10_03 = _read_json(P10_03_REPORT)
    p09 = _read_json(P09_REPORT)
    entry_before = ENTRY_PATH.read_bytes()
    unified_text = UNIFIED_LAUNCHER.read_text(encoding="utf-8", errors="replace")
    legacy_text = LEGACY_LAUNCHER.read_text(encoding="utf-8", errors="replace")
    app_text = APP_PATH.read_text(encoding="utf-8", errors="replace")
    v3_text = V3_PAGE.read_text(encoding="utf-8", errors="replace")
    online_text = ONLINE_PAGE.read_text(encoding="utf-8", errors="replace")
    event_text = EVENT_PAGE.read_text(encoding="utf-8", errors="replace")
    entry = _read_json(ENTRY_PATH)
    entry_after = ENTRY_PATH.read_bytes()

    checks = {
        "p11_storage_stop_growth_gate_full_pass": gate.get("status") == "FULL_PASS"
        and gate.get("storage_stop_growth", {}).get("status") == "FULL_PASS",
        "p10_01_legacy_matrix_full_pass": p10_01.get("status") == "FULL_PASS",
        "p10_02_sector_set_linkage_full_pass": p10_02.get("status") == "FULL_PASS",
        "p10_03_effect_state_honest": p10_03.get("status") == "FULL_PASS"
        and p10_03.get("effect_status") == "EFFECT_OBSERVATION_PENDING",
        "p09_verified_online_cards_available": p09.get("release_ready") is True,
        "v3_local_page_present": V3_PAGE.is_file()
        and all(marker in v3_text for marker in ("V3 本地研究预览", "CURRENT", "POTENTIAL", "/api/v3/research/context")),
        "verified_online_pages_present": ONLINE_PAGE.is_file()
        and EVENT_PAGE.is_file()
        and "/api/v3/events/overview" in online_text
        and "/api/v3/events/ladder" in event_text,
        "app_serves_v3_and_fallback_routes": all(
            marker in app_text for marker in ("'/v3'", "'/v3/online'", "'/v3/events'", "u.path=='/view'")
        ),
        "current_primary_entry_is_v2_before_switch": entry.get("primary_entry", {}).get("route") == "/v2",
        "unified_launcher_currently_opens_v2": "http://127.0.0.1:28765/v2" in unified_text,
        "legacy_launcher_and_pointer_preserved": (
            LEGACY_LAUNCHER.is_file()
            and "CURRENT_WORKBENCH.json" in legacy_text
            and entry.get("fallback_entry", {}).get("route") == "/view"
            and entry.get("legacy_route_preserved") is True
        ),
        "entry_unchanged_during_preflight": entry_before == entry_after,
    }

    report = {
        "contract_version": CONTRACT_VERSION,
        "status": "FULL_PASS" if all(checks.values()) else "DEGRADED_PASS",
        "stage": "P11-04 main-entry handoff preflight",
        "checks": checks,
        "handoff": {
            "preflight_status": "READY_FOR_EXPLICIT_P11_04_SWITCH" if all(checks.values()) else "NOT_READY",
            "current_primary_entry": entry.get("primary_entry"),
            "target_primary_entry": {
                "route": "/v3",
                "mode": "V3_LOCAL_DUAL_TRACK_WITH_VERIFIED_ONLINE_CARDS",
            },
            "fallback_entry": entry.get("fallback_entry"),
            "switch_executed": False,
            "entry_mutation_authorized_by_this_preflight": False,
        },
        "evidence": {
            "storage_gate": str(GATE_REPORT),
            "p10_01": str(P10_01_REPORT),
            "p10_02": str(P10_02_REPORT),
            "p10_03": str(P10_03_REPORT),
            "p09": str(P09_REPORT),
            "app": str(APP_PATH),
            "v3_page": str(V3_PAGE),
            "online_page": str(ONLINE_PAGE),
            "event_page": str(EVENT_PAGE),
        },
        "safety": {
            "runtime_entry_mutated": False,
            "launcher_mutated": False,
            "production_database_mutated": False,
            "tdx_accessed": False,
            "cleanup_executed": False,
            "backup_created": False,
        },
        "known_limits": [
            "P10-03 remains EFFECT_OBSERVATION_PENDING; handoff does not claim trading or predictive effect.",
            "Online cards use their dataset-specific capability and fail-closed status; unavailable sources are not replaced with local facts.",
            "Old tables remain retained until V3 development and old-page migration finish, per user decision.",
        ],
        "spec_path": str(SPEC_PATH),
        "spec_sha256": _sha256(SPEC_PATH),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "next_stage": "P11-04 explicit user-authorized default-entry switch and post-switch smoke",
    }
    _atomic_json(REPORT_PATH, report)
    print(json.dumps({"status": report["status"], "checks": checks, "report": str(REPORT_PATH)}, ensure_ascii=False))
    return 0 if report["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
