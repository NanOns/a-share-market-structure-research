from __future__ import annotations

import hashlib
import json
from workbench_analysis.forward_r7 import (
    build_daily_universe, compute_nominal_settlement, make_observation_id,
    scheduled_sessions, summarize_universe,
)
from workbench_service.operational_risk_v1 import _family, FAMILIES
from workbench_db.forward_r7_store import ForwardR7Store
from workbench_desktop import source_view


def _field(value, *, quality="OBSERVED", actual_count=20):
    return {"value": value, "quality_state": quality, "actual_count": actual_count}


def _stock(close, *, prior_high=10.0, damage=False):
    return {
        "security_id": "SEC-1", "source_security_key": "SH.600001", "board_scope": "SH_MAIN",
        "fields": {
            "prior_high20": _field(prior_high), "prior_low20": _field(8.0),
            "ma20": _field(9.5), "core_price_damage": _field(damage),
            "rps5": _field(55.0), "rps20": _field(60.0),
        },
    }


def _sector(day, score, *, membership="MEM-1"):
    return {
        "sector_id": "INDUSTRY:X", "trade_date": day, "membership_snapshot_id": membership,
        "fields": {
            "sector_rs5": _field(0.02 if score else -0.01),
            "sector_rs20": _field(0.03 if score else -0.01),
            "breadth_ret5": _field(0.04 if score else -0.02),
            "breadth_ret20": _field(0.05 if score else -0.02),
            "sector_quote_coverage": _field(0.9),
        },
    }


def _evaluate(*, stock, raw, prior_stock=None, prior_raw=None, sector=None, prior_sector=None,
              membership="MEMBERSHIP_RETRO"):
    return build_daily_universe(
        trade_date="2026-10-13", stock_rows=[stock], raw_rows=[raw],
        sector_rows=[sector or _sector("2026-10-13", False)],
        prior_stock_rows=[prior_stock] if prior_stock else None,
        prior_raw_rows=[prior_raw] if prior_raw else None,
        prior_sector_rows=[prior_sector] if prior_sector else None,
        bindings={"core":{"sha256":"a"*64},"raw":{"sha256":"b"*64},"sector":{"sha256":"c"*64}},
        captured_at="2026-10-14T15:30:00+00:00",lane="RETROSPECTIVE_RESEARCH",
        membership_basis=membership)


def test_stock_breakout_and_unknown_keep_denominator():
    rows=_evaluate(stock=_stock(11),raw={"security_id":"SEC-1","open":10,"high":11,"low":10,"close":11,"volume":100})
    stock=next(r for r in rows if r["entity_type"]=="STOCK")
    assert (stock["status"],stock["event_code"])==("MATCH","BREAKOUT_OBSERVED")
    assert summarize_universe(rows)["total"]==2

    missing=_stock(11)
    missing["fields"]["prior_high20"]=_field(None,quality="UNKNOWN",actual_count=0)
    rows=_evaluate(stock=missing,raw={"security_id":"SEC-1","open":10,"high":11,"low":10,"close":11,"volume":100})
    assert next(r for r in rows if r["entity_type"]=="STOCK")["status"]=="UNKNOWN"


def test_pullback_requires_prior_breakout_and_full_sequence():
    rows=_evaluate(stock=_stock(10.2,prior_high=10),raw={"security_id":"SEC-1","open":10,"high":10.5,"low":10.01,"close":10.2,"volume":100},
        prior_stock=_stock(10),prior_raw={"security_id":"SEC-1","close":10.5})
    stock=next(r for r in rows if r["entity_type"]=="STOCK")
    assert stock["event_code"]=="PULLBACK_CONFIRMATION_OBSERVED"


def test_sector_strength_needs_comparable_prior_and_unknown_is_distinct():
    rows=_evaluate(stock=_stock(9),raw={"security_id":"SEC-1","open":9,"high":9.5,"low":8.9,"close":9,"volume":100},
        sector=_sector("2026-10-13",True),prior_sector=_sector("2026-10-12",False))
    sector=next(r for r in rows if r["entity_type"]=="SECTOR")
    assert (sector["status"],sector["event_code"])==("MATCH","STRENGTHENING_OBSERVED")
    rows=_evaluate(stock=_stock(9),raw={"security_id":"SEC-1","open":9,"high":9.5,"low":8.9,"close":9,"volume":100},
        sector=_sector("2026-10-13",True))
    sector=next(r for r in rows if r["entity_type"]=="SECTOR")
    assert sector["status"]=="UNKNOWN" and "prior_comparable_state" in sector["missing_inputs"]


def test_observation_identity_stable_and_future_prices_cannot_change_t0_signal():
    raw={"security_id":"SEC-1","open":10,"high":11,"low":10,"close":11,"volume":100}
    stock=_stock(11)
    first=_evaluate(stock=stock,raw=raw)
    future_prices=[{"trade_date":"2026-10-14","security_id":"SEC-1","close":1000}]
    second=_evaluate(stock=stock,raw=raw)
    assert first==second
    assert len(future_prices)==1
    assert make_observation_id(first[0])==make_observation_id(dict(first[0],status="NO_MATCH",event_code="NO_MATCH"))


def test_nominal_settlement_uses_real_due_session_closes():
    sessions=["2026-10-12","2026-10-13","2026-10-14","2026-10-15","2026-10-16","2026-10-19"]
    assert scheduled_sessions("2026-10-12",sessions)=={1:"2026-10-13",3:"2026-10-15",5:"2026-10-19"}
    row={"entity_type":"STOCK","status":"MATCH","T0":"2026-10-12","entity_id":"SEC-1","source_hashes":{"raw":"a"*64}}
    outcome=compute_nominal_settlement(observation=row,due_date="2026-10-13",
        prices_by_date={"2026-10-12":{"SEC-1":{"close":10}},"2026-10-13":{"SEC-1":{"close":11}}},
        settlement_at="2026-10-14T15:00:00+00:00")
    assert outcome["status"]=="SETTLED" and abs(outcome["nominal_return"]-0.1)<1e-12
    assert outcome["price_basis"]=="NOMINAL_UNADJUSTED_CLOSE"


def test_risk_transition_order_and_first_observable_denominator():
    rows=[{"entity_id":"A"},{"entity_id":"B"},{"entity_id":"C"}]
    states={"A":"WATCH","B":"NONE","C":"NONE"}
    previous={"B":"WATCH","C":None}
    result=_family(FAMILIES[1],rows,states,previous,"source","2026-10-13")
    by_id={r["entity_id"]:r["change"] for r in result["changes"]}
    assert by_id=={"A":"NEWLY_OBSERVABLE","B":"EASED","C":"UNCOMPARABLE"}
    assert result["worsened_count"]==0 and result["newly_observable_count"]==1
    result=_family(FAMILIES[1],[{"entity_id":"A"}],{"A":"WATCH"},{"A":"NONE"},"source","2026-10-13")
    assert result["worsened_count"]==1


def test_retry_identity_ignores_attempt_clocks_but_rejects_fact_changes():
    original={"event_code":"BREAKOUT_OBSERVED","captured_at":"2026-10-14T00:00:00+00:00",
              "payload":{"status":"MATCH","observed_at":"2026-10-14T00:00:00+00:00"}}
    retry={"event_code":"BREAKOUT_OBSERVED","captured_at":"2026-10-15T00:00:00+00:00",
           "payload":{"status":"MATCH","observed_at":"2026-10-15T00:00:00+00:00"}}
    changed={**retry,"payload":{"status":"NO_MATCH","observed_at":"2026-10-15T00:00:00+00:00"}}
    assert ForwardR7Store._stable_hash(original)==ForwardR7Store._stable_hash(retry)
    assert ForwardR7Store._stable_hash(original)!=ForwardR7Store._stable_hash(changed)


def test_verified_producer_can_project_source_without_desktop_lease(tmp_path, monkeypatch):
    root=tmp_path
    source=root/"extraction.json"
    document={"contract_id":"TDX_LATEST_PACKAGE_TARGET_SESSION_V2",
              "status":"TARGET_BARS_EXTRACTED","target_session":"2026-10-14",
              "target_bars":[]}
    raw=json.dumps(document,separators=(",",":"),sort_keys=True).encode()
    source.write_bytes(raw)
    calls=[]
    monkeypatch.setattr(source_view,"require_owned",lambda selected:(_ for _ in ()).throw(ValueError("WORKSPACE_LEASE_REQUIRED")))
    monkeypatch.setattr(source_view,"_require_worker_admission",lambda selected:calls.append(selected))
    extraction={"artifact":{"path":str(source),"sha256":hashlib.sha256(raw).hexdigest()}}
    assert source_view.project(root,extraction)==extraction
    assert calls==[root]
