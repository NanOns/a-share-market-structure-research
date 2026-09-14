"""Verify the P12-02 pilot lock against current bytes and Git recoverability."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports/p12_02/historical_input_pilot.json"
GBBQ = Path("D:/new_tdx/T0002/hq_cache/gbbq")
PARQUET = ROOT / "data/normalized/adjusted_daily.parquet"
OUT = ROOT / "reports/p12_02/dependency_lock_probe.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: dict) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def git_head_hash(path: str) -> str | None:
    result = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                            capture_output=True, check=False)
    return hashlib.sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def main() -> None:
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    lock = pilot["dependency_lock_draft"]
    recorded = pilot["dependency_lock_draft_sha256"]
    canonical_matches = canonical_sha256(lock) == recorded
    source_checks = {}
    for name, expected in lock["source_hashes"].items():
        actual = sha256(ROOT / name)
        head = git_head_hash(name)
        source_checks[name] = {"matches_worktree": actual == expected,
                               "recoverable_from_head": head == expected,
                               "recorded_sha256": expected}
    data_checks = {"parquet_matches": sha256(PARQUET) == lock["adjusted_daily_sha256"],
                   "gbbq_matches": sha256(GBBQ) == lock["gbbq_current_sha256"]}
    tampered = copy.deepcopy(lock)
    key = next(iter(tampered["source_hashes"]))
    tampered["source_hashes"][key] = "0" * 64
    tamper_rejected = canonical_sha256(tampered) != recorded
    result = {
        "stage_contract": "P12-02_DEPENDENCY_LOCK_PROBE_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "pilot_lock_sha256": recorded,
        "canonical_matches": canonical_matches,
        "source_checks": source_checks,
        "data_checks": data_checks,
        "tamper_rejected": tamper_rejected,
        "source_recoverable_from_head": all(item["recoverable_from_head"] for item in source_checks.values()),
        "production_run_bound": False,
        "historical_source_availability_proven": False,
        "acceptance_result": "DEGRADED_PASS",
        "acceptance_scope": "Current byte and tamper verification only; complete reproducible production lock pending",
        "next_stage": "P12-02_FACTOR_V3_3_CONTINUE",
    }
    if not (canonical_matches and tamper_rejected and all(data_checks.values())
            and all(item["matches_worktree"] for item in source_checks.values())):
        result["acceptance_result"] = "BLOCKED"
        result["next_stage"] = "P12-02_DEPENDENCY_LOCK_REPAIR"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="dependency_lock_probe.", suffix=".tmp", dir=OUT.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, OUT)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(OUT)


if __name__ == "__main__":
    main()
