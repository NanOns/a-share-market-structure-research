"""Whole-population frozen-owner equivalence, separate from producer assertions."""
import argparse,gzip,json
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json


def rows(path):
    with gzip.open(path,'rt',encoding='utf8') as stream:
        for line in stream:yield json.loads(line)


def value(cell):
    if isinstance(cell,dict):
        return {key:cell[key] for key in ('value','quality','quality_state','unknown_reason','reason_code') if key in cell}
    return cell


def semantics(row,families):
    return {family:{key:value(cell) for key,cell in row.get(family,{}).items()} for family in families}


def main(folder):
    root=Path(__file__).resolve().parents[1];folder=Path(folder)
    head=json.loads((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    replay=json.loads((folder/'owner_v3/PROFILE_STRUCTURE_REPLAY.json').read_bytes())
    sectors=json.loads((folder/'sector_v3/SECTOR_REPLAY.json').read_bytes())
    checks=[];errors=[]
    for item in replay['owners']:
        day=item['owner']['trade_date'];old=head['owners'][day]
        sector=next(s for s in sectors['owners'] if s['trade_date']==day)
        for domain,binding,families in [('core',item['owner']['core'],('fields',)),
            ('base_profile',item['owner']['profiles'],('derived_fields','states')),
            ('sector',sector['native'],('fields',))]:
            before=checked(root,old[domain]);after=checked(root,binding);count=0
            left=rows(before);right=rows(after)
            from itertools import zip_longest
            for a,b in zip_longest(left,right):
                count+=1
                key='security_id' if domain!='sector' else 'sector_id'
                if a is None or b is None or a[key]!=b[key]:
                    errors.append(dict(day=day,domain=domain,row=count,reason='IDENTITY_OR_COUNT_MISMATCH'));continue
                av,bv=semantics(a,families),semantics(b,families)
                if av!=bv:
                    differences={f:[k for k in set(av[f])|set(bv[f]) if av[f].get(k)!=bv[f].get(k)] for f in families}
                    errors.append(dict(day=day,domain=domain,entity=a[key],different_fields=differences))
            checks.append(dict(day=day,domain=domain,rows=count,baseline=old[domain],replayed=binding))
    output=root/'docs/evidence/dynamic_daily_20261009/DD03_OWNER_EQUIVALENCE.json'
    atomic_json(root,output,dict(contract_id='DYNAMIC_DAILY_FROZEN_OWNER_EQUIVALENCE_V1',
        evidence_kind='REAL_FROZEN_INPUT_FULL_POPULATION',checks=checks,errors=errors,
        acceptance='PASS_EXACT_NUMERIC_AND_QUALITY_EQUIVALENCE' if not errors else 'FAIL_EQUIVALENCE',
        excluded='Publication IDs, source digests and availability timestamps are intentionally independent namespaces',
        external_acceptance='NOT_GRANTED',next_stage='DYNAMIC_TARGET_DERIVED_READY_AND_CAS'))
    print(json.dumps(dict(checks=len(checks),errors=len(errors),sample_errors=errors[:3])))
    return not errors


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',required=True);args=parser.parse_args()
    raise SystemExit(0 if main(args.folder) else 1)
