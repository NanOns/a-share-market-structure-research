from __future__ import annotations

"""Manifest-based acceptance for BaoStock date-level DailyUpdates access."""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from workbench_analysis.daily_source_freeze import ensure_outside_tdx


CONTRACT_ID = "BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1"
CONTRACT_VERSION = "1.0.0"
REQUIRED_METHODS = (
    "query_daily_history_k_AStock",
    "query_daily_adjust_factor",
)
VALID_AUTH_MODES = frozenset({"PUBLIC_ANONYMOUS", "PUBLIC_ACCOUNT", "VIP_API_KEY"})


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def runtime_acceptance_error(
    manifest: Mapping[str, Any] | None,
    *,
    sdk: Mapping[str, Any],
    auth_mode: str,
) -> str | None:
    if not isinstance(manifest, Mapping) or manifest.get("contract_id") != CONTRACT_ID:
        return "RUNTIME_ACCEPTANCE_MANIFEST_MISSING"
    if manifest.get("version") != CONTRACT_VERSION or manifest.get("status") != "ACCEPTED":
        return "RUNTIME_ACCEPTANCE_NOT_PASS"
    material = dict(manifest)
    supplied_digest = str(material.pop("manifest_sha256", ""))
    if not supplied_digest or supplied_digest != canonical_sha256(material):
        return "RUNTIME_ACCEPTANCE_MANIFEST_DIGEST_INVALID"
    mode = str(auth_mode or "").upper()
    if mode not in VALID_AUTH_MODES or manifest.get("auth_mode") != mode:
        return "RUNTIME_ACCEPTANCE_AUTH_MODE_MISMATCH"
    expected_runtime = manifest.get("runtime")
    if not isinstance(expected_runtime, Mapping):
        return "RUNTIME_ACCEPTANCE_RUNTIME_MISSING"
    for key in ("package", "version", "installed_python_sources_sha256"):
        if not sdk.get(key) or expected_runtime.get(key) != sdk.get(key):
            return "RUNTIME_ACCEPTANCE_SDK_FINGERPRINT_MISMATCH"
    if tuple(manifest.get("supported_methods", ())) != REQUIRED_METHODS:
        return "RUNTIME_ACCEPTANCE_METHOD_SET_MISMATCH"
    smoke = manifest.get("live_smoke")
    if not isinstance(smoke, Mapping) or smoke.get("status") != "PASS":
        return "RUNTIME_ACCEPTANCE_LIVE_SMOKE_NOT_PASS"
    if smoke.get("auth_mode") != mode:
        return "RUNTIME_ACCEPTANCE_SMOKE_AUTH_MODE_MISMATCH"
    target_date = str(smoke.get("target_date") or "")
    daily = smoke.get("daily")
    factor = smoke.get("adjustment_factor")
    if not target_date or not isinstance(daily, Mapping) or not isinstance(factor, Mapping):
        return "RUNTIME_ACCEPTANCE_SMOKE_EVIDENCE_MISSING"
    for method, record in zip(REQUIRED_METHODS, (daily, factor), strict=True):
        if (record.get("method") != method or record.get("provider_date") != target_date
                or not isinstance(record.get("row_count"), int) or record.get("row_count", -1) < 0
                or not record.get("response_sha256")
                or not isinstance(record.get("fields"), list) or not record.get("fields")):
            return "RUNTIME_ACCEPTANCE_SMOKE_RESPONSE_INVALID"
    receipt = manifest.get("smoke_receipt")
    if not isinstance(receipt, Mapping) or not receipt.get("path") or not receipt.get("sha256"):
        return "RUNTIME_ACCEPTANCE_SMOKE_RECEIPT_BINDING_MISSING"
    return None


def load_runtime_acceptance_manifest(
    path: Path,
    *,
    project_root: Path,
    tdx_root: Path = Path("D:/new_tdx"),
) -> dict[str, Any]:
    """Load an accepted manifest and verify its append-only live-smoke receipt."""
    ensure_outside_tdx(path, tdx_root)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("RUNTIME_ACCEPTANCE_MANIFEST_UNREADABLE") from exc
    smoke_ref = manifest.get("smoke_receipt")
    if not isinstance(smoke_ref, Mapping):
        raise ValueError("RUNTIME_ACCEPTANCE_SMOKE_RECEIPT_BINDING_MISSING")
    root = project_root.resolve()
    smoke_path = (root / str(smoke_ref.get("path") or "")).resolve()
    try:
        smoke_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("RUNTIME_ACCEPTANCE_SMOKE_RECEIPT_OUTSIDE_PROJECT") from exc
    ensure_outside_tdx(smoke_path, tdx_root)
    try:
        raw = smoke_path.read_bytes()
        receipt = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("RUNTIME_ACCEPTANCE_SMOKE_RECEIPT_UNREADABLE") from exc
    if hashlib.sha256(raw).hexdigest() != smoke_ref.get("sha256"):
        raise ValueError("RUNTIME_ACCEPTANCE_SMOKE_RECEIPT_DIGEST_MISMATCH")
    smoke = manifest.get("live_smoke")
    if (not isinstance(smoke, Mapping) or receipt.get("contract_id") != "BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1"
            or receipt.get("status") != "PASS"):
        raise ValueError("RUNTIME_ACCEPTANCE_LIVE_SMOKE_NOT_PASS")
    if (receipt.get("runtime") != manifest.get("runtime") or receipt.get("auth_mode") != manifest.get("auth_mode")
            or receipt.get("live_smoke") != dict(smoke)):
        raise ValueError("RUNTIME_ACCEPTANCE_SMOKE_RECEIPT_CONTENT_MISMATCH")
    return manifest


def build_runtime_acceptance_manifest(
    *,
    sdk: Mapping[str, Any],
    auth_mode: str,
    live_smoke: Mapping[str, Any],
    smoke_receipt_path: str,
    smoke_receipt_sha256: str,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "version": CONTRACT_VERSION,
        "status": "ACCEPTED",
        "runtime": {key: sdk[key] for key in ("package", "version", "installed_python_sources_sha256")},
        "auth_mode": auth_mode,
        "supported_methods": list(REQUIRED_METHODS),
        "live_smoke": dict(live_smoke),
        "smoke_receipt": {"path": smoke_receipt_path, "sha256": smoke_receipt_sha256},
    }
    error = runtime_acceptance_error(manifest | {"manifest_sha256": canonical_sha256(manifest)},
                                     sdk=sdk, auth_mode=auth_mode)
    if error:
        raise ValueError("RUNTIME_ACCEPTANCE_BUILD_REJECTED:" + error)
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest
