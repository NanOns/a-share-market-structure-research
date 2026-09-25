from __future__ import annotations

"""Verify V4-01 source inputs and build a deterministic source-priority manifest."""

import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from market_calendar.trading_calendar import read_day_dates  # noqa: E402
from tdx.day_reader import DAY_STRUCT, validate_day_file  # noqa: E402
from v4.contracts.source_overlap import compare_day_values, research_a_stock_ids, sessions_from_index_chains  # noqa: E402
from workbench_analysis.canonical_source_selection import (  # noqa: E402
    LOCAL_FAMILY, PACKAGE_FAMILY, select_records, selection_digest, selection_segments,
)
from workbench_analysis.source_bundle_identity import verify_source_bundle_identity  # noqa: E402
from workbench_analysis.tdx_local_snapshot import verify_local_snapshot  # noqa: E402
from workbench_analysis.tdx_snapshot import sha256_file, verify_zip_snapshot  # noqa: E402
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402


PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
BUNDLE_ID = "6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2"
LOCAL_SNAPSHOT_ID = "1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70"


def package_inventory(extracted_root: Path) -> tuple[dict[str, dict[str, str]], str, int, int]:
    inventory: dict[str, dict[str, str]] = {}
    digest = hashlib.sha256()
    expanded_bytes = 0
    for path in sorted(extracted_root.rglob("*.day"), key=lambda item: item.relative_to(extracted_root).as_posix().casefold()):
        relative = path.relative_to(extracted_root).as_posix()
        size = path.stat().st_size
        checksum = sha256_file(path)
        inventory[relative] = {"byte_count": str(size), "sha256": checksum}
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        digest.update(str(size).encode("ascii")); digest.update(b"\0")
        digest.update(checksum.encode("ascii")); digest.update(b"\n")
        expanded_bytes += size
    return inventory, digest.hexdigest(), expanded_bytes, len(inventory)


def index_source(root: Path, family: str, *, collect_errors: bool = True):
    indexed = {}
    errors = []
    for path in sorted(root.glob("*/lday/*.day"), key=lambda item: item.relative_to(root).as_posix().casefold()):
        relative = path.relative_to(root).as_posix()
        match = re.fullmatch(r"(sh|sz|bj)/lday/(sh|sz|bj)(\d{6})\.day", relative.lower())
        checksum = sha256_file(path)
        if not match or match.group(1) != match.group(2):
            errors.append({"source_family": family, "relative_path": relative,
                           "sha256": checksum, "reason": "INVALID_SOURCE_SECURITY_KEY"})
            continue
        market, _, code = match.groups()
        security_key = f"{market.upper()}.{code}"
        validation = validate_day_file(path, market)
        if not validation["valid"]:
            errors.append({"source_family": family, "relative_path": relative,
                           "source_security_key": security_key, "sha256": checksum,
                           "reason": "SOURCE_DAY_FILE_VALIDATION_FAILED", "errors": validation["errors"]})
            continue
        raw = path.read_bytes()
        records = {}
        previous = None
        for values in DAY_STRUCT.iter_unpack(raw):
            day = int(values[0])
            if previous is not None and day <= previous:
                raise ValueError("VALIDATOR_AND_SOURCE_READER_DATE_ORDER_DISAGREE")
            previous = day
            records[day] = raw[(len(records) * DAY_STRUCT.size):((len(records) + 1) * DAY_STRUCT.size)]
        indexed[security_key] = {
            "records": records,
            "revision": checksum,
            "path": relative,
            "record_count": len(records),
            "first_date": min(records, default=None),
            "last_date": max(records, default=None),
            "mtime_ns": path.stat().st_mtime_ns,
        }
    return indexed, errors


def values_for_00d(raw: bytes) -> tuple[float | int, ...]:
    _day, open_, high, low, close, amount, volume, _reserved = DAY_STRUCT.unpack(raw)
    return (open_, high, low, close, float(amount), int(volume))


def main() -> int:
    bundle_path = ROOT / "data/source_bundles" / BUNDLE_ID / "source_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_identity = verify_source_bundle_identity(bundle, BUNDLE_ID)
    if bundle["package"]["sha256"] != PACKAGE_SHA:
        raise SystemExit("SOURCE_PACKAGE_ID_MISMATCH")
    package_path = ROOT / bundle["package"]["staged_path"]
    extracted_root = ROOT / bundle["extraction"]["root"]
    local_root = ROOT / "data/v4/local_tdx_snapshots" / LOCAL_SNAPSHOT_ID
    if sha256_file(package_path) != PACKAGE_SHA:
        raise SystemExit("SOURCE_PACKAGE_HASH_MISMATCH")
    stage_manifest_path = ROOT / "reports/v4_01/v4_01_source_manifest_R4_20260925.json"
    stage_manifest = json.loads(stage_manifest_path.read_text(encoding="utf-8"))
    if stage_manifest.get("source_bundle_identity", {}).get("source_bundle_id") != BUNDLE_ID:
        raise SystemExit("V4_01_BASE_STAGE_RECEIPT_MISSING_VERIFIED_BUNDLE")

    inventory, extraction_digest, expanded_bytes, zip_count = package_inventory(extracted_root)
    with zipfile.ZipFile(package_path) as archive:
        zip_infos = [info for info in archive.infolist() if not info.is_dir()]
        zip_mtime_by_security = {}
        for info in zip_infos:
            match = re.search(r"(?:^|/)(sh|sz|bj)/lday/((?:sh|sz|bj)\d{6})\.day$", info.filename.replace("\\", "/").lower())
            if match:
                market, stem = match.groups()
                zip_mtime_by_security[f"{market.upper()}.{stem[2:]}"] = date(*info.date_time[:3]).isoformat()
    if zip_count != int(bundle["extraction"]["entry_count"]):
        raise SystemExit("EXTRACTION_FILE_COUNT_MISMATCH")
    zip_verification = verify_zip_snapshot(
        package_path, extracted_root, inventory, zip_count, extraction_digest
    )
    prior_manifest = json.loads((ROOT / "reports/v4_01/v4_01_source_manifest_R2_20260925.json").read_text(encoding="utf-8"))
    if prior_manifest.get("source", {}).get("extracted_content_digest") != extraction_digest:
        raise SystemExit("EXTRACTION_CONTENT_DIGEST_DIFFERS_FROM_PRIOR_ACCEPTED_SNAPSHOT")
    local_evidence = verify_local_snapshot(ROOT / "data/v4/local_tdx_snapshots", LOCAL_SNAPSHOT_ID)
    local_manifest_sha = sha256_file(Path(local_evidence["manifest_path"]))

    package_sources, package_errors = index_source(extracted_root, PACKAGE_FAMILY)
    local_sources, local_errors = index_source(local_root, LOCAL_FAMILY)
    keys = sorted(set(package_sources) | set(local_sources))
    source_segments = []
    totals = Counter()
    per_security = []
    integration = Counter()
    integration_digest = hashlib.sha256()
    integration_samples = []

    metadata_root = ROOT / bundle["metadata"]["root"]
    a_stock_ids = research_a_stock_ids(metadata_root)
    session_list = sessions_from_index_chains(extracted_root, 60)
    session_set = set(session_list)
    archive_day = ROOT / "reports/v4_00d/v4_00d_asset_stratified_postcheck_20260925.json"
    overlap_report = json.loads(archive_day.read_text(encoding="utf-8"))
    expected_refresh = int(overlap_report["asset_types"]["A_STOCK"]["source_refresh_volume_revision_rows"])
    if overlap_report.get("asset_types", {}).get("A_STOCK", {}).get("acceptance") != "ACCEPTED_SOURCE_PACKAGE":
        raise SystemExit("V4_00D_A_STOCK_SOURCE_ACCEPTANCE_NOT_PASS")

    for index, security_key in enumerate(keys, start=1):
        psource, lsource = package_sources.get(security_key), local_sources.get(security_key)
        package_records = psource["records"] if psource else {}
        local_records = lsource["records"] if lsource else {}
        selected, counts = select_records(
            security_key, package_records, local_records,
            package_revision=psource["revision"] if psource else PACKAGE_SHA,
            local_revision=lsource["revision"] if lsource else LOCAL_SNAPSHOT_ID,
        )
        segments = selection_segments(selected, security_key)
        source_segments.extend(segments)
        totals.update(counts)
        totals["selected_rows"] += len(selected)
        totals["security_keys"] += 1
        totals["package_source_files"] += int(psource is not None)
        totals["local_source_files"] += int(lsource is not None)
        totals["security_keys_with_both_sources"] += int(psource is not None and lsource is not None)
        per_security.append({
            "source_security_key": security_key,
            "canonical_security_id": None,
            "identity_quality": "UNKNOWN_UNMAPPED",
            "package_file_sha256": psource["revision"] if psource else None,
            "local_file_sha256": lsource["revision"] if lsource else None,
            "package_record_count": psource["record_count"] if psource else 0,
            "local_record_count": lsource["record_count"] if lsource else 0,
            "selected_record_count": len(selected),
            "selected_segment_count": len(segments),
            "selection_counts": counts,
        })

        # Re-run the accepted 00D source-refresh revision rows through the new
        # selection rule using the same identity/session/eligibility conditions.
        if psource and lsource and security_key in a_stock_ids:
            p_last, l_last = psource["last_date"] or 0, lsource["last_date"] or 0
            p_zip_day = zip_mtime_by_security.get(security_key)
            l_mtime_day = datetime.fromtimestamp(lsource["mtime_ns"] / 1_000_000_000, timezone.utc).date().isoformat()
            for day in sorted(set(package_records) & set(local_records) & session_set):
                source_refresh_eligible = (
                    p_last > l_last and p_zip_day is not None
                    and p_zip_day >= date(int(str(p_last)[:4]), int(str(p_last)[4:6]), int(str(p_last)[6:])).isoformat()
                    and p_zip_day > l_mtime_day
                )
                comparison, reason, _fields = compare_day_values(
                    values_for_00d(package_records[day]), values_for_00d(local_records[day]),
                    source_refresh_eligible=source_refresh_eligible,
                )
                if reason == "TOLERATED_SOURCE_REFRESH_VOLUME_REVISION":
                    picked = next(item for item in selected if item.trade_date == day)
                    integration["source_refresh_volume_revision_rows"] += 1
                    integration["local_priority_rows"] += int(picked.source_family == LOCAL_FAMILY)
                    delta = abs(int(values_for_00d(package_records[day])[-1]) - int(values_for_00d(local_records[day])[-1]))
                    integration["max_volume_abs_delta"] = max(integration["max_volume_abs_delta"], delta)
                    identity = f"{security_key}\0{day}\0{delta}\n"
                    integration_digest.update(identity.encode("ascii"))
                    if len(integration_samples) < 20:
                        integration_samples.append({"source_security_key": security_key, "trade_date": day,
                                                    "volume_abs_delta": delta,
                                                    "selected_source_family": picked.source_family,
                                                    "selection_reason": picked.selection_reason})
        if index % 1000 == 0:
            print(json.dumps({"progress": index, "security_keys": len(keys), "segments": len(source_segments)}), flush=True)

    selection_hash = selection_digest(source_segments)
    current_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    execution_identity = {
        "input_commit": current_commit,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "selection_module_sha256": sha256_file(ROOT / "src/workbench_analysis/canonical_source_selection.py"),
        "source_bundle_verifier_sha256": sha256_file(ROOT / "src/workbench_analysis/source_bundle_identity.py"),
        "zip_verifier_sha256": sha256_file(ROOT / "src/workbench_analysis/tdx_snapshot.py"),
        "stage_manifest_sha256": sha256_file(stage_manifest_path),
        "bootstrap_contract_sha256": sha256_file(ROOT / "config/v4_01_bootstrap_contract_v1.json"),
        "overlap_report_sha256": sha256_file(archive_day),
        "local_snapshot_manifest_sha256": local_manifest_sha,
    }
    manifest = {
        "contract_id": "CANONICAL_SOURCE_SELECTION_V1",
        "version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_bundle_identity": bundle_identity,
        "package_revision": PACKAGE_SHA,
        "local_snapshot_id": LOCAL_SNAPSHOT_ID,
        "identity_policy": "SOURCE_SECURITY_KEY_IS_NOT_CANONICAL_SECURITY_ID; unresolved identity remains null",
        "selection_policy": {"overlap": "LOCAL_ACCEPTED_TDX_CURRENT_CHAIN_WINS",
                              "local_gap": "COMPLETE_TDX_PACKAGE_FILLS_GAP",
                              "source_rows_not_present_in_either": "NOT_SYNTHESIZED"},
        "source_inventory": {"package_zip_extraction": zip_verification,
                              "package_inventory_count": zip_count,
                              "package_expanded_bytes": expanded_bytes,
                              "package_content_digest": extraction_digest,
                              "local_snapshot": local_evidence,
                              "local_snapshot_manifest_sha256": local_manifest_sha},
        "totals": dict(totals),
        "selection_digest": selection_hash,
        "segments": source_segments,
        "source_exceptions": package_errors + local_errors,
        "execution_identity": execution_identity,
    }
    manifest_path = ROOT / "reports/v4_01/canonical_source_selection_R4_20260925.json"
    _atomic_json(manifest_path, manifest)
    manifest_sha = sha256_file(manifest_path)
    expected_refresh_matched = integration.get("source_refresh_volume_revision_rows", 0) == expected_refresh
    integration_pass = expected_refresh_matched and integration.get("local_priority_rows", 0) == expected_refresh
    blocked = ["CANONICAL_IDENTITY_MAPPING_PENDING", "HISTORICAL_LIFECYCLE_AND_EVALUABLE_UNIVERSE_PENDING",
               "ADJUSTED_CANONICAL_EMPIRICAL_ACCEPTANCE_PENDING", "AS_RECORDED_HISTORY_POLICY_PENDING"]
    if package_errors or local_errors:
        blocked.append("INVALID_OR_UNIDENTIFIED_SOURCE_FILES_RETAINED_AND_EXCLUDED_FROM_SELECTION")
    receipt = {
        "stage": "V4-01-SOURCE-SELECTION-R4",
        "stage_contract": "V4.2.2 REV2 §§3B.1-3B.6; CANONICAL_SOURCE_SELECTION_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "SOURCE_SELECTION_BUILT_ACCEPTANCE_PENDING" if integration_pass else "SOURCE_SELECTION_INTEGRATION_BLOCKED",
        "stage_completion_authorized": False,
        "source_selection_manifest": manifest_path.relative_to(ROOT).as_posix(),
        "source_selection_manifest_sha256": manifest_sha,
        "selection_digest": selection_hash,
        "zip_extraction_verification": zip_verification,
        "source_bundle_identity": bundle_identity,
        "totals": dict(totals),
        "00d_integration": {
            "source_overlap_report": archive_day.relative_to(ROOT).as_posix(),
            "expected_source_refresh_volume_rows": expected_refresh,
            "recomputed_source_refresh_volume_rows": integration.get("source_refresh_volume_revision_rows", 0),
            "rows_selected_from_local": integration.get("local_priority_rows", 0),
            "max_volume_abs_delta": integration.get("max_volume_abs_delta", 0),
            "integration_digest": integration_digest.hexdigest(),
            "samples": integration_samples,
            "status": "PASS" if integration_pass else "BLOCKED",
        },
        "source_exceptions": {"package": len(package_errors), "local": len(local_errors),
                              "package_samples": package_errors[:25], "local_samples": local_errors[:25]},
        "execution_identity": execution_identity,
        "blocked_scopes": blocked,
        "next_stage": "V4_01_CANONICAL_IDENTITY_LIFECYCLE_AND_RECONSTRUCTED_UNIVERSE",
        "acceptance": "Source selection precedence is mechanically applied and bound to package/local hashes. This receipt does not accept canonical identity, lifecycle/PIT universe, adjusted history, or V4-01 completion.",
    }
    receipt_path = ROOT / "reports/v4_01/v4_01_source_selection_receipt_R4_20260925.json"
    _atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "security_keys": len(keys),
                      "selection_segments": len(source_segments), "selected_rows": totals.get("selected_rows", 0),
                      "local_rows": totals.get("local_rows", 0), "package_rows": totals.get("package_rows", 0),
                      "00d_source_refresh": receipt["00d_integration"],
                      "source_exceptions": receipt["source_exceptions"]["package"],
                      "manifest_sha256": manifest_sha, "receipt": receipt_path.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0 if integration_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
