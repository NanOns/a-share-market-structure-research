import json
from pathlib import Path

import pytest

from workbench_service.source_freezer import (
    CONTRACT_VERSION,
    SourceFreezeError,
    atomic_write_manifest,
    build_source_manifest,
    directory_digest,
    verify_source_manifest,
)


def _manifest(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"frozen-input")
    return source, build_source_manifest(
        publication_id="pub-1",
        cutoff_date="2026-09-08",
        source_revision_id=1,
        source_identity_sha256="identity",
        source_snapshot_manifest_sha256="snapshot",
        source_bundle_id="bundle-1",
        observed_at="2026-09-08T09:00:00+00:00",
        window_plan={"output_start": "2025-08-28", "output_end": "2026-09-08", "read_start": "2025-04-03", "read_end": "2026-09-08", "output_days": 250, "required_history": 100, "missing_dates": []},
        inputs=[{"path": "source.bin", "kind": "file", "role": "raw_day_source", "sha256": __import__('hashlib').sha256(b"frozen-input").hexdigest(), "observed_at": "2026-09-08T09:00:00+00:00", "effective_date": "2026-09-08", "date_scope": {"from": "2025-04-03", "to": "2026-09-08"}}],
    )


def test_manifest_is_versioned_atomic_and_verifiable(tmp_path):
    source, manifest = _manifest(tmp_path)
    assert manifest["contract_version"] == CONTRACT_VERSION
    path = atomic_write_manifest(tmp_path / "reports/SOURCE_MANIFEST.json", manifest)
    assert json.loads(path.read_text(encoding="utf-8")) == manifest
    assert verify_source_manifest(tmp_path, manifest)["status"] == "PASS"
    atomic_write_manifest(path, manifest)


def test_manifest_detects_source_change_and_immutable_conflict(tmp_path):
    source, manifest = _manifest(tmp_path)
    path = atomic_write_manifest(tmp_path / "SOURCE_MANIFEST.json", manifest)
    source.write_bytes(b"changed-input")
    assert verify_source_manifest(tmp_path, manifest)["status"] == "FAIL"
    conflicting = dict(manifest, observed_at="2026-09-08T10:00:00+00:00")
    payload = dict(conflicting)
    payload.pop("manifest_sha256", None)
    conflicting["manifest_sha256"] = __import__('hashlib').sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    with pytest.raises(SourceFreezeError, match="IMMUTABLE_CONFLICT"):
        atomic_write_manifest(path, conflicting)


def test_manifest_rejects_workspace_escape(tmp_path):
    _, manifest = _manifest(tmp_path)
    escaped = dict(manifest)
    escaped["inputs"] = [dict(manifest["inputs"][0], path="../outside.bin")]
    payload = dict(escaped)
    payload.pop("manifest_sha256", None)
    escaped["manifest_sha256"] = __import__('hashlib').sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    with pytest.raises(SourceFreezeError, match="SOURCE_PATH_OUTSIDE_WORKSPACE"):
        verify_source_manifest(tmp_path, escaped)


def test_directory_tree_hash_detects_content_change_without_count_change(tmp_path):
    folder = tmp_path / "raw"
    folder.mkdir()
    (folder / "a.day").write_bytes(b"one")
    tree = directory_digest(folder)
    _, manifest = _manifest(tmp_path)
    manifest["inputs"] = [{"path": "raw", "kind": "directory", "role": "raw_day_source", **tree}]
    payload = dict(manifest)
    payload.pop("manifest_sha256", None)
    manifest["manifest_sha256"] = __import__('hashlib').sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    assert verify_source_manifest(tmp_path, manifest)["status"] == "PASS"
    (folder / "a.day").write_bytes(b"two")
    assert verify_source_manifest(tmp_path, manifest)["status"] == "FAIL"
