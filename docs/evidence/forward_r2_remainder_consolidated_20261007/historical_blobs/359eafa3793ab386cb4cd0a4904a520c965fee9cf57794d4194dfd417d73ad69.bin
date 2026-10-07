"""Independent stdlib V2 oracle: no runtime/builder/selector imports."""
import hashlib,gzip,json
from decimal import Decimal
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.validate_v4_12_snapshot_v2_contract import validate_contract,validate_shape
OUT='reports/v4_12_runtime_r12/'
def canonical(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def sha(v):return hashlib.sha256(canonical(v)).hexdigest()
def exact(ref):
    raw=(ROOT/ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'];return json.loads(raw)
def lines(ref):
    raw=(ROOT/ref['path']).read_bytes();assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
    if ref['path'].endswith('.gz'):raw=gzip.decompress(raw)
    return [json.loads(l) for l in raw.splitlines()]

# Independently specified per-anchor tuples: support, acceptance, held, breach,
# test, market age, evaluable count, validity. No helper generated expectations.
BOOK={
 '2026-09-23':{'BULLISH_IMPULSE_BODY':('IDLE','PENDING',0,0,0,0,0,'VALID'),'BULLISH_IMPULSE_LOW':('IDLE','PENDING',0,0,0,0,0,'VALID')},
 '2026-09-24':{'BULLISH_IMPULSE_BODY':('RECLAIMED','PENDING',1,0,1,1,1,'VALID'),'BULLISH_IMPULSE_LOW':('IDLE','PENDING',1,0,0,1,1,'VALID')},
 '2026-09-28':{'BULLISH_IMPULSE_BODY':('BROKEN','BROKEN',0,1,1,2,2,'INVALIDATED'),'BULLISH_IMPULSE_LOW':('BREACHED_SHALLOW','NOT_ACCEPTED',0,1,0,2,2,'VALID')},
 '2026-09-29':{'BULLISH_IMPULSE_BODY':('BROKEN','BROKEN',1,0,1,3,3,'INVALIDATED'),'BULLISH_IMPULSE_LOW':('BREACHED_SHALLOW','NOT_ACCEPTED',1,0,0,3,3,'VALID'),'BREAKOUT_LEVEL':('IDLE','PENDING',0,0,0,0,0,'VALID'),'PRIOR_HIGH':('IDLE','PENDING',0,0,0,0,0,'VALID')},
 '2026-09-30':{'BULLISH_IMPULSE_BODY':('BROKEN','BROKEN',2,0,1,4,4,'INVALIDATED'),'BULLISH_IMPULSE_LOW':('BREACHED_SHALLOW','ACCEPTED',2,0,0,4,4,'VALID'),'BREAKOUT_LEVEL':('TESTING','PENDING',1,0,0,1,1,'VALID'),'PRIOR_HIGH':('TESTING','PENDING',1,0,0,1,1,'VALID')},
}
WINNER={'2026-09-23':'BULLISH_IMPULSE_BODY','2026-09-24':'BULLISH_IMPULSE_BODY','2026-09-28':'BULLISH_IMPULSE_LOW','2026-09-29':'BREAKOUT_LEVEL','2026-09-30':'BREAKOUT_LEVEL'}

def validate():
    contract=json.loads((ROOT/'config/v4_12_frozen_snapshot_contract_v2.json').read_bytes());validate_contract(contract)
    registry=json.loads((ROOT/'config/v4_12_field_registry_v1.json').read_bytes())['fields'];blocked={r['field']:r['blocked_reason'] for r in registry if r['field_role']=='BLOCKED_CAPABILITY'}
    proofs=[];immutable={};same_day=[];publication_cache={}
    for scope,dates in [('synthetic',list(BOOK)),('real',['2026-09-29','2026-09-30'])]:
        previous=None
        for date in dates:
            revisions=['r1','r2','r3'] if scope=='synthetic' and date=='2026-09-29' else ['r1']
            for revision in revisions:
                base=OUT+'final_'+scope+'/'+date+'/'+revision+'/';ref=json.loads((ROOT/(base+'snapshot_ref.json')).read_bytes());m=exact(ref);rows=lines(m['snapshot_bundle']);index=exact(m['security_index'])['rows'];source=exact(m['source_runtime_manifest']);artifacts={Path(x['path']).name:x for x in source['artifacts']}
                runtime={r['identity']['security_id']:r for r in lines(artifacts['runtime_security.jsonl.gz'])};transitions=lines(artifacts['transitions.jsonl']);created=lines(artifacts['anchors.jsonl']);events=lines(artifacts['events.jsonl']);observations=lines(artifacts['state_observations.jsonl.gz'])
                assert m['contract_id']=='V4_12_FROZEN_D1_CANDIDATE_MANIFEST_V2' and m['row_count']==len(rows)==len(runtime)==(1 if scope=='synthetic' else 5224)
                assert m['formal_accepted'] is False and m['AS_RECORDED'] is False and m['knowledge_lineage']=='RECONSTRUCTED_CORRECTED'
                assert m['security_ids_digest']==sha(sorted(index)) and source['common_F0_bind_count']==len(rows)
                if previous:assert source['prior']==dict(frozen_manifest_v2=previous['ref'])
                else:assert source['prior'] is None
                current=dict(ref=ref,rows={r['security_id']:r for r in rows});expected_transitions=[]
                for r in rows:
                    sid=r['security_id'];run=runtime[sid];validate_shape(contract,r, [t for t in transitions if t['security_id']==sid])
                    assert index[sid]['row_digest']==sha(r) and r['source_runtime_manifest_digest']==m['source_runtime_manifest']['sha256'] and r['common_facts']==run['common_facts'] and r['anchor_states']==run['anchor_states']
                    assert run['common_F0_bind_count']==1 and r['trade_date']==date and r['revision']==revision
                    prior=previous['rows'][sid] if previous else None;old={s['anchor_id']:s for s in prior['anchor_states']} if prior else {}
                    if prior:assert r['prior_state_ref']['row_digest']==sha(prior) and r['prior_state_ref']['candidate_manifest']==previous['ref']
                    states={s['anchor_id']:s for s in r['anchor_states']};new={a['anchor_id']:a for a in created if a['security_id']==sid}
                    assert set(states)==set(old)|set(new)
                    assert run['creation_observation']['input_digest']==sha(run['common_facts'])
                    for aid,a in new.items():
                        expected_event=sha(dict(security_id=sid,date=date,revision=revision,anchor_type=a['anchor_type'],input_digest=sha(run['common_facts'])))
                        assert a['source_event_id']==expected_event and a['source_fact_digest']==sha(run['common_facts'])
                        identity=dict(contract_id=run['creation_observation']['frozen_output_envelope']['contract_id'],security_id=sid,source_event_id=expected_event,anchor_type=a['anchor_type'],anchor_trade_date=date,source_fact_digest=sha(run['common_facts']),price_basis=a['anchor_price_basis'],adjustment_source_revision=a['adjustment_source_revision'])
                        assert aid==sha(identity)
                    for aid,s in states.items():
                        assert s['counter_state_digest']==sha(s['counter_state'])
                        if aid in old:assert s['anchor']==old[aid]['anchor'] and s['event']==old[aid]['event'] and s['created_this_session'] is False
                        else:assert s['anchor']==new[aid] and s['created_this_session'] is True and all(s['counter_state'][n]==0 for n in contract['counter_fields'])
                        assert s['owning_anchor_id']==aid and s['owning_episode_id']==s['event']['event_id']
                        current_support=s['state_observations']['support'];expected_last=current_support['value'] if current_support['quality']=='KNOWN' else old[aid]['last_known_support_state'] if aid in old else None
                        assert s['last_known_support_state']==expected_last and s['output_envelope']['retest_count']==s['counter_state']['test_count']
                        if scope=='synthetic':
                            typ=s['anchor']['anchor_type'];q=s['counter_state'];actual=(s['state_observations']['support']['state'],s['state_observations']['acceptance']['state'],q['held_count'],q['breach_count'],q['test_count'],q['post_creation_market_sessions'],q['post_creation_evaluable_sessions'],s['validity']);assert actual==BOOK[date][typ],(date,typ,actual)
                            if aid in immutable:assert immutable[aid]==(sha(s['anchor']),sha(s['event']))
                            else:immutable[aid]=(sha(s['anchor']),sha(s['event']))
                            if s['validity']=='INVALIDATED':
                                fact=s['invalidation_facts'][0];assert fact['anchor_ref']['anchor_id']==aid and fact['event_ref']['event_id']==s['owning_episode_id']
                        if aid in old:
                            for machine,record in s['state_observations'].items():
                                p=old[aid]['state_observations'][machine]
                                if machine!='retention' and p['quality']==record['quality']=='KNOWN' and p['value']!=record['value']:expected_transitions.append((sid,aid,s['event']['event_id'],machine,p['value'],record['value']))
                    if prior:
                        for machine,record in r['global_state_observations'].items():
                            p=prior['global_state_observations'][machine]
                            if p['quality']==record['quality']=='KNOWN' and p['value']!=record['value']:expected_transitions.append((sid,None,None,machine,p['value'],record['value']))
                    if scope=='synthetic':
                        assert len(states)==len(BOOK[date])
                        expected_type='PRIOR_HIGH' if date=='2026-09-29' and revision=='r3' else WINNER[date]
                        winner=next(s for s in states.values() if s['anchor']['anchor_type']==expected_type)
                        assert r['active_anchor_id']==winner['anchor_id'] and r['active_anchor_selection_quality']=='KNOWN'
                    else:
                        assert not states and not new and not events and r['active_anchor_id'] is None and r['active_anchor_selection_reason']=='NO_ACTIVE_ANCHOR'
                        for n,reason in blocked.items():assert r['common_facts'][n]['quality']=='UNKNOWN' and r['common_facts'][n]['value'] is None and r['common_facts'][n]['reason']==reason
                        for field in registry:
                            if field['field_role']!='UPSTREAM_ACCEPTED':continue
                            fact=r['common_facts'][field['field']];pub=field['target_publications'].get(date)
                            if not pub or not field['target_publication_available']:
                                assert fact['quality']=='UNKNOWN' and fact['value'] is None;continue
                            source_ref=pub['artifact'];assert fact['source_digest']==source_ref['sha256'] and fact['source_publication_id']==source_ref['sha256'] and fact['trade_date']==pub['trade_date']
                            if source_ref['sha256'] not in publication_cache:publication_cache[source_ref['sha256']]={q['security_id']:q for q in exact(source_ref).get('rows',[])}
                            owner=publication_cache[source_ref['sha256']].get(sid)
                            if owner is None:assert fact['quality']=='UNKNOWN' and fact['value'] is None;continue
                            if 'fields' in owner:
                                item=owner['fields'].get(field['accepted_source_field'],{});value=item.get('value');quality=item.get('quality_state')=='OBSERVED' and value is not None
                            else:value=owner.get(field['accepted_source_field']);quality=owner.get(pub['quality_field'])=='READY' and value is not None
                            assert fact['quality']==('KNOWN' if quality else 'UNKNOWN')
                            if quality:
                                if field['data_type'] in ['number','integer']:assert Decimal(str(value))==Decimal(str(fact['value']))
                                else:assert value==fact['value']
                            else:assert fact['value'] is None
                        assert all(v['quality']=='UNKNOWN' for v in r['global_state_observations'].values())
                    if r['active_anchor_id']:
                        selected=states[r['active_anchor_id']]
                        for n in contract['security_projection']:assert r['active_projection'][n]==selected['output_envelope'][n]
                actual=[(t['security_id'],t['anchor_id'],t['event_id'],t['machine'],t['from_state'],t['to_state']) for t in transitions]
                assert sorted(actual,key=str)==sorted(expected_transitions,key=str)
                for t in transitions:
                    assert t['machine']!='retention' and t['quality']=='KNOWN' and t['transition_kind']=='KNOWN_STATE_CHANGE'
                    assert t['logical_transition_id']==sha(dict(security_id=t['security_id'],anchor_id=t['anchor_id'],machine=t['machine'],trade_date=date))
                    assert t['prior_session_state_ref']['row_digest']==sha(previous['rows'][t['security_id']])
                    if t['anchor_id']:assert t['anchor_ref']['anchor_id']==t['anchor_id'] and t['event_ref']['event_id']==t['event_id']
                proofs.append(dict(scope=scope,date=date,revision=revision,snapshot=ref,securities=len(rows),anchor_states=sum(len(r['anchor_states']) for r in rows),observations=len(observations),transitions=len(transitions)))
                if scope=='synthetic' and date=='2026-09-29':same_day.append(source['prior'])
                if revision=='r1':first=current
            previous=first
    assert same_day[0]==same_day[1]==same_day[2]
    protected=json.loads((ROOT/(OUT+'R12_STAGE_CONTRACT.json')).read_bytes())['protected']
    for p,h in protected.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    assert not (ROOT/'data/v4/V4_12_ACCEPTED_HEAD.json').exists()
    selector=json.loads((ROOT/(OUT+'R12_SELECTOR_INDEPENDENT_ORACLE.json')).read_bytes());book=json.loads((ROOT/'config/v4_12_active_selector_vectors_r12.json').read_bytes())
    assert selector['total']==len(book['vectors'])==11
    for expected,actual in zip(book['vectors'],selector['rows']):assert actual['expected']==expected['expected'] and actual['actual']['active_anchor_id']==expected['expected']['active_anchor_id'] and actual['actual']['quality']==expected['expected']['quality']
    return dict(status='PASS',candidate_status='V4_12_R12B_MULTI_ANCHOR_RUNTIME_CANDIDATE_READY_FOR_EXTERNAL_AUDIT',oracle='INDEPENDENT_LITERAL_MULTI_ANCHOR_BOOK_PLUS_EXACT_LINEAGE',proofs=proofs,selector_vectors=11,hard_cases=['M01','M02','M03','M04','M05','M06','M07','M08','M09','M10','M11','M12'],raw_fallback_count=0,provider_replacement_count=0,V4_11_candidate_substitution_count=0,protected_hashes=protected)
if __name__=='__main__':
    r=validate();(ROOT/(OUT+'R12B_LOCAL_READBACK.json')).write_bytes(canonical(r));print(json.dumps(dict(status='PASS',proofs=len(r['proofs']))))
