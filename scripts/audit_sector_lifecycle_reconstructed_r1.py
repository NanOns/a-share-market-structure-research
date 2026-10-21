"""Read-only real-source audit for SECTOR_LIFECYCLE_RECONSTRUCTED_V1."""
import argparse
import gzip
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from sector.lifecycle_reconstructed_v1 import evaluate_sector,load_parameters


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def read_rows(root,binding):
    path=root/binding['path'];raw=path.read_bytes()
    if len(raw)!=binding.get('bytes',len(raw)) or hashlib.sha256(raw).hexdigest()!=binding['sha256']:
        raise ValueError('OWNER_SOURCE_BYTES_OR_SHA_MISMATCH:'+binding['path'])
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',encoding='utf-8') as stream:return [json.loads(line) for line in stream]


def numeric(row,key):
    cell=(row.get('fields') or {}).get(key) or {};value=cell.get('value')
    return value if isinstance(value,(int,float)) and not isinstance(value,bool) and cell.get('quality') not in ('UNKNOWN','SOURCE_INCOMPLETE','DATA_UNAVAILABLE') else None


def oracle_maturity(row,params):
    metrics={key:numeric(row,key) for key in params['maturity']['required_inputs']}
    if (row.get('fields',{}).get('membership_ready') or {}).get('value') is not True:return 'UNKNOWN'
    if any(value is None for value in metrics.values()) or metrics['sector_quote_coverage']<params['maturity']['minimum_quote_coverage']:return 'UNKNOWN'
    tests=[metrics['sector_rs5']>0,metrics['sector_rs20']>0,metrics['breadth_ret5']>=.5,
        metrics['breadth_ret20']>=.5,metrics['seed_retention']>=.5,metrics['participation_proxy']>=.9]
    count=sum(tests)
    return 'MATURE' if count>=6 else 'DEVELOPING' if count>=3 else 'EARLY' if tests[0] and tests[2] else 'NONE'


def oracle_health(current,prior,earlier,params):
    required=params['health']['required_inputs']
    if prior is None or earlier is None or (current.get('fields',{}).get('membership_ready') or {}).get('value') is not True:return 'UNKNOWN'
    values={key:numeric(current,key) for key in required}
    old={key:numeric(prior,key) for key in ('sector_rs5','breadth_ret1','seed_retention')}
    if any(value is None for value in values.values()) or any(value is None for value in old.values()):return 'UNKNOWN'
    if values['sector_quote_coverage']<params['health']['minimum_quote_coverage']:return 'UNKNOWN'
    if current.get('membership_snapshot_id') and prior.get('membership_snapshot_id') and current['membership_snapshot_id']!=prior['membership_snapshot_id']:return 'UNKNOWN'
    older={key:numeric(earlier,key) for key in old}
    weakening=sum(older[key] is not None and values[key]-old[key] < old[key]-older[key]
                  for key in ('sector_rs5','breadth_ret1','seed_retention'))
    unknown=sum(older[key] is None for key in old)
    if values['sector_rs5']<0 and values['breadth_ret5']<.25:return 'DAMAGED'
    if weakening>=params['health']['weakening_minimum_matches']:return 'WEAKENING'
    if weakening:return 'WATCH'
    if unknown:return 'UNKNOWN'
    return 'NONE'


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_bytes(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode('utf-8')+b'\n')
    os.replace(tmp,path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True,help='Read-only V4 workspace root')
    parser.add_argument('--candidate',type=Path,help='Explicit non-formal successor candidate JSON; uses its dated Owners without changing formal Head')
    parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path,default=Path('G:/codex_tmp/r6_sector_lifecycle/sector_lifecycle_r1.json'))
    args=parser.parse_args();root=args.root.resolve();source_root=args.source_root.resolve()
    head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head=json.loads(args.candidate.read_bytes()) if args.candidate else json.loads(head_path.read_bytes())
    day=head['accepted_trade_date'];sessions=head['published_sessions'][-5:]
    if len(sessions)!=5 or sessions[-1]!=day:raise ValueError('SECTOR_LIFECYCLE_REQUIRED_SESSION_WINDOW_UNAVAILABLE')
    params,_=load_parameters(source_root);producer_sha=hashlib.sha256((source_root/'src/sector/lifecycle_reconstructed_v1.py').read_bytes()).hexdigest()
    histories={};rotations={};sources={}
    for session in sessions:
        sources[session]={}
        for domain in ('sector','rotation'):
            binding=head['owners'][session][domain]
            sources[session][domain]=binding
            rows=read_rows(root,binding)
            target=histories if domain=='sector' else rotations
            target[session]={r['sector_id']:r for r in rows if r.get('sector_id')}
            if domain=='sector' and len(target[session])!=400:raise ValueError('SECTOR_LIFECYCLE_SECTOR_DENOMINATOR_MISMATCH')
            if domain=='rotation' and len(target[session])!=400:raise ValueError('SECTOR_LIFECYCLE_ROTATION_DENOMINATOR_MISMATCH')
    sector_ids=sorted(histories[day]);outputs=[]
    for sid in sector_ids:
        rows=[]
        for session in sessions:
            row=dict(histories[session][sid]);rot=rotations[session].get(sid,{}).get('rotation',{})
            row['rotation_state']=rot.get('output_state')
            rows.append(row)
        bindings={session:{'sector':sources[session]['sector'],'rotation':sources[session]['rotation']} for session in sessions}
        outputs.append(evaluate_sector(sid,rows,head['published_sessions'],bindings,params,producer_sha256=producer_sha))
    if len(outputs)!=400 or len({row['sector_id'] for row in outputs})!=400:raise ValueError('SECTOR_LIFECYCLE_OUTPUT_DENOMINATOR_MISMATCH')
    if any(row['T0']!=day for row in outputs):raise ValueError('SECTOR_LIFECYCLE_OUTPUT_DATE_MISMATCH')
    by_day=histories
    grouped={kind:Counter(row[kind]['current'] for row in outputs) for kind in ('maturity','health')}
    selected=[]
    for sector_type in sorted({histories[day][sid].get('sector_type') for sid in sector_ids}):
        candidates=[sid for sid in sector_ids if histories[day][sid].get('sector_type')==sector_type]
        step=max(1,len(candidates)//10)
        selected.extend(candidates[::step][:10])
    selected=sorted(set(selected))[:20]
    result_by_id={row['sector_id']:row for row in outputs};oracle_checks=[]
    for sid in selected:
        prior_day,earlier_day=sessions[-2],sessions[-3]
        current=histories[day][sid];prior=histories[prior_day][sid];earlier=histories[earlier_day][sid]
        checked={'sector_id':sid,'sector_type':current.get('sector_type'),
            'producer_maturity':result_by_id[sid]['maturity']['current'],'oracle_maturity':oracle_maturity(current,params),
            'producer_health':result_by_id[sid]['health']['current'],
            'oracle_health':oracle_health(current,prior,earlier,params),
            'maturity_reasons':result_by_id[sid]['maturity']['reason_codes'],
            'health_reasons':result_by_id[sid]['health']['reason_codes'],
            'source_hashes':{d:{k:v['sha256'] for k,v in sources[d].items()} for d in sessions}}
        checked['match']=(checked['producer_maturity']==checked['oracle_maturity'] and checked['producer_health']==checked['oracle_health'])
        oracle_checks.append(checked)
    output=dict(contract_id='SECTOR_LIFECYCLE_RECONSTRUCTED_AUDIT_R1',T0=day,
        input_authority='EXPLICIT_SUCCESSOR_CANDIDATE' if args.candidate else 'FORMAL_HEAD',
        accepted_head_digest=hashlib.sha256(canonical(head)).hexdigest(),session_window=sessions,
        sector_count=len(outputs),unique_sector_count=len({row['sector_id'] for row in outputs}),
        maturity_counts=dict(grouped['maturity']),health_counts=dict(grouped['health']),
        source_bindings={d:{k:v for k,v in sources[d].items()} for d in sessions},
        producer_sha256=producer_sha,parameter_sha256=hashlib.sha256((source_root/'config/sector_lifecycle_reconstructed_v1.json').read_bytes()).hexdigest(),
        independent_real_sample_count=len(oracle_checks),independent_real_samples=oracle_checks,
        independent_oracle_acceptance='PASS' if len(oracle_checks)==20 and all(x['match'] for x in oracle_checks) else 'FAIL',
        outputs=outputs,AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False)
    atomic_json(args.output,output);print(json.dumps({k:v for k,v in output.items() if k not in ('outputs','source_bindings','independent_real_samples')},ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()
