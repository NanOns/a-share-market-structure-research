from __future__ import annotations

"""Build candidate stable entity and symbol-alias identities for V4-01 R5."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.security_entity_identity import bao_source_entity, bse_alias_entity  # noqa: E402

CODE = re.compile(r"^(SH|SZ|BJ)\.([0-9]{6})$", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def board_for(exchange: str, code: str) -> str:
    number = code[-6:]
    if exchange == "SH" and number.startswith(("688", "689")):
        return "STAR"
    if exchange == "SZ" and number.startswith(("300", "301")):
        return "CHINEXT"
    if exchange == "BJ":
        return "BEIJING"
    return "MAIN"


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lifecycle-facts", default="reports/v4_01/baostock_lifecycle_facts_R4_20260925.json")
    ap.add_argument("--source-selection", default="reports/v4_01/canonical_source_selection_R4_20260925.json")
    ap.add_argument("--bse-source", default="data/v4/artifact_store/v4_01/bse_security_lifecycle_candidate_R5_20260925.json")
    ap.add_argument("--output", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    ap.add_argument("--receipt", default="reports/v4_01/security_entity_map_receipt_R5_20260925.json")
    args = ap.parse_args()

    fact_path, selection_path, bse_path = (ROOT / args.lifecycle_facts, ROOT / args.source_selection, ROOT / args.bse_source)
    facts_doc = json.loads(fact_path.read_text(encoding="utf-8"))
    selection_doc = json.loads(selection_path.read_text(encoding="utf-8"))
    bse_doc = json.loads(bse_path.read_text(encoding="utf-8"))
    source_keys = sorted({str(row["source_security_key"]).upper() for row in selection_doc["segments"]})
    facts = {row["source_security_key"].upper(): row for row in facts_doc["facts"]}
    type1 = {key: row for key, row in facts.items() if row.get("security_type_provider") == "1"}

    bse_aliases: dict[str, dict[str, object]] = {}
    bse_rows = bse_doc["records"]
    bse_cutover = bse_doc["code_cutover_date"]
    for row in bse_rows:
        entity = bse_alias_entity(row["old_code"], row["new_code"], row["reported_listing_date"])
        old_symbol, new_symbol = entity["old_symbol"], entity["new_symbol"]
        base = {"security_id": entity["security_id"], "lifecycle_entity_id": entity["security_id"],
                "exchange": "BJ", "security_type": "A_STOCK", "board": "BEIJING",
                "list_date": row["reported_listing_date"], "delist_date": None,
                "identity_quality": "BSE_OFFICIAL_ALIAS_CAPTURE_CANDIDATE",
                "source_contract_id": bse_doc["contract_id"],
                "source_revision_id": bse_doc["source_revision_id"], "security_name": row["security_name"]}
        bse_aliases[old_symbol] = {**base, "symbol": old_symbol,
                                   "symbol_effective_from": row["reported_listing_date"],
                                   "symbol_effective_to": "2025-10-08", "alias_role": "PREDECESSOR"}
        bse_aliases[new_symbol] = {**base, "symbol": new_symbol,
                                   "symbol_effective_from": bse_cutover,
                                   "symbol_effective_to": None, "alias_role": "CURRENT"}

    identity_rows: list[dict[str, object]] = []
    non_core: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []
    for source_key in source_keys:
        match = CODE.fullmatch(source_key)
        if not match:
            non_core.append({"source_security_key": source_key, "security_type": "UNIDENTIFIED_SOURCE_FILE",
                             "is_core_a_stock": False, "classification": "INVALID_SOURCE_SECURITY_KEY",
                             "evidence": "The source key does not satisfy the frozen exchange.code six-digit identity form."})
            continue
        exchange, digits = match.group(1).upper(), match.group(2)
        if exchange == "BJ":
            alias = bse_aliases.get(source_key)
            if alias:
                identity_rows.append({"source_security_key": source_key, **alias})
            elif digits.startswith(("810", "821", "899")):
                non_core.append({"source_security_key": source_key, "security_type": "NON_EQUITY_CANDIDATE",
                                 "is_core_a_stock": False, "classification": "BSE_NON_STOCK_CODE_FAMILY_CANDIDATE",
                                 "evidence": "Code family is outside six-digit BSE listed-stock code assignment; independent official instrument-type closure is pending."})
            else:
                unresolved.append({"source_security_key": source_key, "reason": "NO_BSE_OFFICIAL_LIFECYCLE_OR_ALIAS_RECORD_CAPTURED"})
            continue
        fact = type1.get(source_key)
        if fact:
            resolved = bao_source_entity(exchange, source_key, fact.get("listed_from"))
            if resolved["security_id"]:
                identity_rows.append({"source_security_key": source_key, "security_id": resolved["security_id"],
                                      "lifecycle_entity_id": resolved["security_id"], "exchange": exchange,
                                      "symbol": source_key, "symbol_effective_from": fact["listed_from"],
                                      "symbol_effective_to": fact.get("listed_to_provider_reported"),
                                      "list_date": fact["listed_from"],
                                      "delist_date": fact.get("listed_to_provider_reported"),
                                      "security_type": "A_STOCK", "board": board_for(exchange, digits),
                                      "identity_quality": "BAOSTOCK_TYPE1_LISTING_ANCHOR_CANDIDATE",
                                      "source_contract_id": "BAOSTOCK_LIFECYCLE_FACTS_R5_V1",
                                      "source_revision_id": facts_doc["source_revision_id"],
                                      "provider_status_observed": fact.get("provider_status_observed")})
                continue
        provider_fact = facts.get(source_key)
        if provider_fact and provider_fact.get("security_type_provider") not in (None, "1"):
            non_core.append({"source_security_key": source_key,
                             "security_type": provider_fact.get("security_type_provider"),
                             "is_core_a_stock": False, "classification": "BAOSTOCK_NON_A_STOCK_TYPE",
                             "evidence": "BaoStock query_stock_basic provider type is not 1."})
            continue
        unresolved.append({"source_security_key": source_key, "reason": "NO_ACCEPTED_STABLE_IDENTITY_OR_ASSET_TYPE_FACT"})

    security_to_symbols: dict[str, set[str]] = {}
    seen_alias: dict[str, str] = {}
    for item in identity_rows:
        security_to_symbols.setdefault(str(item["security_id"]), set()).add(str(item["symbol"]))
        symbol = str(item["symbol"])
        owner = seen_alias.setdefault(symbol, str(item["security_id"]))
        if owner != item["security_id"]:
            raise ValueError("SYMBOL_ALIAS_RESOLVES_TO_MULTIPLE_ENTITIES:" + symbol)
    by_id: dict[str, set[str]] = {}
    for row in identity_rows:
        by_id.setdefault(str(row["security_id"]), set()).add(str(row["source_security_key"]))
    source_key_to_id = {str(row["source_security_key"]): str(row["security_id"]) for row in identity_rows}

    bse_old_new_checks = []
    source_set = set(source_keys)
    for row in bse_rows:
        old_symbol, new_symbol = "BJ." + row["old_code"], "BJ." + row["new_code"]
        old_id, new_id = source_key_to_id.get(old_symbol), source_key_to_id.get(new_symbol)
        if old_symbol in source_set or new_symbol in source_set:
            bse_old_new_checks.append({"old_symbol": old_symbol, "new_symbol": new_symbol,
                                      "same_security_id": bool(old_id and old_id == new_id),
                                      "old_in_source": old_symbol in source_set,
                                      "new_in_source": new_symbol in source_set})
    duplicate_symbol_reuse = [symbol for symbol, ids in ((s, {str(x["security_id"]) for x in identity_rows if x["symbol"] == s})
                                for s in seen_alias) if len(ids) > 1]
    doc = {"contract_id": "SECURITY_ENTITY_IDENTITY_V1", "version": "1.0.0",
           "status": "CANDIDATE_ACCEPTANCE_PENDING", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "identity_rule": "source_security_key is an alias, never security_id; stable entity identity includes exchange, lifecycle anchor and listing date",
           "inputs": {"lifecycle_facts_sha256": sha256_file(fact_path), "source_selection_sha256": sha256_file(selection_path),
                      "bse_source_sha256": sha256_file(bse_path), "bse_records_sha256": bse_doc["records_sha256"]},
           "records": identity_rows, "non_core_candidates": non_core, "unresolved": unresolved,
           "summary": {"source_key_count": len(source_keys), "stable_identity_rows": len(identity_rows),
                       "unique_security_ids": len(by_id), "non_core_candidate_count": len(non_core),
                       "unresolved_count": len(unresolved), "bj_source_key_count": sum(x.startswith("BJ.") for x in source_keys),
                       "bj_alias_source_key_resolved_count": sum(x["source_security_key"].startswith("BJ.") for x in identity_rows),
                       "bj_unresolved_count": sum(x["source_security_key"].startswith("BJ.") for x in unresolved),
                       "core_a_stock_unexplained_count": sum(x["source_security_key"].startswith(("SH.", "SZ.")) for x in unresolved),
                       "duplicate_symbol_reuse_conflicts": duplicate_symbol_reuse,
                       "bse_alias_pairs_touched": len(bse_old_new_checks),
                       "bse_alias_pairs_same_identity": sum(x["same_security_id"] for x in bse_old_new_checks)},
           "bse_alias_pair_checks": bse_old_new_checks,
           "acceptance_limitations": ["BSE official page bytes were blocked by HTTP 403; extracted official-page search rendering is a candidate, not a verifiable primary-file digest.",
                                      "100 unmatched BJ.920xxx stock-like keys require official listing-date evidence.",
                                      "17 unmatched BJ.810/821/899 keys remain non-equity candidates pending independent instrument-type closure."],
           "execution_identity": {"input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                  "script_sha256": sha256_file(Path(__file__))}}
    output_path, receipt_path = ROOT / args.output, ROOT / args.receipt
    atomic_json(output_path, doc)
    receipt = {key: value for key, value in doc.items() if key not in {"records", "non_core_candidates", "unresolved", "bse_alias_pair_checks"}}
    receipt["status"] = "BLOCKED" if unresolved or non_core else "CANDIDATE_ACCEPTANCE_PENDING"
    receipt["output"] = {"path": args.output, "sha256": sha256_file(output_path), "record_count": len(identity_rows)}
    atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], **doc["summary"], "receipt": args.receipt}, ensure_ascii=False))
    return 0 if not unresolved and not non_core else 2


if __name__ == "__main__":
    raise SystemExit(main())
