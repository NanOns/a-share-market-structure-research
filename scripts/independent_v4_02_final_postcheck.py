from __future__ import annotations

"""Independent final readback of V4-02 staged components and atomic candidate."""

import argparse
import gzip
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R1.json")
    parser.add_argument("--out", default="reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R1.json")
    parser.add_argument("--universe", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_2_20260926.jsonl.gz")
    parser.add_argument("--calendar-receipt", default="reports/v4_02/V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json")
    parser.add_argument("--temporal-receipt", default="reports/v4_02/V4_02_SECTION_3C4_TEMPORAL_LEAKAGE_REPLAY_20260926.json")
    parser.add_argument("--period-receipt", default="reports/v4_02/V4_02_FORMAL_PERIODS_R6_2_20260926.json")
    parser.add_argument("--period-postcheck", default="reports/v4_02/V4_02_FORMAL_PERIODS_INDEPENDENT_POSTCHECK_20260926.json")
    parser.add_argument("--isst-receipt", default="reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json")
    parser.add_argument("--price-receipt", default="reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R1_20260926.json")
    args = parser.parse_args()
    manifest_path = ROOT / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    findings: list[str] = []
    component_hashes = {}
    for name, item in manifest.get("components", {}).items():
        path = ROOT / item["path"]
        if not path.is_file():
            findings.append("COMPONENT_MISSING:" + name)
            continue
        actual_sha, actual_bytes = sha(path), path.stat().st_size
        component_hashes[name] = actual_sha
        if actual_sha != item.get("sha256"):
            findings.append("COMPONENT_SHA256_MISMATCH:" + name)
        if actual_bytes != item.get("bytes"):
            findings.append("COMPONENT_BYTE_COUNT_MISMATCH:" + name)

    import duckdb
    db = duckdb.connect()
    parquet_checks = {}
    for name in ("RAW_CANONICAL_DAILY", "ADJUSTED_CANONICAL_DAILY", "FORMAL_WEEKLY", "FORMAL_MONTHLY"):
        item = manifest["components"][name]
        path = str(ROOT / item["path"]).replace("'", "''")
        try:
            result = db.execute(f"select count(*) from read_parquet('{path}')").fetchone()[0]
            schema = [row[0] for row in db.execute(f"describe select * from read_parquet('{path}')").fetchall()]
            parquet_checks[name] = {"row_count": int(result), "schema": schema}
            if item.get("row_count") is not None and int(item["row_count"]) != int(result):
                findings.append("PARQUET_ROW_COUNT_MISMATCH:" + name)
            if name in {"ADJUSTED_CANONICAL_DAILY", "FORMAL_WEEKLY", "FORMAL_MONTHLY"}:
                required = {"canonical_security_id", "source_security_key", "board_scope"}
                required |= ({"trade_date"} if name == "ADJUSTED_CANONICAL_DAILY" else
                             {"period_start_date", "period_end_date", "period_last_session", "asof_trade_date", "period_view", "period_status"})
                if not required.issubset(schema):
                    findings.append("PARQUET_REQUIRED_SCHEMA_MISSING:" + name)
                board_path = str(ROOT / item["path"]).replace("'", "''")
                boards = {row[0] for row in db.execute(f"select distinct board_scope from read_parquet('{board_path}')").fetchall()}
                parquet_checks[name]["boards"] = sorted(str(value) for value in boards if value is not None)
                if not boards.issubset({"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}):
                    findings.append("BSE_OR_UNKNOWN_BOARD_IN_REQUIRED_PARQUET:" + name)
                if boards != {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}:
                    findings.append("REQUIRED_BOARD_COVERAGE_MISSING:" + name)
        except Exception as exc:
            findings.append("PARQUET_READ_FAILED:" + name + ":" + type(exc).__name__)
    db.close()

    calendar = json.loads((ROOT / args.calendar_receipt).read_text(encoding="utf-8"))
    temporal = json.loads((ROOT / args.temporal_receipt).read_text(encoding="utf-8"))
    periods = json.loads((ROOT / args.period_receipt).read_text(encoding="utf-8"))
    period_post = json.loads((ROOT / args.period_postcheck).read_text(encoding="utf-8"))
    isst = json.loads((ROOT / args.isst_receipt).read_text(encoding="utf-8"))
    price = json.loads((ROOT / args.price_receipt).read_text(encoding="utf-8"))
    if calendar.get("status") != "FORMAL_MARKET_CALENDAR_PASS":
        findings.append("FORMAL_CALENDAR_NOT_ACCEPTED")
    if periods.get("status") != "FORMAL_PERIODS_CANDIDATE_PASS" or period_post.get("status") != "PASS":
        findings.append("PERIOD_OR_CLOSED_ASOF_POSTCHECK_FAILED")
    if temporal.get("status") != "BOUNDED_TEMPORAL_REPLAY_PASS" or temporal.get("case_count") != 8:
        findings.append("REV2_TEMPORAL_CASE_SET_NOT_PASS")
    if isst.get("session_count") != 786 or isst.get("query_receipt_count") != 786 or isst.get("membership_rows") != 4036121:
        findings.append("DATED_ISST_SCOPE_COUNTS_MISMATCH")
    if price.get("row_count") != 4036121:
        findings.append("PRICE_LIMIT_SCOPE_ROW_COUNT_MISMATCH")
    required_samples = {
        "SH_MAIN_NORMAL_SAMPLE", "SH_MAIN_RISK_WARNING_SAMPLE", "SZ_MAIN_NORMAL_SAMPLE", "SZ_MAIN_RISK_WARNING_SAMPLE",
        "CHINEXT_NORMAL_SAMPLE", "STAR_NORMAL_SAMPLE", "IPO_NO_LIMIT", "EX_RIGHT",
        "RULE_BOUNDARY_20260703_SH_MAIN", "RULE_BOUNDARY_20260706_SH_MAIN",
        "RULE_BOUNDARY_20260703_SZ_MAIN", "RULE_BOUNDARY_20260706_SZ_MAIN",
    }
    missing_samples = sorted(required_samples - set(price.get("samples", {})))
    if missing_samples:
        findings.append("PRICE_LIMIT_SAMPLE_SET_INCOMPLETE:" + ",".join(missing_samples))
    price_samples = price.get("samples", {})
    expected_rules = {
        "SH_MAIN_NORMAL_SAMPLE": "SSE_MAIN_NORMAL_20230704_V1",
        "SH_MAIN_RISK_WARNING_SAMPLE": None,
        "SZ_MAIN_NORMAL_SAMPLE": "SZSE_MAIN_NORMAL_20230704_V1",
        "SZ_MAIN_RISK_WARNING_SAMPLE": None,
        "CHINEXT_NORMAL_SAMPLE": "SZSE_GROWTH_NORMAL_20230704_V1",
        "STAR_NORMAL_SAMPLE": "SSE_STAR_NORMAL_20230704_V1",
        "RULE_BOUNDARY_20260703_SH_MAIN": "SSE_MAIN_RISK_WARNING_20230704_20260705_V1",
        "RULE_BOUNDARY_20260706_SH_MAIN": "SSE_MAIN_RISK_WARNING_20260706_V1",
        "RULE_BOUNDARY_20260703_SZ_MAIN": "SZSE_MAIN_RISK_WARNING_20230704_20260705_V1",
        "RULE_BOUNDARY_20260706_SZ_MAIN": "SZSE_MAIN_RISK_WARNING_20260706_V1",
    }
    sample_failures = []
    ratios = {
        "SSE_MAIN_NORMAL_20230704_V1": Decimal("0.10"),
        "SSE_MAIN_RISK_WARNING_20230704_20260705_V1": Decimal("0.05"),
        "SSE_MAIN_RISK_WARNING_20260706_V1": Decimal("0.10"),
        "SZSE_MAIN_NORMAL_20230704_V1": Decimal("0.10"),
        "SZSE_MAIN_RISK_WARNING_20230704_20260705_V1": Decimal("0.05"),
        "SZSE_MAIN_RISK_WARNING_20260706_V1": Decimal("0.10"),
        "SZSE_GROWTH_NORMAL_20230704_V1": Decimal("0.20"),
        "SSE_STAR_NORMAL_20230704_V1": Decimal("0.20"),
    }
    for sample_key, expected_rule in expected_rules.items():
        sample = price_samples.get(sample_key)
        if not sample:
            continue
        if expected_rule and sample.get("rule_id") != expected_rule:
            sample_failures.append(sample_key + ":RULE_ID")
            continue
        if sample_key.startswith("RULE_BOUNDARY_"):
            expected_day = "20260703" if "20260703" in sample_key else "20260706"
            sample_day = str(sample.get("trade_date", "")).replace("-", "")
            if sample_day != expected_day or sample.get("risk_status") != "RISK_WARNING":
                sample_failures.append(sample_key + ":BOUNDARY_BINDING")
        rule_id = sample.get("rule_id")
        ratio = ratios.get(rule_id)
        try:
            if ratio is None:
                raise ValueError("UNMAPPED_RULE_ID")
            ref = Decimal(str(sample["reference_price"]))
            tick = Decimal("0.01")
            up = (ref * (Decimal("1") + ratio) / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
            down = (ref * (Decimal("1") - ratio) / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
            if sample.get("limit_status") == "UNKNOWN" or Decimal(str(sample["limit_up_price"])) != up or Decimal(str(sample["limit_down_price"])) != down:
                sample_failures.append(sample_key + ":PRICE_MATH")
        except (KeyError, TypeError, ValueError, ArithmeticError):
            sample_failures.append(sample_key + ":MISSING_OR_INVALID_REFERENCE")
    ipo_sample = price_samples.get("IPO_NO_LIMIT", {})
    if ipo_sample and (ipo_sample.get("limit_status") != "NO_LIMIT" or ipo_sample.get("limit_up_price") is not None or ipo_sample.get("limit_down_price") is not None):
        sample_failures.append("IPO_NO_LIMIT:STATE")
    ex_right_sample = price_samples.get("EX_RIGHT", {})
    if ex_right_sample and (not str(ex_right_sample.get("reference_basis", "")).startswith("TDX_XRXD_REFERENCE_TRANSFORM") or int(ex_right_sample.get("action_count", 0)) < 1):
        sample_failures.append("EX_RIGHT:REFERENCE_TRANSFORM")
    if sample_failures:
        findings.append("PRICE_LIMIT_SAMPLE_INDEPENDENT_CHECK_FAILED:" + ",".join(sample_failures))

    universe_path = ROOT / args.universe
    status_path = ROOT / manifest["components"]["TRADING_STATUS"]["path"]
    isst_path = ROOT / manifest["components"]["DATED_ISST"]["path"]
    price_path = ROOT / manifest["components"]["PRICE_LIMIT"]["path"]
    reconcile = Counter()
    first_key = None
    try:
        with gzip.open(universe_path, "rt", encoding="utf-8") as universe, \
             gzip.open(status_path, "rt", encoding="utf-8") as statuses, \
             gzip.open(isst_path, "rt", encoding="utf-8") as isst_rows, \
             gzip.open(price_path, "rt", encoding="utf-8") as limits:
            for uline, sline, iline, pline in zip(universe, statuses, isst_rows, limits, strict=True):
                u, s, i, p = json.loads(uline), json.loads(sline), json.loads(iline), json.loads(pline)
                key = (u["trade_date"], u["source_security_key"].lower())
                first_key = first_key or key
                if (s.get("security_id") != u["security_id"] or i.get("security_id") != u["security_id"] or p.get("security_id") != u["security_id"]
                        or s.get("trade_date") != u["trade_date"] or i.get("trade_date") != u["trade_date"] or p.get("trade_date") != u["trade_date"]
                        or s.get("source_security_key") != u["source_security_key"] or i.get("source_security_key") != u["source_security_key"] or p.get("source_security_key") != u["source_security_key"]):
                    raise RuntimeError("PRIMARY_KEY_BINDING_MISMATCH")
                if u.get("board_scope") not in {"SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"}:
                    raise RuntimeError("OPTIONAL_OR_UNKNOWN_BOARD_IN_REQUIRED_UNIVERSE")
                if u.get("source_bar_present") is True and s.get("status") != "ACTUAL_TRADED":
                    raise RuntimeError("LOCAL_TDX_BAR_PRECEDENCE_VIOLATION")
                if s.get("status") == "SUSPENDED" and u.get("source_bar_present") is True:
                    raise RuntimeError("SUSPENDED_STATUS_ON_LOCAL_ACTUAL_BAR")
                if i.get("is_st") not in {"0", "1", None}:
                    raise RuntimeError("ISST_DOMAIN_INVALID")
                if i.get("is_st") is None and i.get("binding_quality") not in {"UNKNOWN_QUERY_FAILURE", "UNKNOWN_NO_VALID_PROVIDER_ROW"}:
                    raise RuntimeError("ISST_UNKNOWN_WITHOUT_REASON")
                if p.get("is_st") != i.get("is_st"):
                    raise RuntimeError("PRICE_LIMIT_ISST_BINDING_MISMATCH")
                if p.get("limit_status") == "UNKNOWN" and not p.get("reason"):
                    raise RuntimeError("PRICE_LIMIT_UNKNOWN_WITHOUT_REASON")
                if p.get("limit_status") not in {"UNKNOWN", "SUSPENDED", "NO_LIMIT", "NOT_LIMIT", "LIMIT_UP", "LIMIT_DOWN"}:
                    raise RuntimeError("PRICE_LIMIT_STATE_DOMAIN_INVALID")
                if p.get("limit_status") in {"NOT_LIMIT", "LIMIT_UP", "LIMIT_DOWN"}:
                    if not p.get("reference_price") or not p.get("limit_up_price") or not p.get("limit_down_price") or not p.get("rule_id"):
                        raise RuntimeError("KNOWN_PRICE_LIMIT_STATE_MISSING_BOUNDARY")
                if p.get("limit_status") in {"SUSPENDED", "NO_LIMIT"} and (p.get("limit_up_price") is not None or p.get("limit_down_price") is not None):
                    raise RuntimeError("UNBOUNDED_PRICE_LIMIT_STATE_HAS_BOUNDARY")
                if p.get("trading_status") != s.get("status"):
                    raise RuntimeError("PRICE_LIMIT_TRADING_STATUS_MISMATCH")
                reconcile["membership_rows"] += 1
                reconcile["board_" + str(u["board_scope"])] += 1
                reconcile["price_limit_" + str(p["limit_status"])] += 1
                if i.get("is_st") is None:
                    reconcile["isst_unknown_rows"] += 1
                if p.get("limit_status") == "UNKNOWN":
                    reconcile["price_limit_unknown_rows"] += 1
    except Exception as exc:
        findings.append("UNIVERSE_FACT_RECONCILIATION_FAILED:" + type(exc).__name__ + ":" + str(exc)[:160])

    expected_membership = 4036121
    if reconcile.get("membership_rows") != expected_membership:
        findings.append("UNIVERSE_FACT_RECONCILIATION_COUNT_MISMATCH")
    checks = {
        "all_component_hashes_match": not any(x.startswith("COMPONENT_SHA256") for x in findings),
        "all_component_byte_counts_match": not any(x.startswith("COMPONENT_BYTE_COUNT") for x in findings),
        "parquet_row_counts_and_schemas_pass": not any(x.startswith("PARQUET_") or x.startswith("REQUIRED_BOARD") or x.startswith("BSE_OR_UNKNOWN") for x in findings),
        "dated_status_isst_price_limit_membership_reconciles": not any(x.startswith("UNIVERSE_FACT") for x in findings),
        "all_unknown_values_have_explicit_reason": "PRICE_LIMIT_UNKNOWN_WITHOUT_REASON" not in " ".join(findings),
        "required_rule_samples_present": not missing_samples,
        "required_rule_sample_values_independently_recomputed": not sample_failures,
        "calendar_period_temporal_receipts_pass": not any(x in findings for x in ["FORMAL_CALENDAR_NOT_ACCEPTED", "PERIOD_OR_CLOSED_ASOF_POSTCHECK_FAILED", "REV2_TEMPORAL_CASE_SET_NOT_PASS"]),
    }
    receipt = {
        "contract_id": "V4_02_FINAL_INDEPENDENT_POSTCHECK_V1",
        "status": "PASS" if all(checks.values()) and not findings else "BLOCKED",
        "checks": checks,
        "findings": findings,
        "input_manifest": {"path": args.manifest, "sha256": sha(manifest_path)},
        "component_hashes": component_hashes,
        "evidence_receipts": {
            "calendar": {"path": args.calendar_receipt, "sha256": sha(ROOT / args.calendar_receipt)},
            "temporal": {"path": args.temporal_receipt, "sha256": sha(ROOT / args.temporal_receipt)},
            "period": {"path": args.period_receipt, "sha256": sha(ROOT / args.period_receipt)},
            "period_postcheck": {"path": args.period_postcheck, "sha256": sha(ROOT / args.period_postcheck)},
            "dated_isst": {"path": args.isst_receipt, "sha256": sha(ROOT / args.isst_receipt)},
            "bounded_isst_recovery": ({"path": isst["bounded_recovery"]["receipt_path"],
                                        "sha256": isst["bounded_recovery"]["receipt_sha256"]}
                                       if isst.get("bounded_recovery") else None),
            "price_limit": {"path": args.price_receipt, "sha256": sha(ROOT / args.price_receipt)},
        },
        "parquet_checks": parquet_checks,
        "membership_reconciliation": dict(reconcile),
        "required_price_limit_samples": sorted(required_samples),
        "missing_price_limit_samples": missing_samples,
        "lineage": {"historical_adjusted": "DIAGNOSTIC_NON_PIT", "historical_provider_isst": "DIAGNOSTIC_NON_PIT_RECONSTRUCTED_FROM_CURRENT_PROVIDER_HISTORY", "future_rows_consumed_for_t0": False},
        "execution_identity": {"postcheck_script_sha256": sha(Path(__file__).resolve())},
        "source_cutoff": "2026-09-24",
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=out.name + ".", suffix=".tmp", dir=out.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, out)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print(json.dumps({"status": receipt["status"], "findings": findings,
                      "rows": reconcile.get("membership_rows"), "unknown_price_rows": reconcile.get("price_limit_unknown_rows")}, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
