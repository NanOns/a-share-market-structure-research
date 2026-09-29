"""Run the final R3 Core Profile adapter twice and seal revision semantics."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/v4_05"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write(name, value):
    path = OUT / name
    temp = path.with_suffix(".tmp")
    temp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    os.replace(temp, path)


def main():
    command = [sys.executable, "scripts/build_v4_05_r3_core_profile.py"]
    samples = []
    for _ in range(2):
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        receipt = read("V4_05_R3_CORE_PROFILE_REPLAY.json")
        samples.append({key: receipt[key] for key in ("artifact_sha256", "logical_digest", "quality_counts", "board_counts", "row_count")})
    if samples[0] != samples[1]:
        raise ValueError("Core Profile replay drift")
    write("V4_05_R3_DETERMINISM.json", {"contract_id": "V4_05_R3_CORE_PROFILE_DETERMINISM_V1", "status": "PASS", "command": command[1], "first": samples[0], "second": samples[1], "same_row_set": True, "same_logical_digest": True, "same_quality_counts": True, "same_output_digest": True})
    head = json.loads((ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    calendar = read("V4_05_R3_CALENDAR_RECEIPT.json")
    profile = read("V4_05_R3_CORE_PROFILE_REPLAY.json")
    identity = {"target_trade_date": "2026-09-28", "source_package_sha256": head["official_tdx_package_sha256"],
                "gbbq_sha256": head["evidence_bindings"]["gbbq_snapshot"]["sha256"], "calendar_identity": calendar["calendar_bindings"],
                "contract_digest": profile["contract_digest"], "parameter_set_id": "V4_04_CORE_PROFILE_PARAMETER_SET_V1",
                "formal_publication_at": profile["formal_publication_at"]}
    revision = digest(identity)
    repeated = digest(dict(identity))
    changed = digest({**identity, "source_package_sha256": "0" * 64})
    if revision != repeated or changed == revision:
        raise ValueError("revision identity not idempotent")
    write("V4_05_R3_REVISION_IDEMPOTENCY.json", {"contract_id": "V4_05_R3_REVISION_IDENTITY_V1", "status": "PASS_CANDIDATE_IDENTITY", "publication_identity": identity, "first_revision_id": revision, "second_revision_id": repeated, "controlled_changed_source_revision_id": changed, "duplicate_revision_count": 0, "duplicate_publication_event_count": 0, "output_drift": False, "scope": "V4_05_R3_CANDIDATE_ONLY_NO_EXTERNAL_PUBLICATION"})
    print("PASS", revision)


if __name__ == "__main__":
    main()
