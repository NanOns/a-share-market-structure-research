"""Independent contract policy gate; no runtime imports."""
import json,hashlib
from copy import deepcopy
from scripts.v4_11_promotion_contract_r1 import ROOT
def validate(c,case):
    if c['owning_anchor_type']!='PRIOR_HIGH' or c['owner_rule']!='UNIQUE_TYPE_NOT_ACTIVE_SELECTOR':raise ValueError('OWNER_ALIAS')
    if case.get('existing') and not case.get('prior_ref'):raise ValueError('MISSING_T_MINUS_1')
    if case.get('existing') and case.get('create'):raise ValueError('DUPLICATE_CREATION')
    if case.get('episode_transition') and not all(case.get(n) for n in c['transition_fields']):raise ValueError('TRANSITION_IDENTITY')
    if case.get('prior_date')==case.get('date') and case.get('date'):raise ValueError('SAME_DAY_PRIOR')
    if case.get('creation_day') and case.get('state') in ['TESTING','BREAKOUT_ACCEPTED']:raise ValueError('SELF_CONFIRM')
    if case.get('absence_quality')=='UNKNOWN' and case.get('create'):raise ValueError('UNKNOWN_IS_NOT_FALSE')
    return True
def run():
    path=ROOT/'config/v4_12_breakout_episode_contract_v1.json';c=json.loads(path.read_bytes())
    validate(c,dict(existing=True,prior_ref='t-1'))
    vector_path=ROOT/'config/v4_12_breakout_episode_vectors_v1.json';vectors=json.loads(vector_path.read_bytes())['vectors']
    assert [v['id'] for v in vectors]==c['hard_vectors']
    for case in vectors:validate(c,case)
    negatives=[dict(existing=True),dict(existing=True,prior_ref='t-1',create=True),dict(owner_alias=True),dict(episode_transition=True),dict(date='t',prior_date='t'),dict(creation_day=True,state='BREAKOUT_ACCEPTED'),dict(absence_quality='UNKNOWN',create=True)]
    for case in negatives:
        other=deepcopy(c)
        if case.get('owner_alias'):other['owner_rule']='ACTIVE_ALIAS'
        try:validate(other,case)
        except ValueError:continue
        raise AssertionError(case)
    stage=json.loads((ROOT/'reports/v4_12_runtime_r13/R13_STAGE_CONTRACT.json').read_bytes())
    for r in stage['protected']:assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
    out=dict(status='PASS',contract=dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size),vector_contract=dict(path=vector_path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(vector_path.read_bytes()).hexdigest(),bytes=vector_path.stat().st_size),negative_cases=len(negatives),hard_vectors=c['hard_vectors'],completion='V4_12_R13A_BREAKOUT_EPISODE_CONTINUITY_CONTRACT_READY',next_stage='R13B')
    (ROOT/'reports/v4_12_runtime_r13/R13A_CONTRACT_LOCAL_GATE.json').write_bytes((json.dumps(out,sort_keys=True,indent=2)+'\n').encode());print(out['completion'])
if __name__=='__main__':run()
