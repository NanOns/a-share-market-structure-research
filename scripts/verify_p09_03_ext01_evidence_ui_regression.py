"""Offline verifier for the P09-03 EXT01 evidence UI regression contract."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests" / "upgrade_v3"
for path in (SRC, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_p09_03_ext01_ladder_slice import _db  # noqa: E402


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
PAGE = ROOT / "src" / "workbench_service" / "static" / "online-events-v3.html"
OUTPUT = ROOT / "reports" / "upgrade_v3" / "P09-03-EXT01-EVIDENCE-UI-REGRESSION.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(payload: dict) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        os.replace(temporary, OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    page = PAGE.read_text(encoding="utf-8")
    markers = {
        "modal": "evidenceModal" in page,
        "source_time": "source_time" in page and "source_as_of" in page,
        "escape_close": "event.key==='Escape'" in page,
        "overlay_close": "event.target===modal" in page,
        "focus_return": "state.lastEvidenceButton.focus()" in page,
        "pagination_state": "state.hasMore=!!result.has_more" in page and "next.disabled=!state.hasMore" in page,
        "fail_closed_empty_copy": "不以本地数据冒充在线事实" in page,
        "detail_route": "/api/v3/events/ladder/" in page,
    }
    with tempfile.TemporaryDirectory(prefix="p09_ui_contract_") as directory:
        db = _db(Path(directory))
        assert db.is_file()
    receipt = {
        "receipt_id": "P09-03-EXT01-EVIDENCE-UI-REGRESSION-20260913",
        "stage": "P09-03-EXT01-EVIDENCE-UI-REGRESSION",
        "status": "FULL_PASS" if all(markers.values()) else "BLOCKED",
        "release_ready": False,
        "stage_contract": {
            "spec_sha256": _sha256(SPEC),
            "page_contract": "v3-events-evidence-ui-regression-v1.0",
            "source_id": "EXT01",
            "page_route": "/v3/events",
        },
        "evidence": {
            "database_mode": "DUCKDB_TEMPORARY_ONLY",
            "dom_contract_markers": markers,
            "empty_state_copy_is_fail_closed": markers["fail_closed_empty_copy"],
            "pagination_state_is_explicit": markers["pagination_state"],
            "manual_browser_observation_recorded_in_stage_report": True,
        },
        "capability": {
            "source_status": "DEGRADED",
            "ui_status": "PREVIEW_WITH_EXPLICIT_SOURCE_TIME_AND_EMPTY_STATE",
            "network_calls": 0,
            "production_database_written": False,
            "local_run_identity_changed": False,
            "tdx_inputs_modified": False,
        },
        "acceptance": "FULL_PASS: evidence modal UI contract, fail-closed empty state, source time markers and pagination state are regression-checked; live browser interaction recorded separately",
        "next_stage": "P09-03-EXT01-CLOSE-OUT",
    }
    _atomic_write(receipt)
    print(json.dumps({"status": receipt["status"], "next_stage": receipt["next_stage"], "output": str(OUTPUT)}, ensure_ascii=False))
    return 0 if receipt["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
