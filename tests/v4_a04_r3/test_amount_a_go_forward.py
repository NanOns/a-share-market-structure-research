from copy import deepcopy
from datetime import date,timedelta
from decimal import Decimal
import json
from pathlib import Path
import pytest
from workbench_analysis.amount_a_go_forward_r3 import calculate_sector_amount,currency,read_verified_observations,compute_ledger_candidate
from workbench_analysis.forward_pit_ledger_r2 import bound,reference

ROOT=Path(__file__).resolve().parents[2]


def engineering_input(member_count=3):
    sessions=[(date(2026,1,1)+timedelta(days=i)).isoformat() for i in range(21)]
    members=["ENGINEERING_MEMBER_"+str(i) for i in range(member_count)]
    observations={day:{"members":members,"membership_basis":"PIT_OBSERVED_ACCEPTED", "amounts":{m:{"amount":100,"unit":"CNY_YUAN","state":"ACTUAL_TRADED"} for m in members}} for day in sessions}
    observations[sessions[-1]]["amounts"][members[0]]["amount"]=300
    return dict(sector_id="ENGINEERING_SECTOR",target=sessions[-1],sessions=sessions,observations=observations,mode="SYNTHETIC_ENGINEERING_ONLY")


def test_complete_h21_value_known_without_universal_threshold_or_consumer_permission():
    x=calculate_sector_amount(**engineering_input())
    assert Decimal(x["amount_a_value"])==Decimal(5)/3
    assert x["arithmetic_status"]=="KNOWN" and x["comparable_member_count"]==3
    assert x["global_coverage_threshold"] is None and x["consumer_permission"]["formal"] is False
    assert x["quality_reasons"]==[]


def test_low_coverage_is_consumer_decision_not_null_arithmetic():
    args=engineering_input(2)
    args["observations"][args["target"]]["members"]=["ENGINEERING_MEMBER_0","ENGINEERING_MEMBER_1"]+["NEW_"+str(i) for i in range(5)]
    x=calculate_sector_amount(**args)
    assert x["amount_a_value"]=="2" and Decimal(x["coverage"])==Decimal(2)/7
    assert x["consumer_permission"]["formal"] is False


@pytest.mark.parametrize("mutation,reason",[("membership_gap","ACCEPTED_PIT_MEMBERSHIP_OBSERVATION_GAP"),("basis","PIT_MEMBERSHIP_NOT_PROVED"),("amount_gap","COMMON_MEMBER_SOURCE_GAP_UNKNOWN"),("unknown_zero","COMMON_MEMBER_SOURCE_GAP_UNKNOWN"),("bad_unit","COMMON_MEMBER_SOURCE_GAP_UNKNOWN")])
def test_actual_source_or_membership_gap_remains_unknown(mutation,reason):
    args=engineering_input();day=args["sessions"][3]
    if mutation=="membership_gap":args["observations"].pop(day)
    elif mutation=="basis":args["observations"][day]["membership_basis"]="CURRENT_SNAPSHOT_RECONSTRUCTED"
    elif mutation=="amount_gap":args["observations"][day]["amounts"].pop("ENGINEERING_MEMBER_0")
    elif mutation=="unknown_zero":args["observations"][day]["amounts"]["ENGINEERING_MEMBER_0"]["amount"]=0
    else:args["observations"][day]["amounts"]["ENGINEERING_MEMBER_0"]["unit"]="SHARES"
    x=calculate_sector_amount(**args)
    assert x["amount_a_value"] is None and reason in x["quality_reasons"]


def test_confirmed_suspension_zero_known_and_conflict_unknown():
    args=engineering_input(1);rows=args["observations"][args["target"]]["amounts"]
    rows["ENGINEERING_MEMBER_0"]={"amount":0,"unit":"CNY_YUAN","state":"SUSPENDED_CONFIRMED"}
    assert calculate_sector_amount(**args)["amount_a_value"]=="0"
    rows["ENGINEERING_MEMBER_0"]["amount"]=1
    assert calculate_sector_amount(**args)["amount_a_value"] is None


def test_no_twenty_rows_backfill_for_missing_market_session():
    args=engineering_input();removed=args["sessions"][5]
    args["observations"].pop(removed)
    x=calculate_sector_amount(**args)
    assert removed in x["missing_accepted_membership_sessions"] and len(x["h21_sessions"])==21
    assert x["amount_a_value"] is None


def test_namespace_excludes_stock_amr_and_ordinary_amount():
    x=json.loads((ROOT/"config/a04_amount_a_namespace_r3.json").read_text(encoding="utf8"))
    assert x["canonical_namespace"]=="SECTOR.amount_a_value"
    assert {"STOCK.amount_ratio20","STOCK.amr20_mean_prior","SOURCE.RAW_AMOUNT","OWNER.AMOUNT"}<=set(x["excluded_namespaces"])
    assert x["stock_confirmation_dependency"] is False


def test_currency_and_order_strict():
    assert currency(1,"CNY_WAN")==10000
    for unit in ("SHARES","TDX_SOURCE_NATIVE"):
        with pytest.raises(ValueError):currency(1,unit)
    args=engineering_input();args["sessions"].append(args["sessions"][-1])
    with pytest.raises(ValueError):calculate_sector_amount(**args)


def test_real_warmup_historical_block_no_head_move_and_exact_observation_readback():
    bindings=[reference(ROOT,p) for p in sorted((ROOT/"data/v4/a04_go_forward_r3/observations").glob("*.json"))]
    assert len(bindings)==1
    items=read_verified_observations(ROOT,bindings)
    assert items[0]["target_trade_date"]=="2026-09-30"
    assert items[0]["membership_basis"]=="PIT_OBSERVED_ACCEPTED"
    x=compute_ledger_candidate(ROOT,bindings,target="2026-09-30")
    assert x["rows"] and all(r["amount_a_value"] is None for r in x["rows"])
    assert all(len(r["missing_accepted_membership_sessions"])==20 for r in x["rows"])
    assert x["historical_limitation"]=="PRE_BASELINE_HISTORICAL_AMOUNT_A_NOT_FORMALLY_RECONSTRUCTABLE"
    assert x["formal_consumer_enabled"] is False and x["stock_confirmation_dependency"] is False
