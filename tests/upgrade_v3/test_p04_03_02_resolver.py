from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import zipfile

import pytest

from workbench_input.pipeline import ExtractionPolicy, restore_source_bundle_extraction


def _zip_bytes(entries):
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries:
            archive.writestr(name, value)
    return output.getvalue()


def _sealed_receipt(root: Path, *, staged_path=True):
    target_date = "2026-09-07"
    package_path = root / "data/input_staging/packages/20260907/hsjday.zip"
    package_path.parent.mkdir(parents=True)
    package_path.write_bytes(_zip_bytes([
        ("vipdoc/sh/lday/sh600001.day", b"day-600001"),
        ("vipdoc/sz/lday/sz000001.day", b"day-000001"),
    ]))
    with zipfile.ZipFile(package_path) as archive:
        infos = archive.infolist()
        extraction = {
            "entry_count": len(infos),
            "expanded_bytes": sum(info.file_size for info in infos),
            "package_sha256": sha256(package_path.read_bytes()).hexdigest(),
            "root": "data/input_staging/extracted/20260907",
        }
    package = {
        "byte_count": package_path.stat().st_size,
        "sha256": extraction["package_sha256"],
    }
    if staged_path:
        package["staged_path"] = "data/input_staging/packages/20260907/hsjday.zip"
    body = {
        "calendar_sha256": "c" * 64,
        "contract": "source-bundle-v1.0",
        "target_trade_date": target_date,
        "package": package,
        "extraction": extraction,
        "metadata": {"root": "data/input_staging/metadata/20260907", "files": {}},
        "validation": {},
        "parser_version": "m3-tdx-input-v1.0",
        "read_only": True,
    }
    identity = sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    body["source_bundle_id"] = identity
    receipt = root / "data/source_bundles" / identity / "source_bundle.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps(body, sort_keys=True, indent=2), encoding="utf-8")
    return receipt, package_path, extraction


def test_resolver_rebuilds_missing_extraction_from_retained_package(tmp_path):
    receipt, package_path, extraction = _sealed_receipt(tmp_path)
    destination = tmp_path / "recovery/20260907"

    result = restore_source_bundle_extraction(
        receipt,
        destination,
        required_members=("vipdoc/sh/lday/sh600001.day", "vipdoc/sz/lday/sz000001.day"),
        policy=ExtractionPolicy(max_compression_ratio=1000),
    )

    assert result["status"] == "PASS"
    assert result["fallback_used"] is False
    assert result["extraction"]["entry_count"] == extraction["entry_count"]
    assert result["extraction"]["expanded_bytes"] == extraction["expanded_bytes"]
    assert result["extraction"]["package_sha256"] == extraction["package_sha256"]
    assert (destination / "vipdoc/sh/lday/sh600001.day").read_bytes() == b"day-600001"
    assert (destination / "vipdoc/sz/lday/sz000001.day").read_bytes() == b"day-000001"
    assert sha256(package_path.read_bytes()).hexdigest() == extraction["package_sha256"]


def test_resolver_supports_legacy_receipt_without_staged_path(tmp_path):
    receipt, _, _ = _sealed_receipt(tmp_path, staged_path=False)

    result = restore_source_bundle_extraction(
        receipt,
        tmp_path / "recovery/legacy",
        required_members=("vipdoc/sh/lday/sh600001.day",),
        policy=ExtractionPolicy(max_compression_ratio=1000),
    )

    assert result["status"] == "PASS"
    assert result["fallback_used"] is True


def test_resolver_rejects_tampered_retained_package_before_writing(tmp_path):
    receipt, package_path, _ = _sealed_receipt(tmp_path)
    package_path.write_bytes(package_path.read_bytes() + b"tampered")
    destination = tmp_path / "recovery/tampered"

    with pytest.raises(ValueError, match="SOURCE_PACKAGE_(SIZE|MISMATCH)"):
        restore_source_bundle_extraction(receipt, destination)
    assert not destination.exists()
