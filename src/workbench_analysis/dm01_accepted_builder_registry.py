from __future__ import annotations

"""Static validation for the DM-01 accepted incremental builder registry."""

import ast
import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from workbench_analysis.daily_data_head import CAPABILITIES


REGISTRY_CONTRACT_ID = "V4_DM01_ACCEPTED_BUILDER_REGISTRY_V1"
REGISTRY_VERSION = "1.0.0"
REGISTRY_PATH = Path("config/v4_dm01_accepted_builder_registry_v1.json")
ADAPTER_MODULE = "workbench_analysis.dm01_incremental_component_builders"
EXPECTED_CALLABLES = {
    "RAW_DAILY": "build_raw_daily",
    "IDENTITY_UNIVERSE": "build_identity_universe",
    "TRADING_STATUS": "build_trading_status",
    "ISST": "build_isst",
    "ADJUSTED_DAILY": "build_adjusted_daily",
    "PERIOD_RAW": "build_period_raw",
    "PERIOD_ADJUSTED": "build_period_adjusted",
    "PRICE_LIMIT": "build_price_limit",
    "SPECIAL_PHASE": "build_special_phase",
}


def validate_incremental_registry(*, project_root: Path) -> dict[str, Any]:
    """R1 engineering exports; the immutable V1 missing-API assessment remains historical evidence."""
    root = project_root.resolve()
    contract_path = root / 'config/dm01_incremental_builders_contract_r1.json'
    errors = []
    try:
        contract = json.loads(contract_path.read_text(encoding='utf8'))
        from workbench_analysis.dm01_incremental_component_builders import BUILDERS
        if set(contract['capabilities']) != set(CAPABILITIES) or set(BUILDERS) != set(CAPABILITIES):
            errors.append('NINE_CAPABILITY_SET_MISMATCH')
        for cap, name in EXPECTED_CALLABLES.items():
            fn = BUILDERS.get(cap)
            if not callable(fn) or fn.__name__ != name or fn.__module__ != ADAPTER_MODULE:
                errors.append('STATIC_CALLABLE_MISMATCH:' + cap)
            if contract['capabilities'][cap]['builder_callable'] != name:
                errors.append('CONTRACT_EXPORT_MISMATCH:' + cap)
        for ref in contract['runtime_bindings']:
            if sha256_file(root / ref['path']) != ref['sha256']:
                errors.append('RUNTIME_DIGEST_MISMATCH:' + ref['path'])
        # Historical Data Head retains its publication-time Stage Head. A later engineering
        # promotion does not justify rebinding or mutating that Data Head.
        for ref in contract['stage_entry_protected_heads']:
            if sha256_file(root / ref['path']) != ref['sha256']:
                errors.append('STAGE_ENTRY_HEAD_CHANGED:' + ref['path'])
    except (OSError,KeyError,TypeError,ValueError) as exc:
        errors.append('INCREMENTAL_REGISTRY_UNREADABLE:' + type(exc).__name__)
    return dict(contract_id='DM01_A01_INCREMENTAL_REGISTRY_VALIDATION_R1',
        status='PASS_ENGINEERING_EXPORTS' if not errors else 'BLOCKED', errors=errors,
        registry_path='config/dm01_incremental_builders_contract_r1.json',
        callable_count=9 if not errors else 0, candidate_only=True,
        external_acceptance='PENDING', data_head_promotion_permitted=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    value = json.loads((root / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ACCEPTED_BUILDER_EVIDENCE_SHAPE_INVALID:" + relative)
    return value


def _top_level_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def validate_registry(
    *,
    project_root: Path,
    builders: Mapping[str, Callable[..., Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Verify the static nine-capability mapping and all accepted-stage bindings.

    The configuration is declarative only. Runtime resolution is deliberately
    checked against caller-supplied Python objects and a fixed callable allowlist;
    configuration text cannot import or discover an arbitrary function.
    """
    root = project_root.resolve()
    errors: list[str] = []
    runtime_api_blockers: list[dict[str, str]] = []
    path = root / REGISTRY_PATH
    try:
        registry_raw = path.read_bytes()
        registry = json.loads(registry_raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "contract_id": REGISTRY_CONTRACT_ID,
            "status": "BLOCKED_REGISTRY_UNREADABLE",
            "errors": [type(exc).__name__ + ":" + str(exc)[:160]],
            "production_builders_ready": False,
        }

    if registry.get("contract_id") != REGISTRY_CONTRACT_ID or registry.get("version") != REGISTRY_VERSION:
        errors.append("REGISTRY_CONTRACT_OR_VERSION_MISMATCH")
    if registry.get("runtime_adapter_module") != ADAPTER_MODULE:
        errors.append("RUNTIME_ADAPTER_MODULE_NOT_ALLOWLISTED")
    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, Mapping) or set(capabilities) != set(CAPABILITIES):
        errors.append("REGISTRY_CAPABILITY_SET_MISMATCH")
        capabilities = {}

    for capability, callable_name in EXPECTED_CALLABLES.items():
        item = capabilities.get(capability, {})
        if not isinstance(item, Mapping) or item.get("builder_callable") != callable_name:
            errors.append("REGISTRY_CALLABLE_BINDING_MISMATCH:" + capability)
            continue
        api = item.get("runtime_api_assessment")
        if not isinstance(api, Mapping):
            errors.append("RUNTIME_API_ASSESSMENT_MISSING:" + capability)
        elif api.get("target_date_artifact_builder_exported") is not True:
            runtime_api_blockers.append({
                "capability": capability,
                "status": str(api.get("status") or "UNKNOWN"),
                "reason": str(api.get("blocker") or "ACCEPTED_TARGET_DATE_BUILDER_API_UNAVAILABLE"),
            })
        accepted = item.get("accepted_source_receipt")
        if not isinstance(accepted, Mapping):
            errors.append("ACCEPTED_SOURCE_RECEIPT_REF_MISSING:" + capability)
        else:
            try:
                receipt = _read_json(root, str(accepted.get("path") or ""))
                actual_sha = sha256_file(root / str(accepted["path"]))
                if actual_sha != accepted.get("sha256"):
                    errors.append("ACCEPTED_SOURCE_RECEIPT_DIGEST_MISMATCH:" + capability)
                expected_status = str(accepted.get("status") or "")
                if expected_status == "EXTERNALLY_ACCEPTED":
                    status = receipt.get("acceptance_result", {}).get("external_acceptance")
                else:
                    status = receipt.get("status")
                if status != expected_status:
                    errors.append("ACCEPTED_SOURCE_RECEIPT_STATUS_MISMATCH:" + capability)
            except (OSError, KeyError, TypeError, ValueError):
                errors.append("ACCEPTED_SOURCE_RECEIPT_UNREADABLE:" + capability)

        runtimes = item.get("accepted_runtime")
        if not isinstance(runtimes, list) or not runtimes:
            errors.append("ACCEPTED_RUNTIME_BINDING_MISSING:" + capability)
            continue
        verified_exports: set[str] = set()
        for runtime in runtimes:
            if not isinstance(runtime, Mapping) or not runtime.get("path") or not runtime.get("sha256"):
                errors.append("ACCEPTED_RUNTIME_BINDING_INVALID:" + capability)
                continue
            runtime_path = root / str(runtime["path"])
            try:
                if sha256_file(runtime_path) != runtime.get("sha256"):
                    errors.append("ACCEPTED_RUNTIME_DIGEST_MISMATCH:" + capability + ":" + str(runtime["path"]))
                symbols = _top_level_symbols(runtime_path)
                declared = runtime.get("callables", [])
                if not isinstance(declared, list):
                    errors.append("ACCEPTED_RUNTIME_CALLABLE_LIST_INVALID:" + capability)
                else:
                    absent = [str(name) for name in declared if str(name) not in symbols]
                    if absent:
                        errors.append("ACCEPTED_RUNTIME_CALLABLE_SYMBOL_MISSING:" + capability + ":" + ",".join(absent))
                    verified_exports.update(str(name) for name in declared if str(name) in symbols)
            except (OSError, SyntaxError, UnicodeError):
                errors.append("ACCEPTED_RUNTIME_MISSING:" + capability + ":" + str(runtime["path"]))
        api = item.get("runtime_api_assessment")
        if isinstance(api, Mapping):
            required_exports = api.get("verified_exports", [])
            if not isinstance(required_exports, list):
                errors.append("RUNTIME_API_VERIFIED_EXPORTS_INVALID:" + capability)
            else:
                absent = [str(name) for name in required_exports if str(name) not in verified_exports]
                if absent:
                    errors.append("RUNTIME_API_EXPORT_NOT_PINNED:" + capability + ":" + ",".join(absent))

    bindings = registry.get("stage_acceptance_bindings", {})
    for stage, refs in bindings.items() if isinstance(bindings, Mapping) else ():
        if not isinstance(refs, Mapping):
            errors.append("STAGE_ACCEPTANCE_BINDING_INVALID:" + str(stage))
            continue
        for path_key, digest_key in (("receipt_path", "receipt_sha256"), ("postcheck_path", "postcheck_sha256"),
                                     ("accepted_head_path", "accepted_head_sha256"),
                                     ("final_receipt_path", "final_receipt_sha256"),
                                     ("external_acceptance_path", "external_acceptance_sha256"),
                                     ("cross_stage_postcheck_path", "cross_stage_postcheck_sha256")):
            relative = refs.get(path_key)
            expected = refs.get(digest_key)
            if relative is None and expected is None:
                continue
            try:
                if not relative or sha256_file(root / str(relative)) != expected:
                    errors.append("STAGE_ACCEPTANCE_BINDING_DIGEST_MISMATCH:" + str(stage) + ":" + path_key)
            except OSError:
                errors.append("STAGE_ACCEPTANCE_BINDING_MISSING:" + str(stage) + ":" + path_key)

    try:
        v402_head = _read_json(root, "data/v4/V4_02_ACCEPTED_HEAD.json")
        v402_receipt = _read_json(root, "reports/v4_02/V4_02_FINAL_RECEIPT_R6.json")
        v402_external = _read_json(root, "reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json")
        cross_stage = _read_json(root, "reports/v4_02/V4_02_R8_CROSS_STAGE_POSTCHECK_20260928.json")
        if (v402_head.get("status") != "PASS_WITH_BSE_SCOPE_DEGRADED"
                or v402_head.get("external_acceptance") != "EXTERNALLY_ACCEPTED"):
            errors.append("V4_02_ACCEPTED_HEAD_NOT_EXTERNAL_PASS")
        if v402_receipt.get("status") != "PASS_WITH_BSE_SCOPE_DEGRADED":
            errors.append("V4_02_FINAL_RECEIPT_NOT_PASS")
        if v402_external.get("acceptance_result", {}).get("external_acceptance") != "EXTERNALLY_ACCEPTED":
            errors.append("V4_02_EXTERNAL_ACCEPTANCE_NOT_PASS")
        if cross_stage.get("status") != "PASS":
            errors.append("V4_02_CROSS_STAGE_POSTCHECK_NOT_PASS")
    except (OSError, TypeError, ValueError):
        errors.append("V4_02_ACCEPTANCE_EVIDENCE_UNREADABLE")

    stage_path = root / "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
    data_path = root / "data/v4/V4_DATA_ACCEPTED_HEAD.json"
    dev_path = root / "data/v4/V4_DEV_BASELINE_HEAD.json"
    try:
        stage_head = json.loads(stage_path.read_text(encoding="utf-8"))
        data_head = json.loads(data_path.read_text(encoding="utf-8"))
        dev_head = json.loads(dev_path.read_text(encoding="utf-8"))
        if hashlib.sha256(stage_path.read_bytes()).hexdigest() != data_head.get("stage_accepted_head_sha256"):
            errors.append("DATA_HEAD_STAGE_HEAD_BINDING_MISMATCH")
        if data_head.get("accepted_trade_date") != "2026-09-24" or dev_head.get("accepted_data_cutoff") != "2026-09-24":
            errors.append("ACCEPTED_PARENT_CUTOFF_CHANGED")
        if stage_head.get("bindings", {}).get("v4_01_r8_1", {}).get("sha256") != bindings.get("v4_01_baseline", {}).get("receipt_sha256"):
            errors.append("STAGE_HEAD_V4_01_R8_1_BINDING_CHANGED")
        if stage_head.get("bindings", {}).get("v4_02_accepted_head", {}).get("sha256") != bindings.get("v4_02_baseline", {}).get("accepted_head_sha256"):
            errors.append("STAGE_HEAD_V4_02_BINDING_CHANGED")
        if any(item.get("cutoff") != "2026-09-24" for item in data_head.get("component_permissions", {}).values()):
            errors.append("DATA_HEAD_COMPONENT_CUTOFF_CHANGED")
    except (OSError, TypeError, ValueError):
        errors.append("ACCEPTED_HEAD_POINTER_UNREADABLE")

    adapter_relative = Path("src") / Path(*ADAPTER_MODULE.split("."))
    adapter_path = root / adapter_relative.with_suffix(".py")
    adapter_module_exists = adapter_path.is_file()

    if builders is None:
        wired = set()
        missing_builders = list(CAPABILITIES)
    else:
        wired = set()
        for capability, expected_name in EXPECTED_CALLABLES.items():
            builder = builders.get(capability)
            if (callable(builder)
                    and getattr(builder, "__name__", None) == expected_name
                    and getattr(builder, "__module__", None) == ADAPTER_MODULE):
                wired.add(capability)
            else:
                errors.append("PRODUCTION_BUILDER_CALLABLE_NOT_BOUND:" + capability)
        missing_builders = [capability for capability in CAPABILITIES if capability not in wired]

    integrity_status = "PASS" if not errors else "BLOCKED"
    production_ready = integrity_status == "PASS" and adapter_module_exists and len(wired) == len(CAPABILITIES)
    if not adapter_module_exists:
        missing_builders = list(CAPABILITIES)
    return {
        "contract_id": REGISTRY_CONTRACT_ID,
        "version": REGISTRY_VERSION,
        "status": "ACCEPTED_BUILDER_REGISTRY_READY" if production_ready else
                  "BLOCKED_REAL_ACCEPTED_BUILDERS_UNAVAILABLE" if integrity_status == "PASS" else "BLOCKED_REGISTRY_BINDING_INVALID",
        "registry_integrity_status": integrity_status,
        "registry_path": REGISTRY_PATH.as_posix(),
        "registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
        "capability_count": len(capabilities),
        "capabilities": list(CAPABILITIES),
        "bound_builder_count": len(wired),
        "missing_builders": missing_builders,
        "runtime_adapter_module": ADAPTER_MODULE,
        "runtime_adapter_module_exists": adapter_module_exists,
        "runtime_api_blockers": runtime_api_blockers,
        "production_builders_ready": production_ready,
        "errors": errors,
        "known_governance_debt": "KNOWN_STAGE_HEAD_GOVERNANCE_DEBT_V4_01_R8_3_NOT_REOPENED",
        "stage_head_mutated": False,
        "data_head_mutated": False,
        "dev_baseline_mutated": False,
    }
