"""Capability-scoped V4-05 R2 gate over the separately accepted forward input."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "reports/v4_05"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(name: str, value: dict) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> None:
    promotion = json.loads((ROOT / "reports/v4_joint/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json").read_text(encoding="utf-8"))
    if promotion["status"] != "PASS":
        raise ValueError("promotion gate not passed")
    head_path = ROOT / "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json"
    head = json.loads(head_path.read_text(encoding="utf-8"))
    global_head = json.loads((ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json").read_text(encoding="utf-8"))
    if global_head["v4_02_go_forward_pit_binding"]["sha256"] != sha(head_path):
        raise ValueError("accepted amendment binding mismatch")
    source = ROOT / head["evidence_bindings"]["official_tdx_package"]["path"]
    if sha(source) != head["official_tdx_package_sha256"]:
        raise ValueError("official package mismatch")
    spec = importlib.util.spec_from_file_location("forward_r3_builder", ROOT / "scripts/build_v4_02_go_forward_adjusted_r3.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.OUT = OUT / "staging/V4_05_R2_FORWARD_DAILY_REPLAY.jsonl.gz"
    builder.RECEIPT = OUT / "V4_05_R2_FORWARD_DAILY_BUILD_RECEIPT.json"
    builder.SAMPLES = OUT / "V4_05_R2_FORWARD_DAILY_SAMPLES.json"
    builder.main()
    first = json.loads(builder.RECEIPT.read_text(encoding="utf-8"))
    builder.main()
    second = json.loads(builder.RECEIPT.read_text(encoding="utf-8"))
    deterministic = first["logical_digest"] == second["logical_digest"] == head["logical_digest"]
    rows = [json.loads(line) for line in gzip.open(builder.OUT, "rt", encoding="utf-8")]
    if len(rows) != 5222 or any(row["max_source_trade_date"] > 20260928 for row in rows):
        raise ValueError("target row count or source date failed")
    counts = second["row_counts"]
    if counts["ADJUSTED_READY"] != 5195 or counts["ADJUSTED_UNAVAILABLE_NO_T0_RAW"] != 12 or counts["ADJUSTED_UNAVAILABLE_UNSUPPORTED_OR_UNKNOWN_EVENT"] != 15:
        raise ValueError("quality propagation failed")
    write("V4_05_R2_ACCEPTED_INPUT_MANIFEST.json", {"contract_id": "V4_05_R2_ACCEPTED_INPUT_MANIFEST_V1", "target_trade_date": "2026-09-28", "publication_mode": head["publication_mode"], "accepted_heads": {name: {"path": name, "sha256": sha(ROOT / name)} for name in ("data/v4/V4_01_ACCEPTED_HEAD.json", "data/v4/V4_02_ACCEPTED_HEAD.json", "data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json", "data/v4/V4_04_ACCEPTED_HEAD.json", "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json")}, "source_package": head["evidence_bindings"]["official_tdx_package"], "gbbq": head["evidence_bindings"]["gbbq_snapshot"]})
    write("V4_05_R2_SOURCE_IDENTITY.json", {"gate": "G01", "status": "PASS", "official_package_sha256": sha(source), "formal_publication_at": rows[0]["formal_publication_at"], "max_source_trade_date": max(row["max_source_trade_date"] for row in rows), "future_raw_rows": 0})
    write("V4_05_R2_UNIVERSE_IDENTITY.json", {"gate": "G02", "status": "PASS_CURRENT_FORWARD", "candidate_entities": len(rows), "actual_target_bars": counts["RAW_READY"], "no_target_bar": counts["ADJUSTED_UNAVAILABLE_NO_T0_RAW"], "identity_evidence": "reports/v4_02/V4_02_GO_FORWARD_UNIVERSE_CANDIDATE_R3.json", "code_change_evidence": "reports/v4_02/V4_02_GO_FORWARD_ADJUSTMENT_SAMPLES_R3.json"})
    write("V4_05_R2_ADJUSTMENT_REPRODUCIBILITY.json", {"gate": "G03", "current_forward_status": "PASS", "historical_as_recorded_status": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE", "ready": counts["ADJUSTED_READY"], "unknown": 27, "replay_digest": second["logical_digest"]})
    write("V4_05_R2_DAILY_DETERMINISM.json", {"gate": "G04", "status": "PASS" if deterministic else "FAIL", "first_digest": first["logical_digest"], "second_digest": second["logical_digest"], "accepted_digest": head["logical_digest"], "row_count": len(rows), "max_source_trade_date": max(row["max_source_trade_date"] for row in rows)})
    if not deterministic:
        raise ValueError("daily replay drift")
    print("G01-G04 PASS; downstream capability gates pending")


if __name__ == "__main__":
    main()
