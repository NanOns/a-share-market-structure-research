"""Record the P07-02 real-input gate without inventing candidates."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    source = ROOT / "reports/upgrade_v3/P07-01_MEMBER_ROLES_DISTRIBUTION.json"
    prior = json.loads(source.read_text(encoding="utf-8"))
    counts = prior["roles"]["counts"]
    candidate_rows = int(counts.get("CURRENT_RESEARCH", 0)) + int(counts.get("EARLY_WATCH", 0))
    if candidate_rows:
        raise RuntimeError("P07_02_EXPECTS_EXPLICIT_ROLE_INPUT_BUILD")
    report = {
        "contract_id": "v3-p07-02-association-distribution-v1.0",
        "association_contract_id": "RESEARCH_ASSOCIATION_PREVIEW_1",
        "shortlist_contract_id": "RESEARCH_SHORTLIST_PREVIEW_1",
        "trade_date": prior["trade_date"],
        "input": {"source_report": str(source), "publication_id": prior["input"]["publication_id"], "membership_snapshot_id": prior["input"]["membership_snapshot_id"], "candidate_role_rows": candidate_rows},
        "distribution": {"association_rows": 0, "current_focus_rows": 0, "early_focus_rows": 0, "reason": "NO_CURRENT_OR_EARLY_ROLE_CANDIDATES_IN_BOUND_REAL_INPUT"},
        "policy": {"legacy_association_read": False, "legacy_candidate_read": False, "database_written": False, "tdx_modified": False, "effectiveness_claim": False},
    }
    output = ROOT / "reports/upgrade_v3/P07-02_ASSOCIATION_DISTRIBUTION.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temp = Path(name)
    try:
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    print(json.dumps({"status": "PASS", "output": str(output), "candidate_role_rows": candidate_rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
