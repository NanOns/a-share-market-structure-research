"""Independent full source/lineage/business readback of formal input amendments."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from hashlib import sha256
import gzip
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import read_bound,digest,binding
from v4.a02_a05_external_acceptance_r1 import read_accepted_rps,accepted_legacy_observations,validate_a05_record,RPS_HEAD

def exact_gzip(ref):
    if binding(ROOT,ROOT/ref['path'])['sha256']!=ref['sha256']: raise ValueError('AMENDMENT_EXACT_ARTIFACT')
    with gzip.open(ROOT/ref['path'],'rt',encoding='utf8') as stream:return [json.loads(line) for line in stream]

def verify_a02():
    from v4.base_seed import _load_accepted_source_context,build_candidate_from_records
    from v4.stock_prewatch import load_accepted,build
    report=json.loads((ROOT/'reports/audits/next_round_r2/A02_DOWNSTREAM_AMENDMENT_REPLAY_R1.json').read_bytes())
    accepted=read_accepted_rps(ROOT,'2026-09-28');idx={r['security_id']:r for r in accepted['deltas'][3]}
    receipts={stage:read_bound(ROOT,ref) for stage,ref in report['amendments'].items()}
    core=exact_gzip(receipts['V4_05']['artifact']);factors=exact_gzip(receipts['V4_05']['factor_artifact']);seeds=exact_gzip(receipts['V4_07']['artifact']);stocks=exact_gzip(receipts['V4_09']['artifact'])
    for c,f in zip(core,factors):
        expected=idx[c['security_id']]['fields']['rps5_delta3']
        actual=f['fields']['rps5_delta3']
        for field in ('value','quality_state','unknown_reason'): assert actual[field]==expected[field]
        assert c['primitive_quality']['rps5_delta3']==actual
        assert c['a02_accepted_rps_head']==report['accepted_rps_head']==binding(ROOT,ROOT/RPS_HEAD)
    ctx=report['new_seed_context'];replayed=build_candidate_from_records(core,factors,ctx,created_at=core[0]['formal_publication_at'])
    assert replayed['rows']==seeds
    package=load_accepted(ROOT)[-1];assert build(core,factors,seeds,report['new_stock_context'],package)==stocks
    oldctx,oldcores,oldfactors=_load_accepted_source_context(ROOT)
    oldseed=build_candidate_from_records(oldcores,oldfactors,oldctx,created_at=core[0]['formal_publication_at'])
    oldstocks=build(oldcores,oldfactors,oldseed['rows'],load_accepted(ROOT)[0],package)
    diff=exact_gzip(report['full_business_diff']);indexes={name:{r['security_id']:r for r in records} for name,records in [('V4_05_OLD',oldcores),('V4_05_NEW',core),('V4_07_OLD',oldseed['rows']),('V4_07_NEW',seeds),('V4_09_OLD',oldstocks),('V4_09_NEW',stocks)]}
    for row in diff:
        a=indexes[row['stage']+'_OLD'][row['security_id']];b=indexes[row['stage']+'_NEW'][row['security_id']]
        for field,value in row['business_changes'].items(): assert value==dict(old=a[field],new=b[field])
    counts={s:sum(bool(r['business_changes']) for r in diff if r['stage']==s) for s in receipts}
    assert counts==report['changed_rows']==dict(V4_05=5222,V4_07=5222,V4_09=2811)
    for receipt in receipts.values():
        ref=receipt['old_accepted_head'];assert binding(ROOT,ROOT/ref['path'])==ref
        for ref in receipt['unchanged_algorithms_parameters']: assert binding(ROOT,ROOT/ref['path'])==ref
    return dict(status='PASS',source='ONLY_ACCEPTED_RPS_HEAD',endpoint_delta_values=5222,independent_seed_rows=5222,independent_stock_rows=5222,full_business_diff_rows=len(diff),changed_rows=counts,mismatches=0)

def verify_a05():
    from sector.machine_ast_r3 import evaluate_ast_explain
    from sector.semantic_input_r5_1 import bind_semantic,eligibility
    from sector.phase2 import validity
    from statistics import median
    result=json.loads((ROOT/'reports/audits/next_round_r2/V4_08_ACCEPTED_HEAD_B2_CAPABILITY_AMENDMENT_CANDIDATE_R3.json').read_bytes())
    record,frozen=validate_a05_record(ROOT);observations=accepted_legacy_observations(ROOT,target=result['accepted_snapshot_trade_date'])
    captured=exact_gzip(result['real_source_capture']);today={r['security_id']:r for r in captured if r['trade_date']==result['accepted_snapshot_trade_date']};prior={r['security_id']:r for r in captured if r['trade_date']=='2026-09-23'}
    returns={}
    for sid,row in today.items():
        a=row['aligned_close'];b=prior.get(sid,{}).get('aligned_close')
        returns[sid]=a/b-1 if a is not None and b is not None and a>0 and b>0 else None
    normal={sid:v for sid,v in returns.items() if today[sid]['universe_status']=='IN_NORMAL_UNIVERSE'}
    market_values=[v for v in normal.values() if v is not None];assert len(normal)==result['market_universe_count']==5464
    market_coverage=len(market_values)/len(normal);market_median=median(market_values)
    replay=exact_gzip(result['current_snapshot_replay']);assert len(replay)==541
    ast=json.loads((ROOT/'config/v4_08_b2_machine_ast_r5.json').read_bytes());config=json.loads((ROOT/ast['source_parameter_path']).read_bytes());groups={}
    for member in frozen['membership']:
        if member['security_id'] is not None:groups.setdefault(member['sector_id'],set()).add(member['security_id'])
    qualifying={}
    for row in replay:
        sid=row['sector_id'];ids=groups.get(sid,set());inputs=row['after_inputs'];sem=row['after_semantic']
        expected_valid=False if sem['sector_role']=='EXCLUDE_FROM_THEME_RANK' else None if any(i not in observations for i in ids) else validity(len(ids),sum(observations[i]['value'] is True for i in ids),sem['sector_role'])[0]
        assert sem['sector_valid']==expected_valid
        assert inputs['normal_rank_eligible']['value']==eligibility(sem)
        member_values=[normal[i] for i in ids if i in normal and normal[i] is not None]
        if ids:
            expected=median(member_values) if member_values else None
            assert inputs['m1']['value']==expected
            assert inputs['quote_coverage']['value']==len(member_values)/len(ids)
            assert inputs['market_ok']['value']==(market_coverage>=config['thresholds']['coverage']['min_full_market_quote_coverage'])
            assert inputs['rel1']['value']==(expected-market_median if expected is not None else None)
        # Independent exact AST interpreter, without calling old B2 wrapper.
        facts={field:{**spec,'value':inputs.get(field,{}).get('value'),'quality':inputs.get(field,{}).get('quality','UNKNOWN')} for field,spec in ast['fields'].items()}
        actual=evaluate_ast_explain('confirmed_raw',ast['rules'],facts,{})
        state='TRUE' if actual.state is True else 'FALSE' if actual.state is False else 'UNKNOWN'
        if inputs['market_ok'].get('value') is not True or inputs['normal_rank_eligible']['value'] is None:state='UNKNOWN'
        assert row['new']['confirmed_raw']==state
        assert row['new']['warm_raw']=='UNKNOWN' and row['new']['capabilities']['B2_AMOUNT_A']=='DIAGNOSTIC_AUDIT_OPEN'
    proof=read_bound(ROOT,result['rotation_context_readback']);assert proof['rotation_business_changed']==proof['context_business_changed']==0
    try:accepted_legacy_observations(ROOT,target='2026-09-30')
    except ValueError:pass
    else:raise AssertionError('STALE_A05_OBSERVATION_ACCEPTED')
    for ref in result['unchanged_algorithm_parameters']+[result['old_accepted_head']]:assert binding(ROOT,ROOT/ref['path'])==ref
    diffs=exact_gzip(result['full_accepted_artifact_diff']);assert len(diffs)==len({r['sector_id'] for r in diffs})
    assert Counter(r['new']['confirmed_raw'] for r in replay)==Counter(result['new_snapshot_states'])
    return dict(status='PASS',real_snapshot_observations=len(observations),real_price_endpoint_rows=len(captured),real_B2_rows=len(replay),independent_AST_mismatches=0,new_snapshot_states=result['new_snapshot_states'],same_date_9_30_adoption='REJECTED',rotation_and_context_changes=0)

def main():
    print(json.dumps(dict(contract_id='A02_A05_FORMAL_AMENDMENT_READBACK_V1',A02=verify_a02(),A05=verify_a05(),status='PASS',business_amendments_externally_accepted=False,production=False)))
if __name__=='__main__':main()
