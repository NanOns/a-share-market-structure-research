"""Retain the mandatory 34/101/49/4 counterexamples against full new projection."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
OUT=ROOT/'docs/audits/v4_full_closeout_20261012/focus_regression'

def main():
    frozen_path=ROOT/'docs/audits/s1b_20261012/FROZEN_REGRESSION.json'
    frozen=json.loads(frozen_path.read_bytes())
    current_path=WORK/'runtime/v4_full_closeout_focus_20261012_R2/CURRENT_ACTION_FOCUS.json.gz'
    current=json.loads(gzip.decompress(current_path.read_bytes()))
    byid={e['episode_id']:e for e in current['episodes']}
    failures=[]
    for sample in frozen['observations']:
        episode=byid[sample['episode']]
        obs=next(o for o in episode['observations'] if o['trade_date']==sample['date'])
        if obs['price_path']['metrics']!=sample['after']:
            failures.append(dict(kind='observation',episode=sample['episode'],day=sample['date']))
    # Every changed outcome and predicate is looked up in the complete current
    # projection. A missing record is an error, never a smaller denominator.
    checked={}
    for key in frozen:
        if key=='observations':continue
        value=frozen[key]
        if not isinstance(value,list):continue
        checked[key]=len(value)
        for sample in value:
            if not isinstance(sample,dict) or 'episode' not in sample:continue
            episode=byid[sample['episode']]
            after=sample.get('after')
            if 'outcome' in key:
                candidates=episode['outcomes']
                if isinstance(after,dict) and 'anchor_id' in after:
                    actual=next(o for o in candidates if o['anchor_id']==after['anchor_id'] and o['horizon']==after['horizon'])
                    if actual['metrics']!=after['metrics']:failures.append(dict(kind=key,episode=sample['episode']))
            elif 'predicate' in key:
                if isinstance(after,dict) and 'trade_date' in after:
                    actual=next(o for o in episode['observations'] if o['trade_date']==after['trade_date'])
                    if actual['predicate_evidence']!=after['predicate_evidence']:failures.append(dict(kind=key,episode=sample['episode']))
    result=dict(contract_id='V4_FULL_PROJECTION_MANDATORY_COUNTEREXAMPLES_R1',observations=len(frozen['observations']),
                securities=len({o['security'] for o in frozen['observations']}),other_frozen_sets=checked,
                projection_episodes=len(byid),failures=failures,expected_source_sha256=hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
                projection_sha256=hashlib.sha256(current_path.read_bytes()).hexdigest(),
                status='PASS_SCOPED' if not failures else 'FAIL',production_changed=False)
    assert result['observations']==101 and result['securities']==34
    OUT.mkdir(parents=True,exist_ok=False)
    (OUT/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
    return int(bool(failures))

if __name__=='__main__':raise SystemExit(main())
