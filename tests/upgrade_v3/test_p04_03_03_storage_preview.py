from datetime import date
import hashlib
import json
from pathlib import Path

import duckdb

from workbench_ops import StorageGovernance


def _service(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text('tdx:\n  root: "D:/new_tdx"\n', encoding="utf-8")
    database = tmp_path / "data/database/market_research.duckdb"
    database.parent.mkdir(parents=True)
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE publications (publication_id VARCHAR, source_manifest_sha256 VARCHAR, source_path VARCHAR, status VARCHAR)")
        connection.execute("CREATE TABLE jobs (job_id VARCHAR, status VARCHAR, payload_json JSON)")
        connection.execute("CREATE TABLE cleanup_jobs (cleanup_job_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        connection.execute("INSERT INTO cleanup_jobs VALUES ('existing', '{}')")
    return StorageGovernance(tmp_path, database), database


def _bundle(root: Path, target_date: str, *, active=False):
    package = root / "data/input_staging/packages" / target_date.replace("-", "") / "hsjday.zip"
    package.parent.mkdir(parents=True, exist_ok=True)
    package.write_bytes((target_date + "-package").encode())
    extracted = root / "data/input_staging/extracted" / target_date.replace("-", "")
    extracted.mkdir(parents=True, exist_ok=True)
    (extracted / "day.bin").write_bytes(b"day")
    metadata_file = root / "data/input_staging/metadata" / target_date.replace("-", "") / "T0002/hq_cache/tdxhy.cfg"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.write_bytes(b"metadata")
    package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
    body = {
        "contract": "source-bundle-v1.0",
        "target_trade_date": target_date,
        "package": {"sha256": package_sha, "byte_count": package.stat().st_size, "staged_path": str(package.relative_to(root)).replace("\\", "/")},
        "extraction": {"root": str(extracted.relative_to(root)).replace("\\", "/"), "entry_count": 1, "expanded_bytes": 3, "package_sha256": package_sha},
        "metadata": {"root": str(metadata_file.parents[2].relative_to(root)).replace("\\", "/"), "files": {"T0002/hq_cache/tdxhy.cfg": {"size": 8, "sha256": hashlib.sha256(b"metadata").hexdigest()} }},
        "validation": {},
        "calendar_sha256": "c" * 64,
        "parser_version": "m3-tdx-input-v1.0",
        "read_only": True,
    }
    bundle_id = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    body["source_bundle_id"] = bundle_id
    receipt = root / "data/source_bundles" / bundle_id / "source_bundle.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps(body, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return bundle_id, receipt, active


def test_v3_preview_retains_recent_two_and_never_writes_cleanup_plan(tmp_path):
    ops, database = _service(tmp_path)
    old_id, _, _ = _bundle(tmp_path, "2026-09-07")
    active_id, _, _ = _bundle(tmp_path, "2026-09-08", active=True)
    recent_id, _, _ = _bundle(tmp_path, "2026-09-09")
    latest_id, _, _ = _bundle(tmp_path, "2026-09-10")
    with duckdb.connect(str(database)) as connection:
        for bundle_id in (old_id, active_id, recent_id, latest_id):
            connection.execute("INSERT INTO publications VALUES (?, ?, ?, 'SUCCESS')", [bundle_id, bundle_id, "data/source_bundles/" + bundle_id])
        connection.execute("INSERT INTO jobs VALUES ('active', 'RUNNING', ?)", [json.dumps({"source_bundle_id": active_id})])
    cache = tmp_path / "data/.phase1_cache"
    cache.mkdir(parents=True)
    (cache / "a.bin").write_bytes(b"a")
    (cache / "b.bin").write_bytes(b"bb")

    result = ops.write_v3_input_storage_preview("reports/upgrade_v3/P04-03-03_STORAGE_PREVIEW.json", as_of=date(2026, 9, 12))
    preview = result["preview"]

    assert set(preview["source_bundles"]["retained_bundle_ids"]) == {recent_id, latest_id}
    assert preview["source_bundles"]["active_task_bundle_ids"] == [active_id]
    assert {item["decision"] for item in preview["extracted"]["items"]} == {
        "PREVIEW_RECLAIMABLE_REBUILDABLE", "PROTECTED_ACTIVE_TASK_REFERENCE", "PROTECTED_RECENT_USED_BUNDLE"
    }
    assert preview["phase1_cache"]["decision"] == "WITHIN_BUDGET"
    assert preview["policy"]["deletion_executed"] is False
    assert (tmp_path / "reports/upgrade_v3/P04-03-03_STORAGE_PREVIEW.json").is_file()
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM cleanup_jobs").fetchone()[0] == 1
    assert (tmp_path / "data/input_staging/extracted/20260907/day.bin").is_file()


def test_v3_cache_preview_fails_closed_when_budget_is_exceeded(tmp_path):
    ops, _ = _service(tmp_path)
    cache = tmp_path / "data/.phase1_cache"
    cache.mkdir(parents=True)
    item = cache / "kept.bin"
    item.write_bytes(b"12345")

    preview = ops.preview_v3_input_storage(as_of=date(2026, 9, 12), phase1_cache_budget_bytes=3)

    assert preview["phase1_cache"]["decision"] == "BLOCKED_NO_SAFE_CANDIDATE"
    assert preview["phase1_cache"]["preview_reclaimable"] == []
    assert item.is_file()


def test_storage_reference_audit_reports_stale_flag_without_mutation(tmp_path):
    ops, database = _service(tmp_path)
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE storage_objects (storage_object_id VARCHAR PRIMARY KEY, payload_json JSON)")
        connection.execute(
            "INSERT INTO storage_objects VALUES (?, ?)",
            ["obj-stale", json.dumps({"storage_object_id": "obj-stale", "referenced": True, "kind": "ANALYSIS_RESULT_OBJECT"})],
        )
    result = ops.write_v3_storage_reference_audit("reports/upgrade_v3/P00-02_STORAGE_REFERENCE_AUDIT.json")
    assert result["audit"]["issues"]["stale_referenced_flags"] == ["obj-stale"]
    assert result["audit"]["automatic_action"] == "NONE"
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT payload_json FROM storage_objects WHERE storage_object_id='obj-stale'").fetchone()[0]


def test_source_catalog_audit_keeps_unregistered_receipts_read_only(tmp_path):
    ops, database = _service(tmp_path)
    bundle_id, _, _ = _bundle(tmp_path, "2026-09-10")
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE source_bundles (source_bundle_id VARCHAR PRIMARY KEY, payload_json JSON)")
        connection.execute("CREATE TABLE source_packages (source_package_id VARCHAR PRIMARY KEY, payload_json JSON)")
        connection.execute("CREATE TABLE source_files (source_package_id VARCHAR, relative_path VARCHAR, payload_json JSON)")
        connection.execute("INSERT INTO source_bundles VALUES ('catalog-only', '{}')")
    result = ops.write_v3_source_catalog_audit("reports/upgrade_v3/P04-03-03_SOURCE_CATALOG_AUDIT.json")
    audit = result["audit"]
    assert audit["physical_receipts_not_in_catalog"] == [bundle_id]
    assert audit["catalog_entries_without_physical_receipt"] == ["catalog-only"]
    assert audit["automatic_action"] == "NONE"
