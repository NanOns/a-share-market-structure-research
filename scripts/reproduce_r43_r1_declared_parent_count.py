"""Expected-failure reproduction of the frozen '23 parent' count claim."""
from pathlib import Path
from collections import defaultdict
import gzip,json

ROOT=Path(__file__).resolve().parents[1]
def main():
    groups=defaultdict(list)
    with gzip.open(ROOT/'docs/evidence/r4_3_four_session_closeout_20261009/latest_member_S.jsonl.gz','rt',encoding='utf8') as f:
        for line in f:
            r=json.loads(line);groups[r['sector_id']].append(r)
    parent=[k for k,v in groups.items() if all('DERIVED_PARENT' in r['source'] for r in v)]
    leaf=[k for k in groups if k.startswith('INDUSTRY:') and k not in parent and k!='INDUSTRY:T00']
    print(json.dumps(dict(actual_named_leaf=len(leaf),actual_derived_parent=len(parent),unclassified=['INDUSTRY:T00'],source_industry_count=133,parent_ids=sorted(parent))),flush=True)
    assert (len(leaf),len(parent))==(110,23), 'FROZEN_23_PARENT_COUNT_CLAIM_CONTRADICTS_ACTUAL_MEMBER_SOURCE'

if __name__=='__main__':main()
