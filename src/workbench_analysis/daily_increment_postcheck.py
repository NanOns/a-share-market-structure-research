from __future__ import annotations

"""Independent reads of DM-01 candidate artifacts before a data-head promotion."""

import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from workbench_analysis.daily_data_head import CAPABILITIES, write_json_atomic
from workbench_analysis.daily_source_freeze import ensure_outside_tdx, source_freeze_complete_v2


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _date_string(value: object) -> str:
    raw = str(value or "")
    if raw.isdigit() and len(raw) == 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw[:10]


def _read_rows(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    name = path.name.lower()
    if name.endswith((".jsonl", ".jsonl.gz")):
        opener = gzip.open if name.endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream if line.strip()]
        return {}, rows
    if name.endswith(".json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return {}, payload
        if not isinstance(payload, dict):
            raise ValueError("COMPONENT_ARTIFACT_JSON_SHAPE_INVALID")
        rows = payload.get("rows", payload.get("data_rows"))
        if not isinstance(rows, list):
            raise ValueError("COMPONENT_ARTIFACT_ROWS_MISSING")
        return payload, rows
    if name.endswith(".csv"):
        with path.open("r", encoding="utf-8", newline="") as stream:
            return {}, list(csv.DictReader(stream))
    if name.endswith(".parquet"):
        import pyarrow.parquet as parquet

        table = parquet.read_table(path)
        return {}, table.to_pylist()
    raise ValueError("COMPONENT_ARTIFACT_FORMAT_UNSUPPORTED")


def _row_key(row: Mapping[str, Any]) -> tuple[str, str] | None:
    identity = str(row.get("security_id") or row.get("stable_security_id") or row.get("canonical_security_id") or "")
    if not identity and str(row.get("identity_status") or "").upper().startswith("IDENTITY_UNKNOWN"):
        identity = "SOURCE:" + str(row.get("source_security_key") or "").upper()
    day = _date_string(row.get("trade_date") or row.get("as_of_date") or row.get("period_end_date"))
    if not identity or not day:
        return None
    return identity, day


def independent_daily_increment_postcheck(
    *,
    trade_date: str,
    source_freeze: Mapping[str, Any],
    component_receipts: Mapping[str, Mapping[str, Any]],
    data_head_path: Path,
    stage_head_path: Path,
    dev_baseline_path: Path,
    expected_data_head_sha256: str,
    expected_stage_head_sha256: str,
    expected_dev_baseline_sha256: str,
    tdx_root: Path = Path("D:/new_tdx"),
) -> dict[str, Any]:
    """Read component bytes independently and verify cross-artifact session invariants."""
    checks: dict[str, str] = {}
    problems: list[str] = []

    def record(name: str, passed: bool, code: str) -> None:
        checks[name] = "PASS" if passed else "BLOCKED"
        if not passed:
            problems.append(code)

    record("source_freeze_v2_complete", source_freeze_complete_v2(source_freeze)
           and source_freeze.get("trade_date") == trade_date, "SOURCE_FREEZE_V2_NOT_COMPLETE")
    families = source_freeze.get("source_families", {})
    tdx_revision = str(families.get("TDX_FULL_PACKAGE", {}).get("source_revision") or "")
    delta_digest = str(families.get("TDX_PACKAGE_DELTA", {}).get("sha256") or "")
    record("tdx_source_lineage_present", bool(tdx_revision and delta_digest), "TDX_SOURCE_LINEAGE_MISSING")
    family_files_ok = True
    family_payloads: dict[str, dict[str, Any]] = {}
    for family, item in families.items():
        path_value = str(item.get("path") or "") if isinstance(item, Mapping) else ""
        if not path_value:
            family_files_ok = False
            problems.append("SOURCE_FAMILY_FILE_REF_MISSING:" + str(family))
            continue
        path = Path(path_value)
        try:
            ensure_outside_tdx(path, tdx_root)
            exists_and_size = path.is_file() and path.stat().st_size == int(item.get("bytes", -1))
            if family == "TDX_FULL_PACKAGE":
                source_revision = str(item.get("source_revision") or "")
                family_files_ok = family_files_ok and exists_and_size and path.name.lower() == "hsjday.zip"
                family_files_ok = family_files_ok and path.parent.name == source_revision
                family_files_ok = family_files_ok and source_revision.removeprefix("sha256-") == item.get("sha256")
            else:
                family_files_ok = family_files_ok and exists_and_size and _sha(path) == item.get("sha256")
            if family in {"TDX_PAGE_CAPTURE", "TDX_PACKAGE_DELTA"} and exists_and_size:
                family_payloads[family] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            family_files_ok = False
    record("source_family_files_independently_verified", family_files_ok,
           "SOURCE_FAMILY_FILE_INTEGRITY_INVALID")
    page_capture = family_payloads.get("TDX_PAGE_CAPTURE", {})
    package_delta = family_payloads.get("TDX_PACKAGE_DELTA", {})
    full_package_sha = str(families.get("TDX_FULL_PACKAGE", {}).get("sha256") or "")
    tdx_capture_binding_ok = (
        page_capture.get("target_date") == trade_date
        and page_capture.get("update_date") == trade_date
        and page_capture.get("snapshot_id") == tdx_revision
        and (page_capture.get("download") or {}).get("sha256") == full_package_sha
        and package_delta.get("target_date") == trade_date
        and package_delta.get("current_snapshot_id") == tdx_revision
        and package_delta.get("delta_sha256") == families.get("TDX_PACKAGE_DELTA", {}).get("source_revision")
    )
    record("official_tdx_capture_and_delta_bindings", tdx_capture_binding_ok,
           "OFFICIAL_TDX_CAPTURE_OR_DELTA_BINDING_INVALID")
    record("all_nine_component_receipts_present", set(component_receipts) == set(CAPABILITIES),
           "DAILY_COMPONENT_RECEIPTS_MISSING_OR_EXTRA")

    loaded: dict[str, list[dict[str, Any]]] = {}
    for capability in CAPABILITIES:
        receipt = component_receipts.get(capability)
        if not isinstance(receipt, Mapping):
            continue
        artifact = receipt.get("artifact")
        if not isinstance(artifact, Mapping) or not artifact.get("path") or not artifact.get("sha256"):
            problems.append("COMPONENT_ARTIFACT_REF_MISSING:" + capability)
            continue
        path = Path(str(artifact["path"]))
        try:
            ensure_outside_tdx(path, tdx_root)
            if not path.is_file() or _sha(path) != artifact.get("sha256"):
                raise ValueError("COMPONENT_ARTIFACT_DIGEST_MISMATCH")
            payload, rows = _read_rows(path)
        except (OSError, ValueError, ImportError) as exc:
            problems.append(f"COMPONENT_ARTIFACT_READ_FAILED:{capability}:{str(exc)[:80]}")
            continue
        loaded[capability] = rows
        target_dates = {
            day for row in rows
            for value in (row.get("trade_date"), row.get("as_of_date"), row.get("period_end_date"))
            if value is not None and (day := _date_string(value))
        }
        metadata_ok = (
            receipt.get("status") in {"FULL_PASS", "DEGRADED_PASS"}
            and bool(receipt.get("contract_id")) and bool(receipt.get("version"))
            and receipt.get("trade_date") == trade_date
            and isinstance(receipt.get("input_source_revisions"), Mapping)
            and "parent_artifact_revision" in receipt
            and isinstance(receipt.get("elapsed_ms"), (int, float))
            and receipt.get("elapsed_ms", -1) >= 0
            and "unknown_or_degraded_rows" in receipt
        )
        artifact_ok = (
            (not payload or payload.get("trade_date") == trade_date)
            and len(rows) == receipt.get("row_count")
            and (not target_dates or max(target_dates) <= trade_date)
            and all(_row_key(row) is not None for row in rows)
        )
        row_keys = [_row_key(row) for row in rows]
        record("unique_stable_id_date:" + capability,
               bool(row_keys) and len(row_keys) == len(set(row_keys)),
               "COMPONENT_DUPLICATE_STABLE_ID_DATE:" + capability)
        source_refs = receipt.get("input_source_revisions") or {}
        source_refs_ok = bool(source_refs) and all(name in families and families[name].get("source_revision") == rev
                                                  for name, rev in source_refs.items())
        record("component_receipt:" + capability, metadata_ok and artifact_ok and source_refs_ok,
               "COMPONENT_ARTIFACT_OR_RECEIPT_INVALID:" + capability)

    raw = loaded.get("RAW_DAILY", [])
    raw_keys = [_row_key(row) for row in raw]
    raw_identity_ok = bool(raw) and all(
        bool(row.get("security_id") or row.get("stable_security_id") or row.get("canonical_security_id"))
        or (str(row.get("identity_status") or "").upper().startswith("IDENTITY_UNKNOWN")
            and bool(row.get("source_security_key")))
        for row in raw
    )
    record("raw_identity_or_isolated_unknown_date_key", raw_identity_ok
           and all(key is not None for key in raw_keys) and len(raw_keys) == len(set(raw_keys)),
           "RAW_DAILY_DUPLICATE_OR_EMPTY_KEYS")
    raw_rows_ok = bool(raw) and all(
        row.get("source_authority") == "TDX_OFFICIAL_PACKAGE"
        and row.get("source_snapshot_id") == tdx_revision
        and row.get("bao_stock_ohlc_substitution_permitted") is False
        and str(row.get("source_authority") or "").upper() != "BAOSTOCK"
        for row in raw
    )
    record("tdx_authority_and_no_baostock_raw_substitution", raw_rows_ok,
           "RAW_DAILY_AUTHORITY_OR_BAOSTOCK_SUBSTITUTION_INVALID")

    status_rows = {_row_key(row): row for row in loaded.get("TRADING_STATUS", [])}
    status_relation_ok = bool(status_rows) and all(
        key in status_rows
        and (status_rows[key].get("actual_bar_present") is True or status_rows[key].get("tdx_bar_present") is True)
        for key in raw_keys
    )
    record("trading_status_covers_raw_bars", status_relation_ok, "TRADING_STATUS_BAR_RELATION_INVALID")
    universe_keys = {_row_key(row) for row in loaded.get("IDENTITY_UNIVERSE", [])}
    record("raw_within_target_identity_universe", bool(universe_keys) and set(raw_keys).issubset(universe_keys),
           "RAW_DAILY_OUTSIDE_TARGET_IDENTITY_UNIVERSE")
    for capability in ("PRICE_LIMIT", "SPECIAL_PHASE"):
        rows = loaded.get(capability, [])
        row_keys = {_row_key(row) for row in rows}
        record("target_keyset:" + capability, bool(row_keys) and row_keys == universe_keys,
               "TARGET_KEYSET_MISMATCH:" + capability)
    for capability in ("ADJUSTED_DAILY", "PERIOD_RAW", "PERIOD_ADJUSTED"):
        rows = loaded.get(capability, [])
        cutoff_ok = bool(rows) and all(
            _date_string(row.get("trade_date") or row.get("as_of_date") or row.get("period_end_date")) <= trade_date
            for row in rows
        )
        record("target_cutoff:" + capability, cutoff_ok, "TARGET_CUTOFF_INVALID:" + capability)
    adjusted_rows = loaded.get("ADJUSTED_DAILY", [])
    accepted_adjustment_states = {"READY", "FULL_PASS", "DEGRADED_PASS", "UNKNOWN", "NOT_APPLICABLE"}
    adjusted_readiness_ok = bool(adjusted_rows) and all(
        str(row.get("adjustment_readiness") or row.get("adjustment_status") or "") in accepted_adjustment_states
        for row in adjusted_rows
    )
    record("adjusted_readiness_explicit", adjusted_readiness_ok,
           "ADJUSTED_DAILY_READINESS_MISSING_OR_INVALID")

    try:
        data_hash = _sha(data_head_path)
        stage_hash = _sha(stage_head_path)
        dev_hash = _sha(dev_baseline_path)
    except OSError:
        data_hash = stage_hash = dev_hash = ""
    record("data_head_unchanged_before_promotion", data_hash == expected_data_head_sha256,
           "DATA_HEAD_CHANGED_BEFORE_PROMOTION")
    record("stage_head_unchanged", stage_hash == expected_stage_head_sha256, "STAGE_HEAD_CHANGED")
    record("dev_baseline_unchanged", dev_hash == expected_dev_baseline_sha256, "DEV_BASELINE_HEAD_CHANGED")
    status = "PASS" if checks and all(value == "PASS" for value in checks.values()) and not problems else "BLOCKED"
    return {
        "contract_id": "V4_DM01_INDEPENDENT_DAILY_ARTIFACT_POSTCHECK_V1",
        "version": "1.0.0",
        "status": status,
        "trade_date": trade_date,
        "checks": checks,
        "artifact_row_counts": {key: len(value) for key, value in loaded.items()},
        "stage_head_sha256": stage_hash,
        "dev_baseline_sha256": dev_hash,
        "data_head_sha256": data_hash,
        "problems": problems,
        "data_head_promotion_permitted": status == "PASS",
        "tdx_root_write_count": 0,
    }


def make_independent_postcheck_callback(
    *,
    staging_root: Path,
    report_root: Path,
    data_head_path: Path,
    stage_head_path: Path,
    dev_baseline_path: Path,
    source_freeze: Mapping[str, Any],
    tdx_root: Path = Path("D:/new_tdx"),
):
    """Return the callback expected by run_incremental_components; re-read staged files."""
    def postcheck(candidate: Mapping[str, Any]) -> str:
        manifest = candidate.get("manifest")
        head = candidate.get("head")
        if not isinstance(manifest, Mapping) or not isinstance(head, Mapping):
            return "BLOCKED"
        trade_date = str(manifest.get("trade_date") or "")
        candidate_path = staging_root / f"candidate_manifest_{trade_date.replace('-', '')}.json"
        try:
            on_disk = json.loads(candidate_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return "BLOCKED"
        if on_disk != manifest:
            return "BLOCKED"
        expected_data = str(head.get("parent_head_sha256") or "")
        expected_stage = str(head.get("stage_accepted_head_sha256") or "")
        expected_dev = str(head.get("dev_baseline_sha256") or "")
        result = independent_daily_increment_postcheck(
            trade_date=trade_date,
            source_freeze=source_freeze,
            component_receipts=manifest.get("components", {}),
            data_head_path=data_head_path,
            stage_head_path=stage_head_path,
            dev_baseline_path=dev_baseline_path,
            expected_data_head_sha256=expected_data,
            expected_stage_head_sha256=expected_stage,
            expected_dev_baseline_sha256=expected_dev,
            tdx_root=tdx_root,
        )
        result["candidate_manifest_path"] = str(candidate_path.resolve())
        result["candidate_manifest_sha256"] = _sha(candidate_path)
        result["candidate_head_parent_sha256"] = expected_data
        report_path = report_root / f"independent_daily_artifact_postcheck_{trade_date.replace('-', '')}.json"
        write_json_atomic(report_path, result, tdx_root=tdx_root)
        return str(result.get("status") or "BLOCKED")

    return postcheck
