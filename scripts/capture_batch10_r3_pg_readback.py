"""Read back exact BATCH10-R3 D0 tokens using the restricted PG verifier."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src")]

RELEASES = {
    "2026-10-20": "283fec0eacc4035237a60f2c8dea77586be09dafa4b1b4df072e02c765ab7562",
    "2026-10-21": "f8c09d96f7200e2b1cab2b140393297b1fcc31511a97c3b6fa3e0970c5686430",
}


def load_dsn(root: Path) -> None:
    env = root / "config/.env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() in ("WORKBENCH_PG_DSN", "V4_NATIVE_PG_DSN", "V4_NATIVE_PG_READER_DSN"):
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    if not os.environ.get("V4_NATIVE_PG_DSN") and os.environ.get("WORKBENCH_PG_DSN"):
        os.environ["V4_NATIVE_PG_DSN"] = os.environ["WORKBENCH_PG_DSN"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.candidate_root.resolve(strict=True)
    load_dsn(root)
    from workbench_analysis.d0_source_seal_r2 import independent_pg_readback

    checks = {}
    for day, token in RELEASES.items():
        value = independent_pg_readback(day, token)
        checks[day] = {
            "token": token,
            "status": value.get("status"),
            "fact_rows": value.get("fact_rows"),
            "fact_digest_readback": value.get("fact_digest_readback"),
            "predicate_digest": value.get("predicate_digest"),
            "publication": value.get("publications"),
            "scenario_status_counts": value.get("scenario_status_counts"),
            "transaction_read_only": value.get("transaction_read_only"),
            "reader_current_user": value.get("reader_current_user"),
            "reason": value.get("reason"),
        }
    evidence = {
        "contract_id": "BATCH10_R3_D0_RESTRICTED_PG_READBACK_R1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": "market_research",
        "database_oid": 646711,
        "checks": checks,
        "no_write": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".tmp")
    tmp.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(args.output)
    print(json.dumps({"output": str(args.output), "checks": {day: {"status": x["status"], "fact_rows": x["fact_rows"], "transaction_read_only": x["transaction_read_only"]} for day, x in checks.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
