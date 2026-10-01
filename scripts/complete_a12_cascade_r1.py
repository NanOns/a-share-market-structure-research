"""Full entity diffs and pure unchanged downstream candidate replays; no head writes."""
import copy,gzip,hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind
from v4 import base_seed as seed,stock_prewatch as prewatch
from sector.accepted_input_r5_1 import build_current
from sector.accepted_context_r5_2 import resolve_daily_context
from sector.native_r5 import build_native
from sector.rotation_r5 import resolve_package,evaluate_b0,advance_rotation
from sector.legacy_b2_r5 import build_b2_inputs,evaluate_b2
from sector.semantic_input_r5_1 import bind_semantic

META={'publication_id','source_publication_id','created_at','formal_publication_at','available_at','source_available_at','observed_at','candidate_available_at','input_formal_publication_at','formal_publication','lineage','knowledge_lineage','first_availability_at_target_proven','input_bindings','input_digests','source_bindings','input_provenance','provenance'}
META.update({'source_publications','window_identity','technical_window_identity','start_universe_snapshot_id','adjustment_basis_id'})
def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def rows(path):
    with gzip.open(ROOT/path,'rt',encoding='utf8') as stream:return [json.loads(line) for line in stream]
def business(value):
    if isinstance(value,dict):return {k:business(v) for k,v in value.items() if k not in META and 'digest' not in k and 'sha256' not in k}
    if isinstance(value,list):return [business(v) for v in value]
    return value
def flatten(value,prefix=''):
    if isinstance(value,dict):
        result={}
        for k,v in value.items():result.update(flatten(v,prefix+'.'+k if prefix else k))
        return result
    return {prefix:value}
def diff(old,new,key='security_id'):
    a={r[key]:r for r in old};b={r[key]:r for r in new};assert len(a)==len(old) and len(b)==len(new) and set(a)==set(b)
    changes=Counter();transitions=Counter();samples=[];ha=hashlib.sha256();hb=hashlib.sha256()
    for sid in sorted(a):
        x,y=business(a[sid]),business(b[sid]);ha.update(seed.canonical_json(x)+b'\n');hb.update(seed.canonical_json(y)+b'\n')
        fx,fy=flatten(x),flatten(y);different=[k for k in sorted(set(fx)|set(fy)) if fx.get(k)!=fy.get(k)]
        changes.update(different)
        if different and len(samples)<20:samples.append(dict(entity_id=sid,changed_fields=different))
        for field in ['profile_quality','base_seed_state','raw_qualification','priority_bucket']:
            if field in x or field in y:transitions[field+':'+str(x.get(field))+' -> '+str(y.get(field))]+=1
    return dict(rows=len(a),security_rows_changed=sum(business(a[k])!=business(b[k]) for k in a),field_change_counts=dict(changes),state_transition_counts=dict(transitions),old_business_digest=ha.hexdigest(),new_business_digest=hb.hexdigest(),samples=samples)
def save(name,value):
    path='reports/audits/a12_candidate_r1/'+name+'.jsonl.gz';payload=gzip.compress(b''.join(seed.canonical_json(r)+b'\n' for r in value),mtime=0)
    destination=ROOT/path
    if destination.exists() and destination.read_bytes()!=payload:raise ValueError('IMMUTABLE_CANDIDATE_CONFLICT:'+path)
    atomic_bytes(destination,payload);return bind(path)
def normalize_availability(row,now):
    row=copy.deepcopy(row)
    row['input_formal_publication_at']=row.get('formal_publication_at');row['formal_publication_at']=now
    row.update(candidate_available_at=now,formal_publication=False,lineage='RECONSTRUCTED_CORRECTED',first_availability_at_target_proven=False)
    for field in row.get('fields',{}).values():
        field['input_formal_publication_at']=field.get('available_at');field['available_at']=now
    for item in row.get('derived_fields',{}).values():
        if isinstance(item,dict) and 'available_at' in item:item['input_formal_publication_at']=item['available_at'];item['available_at']=now
    return row

def sector_replay(core_rows,factors,seeds,bindings):
    head=read('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json');snapshot=read(head['snapshot']['path']);target=snapshot['target_trade_date']
    membership=rows(head['facts']['path']);context=resolve_daily_context(ROOT,target=target)
    # The accepted daily context predates 9/30. Candidate 9/28 inputs cannot supply 9/30 facts.
    assert context['accepted_trade_date']<target and all(r['trade_date']<target for r in core_rows+factors+seeds)
    current=build_current(factors,core_rows,[],[],target=target,cutoff=datetime.now(timezone.utc).isoformat(),binding={})
    assert current=={}
    params=read('config/v4_08_algorithm_parameter_set_r5.json');registry=read('config/v4_08_sector_field_registry_r5.json');b0=read('config/v4_08_sector_prewatch_contract_r5.json');b1=read('config/v4_08_rotation_core_contract_r5.json')
    values,_=resolve_package(b0,params,(ROOT/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes(),registry)
    publication='A12_CANDIDATE_SECTOR:'+seed.sha256_bytes(seed.canonical_json(bindings))
    native=build_native(membership,current,target=target,snapshot_id=snapshot['snapshot_id'],publication_id=publication,parameter_set=params,source_bindings=bindings,seed={},seed_capability=False,max_source_date=max(r['trade_date'] for r in factors))
    ast=read('config/v4_08_b2_machine_ast_r5.json');calendarhead=read(head['calendar_head']['path']);calendar=read(calendarhead['accepted_extension']['path'])
    inputs=build_b2_inputs(native,current,target,read(ast['source_parameter_path']),bind_semantic(membership,current,target));output={k:[] for k in ['SECTOR_NATIVE','B0','ROTATION','B2']}
    for row in native:
        common=dict(publication_id=publication,sector_id=row['sector_id'],sector_type=row['sector_type'],target_trade_date=target,membership_snapshot_id=snapshot['snapshot_id'],parameter_set_id=params['parameter_set_id'],input_digests=bindings,max_source_date=target,acceptance='CANDIDATE')
        output['SECTOR_NATIVE'].append({**common,**row});output['B0'].append({**common,**evaluate_b0(row,b0,values)})
        output['ROTATION'].append({**common,**advance_rotation(row,current,prior_publication=None,prior_members=None,prior_core=None,calendar_sessions=[r['trade_date'] for r in calendar['sessions']],contract=b1,registry=registry,parameters=values)})
        output['B2'].append({**common,**evaluate_b2(inputs[row['sector_id']],ast,source_sha256=bind(ast['source_path'])['sha256'],source_parameter_sha256=bind(ast['source_parameter_path'])['sha256'],parameter_set_sha256=bind('config/v4_08_algorithm_parameter_set_r5.json')['sha256'])})
    result={}
    for kind,value in output.items():
        oldreport=read('reports/v4_08/V4_08_R5_'+kind+'_FULL_MARKET.json')
        result[kind]=dict(artifact=save('V4_08_'+kind+'_AUTHORITY_R1',value),diff=diff(rows(oldreport['artifact']['path']),value,key='sector_id'))
    return dict(status='PASS_TRUE_UNCHANGED_SECTOR_REPLAY_WITH_NO_TARGET_CORE',target_trade_date=target,target_current_core_rows=len(current),daily_context_date=context['accepted_trade_date'],outputs=result)

def main():
    protected=read('config/source_authority_governance_r1.json')['protected_bindings'];assert all(bind(b['path'])['sha256']==b['sha256'] for b in protected)
    previous=ROOT/'reports/audits/A12_DOWNSTREAM_CASCADE_AND_FULL_BUSINESS_DIFF_R1.json'
    now=read(previous.relative_to(ROOT).as_posix())['observed_at'] if previous.exists() else datetime.now(timezone.utc).isoformat()
    oldctx,oldcores,oldfactors=seed._load_accepted_source_context(ROOT)
    cores=[normalize_availability(r,now) for r in rows('reports/audits/a12_v4_05_r1/staging/V4_05_R4_FULL_MARKET_CORE_PROFILE.jsonl.gz')]
    factors=[normalize_availability(r,now) for r in rows('reports/audits/a12_v4_05_r1/staging/V4_05_R4_FULL_SCOPE_FACTORS.jsonl.gz')]
    profilepub='A12_CANDIDATE_CORE:'+seed.sha256_bytes(seed.canonical_json([business(r) for r in cores]))
    existing=ROOT/'reports/audits/a12_candidate_r1/V4_05_CORE_PROFILE_AUTHORITY_AVAILABLE_R1.jsonl.gz'
    if existing.exists():profilepub=rows(existing.relative_to(ROOT).as_posix())[0]['publication_id']
    for r in cores:r['publication_id']=profilepub
    corebinding=save('V4_05_CORE_PROFILE_AUTHORITY_AVAILABLE_R1',cores);factorbinding=save('V4_05_FACTORS_AUTHORITY_AVAILABLE_R1',factors)
    corelogical=seed.sha256_bytes(b''.join(seed.canonical_json(r)+b'\n' for r in cores));factorlogical=seed.sha256_bytes(b''.join(seed.canonical_json(r)+b'\n' for r in factors))
    ctx=copy.deepcopy(oldctx);pub='A12_CANDIDATE_SEED:'+corelogical
    ctx.update(publication_id=pub,profile_row_publication_id=profilepub,core_logical_digest=corelogical)
    ctx['source_bindings'].update(publication_id=pub,profile_row_publication_id=profilepub,core_logical_digest=corelogical,core_profile_artifact_sha256=corebinding['sha256'],full_scope_factors_artifact_sha256=factorbinding['sha256'],full_scope_factors_logical_digest=factorlogical,core_profile_receipt_sha256=bind('reports/audits/a12_v4_05_r1/V4_05_R4_CORE_PROFILE_REPLAY.json')['sha256'],full_scope_factors_receipt_sha256=bind('reports/audits/a12_v4_05_r1/V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json')['sha256'],authority_scope='ENGINEERING_RECONSTRUCTED_CORRECTED_EXTERNAL_PENDING')
    newseed=seed.build_candidate_from_records(cores,factors,ctx,created_at=now);seedbinding=save('V4_07_BASE_SEED_AUTHORITY_R1',newseed['rows'])
    pctx,_,_,oldseeds,package=prewatch.load_accepted(ROOT);oldpre=prewatch.build(oldcores,oldfactors,oldseeds,pctx,package)
    pctx.update(context_id='A12_CANDIDATE_CONTEXT:'+corelogical,source_publication_id=pub,profile_row_publication_id=profilepub,core_logical_digest=corelogical,knowledge_cutoff=now)
    pctx['source_bindings'].update(core_profile=corebinding,factors=factorbinding,seed_artifact=seedbinding,core_logical_digest=corelogical,seed_logical_digest=newseed['logical_digest'],authority_scope='ENGINEERING_ONLY')
    newpre=prewatch.build(cores,factors,newseed['rows'],pctx,package);prebinding=save('V4_09_STOCK_PREWATCH_AUTHORITY_R1',newpre)
    v404old=rows(read('data/v4/V4_04_ACCEPTED_HEAD.json')['accepted_artifact']['path']);v404new=rows(read('reports/audits/A12_V4_04_TRUE_REPLAY_R1.json')['artifact']['path'])
    v403old=rows('reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz');v403new=rows('reports/audits/a12_v4_03_r1/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz')
    stages={'V4_03':dict(diff=diff(v403old,v403new),rebuild_required=True),'V4_04':dict(diff=diff(v404old,v404new),rebuild_required=True),'V4_05':dict(profile_diff=diff(oldcores,cores),factor_diff=diff(oldfactors,factors),rebuild_required=True,artifacts=dict(core=corebinding,factors=factorbinding)),'V4_07':dict(diff=diff(oldseeds,newseed['rows']),rebuild_required=True,artifact=seedbinding),'V4_08':sector_replay(cores,factors,newseed['rows'],pctx['source_bindings']),'V4_09':dict(diff=diff(oldpre,newpre),rebuild_required=True,artifact=prebinding)}
    for stage in stages.values():stage['input_digest_changed']=True;stage['algorithm_parameters_changed']=False
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in protected)
    atomic_json(ROOT/'reports/audits/A12_DOWNSTREAM_CASCADE_AND_FULL_BUSINESS_DIFF_R1.json',dict(status='PASS_ENGINEERING_FULL_SCOPE_TRUE_CASCADE',stages=stages,business_projection_exclusions=sorted(META),observed_at=now,corrected_candidate_available_at=now,old_input_availability_preserved_as_input_only=True,formal_publication=False,external_acceptance=None,accepted_heads_unchanged=True,algorithm_source_proofs=bind('reports/audits/A12_UNCHANGED_REPLAY_SOURCE_PROOFS_R1.json'),next_stage='Independent external source-semantics audit; no amended accepted head until acceptance'))
    print(json.dumps(dict(status='PASS_A12_TRUE_CASCADE',changes={k:v.get('diff',v.get('profile_diff',{})).get('security_rows_changed') for k,v in stages.items()})))

if __name__=='__main__':main()
