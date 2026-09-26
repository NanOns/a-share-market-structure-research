from __future__ import annotations

"""Build a source-selected RAW daily candidate under the V4-02 V2 contract.

This emits only a RAW daily candidate. It does not claim formal PIT, adjusted
prices, exchange-calendar periods, trading status, or V4-02 acceptance.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.canonical_source_selection import (  # noqa: E402
    LOCAL_FAMILY,
    PACKAGE_FAMILY,
    select_records,
    selection_digest,
    selection_segments,
)
from workbench_analysis.tdx_local_snapshot import verify_local_snapshot  # noqa: E402
from workbench_analysis.tdx_snapshot import verify_zip_snapshot  # noqa: E402

PACKAGE_SHA = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"
BUNDLE_ID = "6122afa9db83170f7b442d5ecc5c7c9287b9dd6b04c4d53729d55f71f7dd99d2"
LOCAL_SNAPSHOT_ID = "1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70"
DAY_DTYPE = np.dtype(
    [
        ("trade_date", "<u4"),
        ("open_raw", "<u4"),
        ("high_raw", "<u4"),
        ("low_raw", "<u4"),
        ("close_raw", "<u4"),
        ("amount_source", "<f4"),
        ("volume_source", "<u4"),
        ("reserved", "<u4"),
    ]
)
DAY_BYTES = 32
REQUIRED_BOARDS = {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}
SCHEMA = pa.schema(
    [
        ("canonical_security_id", pa.string()),
        ("source_security_key", pa.string()),
        ("board_scope", pa.string()),
        ("trade_date", pa.uint32()),
        ("open_price_raw", pa.uint32()),
        ("high_price_raw", pa.uint32()),
        ("low_price_raw", pa.uint32()),
        ("close_price_raw", pa.uint32()),
        ("price_scale", pa.uint16()),
        ("amount_source_native", pa.float32()),
        ("volume_source_native", pa.uint32()),
        ("reserved_raw", pa.uint32()),
        ("source_relative_path", pa.string()),
        ("source_file_sha256", pa.string()),
        ("source_record_ordinal", pa.uint32()),
        ("selected_source_family", pa.string()),
        ("selected_source_revision", pa.string()),
        ("selection_reason", pa.string()),
        ("alternative_source_family", pa.string()),
        ("alternative_source_revision", pa.string()),
        ("alternative_record_sha256", pa.string()),
        ("identity_quality", pa.string()),
        ("identity_source_revision_id", pa.string()),
        ("membership_basis", pa.string()),
        ("knowledge_lineage", pa.string()),
        ("adjustment_view", pa.string()),
        ("limit_status", pa.string()),
        ("record_quality", pa.string()),
    ]
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_file_records(path: Path) -> tuple[dict[int, bytes], dict[int, int]]:
    raw = path.read_bytes()
    if len(raw) % DAY_BYTES:
        raise ValueError(f"SOURCE_RECORD_SIZE_INVALID:{path}")
    records: dict[int, bytes] = {}
    ordinals: dict[int, int] = {}
    parsed = np.frombuffer(raw, dtype=DAY_DTYPE)
    for ordinal, row in enumerate(parsed):
        day = int(row["trade_date"])
        if day in records:
            raise ValueError(f"DUPLICATE_SOURCE_DATE:{path}:{day}")
        records[day] = raw[ordinal * DAY_BYTES : (ordinal + 1) * DAY_BYTES]
        ordinals[day] = ordinal
    return records, ordinals


def load_csv_inventory(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return {row["relative_path"]: row for row in csv.DictReader(stream)}


def load_membership_identity(path: Path, accepted_sha: str) -> dict[str, list[dict]]:
    if sha256_file(path) != accepted_sha:
        raise ValueError("R6_2_MEMBERSHIP_INTERVAL_HASH_MISMATCH")
    import gzip

    mapping: dict[str, list[dict]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            mapping.setdefault(row["source_security_key"], []).append(row)
    for source_key, rows in mapping.items():
        rows.sort(key=lambda row: row["normalized_effective_from"])
        for left, right in zip(rows, rows[1:]):
            if left["normalized_effective_to"] >= right["normalized_effective_from"]:
                raise ValueError(f"OVERLAPPING_ACCEPTED_IDENTITY_INTERVALS:{source_key}")
    return mapping


def load_accepted_board_map(path: Path) -> dict[str, str]:
    import gzip

    boards: dict[str, str] = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = row["source_security_key"]
            board = row["board_scope"]
            previous = boards.setdefault(key, board)
            if previous != board:
                raise ValueError(f"ACCEPTED_BOARD_SCOPE_CONFLICT:{key}")
    return boards


def date_identity(source_key: str, trade_date: int, intervals: dict[str, list[dict]]) -> tuple[str | None, str, str, str | None]:
    day = f"{trade_date:08d}"
    day = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    matches = [
        row
        for row in intervals.get(source_key, [])
        if row["normalized_effective_from"] <= day <= row["normalized_effective_to"]
    ]
    if len(matches) > 1:
        raise ValueError(f"AMBIGUOUS_DATE_IDENTITY:{source_key}:{day}")
    if not matches:
        return None, "UNKNOWN_OUTSIDE_R6_2_ROSTER_INTERVAL", "UNKNOWN_NOT_PIT", None
    row = matches[0]
    return row["security_id"], "R6_2_DATED_ROSTER_OBSERVED", "R6_2_NORMALIZED_INTERVAL", row["source_revision_id"]


def check_raw_quality(values: tuple) -> str:
    day, op, hi, lo, close, amount, volume, _reserved = values
    try:
        encoded = f"{int(day):08d}"
        datetime.strptime(encoded, "%Y%m%d")
    except ValueError:
        return "INVALID_DATE"
    zero_bar = op == hi == lo == close == 0
    if not zero_bar and not (hi >= max(op, lo, close) and lo <= min(op, hi, close)):
        return "INVALID_OHLC"
    if not np.isfinite(amount) or amount < 0:
        return "INVALID_AMOUNT"
    if volume < 0:
        return "INVALID_VOLUME"
    return "SOURCE_FILE_VALIDATED_RECORD"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asof", default="20260924", help="YYYYMMDD; must be no later than the frozen source cutoff")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{8}", args.asof):
        raise ValueError("INVALID_ASOF_DATE")
    asof = int(args.asof)

    contract_path = ROOT / "config/v4_02_canonical_daily_pit_contract_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "V4_CANONICAL_DAILY_PIT_PERIODS_V2" or contract.get("version") != "2.0.0":
        raise ValueError("V4_02_V2_CONTRACT_REQUIRED")
    gate_path = ROOT / contract["outputs"]["entry_gate_receipt"]
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("entry_status") != "ENTRY_AUTHORIZED" or gate.get("stage_completion_authorized") is not False:
        raise ValueError("V4_02_ENTRY_GATE_NOT_AUTHORIZED")
    if gate.get("evidence", {}).get("contract_sha256") != sha256_file(contract_path):
        raise ValueError("ENTRY_GATE_CONTRACT_HASH_STALE")
    v4_01_receipt_path = ROOT / contract["inputs"]["v4_01_final_receipt"]
    universe_receipt_path = ROOT / contract["inputs"]["v4_01_required_universe_receipt"]
    selection_receipt_path = ROOT / "reports/v4_01/v4_01_source_selection_receipt_R4_20260925.json"
    for key, path in (
        ("v4_01_final_receipt_sha256", v4_01_receipt_path),
        ("v4_01_historical_universe_receipt_sha256", universe_receipt_path),
        ("v4_01_source_selection_receipt_sha256", selection_receipt_path),
    ):
        if gate.get("evidence", {}).get(key) != sha256_file(path):
            raise ValueError(f"ENTRY_GATE_EVIDENCE_STALE:{key}")
    cutoff = int(contract["inputs"]["source_cutoff"].replace("-", ""))
    if asof > cutoff:
        raise ValueError("ASOF_AFTER_SOURCE_CUTOFF")

    manifest_path = ROOT / contract["inputs"]["canonical_source_selection"]
    selection_receipt = json.loads(selection_receipt_path.read_text(encoding="utf-8"))
    if sha256_file(manifest_path) != selection_receipt.get("source_selection_manifest_sha256"):
        raise ValueError("CANONICAL_SOURCE_SELECTION_MANIFEST_HASH_MISMATCH")
    selection = json.loads(manifest_path.read_text(encoding="utf-8"))
    if selection.get("contract_id") != "CANONICAL_SOURCE_SELECTION_V1":
        raise ValueError("CANONICAL_SOURCE_SELECTION_CONTRACT_MISMATCH")

    package_path = ROOT / contract["inputs"]["raw_archive"].format(source_package_sha256=PACKAGE_SHA)
    bundle_path = ROOT / "data/source_bundles" / BUNDLE_ID / "source_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    extracted_root = ROOT / bundle["extraction"]["root"]
    local_root = ROOT / "data/v4/local_tdx_snapshots" / LOCAL_SNAPSHOT_ID
    source_manifest_path = ROOT / contract["inputs"]["v4_01_source_manifest"]
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    inventory_path = ROOT / contract["inputs"]["v4_01_source_inventory"]
    package_inventory = load_csv_inventory(inventory_path)
    package_hashes = {path: row["sha256"] for path, row in package_inventory.items()}
    local_snapshot_check = verify_local_snapshot(ROOT / "data/v4/local_tdx_snapshots", LOCAL_SNAPSHOT_ID)
    local_manifest_path = local_root / "snapshot_manifest.json"
    local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
    if sha256_file(local_manifest_path) != selection["execution_identity"]["local_snapshot_manifest_sha256"]:
        raise ValueError("LOCAL_SNAPSHOT_MANIFEST_HASH_MISMATCH")
    local_hashes = {row["relative_path"]: row["sha256"] for row in local_manifest["files"]}
    snapshot_check = verify_zip_snapshot(
        package_path,
        extracted_root,
        package_inventory,
        int(bundle["extraction"]["entry_count"]),
        source_manifest["source"]["extracted_content_digest"],
    )
    if snapshot_check.get("status") != "PASS" or local_snapshot_check.get("status") != "PASS":
        raise ValueError("SOURCE_SNAPSHOT_VERIFICATION_FAILED")

    r6_materialization = json.loads(
        (ROOT / "reports/v4_01/security_lifecycle_materialization_receipt_R6_2_20260926.json").read_text(encoding="utf-8")
    )
    v4_01_receipt = json.loads(v4_01_receipt_path.read_text(encoding="utf-8"))
    materialization_path = ROOT / "reports/v4_01/security_lifecycle_materialization_receipt_R6_2_20260926.json"
    if v4_01_receipt.get("evidence", {}).get("R6_2_append_only_lifecycle_materialization", {}).get("sha256") != sha256_file(materialization_path):
        raise ValueError("R6_2_MATERIALIZATION_RECEIPT_HASH_MISMATCH")
    identity_path = ROOT / r6_materialization["intervals"]["current_interval_artifact_path"]
    identity_map = load_membership_identity(identity_path, r6_materialization["intervals"]["current_interval_artifact_sha256"])
    universe_receipt = json.loads(universe_receipt_path.read_text(encoding="utf-8"))
    universe_artifact = ROOT / universe_receipt["required_scope"]["output"]["path"]
    if sha256_file(universe_artifact) != universe_receipt["required_scope"]["output"]["sha256"]:
        raise ValueError("R6_2_REQUIRED_UNIVERSE_ARTIFACT_HASH_MISMATCH")
    accepted_boards = load_accepted_board_map(universe_artifact)
    segments_by_key: dict[str, list[dict]] = {}
    for segment in selection["segments"]:
        segments_by_key.setdefault(segment["source_security_key"], []).append(segment)

    run_id = f"V4_02_RAW_SELECTED_{asof}_{datetime.now(timezone.utc):%H%M%S}Z"
    destination = ROOT / "data/v4/canonical" / run_id
    if destination.exists():
        raise ValueError("RUN_ID_ALREADY_EXISTS")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage_dir = Path(tempfile.mkdtemp(prefix=run_id + ".", suffix=".staging", dir=destination.parent))
    parquet_path = stage_dir / "canonical_daily_raw_selected.parquet"
    writer = pq.ParquetWriter(parquet_path, SCHEMA, compression="zstd", version="2.6")

    selected_segments: list[dict] = []
    total_selected = 0
    emitted_rows = 0
    optional_bse_rows_excluded = 0
    flagged_rows = 0
    identity_rows = 0
    identity_rows_by_board: dict[str, int] = {}
    try:
        for index, source_key in enumerate(sorted(segments_by_key), start=1):
            market, code = source_key.split(".", 1)
            relative = f"{market.lower()}/lday/{market.lower()}{code.lower()}.day"
            package_path_for_key = extracted_root / relative
            local_path_for_key = local_root / relative
            package_raw: dict[int, bytes] = {}
            package_ordinals: dict[int, int] = {}
            local_raw: dict[int, bytes] = {}
            local_ordinals: dict[int, int] = {}
            package_revision = PACKAGE_SHA
            local_revision = LOCAL_SNAPSHOT_ID
            if package_path_for_key.is_file():
                expected = package_hashes.get(relative)
                if not expected or sha256_file(package_path_for_key) != expected:
                    raise ValueError(f"PACKAGE_FILE_HASH_MISMATCH:{relative}")
                package_revision = expected
                package_raw, package_ordinals = read_file_records(package_path_for_key)
            if local_path_for_key.is_file():
                expected = local_hashes.get(relative)
                if not expected or sha256_file(local_path_for_key) != expected:
                    raise ValueError(f"LOCAL_FILE_HASH_MISMATCH:{relative}")
                local_revision = expected
                local_raw, local_ordinals = read_file_records(local_path_for_key)

            selected, _counts = select_records(
                source_key,
                package_raw,
                local_raw,
                package_revision=package_revision,
                local_revision=local_revision,
            )
            calculated_segments = selection_segments(selected, source_key)
            expected_segments = segments_by_key[source_key]
            if calculated_segments != expected_segments:
                raise ValueError(f"SOURCE_SELECTION_SEGMENT_REPLAY_MISMATCH:{source_key}")
            selected_segments.extend(calculated_segments)
            total_selected += len(selected)
            eligible = [row for row in selected if row.trade_date <= asof]
            if not eligible:
                continue
            if market == "BJ":
                optional_bse_rows_excluded += len(eligible)
                continue

            source_identity = []
            source_ordinals = []
            alternative_families = []
            alternative_revisions = []
            alternative_digests = []
            reasons = []
            for item in eligible:
                from_local = item.source_family == LOCAL_FAMILY
                ordinals = local_ordinals if from_local else package_ordinals
                source_identity.append(item.source_revision)
                source_ordinals.append(ordinals[item.trade_date])
                alternative_families.append(item.alternative_family)
                alternative_revisions.append(item.alternative_revision)
                alternative_digests.append(hashlib.sha256(item.alternative_record).hexdigest() if item.alternative_record else None)
                reasons.append(item.selection_reason)

            raw_selected = b"".join(item.selected_record for item in eligible)
            records = np.frombuffer(raw_selected, dtype=DAY_DTYPE)
            count = len(records)
            canonical_ids: list[str | None] = []
            identity_qualities: list[str] = []
            membership_basis: list[str] = []
            identity_revisions: list[str | None] = []
            quality: list[str] = []
            board = accepted_boards.get(source_key)
            for values in records:
                security_id, identity_quality, membership, identity_revision = date_identity(
                    source_key, int(values["trade_date"]), identity_map
                )
                canonical_ids.append(security_id)
                identity_qualities.append(identity_quality)
                membership_basis.append(membership)
                identity_revisions.append(identity_revision)
                quality.append(check_raw_quality(tuple(values)))
            flagged_rows += sum(value != "SOURCE_FILE_VALIDATED_RECORD" for value in quality)
            identity_rows += sum(value is not None for value in canonical_ids)
            if board:
                identity_rows_by_board[board] = identity_rows_by_board.get(board, 0) + sum(
                    value is not None for value in canonical_ids
                )

            table = pa.Table.from_arrays(
                [
                    pa.array(canonical_ids, type=pa.string()),
                    pa.array([source_key] * count, type=pa.string()),
                    pa.array([board] * count, type=pa.string()),
                    pa.array(records["trade_date"], type=pa.uint32()),
                    pa.array(records["open_raw"], type=pa.uint32()),
                    pa.array(records["high_raw"], type=pa.uint32()),
                    pa.array(records["low_raw"], type=pa.uint32()),
                    pa.array(records["close_raw"], type=pa.uint32()),
                    pa.array(np.full(count, 100, dtype=np.uint16), type=pa.uint16()),
                    pa.array(records["amount_source"], type=pa.float32()),
                    pa.array(records["volume_source"], type=pa.uint32()),
                    pa.array(records["reserved"], type=pa.uint32()),
                    pa.array([relative] * count, type=pa.string()),
                    pa.array(source_identity, type=pa.string()),
                    pa.array(source_ordinals, type=pa.uint32()),
                    pa.array([item.source_family for item in eligible], type=pa.string()),
                    pa.array([item.source_revision for item in eligible], type=pa.string()),
                    pa.array(reasons, type=pa.string()),
                    pa.array(alternative_families, type=pa.string()),
                    pa.array(alternative_revisions, type=pa.string()),
                    pa.array(alternative_digests, type=pa.string()),
                    pa.array(identity_qualities, type=pa.string()),
                    pa.array(identity_revisions, type=pa.string()),
                    pa.array(membership_basis, type=pa.string()),
                    pa.array(["DIAGNOSTIC_NON_PIT"] * count, type=pa.string()),
                    pa.array(["RAW"] * count, type=pa.string()),
                    pa.array(["UNKNOWN"] * count, type=pa.string()),
                    pa.array(quality, type=pa.string()),
                ],
                schema=SCHEMA,
            )
            writer.write_table(table, row_group_size=100_000)
            emitted_rows += count
            if index % 1000 == 0:
                print(json.dumps({"security_keys_processed": index, "selected_rows": total_selected, "emitted_rows": emitted_rows}), flush=True)

        if selection_digest(selected_segments) != selection.get("selection_digest"):
            raise ValueError("SOURCE_SELECTION_GLOBAL_DIGEST_MISMATCH")
        if total_selected != int(selection["totals"]["selected_rows"]):
            raise ValueError("SOURCE_SELECTION_ROW_COUNT_MISMATCH")
    except Exception:
        writer.close()
        for item in stage_dir.iterdir():
            if item.is_file():
                item.unlink()
        stage_dir.rmdir()
        raise
    writer.close()

    with parquet_path.open("rb+") as stream:
        os.fsync(stream.fileno())
    parquet_sha = sha256_file(parquet_path)
    parquet_rows = pq.ParquetFile(parquet_path).metadata.num_rows
    if parquet_rows != emitted_rows:
        raise ValueError("RAW_PARQUET_ROW_COUNT_MISMATCH")
    source_manifest = {
        "contract_id": "V4_02_RAW_SOURCE_MANIFEST_V2",
        "run_id": run_id,
        "stage_contract_id": contract["contract_id"],
        "contract_sha256": sha256_file(contract_path),
        "entry_gate_receipt_sha256": sha256_file(gate_path),
        "source_package_sha256": PACKAGE_SHA,
        "source_bundle_id": BUNDLE_ID,
        "source_manifest_v4_01_sha256": sha256_file(source_manifest_path),
        "source_selection_manifest_sha256": sha256_file(manifest_path),
        "source_selection_digest": selection["selection_digest"],
        "source_selection_segments_replayed": len(selected_segments),
        "source_selection_rows": total_selected,
        "required_scope_emitted_rows": emitted_rows,
        "optional_bse_degraded_rows_excluded": optional_bse_rows_excluded,
        "local_snapshot_manifest_sha256": sha256_file(local_manifest_path),
        "membership_interval_artifact_sha256": r6_materialization["intervals"]["current_interval_artifact_sha256"],
        "required_universe_artifact_sha256": universe_receipt["required_scope"]["output"]["sha256"],
        "asof_trade_date": asof,
        "source_cutoff": cutoff,
        "zip_extraction_verification": snapshot_check,
        "local_snapshot_verification": local_snapshot_check,
        "lineage": "SOURCE_SELECTED_RAW; DIAGNOSTIC_NON_PIT; R6_2_MEMBERSHIP_ID_ONLY_WITHIN_ACCEPTED_ROSTER_INTERVAL",
    }
    manifest_path_out = stage_dir / "source_manifest.json"
    atomic_json(manifest_path_out, source_manifest)
    receipt = {
        "contract_id": "V4_02_RAW_CANONICAL_CANDIDATE_RECEIPT_V2",
        "version": "2.0.0",
        "run_id": run_id,
        "stage": "V4-02",
        "stage_contract": "DA-MSR-V4.2.2-CODEX-REV2 §§3B.6/3C.1-3C.4/5.2-5.3/6A/10N/78; V4_CANONICAL_DAILY_PIT_PERIODS_V2",
        "consulted_upgrade": contract["consulted_upgrade"],
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "contract_sha256": sha256_file(contract_path),
        },
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "BLOCKED",
        "stage_completion_authorized": False,
        "acceptance": "Source-selected RAW daily candidate emitted. V4-02 remains BLOCKED until every required adjusted, calendar, trading-status, period, temporal-leakage and price-limit capability passes independent acceptance.",
        "entry_gate_status": gate["entry_status"],
        "source_selection_status": "PASS_REPLAYED",
        "row_counts": {
            "source_selection_full_history_rows": total_selected,
            "raw_daily_rows_at_asof": emitted_rows,
            "optional_bse_degraded_rows_excluded": optional_bse_rows_excluded,
            "identity_mapped_rows_within_r6_2_roster_intervals": identity_rows,
            "record_quality_flagged_rows": flagged_rows,
        },
        "identity_mapped_rows_by_board": identity_rows_by_board,
        "outputs": {
            "canonical_daily_raw_selected": {
                "path": parquet_path.name,
                "sha256": parquet_sha,
                "byte_count": parquet_path.stat().st_size,
                "row_count": parquet_rows,
                "schema": SCHEMA.names,
            }
        },
        "source_manifest": {"path": manifest_path_out.name, "sha256": sha256_file(manifest_path_out)},
        "capabilities": {
            "raw_source_selected_daily": "CANDIDATE_EMITTED",
            "historical_pit_observed": "UNAVAILABLE",
            "adjusted_daily": "UNAVAILABLE",
            "formal_market_calendar": "UNAVAILABLE",
            "dated_trading_status_suspension_resumption": "UNAVAILABLE",
            "formal_weekly_monthly_closed_only_as_of": "UNAVAILABLE",
            "section_3c_4_temporal_leakage": "UNVERIFIED",
            "price_limit_rule_v1": "UNAVAILABLE",
        },
        "degraded_scopes": ["BSE_OPTIONAL_ONLY"],
        "blocked_scopes": [
            "ADJUSTED_CANONICAL_DAILY",
            "FORMAL_MARKET_CALENDAR_AND_DATED_TRADING_STATUS",
            "FORMAL_WEEKLY_MONTHLY_CLOSED_ONLY_AS_OF",
            "SECTION_3C_4_TEMPORAL_LEAKAGE",
            "PRICE_LIMIT_RULE_V1",
            "ATOMIC_FULL_STAGE_PUBLICATION_AND_INDEPENDENT_POSTCHECK",
        ],
        "tdx_root_read_count": 0,
        "tdx_root_write_count": 0,
        "scanner_or_factor_run_count": 0,
        "next_stage": "V4_02_FORMAL_PERIOD_AND_STATUS_CAPABILITIES",
    }
    atomic_json(stage_dir / "stage_receipt.json", receipt)
    os.replace(stage_dir, destination)
    print(json.dumps({"run_id": run_id, "status": receipt["status"], "rows": emitted_rows, "path": destination.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
