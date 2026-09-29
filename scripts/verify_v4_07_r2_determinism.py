from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import sys
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


def main() -> int:
    stamp = "2026-09-30T00:00:00Z"
    with tempfile.TemporaryDirectory(prefix="v4-07-r2-determinism-") as temporary:
        temp_root = Path(temporary)
        first = run_accepted_candidate(
            ROOT,
            temp_root / "first.jsonl.gz",
            created_at=stamp,
            accepted_inputs_root=ACCEPTED_ROOT,
        )
        second = run_accepted_candidate(
            ROOT,
            temp_root / "second.jsonl.gz",
            created_at=stamp,
            accepted_inputs_root=ACCEPTED_ROOT,
        )
    if first["logical_digest"] != second["logical_digest"]:
        raise AssertionError("R2 logical digest changed across identical accepted contexts")
    if first["artifact_sha256"] != second["artifact_sha256"]:
        raise AssertionError("R2 artifact bytes changed across identical timestamps and contexts")
    if first["source_bindings"] != second["source_bindings"] or first["row_count"] != second["row_count"]:
        raise AssertionError("R2 accepted source context changed across fresh loads")
    report = {
        "contract_id": "V4_07_R2_DETERMINISM_VERIFICATION_V1",
        "status": "PASS_IDENTICAL_CONTEXT_REPLAY",
        "runs": 2,
        "created_at": stamp,
        "row_count": first["row_count"],
        "source_bindings_identical": True,
        "logical_digests": [first["logical_digest"], second["logical_digest"]],
        "artifact_sha256_values": [first["artifact_sha256"], second["artifact_sha256"]],
        "accepted_inputs_root": str(ACCEPTED_ROOT),
        "temporary_outputs_removed": True,
        "next_stage": "V4_07_R2_INDEPENDENT_POSTCHECK_AND_EXTERNAL_REVIEW",
    }
    output = ROOT / "reports/v4_07/V4_07_R2_DETERMINISM_VERIFICATION.json"
    atomic_json(output, report)
    print(json.dumps({"status": report["status"], "row_count": report["row_count"], "logical_digest": first["logical_digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
