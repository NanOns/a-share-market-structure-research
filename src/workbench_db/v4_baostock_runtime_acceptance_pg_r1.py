"""Append-only PG authority for date-bound BaoStock runtime acceptance.

The local smoke files are accepted only as an explicit ingress input. Runtime
consumers resolve the exact trade-date fact from PG and never follow a local
manifest or descriptor locator.
"""
from __future__ import annotations

import hashlib
import base64
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
    if not isinstance(value, dict):
        raise ValueError("PG_DATABASE_IDENTITY_CONFIGURATION_INVALID")
    return value


def _record(day: str, manifest: Mapping[str, Any], receipt_raw: bytes,
            zero_change_evidence: Mapping[str, Any] | None = None,
            native_response: Mapping[str, Any] | None = None) -> dict[str, Any]:
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
    if manifest.get("contract_id") == "OPERATIONAL_BAOSTOCK_RUNTIME_ZERO_CHANGE_V2":
        _validate_zero_change_evidence(manifest, zero_change_evidence)
    _validate_native_response(day, receipt, native_response)
    record = {
        "contract_id": CONTRACT,
        "contract_version": "1.0.0",
        "trade_date": day,
        "manifest": dict(manifest),
        "smoke_receipt": receipt,
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "smoke_receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
    }
    if zero_change_evidence is not None:
        record["zero_change_evidence"] = dict(zero_change_evidence)
    record["native_response"] = dict(native_response)
    return record


def _validate_native_response(day: str, receipt: Mapping[str, Any],
                              native_response: Mapping[str, Any] | None) -> None:
    if not isinstance(native_response, Mapping):
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_REQUIRED")
    binding = native_response.get("source_binding")
    payload = native_response.get("payload")
    raw_b64 = native_response.get("raw_b64")
    raw_sha = native_response.get("source_sha256")
    receipt_native = receipt.get("native_response")
    if (not isinstance(binding, Mapping) or not isinstance(payload, Mapping)
            or not isinstance(raw_b64, str) or not isinstance(raw_sha, str)
            or not isinstance(receipt_native, Mapping)
            or binding.get("sha256") != raw_sha
            or receipt_native.get("sha256") != raw_sha
            or receipt_native.get("path") != binding.get("path")
            or payload.get("target_date") != day
            or payload.get("observed_at") != receipt.get("observed_at")):
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_BINDING_INVALID")
    try:
        raw = base64.b64decode(raw_b64, validate=True)
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_ENCODING_INVALID") from exc
    if (hashlib.sha256(raw).hexdigest() != raw_sha or parsed != dict(payload)
            or len(raw) != binding.get("bytes")):
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_DIGEST_MISMATCH")


def _zero_change_evidence(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    from workbench_analysis.r43_owner_replay import checked
    proof_ref = manifest["live_smoke"]["adjustment_factor"]["no_change_proof"]
    proof = json.loads(checked(root, proof_ref).read_bytes())
    responses = []
    for binding in proof.get("responses", []):
        payload = json.loads(checked(root, binding).read_bytes())
        responses.append({"source_binding": dict(binding), "payload": payload})
    return {"proof_binding": dict(proof_ref), "proof": proof, "responses": responses}


def _validate_zero_change_evidence(manifest: Mapping[str, Any], evidence: Mapping[str, Any] | None) -> None:
    if not isinstance(evidence, Mapping):
        raise ValueError("BAOSTOCK_PG_ZERO_CHANGE_EVIDENCE_REQUIRED")
    smoke = manifest["live_smoke"]
    proof_ref = smoke["adjustment_factor"].get("no_change_proof")
    proof = evidence.get("proof")
    if (evidence.get("proof_binding") != proof_ref or not isinstance(proof, Mapping)
            or proof.get("acceptance") != "VERIFIED_ALL_TARGET_UNIVERSE_NO_CHANGE"
            or proof.get("target_session") != smoke.get("target_date")):
        raise ValueError("BAOSTOCK_PG_ZERO_CHANGE_PROOF_BINDING_INVALID")
    universe = proof.get("target_universe_codes")
    queried = proof.get("queried_codes")
    source_responses = proof.get("responses")
    accepted = evidence.get("responses")
    if (not isinstance(universe, list) or not universe or not all(isinstance(code, str) for code in universe)
            or not isinstance(queried, list) or not all(isinstance(code, str) for code in queried)
            or set(universe) != set(queried)
            or not isinstance(source_responses, list) or not isinstance(accepted, list)
            or len(source_responses) != len(accepted)):
        raise ValueError("BAOSTOCK_PG_ZERO_CHANGE_COVERAGE_INVALID")
    response_codes = []
    runtime = manifest.get("runtime", {})
    target = smoke["target_date"]
    for binding, item in zip(source_responses, accepted, strict=True):
        if not isinstance(item, Mapping) or item.get("source_binding") != binding:
            raise ValueError("BAOSTOCK_PG_ZERO_CHANGE_RESPONSE_BINDING_INVALID")
        payload = item.get("payload")
        if not isinstance(payload, Mapping) or not isinstance(payload.get("metadata"), Mapping) or not isinstance(payload.get("sdk"), Mapping):
            raise ValueError("BAOSTOCK_PG_ZERO_CHANGE_RESPONSE_PAYLOAD_INVALID")
        code = payload.get("code")
        if (not isinstance(code, str) or payload.get("rows")
                or payload.get("params") != {"code": code, "start_date": target, "end_date": target}
                or payload.get("metadata", {}).get("error_code") != "0"
                or any(payload.get("sdk", {}).get(k) != runtime.get(k)
                       for k in ("package", "version", "installed_python_sources_sha256"))):
            raise ValueError("BAOSTOCK_PG_ZERO_CHANGE_RESPONSE_INVALID")
        response_codes.append(code)
    if len(response_codes) != len(set(response_codes)) or set(response_codes) != set(universe):
        raise ValueError("BAOSTOCK_PG_ZERO_CHANGE_UNIVERSE_COVERAGE_INVALID")


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
    evidence = None
    if manifest.get("contract_id") == "OPERATIONAL_BAOSTOCK_RUNTIME_ZERO_CHANGE_V2":
        evidence = _zero_change_evidence(root, manifest)
    receipt_raw = receipt_path.read_bytes()
    # Keep the exact receipt bytes in the immutable source-ingress ledger so
    # PG readers can verify the raw-byte digest without reopening workspace
    # files. The manifest's SHA is already checked by the loader.
    from .v4_historical_source_ingress_pg_r1 import ingress_path
    ingress_path(root, receipt_ref["path"], expected_sha256=receipt_ref["sha256"])
    receipt = json.loads(receipt_raw.decode("utf-8"))
    native_ref = receipt.get("native_response")
    if not isinstance(native_ref, Mapping):
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_RECEIPT_REQUIRED")
    native_path = (root / str(native_ref.get("path") or "")).resolve()
    try:
        native_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_PATH_ESCAPE") from exc
    from common.paths import resolve_tdx_root
    from workbench_analysis.daily_source_freeze import ensure_outside_tdx
    ensure_outside_tdx(native_path, resolve_tdx_root(root))
    raw_native = native_path.read_bytes()
    native_sha = hashlib.sha256(raw_native).hexdigest()
    if native_sha != native_ref.get("sha256"):
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_SOURCE_DIGEST_MISMATCH")
    native_payload = json.loads(raw_native.decode("utf-8"))
    native_binding = {"path": native_path.relative_to(root).as_posix(), "sha256": native_sha,
                      "bytes": len(raw_native)}
    native_record = {"source_binding": native_binding, "source_sha256": native_sha,
                     "payload": native_payload, "raw_b64": base64.b64encode(raw_native).decode("ascii")}
    record = _record(_key(day), manifest, receipt_raw, evidence, native_record)
    store = ForwardFactStore(root, FOLDER)
    binding = store.append(KIND, _key(day), record, migration_timeout_seconds=120)
    return {"contract_id": CONTRACT, "trade_date": _key(day), "binding": binding,
            "payload_sha256": digest(canonical(record))}


def load(root: Path, day: str, *, sdk: Mapping[str, Any], auth_mode: str | None = None) -> dict[str, Any]:
    """Read and validate one exact date from PG under read-only RR isolation."""
    root = Path(root).resolve()
    key = _key(day)
    schema = v4_native.workspace_schema(root / FOLDER, "forward")
    workspace_namespace=ForwardFactStore.namespace_for(root/FOLDER)
    with v4_native.connection(schema, read_only=True) as pg:
        relation = pg.execute("SELECT to_regclass('forward_facts')").fetchone()
        if not relation or relation[0] is None:
            raise ValueError("BAOSTOCK_PG_RUNTIME_ACCEPTANCE_NOT_FOUND")
        identity = ForwardFactStore._database_identity(pg)
        expected_identity=dict(_expected_identity())
        if expected_identity and identity != expected_identity:
            raise ValueError("BAOSTOCK_PG_RUNTIME_DATABASE_IDENTITY_MISMATCH")
        row = pg.execute(
            "SELECT payload,payload_sha256 FROM forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s",
            (workspace_namespace,KIND, key),
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
            or record.get("manifest", {}).get("smoke_receipt", {}).get("sha256")
                != record.get("smoke_receipt_sha256")):
        raise ValueError("BAOSTOCK_PG_RUNTIME_RECORD_BINDING_INVALID")
    manifest = record["manifest"]
    receipt = record["smoke_receipt"]
    receipt_binding = manifest.get("smoke_receipt", {})
    try:
        from .v4_historical_source_ingress_pg_r1 import read_bound
        receipt_source = read_bound(root, receipt_binding.get("path", ""),
                                    receipt_binding.get("sha256", ""))
    except ValueError as exc:
        raise ValueError("BAOSTOCK_PG_RUNTIME_SMOKE_RECEIPT_SOURCE_NOT_FOUND") from exc
    receipt_raw = receipt_source["raw"]
    if (hashlib.sha256(receipt_raw).hexdigest() != record.get("smoke_receipt_sha256")
            or json.loads(receipt_raw.decode("utf-8")) != receipt):
        raise ValueError("BAOSTOCK_PG_RUNTIME_SMOKE_RECEIPT_SOURCE_MISMATCH")
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
    if manifest.get("contract_id") == "OPERATIONAL_BAOSTOCK_RUNTIME_ZERO_CHANGE_V2":
        _validate_zero_change_evidence(manifest, record.get("zero_change_evidence"))
    _validate_native_response(key, receipt, record.get("native_response"))
    selected_auth = auth_mode or str(manifest.get("auth_mode", ""))
    error = _acceptance_error(manifest, sdk=sdk, auth_mode=selected_auth)
    if error:
        raise ValueError("BAOSTOCK_PG_RUNTIME_ACCEPTANCE_INVALID:" + error)
    return {"manifest": manifest, "smoke_receipt": receipt,
            "native_response": record["native_response"], "record": record,
            "source": "PG_ACCEPTED_DAILY_RUNTIME_FACT", "database_identity": identity,
            "schema": schema, "payload_sha256": row[1]}


def export_native_response(root: Path, bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Atomically materialize exact PG response bytes as a derived freeze input."""
    root = Path(root).resolve()
    if root.drive.upper() != "G:":
        raise ValueError("BAOSTOCK_PG_RUNTIME_G_ROOT_REQUIRED")
    native = bundle.get("native_response")
    if not isinstance(native, Mapping):
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_REQUIRED")
    try:
        raw = base64.b64decode(native.get("raw_b64", ""), validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_ENCODING_INVALID") from exc
    binding = native.get("source_binding")
    if (not isinstance(binding, Mapping) or hashlib.sha256(raw).hexdigest() != native.get("source_sha256")
            or native.get("source_sha256") != binding.get("sha256")
            or len(raw) != binding.get("bytes")):
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_DIGEST_MISMATCH")
    day = bundle.get("manifest", {}).get("live_smoke", {}).get("target_date")
    if not isinstance(day, str) or _key(day) != day:
        raise ValueError("BAOSTOCK_PG_NATIVE_RESPONSE_DATE_INVALID")
    from common.paths import resolve_tdx_root
    from workbench_analysis.daily_increment_builder import _atomic_bytes
    path = root / "data/v4/runtime_pg_ingress_cache/baostock" / day.replace("-", "") / "native_response.json"
    _atomic_bytes(path, raw, tdx_root=resolve_tdx_root(root))
    return {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "source": "PG_FACT_DERIVED_CACHE", "pg_payload_sha256": bundle.get("payload_sha256")}
