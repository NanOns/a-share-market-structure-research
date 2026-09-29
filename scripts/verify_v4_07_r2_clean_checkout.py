from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_ROOT = Path(os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()
sys.path.insert(0, str(ROOT))

from src.v4.base_seed import run_accepted_candidate  # noqa: E402


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay V4-07 R2 from a clean checkout into temporary storage.")
    parser.add_argument("--evidence", type=Path, required=True, help="Evidence output outside this clean checkout.")
    args = parser.parse_args()
    evidence_path = args.evidence.resolve()
    if evidence_path.is_relative_to(ROOT.resolve()):
        raise ValueError("clean-checkout evidence must be written outside the checkout under test")
    before_status = git_output("status", "--porcelain", "--untracked-files=all")
    if before_status:
        raise RuntimeError("clean-checkout replay started with a dirty working tree")
    head = git_output("rev-parse", "HEAD")
    receipt = json.loads((ROOT / "reports/v4_07/V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="v4-07-r2-clean-replay-") as temporary:
        replay = run_accepted_candidate(
            ROOT,
            Path(temporary) / "candidate.jsonl.gz",
            created_at="2026-09-30T00:00:00Z",
            accepted_inputs_root=ACCEPTED_ROOT,
        )
    if replay["logical_digest"] != receipt.get("logical_artifact_digest"):
        raise AssertionError("clean-checkout replay logical digest differs from sealed R2 receipt")
    if replay["artifact_sha256"] != receipt.get("artifact_sha256"):
        raise AssertionError("clean-checkout replay bytes differ from sealed R2 receipt")
    if replay["source_bindings"] != receipt.get("source_bindings"):
        raise AssertionError("clean-checkout accepted source context differs from sealed R2 receipt")
    after_status = git_output("status", "--porcelain", "--untracked-files=all")
    if after_status:
        raise RuntimeError("clean-checkout replay modified its checkout")
    report = {
        "contract_id": "V4_07_R2_CLEAN_CHECKOUT_VERIFICATION_V1",
        "status": "PASS_CLEAN_CHECKOUT_REPLAY",
        "checkout_head": head,
        "working_tree_clean_before": True,
        "working_tree_clean_after": True,
        "candidate_logical_digest": replay["logical_digest"],
        "candidate_artifact_sha256": replay["artifact_sha256"],
        "row_count": replay["row_count"],
        "accepted_inputs_root": str(ACCEPTED_ROOT),
        "temporary_replay_output_removed": True,
        "evidence_written_outside_checkout": str(evidence_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "next_stage": "V4_07_R2_INDEPENDENT_EXTERNAL_ACCEPTANCE",
    }
    atomic_json(evidence_path, report)
    print(json.dumps({"status": report["status"], "checkout_head": head, "logical_digest": replay["logical_digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
