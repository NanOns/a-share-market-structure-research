"""Fail-closed all-domain G1/G2/G3 binding; never grants runtime publication."""
import argparse,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis.r43_owner_replay import checked,load,ref
from scripts.verify_v4_append_full_values_r1_1 import business

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--generation',required=True);p.add_argument('--candidate',required=True)
    p.add_argument('--values',required=True);p.add_argument('--structure',required=True);p.add_argument('--focus',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();root=Path(a.root).resolve();folder=root/a.generation
    value=load(a.values);structure=load(a.structure);focus=load(a.focus)
    candidate_binding=ref(root,root/a.candidate);candidate=load(checked(root,candidate_binding))
    policy_binding=candidate['release_policy'];policy=load(checked(root,policy_binding))
    parent=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');plan=load(folder/'INCREMENT_PLAN.json')
    period=load(folder/'PERIOD_NUMERIC_ORACLE.json')
    errors=[]
    for name,data in [('structure',structure),('focus',focus)]:
        for gate in ('G1','G2','G3'):
            if data[gate]['status']!='PASS':errors.append(name+':'+gate+':'+data[gate]['status'])
    if structure['counts']['securities']!=5225 or focus['sample_count']!=5225 or focus.get('scope')!='FULL_FOCUS_DOMAIN':errors.append('FULL_SCOPE_REQUIRED')
    if value['acceptance']!='PASS':errors.append('FULL_VALUES_NOT_PASS')
    for name,expected_count in [('core',5225),('profile',5225),('status',5225),('native',400),('rotation',400),('seed',5225)]:
        domain=value['domains'].get(name,{})
        if domain.get('actual_count')!=expected_count or domain.get('reference_count')!=expected_count or domain.get('business_difference_count')!=0 or domain.get('identity_set_equal') is not True:
            errors.append('EXPLICIT_FULL_VALUE_DOMAIN_REQUIRED:'+name)
    old=root/'data/v4/dynamic_daily_owners/2026-10-13/35e5a7c80925e59b640bcc694df1184e8bb850634b10085473cd26f6b9b89b57'
    old_market=next(r for r in load(old/'owner_v3/MARKET_REPLAY.json')['owners'] if r['trade_date']=='2026-10-13')
    actual_market=load(checked(root,candidate['owners']['2026-10-13']['market']))
    market_reference=load(checked(root,old_market['market']))
    def market_business(value):
        if isinstance(value,dict):return {k:market_business(v) for k,v in business(value).items() if k not in ('adjustment_basis_id','market_snapshot_id','input_source_digest')}
        if isinstance(value,list):return [market_business(v) for v in value]
        return value
    if market_business(actual_market)!=market_business(market_reference):errors.append('FULL_MARKET_BUSINESS_DIFF')
    market_patch_g3=Path(checked(root,candidate['owners']['2026-10-13']['market'])).parents[2]/'RESULT_G3.json'
    if not market_patch_g3.is_file():errors.append('MARKET_PATCH_INDEPENDENT_G3_RECEIPT_REQUIRED')
    else:
        market_g3=load(market_patch_g3)
        if market_g3.get('acceptance')!='PASS' or market_g3.get('G3',{}).get('status')!='PASS' or market_g3['market_binding']!=candidate['owners']['2026-10-13']['market']:
            errors.append('MARKET_PATCH_G3_NOT_MATCHED_CANDIDATE')
    if period.get('acceptance',period.get('status')) not in ('PASS','PASS_PERIOD_NUMERIC_ORACLE','PASS_UNCHANGED_PERIOD_KERNEL_EXACT_COORDINATE'):
        # Contract-specific statuses must be listed explicitly, never inferred
        # from the mere absence of a diff or from generic nonempty evidence.
        errors.append('PERIOD_EXPLICIT_PASS_REQUIRED:'+str(period.get('acceptance',period.get('status'))))
    if plan['mode']!='APPEND_DAY' or plan['compute_sessions']!=['2026-10-13']:errors.append('APPEND_SINGLE_DAY_REQUIRED')
    for day,bindings in parent['owners'].items():
        if candidate['owners'].get(day)!=bindings:errors.append('IMMUTABLE_OWNER_CHANGED:'+day)
    core_owner=next(r for r in load(folder/'owner_v3/CORE_REPLAY.json')['owners'] if r['trade_date']=='2026-10-13')
    sector_owner=next(r for r in load(folder/'sector_v3/SECTOR_REPLAY.json')['owners'] if r['trade_date']=='2026-10-13')
    expected_bindings={k:core_owner[k] for k in ('raw','adjusted','core')}
    expected_bindings.update(sector=sector_owner['native'],seed=sector_owner['seed'],rotation=sector_owner['rotation'],
        relative_sector=sector_owner['relative_sector'],profile=sector_owner['enriched_profiles'])
    focus_index=load(folder/'owner_v3/FOCUS_FORWARD_REPLAY.json')
    focus_owner=next(r for r in focus_index['owners'] if r['trade_date']=='2026-10-13')
    expected_bindings.update(focus=focus_owner['D2'],forward=focus_index['focus'],period_raw=period['owners']['period_raw'],period_adjusted=period['owners']['period_adjusted'])
    for name,binding in expected_bindings.items():
        if candidate['owners']['2026-10-13'][name]!=binding:errors.append('CANDIDATE_NOT_BOUND_TO_VERIFIED_OUTPUT:'+name)
    for binding in policy['accepted_algorithm_bindings']:checked(root,binding)
    receipt=load(checked(root,candidate['day_receipt']))
    counts=receipt['source_counts']
    if sum(counts.values())!=5225:errors.append('FULL_LIFECYCLE_COUNT_REQUIRED')
    native=list(__import__('gzip').open(checked(root,candidate['owners']['2026-10-13']['sector']),'rt',encoding='utf8'))
    if len(native)!=400:errors.append('FULL_SECTOR_COUNT_REQUIRED')
    archive=root/'runtime/r1_1/G123_EVIDENCE';archive.mkdir(parents=True,exist_ok=True);refs={}
    paths=[('values',a.values),('structure',a.structure),('focus',a.focus),('period',folder/'PERIOD_NUMERIC_ORACLE.json')]
    if market_patch_g3.is_file():paths.append(('market',market_patch_g3))
    for name,path in paths:
        raw=Path(path).read_bytes();target=archive/(name+'_'+hashlib.sha256(raw).hexdigest()+'.json')
        if not target.exists():target.write_bytes(raw)
        refs[name]=ref(root,target)
    result=dict(contract_id='V4_R1_1_DUAL_REFERENCE_SEMANTIC_AND_IDENTITY_PARITY',scope='FULL_ALL_DOMAIN',target_trade_date='2026-10-13',
        counts=dict(stocks=5225,sectors=400),candidate_binding=candidate_binding,accepted_algorithm_bindings=policy['accepted_algorithm_bindings'],
        generation_policy=policy_binding,evidence=refs,
        market_business_equal=market_business(actual_market)==market_business(market_reference),market_reference=old_market['market'],
        G1=dict(status='PASS' if not errors else 'BLOCKED',errors=errors),G2=dict(status='PASS' if not errors else 'BLOCKED',errors=errors),
        G3=dict(status='PASS' if not errors else 'BLOCKED',errors=errors),G4=dict(status='BLOCKED_PENDING_PG_HEAD_HTTP_READBACK'),
        acceptance='ENGINEERING_G123_ACCEPTED' if not errors else 'BLOCKED',runtime_publication_admission=False)
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(dict(acceptance=result['acceptance'],errors=errors,evidence=refs)))
if __name__=='__main__':main()
