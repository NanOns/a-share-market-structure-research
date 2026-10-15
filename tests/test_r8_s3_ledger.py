from __future__ import annotations

from contextlib import nullcontext

import pytest

from workbench_analysis.forward_r7 import legacy_observation_id, make_observation_id
from workbench_db.forward_r7_store import ForwardR7Store


def _row(*, lane="RETROSPECTIVE_RESEARCH", revision=1, source_digest="a" * 64):
    return dict(rule_id="STOCK_RIGHT_STRUCTURE_EVENT_R1", rule_version="1.0.0",
        T0="2026-10-13", entity_type="STOCK", entity_id="SEC-1", status="MATCH",
        evidence_lane=lane, evidence_class=lane, capture_revision=revision,
        revision=revision, source_digest=source_digest, source_hashes={"raw":source_digest},
        values={"close":10.0})


def test_observation_id_binds_lane_revision_and_source_digest():
    base=_row()
    assert make_observation_id(base)!=make_observation_id(_row(lane="LIVE_OOS"))
    assert make_observation_id(base)!=make_observation_id(_row(revision=2))
    assert make_observation_id(base)!=make_observation_id(_row(source_digest="b"*64))
    assert legacy_observation_id(base)==legacy_observation_id(_row(lane="LIVE_OOS",revision=2))


def test_r6_risk_pg_owner_keeps_r1_history_and_accepts_single_r2_producer():
    from workbench_service.operational_risk_v1 import CONTRACT
    from workbench_db.v4_operational_risk_pg_r1 import RISK_INPUT_CONTRACTS
    assert CONTRACT=="V4_OPERATIONAL_RISK_CHANGE_R2"
    assert RISK_INPUT_CONTRACTS==("V4_OPERATIONAL_RISK_CHANGE_R1","V4_OPERATIONAL_RISK_CHANGE_R2")


def test_forward_revision_filters_are_allowed_only_on_forward_routes():
    from workbench_db.v4_read_index_r2 import validate_query
    query={"trade_date":"2026-10-13","context_token":"token","lane":"historical",
           "revision":"2","limit":"20"}
    assert validate_query(query,"token",["2026-10-13"],"2026-10-13",
                          "/api/v4/forward/observations")=="2026-10-13"


def test_legacy_daily_facts_are_lane_h_only_and_versioned_facts_keep_lane(monkeypatch):
    old=_row(lane="LIVE_OOS")
    old.pop("evidence_lane"); old.pop("capture_revision"); old.pop("revision"); old.pop("source_digest")
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_read_facts",lambda kind:[("2026-10-13",dict(trade_date="2026-10-13",lane="LIVE_OOS",rows=[old]))])
    bundle=store._daily_facts()[0]
    assert bundle["lane"]=="RETROSPECTIVE_RESEARCH"
    assert bundle["rows"][0]["evidence_lane"]=="RETROSPECTIVE_RESEARCH"
    assert bundle["rows"][0]["evidence_class"]=="RETROSPECTIVE_RESEARCH"
    assert bundle["identity_contract"].endswith("LEGACY_LANE_H")


def test_same_day_lane_reads_and_counts_are_partitioned(monkeypatch):
    h=_row(lane="RETROSPECTIVE_RESEARCH")
    l=_row(lane="LIVE_OOS")
    bundles=[dict(trade_date=h["T0"],lane="RETROSPECTIVE_RESEARCH",rows=[h]),
             dict(trade_date=l["T0"],lane="LIVE_OOS",rows=[l])]
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_daily_facts",lambda:bundles)
    monkeypatch.setattr(store,"_latest_publish_index",lambda *a,**k:dict(generation=1,trade_date="2026-10-13"))
    assert store.read_universe(lane="RETROSPECTIVE_RESEARCH")["total"]==1
    assert store.read_universe(lane="LIVE_OOS")["total"]==1
    counts=store.read_counts()
    assert counts["historical"]["count"]==1
    assert counts["live"]["count"]==1


def test_due_settlement_appends_revision_and_is_idempotent(monkeypatch):
    row=_row()
    obs_id=make_observation_id(row)
    daily=[dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2",trade_date=row["T0"],
                lane="RETROSPECTIVE_RESEARCH",rows=[row])]
    settlements=[dict(identity_contract="V4_FORWARD_SETTLEMENT_R2",lane="RETROSPECTIVE_RESEARCH",revision=1,
        items=[dict(observation_id=obs_id,horizon_sessions=1,due_date="2026-10-14",
            schedule_status="DUE_SOURCE_NOT_ACCEPTED",settlement_revision=1)])]
    appended=[]
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_daily_facts",lambda:daily)
    monkeypatch.setattr(store,"_settlement_facts",lambda:settlements)
    monkeypatch.setattr(store,"_connect",lambda:nullcontext(object()))
    def append(pg,kind,key,payload,source_sha256=None):
        appended.append((kind,key,payload))
        if kind=="r7_settlement_schedule":
            settlements.append(payload)
    monkeypatch.setattr(store,"_append_fact",append)
    result=store.advance_due_settlements(accepted_trade_date="2026-10-14",
        accepted_source_dates={"2026-10-14"},prices_by_date={"2026-10-14":{"SEC-1":{"close":11.0}}},
        source_digest="b"*64,source_digests_by_date={"2026-10-14":"c"*64})
    assert result["status"]=="APPENDED" and result["appended"]==1
    updated=appended[0][2]["items"][0]
    assert updated["schedule_status"]=="SETTLED"
    assert updated["settlement_revision"]==2
    assert updated["settlement"]["nominal_return"]==pytest.approx(0.1)
    assert updated["price_basis"]=="NOMINAL_UNADJUSTED_CLOSE"
    retry=store.advance_due_settlements(accepted_trade_date="2026-10-15",
        accepted_source_dates={"2026-10-14","2026-10-15"},
        prices_by_date={"2026-10-14":{"SEC-1":{"close":11.0}}},
        source_digest="b"*64,source_digests_by_date={"2026-10-14":"c"*64})
    assert retry["status"]=="NO_DUE_SETTLEMENTS"


def test_settlement_reads_only_latest_capture_revision_by_lane(monkeypatch):
    old=_row(revision=1,source_digest="a"*64)
    current=_row(revision=2,source_digest="b"*64)
    old_id=make_observation_id(old); current_id=make_observation_id(current)
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_daily_facts",lambda **kwargs:[
        dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2",lane="RETROSPECTIVE_RESEARCH",rows=[old]),
        dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2",lane="RETROSPECTIVE_RESEARCH",rows=[current])])
    monkeypatch.setattr(store,"_settlement_facts",lambda **kwargs:[
        dict(identity_contract="V4_FORWARD_SETTLEMENT_R2",lane="RETROSPECTIVE_RESEARCH",revision=1,
             items=[dict(observation_id=old_id,horizon_sessions=1,due_date="2026-10-14",
                         schedule_status="SETTLED",settlement={"status":"SETTLED","nominal_return":0.2})]),
        dict(identity_contract="V4_FORWARD_SETTLEMENT_R2",lane="RETROSPECTIVE_RESEARCH",revision=2,
             items=[dict(observation_id=current_id,horizon_sessions=1,due_date="2026-10-14",
                         schedule_status="SOURCE_GAP",settlement={"status":"SOURCE_GAP"})])])
    result=store.read_settlement()
    assert result["total"]==1
    assert result["items"][0]["revision"]==2
    assert result["items"][0]["status"]=="SOURCE_GAP"
    assert result["aggregates"][0]["return_denominator"]==0
    assert store.read_matured_count()==0


def test_settlement_reader_selects_latest_append_revision(monkeypatch):
    row=_row(); obs=make_observation_id(row)
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_daily_facts",lambda **kwargs:[dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R2",
        lane="RETROSPECTIVE_RESEARCH",rows=[row])])
    monkeypatch.setattr(store,"_settlement_facts",lambda **kwargs:[
        dict(identity_contract="V4_FORWARD_SETTLEMENT_R2",lane="RETROSPECTIVE_RESEARCH",revision=1,
             items=[dict(observation_id=obs,horizon_sessions=1,due_date="2026-10-14",
                         schedule_status="SOURCE_GAP",settlement_revision=1)]),
        dict(identity_contract="V4_FORWARD_SETTLEMENT_R2",lane="RETROSPECTIVE_RESEARCH",revision=2,
             items=[dict(observation_id=obs,horizon_sessions=1,due_date="2026-10-14",
                         schedule_status="SETTLED",settlement_revision=2,
                         settlement={"status":"SETTLED","nominal_return":0.05})])])
    result=store.read_settlement()
    assert result["total"]==1 and result["items"][0]["settlement_revision"]==2
    assert result["items"][0]["status"]=="SETTLED"
    assert result["aggregates"][0]["return_denominator"]==1
    assert store.read_matured_count()==1
    assert store.read_settlement(lane="RETROSPECTIVE_RESEARCH")["aggregates"][0]["lane"]=="RETROSPECTIVE_RESEARCH"


def test_settlement_append_failure_records_retryable_failure(monkeypatch):
    row=_row()
    obs_id=make_observation_id(row)
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_daily_facts",lambda:[dict(lane="RETROSPECTIVE_RESEARCH",rows=[row])])
    monkeypatch.setattr(store,"_settlement_facts",lambda:[dict(lane="RETROSPECTIVE_RESEARCH",revision=1,
        items=[dict(observation_id=obs_id,horizon_sessions=1,due_date="2026-10-14",
                    schedule_status="DUE_SOURCE_NOT_ACCEPTED")])])
    monkeypatch.setattr(store,"_connect",lambda:nullcontext(object()))
    monkeypatch.setattr(store,"_append_fact",lambda *args,**kwargs:(_ for _ in ()).throw(OSError("PG unavailable")))
    failures=[]
    monkeypatch.setattr(store,"record_failure",lambda **kwargs:failures.append(kwargs) or {"status":"FAILED_RECORDED"})
    result=store.advance_due_settlements(accepted_trade_date="2026-10-14",
        accepted_source_dates={"2026-10-14"},prices_by_date={"2026-10-14":{"SEC-1":{"close":11.0}}},
        source_digest="b"*64)
    assert result["status"]=="RETRY_REQUIRED"
    assert failures and failures[0]["stage"]=="SETTLEMENT_ADVANCE"
    assert failures[0]["payload"]["retryable"] is True


def test_legacy_no_quote_repair_appends_revision_and_repeats_idempotently(monkeypatch):
    row=_row()
    legacy_id=legacy_observation_id(row)
    original=dict(observation_id=legacy_id,horizon_sessions=1,due_date="2026-10-14",
        schedule_status="NO_QUOTE",reason="OLD_R7_NO_QUOTE",settlement={"status":"NO_QUOTE"})
    daily=[dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R1_LEGACY_LANE_H",
        trade_date=row["T0"],lane="RETROSPECTIVE_RESEARCH",rows=[row])]
    settlements=[dict(identity_contract="V4_FORWARD_SETTLEMENT_R1_LEGACY_LANE_H",
        trade_date=row["T0"],lane="RETROSPECTIVE_RESEARCH",items=[original])]
    appended=[]
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_daily_facts",lambda:daily)
    monkeypatch.setattr(store,"_settlement_facts",lambda: settlements)
    monkeypatch.setattr(store,"_connect",lambda:nullcontext(object()))
    def append(pg,kind,key,payload,source_sha256=None):
        appended.append((kind,key,payload))
        if kind=="r7_settlement_schedule":settlements.append(payload)
    monkeypatch.setattr(store,"_append_fact",append)
    assert store.pending_due_dates(accepted_source_dates={"2026-10-14"}) == ["2026-10-14"]
    assert store.legacy_no_quote_due_dates() == ["2026-10-14"]
    review=store.review_legacy_no_quote(accepted_trade_date="2026-10-15",
        accepted_source_dates={"2026-10-14","2026-10-15"},
        prices_by_date={"2026-10-14":{"SEC-1":{"close":11.0}}},
        source_digests_by_date={"2026-10-14":"c"*64},
        source_bindings_by_date={"2026-10-14":{"raw":{"sha256":"c"*64}}},
        reviewed_at="2026-10-15T16:00:00+08:00")
    assert review["corrected_count"]==1
    assert review["legacy_no_quote_count"]==1
    correction=appended[0][2]["items"][0]
    assert correction["schedule_status"]=="SETTLED"
    assert correction["old_revision"]==1 and correction["new_revision"]==2
    assert correction["correction_type"]=="LEGACY_NO_QUOTE_REVIEW_R1"
    assert correction["source_digest"]=="c"*64
    assert original["schedule_status"]=="NO_QUOTE" and "settlement_revision" not in original
    retry=store.review_legacy_no_quote(accepted_trade_date="2026-10-15",
        accepted_source_dates={"2026-10-14","2026-10-15"},
        prices_by_date={"2026-10-14":{"SEC-1":{"close":11.0}}},
        source_digests_by_date={"2026-10-14":"c"*64},
        reviewed_at="2026-10-15T16:00:00+08:00")
    assert retry["appended"]==0


def test_legacy_no_quote_requires_accepted_source_or_security_level_proof(monkeypatch):
    row=_row(); legacy_id=legacy_observation_id(row)
    old=dict(observation_id=legacy_id,horizon_sessions=1,due_date="2026-10-14",
        schedule_status="NO_QUOTE",source_digest="d"*64,
        settlement={"status":"NO_QUOTE","reason":"SECURITY_LEVEL_ACCEPTED_SOURCE_FACT",
                    "source_hash":"d"*64})
    daily=[dict(identity_contract="V4_FORWARD_OBSERVATION_ID_R1_LEGACY_LANE_H",
        trade_date=row["T0"],lane="RETROSPECTIVE_RESEARCH",rows=[row])]
    settlements=[dict(identity_contract="V4_FORWARD_SETTLEMENT_R1_LEGACY_LANE_H",
        lane="RETROSPECTIVE_RESEARCH",items=[old])]
    appended=[]
    store=object.__new__(ForwardR7Store)
    monkeypatch.setattr(store,"_daily_facts",lambda:daily)
    monkeypatch.setattr(store,"_settlement_facts",lambda:settlements)
    monkeypatch.setattr(store,"_connect",lambda:nullcontext(object()))
    def append(pg,kind,key,payload,source_sha256=None):
        appended.append(payload)
        settlements.append(payload)
    monkeypatch.setattr(store,"_append_fact",append)
    legitimate=store.review_legacy_no_quote(accepted_trade_date="2026-10-15",
        accepted_source_dates={"2026-10-14","2026-10-15"},
        prices_by_date={"2026-10-14":{"SEC-1":{"source_status":"SUSPENDED","source_hash":"d"*64}}},
        source_digests_by_date={"2026-10-14":"d"*64})
    assert legitimate["legitimate_security_proofs"]==1
    assert legitimate["appended"]==1
    assert appended[0]["items"][0]["schedule_status"]=="SUSPENDED"
    rebound=store.review_legacy_no_quote(accepted_trade_date="2026-10-15",
        accepted_source_dates={"2026-10-14","2026-10-15"},
        prices_by_date={"2026-10-14":{"SEC-1":{"source_status":"SUSPENDED","source_hash":"e"*64}}},
        source_digests_by_date={"2026-10-14":"e"*64},
        reviewed_at="2026-10-15T16:01:00+08:00")
    assert rebound["legitimate_security_proofs"]==1 and rebound["appended"]==1
    assert appended[-1]["items"][0]["correction_reason"]=="LEGACY_NO_QUOTE_SOURCE_REBOUND"
    unaccepted=store.review_legacy_no_quote(accepted_trade_date="2026-10-15",
        accepted_source_dates={"2026-10-15"},prices_by_date={},source_digests_by_date={})
    assert unaccepted["corrected_count"]==1
    correction=appended[-1]["items"][0]
    assert correction["schedule_status"]=="DUE_SOURCE_NOT_ACCEPTED"
    assert correction["source_digest"] is None
    assert correction["settlement"]["reason"]=="LEGACY_NO_QUOTE_DUE_SOURCE_NOT_ACCEPTED"
