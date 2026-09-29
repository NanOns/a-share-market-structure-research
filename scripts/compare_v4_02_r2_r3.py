"""Exact business-field comparison of R2 and R3 candidates."""

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/v4_02/staging"
FIELDS = ("security_id", "source_security_key", "raw_ohlc", "qfq_ohlc", "adjusted_quality",
          "blocking_event_categories", "visible_effective_event_set_digest")


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return {r["source_security_key"]: r for r in map(json.loads, stream)}


def main():
    old = rows(BASE / "V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R2.jsonl.gz")
    new = rows(BASE / "V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz")
    changes = [{"key": key, "fields": [field for field in FIELDS if old[key][field] != new[key][field]]}
               for key in sorted(old.keys() & new.keys()) if any(old[key][field] != new[key][field] for field in FIELDS)]
    lineage = sorted(set(new[next(iter(new))]) - set(old[next(iter(old))]))
    result = {"contract_id": "V4_02_GO_FORWARD_R2_R3_DIFF_R3", "status": "PASS" if not changes and old.keys() == new.keys() else "BLOCKED_UNEXPECTED_BUSINESS_DIFF",
              "r2_rows": len(old), "r3_rows": len(new), "added_keys": sorted(new.keys() - old.keys()),
              "removed_keys": sorted(old.keys() - new.keys()), "business_changes": changes,
              "new_lineage_fields": lineage,
              "old_lineage_value": old[next(iter(old))]["knowledge_lineage"],
              "new_lineage_value": new[next(iter(new))]["knowledge_lineage"]}
    path = ROOT / "reports/v4_02/V4_02_GO_FORWARD_R2_R3_DIFF_R3.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["status"], len(old), len(new), len(changes))


if __name__ == "__main__":
    main()
