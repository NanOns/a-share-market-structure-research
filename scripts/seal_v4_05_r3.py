"""Run the formal test gate and hash-bind the R3 replay candidate evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05"
IMPLEMENTATION = "fc92ce7292794583ef4bd1bb0d7f33e5f10cccc1"
COMMAND = "python -m pytest -q tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_05 tests/v4_joint tests/v4_phase0"
REQUIRED = (
    "V4_05_R3_STAGE_ENTRY.md", "V4_05_R3_ACCEPTED_INPUT_MANIFEST.json", "V4_05_R3_DAILY_HISTORY_RECEIPT.json", "V4_05_R3_CALENDAR_RECEIPT.json",
    "V4_05_R3_PERIOD_ASOF.json", "V4_05_R3_FACTOR_SOURCE_TIME.json", "V4_05_R3_FULL_SCOPE_FACTORS_RECEIPT.json",
    "V4_05_R3_MARKET_REFERENCE.json", "V4_05_R3_MARKET_REGIME.json", "V4_05_R3_CORE_PROFILE_REPLAY.json",
    "V4_05_R3_DETERMINISM.json", "V4_05_R3_REVISION_IDEMPOTENCY.json", "V4_05_R3_TEMPORAL_LEAKAGE.json",
    "V4_05_R3_CAPABILITY_GATE.json", "V4_05_R3_RUNTIME_TEST_RECEIPT.json", "V4_05_R3_INDEPENDENT_POSTCHECK.json",
    "V4_05_R3_CLOSURE.md", "staging/V4_05_R3_T0_COORDINATE_DAILY_HISTORY.jsonl.gz",
    "staging/V4_05_R3_PERIOD_ASOF.jsonl.gz", "staging/V4_05_R3_PURE_CORE_FACTORS.jsonl.gz",
    "staging/V4_05_R3_FULL_SCOPE_FACTORS.jsonl.gz", "staging/V4_05_R3_FULL_MARKET_CORE_PROFILE.jsonl.gz",
)


def sha(path):
    h = sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def write(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(tmp, path)


def main():
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != IMPLEMENTATION:
        raise ValueError("implementation commit drift")
    check = json.loads((OUT / "V4_05_R3_INDEPENDENT_POSTCHECK.json").read_text(encoding="utf-8"))
    if check["status"] != "PASS":
        raise ValueError("independent postcheck not passed")
    accepted_paths = ("data/v4/V4_01_ACCEPTED_HEAD.json", "data/v4/V4_02_ACCEPTED_HEAD.json",
                      "data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json", "data/v4/V4_04_ACCEPTED_HEAD.json",
                      "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json")
    head = json.loads((ROOT / accepted_paths[-1]).read_text(encoding="utf-8"))
    calendar = json.loads((OUT / "V4_05_R3_CALENDAR_RECEIPT.json").read_text(encoding="utf-8"))
    input_manifest = {"contract_id": "V4_05_R3_ACCEPTED_INPUT_MANIFEST_V1", "target_trade_date": "2026-09-28",
                      "publication_mode": "DELAYED_FORMAL_PUBLICATION", "knowledge_lineage": "PIT_OBSERVED_AFTER_FORMAL_PUBLICATION",
                      "accepted_heads": {path: sha(ROOT / path) for path in accepted_paths},
                      "source_package": head["evidence_bindings"]["official_tdx_package"],
                      "gbbq_snapshot": head["evidence_bindings"]["gbbq_snapshot"],
                      "go_forward_calendar": calendar["calendar_bindings"],
                      "accepted_v4_04_contracts": json.loads((ROOT / accepted_paths[3]).read_text(encoding="utf-8"))["contract_bindings"],
                      "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"}
    write(OUT / "V4_05_R3_ACCEPTED_INPUT_MANIFEST.json", input_manifest)
    start = datetime.now(timezone.utc).isoformat()
    run = subprocess.run(COMMAND.split(), cwd=ROOT, capture_output=True, text=True)
    end = datetime.now(timezone.utc).isoformat()
    match = re.search(r"(\d+) passed, (\d+) skipped", run.stdout)
    if run.returncode or not match:
        raise RuntimeError(run.stdout + run.stderr)
    tests = {}
    for group in ("v4_01", "v4_02", "v4_03", "v4_04", "v4_05", "v4_joint", "v4_phase0"):
        for path in sorted((ROOT / "tests" / group).rglob("test_*.py")):
            tests[path.relative_to(ROOT).as_posix()] = sha(path)
    runtime = {"contract_id": "V4_05_R3_RUNTIME_TEST_RECEIPT_V1", "implementation_commit": IMPLEMENTATION,
               "exact_command": COMMAND, "started_at_utc": start, "ended_at_utc": end,
               "passed": int(match.group(1)), "failed": 0, "skipped": int(match.group(2)), "exit_code": run.returncode,
               "test_file_hashes": tests, "runtime_versions": {"python": sys.version, "pytest": pytest.__version__, "platform": platform.platform()},
               "pytest_summary": run.stdout.strip().splitlines()[-1]}
    write(OUT / "V4_05_R3_RUNTIME_TEST_RECEIPT.json", runtime)
    closure = """# V4-05 Replay Gate A R3 closure

- Stage contract: V4-05 Replay Gate A R3, target 2026-09-28, delayed formal publication under accepted go-forward PIT amendment.
- Evidence: target-coordinate history, official schedule, RAW/QFQ periods, Pure-Core and relative factors, equal-weight market reference, target market axes, full-market Core Profile, two-run determinism, candidate revision idempotency, eight executable temporal negatives, independent postcheck and formal runtime receipt. See `V4_05_R3_STAGE_CANDIDATE_MANIFEST.json` for hashes.
- Acceptance result: `V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R3`, scoped to `CURRENT_FORWARD_STOCK_CORE`; 5222 profiles retained. Prior-RPS delta, target breadth/stress and market UI remain field-local UNKNOWN. Historical AS_RECORDED adjusted price stays `BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`. No V4-05 Accepted Head is issued.
- Next stage: independent external audit of this scoped candidate. V4-06/V4-07/V4-08 remain unauthorized.
"""
    (OUT / "V4_05_R3_CLOSURE.md").write_bytes(closure.encode("utf-8"))
    artifacts = {name: {"sha256": sha(OUT / name), "byte_count": (OUT / name).stat().st_size} for name in REQUIRED}
    manifest = {"contract_id": "V4_05_R3_STAGE_CANDIDATE_MANIFEST_V1", "status": "V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R3",
                "implementation_commit": IMPLEMENTATION, "artifacts": artifacts, "external_acceptance": "PENDING",
                "data_factor_replay_pass": {"scope": "CURRENT_FORWARD_STOCK_CORE", "status": "DEGRADED_PASS"},
                "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE", "tdx_root_write_count": 0,
                "stage_record": {"stage_contract": "V4_05_REPLAY_GATE_A_R3", "evidence": "R3 hash-bound daily, calendar, period, factor, market, profile, deterministic, temporal, postcheck and runtime receipts", "acceptance_result": "DEGRADED_PASS_CURRENT_FORWARD_STOCK_CORE_CANDIDATE", "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R3"}}
    write(OUT / "V4_05_R3_STAGE_CANDIDATE_MANIFEST.json", manifest)
    print(runtime["pytest_summary"], manifest["status"])


if __name__ == "__main__":
    main()
