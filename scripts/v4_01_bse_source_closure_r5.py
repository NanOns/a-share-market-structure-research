from __future__ import annotations

"""Account for every retained BJ TDX source key without inventing identities."""

import argparse
import hashlib
import json
import subprocess
import sys
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
    parser.add_argument("--selection", default="reports/v4_01/canonical_source_selection_R4_20260925.json")
    parser.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    parser.add_argument("--receipt", default="reports/v4_01/bse_source_closure_receipt_R5_20260925.json")
    args = parser.parse_args()
    selection_path, map_path = ROOT / args.selection, ROOT / args.identity_map
    selection, identity = json.loads(selection_path.read_text("utf-8")), json.loads(map_path.read_text("utf-8"))
    bj_keys = sorted({str(item["source_security_key"]).upper() for item in selection["segments"]
                      if str(item["source_security_key"]).upper().startswith("BJ.")})
    records = {str(row["source_security_key"]).upper(): row for row in identity.get("records", [])}
    noncore = {str(row["source_security_key"]).upper(): row for row in identity.get("non_core_candidates", [])}
    unresolved = {str(row["source_security_key"]).upper(): row for row in identity.get("unresolved", [])}
    rows = []
    for key in bj_keys:
        if key in records:
            fact = records[key]
            alias = fact.get("symbol_effective_to") is not None or fact.get("alias_role") == "PREDECESSOR"
            rows.append({"source_security_key": key, "disposition": "HISTORICAL_ALIAS" if alias else "MAPPED_STABLE_BSE_ENTITY",
                         "security_id": fact.get("security_id"), "list_date": fact.get("list_date"),
                         "symbol_effective_from": fact.get("symbol_effective_from"),
                         "symbol_effective_to": fact.get("symbol_effective_to"),
                         "evidence_status": fact.get("identity_quality"), "source_revision_id": fact.get("source_revision_id")})
        elif key in noncore:
            fact = noncore[key]
            rows.append({"source_security_key": key, "disposition": "NON_EQUITY_CANDIDATE",
                         "reason": fact.get("classification"), "evidence": fact.get("evidence"),
                         "evidence_status": "CANDIDATE_INDEPENDENT_TYPE_CLOSURE_PENDING"})
        elif key in unresolved:
            fact = unresolved[key]
            rows.append({"source_security_key": key, "disposition": "UNRESOLVED_WITH_EXPLICIT_REASON",
                         "reason": fact.get("reason"), "evidence_status": "OFFICIAL_LIFECYCLE_CAPTURE_MISSING"})
        else:
            rows.append({"source_security_key": key, "disposition": "UNEXPLAINED", "reason": "No identity, non-equity, or unresolved record."})
    counts = {name: sum(row["disposition"] == name for row in rows)
              for name in ("MAPPED_STABLE_BSE_ENTITY", "HISTORICAL_ALIAS", "NON_EQUITY_CANDIDATE",
                           "UNRESOLVED_WITH_EXPLICIT_REASON", "UNEXPLAINED")}
    unresolved_core = sum(row["disposition"] == "UNRESOLVED_WITH_EXPLICIT_REASON" and row["source_security_key"].startswith("BJ.920") for row in rows)
    doc = {"stage": "V4-01-BSE-SOURCE-CLOSURE-R5", "contract_id": "BSE_SECURITY_SOURCE_KEY_CLOSURE_V1",
           "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "status": "PASS" if len(rows) == 613 and counts["UNEXPLAINED"] == 0 and unresolved_core == 0 and counts["NON_EQUITY_CANDIDATE"] == 0 else "BLOCKED",
           "stage_completion_authorized": False,
           "source": {"official_mapping_url": "https://www.bse.cn/service/code_mapping.html",
                      "cutover_notice_url": "https://www.bse.cn/important_news/200026735.html",
                      "mapping_records_sha256": identity.get("inputs", {}).get("bse_records_sha256"),
                      "mapping_capture_acceptance": "OFFICIAL_INDEX_CAPTURE_CANDIDATE_ACCEPTANCE_PENDING"},
           "inputs": {"source_selection": args.selection, "source_selection_sha256": sha256(selection_path),
                      "identity_map": args.identity_map, "identity_map_sha256": sha256(map_path)},
           "summary": {"source_key_count": len(rows), **counts, "unresolved_core_membership_count": unresolved_core},
           "blockers": (["OFFICIAL_BSE_PRIMARY_CAPTURE_NOT_ACCEPTED"] if counts["MAPPED_STABLE_BSE_ENTITY"] + counts["HISTORICAL_ALIAS"] else [])
                       + (["BSE_CORE_STOCK_KEYS_WITHOUT_ACCEPTED_STABLE_IDENTITY"] if unresolved_core else [])
                       + (["BSE_NON_EQUITY_CANDIDATES_NOT_INDEPENDENTLY_VERIFIED"] if counts["NON_EQUITY_CANDIDATE"] else [])
                       + (["UNEXPLAINED_BJ_SOURCE_KEYS"] if counts["UNEXPLAINED"] else []),
           "records": rows,
           "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                  "script_sha256": sha256(Path(__file__))},
           "next_stage": "V4_01_EXACT_DATED_UNIVERSE_AND_FINAL_GATE_R5"}
    _atomic_json(ROOT / args.receipt, doc)
    print(json.dumps({"status": doc["status"], "summary": doc["summary"], "receipt": args.receipt}, ensure_ascii=False))
    return 0 if doc["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
