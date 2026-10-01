from fractions import Fraction
from decimal import Decimal
import json
from pathlib import Path
from copy import deepcopy
from workbench_analysis.forward_pit_ledger_r2 import bound
from workbench_analysis.amount_a_go_forward_r3 import calculate_sector_amount
from .test_amount_a_go_forward import engineering_input

ROOT=Path(__file__).resolve().parents[2]


def test_fraction_oracle_without_producer_results_or_quality_defaults():
    args=engineering_input(4)
    for position,day in enumerate(args["sessions"]):
        for index,member in enumerate(args["observations"][day]["members"]):
            args["observations"][day]["amounts"][member]["amount"]=(position+1)*(index+2)*17+position%3
    sums={day:sum((Fraction(str(row["amount"])) for row in args["observations"][day]["amounts"].values()),Fraction(0)) for day in args["sessions"]}
    independently=sums[args["target"]]/(sum((sums[day] for day in args["sessions"][:-1]),Fraction(0))/20)
    expected=Decimal(independently.numerator)/Decimal(independently.denominator)
    result=calculate_sector_amount(**args)
    assert Decimal(result["amount_a_value"])==expected
    assert result["comparable_member_count"]==4 and result["consumer_permission"]["formal"] is False
    reversed_args=deepcopy(args)
    reversed_args["observations"]=dict(reversed(list(args["observations"].items())))
    for observation in reversed_args["observations"].values():observation["members"]=list(reversed(observation["members"]))
    assert calculate_sector_amount(**reversed_args)==result


def test_real_scope_archaeology_consumer_and_candidate_evidence_byte_readback():
    proof=json.loads((ROOT/"reports/audits/a04_r3/A04_R3_REAL_SCOPED_CANDIDATE_PROOF_R1.json").read_text(encoding="utf8"))
    for field in ("task","master","scope_external_audit","stage_entry","data_head","stage_head","namespace_contract","producer_contract"):
        bound(ROOT,proof[field])
    for runtime in proof["runtime_bindings"]:bound(ROOT,runtime)
    archaeology=json.loads(bound(ROOT,proof["threshold_authority_archaeology"]))
    assert archaeology["universal_threshold"] is None and archaeology["missing_global_threshold_is_arithmetic_blocker"] is False
    for record in archaeology["records"]:bound(ROOT,record["source"]["binding"])
    scopes=json.loads(bound(ROOT,proof["h21_membership_scope"]))
    for source in scopes["inventory"]:bound(ROOT,source["binding"])
    assert scopes["actual_accepted_dates"]==["2026-09-30"] and scopes["proved_sessions"]==1
    assert len(scopes["missing_accepted_h21_dates"])==20
    consumers=json.loads(bound(ROOT,proof["consumer_gates"]))
    for consumer in consumers["records"]:
        assert consumer["formal_consumer_enabled"] is False
        for source in consumer.get("source_bindings",[]):bound(ROOT,source)
    candidate=json.loads(bound(ROOT,proof["candidate"]))
    assert len(candidate["rows"])==378==proof["real_sector_rows"]
    assert proof["real_known_arithmetic_rows"]==0
    assert all(r["namespace"]=="SECTOR.amount_a_value" and r["amount_a_value"] is None for r in candidate["rows"])
    assert proof["stock_confirmation_dependency"] is False and proof["formal_consumer_enabled"] is False
