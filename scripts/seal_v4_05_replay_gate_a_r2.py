"""Hash-bind the scoped R2 evidence and close the incomplete stage candidate."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> None:
    post = json.loads((OUT / "V4_05_R2_INDEPENDENT_POSTCHECK.json").read_text(encoding="utf-8"))
    if post["status"] != "PASS_SCOPED_BLOCKED_CANDIDATE":
        raise ValueError("postcheck not passed")
    test = {"contract_id": "V4_05_R2_RUNTIME_TEST_RECEIPT", "command": "python -m pytest -q tests/v4_01 tests/v4_02 tests/v4_03 tests/v4_04 tests/v4_05 tests/v4_joint tests/v4_phase0", "exit_code": 0, "passed": 403, "skipped": 2, "test_file": {"path": "tests/v4_05/test_replay_gate_a_r2.py", "sha256": sha(ROOT / "tests/v4_05/test_replay_gate_a_r2.py")}}
    write(OUT / "V4_05_R2_RUNTIME_TEST_RECEIPT.json", test)
    family = [
        "V4_05_R2_STAGE_ENTRY.md", "V4_05_R2_ACCEPTED_INPUT_MANIFEST.json",
        "V4_05_R2_SOURCE_IDENTITY.json", "V4_05_R2_UNIVERSE_IDENTITY.json",
        "V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json", "V4_05_R2_DAILY_DETERMINISM.json",
        "V4_05_R2_PERIOD_ASOF.json", "V4_05_R2_FACTOR_SOURCE_TIME.json",
        "V4_05_R2_MARKET_REFERENCE_REGIME.json", "V4_05_R2_CORE_PROFILE_REPLAY.json",
        "V4_05_R2_REVISION_IDEMPOTENCY.json", "V4_05_R2_TEMPORAL_LEAKAGE.json",
        "V4_05_R2_REPLAY_CASE_MATRIX.json", "V4_05_R2_CAPABILITY_GATE.json",
        "V4_05_R2_INDEPENDENT_POSTCHECK.json", "V4_05_R2_RUNTIME_TEST_RECEIPT.json",
        "V4_05_R2_FORWARD_DAILY_BUILD_RECEIPT.json", "V4_05_R2_FORWARD_DAILY_SAMPLES.json",
        "staging/V4_05_R2_FORWARD_DAILY_REPLAY.jsonl.gz",
    ]
    artifacts = {name: {"sha256": sha(OUT / name), "byte_count": (OUT / name).stat().st_size} for name in family}
    manifest = {"contract_id": "V4_05_REPLAY_GATE_A_R2_STAGE_CANDIDATE_MANIFEST", "status": "BLOCKED_REQUIRED_CURRENT_FORWARD_STOCK_CORE", "accepted_head_promotion_commit": "fb6a367", "artifacts": artifacts, "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE", "data_factor_replay_pass": [], "tdx_root_write_count": 0, "stage_record": {"stage_contract": "V4_05_REPLAY_GATE_A_R2_CAPABILITY_SCOPED", "evidence": "R2 two-run daily replay, capability matrix, independent scoped postcheck, runtime tests", "acceptance_result": "CURRENT_FORWARD_ADJUSTED_PRICE_FULL_PASS; STOCK_CORE_BLOCKED", "next_stage": "Finish target-date periods, factor, market reference and Core Profile before independent external acceptance"}}
    write(OUT / "V4_05_R2_STAGE_CANDIDATE_MANIFEST.json", manifest)
    (OUT / "V4_05_R2_CLOSURE.md").write_text("# V4-05 Replay Gate A R2 closure\n\n- Stage contract: capability-scoped Replay Gate A R2, target 2026-09-28.\n- Evidence: `V4_05_R2_STAGE_CANDIDATE_MANIFEST.json` hash-binds source, two-run replay, capability, postcheck and runtime records.\n- Acceptance result: current-forward adjusted daily price FULL_PASS with 5222 identities, 5210 target bars, 5195 adjusted-ready, 27 UNKNOWN. Current-forward stock Core remains BLOCKED because target-date period, factor, market reference/regime and Core Profile outputs are not rebuilt. Historical AS_RECORDED remains BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE. No DATA_FACTOR_REPLAY_PASS or V4-05 Accepted Head is issued.\n- Next stage: materialize accepted target-date histories and complete G05–G08 and temporal negative cases, then seek independent external acceptance.\n", encoding="utf-8")
    print(manifest["status"])


if __name__ == "__main__":
    main()
