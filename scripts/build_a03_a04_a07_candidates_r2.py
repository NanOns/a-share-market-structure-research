"""Hash-bound real observations and independent arithmetic; no accepted publication writes."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import gzip
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile

from workbench_analysis.forward_pit_ledger_r2 import atomic, append_observation, bound, canonical, digest, reference, publications
from workbench_analysis.amount_a_authority_r2 import calculate_candidate
from workbench_analysis.adjusted_price_lineage_r2 import capture_source, classify_lineage, independent_ex_right_reference
from tdx.gbbq_reader import read_gbbq

ROOT = Path(__file__).resolve().parents[1]
BASE = "bc3e398efb4f4a05c20973ff3cb335a6b101ac87"


def read(ref):
    return json.loads(bound(ROOT, ref))


def write(relative, value):
    atomic(ROOT/relative, canonical(value), immutable=True)
    return reference(ROOT, ROOT/relative)


def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf8"))


def common(task, contract):
    return {"baseline_head": BASE, "batch_entry": reference(ROOT, ROOT/"reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json"),
            "task": reference(ROOT, ROOT/"docs/evidence/next_round_r1"/task),
            "contract": reference(ROOT, ROOT/contract), "accepted_data_head": reference(ROOT, ROOT/"data/v4/V4_DATA_ACCEPTED_HEAD.json"),
            "stage_head": reference(ROOT, ROOT/"data/v4/V4_STAGE_ACCEPTED_HEAD.json"),
            "permissions": {"production": False, "shadow": False, "focus_cutover": False, "global_mandatory_adoption": False},
            "external_acceptance": None, "next_stage": "INDEPENDENT_EXTERNAL_REAUDIT", "head_write_permission": False}


def ensure_heads():
    entry = load("reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json")
    # Root captures every Accepted Head. Discover binding records recursively rather than assuming entry key names.
    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("path"), str) and "ACCEPTED_HEAD" in value["path"] and "sha256" in value:
                if "bytes" in value or "byte_count" in value:
                    bound(ROOT, value)
                else:
                    if digest((ROOT/value["path"]).read_bytes()) != value["sha256"]:
                        raise ValueError("PROTECTED_HEAD_CHANGED")
            for v in value.values(): walk(v)
        elif isinstance(value, list):
            for v in value: walk(v)
    walk(entry)


def a03(head):
    report = "reports/audits/A03_FORWARD_PIT_BUILDER_R2_REAL_OBSERVATION.json"
    if (ROOT/report).exists():
        publications(ROOT, "data/v4/a03_forward_pit_r2")
        return reference(ROOT, ROOT/report)
    started = datetime.now(timezone.utc).isoformat()
    sources = {}
    for family in ("RAW_DAILY", "ADJUSTED_DAILY", "IDENTITY_UNIVERSE", "TRADING_STATUS", "ISST"):
        ref = head["component_artifacts"][family]
        payload = read(ref)
        sources[family] = {"bytes_binding": ref, "source_revision": "sha256:"+ref["sha256"],
                           "target_trade_date": payload["trade_date"], "schema_id": payload["contract_id"],
                           "received_at": datetime.now(timezone.utc).isoformat(),
                           "capture_kind": "ACTUAL_ACCEPTED_BASELINE_READ_NOW_NOT_TARGET_TIME_CAPTURE"}
    received = datetime.now(timezone.utc).isoformat()
    env = {"capture_id": "A03_ACCEPTED_20260930_BASELINE_OBSERVATION_R2", "target_trade_date": "2026-09-30",
           "observed_at": started, "received_at": received, "expected_available_by": "2026-09-30T15:00:00+08:00",
           "calendar_binding": head["calendar"], "identity_binding": head["identity"], "identity_complete": True,
           "expected_source_families": sorted(sources), "expected_schema_ids": {k: v["schema_id"] for k,v in sources.items()}, "sources": sources}
    envelope = write("data/v4/a03_forward_pit_r2/accepted_baseline_capture_envelope.json", env)
    result = append_observation(ROOT, "data/v4/a03_forward_pit_r2", env)
    replay = append_observation(ROOT, "data/v4/a03_forward_pit_r2", env)
    pubs = publications(ROOT, "data/v4/a03_forward_pit_r2")
    value = common("V4_A03_FORWARD_PIT_HISTORY_ACCUMULATION_TASK_R2_20261001.md", "config/a03_forward_pit_ledger_r2.json")
    value.update(status="A03_FORWARD_PIT_BUILDER_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT", engineering_status="CANDIDATE_READY_FOR_EXTERNAL_REAUDIT",
                 capture_envelope=envelope, publication=reference(ROOT, ROOT/"data/v4/a03_forward_pit_r2/publications"/(result["publication"]["publication_id"]+".json")),
                 real_observation_count=len(pubs), duplicate_retry=replay["detectors"], immutable_replay="PASS",
                 current_observation_lineage=result["publication"]["knowledge_lineage"],
                 calendar_known_through=head["accepted_trade_date"],
                 accumulation_status="PARTIAL_AWAITING_NEXT_REAL_CAPTURE_WITH_ACCEPTED_CALENDAR_IDENTITY_BINDINGS",
                 next_session_capture="NO_COMPLETED_POST_20260930_SESSION_PROVED_BY_CURRENT_ACCEPTED_CALENDAR; NO_WAIT",
                 future_observation_required=True, consumer_permission_granted=False,
                 daily_command="E:/python/python.exe scripts/run_a03_forward_pit_daily_r2.py --capture-envelope <actual-envelope.json>",
                 recovery_command="E:/python/python.exe scripts/run_a03_forward_pit_daily_r2.py --recover",
                 automation_execution="DAILY_CAPTURE_COMPLETION_COMMAND_DELIVERED; NO_UNREQUESTED_OS_SCHEDULE_INSTALL")
    return write(report, value)


def archaeology():
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf8").split("\0")
    pattern = re.compile(r"sector_amount_vs_prior20|amount_A|amount_a|Amount A|amount_concentration|member_amount_ratio_median_vs_prior20")
    records = []
    for path in paths:
        if not path or not path.startswith(("src/", "scripts/", "config/", "tests/", "ui/")) or Path(path).suffix not in {".py", ".sql", ".json", ".yaml", ".js", ".ts", ".tsx", ".html"}:
            continue
        file = ROOT/path
        if not file.exists(): continue
        matches = [{"line": n, "text": line[:1000]} for n,line in enumerate(file.read_text(encoding="utf8", errors="replace").splitlines(),1) if pattern.search(line)]
        if matches:
            role = "DB_CACHE" if file.suffix == ".sql" or "workbench_db" in path else "UI_API" if "workbench_service" in path else "PRODUCER" if "sector_amount" in path or "sector_factors" in path else "CONTRACT" if path.startswith("config/") else "TEST" if path.startswith("tests/") else "CONSUMER_OR_RESEARCH_DIAGNOSTIC"
            records.append({"binding": reference(ROOT, file), "role": role, "matches": matches})
    return {"scope": "ALL_BASELINE_GIT_TRACKED_CODE_CONTRACT_DB_UI_TEST_FILES", "files": records,
            "legacy_formula": "A=S(common,t)/mean(S(common,u) for exact prior20 master-calendar sessions)",
            "legacy_unaccepted_policy_defaults": {"min_comparable_members": 5, "min_comparable_coverage": "0.80"},
            "candidate_policy": "DO_NOT_ADOPT_LEGACY_THRESHOLDS_WITHOUT_AUTHORITY", "unit_evidence": reference(ROOT, ROOT/"src/tdx/tdx_audit.py"),
            "tdx_native_field_interpretation": "RAW_FLOAT32_CNY_FOR_A_SHARES_CROSS_FIELD_VERIFIED; NOT_SHARE_COUNT"}


def a04(head, ctx):
    report = "reports/audits/A04_AMOUNT_A_FORMAL_AUTHORITY_R2_REAL_PROOF.json"
    if (ROOT/report).exists(): return reference(ROOT, ROOT/report)
    inventory = write("reports/audits/A04_AMOUNT_A_R2_REPO_CONSUMER_INVENTORY.json", archaeology())
    calendar = read(head["calendar"])["session_dates"]
    target = head["accepted_trade_date"]
    window = calendar[calendar.index(target)-20:calendar.index(target)+1]
    identity = read(head["component_artifacts"]["IDENTITY_UNIVERSE"])["rows"]
    by_id = {r["security_id"]: r for r in identity}
    statuses = {r["security_id"]: r["status"] for r in read(head["component_artifacts"]["TRADING_STATUS"])["rows"]}
    accepted_raw = {r["security_id"]: r for r in read(head["component_artifacts"]["RAW_DAILY"])["rows"]}
    mh = load("data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json")
    facts = [json.loads(line) for line in gzip.decompress(bound(ROOT, mh["facts"])).decode("utf8").splitlines()]
    groups = {}
    for row in facts:
        if row["sector_type"] == "INDUSTRY" and row["security_id"] in by_id:
            groups.setdefault(row["sector_id"], set()).add(row["security_id"])
    selected_groups = {g: sorted(members)[:8] for g,members in sorted(groups.items()) if len(members) >= 6}
    selected_groups = dict(list(selected_groups.items())[:4])
    for board in sorted({x["board_scope"] for x in identity}):
        selected_groups["BOARD_DIAGNOSTIC:"+board] = sorted([x["security_id"] for x in identity if x["board_scope"] == board])[:4]
    fresh = sorted([x for x in identity if x.get("list_date") and x["list_date"] >= window[0]], key=lambda x:x["list_date"], reverse=True)[:5]
    suspended = [x for x in identity if statuses[x["security_id"]] == "SUSPENDED"][:5]
    selected_groups["BOUNDARY_NEW_LISTING_AND_SUSPENSION"] = sorted({x["security_id"] for x in fresh+suspended})
    package = ctx["inputs"][target]["families"]["TDX_FULL_PACKAGE"]
    # Read/hash exact official archive once. Independent raw decoder never invokes Amount A producer.
    bound(ROOT, package)
    rows, sample_sources, raw_rows = {}, [], []
    with zipfile.ZipFile(ROOT/package["path"]) as z:
        for member in sorted(set().union(*map(set, selected_groups.values()))):
            item = by_id[member]; exchange, code = item["source_security_key"].split(".")
            name = f"{exchange.lower()}/lday/{exchange.lower()}{code}.day"
            raw = z.read(name) if name in z.namelist() else b""
            source = {"security_id": member, "source_security_key": item["source_security_key"], "list_date": item.get("list_date"),
                      "board_scope": item["board_scope"], "archive_member": name, "member_sha256": digest(raw), "member_bytes": len(raw),
                      "target_dated_status": statuses[member], "sample_rows": []}
            for d,op,hi,lo,cl,amt,vol,res in struct.iter_unpack("<IIIIIfII", raw):
                day = f"{d//10000:04}-{d//100%100:02}-{d%100:02}"
                if day not in window: continue
                state = "ACTUAL_TRADED" if amt > 0 and vol > 0 else "UNKNOWN"
                rows[(member,day)] = {"amount": str(amt), "state": state}
                source["sample_rows"].append({"trade_date": day, "amount_cny_native_float32": str(amt), "volume_shares": vol,
                                               "close_cny": str(Decimal(cl)/100),
                                               "state": state})
                if day == target and member in accepted_raw and Decimal(str(amt)) != Decimal(str(accepted_raw[member]["amount"])):
                    raise ValueError("RAW_AMOUNT_ACCEPTED_ARTIFACT_DIFFERENCE")
            if statuses[member] == "SUSPENDED" and (member,target) not in rows:
                rows[(member,target)] = {"amount": "0", "state": "SUSPENDED_CONFIRMED"}
                source["sample_rows"].append({"trade_date": target, "amount_cny_native_float32": "0", "state": "SUSPENDED_CONFIRMED", "evidence": head["component_artifacts"]["TRADING_STATUS"]})
            sample_sources.append(source)
    source_ref = write("data/v4/source_evidence/a04_r2/raw_amount_exact_source_samples_r2.json", {"official_archive": package, "exact_sessions": window, "sources": sample_sources,
                           "decoder": "INDEPENDENT_STRUCT_UNPACK_LITTLE_ENDIAN_32_BYTE_TDX_DAY; NO_AMOUNT_A_PRODUCER_RESULT_READ"})
    proofs = []
    for group, members in selected_groups.items():
        # Reconstruction is explicitly a current snapshot diagnostic, never invented historical PIT memberships.
        memberships = {day:[m for m in members if by_id[m].get("list_date") and by_id[m]["list_date"] <= day] for day in window}
        candidate = calculate_candidate(target=target,sessions=calendar,members_by_session=memberships,amount_rows=rows,
                        source_unit="CNY_YUAN", membership_timestamp="2026-09-30_CURRENT_SNAPSHOT_RECONSTRUCTION_ONLY",
                        source_revision=package["source_revision"])
        valid = candidate["comparable_members"]
        independent_sums = {day: sum((Fraction(rows[(m,day)]["amount"]) for m in valid), Fraction(0)) for day in window}
        denom = sum((independent_sums[day] for day in window[:-1]), Fraction(0))/20 if valid else None
        numerator = independent_sums[target] if valid else None
        independent_a = numerator/denom if denom and denom>0 else None
        comparable = Decimal(independent_a.numerator)/Decimal(independent_a.denominator) if independent_a is not None else None
        actual = Decimal(candidate["diagnostic_amount_a"]) if candidate["diagnostic_amount_a"] is not None else None
        if actual != comparable:
            raise ValueError(f"INDEPENDENT_FRACTION_ARITHMETIC_MISMATCH:{group}:{actual}:{comparable}")
        proofs.append({"group": group, "membership_lineage": "RECONSTRUCTED_CURRENT_FIXED_SNAPSHOT_NOT_HISTORICAL_PIT",
                       "candidate": candidate, "independent_rational_numerator": str(numerator), "independent_rational_denominator": str(denom),
                       "independent_rational_amount_a": str(independent_a), "arithmetic_compare": "PASS"})
    value = common("V4_A04_AMOUNT_A_FORMAL_AUTHORITY_TASK_R2_20261001.md", "config/a04_amount_a_authority_candidate_r2.json")
    value.update(status="A04_AMOUNT_A_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT", engineering_status="CANDIDATE_READY_FOR_EXTERNAL_REAUDIT",
                 formal_capability_status="BLOCKED_PENDING_EXTERNAL_UNIT_COVERAGE_AND_HISTORICAL_MEMBERSHIP_AUTHORITY",
                 consumer_inventory=inventory, real_raw_samples=source_ref, accepted_membership_source=mh["facts"],
                 accepted_membership_earliest_date=mh["first_accepted_trade_date"], exact_prior20_sessions=window[:-1],
                 sample_groups=proofs, real_member_count=len(sample_sources), real_new_listing_samples=[x["source_security_key"] for x in fresh],
                 real_suspension_samples=[x["source_security_key"] for x in suspended],
                 real_missing_amount_cells=sum(len([d for d in window if (x["security_id"],d) not in rows]) for x in sample_sources),
                 raw_accepted_target_amount_parity="PASS", independent_arithmetic="PASS",
                 historical_pit_membership_coverage="BLOCKED_H21_NOT_PROVED_CURRENT_20260930_FACTS_ONLY",
                 accepted_owner_registered=False, formal_consumer_enabled=False, v4_11_amount_a_branch_enabled=False,
                 existing_legacy_consumers="INVENTORIED_UNCHANGED; NO_NEW_FORMAL_AUTHORITY_GRANTED")
    return write(report, value)


def a07(head, ctx, source_path):
    report="reports/audits/A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_R2_REAL_PROOF.json"
    if (ROOT/report).exists(): return reference(ROOT,ROOT/report)
    captured = capture_source(ROOT, source_path, source_kind="GBBQ", source_identity=str(source_path.resolve()))
    old = ctx["inputs"]["2026-09-30"]["families"]["GBBQ"]
    records = read_gbbq(ROOT/old["path"])
    event_samples = []
    for label, predicate in [("CASH_DIVIDEND",lambda x:x.c1>0), ("SPLIT_BONUS",lambda x:x.c3>0), ("RIGHTS_ISSUE",lambda x:x.c4>0 and x.c2>0)]:
        event = next(x for x in records if x.category == 1 and predicate(x))
        # Decimal independent event arithmetic at an explicitly hypothetical reference close.
        price = independent_ex_right_reference(100,cash_per10=event.c1,bonus_per10=event.c3,rights_per10=event.c4,rights_price=event.c2)
        event_samples.append({"event_kind":label,"actual_gbbq_source_event":asdict(event),"source_binding":old,
                              "reference_close":"100","reference_close_role":"HYPOTHETICAL_ARITHMETIC_FIXTURE_NOT_MARKET_PRICE",
                              "independent_theoretical_ex_price":str(price),"historical_as_recorded":False})
    tracked = subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).decode("utf8").split("\0")
    source_inventory=[reference(ROOT, ROOT/p) for p in tracked if p and ("gbbq" in p.lower() or "adjustment_factor" in p.lower() or "adjusted" in p.lower()) and (ROOT/p).is_file()]
    git_history = subprocess.check_output(["git","log","-8","--format=%H %aI %s","--","data/v4/source_snapshot_store/gbbq","data/v4/canonical","src/adjustment"],cwd=ROOT).decode("utf8")
    current = classify_lineage(ROOT,captured,knowledge_time=captured["received_at"])
    historical = classify_lineage(ROOT,captured,knowledge_time="2026-09-24T15:00:00+08:00")
    value=common("V4_A07_HISTORICAL_AS_RECORDED_ADJUSTED_PRICE_TASK_R2_20261001.md","config/a07_adjusted_price_lineage_r2.json")
    value.update(status="A07_HISTORICAL_ADJUSTED_PRICE_LINEAGE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT",engineering_status="CANDIDATE_READY_FOR_EXTERNAL_REAUDIT",
                 historical_capability_status="PERMANENTLY_BLOCKED_PRE_CAPTURE_AS_RECORDED",real_capture=captured,
                 current_source_version_knowledge=current,historical_knowledge_gate=historical,
                 accepted_price_artifact_lineage=head["knowledge_lineage"], accepted_head_as_recorded=head["AS_RECORDED"],
                 go_forward_capture_status="REAL_GBBQ_BYTES_CAPTURED_CURRENT_KNOWLEDGE_ONLY_NO_ADJUSTED_PRICE_AUTHORITY_GRANT",
                 old_accepted_gbbq_source=old,old_source_first_known_manifest=reference(ROOT,(ROOT/old["path"]).with_name("manifest.json")),
                 raw_source_inventory=source_inventory,source_inventory_receipts_and_git_history=git_history,
                 provider_factor_status="SUPPLEMENTAL_AVAILABILITY_RECEIPTS_INVENTORIED_NOT_ADJUSTMENT_AUTHORITY",
                 manual_record_status="NO_HASH_BOUND_FIRST_AVAILABILITY_ADJUSTMENT_MANUAL_AUTHORITY_PROVED",
                 actual_price_event_samples=event_samples,
                 consumer_inventory={"V4_05_Replay":{"basis":"RECONSTRUCTED_CORRECTED_EXPLICIT_ACCEPTED_CONTRACT_ONLY","bindings":[reference(ROOT,ROOT/"src/workbench_analysis/forward_v3_3.py")]},
                                     "V4_12_Structure_Anchor":{"basis":"FUTURE_ENTRY_FORBIDDEN_THIS_BATCH","implementation_executed":False},
                                     "Forward_Outcome":{"basis":"AS_RECORDED_NEEDED_FOR_HISTORICAL_KNOWLEDGE_CLAIMS","bindings":[reference(ROOT,ROOT/"src/workbench_analysis/forward_outcome_v3_3.py")]},
                                     "Support_Retention":{"basis":"AS_RECORDED_REQUIRED_FOR_HISTORICAL_KNOWLEDGE; NO_IMPLICIT_UPGRADE"}},
                 formal_consumer_enabled=False,future_observation_required=True)
    return write(report,value)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--gbbq-source",type=Path,default=Path("D:/new_tdx/T0002/hq_cache/gbbq"));a=parser.parse_args()
    ensure_heads()
    head=load("data/v4/V4_DATA_ACCEPTED_HEAD.json")
    contract=load("config/dm01_incremental_builders_contract_r3_3.json");ctx=read(contract["execution_context"])
    reports={"A03":a03(head),"A04":a04(head,ctx),"A07":a07(head,ctx,a.gbbq_source)}
    ensure_heads()
    print(canonical(reports).decode("utf8"))

if __name__=="__main__":main()
