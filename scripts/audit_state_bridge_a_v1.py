"""Small independent numeric oracle over frozen original target values (no recompute)."""
import ast, gzip, hashlib, json, random
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked, gzrows
from workbench_analysis.v4_14_replay_io import publish, ref
from v4.confirmation import package
ROOT=Path(__file__).resolve().parents[1]
OUT='docs/evidence/next_stage_after_audit_r1_20261010'

def run():
    receipt=json.loads((ROOT/'docs/evidence/pre_next_t0_execution_r1_20261010/final/STATE_PUBLISHER_ISOLATED_RUN.json').read_bytes())
    source=json.loads(gzip.decompress(checked(ROOT,receipt['source']).read_bytes()))
    facts={r['security_id']:r['target_values'] for r in gzrows(checked(ROOT,source['source_owners']['prewatch']))}
    contract, manifest, parameters, machine, scanner=package()
    tree=ast.parse(checked(ROOT,manifest['legacy_source']).read_text(encoding='utf-8'))
    assert {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}==manifest['exact_function_AST']
    truths=[r for r in source['scenario_outputs'] if r['state']=='TRUE']
    fixed=truths[:12]+[next(r for r in truths if r['scenario']==s) for s in sorted({r['scenario'] for r in truths})]
    sampled=random.Random(20261010).sample(truths,24)
    selected={ (r['security_id'],r['scenario']):r for r in fixed+sampled}
    results=[]
    for key,row in sorted(selected.items()):
        v=facts[key[0]]
        base=all(v[k] is True for k in ('normal_universe','actual_bar','window_valid','liq20','input_identity_compatible')) and all(v[k] is False for k in ('structure_break_v3','extended_v3','first_day_damage','severe_drop'))
        if key[1]=='LAUNCH_CONFIRM':
            expected=base and v['breakout_v3'] is True and v['break_margin_close20']>0 and v['ret1_adj']>0 and v['clv']>=.60 and v['amr20_mean_prior']>=1.20 and v['intraday_reject_high20'] is False
        elif key[1]=='RECOVERY_TURN':
            r5=v['recovery_v3'] is True and v['reclaim_ma5'] is True
            r20=v['reclaim_ma20'] is True and v['prior5_below_ma20_count']>=2 and v['ma20_nondeclining_3'] is True
            expected=base and (r5 or r20) and v['ret1_adj']>0 and v['clv']>=.55 and v['rps5_delta3']>0 and v['amr20_mean_prior']>=1.05 and v['close_to_ma20']>=.98
        elif key[1]=='STRONG_PULLBACK':expected=base and v['pullback_episode_confirmed'] is True
        else:raise ValueError('UNEXPECTED_TRUE_SCENARIO')
        original=scanner(v)
        results.append(dict(security_id=key[0],scenario=key[1],manual_numeric_result=expected,publisher_state=row['state'],original_ast_eligible=original[manifest['scenario_mapping'] and {'LAUNCH_CONFIRM':'launch','RECOVERY_TURN':'recovery_turn','STRONG_PULLBACK':'pullback'}[key[1]]]['eligible']))
        assert expected is True and results[-1]['original_ast_eligible'] is True
    return publish(ROOT,OUT+'/A_NUMERICAL_ORACLE.json',dict(contract_id='A_SMALL_INDEPENDENT_NUMERIC_ORACLE_V1',source=receipt['source'],target_values_source=source['source_owners']['prewatch'],original_ast_source=manifest['legacy_source'],oracle=ref(ROOT,'scripts/audit_state_bridge_a_v1.py'),random_seed=20261010,fixed_count=len(fixed),random_count=24,unique_checked=len(results),TRUE_population=len(truths),results=results,result='PASS_SCOPED',limitation='Only sampled TRUE predicates; does not independently regenerate upstream target_values or validate all 200 regression meanings.',production_authorization=False))

if __name__=='__main__': print(json.dumps(run()))
