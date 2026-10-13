"""Dual-reference R1.1 verification; read-only inputs, no identity rewriting."""
import argparse,gzip,hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from v4.state_identity import digest
from v4.confirmation_d2_candidate_r5 import ROW_PREFIX,validate_candidate_output
from v4.confirmation_d2_candidate_r5 import input_skeleton

def load(path):
    path=Path(path)
    if path.suffix=='.gz':
        with gzip.open(path,'rt',encoding='utf8') as f:return json.load(f)
    return json.loads(path.read_bytes())

def rows(path):
    with gzip.open(path,'rt',encoding='utf8') as f:return [json.loads(line) for line in f]

def checked(root,binding):
    path=(root/binding['path']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('REFERENCE_ESCAPE')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=binding['sha256']:raise ValueError('REFERENCE_HASH_MISMATCH:'+binding['path'])
    if 'bytes' in binding and path.stat().st_size!=binding['bytes']:raise ValueError('REFERENCE_SIZE_MISMATCH')
    return path

def verify_bindings(root,value,t0,seen=None):
    seen=seen if seen is not None else set()
    if isinstance(value,dict):
        if 'path' in value and 'sha256' in value:
            key=(value['path'],value['sha256'])
            if key not in seen:checked(root,value);seen.add(key)
        for key,child in value.items():
            if key in ('trade_date','source_cutoff','target_trade_date') and isinstance(child,str) and child>t0:raise ValueError('REFERENCE_FUTURE_DATE')
            verify_bindings(root,child,t0,seen)
    elif isinstance(value,list):
        for child in value:verify_bindings(root,child,t0,seen)
    return seen

def canonical_event_map(publication):
    mapping={};keys=set()
    for episode in publication['episodes']:
        # Strict business discriminator; never written back into production IDs.
        key=(episode['entity_id'],episode['start_date'],episode.get('entity_type'),episode.get('source'),episode.get('start_membership'))
        if key in keys:raise ValueError('FOCUS_SEMANTIC_MATCH_AMBIGUOUS:'+str(key))
        keys.add(key);mapping[episode['episode_id']]=list(key)
    return mapping

def d2_event_map(root,index):
    mapping={};reverse={}
    for receipt in sorted(index['owners'],key=lambda r:r['trade_date']):
        for row in load(checked(root,receipt['D2']))['rows']:
            if row['publication_id']!=ROW_PREFIX+digest({k:v for k,v in row.items() if k!='publication_id'}):raise ValueError('HISTORICAL_D2_ROW_HASH_MISMATCH')
            mapping[row['publication_id']]=['D2_ROW',row['entity_id'],row['entity_type'],row['trade_date']]
            eid=row.get('episode_id')
            if not eid or eid in mapping:continue
            key=[row['entity_id'],row['entity_type'],row['trade_date'],row['maturity'],row['scenario'],row['raw_qualification']]
            canonical=json.dumps(key,sort_keys=True)
            if canonical in reverse and reverse[canonical]!=eid:raise ValueError('D2_SEMANTIC_EVENT_AMBIGUOUS')
            mapping[eid]=key;reverse[canonical]=eid
    return mapping

def normalize(value,identities,counts,path=''):
    provenance={'source_refs','source_bindings','source_contract','input_digest','input_provenance','input_publication_ids',
        'input_publication_manifest_digest','prior_state_binding','publication_id','producer_identity','projection_provenance',
        'original_anchor_digest','available_at','cutoff','source_digest','output_digest','input_binding_digest','calculation_id',
        'research_mainline_source_bindings','input_publication_id','source_fact_digest'}
    if isinstance(value,dict):
        if 'path' in value and 'sha256' in value:
            counts['hash_verified_binding']+=1;return {'source_content_sha256':value['sha256']}
        result={}
        for key,child in value.items():
            if key in provenance:counts[key]+=1;continue
            if key=='native_core_evidence':
                result[key]=normalize({k:v for k,v in child.items() if k!='source'},identities,counts,path+'/'+key)
                counts['native_core_evidence_source_binding']+=1
                continue
            result[key]=normalize(child,identities,counts,path+'/'+key)
        return result
    if isinstance(value,list):return [normalize(x,identities,counts,path) for x in value]
    if isinstance(value,str) and value in identities:return {'semantic_entity':identities[value]}
    return value

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--actual-index',default='sample_focus_append/FOCUS_FORWARD_REPLAY.json')
    parser.add_argument('--reference-index',default='sample_focus_full_reference/FOCUS_FORWARD_REPLAY.json')
    parser.add_argument('--expected-securities',type=int,default=30)
    args=parser.parse_args();root=Path(args.root).resolve();out=Path(args.out)
    head=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day='2026-10-13'
    actual_index=load(root/args.actual_index);reference_index=load(root/args.reference_index)
    actual=load(checked(root,actual_index['focus']));reference=load(checked(root,reference_index['focus']))
    amap=canonical_event_map(actual);bmap=canonical_event_map(reference)
    amap.update(d2_event_map(root,actual_index));bmap.update(d2_event_map(root,reference_index))
    # The accepted latest publication includes its actual recursive input
    # chain. Older daily Head bindings remain immutable even where the legacy
    # producer replayed their states into this accepted publication namespace.
    accepted_chain_path=checked(root,head['owners'][head['accepted_trade_date']]['forward']).parent/'FOCUS_FORWARD_REPLAY.json'
    accepted_chain_map=d2_event_map(root,load(accepted_chain_path))
    # Accepted recursive identities fill missing historical ancestry only;
    # never overwrite a current-day or observed-chain semantic match.
    for identity,semantic in accepted_chain_map.items():
        if identity not in amap or semantic[0]!='D2_ROW':amap[identity]=semantic
        if identity in bmap and semantic[0]!='D2_ROW':bmap[identity]=semantic
    ar=load(checked(root,actual_index['owners'][-1]['D2']));br=load(checked(root,reference_index['owners'][-1]['D2']))
    accepted={}
    for date,bindings in head['owners'].items():
        p=load(checked(root,bindings['focus']));accepted[date]=p
    prior=accepted[head['accepted_trade_date']];prior_rows={r['entity_id']:r for r in prior['rows']}
    exceptions=Counter();business_differences=[];hash_errors=[];identity_errors=[];changed=Counter()
    calendar=load((root/args.actual_index).parent/'FOCUS_CALENDAR.json')
    if len(ar['rows'])!=args.expected_securities or len({r['entity_id'] for r in ar['rows']})!=args.expected_securities:raise ValueError('EXPLICIT_EXPECTED_SECURITY_COUNT_MISMATCH')
    reference_rows={r['entity_id']:r for r in br['rows']}
    for row in ar['rows']:
        full=reference_rows[row['entity_id']]
        for key in row:
            if row[key]!=full.get(key):changed[key]+=1
        if normalize(row,amap,exceptions)!=normalize(full,bmap,exceptions):business_differences.append(dict(domain='D2',security_id=row['entity_id']))
        old=prior_rows.get(row['entity_id']);binding=row['prior_state_binding']
        if old:
            expected=dict(publication_id=old['publication_id'],payload_digest=digest(old),engineering_publication_id=prior['publication_id'],ledger_id='V4_11_R5B_SEALED_FILE_CANDIDATE_LEDGER_V1')
            if binding!=expected:identity_errors.append(dict(security_id=row['entity_id'],reason='PRIOR_BINDING_NOT_ACCEPTED_PREDECESSOR'))
            if old['episode_id'] and 'ENROLLED' not in row['transition_reasons'] and 'REENTERED' not in row['transition_reasons'] and row['episode_id']!=old['episode_id']:
                identity_errors.append(dict(security_id=row['entity_id'],reason='CONTINUING_EPISODE_ID_CHANGED'))
        elif binding is not None:identity_errors.append(dict(security_id=row['entity_id'],reason='NEW_SECURITY_FALSE_PRIOR'))
        try:
            validate_candidate_output(row)
            if row['publication_id']!=ROW_PREFIX+digest({k:v for k,v in row.items() if k!='publication_id'}):raise ValueError('D2_PUBLICATION_DIGEST')
            if row['input_publication_manifest_digest']!=digest(dict(input_publication_ids=row['input_publication_ids'],fields=row['input_provenance'])):raise ValueError('D2_PROVENANCE_MANIFEST_DIGEST')
            fields=row['input_provenance'];values={name:field['value'] for name,field in fields.items()}
            x=input_skeleton(entity_id=row['entity_id'],trade_date=row['trade_date'],session_index=row['session_index'],cutoff=row['cutoff'],
                calendar_manifest=calendar,fields=fields,prior_state=old,prior_publication_id=prior['publication_id'] if old else None)
            x['detectors']={s:dict(value=values[s],status=fields[s]['status'],contract_id=fields[s]['producer_contract_id'],
                parameter_set_id=fields[s]['producer_parameter_set_id'],publication_id=fields[s]['publication_id']) for s in ('CONFIRMED','WARM','PREWATCH','SEED')}
            x.update(core_price_damage=values['core_price_damage'],frozen_invalidation=dict(value=values['frozen_invalidation'],
                episode_id=fields['frozen_invalidation']['source_field_payload'].get('episode_id'),contract_id=fields['frozen_invalidation']['source_field_payload'].get('invalidation_contract_id')),
                episode_invalidation_contract_id=None if values['episode_invalidation_contract_id']=='UNKNOWN' else values['episode_invalidation_contract_id'],
                risk=values['risk'],delta3=None if values['delta3']=='UNKNOWN' else values['delta3'],dq5=None if values['dq5']=='UNKNOWN' else values['dq5'],
                scenario=dict(value=values['scenario'],status='UNKNOWN' if values['scenario']=='UNKNOWN' else 'KNOWN'),suspended=values['suspended'],
                followup_complete=values['followup_complete'],model_boundary=False,provenance_unknown=[],authorized_boundary=None)
            if digest(x)!=row['input_digest']:raise ValueError('D2_ACTUAL_INPUT_DIGEST_MISMATCH')
        except ValueError as exc:hash_errors.append(dict(security_id=row['entity_id'],reason=str(exc)))
    # Compare every event/observation/anchor/outcome field, with IDs mapped by a
    # unique event semantic key. Explicit source exceptions remain counted.
    na=normalize(actual,amap,exceptions);nb=normalize(reference,bmap,exceptions)
    if na!=nb:business_differences.append(dict(domain='FULL_FOCUS_FORWARD',reason='SEMANTIC_TREE_DIFF'))
    verified=set()
    for binding in (actual_index['focus'],reference_index['focus']):verify_bindings(root,load(checked(root,binding)),day,verified)
    for bindings in head['owners'].values():verify_bindings(root,bindings,head['accepted_trade_date'],verified)
    for row in ar['rows']:verify_bindings(root,row,day,verified)
    # Candidate publication digest has its own namespace and excludes its ID.
    if ar['publication_id']!='R4_D2:'+digest({k:v for k,v in ar.items() if k!='publication_id'}):hash_errors.append(dict(reason='D2_BATCH_PUBLICATION_DIGEST'))
    result=dict(contract_id='V4_R1_1_DUAL_REFERENCE_SEMANTIC_AND_IDENTITY_PARITY',target_trade_date=day,sample_count=len(ar['rows']),
        scope='FULL_FOCUS_DOMAIN' if args.expected_securities==5225 else 'SAMPLE_FOCUS_DOMAIN',
        G1=dict(status='PASS' if not business_differences else 'FAIL',differences=business_differences),
        G2=dict(status='PASS' if not identity_errors else 'FAIL',errors=identity_errors,accepted_history_days=len(accepted),
            note='Read-only accepted bindings and every continuing sampled D2 episode checked; full candidate Owner conservation not yet available'),
        G3=dict(status='PASS' if not hash_errors else 'FAIL',errors=hash_errors,verified_raw_binding_count=len(verified),
            note='Sample D2 actual transformed inputs, row/batch publication and provenance manifest independently hashed; recursive raw bindings verified'),
        G4=dict(status='BLOCKED',reason='Full 5225 all-domain candidate and PG/CAS admission not executed'),
        classified_differences=dict(changed),explicit_provenance_exception_counts=dict(exceptions),
        acceptance='BLOCKED_PENDING_COMPLETE_GATES',production_head_modified=False)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
