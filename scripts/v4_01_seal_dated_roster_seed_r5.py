from __future__ import annotations

"""Recover complete per-day records from an interrupted gzip stream safely."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-receipt", default="reports/v4_01/historical_evaluable_universe_receipt_R4_20260925.json")
    parser.add_argument("--partial", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R5_20260925.jsonl.gz.partial")
    parser.add_argument("--output", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R5_seed_00.jsonl.gz")
    parser.add_argument("--receipt", default="reports/v4_01/baostock_dated_roster_shard_00_receipt_R5_20260925.json")
    args = parser.parse_args()
    candidate_path, partial_path = ROOT / args.candidate_receipt, ROOT / args.partial
    candidate = json.loads(candidate_path.read_text("utf-8"))
    sessions = [row["trade_date"] for row in candidate["daily_reconstructed_universe"]["days"]]
    records = []
    try:
        with gzip.open(partial_path, "rt", encoding="utf-8") as stream:
            for line in stream:
                records.append(json.loads(line))
    except (EOFError, OSError):
        # A missing trailer is expected if interruption occurred during a write.
        # Only complete JSON lines are recovered; every line is checked below.
        pass
    if not records or len(records) > len(sessions):
        raise SystemExit("ROSTER_SEED_HAS_NO_RECOVERABLE_RECORDS_OR_TOO_MANY_RECORDS")
    daily = []
    root = hashlib.sha256()
    total_rows = 0
    for index, record in enumerate(records):
        codes = record.get("source_codes", [])
        digest = hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest()
        if (record.get("trade_date") != sessions[index] or record.get("contract_id") != "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1"
                or codes != sorted(set(codes)) or record.get("row_count") != len(codes) or record.get("codes_sha256") != digest):
            raise SystemExit(f"ROSTER_SEED_RECORD_INVALID:{index}")
        daily.append({"trade_date": record["trade_date"], "row_count": len(codes),
                      "page_count": record.get("page_count"), "codes_sha256": digest})
        root.update(f"{record['trade_date']}\0{len(codes)}\0{digest}\n".encode("ascii"))
        total_rows += len(codes)
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    os.close(fd)
    temp_path = Path(name)
    with gzip.open(temp_path, "wt", encoding="utf-8", newline="\n", compresslevel=6) as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    with temp_path.open("rb+") as stream:
        os.fsync(stream.fileno())
    os.replace(temp_path, output_path)
    receipt = {"stage": "V4-01-BAOSTOCK-DATED-ROSTER-SHARD-R5", "contract_id": "BAOSTOCK_DATED_ROSTER_SNAPSHOT_V1",
               "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "status": "BUILT", "stage_completion_authorized": False,
               "source": {"provider": "BaoStock", "method": "query_all_stock(day)", "auth_mode": "PUBLIC_ANONYMOUS",
                          "source_document": "https://www.baostock.com/mainContent?file=pythonAPI.md"},
               "input": {"candidate_receipt": args.candidate_receipt, "candidate_receipt_sha256": sha256(candidate_path),
                         "session_basis": candidate["formal_window"]["session_basis"], "first_session": sessions[0],
                         "last_session": daily[-1]["trade_date"], "session_count": len(records),
                         "full_session_count": len(sessions), "slice_start_index": 0,
                         "slice_end_index_exclusive": len(records), "recovered_complete_json_records_from_interrupted_partial": True},
               "output": {"path": args.output, "sha256": sha256(output_path), "byte_count": output_path.stat().st_size,
                          "format": "GZIP_JSONL", "total_roster_rows": total_rows, "daily_roster_digest_root": root.hexdigest()},
               "daily_counts": daily,
               "request_budget": {"ledger_path": None, "ledger_already_aggregated": True,
                                  "central_ledger": "reports/v4_baostock/request_ledger.json"},
               "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                      "script_sha256": sha256(Path(__file__))},
               "next_stage": "V4_01_EXACT_DATED_ROSTERS_R5"}
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "session_count": len(records), "total_rows": total_rows,
                      "output_sha256": receipt["output"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
