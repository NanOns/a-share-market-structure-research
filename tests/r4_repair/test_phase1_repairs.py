from __future__ import annotations
import json,struct
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from production.daily import _calendar_snapshot,day_source_fingerprint,published_release_binding
from forward.live import append_outcomes,latest_revision,make_observation_rows,publish_observation,read_observation
from run_live_forward import ProductionServices


def _day_bytes(dates):
    record=bytearray()
    for value in dates:
        record.extend(struct.pack("<I",value)+b"\0"*28)
    return bytes(record)


def test_calendar_fills_every_local_index_session(tmp_path):
    path=tmp_path/"reports/phase0_1/MASTER_TRADING_CALENDAR.csv"
    path.parent.mkdir(parents=True)
    pd.DataFrame([{"calendar_date":20260601,"is_market_open":True}]).to_csv(path,index=False)
    for market,code in (("sh","000001"),("sz","399001")):
        target=tmp_path/f"tdx/vipdoc/{market}/lday/{market}{code}.day"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(_day_bytes([20260601,20260602,20260603]))
    frame,_,_=_calendar_snapshot(tmp_path,"20260603",tmp_path/"tdx")
    assert frame.loc[frame.is_market_open,"calendar_date"].tolist()==[20260601,20260602,20260603]


def test_day_identity_detects_metadata_preserving_middle_revision(tmp_path):
    target=tmp_path/"vipdoc/sh/lday/sh600000.day";target.parent.mkdir(parents=True)
    target.write_bytes(_day_bytes([20260601,20260602]));stat=target.stat();before=day_source_fingerprint(tmp_path)[0]
    raw=bytearray(target.read_bytes());raw[4]=1;target.write_bytes(raw)
    import os
    os.utime(target,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    assert day_source_fingerprint(tmp_path)[0]!=before


def _item(sid):
    return {"security_id":sid,"shadow_research_band":"CORE_RESEARCH","steady_queue_tier":"CORE",
            "pullback_queue_tier":None,"breakout_queue_tier":None,"leader_queue_tier":None,
            "early_queue_tier":None}


def test_nulls_are_persistent_and_exited_candidate_reenters():
    first=_item("SH.600000")
    persistent=make_observation_rows(pd.DataFrame([first]),[first],{"SH.600000"},"20260602",1,"x")
    assert persistent.iloc[0].candidate_state=="PERSISTENT"
    exited=make_observation_rows(pd.DataFrame(columns=first),[first],{"SH.600000"},"20260603",1,"y")
    reentered=make_observation_rows(pd.DataFrame([first]),exited.to_dict("records"),{"SH.600000"},"20260604",1,"z")
    assert reentered.iloc[0].candidate_state=="REENTERED"


def test_missing_current_price_is_data_unavailable():
    first=_item("SH.600000")
    frame=make_observation_rows(pd.DataFrame(columns=first),[first],{"SH.600000"},"20260602",1,"x",prices=pd.DataFrame(columns=["security_id","adj_close","adj_high","adj_low"]))
    assert frame.iloc[0].candidate_state=="DATA_UNAVAILABLE"


def test_two_security_outcomes_have_distinct_keys(tmp_path):
    base={"signal_observation_id":"snapshot","horizon":1,"target_revision":1,"outcome_status":"OBSERVED"}
    stats=append_outcomes(tmp_path,[{**base,"security_id":"SH.600000"},{**base,"security_id":"SH.600001"}])
    assert stats["observed"]==2
    assert len(list((tmp_path/"data/forward/outcomes").glob("*.json")))==2


def test_default_outcome_service_computes_security_level_result(tmp_path):
    signal=pd.DataFrame([{**_item("SH.600000"),"candidate_state":"NEW","active_candidate":True,
                          "observation_id":"signal","source_revision_id":1,"adj_close":10.0,
                          "adj_high":10.5,"adj_low":9.5}])
    publish_observation(tmp_path,"20260601",1,signal,{"observation_id":"signal"},{"outcomes":{}})
    target=pd.DataFrame([{**_item("SH.600000"),"candidate_state":"PERSISTENT","active_candidate":True,
                          "observation_id":"target","source_revision_id":1,"adj_close":11.0,
                          "adj_high":12.0,"adj_low":9.0}])
    rows=ProductionServices().outcomes(tmp_path,"20260602",target,["20260601","20260602"])
    assert len(rows)==1 and rows[0]["security_id"]=="SH.600000"
    assert rows[0]["forward_return"]==pytest.approx(.1)
    assert rows[0]["max_high_return"]==pytest.approx(.2)
    assert rows[0]["max_drawdown"]==pytest.approx(-.1)


def test_publish_checks_content_and_ignores_incomplete_revision(tmp_path):
    frame=pd.DataFrame([_item("SH.600000")])
    frame["candidate_state"]="NEW"
    identity={"observation_id":"one"}
    receipt={"outcomes":{}}
    assert publish_observation(tmp_path,"20260602",1,frame,identity,receipt)=="PUBLISHED"
    assert latest_revision(tmp_path,"20260602").name=="revision_1"
    altered=frame.copy();altered["shadow_research_band"]="DIAGNOSTIC_ONLY"
    with pytest.raises(RuntimeError,match="OBSERVATION_CONFLICT_BLOCKED"):
        publish_observation(tmp_path,"20260602",1,altered,identity,receipt)
    parquet=tmp_path/"data/forward/observations/20260602/revision_1/FORWARD_OBSERVATION.parquet"
    pq.write_table(pa.Table.from_pandas(altered,preserve_index=False),parquet)
    with pytest.raises(RuntimeError,match="FORWARD_OBSERVATION_HASH_MISMATCH"):
        read_observation(parquet.parent)
    (tmp_path/"data/forward/observations/20260602/revision_2").mkdir()
    assert latest_revision(tmp_path,"20260602") is None


def test_publish_recovers_orphaned_data_directory(tmp_path):
    orphan=tmp_path/"data/forward/observations/20260602/revision_1";orphan.mkdir(parents=True)
    (orphan/"partial").write_text("uncommitted")
    frame=pd.DataFrame([_item("SH.600000")]);frame["candidate_state"]="NEW"
    assert publish_observation(tmp_path,"20260602",1,frame,{"observation_id":"one"},{"outcomes":{}})=="PUBLISHED"
    assert not (orphan/"partial").exists()


def test_noop_binding_returns_existing_release_not_invocation(tmp_path):
    release=tmp_path/"reports/releases/20260603/published-release"
    release.mkdir(parents=True)
    computation={"version":"test","sha256":"a"*64}
    (release/"PRODUCTION_RECEIPT.json").write_text(
        json.dumps({"computation_identity":computation}),encoding="utf8")
    pointer={"run_id":"published-release","release_path":str(release)}
    value=published_release_binding(pointer,release,"new-invocation")
    assert value["invocation_id"]=="new-invocation"
    assert value["published_release_id"]=="published-release"
    assert value["published_release_exists"] is True
    assert value["published_computation_identity"]==computation
