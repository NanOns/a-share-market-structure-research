from __future__ import annotations

"""Seal the existing V4-02 source-selected RAW candidate without rebuilding it."""

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/v4_02_raw_formal_acceptance_v1.json"
REQUIRED_MARKERS = {
    "raw_non_pit_and_unknown_limit_fail_closed": True,
    "optional_bse_excluded_from_required_output": True,
    "asof_future_row_exclusion": True,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    return json.loads(data), data


def main() -> int:
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract = json.loads(contract_bytes)
    root = ROOT
    artifact = root / contract["raw_artifact"]
    receipt, receipt_bytes = load(root / contract["evidence"]["stage_receipt"])
    source_manifest, source_bytes = load(root / contract["evidence"]["source_manifest"])
    postcheck, postcheck_bytes = load(root / contract["evidence"]["independent_candidate_postcheck"])
    expected = contract["expected"]
    metadata = pq.ParquetFile(artifact).metadata
    actual_sha = sha256_file(artifact)
    actual_size = artifact.stat().st_size
    actual_rows = int(metadata.num_rows)
    checks = {
        "artifact_sha256_matches": actual_sha == expected["sha256"] == receipt["outputs"]["canonical_daily_raw_selected"]["sha256"],
        "artifact_size_matches": actual_size == expected["byte_count"] == receipt["outputs"]["canonical_daily_raw_selected"]["byte_count"],
        "parquet_row_count_matches": actual_rows == expected["row_count"] == receipt["outputs"]["canonical_daily_raw_selected"]["row_count"],
        "source_selection_digest_bound": source_manifest["source_selection_digest"] == expected["source_selection_digest"],
        "source_selection_status_pass": receipt["source_selection_status"] == "PASS_REPLAYED",
        "postcheck_passed": postcheck["independent_postcheck_status"] == "CANDIDATE_POSTCHECK_PASS" and all(postcheck["checks"].values()),
        "required_board_consumer_scope_present": set(expected["required_boards"]).issubset(postcheck["summary"]["board_scope_counts"]) and all(postcheck["summary"]["board_scope_counts"][board] > 0 for board in expected["required_boards"]),
        "bse_isolated": postcheck["summary"]["bse_rows_emitted"] == 0 and postcheck["summary"]["optional_bse_degraded_rows_excluded"] == expected["excluded_bse_rows"] and source_manifest["optional_bse_degraded_rows_excluded"] == expected["excluded_bse_rows"],
        "quality_markers_preserved": all(postcheck["checks"].get(name) is value for name, value in REQUIRED_MARKERS.items()) and postcheck["summary"]["unknown_limit_rows"] == expected["row_count"] and postcheck["summary"]["diagnostic_non_pit_rows"] == expected["row_count"],
        "source_cutoff_bound": source_manifest["source_cutoff"] == int(contract["source_cutoff"].replace("-", "")) and source_manifest["asof_trade_date"] <= int(contract["source_cutoff"].replace("-", "")) and receipt["row_counts"]["raw_daily_rows_at_asof"] == expected["row_count"],
        "schema_has_required_consumer_keys": {"canonical_security_id", "source_security_key", "board_scope", "trade_date", "adjustment_view", "limit_status", "record_quality"}.issubset(set(metadata.schema.to_arrow_schema().names)),
    }
    status = "RAW_CANONICAL_DAILY_PASS" if all(checks.values()) else "RAW_CANONICAL_DAILY_BLOCKED"
    result = {
        "contract_id": "V4_02_RAW_CANONICAL_FORMAL_ACCEPTANCE_V1",
        "status": status,
        "capability": "RAW_CANONICAL_DAILY_PASS" if status.endswith("PASS") else "RAW_CANONICAL_DAILY_BLOCKED",
        "stage_status": "BLOCKED_OPEN_OTHER_REQUIRED_CAPABILITIES",
        "stage_completion_authorized": False,
        "run_id": receipt["run_id"],
        "source_cutoff": contract["source_cutoff"],
        "execution_identity": {
            "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "contract_sha256": sha256_bytes(contract_bytes),
            "script_sha256": sha256_file(Path(__file__).resolve()),
        },
        "artifact": {"path": contract["raw_artifact"], "sha256": actual_sha, "byte_count": actual_size, "row_count": actual_rows, "schema_sha256": sha256_bytes(metadata.schema.to_arrow_schema().serialize().to_pybytes())},
        "source_selection": {"digest": source_manifest["source_selection_digest"], "manifest_sha256": sha256_bytes(source_bytes), "selected_rows": source_manifest["source_selection_rows"], "segments_replayed": source_manifest["source_selection_segments_replayed"]},
        "evidence": {
            "stage_receipt_sha256": sha256_bytes(receipt_bytes),
            "source_manifest_sha256": sha256_bytes(source_bytes),
            "independent_candidate_postcheck_sha256": sha256_bytes(postcheck_bytes),
            "independent_candidate_postcheck": postcheck["independent_postcheck_status"],
        },
        "required_board_counts": postcheck["summary"]["board_scope_counts"],
        "bse": {"emitted_rows": postcheck["summary"]["bse_rows_emitted"], "excluded_rows": postcheck["summary"]["optional_bse_degraded_rows_excluded"], "scope": "OPTIONAL_DEGRADED_ISOLATED"},
        "lineage": "SOURCE_SELECTED_RAW; DIAGNOSTIC_NON_PIT; membership identity only within accepted R6.2 roster intervals.",
        "adjusted_quality": "NOT_ACCEPTED_BY_RAW_SEAL",
        "checks": checks,
        "acceptance_boundary": "This formal seal accepts the existing RAW artifact and its source-selection/readback evidence only. It does not accept adjusted data, trading status, periods, leakage, price limits, whole-stage publication, or V4-02 completion.",
        "next_stage": "PACK_A_ADJUSTMENT_AND_TRADING_STATUS",
    }
    output = ROOT / "reports/v4_02/V4_02_RAW_CANONICAL_FORMAL_ACCEPTANCE_V1.json"
    atomic_json(output, result)
    print(json.dumps({"status": status, "checks": checks, "receipt": output.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0 if status == "RAW_CANONICAL_DAILY_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
