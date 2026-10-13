"""Stream all target-day values against the once-frozen full reference."""
import argparse,gzip,json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from workbench_analysis.r43_owner_replay import load,checked,ref
from workbench_analysis.tdx_official_daily_source import sha256_file

def read(path):
    with gzip.open(path,'rt',encoding='utf8') as f:return [json.loads(line) for line in f]

def business(value):
    provenance={'path','sha256','bytes','input_digest','output_digest','source_digest','source_refs','source_bindings',
        'window_identity','publication_id','prior_publication_id','stock_fact_bindings','producer_identity','projection_provenance'}
    if isinstance(value,dict):return {k:business(v) for k,v in value.items() if k not in provenance}
    if isinstance(value,list):return [business(v) for v in value]
    return value


def qualified_rows(folder,expected_profile):
    folder=Path(folder);report=load(folder/'RESULT.json')
    if report.get('acceptance')!='PASS_AFFECTED_REFERENCE_REQUALIFICATION' or report.get('scan_rows')!=5225 or report.get('changed_rows')!=6 or report.get('errors') or report.get('actual_used_only_after_reference_construction') is not True or report.get('old_reference_profile')!=expected_profile:
        raise ValueError('QUALIFIED_REFERENCE_SCOPE_OR_ORACLE_REQUIRED')
    profile=load(folder/'PROFILE_AFFECTED6.json')['rows'];seed=load(folder/'SEED_AFFECTED6.json')['rows']
    wanted={r['security_id'] for r in report['corrections']}
    if len(wanted)!=6 or len(profile)!=6 or len(seed)!=6 or {r['security_id'] for r in profile}!=wanted or {r['security_id'] for r in seed}!=wanted or any(r.get('trade_date')!='2026-10-13' for r in profile+seed):raise ValueError('QUALIFIED_REFERENCE_EXACT_SIX_TARGET_ROWS_REQUIRED')
    return {'profile':{r['security_id']:r for r in profile},'seed':{r['security_id']:r for r in seed}},dict(result_path=str(folder/'RESULT.json'),result_sha256=sha256_file(folder/'RESULT.json'),profile_sha256=sha256_file(folder/'PROFILE_AFFECTED6.json'),seed_sha256=sha256_file(folder/'SEED_AFFECTED6.json'),changed_entities=sorted(wanted),scope='Only independently generated six current-day Profile/Seed rows; other reference rows/domains unchanged')


def apply_qualified(expected,replacement):
    if not set(replacement)<=set(expected):raise ValueError('QUALIFIED_REFERENCE_ENTITY_NOT_IN_OLD_REFERENCE')
    return dict(expected,**replacement)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--generation',required=True);p.add_argument('--out',required=True);p.add_argument('--qualified-reference');a=p.parse_args()
    root=Path(a.root);new=root/a.generation;old=root/'data/v4/dynamic_daily_owners/2026-10-13/35e5a7c80925e59b640bcc694df1184e8bb850634b10085473cd26f6b9b89b57'
    nc=load(new/'owner_v3/CORE_REPLAY.json');oc=load(old/'owner_v3/CORE_REPLAY.json')
    np=load(new/'owner_v3/PROFILE_STRUCTURE_REPLAY.json');op=load(old/'owner_v3/PROFILE_STRUCTURE_REPLAY.json')
    ns=load(new/'sector_v3/SECTOR_REPLAY.json');os=load(old/'sector_v3/SECTOR_REPLAY.json')
    def last(doc,key='trade_date'):return next(r for r in doc['owners'] if (r['owner'][key] if 'owner' in r else r[key])=='2026-10-13')
    c1,c2=last(nc),last(oc);p1,p2=last(np),last(op);s1,s2=last(ns),last(os)
    pairs=[('raw',c1['raw'],c2['raw'],'security_id'),('adjusted',c1['adjusted'],c2['adjusted'],'security_id'),
        ('core',c1['core'],c2['core'],'security_id'),('profile',p1['owner']['profiles'],p2['owner']['profiles'],'security_id'),
        ('status',p1['owner']['status'],p2['owner']['status'],'security_id')]
    pairs.extend((name,s1[name],s2[name],'sector_id' if name in ('native','rotation') else 'security_id') for name in ('native','rotation','relative_sector','seed'))
    overrides,qualification=qualified_rows(a.qualified_reference,p2['owner']['profiles']) if a.qualified_reference else ({},None)
    results={}
    for name,actual,expected,key in pairs:
        aa={r[key]:r for r in read(checked(root,actual))};bb={r[key]:r for r in read(checked(root,expected))};diff=[]
        if name in overrides:bb=apply_qualified(bb,overrides[name])
        for entity in sorted(aa.keys()&bb.keys()):
            if business(aa[entity])!=business(bb[entity]):
                if len(diff)<30:diff.append(entity)
        results[name]=dict(actual_count=len(aa),reference_count=len(bb),identity_set_equal=aa.keys()==bb.keys(),
            business_difference_count=sum(business(aa[e])!=business(bb[e]) for e in aa.keys()&bb.keys()),examples=diff)
    plan=load(new/'INCREMENT_PLAN.json')
    result=dict(contract_id='V4_R1_1_FULL_TARGET_VALUE_PARITY',compute_sessions=plan['compute_sessions'],mode=plan['mode'],domains=results,
        acceptance='PASS' if all(r['identity_set_equal'] and not r['business_difference_count'] for r in results.values()) else 'FAIL',
        new_generation=a.generation,reference_core=ref(root,old/'owner_v3/CORE_REPLAY.json'),
        scope='All raw/adjusted/Core/Profile/status/Sector/rotation/relative/Seed fields; Structure identities, Focus, Period and publication require independent gates')
    if qualification:
        prior=Path('G:/codex_tmp/r11_full_values.json')
        if Path(a.out).resolve()==prior.resolve():raise ValueError('PRESERVE_ORIGINAL_FAIL_REPORT')
        qualification['original_fail']=dict(path=str(prior),sha256=sha256_file(prior),acceptance=load(prior)['acceptance'])
        result['reference_qualification']=qualification
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
