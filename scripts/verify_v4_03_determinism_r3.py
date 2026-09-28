"""Replay the five R3 deliverable families twice against unchanged frozen inputs."""

import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/v4_03/V4_03_DETERMINISM_REPLAY_R3.json"
CASES = [
    ("prior_rps", "scripts.build_v4_03_prior_rps_staging", "reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json"),
    ("market_path", "scripts.run_v4_03_market_path_candidate", "reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz", "--full-history"),
    ("full_scope", "scripts.run_v4_03_full_scope_candidate", "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz", "--r3"),
    ("market_regime", "scripts.run_v4_03_market_regime_native_r3", "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"),
    ("contract_vectors", "scripts.verify_v4_03_ast_golden_vectors_r3", "reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json"),
]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=[case[0] for case in CASES])
    args = parser.parse_args()
    results = json.loads(OUTPUT.read_text(encoding="utf-8"))["results"] if args.only and OUTPUT.exists() else {}
    for name, module, path, *options in CASES:
        if args.only and name != args.only:
            continue
        artifact = ROOT / path
        before = sha(artifact) if artifact.exists() else None
        digests = []
        for attempt in range(2):
            subprocess.run([sys.executable, "-m", module, *options], cwd=ROOT, check=True,
                           stdout=subprocess.DEVNULL)
            digests.append(sha(artifact))
            print(f"{name} replay {attempt + 1}/2: {digests[-1]}", flush=True)
        results[name] = {"artifact_path": path, "baseline_sha256": before, "replay_sha256": digests,
                         "deterministic": (before is None or before == digests[0]) and digests[0] == digests[1]}
    status = "PASS" if all(x["deterministic"] for x in results.values()) else "FAIL"
    report = {"contract_id": "V4_03_DETERMINISM_REPLAY_R3", "status": status,
              "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
              "runs_per_artifact": 2, "results": results, "stage_acceptance": "NOT_GRANTED"}
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    if status != "PASS":
        raise RuntimeError("R3 artifact determinism mismatch")
    print(json.dumps({"status": status, "artifact_families": len(results)}))


if __name__ == "__main__":
    main()
