from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import v4_01_identity_event_discovery_r8_3 as discovery


def _capture_fixture(root: Path) -> Path:
    run_dir = root / "evidence" / "20260928T000000Z"
    run_dir.mkdir(parents=True)
    response = b'{"announcements":[],"hasMore":false}'
    response_path = root / "raw" / "page.json"
    response_path.parent.mkdir(parents=True)
    response_path.write_bytes(response)
    queries = []
    for index in range(12):
        queries.append({
            "query_id": f"query_{index + 1:02d}",
            "status": "PASS",
            "truncated_at_page_limit": False,
            "pages": [{
                "capture_path": response_path.relative_to(root).as_posix(),
                "response_sha256": hashlib.sha256(response).hexdigest(),
            }],
        })
    manifest = {
        "contract_id": "CNINFO_CODE_CHANGE_FULLTEXT_SEARCH_CAPTURE_R1",
        "acceptance": "PASS_CAPTURE_ONLY",
        "coverage_effect": "DOES_NOT_CLOSE_OFFICIAL_EVENT_INDEX_COVERAGE",
        "observed_at_utc": "2026-09-28T00:00:00+00:00",
        "scope": {"query_count": 12},
        "failed_query_count": 0,
        "queries": queries,
    }
    manifest_path = run_dir / "query_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_supplemental_search_capture_requires_hash_bound_successful_queries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _capture_fixture(tmp_path)
    monkeypatch.setattr(discovery, "ROOT", tmp_path)
    monkeypatch.setattr(discovery, "SEARCH_CAPTURE_ROOT", tmp_path / "evidence")

    captured = discovery.supplemental_search_capture()

    assert captured is not None
    assert captured["manifest_path"] == manifest_path.relative_to(tmp_path).as_posix()
    assert captured["manifest"]["coverage_effect"] == "DOES_NOT_CLOSE_OFFICIAL_EVENT_INDEX_COVERAGE"


def test_supplemental_search_capture_rejects_changed_raw_response_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _capture_fixture(tmp_path)
    monkeypatch.setattr(discovery, "ROOT", tmp_path)
    monkeypatch.setattr(discovery, "SEARCH_CAPTURE_ROOT", tmp_path / "evidence")
    (tmp_path / "raw" / "page.json").write_bytes(b"tampered")

    with pytest.raises(SystemExit, match="R8_3_SUPPLEMENTAL_SEARCH_RESPONSE_HASH_MISMATCH"):
        discovery.supplemental_search_capture()
