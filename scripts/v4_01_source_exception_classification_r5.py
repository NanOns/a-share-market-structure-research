from __future__ import annotations

"""Classify every retained R4 source-file exception against V4-01 scope."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, RequestBudget, _atomic_json  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_classification(key: str, relative_path: str) -> tuple[str, str] | None:
    if not key:
        return "INVALID_SOURCE_SECURITY_KEY", "Provider exchange.code symbol grammar rejects the non-six-digit TDX filename."
    exchange, code = key.split(".", 1)
    if exchange == "SH" and code.startswith("880"):
        return "NON_CORE_INDUSTRY_INDEX_CODE_FAMILY", "TDX SH.880xxx instrument-family candidate; BaoStock basic catalogue returned no A-stock row."
    if exchange == "SH" and code.startswith("999"):
        return "NON_CORE_SPECIAL_INDEX_CODE_FAMILY", "TDX SH.999xxx special/index instrument-family candidate; BaoStock basic catalogue returned no A-stock row."
    if exchange == "SZ" and code.startswith("399"):
        return "NON_CORE_INDEX", "BaoStock provider type=2 identifies an index, not an A-stock lifecycle entity."
    if exchange == "SZ" and code.startswith("13"):
        return "NON_CORE_CONVERTIBLE_BOND_CODE_FAMILY", "SZ.13xxxx is a convertible-bond code-family candidate; not an A-stock identity."
    if exchange == "SZ" and code.startswith("20"):
        return "NON_CORE_B_SHARE_CODE_FAMILY", "SZ.20xxxx identifies a B-share instrument family, not a mainland A-stock."
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-selection", default="reports/v4_01/canonical_source_selection_R4_20260925.json")
    parser.add_argument("--lifecycle-facts", default="reports/v4_01/baostock_lifecycle_facts_R4_20260925.json")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_01/source_exception_classification_R5_20260925.json")
    args = parser.parse_args()
    selection_path, facts_path = ROOT / args.source_selection, ROOT / args.lifecycle_facts
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    facts_doc = json.loads(facts_path.read_text(encoding="utf-8"))
    facts = {row["source_security_key"].upper(): row for row in facts_doc["facts"]}
    exceptions = selection.get("source_exceptions", [])
    unresolved_types = {}
    for item in exceptions:
        key = item.get("source_security_key")
        if key and key.upper() not in facts and key.upper() not in unresolved_types:
            unresolved_types[key.upper()] = None

    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(value.get("count", 0)) for value in before.get("by_shanghai_date", {}).values())
    failures = {}
    if unresolved_types:
        active_client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS", timeout=30)
        try:
            active_client.__enter__()
            for key in sorted(unresolved_types):
                rows = None
                for attempt in range(2):
                    try:
                        rows, meta = active_client.query_rows("query_stock_basic", "query_stock_basic",
                                                              code=key.lower(), max_rows=5, max_pages=1)
                        unresolved_types[key] = {"error_code": meta["error_code"], "row_count": len(rows),
                                                 "security_type_provider": rows[0].get("type") if rows else None,
                                                 "source_code_digest": hashlib.sha256("\n".join(r.get("code", "") for r in rows).encode()).hexdigest()}
                        break
                    except BaoStockError as exc:
                        if attempt == 0 and exc.provider_code == "10001001":
                            active_client.__exit__(type(exc), exc, exc.__traceback__)
                            active_client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS", timeout=30)
                            active_client.__enter__()
                            continue
                        unresolved_types[key] = {"error_code": getattr(exc, "provider_code", None), "row_count": None,
                                                 "security_type_provider": None}
                        failures[key] = str(exc)[:120]
                        break
        except BaoStockError as exc:
            failures["SESSION"] = str(exc)[:120]
        finally:
            if active_client.logged_in:
                active_client.__exit__(None, None, None)

    classified = []
    for item in exceptions:
        key = str(item.get("source_security_key") or "").upper()
        path = str(item.get("relative_path", ""))
        fact = facts.get(key, {})
        probe = unresolved_types.get(key)
        provider_type = fact.get("security_type_provider") or (probe or {}).get("security_type_provider")
        rationale = code_classification(key, path)
        if provider_type and provider_type != "1":
            classification, evidence = "NON_CORE_CONFIRMED_BY_BAOSTOCK_TYPE", f"BaoStock type={provider_type}; listing fact source revision {facts_doc['source_revision_id']} or same-session direct probe."
            security_type = f"BAOSTOCK_TYPE_{provider_type}"
            final_disposition = "EXCLUDE_FROM_CORE_A_STOCK_SOURCE_SELECTION"
            acceptance_status = "CLASSIFIED_NONCORE"
        elif rationale:
            classification, evidence = rationale
            security_type = classification
            final_disposition = "EXCLUDE_FROM_CORE_A_STOCK_SOURCE_SELECTION"
            acceptance_status = "CLASSIFIED_NONCORE_CANDIDATE"
        else:
            classification = "UNRESOLVED_SOURCE_EXCEPTION"
            evidence = "No accepted provider lifecycle type or verified instrument-family evidence."
            security_type = "UNKNOWN"
            final_disposition = "RETAIN_UNRESOLVED"
            acceptance_status = "BLOCKED"
        classified.append({"source_security_key": key or None, "source_family": item.get("source_family"),
                           "relative_path": path, "source_sha256": item.get("sha256"),
                           "validation_reason": item.get("reason"), "validation_errors": item.get("errors", []),
                           "security_type": security_type, "historical_lifecycle_type": provider_type,
                           "is_core_a_stock": provider_type == "1", "classification": classification,
                           "evidence": evidence, "provider_probe": probe,
                           "consumer_impact": "Excluded from the selected research A-stock series; raw archive row/file remains preserved.",
                           "final_disposition": final_disposition, "acceptance_status": acceptance_status})
    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(value.get("count", 0)) for value in after.get("by_shanghai_date", {}).values())
    unexplained_core = sum(row["acceptance_status"] == "BLOCKED" or row["is_core_a_stock"] for row in classified)
    candidate_count = sum(row["acceptance_status"] == "CLASSIFIED_NONCORE_CANDIDATE" for row in classified)
    doc = {"stage": "V4-01-SOURCE-EXCEPTION-CLASSIFICATION-R5",
           "contract_id": "V4_01_SOURCE_EXCEPTION_CLASSIFICATION_V1",
           "version": "1.0.0", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "status": "PASS" if len(classified) == 38 and unexplained_core == 0 and candidate_count == 0 else "BLOCKED",
           "stage_completion_authorized": False,
           "inputs": {"source_selection_path": args.source_selection, "source_selection_sha256": sha256_file(selection_path),
                      "lifecycle_facts_path": args.lifecycle_facts, "lifecycle_facts_sha256": sha256_file(facts_path)},
           "summary": {"exception_row_count": len(classified),
                       "unique_source_exception_keys": len({row["source_security_key"] for row in classified}),
                       "provider_type_verified_count": sum(row["acceptance_status"] == "CLASSIFIED_NONCORE" for row in classified),
                       "code_family_candidate_count": candidate_count,
                       "core_a_stock_unexplained_exception_count": unexplained_core,
                       "source_exception_rows_retained": len(classified)},
           "blockers": (["SOURCE_EXCEPTION_ROWS_UNEXPLAINED_OR_CORE_A_STOCK"] if unexplained_core else [])
                       + (["SOURCE_EXCEPTION_CODE_FAMILY_CANDIDATES_NOT_INDEPENDENTLY_VERIFIED"] if candidate_count else []),
           "request_budget": {"before_total_count": before_count, "after_total_count": after_count,
                              "request_count_delta": after_count - before_count, "soft_cap": 40_000, "hard_cap": 45_000,
                              "provider_limit": 50_000},
           "failures": failures, "records": classified,
           "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                  "script_sha256": sha256_file(Path(__file__))},
           "next_stage": "V4_01_FORMAL_IDENTITY_LIFECYCLE_AND_HISTORICAL_UNIVERSE_R5"}
    _atomic_json(ROOT / args.receipt, doc)
    print(json.dumps({"status": doc["status"], **doc["summary"], "request_count_delta": after_count - before_count,
                      "receipt": args.receipt}, ensure_ascii=False))
    return 0 if doc["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
