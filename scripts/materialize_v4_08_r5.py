"""Scoped membership promotion and engineering materialization from accepted inputs."""
from pathlib import Path
import sys,json,gzip,hashlib
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from sector.native_r5 import build_native
from sector.accepted_input_r5_1 import load_accepted_current
from sector.accepted_context_r5_2 import resolve_daily_context
from sector.semantic_input_r5_1 import bind_semantic
from sector.rotation_r5 import resolve_package,evaluate_b0,advance_rotation
from sector.legacy_b2_r5 import evaluate_b2,build_b2_inputs

def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def bind(path):return dict(path=path,sha256=sha(path),byte_count=(ROOT/path).stat().st_size)
def verify(binding):
    p=(ROOT/binding['path']).resolve()
    if not p.is_relative_to(ROOT) or sha(binding['path'])!=binding['sha256']:raise ValueError('ACCEPTED_FILE_BINDING_MISMATCH')
    return p
def report(name,value):atomic_json(ROOT/f'reports/v4_08/V4_08_R5_{name}.json',value)
def rows(binding):
    with gzip.open(verify(binding),'rt',encoding='utf8') as stream:return [json.loads(line) for line in stream]

def main():
    audit='docs/evidence/V4_08_R4_1_FINAL_EXTERNAL_AUDIT_AND_PIT_MEMBERSHIP_ACCEPTANCE_20260930.md'
    if sha(audit)!='4fd4938bbfdc7dde9aa2bf6193efc16621156bcc1abf04d8ccf241ece19c7d2b':raise ValueError('EXTERNAL_ACCEPTANCE_AUTHORITY_MISMATCH')
    candidate=read('data/v4/V4_08_PIT_MEMBERSHIP_CANDIDATE_HEAD_R1.json')
    for k in ('facts','source_revision','snapshot','calendar_head','identity_head'):verify(candidate[k])
    snapshot=read(candidate['snapshot']['path']);membership=rows(candidate['facts'])
    if len(membership)!=snapshot['row_count'] or Counter(r['sector_type'] for r in membership)!=Counter(INDUSTRY=5224,THEME=44938):raise ValueError('SCOPED_PIT_PROMOTION_COUNT_MISMATCH')
    head={**candidate,'head_id':'V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1','status':'ACCEPTED','external_acceptance':'EXTERNALLY_ACCEPTED',
        'membership_acceptance_scope':'FORWARD_PIT_MEMBERSHIP_ONLY','first_accepted_trade_date':snapshot['target_trade_date'],
        'membership_snapshot_id':snapshot['snapshot_id'],'row_count':len(membership),'formal_rows_by_type':dict(Counter(r['sector_type'] for r in membership)),
        'does_not_grant_sector_algorithm_acceptance':True,'does_not_grant_rotation_production_permission':True,
        'first_accepted_pit_date_pending_external_acceptance':False,'external_acceptance_evidence':bind(audit)}
    destination=ROOT/'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json'
    if destination.exists() and read(destination.relative_to(ROOT))!=head:raise ValueError('SCOPED_ACCEPTED_HEAD_ALREADY_EXISTS_DIFFERENT')
    atomic_json(destination,head)
    report('PIT_MEMBERSHIP_PROMOTION',dict(status='PASS_SCOPED_EXTERNAL_ACCEPTANCE_PROMOTION',accepted_head=bind(destination.relative_to(ROOT).as_posix()),**{k:head[k] for k in ('membership_acceptance_scope','first_accepted_trade_date','row_count','formal_rows_by_type','does_not_grant_sector_algorithm_acceptance','does_not_grant_rotation_production_permission')}))
    corehead=read('data/v4/V4_05_ACCEPTED_HEAD.json');seedhead=read('data/v4/V4_07_ACCEPTED_HEAD.json')
    if corehead['external_acceptance']!='EXTERNALLY_ACCEPTED' or seedhead['external_acceptance']!='EXTERNALLY_ACCEPTED':raise ValueError('UNACCEPTED_CORE_OR_SEED')
    target=snapshot['target_trade_date'];factors=rows(corehead['accepted_artifacts']['full_scope_factors']);seed_rows=rows(seedhead['evidence_bindings']['candidate_artifact'])
    dates=Counter(r['trade_date'] for r in factors);seed_dates=Counter(r['trade_date'] for r in seed_rows)
    if any(date>target for date in [*dates,*seed_dates]):raise ValueError('FUTURE_ACCEPTED_INPUT_NOT_ALLOWED_AT_TARGET')
    daily_context=resolve_daily_context(ROOT,target=target)
    current,adapter_binding=load_accepted_current(ROOT,corehead,target=target,cutoff=target+'T23:59:59+08:00',accepted_input_context=daily_context)
    params_path='config/v4_08_algorithm_parameter_set_r5.json';params=read(params_path);parameter_bytes=(ROOT/params_path).read_bytes()
    registry=read('config/v4_08_sector_field_registry_r5.json');b0contract=read('config/v4_08_sector_prewatch_contract_r5.json');b1contract=read('config/v4_08_rotation_core_contract_r5.json')
    values,_=resolve_package(b0contract,params,parameter_bytes,registry);resolve_package(b1contract,params,parameter_bytes,registry)
    source_bindings={k:bind(p) for k,p in [('membership_head',destination.relative_to(ROOT).as_posix()),('core_head','data/v4/V4_05_ACCEPTED_HEAD.json'),('seed_head','data/v4/V4_07_ACCEPTED_HEAD.json'),('calendar_head',candidate['calendar_head']['path']),('parameter_set',params_path),('native_producer','src/sector/native_r5.py'),('rotation_producer','src/sector/rotation_r5.py'),('b2_producer','src/sector/legacy_b2_r5.py'),('b2_ast','config/v4_08_b2_machine_ast_r5.json')]}
    for key,path in [('field_registry','config/v4_08_sector_field_registry_r5.json'),('native_contract','config/v4_08_sector_native_contract_r5.json'),('b0_contract','config/v4_08_sector_prewatch_contract_r5.json'),('rotation_contract','config/v4_08_rotation_core_contract_r5.json'),('core_factors',corehead['accepted_artifacts']['full_scope_factors']['path']),('core_profile',corehead['accepted_artifact']['path']),('seed_artifact',seedhead['evidence_bindings']['candidate_artifact']['path'])]:source_bindings[key]=bind(path)
    source_bindings['accepted_input_adapter']=bind('src/sector/accepted_input_r5_1.py')
    source_bindings['accepted_context_resolver']=bind('src/sector/accepted_context_r5_2.py')
    source_bindings['semantic_adapter']=bind('src/sector/semantic_input_r5_1.py')
    source_bindings['accepted_input_contract']=bind('config/v4_08_accepted_context_contract_r5_2.json')
    source_bindings['canonical_hash_producer']=bind('src/v4/canonical_governance_hash.py')
    source_bindings['canonical_input_binding']=adapter_binding
    ast_binding=read('config/v4_08_b2_machine_ast_r5.json')
    source_bindings['b2_semantic_dependencies']=ast_binding['semantic_dependencies']
    publication='V4_08_R5_ENGINEERING_20260930_'+hashlib.sha256(json.dumps(source_bindings,sort_keys=True).encode()).hexdigest()[:20]
    seed_capability=seedhead['capabilities']['REAL_BASE_SEED_SIGNAL'] in {'FULL_PASS','EXTERNALLY_ACCEPTED'}
    seed_truth={r['security_id']:True if r['base_seed_state']=='TRUE' else False if r['base_seed_state']=='FALSE' else None for r in seed_rows if r['trade_date']==target}
    native=build_native(membership,current,target=target,snapshot_id=snapshot['snapshot_id'],publication_id=publication,parameter_set=params,source_bindings=source_bindings,seed=seed_truth,seed_capability=seed_capability,max_source_date=max(dates))
    ast=read('config/v4_08_b2_machine_ast_r5.json');calendarhead=read(candidate['calendar_head']['path']);calendar=read(calendarhead['accepted_extension']['path'])
    sessions=[r['trade_date'] for r in calendar['sessions']]
    b2_inputs=build_b2_inputs(native,current,target,read(ast['source_parameter_path']),bind_semantic(membership,current,target))
    output={k:[] for k in ('SECTOR_NATIVE','B0','ROTATION','B2')}
    for row in native:
        common=dict(publication_id=publication,sector_id=row['sector_id'],sector_type=row['sector_type'],target_trade_date=target,membership_snapshot_id=snapshot['snapshot_id'],parameter_set_id=params['parameter_set_id'],input_digests=source_bindings,max_source_date=max(target,max(dates)),acceptance='CANDIDATE')
        output['SECTOR_NATIVE'].append({**common,**row})
        output['B0'].append({**common,**evaluate_b0(row,b0contract,values)})
        output['ROTATION'].append({**common,**advance_rotation(row,current,prior_publication=None,prior_members=None,prior_core=None,calendar_sessions=sessions,contract=b1contract,registry=registry,parameters=values)})
        b2=evaluate_b2(b2_inputs[row['sector_id']],ast,source_sha256=sha(ast['source_path']),source_parameter_sha256=sha(ast['source_parameter_path']),parameter_set_sha256=sha(params_path))
        output['B2'].append({**common,**b2})
    paths={}
    for kind,records in output.items():
        path=f'data/v4/artifact_store/v4_08/V4_08_R5_{kind}_20260930_{publication.rsplit("_",1)[1]}.jsonl.gz'
        payload=gzip.compress(b''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n' for r in records),mtime=0)
        p=ROOT/path
        if p.exists() and p.read_bytes()!=payload:raise ValueError('APPEND_ONLY_MATERIALIZATION_CONFLICT')
        atomic_bytes(p,payload);paths[kind]=bind(path)
        state_key='confirmed_raw' if kind=='B2' else 'output_state'
        report(kind+'_FULL_MARKET',dict(status='PASS_ENGINEERING_MATERIALIZATION',publication_id=publication,row_count=len(records),sector_counts=dict(Counter(r['sector_type'] for r in records)),artifact=paths[kind],state_distribution=dict(Counter(r.get(state_key,'PRIMITIVES') for r in records)),
            target_trade_date=target,accepted_core_source_dates=dict(dates),accepted_seed_source_dates=dict(seed_dates),target_accepted_core_count=len(current),stale_core_relabelled=False,
            reasons=['NO_TARGET_ACCEPTED_CORE_FACTS','NO_PRIOR_ACCEPTED_PIT_HISTORY','DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL'],external_acceptance_pending=True))
    report('COMMON_MEMBER_QUALITY',dict(status='PASS_FIRST_PIT_NO_HISTORY_PRESERVED',row_count=len(native),common_member_quality=[dict(sector_id=r['sector_id'],endpoints=r['common_member_quality']) for r in native],current_membership_replayed_as_prior=False))
    for kind,source,contract in [('SECTOR_NATIVE','src/sector/native_r5.py','config/v4_08_sector_native_contract_r5.json'),('B0','src/sector/rotation_r5.py','config/v4_08_sector_prewatch_contract_r5.json'),('ROTATION','src/sector/rotation_r5.py','config/v4_08_rotation_core_contract_r5.json')]:
        report(kind+'_IMPLEMENTATION',dict(status='IMPLEMENTED_ENGINEERING_CANDIDATE',producer=bind(source),contract=bind(contract),parameter_set=bind(params_path),full_market_artifact=paths[kind],real_same_day_signal_available=False,reason='ACCEPTED_CORE_TARGET_DATE_20260928_NOT_20260930',external_acceptance_pending=True))
    report('STAGE_CANDIDATE_MANIFEST',dict(status='R5_ENGINEERING_CANDIDATE_PENDING_VERIFICATION',publication_id=publication,artifacts=paths,input_bindings=source_bindings,
        capabilities={'SECTOR_NATIVE_NON_SEED':'IMPLEMENTED_TARGET_CORE_UNAVAILABLE','B0_SEED_DEPENDENT':'DEGRADED_UNKNOWN','ROTATION_HISTORY_DEPENDENT':'SHADOW_UNKNOWN','B2_NON_AMOUNT_A':'NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE','B2_AMOUNT_A':'DIAGNOSTIC_AUDIT_OPEN'},
        final_v4_08_accepted_head_written=False,global_acceptance_unchanged='V4_00_TO_V4_07_ACCEPTED',independent_audits=['Prior-RPS','AUD-AMOUNT-A-06','V4-01 listing-anchor']))
    print(json.dumps({'status':'MATERIALIZED_ENGINEERING_CANDIDATE','publication_id':publication,'row_counts':{k:len(v) for k,v in output.items()},'target_accepted_core_count':len(current)}))

if __name__=='__main__':main()
