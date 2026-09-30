"""Independent declared-oracle comparison, domain and transition invariants."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.v4.research_state import reduce_state
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.promote_v4_09_accepted_head import bind

def check_vectors():
    vectors=json.loads((ROOT/'config/v4_10_machine_vectors_v1.json').read_text(encoding='utf8'))['vectors']
    contract=json.loads((ROOT/'config/v4_10_research_state_contract_v1.json').read_text(encoding='utf8'))
    schema=json.loads((ROOT/'config/v4_10_output_schema_v1.json').read_text(encoding='utf8'))
    checks=[]; coverage={}; outputs=[]
    for v in vectors:
        for tag in v['coverage']:coverage.setdefault(tag,[]).append(v['id'])
        try:
            r=reduce_state(v['input']);outputs.append(r)
            diff={k:dict(expected=e,actual=r.get(k)) for k,e in v['expected'].items() if e!=r.get(k)}
            errors=[]
            if v['expected_error']: errors.append('EXPECTED_ERROR_NOT_RAISED')
            if set(schema['required'])-set(r):errors.append('OUTPUT_SCHEMA_MISSING_FIELDS')
            for axis,domain in contract['axes'].items():
                allowed=domain[r['entity_type']] if isinstance(domain,dict) else domain
                if r[axis] not in allowed:errors.append('ILLEGAL_AXIS:'+axis)
            if r['state_freshness']=='STALE' and r['final_eligibility']!='UNKNOWN':errors.append('STALE_COUNTED_ELIGIBLE')
            if 'HARD_INVALIDATION' in r['transition_reasons'] and r['health']!='DAMAGED':errors.append('HARD_INVALIDATION_OVERRIDDEN')
            if r['boundary_event'] and 'REENTERED' in r['transition_reasons']:errors.append('BOUNDARY_FAKE_REENTRY')
            if 'REENTERED' in r['transition_reasons'] and (not r['parent_episode_id'] or r['episode_id']==r['parent_episode_id']):errors.append('REENTRY_IDENTITY_INVALID')
            if r['parent_episode_id'] and r['parent_episode_id'] not in r['preserved_followup_episode_ids']:errors.append('OLD_FOLLOWUP_LOST')
            if v['input']['prior_state'] and 'ENROLLED' not in r['transition_reasons'] and 'REENTERED' not in r['transition_reasons'] and not r['boundary_event']:
                if r['episode_id']!=v['input']['prior_state']['episode_id']:errors.append('STAGE_CHANGE_NEW_EPISODE')
            checks.append(dict(id=v['id'],passed=not diff and not errors,differences=diff,invariant_errors=errors))
        except ValueError as e:
            checks.append(dict(id=v['id'],passed=bool(v['expected_error'] and v['expected_error'] in str(e)),error=str(e)))
    required=['hard_over_confirmation','required_unknown','PREWATCH_GT_SEED','CONFIRMED_GT_PREWATCH','stock_warm_na','upgrade_immediate',
        'downgrade_day1','downgrade_day2','hysteresis_break','risk_extreme','health_boundaries','tracking','expiry_boundary',
        'expiry_unknown_pause','expiry_baseline_frozen','next_session_reentry','same_day_reentry_forbidden','model_boundary_not_reentry',
        'scenario_unknown','all_maturity_preserved','all_tracking_preserved','health_unknown','no_fake_detector','prior_binding']
    missing=sorted(set(required)-set(coverage))
    result=dict(contract_id='V4_10_INDEPENDENT_POSTCHECK_V1',status='PASS' if not missing and all(v['passed'] for v in checks) else 'FAIL',
        vector_count=len(vectors),mismatch_count=sum(not v['passed'] for v in checks),missing_coverage=missing,
        oracle='MANUALLY_DECLARED_STATIC_EXPECTATIONS; verifier uses no runtime rule helper as expected-value oracle',
        source_vectors=bind('config/v4_10_machine_vectors_v1.json'),checks=checks)
    covered=dict(contract_id='V4_10_MACHINE_VECTOR_COVERAGE_V1',status=result['status'],vector_count=len(vectors),coverage=coverage,
        axes={axis:sorted({r[axis] for r in outputs}) for axis in contract['axes']},
        unknown_semantics=dict(maturity='last_known enum retained',tracking='last_known enum retained',scenario='value retained + UNKNOWN status',
            health='UNKNOWN',validity='UNKNOWN',eligibility='UNKNOWN',state_freshness='STALE'),
        missing_required_tags=missing)
    return result,covered

def main():
    result,coverage=check_vectors()
    atomic_json(ROOT/'reports/v4_10/V4_10_INDEPENDENT_POSTCHECK.json',result)
    atomic_json(ROOT/'reports/v4_10/V4_10_MACHINE_VECTOR_COVERAGE.json',coverage)
    print(json.dumps(dict(status=result['status'],vector_count=result['vector_count'],mismatch_count=result['mismatch_count'])))
    return result['status']!='PASS'

if __name__=='__main__':
    from scripts.verify_v4_10_r1_1 import main as repair_main
    sys.exit(repair_main())
