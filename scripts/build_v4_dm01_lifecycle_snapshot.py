from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402
from workbench_analysis.daily_source_manifests import build_current_lifecycle_snapshot  # noqa: E402
from workbench_analysis.baostock_runtime_acceptance import (  # noqa: E402
    load_runtime_acceptance_manifest,
    runtime_acceptance_error,
)
from workbench_analysis.baostock_supplemental import package_metadata  # noqa: E402


SHANGHAI = ZoneInfo("Asia/Shanghai")
TDX_ROOT = Path("D:/new_tdx")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_input(root: Path, manifest: dict, name: str) -> tuple[Path, dict]:
    record = manifest.get("parent_artifacts", {}).get(name)
    if not isinstance(record, dict) or not record.get("path") or not record.get("sha256"):
        raise ValueError("LIFECYCLE_BOOTSTRAP_INPUT_MISSING:" + name)
    path = (root / record["path"]).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("LIFECYCLE_BOOTSTRAP_INPUT_OUTSIDE_PROJECT:" + name) from exc
    if not path.is_file() or sha256(path) != record["sha256"]:
        raise ValueError("LIFECYCLE_BOOTSTRAP_INPUT_DIGEST_MISMATCH:" + name)
    return path, record


def accepted_parent_rows(path: Path, baseline_date: str) -> list[dict]:
    rows: list[dict] = []
    last_date = ""
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            row_date = str(row.get("trade_date") or "")
            if row_date < last_date:
                raise ValueError("LIFECYCLE_PARENT_UNIVERSE_NOT_DATE_SORTED")
            last_date = row_date
            if row_date == baseline_date:
                rows.append(row)
            elif row_date > baseline_date:
                break
    return rows


def select_baostock_snapshot(target_date: str, snapshot_id: str | None) -> tuple[dict, Path]:
    folder = ROOT / "data/v4/source_snapshots/baostock" / target_date.replace("-", "")
    matches = []
    for path in folder.glob("sha256-*/daily_update.json") if folder.is_dir() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (record.get("trade_date") == target_date and record.get("provider_date") == target_date
                and record.get("status") in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"}
                and record.get("daily_rows") and "adjustment_factor_rows" in record
                and (snapshot_id is None or record.get("snapshot_id") == snapshot_id)):
            matches.append((record, path))
    if not matches:
        raise ValueError("LIFECYCLE_BAOSTOCK_TARGET_SNAPSHOT_MISSING")
    if len(matches) != 1:
        raise ValueError("LIFECYCLE_BAOSTOCK_TARGET_SNAPSHOT_AMBIGUOUS_REQUIRE_SNAPSHOT_ID")
    record, path = matches[0]
    if not record["snapshot_id"].startswith("sha256-") or path.parent.name != record["snapshot_id"]:
        raise ValueError("LIFECYCLE_BAOSTOCK_SNAPSHOT_IDENTITY_MISMATCH")
    return record, path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a PIT current lifecycle snapshot from accepted parent and target-date inputs.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--baostock-snapshot-id")
    args = parser.parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    from workbench_analysis.dm01_runtime_r4 import session_gate
    gate = session_gate(args.target_date, now.isoformat())
    local = now.astimezone(SHANGHAI)
    output = ROOT / "reports/v4_dm01" / args.target_date / "current_lifecycle_snapshot.json"
    receipt_path = ROOT / "reports/v4_dm01" / args.target_date / "current_lifecycle_snapshot_receipt.json"
    if gate['status'] == 'WAIT_MARKET_CLOSE':
        result = {"contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1", "status": "WAIT_MARKET_CLOSE",
                  "trade_date": args.target_date, "observed_at": now.isoformat(), "tdx_root_write_count": 0}
    else:
        try:
            head_path = ROOT / "data/v4/V4_DATA_ACCEPTED_HEAD.json"
            head = json.loads(head_path.read_text(encoding="utf-8"))
            baseline_date = str(head.get("accepted_trade_date") or "")
            from workbench_analysis.dm01_runtime_r4 import current_parent, calendar as accepted_calendar
            from workbench_analysis.dm01_sources_r4 import identity_projection
            parent = current_parent(ROOT)
            universe_path = ROOT / parent['components']['IDENTITY_UNIVERSE']['path']
            universe_rows = json.loads(universe_path.read_bytes())['rows']
            identity = identity_projection(ROOT, args.target_date, now.isoformat())
            identity_path = Path(identity['binding']['path'])
            identity_records = identity['records']
            cal = accepted_calendar(ROOT)
            calendar_path = ROOT / cal['binding']['path']
            calendar = dict(status='PASS', latest_completed_official_session=baseline_date, official_sessions_after_base_cutoff=[d for d in cal['session_dates'] if d > baseline_date])
            bootstrap_path = ROOT / head['accepted_chain']['path']
            bao, bao_path = select_baostock_snapshot(args.target_date, args.baostock_snapshot_id)
            config = json.loads((ROOT / "config/baostock_supplemental_contract_v1.json").read_text(encoding="utf-8"))
            runtime_template = config["dm01_daily_updates"]["runtime_acceptance_manifest_template"]
            runtime_path = ROOT / runtime_template.replace("{YYYYMMDD}", args.target_date.replace("-", ""))
            runtime = load_runtime_acceptance_manifest(runtime_path, project_root=ROOT, tdx_root=TDX_ROOT)
            runtime_error = runtime_acceptance_error(runtime, sdk=package_metadata(), auth_mode=str(runtime.get("auth_mode") or ""))
            if runtime_error or runtime.get("live_smoke", {}).get("target_date") != args.target_date:
                raise ValueError("LIFECYCLE_BAOSTOCK_RUNTIME_NOT_ACCEPTED:" + str(runtime_error or "TARGET_DATE_MISMATCH"))
            source_evidence = {
                "baseline_data_head_path": head_path.relative_to(ROOT).as_posix(),
                "baseline_data_head_sha256": sha256(head_path),
                "bootstrap_manifest_path": bootstrap_path.relative_to(ROOT).as_posix(),
                "bootstrap_manifest_sha256": sha256(bootstrap_path),
                "parent_universe_path": universe_path.relative_to(ROOT).as_posix(),
                "parent_universe_sha256": sha256(universe_path),
                "identity_map_path": identity_path.relative_to(ROOT).as_posix(),
                "identity_map_sha256": sha256(identity_path),
                "baostock_snapshot_path": bao_path.relative_to(ROOT).as_posix(),
                "baostock_snapshot_sha256": sha256(bao_path),
                "baostock_snapshot_id": bao["snapshot_id"],
                "baostock_runtime_acceptance_path": runtime_path.relative_to(ROOT).as_posix(),
                "baostock_runtime_acceptance_sha256": sha256(runtime_path),
                "calendar_bridge_path": calendar_path.relative_to(ROOT).as_posix(),
                "calendar_bridge_sha256": sha256(calendar_path),
            }
            manifest = build_current_lifecycle_snapshot(
                trade_date=args.target_date,
                baseline_date=baseline_date,
                baseline_data_head=head,
                parent_universe_rows=universe_rows,
                identity_records=identity_records,
                baostock_snapshot=bao,
                official_session_bridge=calendar,
                source_evidence=source_evidence,
                observed_at=now.isoformat(),
            )
            artifact_sha = write_json_atomic(output, manifest, tdx_root=TDX_ROOT)
            result = {
                "contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1",
                "status": manifest["status"],
                "trade_date": args.target_date,
                "event_status": manifest["event_status"],
                "artifact_path": str(output),
                "artifact_sha256": artifact_sha,
                "unknown_source_key_count": len(manifest["unknown_source_keys"]),
                "identity_candidate_count": manifest["identity_detector"]["candidate_count"],
                "tdx_root_write_count": 0,
            }
        except (OSError, KeyError, TypeError, ValueError) as exc:
            result = {"contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1", "status": "WAIT_INPUTS_OR_BLOCKED",
                      "trade_date": args.target_date, "reason": str(exc)[:240],
                      "observed_at": now.isoformat(), "tdx_root_write_count": 0}
    receipt_sha = write_json_atomic(receipt_path, result, tdx_root=TDX_ROOT)
    print(json.dumps({**result, "receipt_path": str(receipt_path), "receipt_sha256": receipt_sha}, ensure_ascii=False))
    return 0 if result["status"] in {"READY", "DEGRADED_PASS", "WAIT_MARKET_CLOSE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
