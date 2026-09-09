"""Capture and verify a user-operated TDX update without writing to TDX."""
from __future__ import annotations

import hashlib
import json
import os
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "m0-terminal-update-observation-v1.0"
MONITORED_METADATA = (
    "T0002/hq_cache/gbbq", "T0002/hq_cache/gbbq.map", "T0002/hq_cache/tdxhy.cfg",
    "T0002/hq_cache/tdxzs.cfg", "T0002/hq_cache/infoharbor_block.dat",
    "T0002/hq_cache/shs.tnf", "T0002/hq_cache/szs.tnf", "T0002/hq_cache/bjs.tnf",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _snapshot(tdx: Path) -> dict[str, Any]:
    rows = []
    for market in ("sh", "sz", "bj"):
        for path in sorted((tdx / "vipdoc" / market / "lday").glob(f"{market}*.day")):
            stat = path.stat()
            latest_date = None
            if stat.st_size >= 32 and stat.st_size % 32 == 0:
                with path.open("rb") as handle:
                    handle.seek(-32, 2)
                    latest_date = struct.unpack("<I", handle.read(4))[0]
            rows.append({"path": str(path.relative_to(tdx)).replace("\\", "/"), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "latest_date": latest_date})
    for relative in MONITORED_METADATA:
        path = tdx / relative
        if path.is_file():
            stat = path.stat()
            rows.append({"path": relative, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    digest = hashlib.sha256(_canonical(rows)).hexdigest()
    return {"captured_at_utc": datetime.now(timezone.utc).isoformat(), "manifest_sha256": digest, "rows": rows}


def _atomic(path: Path, value: dict[str, Any], tdx: Path) -> None:
    path = path.resolve(); tdx = tdx.resolve()
    if path == tdx or tdx in path.parents:
        raise ValueError("OUTPUT_UNDER_TDX_ROOT")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def capture(root: Path, tdx: Path) -> dict[str, Any]:
    value = {"version": VERSION, "final_status": "BASELINE_CAPTURED", "tdx_root": str(tdx), "before": _snapshot(tdx), "tdx_write_attempted": False}
    _atomic(root / "reports/upgrade_m0/TERMINAL_UPDATE_BASELINE.json", value, tdx)
    return value


def finalize(root: Path, tdx: Path, stability_seconds: int = 5) -> dict[str, Any]:
    baseline_path = root / "reports/upgrade_m0/TERMINAL_UPDATE_BASELINE.json"
    if not baseline_path.is_file():
        raise FileNotFoundError("TERMINAL_UPDATE_BASELINE_MISSING")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    first = _snapshot(tdx)
    time.sleep(stability_seconds)
    second = _snapshot(tdx)
    before_rows = {row["path"]: row for row in baseline["before"]["rows"]}
    after_rows = {row["path"]: row for row in second["rows"]}
    changed = sorted(path for path in before_rows.keys() | after_rows.keys() if before_rows.get(path) != after_rows.get(path))
    day_changes = [path for path in changed if path.endswith(".day")]
    metadata_changes = [path for path in changed if path in MONITORED_METADATA]
    markets = sorted({path.split("/")[1].upper() for path in day_changes if path.startswith("vipdoc/")})
    stable = first["manifest_sha256"] == second["manifest_sha256"]
    market_latest: dict[str, dict[str, Any]] = {}
    for market in ("SH", "SZ", "BJ"):
        dates = [int(row["latest_date"]) for row in second["rows"] if row.get("latest_date") and row["path"].startswith(f"vipdoc/{market.lower()}/lday/")]
        latest = max(dates) if dates else None
        market_latest[market] = {
            "latest_date": latest,
            "latest_date_file_count": sum(1 for value in dates if value == latest),
            "valid_day_file_count": len(dates),
        }
    latest_dates = {item["latest_date"] for item in market_latest.values() if item["latest_date"] is not None}
    three_market_date_alignment = len(latest_dates) == 1 and len(market_latest) == 3 and all(item["valid_day_file_count"] > 0 for item in market_latest.values())
    passed = bool(changed and day_changes and stable and three_market_date_alignment)
    value = {
        "version": VERSION, "final_status": "PASS" if passed else "BLOCKED", "tdx_root": str(tdx),
        "before_manifest_sha256": baseline["before"]["manifest_sha256"], "after_manifest_sha256": second["manifest_sha256"],
        "stability_manifest_sha256_a": first["manifest_sha256"], "stability_manifest_sha256_b": second["manifest_sha256"],
        "stability_seconds": stability_seconds, "stable_after_update": stable, "changed_file_count": len(changed),
        "changed_day_file_count": len(day_changes), "changed_metadata_file_count": len(metadata_changes), "changed_markets": markets,
        "metadata_change_status": "CHANGED" if metadata_changes else "UNCHANGED",
        "metadata_freshness": "UNCHANGED_NOT_ASSUMED_STALE" if not metadata_changes else "CHANGED",
        "market_latest_dates": market_latest,
        "three_market_latest_date_alignment": three_market_date_alignment,
        "observation_basis": "USER_CONFIRMED_UPDATE_WITH_BEFORE_AFTER_MANIFESTS",
        "changed_file_samples": changed[:100], "tdx_write_attempted": False,
        "blocking_reasons": [] if passed else [name for name, ok in (("NO_CHANGE_SINCE_BASELINE", bool(changed)), ("NO_DAY_FILE_CHANGE", bool(day_changes)), ("THREE_MARKET_LATEST_DATE_MISMATCH", three_market_date_alignment), ("SOURCE_NOT_STABLE_AFTER_UPDATE", stable)) if not ok],
    }
    _atomic(root / "reports/upgrade_m0/TERMINAL_UPDATE_OBSERVATION.json", value, tdx)
    return value
