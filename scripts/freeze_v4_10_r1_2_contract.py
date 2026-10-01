"""Freeze a separate authority revision, preserving all earlier candidates."""
from pathlib import Path
from copy import deepcopy
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.promote_v4_09_accepted_head import bind,validate
def main():
    assert validate()['status']=='PASS'
    names=['research_state_contract','machine_ast','parameter_set','input_schema','output_schema','input_provenance']
    from scripts.v4_10_old_state_fixture_producer import emit_old_goldens
    atomic_json(ROOT/'config/v4_10_boundary_old_source_fixture_r1_2.json',dict(contract_id='V4_10_INDEPENDENT_OLD_STATE_GOLDEN_SOURCE_R1_2',
        producer_binding=bind('scripts/v4_10_old_state_fixture_producer.py'),source_authority='Immutable independent V0 golden output issued only by disposable DB owner',goldens=emit_old_goldens()))
    for name in names:
        value=json.loads((ROOT/f'config/v4_10_{name}_r1_1.json').read_text(encoding='utf8'))
        if name!='parameter_set':value['engineering_revision']='R1.2'
        if name=='research_state_contract':
            value.update(repair_task=bind('docs/evidence/V4_10_R1_2_EXTERNAL_REAUDIT_REPAIR_TASK_20261001.md'),
                supersedes_candidate=bind('reports/v4_10/V4_10_R1_1_STAGE_CANDIDATE_MANIFEST.json'),
                model_boundary='immutable OLD source authority + exact migration manifest; from tuple must differ from current',
                db_hardening='024 immutable boundary prior ledger, implemented-status authority, controlled reducer publisher role',
                controlled_publisher_contract='V4_10_CONTROLLED_STATE_PUBLISHER_R1_2')
        if name=='input_provenance':
            value.update(implemented_status_authority='IMPLEMENTED only for an applicable implemented owner; UNKNOWN still binds its producer publication',
                boundary_prior_ledger='V4_10_BOUNDARY_PRIOR_LEDGER_R1_2',controlled_publisher_role='v4_10_reducer_publisher_r1_2')
            for field,d in value['fields'].items():
                d['not_applicable_entity_types']=['SECTOR'] if d['implemented'] and d['accepted_entity_types']==['STOCK'] else ['STOCK'] if field in ('WARM','dq5') else []
        atomic_json(ROOT/f'config/v4_10_{name}_r1_2.json',value)
    # The prior fixture is produced through a disposable trusted resolver; expectations
    # remain literal. This interim freeze binds all six contracts before fixture creation.
    atomic_json(ROOT/'reports/v4_10/V4_10_R1_2_CONTRACT_FREEZE.json',dict(contract_id='V4_10_R1_2_CONTRACT_FREEZE',status='PASS_R1_2_AUTHORITY_FREEZE',
        fixture_construction_only=True,bindings={n:bind(f'config/v4_10_{n}_r1_2.json') for n in names}))
    from scripts.build_v4_10_r1_2_vectors import build_vectors
    vectors=build_vectors();atomic_json(ROOT/'config/v4_10_machine_vectors_r1_2.json',dict(vectors=vectors,contract_id='V4_10_R1_2_STATIC_VECTORS',
        original_vectors=bind('config/v4_10_machine_vectors_r1_1.json'),original_expected_values_preserved=True,
        fixture_supersession='Two no-op positive boundary inputs adapted to authentic OLD authority; original files untouched'))
    names+=['machine_vectors','boundary_old_source_fixture']
    atomic_json(ROOT/'reports/v4_10/V4_10_R1_2_CONTRACT_FREEZE.json',dict(contract_id='V4_10_R1_2_CONTRACT_FREEZE',status='PASS_R1_2_AUTHORITY_FREEZE',
        bindings={n:bind(f'config/v4_10_{n}_r1_2.json') for n in names},repair_task=bind('docs/evidence/V4_10_R1_2_EXTERNAL_REAUDIT_REPAIR_TASK_20261001.md'),
        authority=json.loads((ROOT/'reports/v4_10/V4_10_R1_1_CONTRACT_FREEZE.json').read_text())['authority'],
        stage_entry=bind('docs/evidence/V4_10_R1_2_STAGE_ENTRY_20261001.md'),
        protected_bindings=json.loads((ROOT/'reports/v4_10/V4_10_R1_1_CONTRACT_FREEZE.json').read_text())['protected_bindings'],
        previous_candidate=bind('reports/v4_10/V4_10_R1_1_STAGE_CANDIDATE_MANIFEST.json'),business_thresholds_unchanged=True,stop_for_external_reaudit=True))
    print('R1.2 frozen vectors:',len(vectors))
if __name__=='__main__':main()
