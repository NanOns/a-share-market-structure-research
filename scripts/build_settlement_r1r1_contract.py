"""Refresh only the P0-02 candidate's exact V5 bindings."""
import json
from scripts.full_chain_repair_io import ROOT,write,binding

def build():
    contract=write('config/v4_16_settlement_restart_idempotency_v1.json',dict(
        contract_id='V4_16_SETTLEMENT_RESTART_IDEMPOTENCY_V1',version='1.0.0',
        scope='P0_02_R1R1_ONLY',baseline_commit='efe2d0c5f2b0d94878929120521fa48982e3cf56',
        activation_selection='EXACT_SINGLETON_ACTIVATION_HEAD_THEN_EXACT_FACT_ID_IN_READ_TRANSACTION',
        queue_retry='TRANSACTIONAL_EXACT_PK_DUE_KIND_DUE_ID_AND_RECOMPUTED_FROZEN_IDENTITY_READBACK',
        conflict='QUEUE_IDEMPOTENCY_CONFLICT',migrations_added=False,
        runtime_dependency_contract_id='V4_16_RUNTIME_DEPENDENCIES_V5',
        implementations=[binding(p) for p in ('scripts/v4_16_go_forward_shadow_runtime_r4r3.py','scripts/v4_16_settlement_worker_v2.py')],
        runtime_authorized=False,production=False,external_acceptance=False))
    worker=json.loads((ROOT/'config/v4_16_settlement_worker_contract_v2.json').read_bytes())
    worker['restart_idempotency_contract']=contract
    worker_ref=write('config/v4_16_settlement_worker_contract_v2.json',worker)
    deps=json.loads((ROOT/'config/v4_16_runtime_dependencies_v5.json').read_bytes())
    paths={'scripts/v4_16_go_forward_shadow_runtime_r4r3.py','scripts/v4_16_settlement_worker_v2.py','config/v4_16_settlement_worker_contract_v2.json'}
    deps['bindings']=[binding(b['path']) if b['path'] in paths else b for b in deps['bindings'] if b['path']!=contract['path']]
    deps['bindings'].append(contract)
    deps.update(runtime_writer=binding('scripts/v4_16_go_forward_shadow_runtime_r4r3.py'),settlement_writer=binding('scripts/v4_16_settlement_worker_v2.py'),settlement_worker=worker_ref)
    write('config/v4_16_runtime_dependencies_v5.json',deps)

if __name__=='__main__':build()
