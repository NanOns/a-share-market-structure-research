"""Auditable continuous Focus driver; no promotion without the joint gate."""
import argparse,copy,gzip,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from focus_tracker.v4_daily_driver import advance,CONTRACT
from focus_tracker.v4_path_adapter import checked
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.current_v4_context import SourceInvalid
from workbench_service.joint_release import AUTHORITY

OUT=ROOT/'docs/evidence/r2_continuous_daily_20261008'

def head(binding):
    with sqlite3.connect(checked(ROOT,binding).as_uri()+'?mode=ro',uri=True) as db:
        return db.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--replay',action='store_true');args=parser.parse_args()
    before=(ROOT/AUTHORITY).read_bytes();reader=ProductionV4ResearchReader(ROOT);manifest=reader.manifest
    if not args.replay:
        binding=manifest['sources'].get('focus_journal')
        if not binding:raise SourceInvalid('CONTINUOUS_JOURNAL_NOT_BOUND')
        # The current joint release may bind the native-Core journal namespace.
        # Use that exact driver's immutable input identity for same-day NOOP;
        # the legacy path-only driver correctly rejects a cross-namespace retry.
        journal_path=binding.get('path','').replace('\\','/')
        if '/r2_focus_native_core/' in '/'+journal_path:
            from focus_tracker.v4_native_core_daily_driver import advance as selected_advance, CONTRACT as selected_contract
        else:
            selected_advance,selected_contract=advance,CONTRACT
        result=selected_advance(ROOT,manifest,previous_journal=binding,
            previous_publication=manifest['sources']['focus_operational'],expected_head=head(binding))
        if result['status']=='NOOP' and not result['production_changed'] and result['source_requests']==0:
            write(ROOT/'docs/evidence/three_day_repair_r3_20261008'/'R3_DAILY_REAL_OR_NOOP.json',
                  dict(stage_contract=selected_contract,result='NO_NEW_COMPLETED_SESSION_NOOP',**result,
                       authority_sha256=__import__('hashlib').sha256(before).hexdigest(),live_authority_preserved=(ROOT/AUTHORITY).read_bytes()==before))
        else:
            write(OUT/'DAILY_NOOP.json',result)
        print(json.dumps(result));return
    current=manifest['sources']['states'];payload=json.load(gzip.open(checked(ROOT,current),'rt',encoding='utf8'))
    prior=payload['prior_binding'];old=json.load(gzip.open(checked(ROOT,prior),'rt',encoding='utf8'))
    previous=copy.deepcopy(manifest);previous['context']['accepted_trade_date']=old['rows'][0]['trade_date'];previous['sources']['states']=prior
    first=advance(ROOT,previous)
    try:advance(ROOT,manifest,previous_journal=first['journal'],previous_publication=first['publication'],expected_head=first['head'],fail_after_append=True)
    except SourceInvalid as error:assert str(error)=='JOURNAL_INJECTED_FAILURE'
    else:raise AssertionError('CONTINUOUS_FAILURE_NOT_ROLLED_BACK')
    assert head(first['journal'])==first['head']
    second=advance(ROOT,manifest,previous_journal=first['journal'],previous_publication=first['publication'],expected_head=first['head'])
    noop=advance(ROOT,manifest,previous_journal=second['journal'],previous_publication=second['publication'],expected_head=second['head'])
    assert noop['status']=='NOOP'
    publication=json.loads(checked(ROOT,second['publication']).read_bytes())
    assert publication['episodes']==manifest['domain_features']['focus']['episodes']
    assert publication['events']==manifest['domain_features']['focus']['events']
    market=json.loads(checked(ROOT,manifest['sources']['market_operational']).read_bytes());qa=[]
    for binding,states in [(prior,old),(current,payload)]:
        rows=states['rows'];day=rows[0]['trade_date'];assert all(r['trade_date']==day for r in rows)
        assert len({r['entity_id'] for r in rows})==len(rows)
        raw_binding=market['sources'][day+':RAW_DAILY'];raw=json.loads(checked(ROOT,raw_binding).read_bytes())['rows']
        assert all(r['trade_date']==day for r in raw)
        enrollments=[r for r in manifest['domain_features']['forward']['enrollments'] if r['T0']<=day]
        due=[p for p in manifest['domain_features']['forward']['plans'] if p['T0']<=day and p['due_date'] and p['due_date']<=day]
        qa.append(dict(day=day,states=binding,raw=raw_binding,unique_state_rows=len(rows),actual_raw_rows=len(raw),
            DM01='ACCEPTED_REAL_INPUT_REUSED',owner_field_QA='DATED_UNIQUE_BOUND_OWNER_PASS',
            projection='CONTINUOUS_JOURNAL_PASS',journal_append='PASS',forward_enrollments=len(enrollments),
            forward_due_count=len(due),forward_due='NO_DUE' if not due else 'REQUIRES_OWNER_SETTLEMENT',
            snapshot_UI='NOT_YET_RUN_FOR_BOTH_DAYS'))
    assert (ROOT/AUTHORITY).read_bytes()==before
    receipt=dict(contract_id=CONTRACT,result='CONTINUOUS_JOURNAL_REPLAY_PASS',first=first,second=second,noop=noop,
        per_day=qa,failure_preserved_previous_immutable_journal=True,existing_production_projection_equal=True,
        live_authority_preserved=True,automatic_production_write_admitted=False,full_daily_e2e_pass=False,
        next_stage='TWO_DATE_SNAPSHOT_UI_AND_OWNER_CHAIN_INTEGRATION')
    write(OUT/'CONTINUOUS_REPLAY.json',receipt)
    print(json.dumps(dict(result=receipt['result'],days=[first['trade_date'],second['trade_date']],full_daily_e2e_pass=False)))

if __name__=='__main__':main()
