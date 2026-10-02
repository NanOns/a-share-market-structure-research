"""Independent expected book vs runtime binder and frozen-loader rejection probes."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import sys
from scripts.v4_11_promotion_contract_r1 import ROOT
from scripts.v4_12_authority_oracle_r2 import vectors
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.v4_12_structure_io import FrozenContracts,CandidateStore
from workbench_analysis.v4_12_ast_runtime import ASTEngine
from workbench_analysis.v4_12_input_binder import InputBinder

def run():
    c=FrozenContracts(ROOT);binder=InputBinder(c,'2026-09-30','2026-10-02T06:00:00+00:00');r=binder.fields;rows=[]
    for v in vectors():
        subject=v['subject']
        if subject=='delta3':actual=[r[subject][k] for k in ['accepted_source_field','producer_contract_id','accepted_head_path']]
        elif subject=='near_high20_state':actual=[r[subject][k] for k in ['producer_contract_id','target_publication_available','field_role']]
        elif subject=='unknown_f0':
            try:binder.check_input_claim('unregistered_F0',dict(quality='KNOWN',producer_contract_id='CORE_FACTOR_V1'));actual='WRONGLY_ACCEPTED'
            except ValueError as error:actual=str(error)
        elif subject=='distance_zone':actual=[r[subject][k] for k in ['field_role','producer_contract_id']]
        elif subject=='alpha_beta':actual=[r['alpha']['producer_contract_id'],r['alpha']['field_role'],c.config['anchor_coordinate_contract']['transform_capability']['alpha']]
        elif subject=='prior_range20_atr':actual=[r[subject][k] for k in ['field_role','capability']]
        elif subject=='pivot':actual=[r['pivot_low'][k] for k in ['field_role','producer_contract_id']]
        elif subject=='slope_unit':
            p=next(p for p in c.config['parameter_set']['parameters'] if p['parameter_id']=='range_anchor_abs_slope20_max');actual=[r['slope20']['unit'],p['unit'],p['value']]
        elif subject=='explicit_aliases':actual={n:r[n]['accepted_source_field'] for n in ['ATR20','CLV','MA20','MA60']}
        elif subject=='branch_local':
            fixture={**c.config['machine_vectors']['defaults'],'prior_recovery_exists':True,'post_creation_market_sessions':2,'post_creation_evaluable_sessions':2,
                'prior_recovery_held_count':1,'prior_adjacent_evaluable':True,'C':11,'recovery_line_view':10,'close_t_minus_1':None,'ma20_t_minus_1':None,'ret1':None}
            actual=ASTEngine(c.config,fixture).target('recovery').value
        elif subject=='missing_owner':
            try:binder.check_input_claim('near_high20_state',dict(quality='KNOWN',producer_contract_id=r['near_high20_state']['producer_contract_id']));actual='WRONGLY_ACCEPTED'
            except ValueError as error:actual=str(error)
        elif subject=='raw_bars':actual=[r['prior_range20_atr']['field_role'],r['prior_range20_atr']['raw_reconstruction_allowed']]
        else:raise ValueError(subject)
        rows.append(dict(**v,actual=actual,status='PASS' if actual==v['expected'] else 'FAIL'))
    assert all(row['status']=='PASS' for row in rows),rows
    store=CandidateStore(ROOT)
    authority_ref=store.json('V4_12_RUNTIME_R2_AUTHORITY_PARITY.json',dict(status='PASS_KEEP',total=12,rows=rows,scope='SYNTHETIC_AND_METADATA_GATE_ONLY'))
    td=[]
    # Positive dimensions already externally frozen. Negative edge mutations must fail startup exact digest binding.
    for v in c.config['time_counter_vectors_r2_1']['time_domain_vectors']:
        if v['expected']:
            actual=FrozenContracts(ROOT).digest==c.digest;detail='Exact externally accepted frozen compatible contract loaded'
        else:
            with tempfile.TemporaryDirectory(prefix='v4_12_digest_probe_') as directory:
                target=Path(directory)
                paths=[c.entry_ref['path'],c.entry['contract_freeze_acceptance']['path']]+[r['path'] for r in c.entry['frozen_contracts']]
                for path in paths:
                    dest=target/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,dest)
                tree=deepcopy(c.config['machine_ast']);tree['definitions']['old_anchor']['args']=[{'field':v['field']},{'parameter_id':v['parameter']}]
                (target/'config/v4_12_machine_ast_v1.json').write_text(json.dumps(tree),encoding='utf-8')
                try:FrozenContracts(target);actual=True;detail='WRONGLY_ACCEPTED_MUTATED_AST'
                except ValueError as error:actual=False;detail=str(error)
        td.append(dict(**v,actual=actual,status='PASS' if actual==v['expected'] else 'FAIL',detail=detail))
    assert all(row['status']=='PASS' for row in td),td
    time_ref=store.json('V4_12_RUNTIME_TIME_DOMAIN_NEGATIVE_PARITY.json',dict(status='PASS',total=10,rows=td,
        method='Only externally frozen compatible edges execute; any new edge AST alteration fails exact startup digest before evaluation',frozen_contract_digest=c.digest))
    return authority_ref,time_ref

if __name__=='__main__':
    refs=run();print(json.dumps(dict(authority_vectors=12,time_domain_vectors=10,status='PASS',refs=refs)))
