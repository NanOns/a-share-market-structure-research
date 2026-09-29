"""Replay major R4 outputs twice and compare restored artifact bytes."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports/v4_05/V4_05_R4_DETERMINISM.json"


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def snapshot() -> dict[str, str]:
    paths = {
        "period_artifact": ROOT / "reports/v4_05/staging/V4_05_R4_PERIOD_ASOF.jsonl.gz",
        "market_snapshot": ROOT / "reports/v4_05/V4_05_R4_TARGET_MARKET_SNAPSHOT.json",
        "market_reference": ROOT / "reports/v4_05/V4_05_R4_MARKET_REFERENCE.json",
        "full_scope_factor_artifact": ROOT / "reports/v4_05/staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz",
        "market_regime": ROOT / "reports/v4_05/V4_05_R4_MARKET_REGIME.json",
        "core_profile_artifact": ROOT / "reports/v4_05/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz",
    }
    return {name: sha(path) for name, path in paths.items()}


def main() -> dict:
    first = snapshot()
    stages = [
        ("period", load("v405r4_period", "build_v4_05_r4_periods.py").main),
        ("market_identity_reference", load("v405r4_market", "build_v4_05_r4_market_reference.py").main),
        ("full_scope_factors", load("v405r4_factors", "build_v4_05_r4_full_scope_factors.py").main),
        ("market_regime", load("v405r4_regime", "build_v4_05_r4_market_regime.py").main),
        ("core_profile", load("v405r4_profile", "build_v4_05_r4_core_profile.py").main),
    ]
    elapsed = {}
    for name, run in stages:
        start = time.perf_counter()
        run()
        elapsed[name] = round(time.perf_counter() - start, 3)
        print(json.dumps({"stage": name, "seconds": elapsed[name]}, ensure_ascii=False), flush=True)
    second = snapshot()
    checks = {key: {"first_sha256": first[key], "second_sha256": second[key], "match": first[key] == second[key]} for key in first}
    result = {"contract_id": "V4_05_R4_DETERMINISM_V1", "status": "PASS" if all(item["match"] for item in checks.values()) else "FAIL",
              "runs": 2, "first_run_artifact_sha256": first, "second_run_artifact_sha256": second,
              "artifact_checks": checks, "second_run_seconds_by_stage": elapsed,
              "gz_metadata": "mtime=0, empty embedded filename", "external_acceptance": "PENDING"}
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUT)
    return result


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, sort_keys=True))
