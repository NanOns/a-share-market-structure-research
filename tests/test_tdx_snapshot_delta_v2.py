import hashlib
import struct
import zipfile
import pytest
from workbench_analysis.tdx_snapshot_delta_v2 import build_typed_delta, classify


def bar(day,close=1000):return struct.pack('<IIIIIfII',day,close,close+10,close-10,close,10000.,100,0)


def run(tmp_path,old,new,identity=None):
    paths=[]
    for name,rows in (('old',old),('new',new)):
        p=tmp_path/(name+'.zip')
        with zipfile.ZipFile(p,'w') as z:
            for key,raw in rows.items():z.writestr(key,raw)
        paths.append(p)
    ident=identity or {'SH.600123':dict(security_id='SEC-TEST',security_type='A_STOCK',list_date='2020-01-01')}
    return build_typed_delta(parent_zip=paths[0],current_zip=paths[1],target_dates=['2026-10-08'],
        identities=ident,identity_binding={'sha256':'test'},policy_binding={'sha256':'test'},
        parent_sha256=hashlib.sha256(paths[0].read_bytes()).hexdigest(),
        current_sha256=hashlib.sha256(paths[1].read_bytes()).hexdigest(),dated_members={'2026-10-08':set(ident)})


def test_foreign_bad_prices_quarantined_with_bytes(tmp_path):
    a='sh/lday/sh600123.day';index='sh/lday/sh000001.day'
    invalid=struct.pack('<IIIIIfII',20261008,1000,1,900,1000,100.,1,0)
    r=run(tmp_path,{a:bar(20260930)},{a:bar(20260930)+bar(20261008),index:invalid})
    assert r['status']=='READY' and r['targets']['2026-10-08']['target_bar_count']==1
    q=next(x for x in r['entry_manifest'] if x['path']==index)
    assert q['consumer_scope']=='INDEX_SEPARATE_CONSUMER_REQUIRED'
    assert q['validation_error'] and q['current_sha']


@pytest.mark.parametrize('mutation',['bad_ohlc','truncate','rewrite','removed'])
def test_canonical_target_remains_fail_closed(tmp_path,mutation):
    a='sh/lday/sh600123.day';old={a:bar(20260929)+bar(20260930)}
    raw={'bad_ohlc':bar(20260929)+bar(20260930)+struct.pack('<IIIIIfII',20261008,100,1,90,100,1.,1,0),
         'truncate':bar(20260929), 'rewrite':bar(20260928)+bar(20260930)}
    new={} if mutation=='removed' else {a:raw[mutation]}
    r=run(tmp_path,old,new)
    assert r['status']=='BLOCKED_TARGET_A_STOCK' and r['target_failures']


def test_prefix_does_not_grant_identity_and_interval_required(tmp_path):
    a='sh/lday/sh600123.day';other='sh/lday/sh600124.day'
    r=run(tmp_path,{a:bar(20260930)},{a:bar(20260930)+bar(20261008),other:bar(20261008)})
    assert r['targets']['2026-10-08']['target_bar_count']==1
    assert next(x for x in r['entry_manifest'] if x['path']==other)['consumer_scope']=='CANONICAL_IDENTITY_UNPROVEN'
    r=run(tmp_path,{a:bar(20260930)},{a:bar(20260930)+bar(20261008)},
        {'SH.600123':dict(security_id='SEC-TEST',security_type='A_STOCK',list_date='2026-10-09')})
    assert not r['targets']['2026-10-08']['target_bars']


def test_historical_correction_is_retained(tmp_path):
    a='sh/lday/sh600123.day'
    r=run(tmp_path,{a:bar(20260930)},{a:bar(20260930,1100)+bar(20261008)})
    assert r['revision_events'][0]['affected_trade_dates']==[20260930]


@pytest.mark.parametrize('key,consumer',[('SZ.200012','NON_A_STOCK_ENTRY_QUARANTINED'),
    ('SZ.131804','NON_A_STOCK_ENTRY_QUARANTINED'),('SH.880006','UNSUPPORTED_INSTRUMENT'),
    ('BJ.920001','CANONICAL_IDENTITY_UNPROVEN')])
def test_generic_consumer_classification(key,consumer):
    assert classify(key,None)[1]==consumer


def test_unsafe_package_rejected(tmp_path):
    with pytest.raises(ValueError,match='UNSAFE_ENTRY'):
        run(tmp_path,{'sh/lday/sh600123.day':bar(20260930)}, {'../sh600123.day':bar(20261008)})
