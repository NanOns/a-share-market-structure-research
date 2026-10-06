"""Build explicit versioned successors; no accepted head or historical migration writes."""
import copy
import json
import re
from scripts.full_chain_repair_io import ROOT,write,binding,PREFIX
from scripts.v4_16_capability_resolution import FIELDS,resolve

def build():
    old=json.loads((ROOT/'config/v4_16_runtime_dependencies_v4.json').read_bytes())
    head=json.loads((ROOT/old['current_audit_head']['path']).read_bytes())
    ids=set(old['blocked_capabilities']) | {k for k,v in head['entries'].items() if not v.get('alias_of') and (v.get('blocks_affected_capability_in_shadow') or v.get('blocks_v4_16_runtime_activation'))}
    graph={'PURE_CORE_STOCK':['V4_09_N01_CURRENT_RUNTIME_PREWATCH'], 'V4_09_N01_CURRENT_RUNTIME_PREWATCH':[],
           'AMOUNT_A_H21_FORMAL_CONSUMER':[], 'HISTORICAL_AMOUNT_A_FORMAL_CONSUMER':[]}
    for issue in ids:
        for cap in head['entries'][issue]['affected_capabilities']:graph.setdefault(cap,[])
    resolution=dict(contract_id='V4_16_RUNTIME_CAPABILITY_RESOLUTION_V1',version='1.0.0',current_audit_head=old['current_audit_head'],
        blocked_issue_ids=sorted(ids),runtime_capability_dependency_graph=graph,
        current_audit_issue_resolution={k:{f:head['entries'][k].get(f,False) for f in FIELDS} for k in sorted(ids)},
        dependency_evidence=[binding('scripts/v4_16_real_owner_projection_v1.py'),binding('scripts/v4_16_go_forward_shadow_runtime.py')],
        pure_core_prewatch_decision='DEPENDS_ON_CURRENT_PREWATCH_OWNER_STATE_AND_ENROLLED_TRANSITION',
        runtime_authorized=False,production=False)
    resolution['effective_blocked_runtime_capabilities']=resolve(resolution,head,['PURE_CORE_STOCK'])['effective_blocked_runtime_capabilities']
    resolution_ref=write('config/v4_16_runtime_capability_resolution_v1.json',resolution)
    activation=json.loads((ROOT/old['activation']['path']).read_bytes())
    activation['predecessor']=old['activation'];activation['contract_id']='V4_16_RUNTIME_ACTIVATION_AUTHORITY_V4'
    activation['blocked_issue_ids']=activation.pop('blocked_capabilities');activation['capability_resolution']=resolution_ref
    activation_ref=write('config/v4_16_runtime_activation_authority_v4.json',activation)
    worker=json.loads((ROOT/'config/v4_16_settlement_worker_contract_v1.json').read_bytes())
    worker.update(contract_id='V4_16_SETTLEMENT_WORKER_RUNTIME_V2',version='2.0.0',runtime_implemented=True,
                  predecessor=binding('config/v4_16_settlement_worker_contract_v1.json'),runtime_authorized=False,
                  queue_migration=binding('migrations/v4_16_settlement_queue_v2.sql'),
                  dependency_contract_id='V4_16_RUNTIME_DEPENDENCIES_V5',input_contract=binding('config/v4_16_go_forward_input_authority_v1_1.json'),
                  future_authority='EXACT_R4R2_ACCEPTED_TARGET_SESSION_DAILY_BRIDGE_ONLY',
                  claim_lease='FENCED_VERSION_AND_BOUNDED_LEASE',current_audit_head=old['current_audit_head'])
    worker.update(entrypoint=binding('scripts/run_v4_16_settlement_v2.py'),
                  durable_due_outbox='IMMUTABLE_DUE_FACTS; NULL_DUE_SESSION_APPENDS_DUE_REVISION_AFTER_ACCEPTED_CALENDAR_EXTENSION',
                  source_bound_delivery_queue='settlement_queue_v2',same_day_readiness='WAIT_UNTIL_EXACT_ACCEPTED_FUTURE_SESSION_SOURCE',
                  acceptance='ENGINEERING_CANDIDATE_NOT_RUNTIME_OR_EXTERNAL_ACCEPTANCE')
    worker_ref=write('config/v4_16_settlement_worker_contract_v2.json',worker)
    packet=json.loads((ROOT/'config/v4_16_r25_packet_preflight_v2.json').read_bytes())
    packet.update(contract_id='V4_16_R25_PACKET_PREFLIGHT_V3',predecessor=old['packet_contract'],capability_resolution=resolution_ref,
                  blocked_issue_ids=sorted(ids),runtime_dependency_contract_id='V4_16_RUNTIME_DEPENDENCIES_V5')
    packet.pop('blocked_capabilities',None)
    packet_ref=write('config/v4_16_r25_packet_preflight_v3.json',packet)
    deps=copy.deepcopy(old);deps.update(contract_id='V4_16_RUNTIME_DEPENDENCIES_V5',version='5.0.0',predecessor=binding('config/v4_16_runtime_dependencies_v4.json'),
        activation=activation_ref,capability_resolution=resolution_ref,blocked_issue_ids=sorted(ids),settlement_worker=worker_ref,
        queue_migration=worker['queue_migration'],integrity_migration=binding('migrations/v4_16_real_shadow_integrity_v2.sql'),
        runtime_writer=binding('scripts/v4_16_go_forward_shadow_runtime_r4r3.py'),settlement_writer=binding('scripts/v4_16_settlement_worker_v2.py'),packet_contract=packet_ref)
    deps.pop('blocked_capabilities')
    deps['bindings']=[b for b in old['bindings'] if b!=old['activation']]
    deps['bindings'] += [activation_ref,resolution_ref,worker_ref,packet_ref,deps['queue_migration'],deps['integrity_migration'],deps['runtime_writer'],deps['settlement_writer'],worker['entrypoint'],binding('scripts/build_r25_packet_r4r3.py'),binding('scripts/v4_16_shadow_runtime.py'),binding('scripts/v4_16_capability_resolution.py'),binding('src/workbench_analysis/v4_15_settlement_successor.py')]
    # The one authorized existing entry-point change gets a fresh candidate binding.
    deps['bindings']=[binding(b['path']) if b['path']=='scripts/validate_r25_preflight.py' else b for b in deps['bindings']]
    write('config/v4_16_runtime_dependencies_v5.json',deps)
    write('config/v4_15_forward_benchmark_runtime_contract_v1_1.json',dict(contract_id='V4_15_FORWARD_BENCHMARK_RUNTIME_V1_1',
        predecessors=[binding('config/v4_15_forward_market_benchmark_contract_v1.json'),binding('config/v4_15_forward_sector_benchmark_contract_v1.json')],
        implementation=binding('src/workbench_analysis/v4_15_settlement_successor.py'),marked_permission=False,
        affine_policy='EXACT_ALPHA_BETA_FINITE_ALPHA_POSITIVE_ALL_ACTUAL_ROWS_AND_T0',historical_outputs='READ_ONLY',runtime_authorized=False))
    inventory=json.loads((ROOT/'config/v4_18_migration_replay_contract_v1_2.json').read_bytes())
    inventory.update(contract_id='V4_18_MIGRATION_REPLAY_CONTRACT_V1_3',supersedes=binding('config/v4_18_migration_replay_contract_v1_2.json'),
                     baseline=json.loads((ROOT/(PREFIX+'ENTRY_BASELINE.json')).read_bytes())['baseline_commit'])
    for path in ('src/workbench_db/migrations/v4_postgres/033_fep_signal_contract_integrity_v1.sql','migrations/v4_16_settlement_queue_v2.sql','migrations/v4_16_real_shadow_integrity_v2.sql'):
        for table in re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.]+)',(ROOT/path).read_text(encoding='utf8'),re.I):
            inventory['namespace_matrix'].append(dict(state_or_table=table,declaration=path,declaration_binding=binding(path),
                read_source='FEP_SIGNAL_CONTRACT_REGISTRY' if table.startswith('fep.') else 'SHADOW_V4',disposition='REFERENCE',write_target=None,
                immutable_source_identity='EXACT_VERSIONED_CONTRACT_AND_APPEND_ONLY_FACT_REFERENCES',
                target_identity_rule='PRESERVE_NATIVE_ID_AND_NAMESPACE',rollback='KEEP_IMMUTABLE_FACTS_AND_PENDING_OBLIGATIONS',
                production_cutover=False,migration_replay_pass='NOT_GRANTED'))
    write('config/v4_18_migration_replay_contract_v1_3.json',inventory)

if __name__=='__main__':build()
