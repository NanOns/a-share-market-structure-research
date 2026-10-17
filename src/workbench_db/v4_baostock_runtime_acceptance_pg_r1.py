"""Append-only PG authority for date-bound BaoStock runtime acceptance.

The local smoke files are accepted only as an explicit ingress input. Runtime
consumers resolve the exact trade-date fact from PG and never follow a local
manifest or descriptor locator.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from . import v4_native
from .v4_forward_pg_r1 import ForwardFactStore, canonical, digest

CONTRACT = "V4_BAOSTOCK_RUNTIME_ACCEPTANCE_PG_R1"
FOLDER = "data/v4/baostock_runtime_acceptance_pg_r1"
KIND = "daily_runtime_acceptance"


def _key(day: str) -> str:
    from datetime import date
    return date.fromisoformat(day).isoformat()


def _expected_identity() -> Mapping[str, Any]:
    try:
        value = json.loads(os.environ.get("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", "{}"))
    except ValueError as exc:
        raise ValueError("PG_DATABASE_IDENTITY_CONFIGURATION_INVALID") from exc
    if not isinstance(value, dict) or not value:
        raise ValueError("PG_EXPECTED_DATABASE_IDENTITY_REQUIRED")
    return value


def _record(day: str, manifest: Mapping[str, Any], receipt_raw: bytes) -> dict[str, Any]:
    receipt = json.loads(receipt_raw.decode("utf-8"))
    manifest_raw = canonical(dict(manifest))
    if hashlib.sha256(receipt_raw).hexdigest() != manifest.get("smoke_receipt", {}).get("sha256"):
        raise ValueError("BAOSTOCK_PG_SMOKE_RECEIPT_DIGEST_MISMATCH")
    smoke = manifest.get("live_smoke")
    if (manifest.get("contract_id") not in {
                "BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1",
                "OPERATIONAL_BAOSTOCK_RUNTIME_ZERO_CHANGE_V2",
            }
            or manifest.get("status") != "ACCEPTED"
            or not isinstance(smoke, Mapping) or smoke.get("target_date") != day
            or receipt.get("contract_id") != "BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1"
            or receipt.get("status") != "PASS" or receipt.get("target_date") != day
            or receipt.get("runtime") != manifest.get("runtime")
            or receipt.get("auth_mode") != manifest.get("auth_mode")
            or receipt.get("live_smoke") != dict(smoke)):
        raise ValueError("BAOSTOCK_PG_RUNTIME_ACCEPTANCE_BINDING_INVALID")
    from workbench_analysis.baostock_runtime_acceptance import canonical_sha256, runtime_acceptance_error
    material = dict(manifest)
    supplied = material.pop("manifest_sha256", "")
    if supplied != canonical_sha256(material):
        raise ValueError("BAOSTOCK_PG_RUNTIME_MANIFEST_DIGEST_INVALID")
    error = _acceptance_error(manifest, sdk=manifest.get("runtime", {}),
                              auth_mode=str(manifest.get("auth_mode", "")))
    if error:
        raise ValueError("BAOSTOCK_PG_RUNTIME_ACCEPTANCE_INVALID:" + error)
    return {
        "contract_id": CONTRACT,
        "contract_version": "1.0.0",
        "trade_date": day,
        "manifest": dict(manifest),
        "smoke_receipt": receipt,
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "smoke_receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
    }


def _acceptance_error(manifest: Mapping[str, Any], *, sdk: Mapping[str, Any], auth_mode: str) -> str | None:
    if manifest.get("contract_id") == "OPERATIONAL_BAOSTOCK_RUNTIME_ZERO_CHANGE_V2":
        from workbench_analysis.operational_runtime_acceptance_v2 import error
        return error(manifest, sdk=sdk, auth_mode=auth_mode)
    from workbench_analysis.baostock_runtime_acceptance import runtime_acceptance_error
    return runtime_acceptance_error(manifest, sdk=sdk, auth_mode=auth_mode)


def append_from_files(root: Path, day: str, manifest_path: Path) -> dict[str, Any]:
    """Validate exact ingress bytes and append the acceptance record to PG."""
    root = Path(root).resolve()
    if root.drive.upper() != "G:":
        raise ValueError("BAOSTOCK_PG_RUNTIME_G_ROOT_REQUIRED")
    from workbench_analysis.baostock_runtime_acceptance import load_runtime_acceptance_manifest
    manifest_path = Path(manifest_path).resolve()
    manifest = load_runtime_acceptance_manifest(manifest_path, project_root=root)
    receipt_ref = manifest["smoke_receipt"]
    receipt_path = (root / receipt_ref["path"]).resolve()
    try:
        receipt_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("BAOSTOCK_PG_SMOKE_RECEIPT_PATH_ESCAPE") from exc
    record = _record(_key(day), manifest, receipt_path.read_bytes())
    store = ForwardFactStore(root, FOLDER)
    binding = store.append(KIND, _key(day), record, migration_timeout_seconds=120)
    return {"contract_id": CONTRACT, "trade_date": _key(day), "binding": binding,
            "payload_sha256": digest(canonical(record))}


def load(root: Path, day: str, *, sdk: Mapping[str, Any], auth_mode: str | None = None) -> dict[str, Any]:
    """Read and validate one exact date from PG under read-only RR isolation."""
    root = Path(root).resolve()
    key = _key(day)
    schema = v4_native.workspace_schema(root / FOLDER, "forward")
    with v4_native.connection(schema, read_only=True) as pg:
        identity = ForwardFactStore._database_identity(pg)
        if identity != dict(_expected_identity()):
            raise ValueError("BAOSTOCK_PG_RUNTIME_DATABASE_IDENTITY_MISMATCH")
        row = pg.execute(
            "SELECT payload,payload_sha256 FROM forward_facts WHERE kind=%s AND fact_key=%s",
            (KIND, key),
        ).fetchone()
    if row is None:
        raise ValueError("BAOSTOCK_PG_RUNTIME_ACCEPTANCE_NOT_FOUND")
    payload_raw = row[0].encode("utf-8")
    if digest(payload_raw) != row[1]:
        raise ValueError("BAOSTOCK_PG_RUNTIME_PAYLOAD_DIGEST_MISMATCH")
    record = json.loads(payload_raw)
    if (record.get("contract_id") != CONTRACT or record.get("contract_version") != "1.0.0"
            or record.get("trade_date") != key
            or hashlib.sha256(canonical(record.get("manifest", {}))).hexdigest() != record.get("manifest_sha256")
            or hashlib.sha256(canonical(record.get("smoke_receipt", {}))).hexdigest() != record.get("smoke_receipt_sha256")):
        raise ValueError("BAOSTOCK_PG_RUNTIME_RECORD_BINDING_INVALID")
    manifest = record["manifest"]
    receipt = record["smoke_receipt"]
    # The ingress digest uses original receipt bytes. Canonical PG JSON is the
    # stored representation, so validate its semantic binding independently.
    smoke = manifest.get("live_smoke")
    if (manifest.get("contract_id") not in {
                "BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1",
                "OPERATIONAL_BAOSTOCK_RUNTIME_ZERO_CHANGE_V2",
            }
            or manifest.get("status") != "ACCEPTED" or smoke.get("target_date") != key
            or receipt.get("contract_id") != "BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1"
            or receipt.get("status") != "PASS" or receipt.get("target_date") != key
            or receipt.get("runtime") != manifest.get("runtime")
            or receipt.get("auth_mode") != manifest.get("auth_mode")
            or receipt.get("live_smoke") != smoke):
        raise ValueError("BAOSTOCK_PG_RUNTIME_ACCEPTANCE_BINDING_INVALID")
    selected_auth = auth_mode or str(manifest.get("auth_mode", ""))
    error = _acceptance_error(manifest, sdk=sdk, auth_mode=selected_auth)
    if error:
        raise ValueError("BAOSTOCK_PG_RUNTIME_ACCEPTANCE_INVALID:" + error)
    return {"manifest": manifest, "smoke_receipt": receipt, "record": record,
            "source": "PG_ACCEPTED_DAILY_RUNTIME_FACT", "database_identity": identity,
            "schema": schema, "payload_sha256": row[1]}
