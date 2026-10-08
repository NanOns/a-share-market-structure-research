"""Real two-date UI replay, explicitly degraded where historical owners are absent."""
import copy,gzip,json,shutil,sqlite3,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,compact_cell,DOMAINS
from workbench_service.current_v4_context import canonical,digest
from workbench_service.joint_release import AUTHORITY,validate

OUT=ROOT/'docs/evidence/r2_continuous_daily_20261008'

def main():
    before=(ROOT/AUTHORITY).read_bytes();base=json.loads(before);live=ProductionV4ResearchReader(ROOT)
    chain=json.loads((OUT/'OWNER_CHAIN_STAGING.json').read_bytes())
    first=chain.get('first_day') or json.loads((OUT/'CONTINUOUS_REPLAY.json').read_bytes())['first']
    day=first['trade_date'];publication=json.loads((ROOT/first['publication']['path']).read_bytes())
    market=json.loads((ROOT/live.manifest['sources']['market_operational']['path']).read_bytes())
    raw_binding=market['sources'][day+':RAW_DAILY'];raw=json.loads((ROOT/raw_binding['path']).read_bytes())['rows']
    states_binding=publication['sources']['states'];states=json.load(gzip.open(ROOT/states_binding['path'],'rt',encoding='utf8'))
    assert all(r['trade_date']==day for r in raw+states['rows'])
    directory=ROOT/'data/v4/research_snapshots'/uuid.uuid4().hex;directory.mkdir(parents=True)
    path=directory/'daily_research.sqlite';shutil.copyfile(live.path,path)
    meta=copy.deepcopy(live.manifest);meta.pop('database');meta['release_id']=directory.name
    meta['context']['accepted_trade_date']=day
    meta['context']['knowledge_lineage']='RECONSTRUCTED_CORRECTED'
    meta['context']['data_head_digest']=raw_binding['sha256']
    meta['source_contract_digest']=digest(canonical(dict(raw=raw_binding,states=states_binding)))
    meta['owners']={};meta['sources']=dict(RAW_DAILY=raw_binding,states=states_binding,events=states_binding,
        focus_operational=first['publication'],focus_journal=first['journal'])
    for name,binding in publication['sources']['implementation'].items():meta['sources']['focus_kernel_'+name]=binding
    stats=dict(enrollment_denominator=0,planned_horizon_denominator=0,published_enrollment_count=0,
        published_outcomes=0,mature_eligible_count=0,state_counts={},win_rate=None,return_quantiles=None,
        reason='NO_ACCEPTED_ENROLLMENTS_AS_OF_REPLAY_DATE',failure_and_censored_not_dropped=True)
    # Existing enrollments all start on 9/30; their plans/outcomes cannot enter 9/29.
    assert not [e for e in live.manifest['domain_features']['forward']['enrollments'] if e['T0']<=day]
    meta['domain_features']=dict(focus=publication,forward=dict(statistics=stats,enrollments=[],plans=[],fep=dict(status='NOT_BOUND')))
    meta['gaps']=[dict(domain=d,state='SOURCE_INCOMPLETE',reason='NO_ACCEPTED_DATED_OWNER_FOR_HISTORICAL_REPLAY')
        for d in ('sectors','market','events','radar','settlement')]
    meta['gaps'].append(dict(domain='stocks',state='SOURCE_INCOMPLETE',reason='RAW_FACTS_ONLY_NO_HISTORICAL_FACTOR_OR_MEMBERSHIP_BACKFILL'))
    meta['publication_scope']='HISTORICAL_CORRECTED_RAW_FOCUS_REPLAY_DEGRADED'
    meta['metadata'].update(release_id=directory.name,trading_date=day,source_snapshot=raw_binding['sha256'],
        input_digest=digest(canonical(meta['sources'])),published_at=datetime.now(timezone.utc).isoformat())
    with sqlite3.connect(path) as db:
        identities={json.loads(p)['entity_id']:json.loads(p) for p, in db.execute("SELECT payload FROM objects WHERE domain='stocks'")}
        db.execute('DELETE FROM objects');db.execute('DELETE FROM members')
        def put(domain,item,state=''):
            db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',(domain,item['entity_id'],item['display_name'].casefold(),item.get('symbol',''),state,canonical(item).decode()))
        for r in raw:
            sid=r['security_id'];old=identities.get(sid,{})
            fields={k:compact_cell(dict(value=r[k],quality='KNOWN',unit=r.get(k+'_unit')),raw_binding,k,day)
                for k in ('open','high','low','close','volume','amount','trade_date')}
            item=dict(entity_id=sid,display_name=old.get('display_name',sid),symbol=r['source_security_key'],fields=fields,
                display_identity=dict(purpose='DISPLAY_ONLY',pit_safe=False,observed_at=live.manifest['metadata']['source_as_of']))
            put('stocks',item)
        for ep in {e['entity_id']:e for e in publication['episodes']}.values():
            last=ep['observations'][-1];assert last['trade_date']<=day
            values={**last,**{k:ep[k] for k in ('episode_id','T0','end_date','parent_episode_id')}}
            fields={k:compact_cell(dict(value=v,quality='UNKNOWN' if v is None or v=='UNKNOWN' else 'KNOWN'),first['publication'],k,day) for k,v in values.items()}
            old=identities.get(ep['entity_id'],{})
            put('focus',dict(entity_id=ep['entity_id'],display_name=old.get('display_name',ep['entity_id']),symbol=old.get('symbol',''),fields=fields))
        meta['counts']={d:db.execute('SELECT count(*) FROM objects WHERE domain=?',(d,)).fetchone()[0] for d in DOMAINS}
        db.execute("UPDATE metadata SET value=? WHERE key='snapshot'",(canonical(meta).decode(),));db.commit();db.execute('VACUUM')
    write(directory/'manifest.json',dict(meta,database=ref(path)))
    pointers=[dict(contract_id='V4_RESEARCH_SNAPSHOT_AUTHORITY_V1',manifest=ref(directory/'manifest.json'),previous=None),chain['snapshot']['pointer']]
    assets={};static=ROOT/'src/workbench_service/static/research'
    build=digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(static.iterdir()) if p.is_file()}))
    for p in static.iterdir():
        if p.is_file():
            target=ROOT/'data/v4/ui_releases'/build/p.name;write(target,p.read_bytes());assets[p.name]=ref(target)
    candidates=[]
    for day,pointer in zip([first['trade_date'],chain['trade_date']],pointers):
        candidate=copy.deepcopy(base);candidate.update(snapshot=pointer,trade_date=day,ui_build_id=build,ui_assets=assets,
            full_product_release=False,focus_automatic_write=False,operational_release_scope=['focus_read_corrected','forward_read','diagnostics'])
        validate(ROOT,candidate);ProductionV4ResearchReader(ROOT,snapshot_authority=pointer)
        write(OUT/('REPLAY_'+day+'.json'),candidate);candidates.append(ref(OUT/('REPLAY_'+day+'.json')))
    assert (ROOT/AUTHORITY).read_bytes()==before
    write(OUT/'TWO_DATE_CANDIDATES.json',dict(result='REAL_DATED_CANDIDATES_PASS',candidates=candidates,
        first_day_counts=meta['counts'],historical_membership='UNAVAILABLE_NOT_BACKFILLED',strict_pit=False,
        full_daily_e2e_pass=False,live_authority_preserved=True,next_stage='IAB_TWO_DATE_AND_JOINT_SWITCH'))
    print(json.dumps(dict(result='REAL_DATED_CANDIDATES_PASS',first_day_counts=meta['counts'])))

if __name__=='__main__':main()
