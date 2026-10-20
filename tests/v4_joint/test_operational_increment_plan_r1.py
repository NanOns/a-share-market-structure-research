from copy import deepcopy
import pytest
from workbench_analysis.operational_increment_plan_v1 import plan, assert_old_owners_unchanged, verify_history_overlap

SESSIONS=['2026-09-23','2026-09-24','2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-08','2026-10-09','2026-10-12','2026-10-13']


def parent():
    return dict(accepted_trade_date='2026-10-12',dates=SESSIONS[3:-1],
                owners={d:{'core':{'path':d+'.gz','sha256':'a'*64}} for d in SESSIONS[3:-1]})


def test_normal_append_does_not_compute_published_days():
    source=parent();before=deepcopy(source)
    result=plan(source,'2026-10-13',SESSIONS)
    assert result['mode']=='APPEND_DAY'
    assert result['compute_sessions']==['2026-10-13']
    assert result['history_dependencies']==['2026-10-12','2026-10-08','2026-09-30','2026-09-29']
    assert source==before
    result['historical_owners']['2026-10-12']['core']['path']='changed'
    assert source==before


def test_revision_is_explicit_repair_and_current_replay_is_not_append():
    assert plan(parent(),'2026-10-13',SESSIONS,revisions=['GBBQ_REVISION'])['mode']=='RANGE_REPAIR'
    result=plan(parent(),'2026-10-12',SESSIONS,replay_current=True)
    assert result['mode']=='FULL_REBUILD'
    assert result['published_sessions'].count('2026-10-12')==1


@pytest.mark.parametrize('target',['2026-10-09','2026-10-14','2026-09-24'])
def test_non_successor_fails_closed(target):
    with pytest.raises(ValueError):plan(parent(),target,SESSIONS)


def test_old_owner_mutation_is_rejected():
    source=parent();candidate=dict(accepted_trade_date='2026-10-13',owners=deepcopy(source['owners']))
    assert_old_owners_unchanged(source,candidate)
    candidate['owners']['2026-10-12']['core']['sha256']='b'*64
    with pytest.raises(ValueError,match='IMMUTABLE_OWNER_CHANGED'):assert_old_owners_unchanged(source,candidate)


def sample():
    return {'S':('SH.600001',[(20261012,1000,1100,900,1050,5000.,100,0),(20261013,1050,1200,1000,1150,6000.,110,0)])},[dict(security_id='S',bars=[dict(trade_date='2026-10-12',raw_ohlc=[10.,11.,9.,10.5],amount=5000.,volume=100)])]


def test_append_retains_exact_historical_input_and_allows_retention_roll():
    cache,saved=sample();verify_history_overlap(cache,saved)
    saved[0]['bars'].insert(0,dict(trade_date='2026-10-09',raw_ohlc=[1]*4,amount=1,volume=1))
    verify_history_overlap(cache,saved)


@pytest.mark.parametrize('field,value',[('amount',4999.),('volume',99),('raw_ohlc',[10.,11.,9.,10.51])])
def test_historical_correction_requires_explicit_repair(field,value):
    cache,saved=sample();saved[0]['bars'][0][field]=value
    with pytest.raises(ValueError,match='RANGE_REPAIR_REQUIRED:SOURCE_HISTORY_REVISION'):verify_history_overlap(cache,saved)


def test_missing_prior_security_history_is_not_claimed_reusable():
    _,saved=sample()
    with pytest.raises(ValueError,match='PREDECESSOR_HISTORY_MISSING'):verify_history_overlap({},saved)


def test_absent_code_keeps_old_owner_without_requiring_today_package_entry():
    _,saved=sample()
    verify_history_overlap({},saved,active_security_ids=set())


def test_focus_predecessor_reads_hash_bound_sqlite_series_read_only(tmp_path):
    import gzip
    import json
    import sqlite3
    from workbench_analysis.r43_owner_replay import ref
    from workbench_analysis.operational_increment_plan_v1 import focus_predecessor

    focus=tmp_path/'focus.json.gz'
    focus.write_bytes(gzip.compress(json.dumps(dict(publication_id='focus-1',rows=[
        dict(entity_id='S',trade_date='2026-10-12',state_freshness='KNOWN')])).encode(),mtime=0))
    prewatch=tmp_path/'prewatch.jsonl.gz'
    prewatch.write_bytes(gzip.compress((json.dumps(dict(security_id='S',research_mainline_context={'state':'KNOWN'},
        confirmation={'confirmation_status':'UNKNOWN'},prewatch={'raw_qualification':'UNKNOWN'}))+'\n').encode(),mtime=0))
    series=tmp_path/'focus_actual_bars.sqlite'
    with sqlite3.connect(series) as db:
        db.execute('CREATE TABLE bars(security TEXT,day TEXT,payload TEXT,PRIMARY KEY(security,day))')
        db.execute('INSERT INTO bars VALUES(?,?,?)',('S','2026-10-12',json.dumps(dict(trade_date='2026-10-12',symbol='S',close=10))))
    forward=tmp_path/'forward.json.gz'
    forward.write_bytes(gzip.compress(json.dumps(dict(source_bindings=dict(
        series=ref(tmp_path,series),status={},native_core={}))).encode(),mtime=0))
    identity=tmp_path/'identity.json';identity.write_text(json.dumps({'rows':[{
        'security_id':'S','source_security_key':'SH.600001'}]}))
    lifecycle=tmp_path/'lifecycle.json';lifecycle.write_text(json.dumps(dict(identity=ref(tmp_path,identity))))
    result=focus_predecessor(tmp_path,{'2026-10-12':dict(
        focus=ref(tmp_path,focus),prewatch=ref(tmp_path,prewatch),forward=ref(tmp_path,forward),
        lifecycle=ref(tmp_path,lifecycle))})
    assert result['allbars'][('S','2026-10-12')]['close']==10
    assert result['allbars'][('S','2026-10-12')]['symbol']=='S'
    assert result['prior']['S']['trade_date']=='2026-10-12'


def test_focus_predecessor_rejects_future_sqlite_series_bar(tmp_path):
    import gzip
    import json
    import sqlite3
    from workbench_analysis.r43_owner_replay import ref
    from workbench_analysis.operational_increment_plan_v1 import focus_predecessor

    focus=tmp_path/'focus.json.gz';focus.write_bytes(gzip.compress(json.dumps(dict(publication_id='focus-1',rows=[dict(entity_id='S',trade_date='2026-10-12',state_freshness='KNOWN')])).encode(),mtime=0))
    prewatch=tmp_path/'prewatch.jsonl.gz';prewatch.write_bytes(gzip.compress((json.dumps(dict(security_id='S',confirmation={'confirmation_status':'UNKNOWN'},prewatch={'raw_qualification':'UNKNOWN'}))+'\n').encode(),mtime=0))
    series=tmp_path/'focus_actual_bars.sqlite'
    with sqlite3.connect(series) as db:
        db.execute('CREATE TABLE bars(security TEXT,day TEXT,payload TEXT,PRIMARY KEY(security,day))')
        db.execute('INSERT INTO bars VALUES(?,?,?)',('S','2026-10-13',json.dumps(dict(trade_date='2026-10-13'))))
    forward=tmp_path/'forward.json.gz';forward.write_bytes(gzip.compress(json.dumps(dict(source_bindings=dict(series=ref(tmp_path,series),status={},native_core={}))).encode(),mtime=0))
    identity=tmp_path/'identity.json';identity.write_text(json.dumps({'rows':[{
        'security_id':'S','source_security_key':'SH.600001'}]}))
    lifecycle=tmp_path/'lifecycle.json';lifecycle.write_text(json.dumps(dict(identity=ref(tmp_path,identity))))
    with pytest.raises(ValueError,match='INCREMENT_FOCUS_FUTURE_BAR'):
        focus_predecessor(tmp_path,{'2026-10-12':dict(focus=ref(tmp_path,focus),prewatch=ref(tmp_path,prewatch),forward=ref(tmp_path,forward),lifecycle=ref(tmp_path,lifecycle))})

