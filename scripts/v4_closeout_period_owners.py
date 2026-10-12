"""Real dated period reconstruction; no source status is inferred from absence."""
import gzip
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
TARGET=Path('G:/codex_tmp/v4_ui_default_r1')
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/period_owners')

def main():
    from workbench_analysis.market_source_acquisition import official_sessions
    from workbench_analysis.r43_owner_replay import checked
    from workbench_analysis.exact_period_consumer_r3 import derive_exact_periods
    from workbench_db.v4_period_pg_r1 import prepare,read,OWNER
    from workbench_service.current_v4_context import canonical
    from workbench_service.v4_daily_refresh import atomic_bytes
    from workbench_service.core_product_bff_r1 import dated_product_manifest
    from workbench_analysis.period_indexed_closeout import CONTRACT as KERNEL_CONTRACT
    from workbench_analysis.operational_successor_v1 import accepted_api
    parser=argparse.ArgumentParser();parser.add_argument('day');parser.add_argument('--label',default='R2')
    args=parser.parse_args();day=args.day
    if not args.label.isalnum():raise ValueError('EXPLICIT_PERIOD_RUN_LABEL_REQUIRED')
    OUT.mkdir(parents=True,exist_ok=True);folder=OUT/args.label/day;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'RESULT.json').exists():raise ValueError('PRESERVE_COMPLETED_PERIOD_RUN')
    head_path=TARGET/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=head_path.read_bytes();head=json.loads(before)
    if day not in head['published_sessions']:raise ValueError('PERIOD_DAY_NOT_GRANTED')
    token=hashlib.sha256(before).hexdigest();authority_path=TARGET/'config/core_product_read_authority_r1.json'
    prior=authority_path.read_bytes();authority=json.loads(prior)
    manifest=dated_product_manifest(TARGET,authority,day)
    if manifest is None:raise ValueError('PG_DATED_HISTORY_REQUIRED')
    sessions=official_sessions(TARGET)
    source=manifest['source_bindings']['history'];rows={'period_raw':[],'period_adjusted':[]};count=0
    api=accepted_api(TARGET)
    identity=json.loads(checked(TARGET,api.snapshot['identity_source']).read_bytes())
    members={row['security_id']:row for row in identity['rows']}
    sources={}
    for relative in ('src/workbench_analysis/period_indexed_closeout.py','src/workbench_analysis/operational_daily_periods_v1.py',
                     'src/workbench_analysis/exact_period_consumer_r3.py','src/workbench_analysis/dm01_incremental_component_builders_r3_3.py'):
        raw=(ROOT/relative).read_bytes();sha=hashlib.sha256(raw).hexdigest()
        target=TARGET/'data/v4/core_period_pg_r1/sources'/sha/Path(relative).name
        atomic_bytes(target,raw)
        sources[relative]=dict(path=target.relative_to(TARGET).as_posix(),bytes=len(raw),sha256=sha)
    run_signature=hashlib.sha256(canonical(dict(day=day,head_token=token,history=source,sessions=sessions,kernel_sources=sources,members=api.snapshot['identity_source']))).hexdigest()
    checkpoints=folder/'checkpoints';checkpoints.mkdir(exist_ok=True)
    with gzip.open(checked(TARGET,source),'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line);history=row['bars'];sid=row['security_id']
            if not history:continue
            member=members[sid]
            # Absence alone cannot prove suspension; unknown state propagates.
            checkpoint=checkpoints/(hashlib.sha256(sid.encode()).hexdigest()+'.json.gz')
            if checkpoint.exists():
                saved=json.loads(gzip.decompress(checkpoint.read_bytes()))
                if saved['run_signature']!=run_signature or saved['security_id']!=sid:raise ValueError('PERIOD_CHECKPOINT_CONTEXT_MISMATCH')
                result=saved['result']
            else:
                result=derive_exact_periods(member,history,{},sessions,day,sessions[-1],indexed_calendar=True)
                atomic_bytes(checkpoint,gzip.compress(canonical(dict(run_signature=run_signature,security_id=sid,result=result)),mtime=0))
            rows['period_raw'].extend(result['PERIOD_RAW']);rows['period_adjusted'].extend(result['PERIOD_ADJUSTED'])
            count+=1
            if count%100==0:print(json.dumps(dict(day=day,securities=count)),flush=True)
    bindings={}
    for domain,values in rows.items():
        payload=dict(contract_id=OWNER,T0=day,head_token=token,domain=domain,rows=values,
                     source_bindings=dict(history=source,**{Path(name).stem:ref for name,ref in sources.items()}),
                     kernel_contract=KERNEL_CONTRACT,PIT_ELIGIBLE=False,AS_RECORDED=False,
                     status_contract='ABSENT_STATUS_REMAINS_UNKNOWN_NO_SYNTHETIC_SUSPENSION')
        binding=prepare(TARGET,payload,token+'_'+day+'_'+domain+'_'+run_signature)
        assert read(TARGET,binding,day,domain,token)==values
        bindings[domain]=binding
    manifest=dict(manifest,period_owners=bindings)
    target=TARGET/'data/v4/core_period_pg_r1/manifests'/day/(token+'.json')
    atomic_bytes(target,canonical(manifest))
    ref=dict(path=target.relative_to(TARGET).as_posix(),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    assert head_path.read_bytes()==before and authority_path.read_bytes()==prior
    for relative,binding in sources.items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=binding['sha256']:raise ValueError('PERIOD_EXECUTED_SOURCE_CHANGED')
    authority['dates'][day]=ref
    atomic_bytes(authority_path,canonical(authority))
    (folder/'RESULT.json').write_text(json.dumps(dict(day=day,securities=count,binding=bindings,manifest=ref,
        whole_payload_difference=0,production_changed=False,run_signature=run_signature,
        kernel_contract=KERNEL_CONTRACT,numeric_oracle='SEPARATE_REQUIRED'),indent=2),encoding='utf8')
if __name__=='__main__':main()
