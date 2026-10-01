"""Fresh exact downstream run reads prior scores only from accepted RPS head."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import binding,digest,immutable_json
from v4.a02_a05_external_acceptance_r1 import read_accepted_rps,RPS_HEAD,BASELINE
from v4.base_seed import _load_accepted_source_context,build_candidate_from_records
from v4.stock_prewatch import load_accepted,build,write_immutable_gzip_jsonl

def main():
    entry=json.loads((ROOT/'reports/next_round_r2/BATCH_STAGE_ENTRY_R1.json').read_bytes());timestamp=entry['observed_at_utc']
    ctx,cores,factors=_load_accepted_source_context(ROOT);day=ctx['trade_date']
    accepted=read_accepted_rps(ROOT,day);rps_ref=binding(ROOT,ROOT/RPS_HEAD)
    oldseed=build_candidate_from_records(cores,factors,ctx,created_at=timestamp)
    stockctx,_,_,_,package=load_accepted(ROOT);oldstock=build(cores,factors,oldseed['rows'],stockctx,package)
    changedcore=deepcopy(cores);changedfactor=deepcopy(factors)
    profile='V4_05_A02_ACCEPTED_RPS_AMENDMENT_R1:'+digest(dict(old=ctx['core_logical_digest'],rps_head=rps_ref))
    seedpub='V4_07_A02_ACCEPTED_RPS_AMENDMENT_R1:'+digest(dict(profile=profile,rps_head=rps_ref))
    delta_index={r['security_id']:r for r in accepted['deltas'][3]}
    for core,factor in zip(changedcore,changedfactor):
        sid=core['security_id'];actual=delta_index.get(sid,{}).get('fields',{}).get('rps5_delta3',dict(value=None,quality_state='UNKNOWN',unknown_reason='PRIOR_UNIVERSE_MEMBER_MISSING'))
        field=deepcopy(factor['fields']['rps5_delta3'])
        field.update(value=actual['value'],quality_state=actual['quality_state'],unknown_reason=actual['unknown_reason'],available_at=timestamp,input_digest=digest(dict(actual=actual,rps_head=rps_ref)),output_digest=digest(dict(actual=actual,rps_head=rps_ref,value=actual['value'])),window_identity=digest(dict(actual=actual,rps_head=rps_ref)))
        factor['fields']['rps5_delta3']=field;core['primitive_quality']['rps5_delta3']=deepcopy(field)
        for row in (core,factor):
            row['original_accepted_publication_id']=row.get('publication_id');row['publication_id']=profile;row['candidate_only']=True;row['formal_publication_at']=timestamp;row['a02_accepted_rps_head']=rps_ref
    directory=ROOT/'data/v4/a02_accepted_amendments_r1';cp=directory/'V4_05_CORE_AMENDMENT_CANDIDATE_R1.jsonl.gz';fp=directory/'V4_05_FACTORS_AMENDMENT_CANDIDATE_R1.jsonl.gz'
    write_immutable_gzip_jsonl(cp,changedcore);write_immutable_gzip_jsonl(fp,changedfactor)
    newctx=deepcopy(ctx);core_digest=digest(changedcore)
    newctx.update(publication_id=seedpub,profile_row_publication_id=profile,core_logical_digest=core_digest)
    newctx['source_bindings'].update(publication_id=seedpub,profile_row_publication_id=profile,core_logical_digest=core_digest,core_profile_artifact_sha256=binding(ROOT,cp)['sha256'],full_scope_factors_artifact_sha256=binding(ROOT,fp)['sha256'],full_scope_factors_logical_digest=digest(changedfactor),a02_accepted_rps_head=rps_ref,candidate_amendment_only=True)
    seeds=build_candidate_from_records(changedcore,changedfactor,newctx,created_at=timestamp)
    sp=directory/'V4_07_SEED_AMENDMENT_CANDIDATE_R1.jsonl.gz';write_immutable_gzip_jsonl(sp,seeds['rows'])
    newstockctx=deepcopy(stockctx);newstockctx.update(source_publication_id=seedpub,profile_row_publication_id=profile,core_logical_digest=core_digest,knowledge_cutoff=timestamp)
    newstockctx['source_bindings'].update(core_profile=binding(ROOT,cp),factors=binding(ROOT,fp),seed_artifact=dict(**binding(ROOT,sp),logical_digest=seeds['logical_digest'],row_count=len(seeds['rows'])),core_logical_digest=core_digest,seed_logical_digest=seeds['logical_digest'],a02_accepted_rps_head=rps_ref,candidate_amendment_only=True)
    newstockctx['context_id']='A02_FORMAL_INPUT_AMENDMENT:'+digest(newstockctx['source_bindings'])
    stocks=build(changedcore,changedfactor,seeds['rows'],newstockctx,package)
    stp=directory/'V4_09_STOCK_AMENDMENT_CANDIDATE_R1.jsonl.gz';write_immutable_gzip_jsonl(stp,stocks)
    diffs=[]
    projection_fields=['states','primitive_quality','derived_fields']
    seedfields=['base_seed_state','matched_seed_paths','domain_states','waiting_for','invalid_if','quality','quality_codes','seed_participation_annotation']
    stockfields=['base_seed_state','mandatory_core_quality_ready','raw_qualification','emergence_axis','structure_quality_axis','risk_axis','priority_bucket','priority_sort_key','waiting_for','quality']
    for name,old,new,fields in [('V4_05',cores,changedcore,projection_fields),('V4_07',oldseed['rows'],seeds['rows'],seedfields),('V4_09',oldstock,stocks,stockfields)]:
        for a,b in zip(old,new):
            changes={f:dict(old=a.get(f),new=b.get(f)) for f in fields if a.get(f)!=b.get(f)}
            diffs.append(dict(stage=name,security_id=a['security_id'],business_changes=changes))
        p=directory/(name+'_OLD_NEW_FULL_REPLAY_R1.jsonl.gz');write_immutable_gzip_jsonl(p,[dict(security_id=a['security_id'],old=a,new=b) for a,b in zip(old,new)])
    diffp=directory/'FULL_BUSINESS_DIFF_R1.jsonl.gz';write_immutable_gzip_jsonl(diffp,diffs)
    counts={name:sum(bool(r['business_changes']) for r in diffs if r['stage']==name) for name in ('V4_05','V4_07','V4_09')}
    if counts['V4_07']!=5222 or counts['V4_09']!=2811: raise ValueError('A02_BUSINESS_DIFF_RECONCILIATION_REQUIRES_EXPLANATION:'+str(counts))
    algorithms=[binding(ROOT,ROOT/p) for p in ['src/v4/base_seed.py','src/v4/stock_prewatch.py','config/v4_07_base_seed_contract_v1.json','config/v4_07_parameter_set_v1.json','config/v4_09_parameter_set_v1.json']]
    receipts={}
    for stage,artifact in [('V4_05',cp),('V4_07',sp),('V4_09',stp)]:
        receipt=dict(contract_id=stage+'_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE',status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',old_accepted_head=binding(ROOT,ROOT/f'data/v4/{stage}_ACCEPTED_HEAD.json'),accepted_rps_head=rps_ref,unchanged_algorithms_parameters=algorithms,artifact=binding(ROOT,artifact),full_business_diff=binding(ROOT,diffp),rows_changed=counts[stage],row_count=5222,trade_date=day,real_replay_at=timestamp,external_authority=accepted['head']['external_authority'],audited_head=BASELINE,old_head_replaced=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
        if stage=='V4_05': receipt['factor_artifact']=binding(ROOT,fp)
        path=ROOT/f'reports/audits/next_round_r2/{stage}_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE_R1.json';immutable_json(path,receipt);receipts[stage]=binding(ROOT,path)
    report=dict(contract_id='A02_ACCEPTED_INPUT_DOWNSTREAM_REPLAY_R1',status='A02_DOWNSTREAM_AMENDMENTS_READY_FOR_EXTERNAL_REAUDIT',A02_EXTERNAL_ACCEPTANCE_FORMALIZED='PASS',accepted_rps_head=rps_ref,external_authority=accepted['head']['external_authority'],audited_head=BASELINE,amendments=receipts,changed_rows=counts,old_seed_counts=oldseed['state_counts'],new_seed_counts=seeds['state_counts'],previous_diff_reconciled=dict(expected_seed_rows=5222,expected_stock_rows=2811,actual_seed_rows=counts['V4_07'],actual_stock_rows=counts['V4_09'],business_change_due_to_new_RPS_source=False,explanation='Accepted score/delta numeric values exactly match prior independently accepted producer scope; formalization changes provenance and candidate namespaces only, so the established full business diff is preserved.'),new_seed_context=newctx,new_stock_context=newstockctx,full_business_diff=binding(ROOT,diffp),formal_V4_11_real_confirmation_enabled=False,production=False,Stage_Head_changed=False,Data_Head_changed=False)
    immutable_json(ROOT/'reports/audits/next_round_r2/A02_DOWNSTREAM_AMENDMENT_REPLAY_R1.json',report)
    print(json.dumps(dict(status=report['status'],changed_rows=counts,seed_counts=seeds['state_counts'])))
if __name__=='__main__': main()
