"""Materialize R3 scoped source, contract, and real-owner evidence."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/three_day_repair_r3_20261008"
OUT.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def ref(path):
    p = ROOT / path
    return {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "exists": p.exists(),
            "bytes": p.stat().st_size if p.exists() else None,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}


def gzrows(path):
    with gzip.open(ROOT / path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def write(name, value):
    path = OUT / name
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main():
    from workbench_service.production_v4 import ProductionV4ResearchReader

    reader = ProductionV4ResearchReader(ROOT)
    current = []
    for offset in range(0, 6000, 200):
        page = reader.query("stocks", {"limit": 200, "offset": offset})["items"]
        current.extend(page)
        if len(page) < 200:
            break
    fields = ["basic_breakout_state", "basic_pullback_state", "basic_recovery_state", "structure_health",
              "support_state", "relative_market_state", "relative_sector_state"]
    counts, reasons, examples = {}, {}, {}
    for name in fields:
        values = [row["fields"].get(name, {}) for row in current]
        known = [v for v in values if v.get("quality") in ("KNOWN", "ACCEPTED") and v.get("value") not in (None, "UNKNOWN")]
        counts[name] = {"known": len(known), "unknown": len(values) - len(known)}
        reasons[name] = dict(collections.Counter(str(v.get("reason")) for v in values
                                                  if v.get("quality") not in ("KNOWN", "ACCEPTED") or v.get("value") in (None, "UNKNOWN")))
        examples[name] = [{"symbol": r.get("symbol"), "security_id": r.get("security_id"),
                           "value": r["fields"].get(name, {}).get("value"),
                           "quality": r["fields"].get(name, {}).get("quality"),
                           "reason": r["fields"].get(name, {}).get("reason"),
                           "source_digest": r["fields"].get(name, {}).get("source_digest")} for r in current[:3]]

    registry = read("config/v4_12_field_registry_v1.json")
    schema = read("config/v4_12_output_schema_v1.json")
    ast = read("config/v4_12_machine_ast_v1.json")
    ref_contracts = {n: ref("config/" + n) for n in (
        "v4_12_structure_event_contract_v1.json", "v4_12_support_state_contract_v1.json",
        "v4_12_machine_ast_v1.json", "v4_12_output_schema_v1.json", "v4_12_producer_registry_v1.json",
        "v4_12_parameter_set_v1.json", "v4_13_loo_context_v1_1.json", "v4_04_algorithm_contracts_v3.json",
        "v4_04_parameter_set_v1.json")}
    matrix = {
        "basic_breakout_state": ("STRUCTURE_EVENT_V1 / breakout AST", "ordered frozen-anchor breakout rules", "NO_BREAKOUT/APPROACHING/BREAKOUT_TENTATIVE/BREAKOUT_ACCEPTED/FAILED_BREAKOUT/UNKNOWN", "T with exact T-1 owner; ATR20, MA20/CLV and prior high/pivot", "target V4-03 Core owner fields are blocked; real R13 candidate has no anchors"),
        "basic_pullback_state": ("STRUCTURE_EVENT_V1 / pullback AST", "per-anchor state machine with previous evaluable state", "NOT_PULLBACK/PULLBACK_IN_PROGRESS/PULLBACK_TO_BREAKOUT/PULLBACK_TO_IMPULSE/PULLBACK_TO_MA/PULLBACK_HELD/PULLBACK_RECLAIMED/PULLBACK_FAILED/UNKNOWN", "per-anchor D0 and exact T-1 state; anchor geometry and accepted OHLC/ATR", "no accepted anchor or prior D1 owner materialized"),
        "basic_recovery_state": ("STRUCTURE_EVENT_V1 / recovery AST", "ordered recovery machine; missing prior inputs are not reconstructed", "BOUNCE_ONLY/MA20_RECLAIM/RELATIVE_RECOVERY/RECOVERY_CONFIRMED/RECOVERY_FAILED/UNKNOWN", "per-anchor evaluable sessions, prior close/MA20/ATR and accepted relative inputs", "target Core and prior owner dependencies blocked"),
        "structure_health": ("V4_12_OUTPUT_SCHEMA_V1 selected-anchor projection", "BROKEN/INVALIDATED→DAMAGED; HELD_CONFIRMED→STABLE; RECLAIMED→IMPROVING; UNKNOWN→UNKNOWN", "STABLE/WEAKENING/DAMAGED/IMPROVING/UNKNOWN", "selected anchor and support-state owner at T", "dependent selected-anchor/support owner absent"),
        "support_state": ("SUPPORT_STATE_V1", "ordered support state/counters; separation, missing reset, terminal no-resurrection", "IDLE/TESTING/RETESTING/HELD_TENTATIVE/HELD_CONFIRMED/BREACHED_SHALLOW/BROKEN/RECLAIMED/INVALIDATED/UNKNOWN", "creation-bound anchor, target OHLC/ATR/MA20, exact prior state and counters", "runtime candidate emits zero anchors due blocked target owner"),
        "relative_market_state": ("RELATIVE_STATE_V1 / V4-04", "accepted AST on RPS5/RPS20/RPS20 delta3, relative market returns, compression and MA structure", "ACTIVE_EMERGENCE/PASSIVE_RESILIENCE/LEADING_ACCELERATING/LAGGING/NEUTRAL/UNKNOWN", "same T plus accepted prior RPS endpoint for delta3", "9/30 Profile exists; required RPS delta3 is explicitly not bound/backfilled"),
        "relative_sector_state": ("LOO_CONTEXT_V1.1 / V4-13", "remove target before sector medians/ranks/base/seed; then exact relative-state AST", "same relative-state enum plus UNKNOWN/NOT_APPLICABLE per complete-set rule", "T exact dated membership and non-target returns plus accepted stock relative fields", "contract is freeze-only, runtime_implemented=false; required accepted inputs not bound"),
    }
    rows = {}
    for name, (owner, formula, states, window, root_cause) in matrix.items():
        rows[name] = {"owner_contract": owner, "formula_or_projection": formula, "state_space": states,
                      "window_and_inputs": window, "quality_and_boundary": "UNKNOWN remains UNKNOWN with exact reason; no UNKNOWN-to-FALSE; no target date is inferred",
                      "artifact": "V4-12 real R13 candidate runtime_security/state_observations" if name not in ("relative_market_state", "relative_sector_state") else ("9/30 FP06 profiles" if name == "relative_market_state" else "no accepted V4-13 owner artifact"),
                      "consumer": "FP07 stock snapshot → ProductionV4ResearchReader / stock_views.py",
                      "status": "OWNER_PRESENT_INPUT_BLOCKED" if name == "relative_market_state" else "BLOCKED_WITH_EVIDENCE",
                      "root_cause": root_cause}
    write("R3_SEVEN_STRUCTURE_FIELDS_OWNER_CONTRACT_MATRIX.json", {"contract_id": "R3_SEVEN_STRUCTURE_FIELDS_OWNER_CONTRACT_MATRIX_V1", "fields": rows,
          "contract_refs": ref_contracts, "V4_12_field_registry": ref("config/v4_12_field_registry_v1.json"),
          "V4_12_breakout_rules": ast.get("machines", {}).get("breakout"), "V4_12_pullback_rules": ast.get("machines", {}).get("pullback"),
          "V4_12_recovery_rules": ast.get("machines", {}).get("recovery"), "structure_health_mapping": schema.get("structure_health_mapping"),
          "acceptance": "PARTIAL: contracts mapped; formal materialization blocked by owner capability and runtime admission"})

    before_after = read("docs/evidence/three_day_repair_r2_20261008/R2_STOCK_FIELD_BEFORE_AFTER.json")
    write("R3_STOCK_BEFORE_AFTER_ALL_5213.json", {"contract_id": "R3_STOCK_BEFORE_AFTER_ALL_5213_V1", "target_trade_date": "2026-09-30",
          "population": {"expected": 5213, "observed": len(current), "match": len(current) == 5213},
          "fields": {n: {"before": before_after["field_counts"][n]["before"], "after_recomputed": counts[n],
                         "unknown_reason_distribution": reasons[n], "sample_rows": examples[n], "change": "NO_CHANGE"} for n in fields},
          "source_hashes": {"before_after": ref("docs/evidence/three_day_repair_r2_20261008/R2_STOCK_FIELD_BEFORE_AFTER.json"),
                            "current_snapshot": ref("data/v4/research_snapshots/3a3f5d9074b646189ccfd830c15e7161/manifest.json"),
                            "structure_runtime": ref("reports/v4_12_runtime_r13/real/2026-09-30/r1/runtime_manifest.json")},
          "acceptance": "FAIL_STRUCTURE_OWNER_CHAIN_NOT_MATERIALIZED; reasons are field-local"})

    real = list(gzrows("reports/v4_12_runtime_r13/real/2026-09-30/r1/runtime_security.jsonl.gz"))
    event_count = sum(len(r.get("breakout_episodes", [])) for r in real)
    anchor_count = sum(len(r.get("anchors", [])) for r in real)
    real_samples = [{"security_id": r.get("security_id"), "trade_date": r.get("trade_date"),
                     "basis": "RECONSTRUCTED_CORRECTED", "active_anchor_id": r.get("active_projection", {}).get("active_anchor_id"),
                     "basic_breakout_state": r.get("basic_breakout_state"),
                     "basic_pullback_state": r.get("active_projection", {}).get("basic_pullback_state"),
                     "basic_recovery_state": r.get("active_projection", {}).get("basic_recovery_state"),
                     "support_state": r.get("active_projection", {}).get("support_state"),
                     "reason": r.get("active_projection", {}).get("breakout_projection_reason")} for r in real[:12]]
    write("R3_STOCK_STRUCTURE_REAL_ORACLE.json", {"contract_id": "R3_STOCK_STRUCTURE_REAL_ORACLE_V1", "result": "BLOCKED_WITH_REAL_SOURCE_EVIDENCE",
          "candidate_rows": len(real), "formal_accepted": False, "anchor_count": anchor_count, "event_count": event_count,
          "real_examples": real_samples, "runtime_manifest": ref("reports/v4_12_runtime_r13/real/2026-09-30/r1/runtime_manifest.json"),
          "reason": "Target-date V4-03 ATR20/MA20/CLV and predecessor owner fields are blocked in the accepted V4-12 head; candidate emits no anchor/event. This proves a missing producer binding, not an absent algorithm.",
          "acceptance": "UNKNOWN preserved; no semantic pass claimed"})

    membership_path = "data/v4/artifact_store/v4_08/V4_08_PIT_MEMBERSHIP_FACTS_20260930_R1.jsonl.gz"
    days, basis = collections.Counter(), collections.Counter()
    for row in gzrows(membership_path):
        day = row.get("target_trade_date") or row.get("membership_asof_date")
        days[day] += 1
        basis[day + ":" + str(row.get("membership_basis"))] += 1
    write("R3_DATED_MEMBERSHIP_AVAILABILITY.json", {"contract_id": "R3_DATED_MEMBERSHIP_AVAILABILITY_V1",
          "accepted_source": ref(membership_path), "dates_found": dict(days), "membership_basis_counts": dict(basis),
          "target_dates": {d: {"availability": "ACCEPTED_DATED_MEMBERSHIP_PRESENT" if d in days else "NO_ACCEPTED_EFFECTIVE_DATE_MEMBER_SOURCE_IN_SCOPED_OWNER_STORE",
                               "count": days.get(d, 0), "strict_pit": "PIT_OBSERVED" if d in days else "NOT_PROVEN"}
                           for d in ("2026-09-28", "2026-09-29", "2026-09-30")},
          "search_scope": ["current V4_08 PIT membership accepted head", "its exact accepted artifact", "data/v4/artifact_store/v4_08"],
          "limitation": "Bounded accepted-owner search; does not claim absence from inaccessible external official sources."})
    write("EXTERNAL_DEPENDENCY_PROOF.json", {"contract_id": "R3_EXTERNAL_DEPENDENCY_PROOF_V1", "blockers": [
        {"scope": "9/28–9/29 historical sector rotation, deltas, retention", "evidence": ref(membership_path),
         "reason": "Scoped accepted V4-08 membership owner contains 9/30 only; no effective-date member authority for the two prior dates.",
         "minimum_input": "dated sector→security membership facts for 9/28 and 9/29 with source revision, provider availability and accepted identity link",
         "alternative": "Never reverse-fill from 9/30; process immediately if exact historical owner arrives; preserve UNKNOWN meanwhile."},
        {"scope": "9/30 V4-12 structure fields", "evidence": ref("reports/v4_12_runtime_r13/real/2026-09-30/r1/runtime_manifest.json"),
         "reason": "Accepted V4-12 head blocks target Core fields and prior owner; real candidate cannot create anchors; formal production permission is false.",
         "minimum_input": "accepted target-date V4-03 publication for the required fields, exact T-1 structure owner, and explicit runtime admission",
         "alternative": "Continue isolated candidate adapter/oracle; no formal publish before authority."},
        {"scope": "relative_sector_state", "evidence": ref("config/v4_13_loo_context_v1_1.json"),
         "reason": "V4-13 LOO remains contract freeze only, runtime_implemented=false; accepted required stock-relative endpoints are not bound.",
         "minimum_input": "implemented versioned LOO owner/consumer and accepted required factor endpoints",
         "alternative": "Keep same-day membership relationship projection; do not substitute self-including sector data."}], "independent_work_continues": True})
    print(json.dumps({"stock_rows": len(current), "fields": counts, "V4_12_rows": len(real), "anchors": anchor_count,
                      "events": event_count, "membership_dates": dict(days)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
