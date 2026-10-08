"""Real accepted-day shadow, with failure rollback and immutable publication."""
import gzip,json,sqlite3,sys,uuid
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from focus_tracker.v4_journal import append
from focus_tracker.v4_path_adapter import checked,CONTRACT
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.current_v4_context import canonical,digest,SourceInvalid
from workbench_service.joint_release import AUTHORITY

OUT=ROOT/'docs/evidence/r2_focus_continuation_20261008'

def main():
    before=(ROOT/AUTHORITY).read_bytes();reader=ProductionV4ResearchReader(ROOT)
    current=reader.manifest['sources']['states']
    payload=json.load(gzip.open(checked(ROOT,current),'rt',encoding='utf8'))
    prior=payload['prior_binding']
    market=json.loads(checked(ROOT,reader.manifest['sources']['market_operational']).read_bytes())
    sources=market['sources']
    inputs=dict(series=reader.manifest['sources']['stock_series'],calendar=sources['calendar'],
                gbbq=sources['gbbq'],classification=sources['adjustment_classification'],
                status={k.split(':')[0]:v for k,v in sources.items() if k.endswith(':TRADING_STATUS')})
    inputs['implementation']={name:ref('src/focus_tracker/'+name+'.py') for name in
        ('v4_path_adapter','v4_successor','v4_journal','path_state_v2','states','outcomes','price_path')}
    path=Path('E:/codex_tmp/r2_focus_continuation')/(uuid.uuid4().hex+'.sqlite')
    first=append(path,ROOT,prior,None,path_inputs=inputs)
    try:append(path,ROOT,current,first['head'],path_inputs=inputs,fail_after_append=True)
    except SourceInvalid as error:
        assert str(error)=='JOURNAL_INJECTED_FAILURE'
    else:raise AssertionError('failure not injected')
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]==first['head']
        assert db.execute('SELECT count(*) FROM days').fetchone()[0]==1
    second=append(path,ROOT,current,first['head'],path_inputs=inputs)
    noop=append(path,ROOT,current,second['head'],path_inputs=inputs);assert noop['status']=='NOOP'
    with sqlite3.connect(path) as db:
        projection=json.loads(db.execute("SELECT value FROM metadata WHERE key='projection'").fetchone()[0])
    outcomes=[o for ep in projection['episodes'] for o in ep['outcomes']]
    observations=[o for ep in projection['episodes'] for o in ep['observations']]
    assert len({e['idempotency_key'] for e in projection['events']})==len(projection['events'])
    # Independently check every observed T+1 against accepted raw closes when
    # no price-affecting action occurs; retain the affine owner for other cases.
    oracle=[]
    from focus_tracker.v4_path_adapter import AcceptedPaths
    paths=AcceptedPaths(ROOT,inputs)
    with sqlite3.connect(paths.series.as_uri()+'?mode=ro',uri=True) as db:
        for ep in projection['episodes']:
            for o in ep['outcomes']:
                if o['outcome_status']!='OBSERVED':continue
                anchor=next(a for a in ep['anchors'] if a['anchor_id']==o['anchor_id'])
                bars=[json.loads(x[0]) for x in db.execute('SELECT payload FROM bars WHERE security=? AND day>=? AND day<=? ORDER BY day',(ep['entity_id'],anchor['trade_date'],o['target_trade_date']))]
                events=[e for e in paths.events[bars[-1]['symbol']] if int(anchor['trade_date'].replace('-',''))<e.event_date<=int(o['target_trade_date'].replace('-',''))]
                if events:continue
                from decimal import Decimal
                expected=Decimal(bars[-1]['raw_ohlc'][3])/Decimal(bars[0]['raw_ohlc'][3])-1
                assert abs(expected-Decimal(o['metrics']['return_close']))<Decimal('0.000000000001')
                oracle.append(dict(episode_id=ep['episode_id'],anchor_id=o['anchor_id'],horizon=o['horizon'],expected=str(expected),actual=o['metrics']['return_close']))
    publication=dict(projection,contract_id=CONTRACT,trade_date=second['trade_date'],
        earliest_valid_date=first['trade_date'],namespace='V4_INDEPENDENT_CORRECTED_JOURNAL_V2',
        sources=dict(states=current,prior=prior,**inputs),knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,
        legacy_history=dict(status='UNRECONCILED_PG_UNAVAILABLE',preserved=True),
        permissions=dict(read=True,automatic_event_write=False,manual_pin=False),
        write_block_reason='SHADOW_ACCEPTANCE_BEFORE_PRODUCTION_CAS')
    folder=ROOT/'data/v4/r2_focus_journal'/second['head'];write(folder/'focus.json',publication)
    # Freeze the journal after closing all connections. No live mutable DB is
    # referenced by a release manifest.
    frozen=folder/'journal.sqlite'
    if frozen.exists():
        with sqlite3.connect(frozen) as db:assert db.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]==second['head']
    else:write(frozen,path.read_bytes())
    receipt=dict(contract_id=CONTRACT,status='SHADOW_SOURCE_PASS',source_days=[first['trade_date'],second['trade_date']],
        first=first,second=second,noop=noop,append_failure_exact_rollback=True,
        publication=ref(folder/'focus.json'),journal=ref(frozen),sources=inputs,
        observations=len(observations),price_quality=dict(Counter(o['price_path']['quality'] for o in observations)),
        path_resolution=dict(Counter(o['path_resolution'] for o in observations)),
        outcomes=dict(Counter(o['outcome_status'] for o in outcomes)),oracle=oracle,
        live_last_good_preserved=(ROOT/AUTHORITY).read_bytes()==before,
        full_daily_e2e_pass=False,production_write_admitted=False,
        remaining=['SNAPSHOT_UI_AND_DAILY_CHAIN_ADMISSION','UNRESOLVED_PATH_PREDICATE_OWNERS','LEGACY_PG_RECONCILIATION','HISTORICAL_STRICT_PIT'])
    assert receipt['live_last_good_preserved']
    write(OUT/'SHADOW_READBACK.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k in ('status','observations','price_quality','path_resolution','outcomes','live_last_good_preserved')}))

if __name__=='__main__':main()
