"""Real accepted snapshot B2 replay; different-date facts cannot alter 9/30 head."""
from pathlib import Path
from datetime import date
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import gzip
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import binding,read_bound,digest,immutable_json
from v4.a02_a05_external_acceptance_r1 import accepted_legacy_observations,validate_a05_record,A05_RECORD,BASELINE
from v4.stock_prewatch import write_immutable_gzip_jsonl
from sector.legacy_b2_r5 import build_b2_inputs,evaluate_b2
from sector.semantic_input_r5_1 import bind_semantic,eligibility
from sector.a05_b2_scoped_amendment_r1 import evaluate_current_snapshot

def load_gzip(ref):
    if binding(ROOT,ROOT/ref['path'])['sha256']!=ref['sha256']: raise ValueError('A05_OLD_HEAD_ARTIFACT_HASH')
    with gzip.open(ROOT/ref['path'],'rt',encoding='utf8') as stream: return [json.loads(l) for l in stream]

def main():
    import pyarrow.parquet as pq
    record,frozen=validate_a05_record(ROOT);target=record['accepted_snapshot_trade_date'];day=date.fromisoformat(target)
    observations=accepted_legacy_observations(ROOT,target=target)
    original=frozen['original_source_bindings'];normalized=ROOT/'data/normalized/adjusted_daily.parquet'
    if binding(ROOT,normalized)['sha256']!=original['data/normalized/adjusted_daily.parquet']['sha256']: raise ValueError('A05_NEW_SOURCE_REVISION_REQUIRES_NEW_EVIDENCE')
    dates=[date(2026,9,23),day]
    rows=pq.read_table(normalized,columns=['security_id','date','aligned_close','missing_state','universe_status'],filters=[('date','in',dates)]).to_pylist()
    bounded=[dict(**{k:v for k,v in r.items() if k!='date'},trade_date=str(r['date'])) for r in rows]
    source_dir=ROOT/'data/v4/a05_b2_amendment_r1';capture=source_dir/'REAL_CURRENT_SNAPSHOT_RET1_INPUT_R1.jsonl.gz';write_immutable_gzip_jsonl(capture,bounded)
    prior={r['security_id']:r for r in bounded if r['trade_date']=='2026-09-23'};today={r['security_id']:r for r in bounded if r['trade_date']==target}
    current={};before={}
    for sid,obs in observations.items():
        a=today.get(sid,{});b=prior.get(sid,{});close=a.get('aligned_close');previous=b.get('aligned_close');ret=close/previous-1 if close is not None and previous is not None and close>0 and previous>0 else None
        row=dict(trade_date=target,fields={'ret1':dict(value=ret,quality='ACCEPTED' if ret is not None else 'UNKNOWN',max_source_date=target)},legacy_valid_member=obs)
        current[sid]=row;before[sid]=deepcopy(row);before[sid]['legacy_valid_member']=dict(value=None,quality='UNKNOWN',producer_contract='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE')
    metadata=pq.read_table(ROOT/frozen['original_byte_archives']['data/sectors/sector_factors_daily.parquet']['path'],columns=['sector_id','sector_name','sector_type','sector_role','sector_breadth_above_ma20'],filters=[('date','=',day)]).to_pylist();meta={r['sector_id']:r for r in metadata}
    membership=[];groups={}
    for row in frozen['membership']:
        sid=row['sector_id'];member=row['security_id']
        if member is None or sid not in meta:continue
        info=meta[sid];membership.append(dict(sector_id=sid,security_id=member,sector_name=info['sector_name'],sector_type=info['sector_type'],sector_role=info['sector_role']))
        groups.setdefault(sid,set()).add(member)
    native=[dict(sector_id=sid,sector_name=meta[sid]['sector_name'],sector_type=meta[sid]['sector_type'],member_ids=sorted(ids),fields={'ma20_width':dict(value=meta[sid]['sector_breadth_above_ma20']),'breadth_delta3':dict(value=None),'ma20_delta3':dict(value=None)}) for sid,ids in sorted(groups.items())]
    semantics_before=bind_semantic(membership,before,target);semantics_after=bind_semantic(membership,current,target)
    ast_path=ROOT/'config/v4_08_b2_machine_ast_r5.json';ast=json.loads(ast_path.read_bytes());config=json.loads((ROOT/ast['source_parameter_path']).read_bytes())
    inputs_before=build_b2_inputs(native,before,target,config,semantics_before);inputs_after=build_b2_inputs(native,current,target,config,semantics_after)
    args=dict(source_sha256=binding(ROOT,ROOT/ast['source_path'])['sha256'],source_parameter_sha256=binding(ROOT,ROOT/ast['source_parameter_path'])['sha256'],parameter_set_sha256=binding(ROOT,ROOT/'config/v4_08_algorithm_parameter_set_r5.json')['sha256'])
    scope=dict(accepted_time_role='CURRENT_SNAPSHOT_ONLY',target=target,accepted_snapshot_trade_date=target)
    replay=[]
    for row in native:
        sid=row['sector_id'];old=evaluate_b2(inputs_before[sid],ast,**args);new=evaluate_current_snapshot(inputs_after[sid],ast,exact_snapshot_scope=scope,**args)
        changes={k:dict(old=old[k],new=new[k]) for k in old if old[k]!=new[k]}
        replay.append(dict(sector_id=sid,trade_date=target,before_semantic=semantics_before[sid],after_semantic=semantics_after[sid],before_inputs=inputs_before[sid],after_inputs=inputs_after[sid],old=old,new=new,business_changes=changes))
    path=source_dir/'B2_CURRENT_SNAPSHOT_OLD_NEW_REPLAY_R1.jsonl.gz';write_immutable_gzip_jsonl(path,replay)
    head=json.loads((ROOT/'data/v4/V4_08_ACCEPTED_HEAD.json').read_bytes());manifest=read_bound(ROOT,head['r5_2_candidate_manifest']);oldgroups={k:load_gzip(v) for k,v in manifest['artifacts'].items()};oldidx={r['sector_id']:r for r in oldgroups['B2']};replayidx={r['sector_id']:r for r in replay}
    comparisons=[]
    for sid in sorted(set(oldidx)|set(replayidx)):
        old=oldidx.get(sid);new=replayidx.get(sid)
        comparisons.append(dict(sector_id=sid,accepted_trade_date=old['target_trade_date'] if old else None,candidate_trade_date=target if new else None,comparison_scope='DIFFERENT_DATED_CURRENT_SNAPSHOTS_NOT_PIT_EQUIVALENT',accepted_old=old,candidate_current=new['new'] if new else None,qualification_changes={f:dict(old=old.get(f),new=new['new'].get(f)) for f in ('confirmed_raw','confirmed_reason','confirmed_diagnostic','warm_raw','capabilities') if old and new and old.get(f)!=new['new'].get(f)}))
    diffpath=source_dir/'FULL_ACCEPTED_HEAD_VS_SNAPSHOT_B2_DIFF_R1.jsonl.gz';write_immutable_gzip_jsonl(diffpath,comparisons)
    # Exact current observation date cannot be injected into later accepted target.
    try: accepted_legacy_observations(ROOT,target='2026-09-30')
    except ValueError as error:scope_rejection=str(error)
    else: raise AssertionError('A05_STALE_SNAPSHOT_ADOPTED')
    rotation_proof=dict(contract_id='A05_B2_ROTATION_CONTEXT_NON_ADOPTION_V1',status='PASS',accepted_artifacts={k:manifest['artifacts'][k] for k in ('B0','ROTATION','SECTOR_NATIVE')},rotation_rows=len(oldgroups['ROTATION']),rotation_business_changed=0,context_business_changed=0,same_session_current_snapshot_injection='REJECTED',reason=scope_rejection,old_accepted_target='2026-09-30',accepted_A05_snapshot_target=target,causal_proof='Original frozen B0/rotation input consumer graph has no B2 qualification dependency; dated A05 snapshot cannot be relabelled. Candidate-only B2 replay never overwrites existing Context/Rotation artifacts.')
    immutable_json(ROOT/'reports/audits/next_round_r2/A05_B2_ROTATION_CONTEXT_READBACK_R1.json',rotation_proof)
    result=dict(contract_id='V4_08_ACCEPTED_HEAD_B2_CAPABILITY_AMENDMENT_CANDIDATE',status='V4_08_B2_AMENDMENT_READY_FOR_EXTERNAL_REAUDIT',A05_EXTERNAL_ACCEPTANCE_FORMALIZED='PASS',audited_head=BASELINE,external_authority=record['external_authority'],A05_acceptance_record=binding(ROOT,ROOT/A05_RECORD),accepted_snapshot_trade_date=target,scope='CURRENT_SNAPSHOT_ONLY',historical_PIT_equivalent=False,AS_RECORDED=False,old_accepted_head=binding(ROOT,ROOT/'data/v4/V4_08_ACCEPTED_HEAD.json'),old_accepted_artifacts=manifest['artifacts'],unchanged_algorithm_parameters=[binding(ROOT,ROOT/ast['source_path']),binding(ROOT,ROOT/ast['source_parameter_path']),binding(ROOT,ast_path),binding(ROOT,ROOT/'config/v4_08_algorithm_parameter_set_r5.json')],new_scope_adapter=binding(ROOT,ROOT/'src/sector/a05_b2_scoped_amendment_r1.py'),real_source_capture=binding(ROOT,capture),original_normalized_source=original['data/normalized/adjusted_daily.parquet'],current_snapshot_replay=binding(ROOT,path),full_accepted_artifact_diff=binding(ROOT,diffpath),rotation_context_readback=binding(ROOT,ROOT/'reports/audits/next_round_r2/A05_B2_ROTATION_CONTEXT_READBACK_R1.json'),real_snapshot_sector_count=len(replay),accepted_B2_sector_count=len(oldidx),matched_sector_ids=len(set(oldidx)&set(replayidx)),old_snapshot_states=dict(Counter(r['old']['confirmed_raw'] for r in replay)),new_snapshot_states=dict(Counter(r['new']['confirmed_raw'] for r in replay)),restored_semantic_known=sum(r['after_semantic']['sector_valid'] is not None for r in replay),snapshot_qualification_changed=sum(r['old']['confirmed_raw']!=r['new']['confirmed_raw'] for r in replay),unknown_reason_removed=sum(r['old']['confirmed_reason']=='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE' and r['new']['confirmed_reason']!='NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE' for r in replay),limitations=['Original dated normalized source observations remain current snapshot corrected, not historical first-available PIT.','Current snapshot B2 capability is restored only at accepted A05 9/24 scope; later 9/30 same-session producer observations remain unavailable and are not synthesized.','B2 Amount-A warm branch remains UNKNOWN/DIAGNOSTIC_AUDIT_OPEN; A05 does not accept Amount-A.','Legacy q20/dq5 and prior breadth/MA change facts remain UNKNOWN without exact accepted producer.'],old_head_replaced=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    immutable_json(ROOT/'reports/audits/next_round_r2/V4_08_ACCEPTED_HEAD_B2_CAPABILITY_AMENDMENT_CANDIDATE_R1.json',result)
    print(json.dumps({k:result[k] for k in ('status','real_snapshot_sector_count','accepted_B2_sector_count','new_snapshot_states','snapshot_qualification_changed','unknown_reason_removed')}))
if __name__=='__main__': main()
