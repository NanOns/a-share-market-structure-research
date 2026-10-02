"""R10A governance registration only; runtime begins after exact readback PASS."""
import argparse
import subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT,atomic,bind,write,UPGRADE,PERMISSIONS
from scripts.record_r7_stage_contract import put

BASELINE='d99c242ff90180372df1055d5fff266a48f38102'
DOC='docs/evidence/next_round_v4_12_r10/'
OUT='reports/v4_12_runtime_r1/'
ACCEPTANCE='reports/v4_12/V4_12_CONTRACT_FREEZE_EXTERNAL_ACCEPTANCE_R1.json'
ENTRY='reports/v4_12/V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json'
NAMES=['V4_NEXT_ROUND_EXECUTION_MASTER_R10_20261002.md','V4_12_R10A_CONTRACT_FREEZE_PROMOTION_RUNTIME_ENTRY_TASK_20261002.md',
    'V4_12_R10B_D1_RUNTIME_ENGINE_IMPLEMENTATION_TASK_20261002.md','V4_R9_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md']
EVIDENCE=['reports/v4_12_r2/R8_AUTHORITY_REPAIR_HANDOFF.json','reports/v4_12_r2/V4_12_R2_PRODUCER_AUTHORITY_PARITY.json',
    'reports/v4_12_r2/V4_12_R2_COORDINATE_AUTHORITY_AUDIT.json','reports/v4_12_r2_1/R9_TIME_COUNTER_HANDOFF.json',
    'reports/v4_12_r2_1/V4_12_R2_1_TIME_COUNTER_SEMANTICS.json','reports/v4_12_r2_1/V4_12_R2_1_TIME_DOMAIN_COMPATIBILITY_AUDIT.json']

def prepare(bundle):
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASELINE
    for name in NAMES:atomic(DOC+name,(Path(bundle)/name).read_bytes())
    for path in [DOC,OUT]:atomic(path+'.gitattributes',b'* -text\n')
    from scripts.validate_v4_12_time_counter_r2_1 import validate
    prior=validate();assert prior['status']=='V4_12_R2_1_TIME_COUNTER_SEMANTICS_CANDIDATE_READY_FOR_EXTERNAL_AUDIT'
    contracts=[bind(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'config').glob('v4_12_*.json'))]
    frozen=dict(contract_id='V4_12_CONTRACT_FREEZE_EXTERNAL_ACCEPTANCE_R1',status='EXTERNAL_PASS',external_audit_status='PASS_V4_12_CONTRACT_FREEZE',
        external_authority=bind(DOC+NAMES[3]),master=bind(DOC+NAMES[0]),task=bind(DOC+NAMES[1]),upgrade=bind(UPGRADE),
        tested_source_sha='11d8015d608670572bd57fc50fb6327e2b693a73',audited_remote_head=BASELINE,
        accepted_parent=bind('data/v4/V4_11_ACCEPTED_HEAD.json'),stage_entry=bind('reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json'),
        evidence=[bind(p) for p in EVIDENCE],frozen_contracts=contracts,stage_accepted=False,**PERMISSIONS)
    write(ACCEPTANCE,frozen)
    fields=__import__('json').loads((ROOT/'config/v4_12_field_registry_v1.json').read_bytes())['fields']
    entry=dict(contract_id='V4_12_RUNTIME_ENGINEERING_ENTRY_R1',status='V4_12_RUNTIME_ENGINEERING_ENTRY_R1_READY',scope='V4_12_D1_ENGINEERING_RUNTIME_R1',
        contract_freeze_acceptance=bind(ACCEPTANCE),frozen_contracts=contracts,task=bind(DOC+NAMES[2]),scoped_engineering_implementation_permission=True,
        allowed_namespaces=['F0[t]','Frozen D1[t-1]','frozen calendar','frozen contract/parameter'],
        forbidden_namespaces=['D2','Final State','state_events','Radar','Focus','UI','Forward outcomes','Validation Cohort'],
        blocked_fields=[dict(field=r['field'],reason=r['blocked_reason'],producer=r['producer_contract_id']) for r in fields if r['field_role'] in ['BLOCKED_CAPABILITY','FROZEN_PRIOR_D1']],
        capability_inheritance='R2/R2.1 exact; no raw fallback, provider replacement, candidate substitute or local recompute grants authority',
        stage_head=bind('data/v4/V4_STAGE_ACCEPTED_HEAD.json'),data_head=bind('data/v4/V4_DATA_ACCEPTED_HEAD.json'),
        stage_accepted=False,formal_V4_12_head_permission=False,DB_migration_permission=False,D2_integration_permission=False,V4_13_permission=False,**PERMISSIONS)
    write(ENTRY,entry)
    put(OUT+'R10_STAGE_CONTRACT.json',dict(starting_remote_head=BASELINE,master=bind(DOC+NAMES[0]),authority=bind(DOC+NAMES[3]),
        tasks=[bind(DOC+n) for n in NAMES[1:3]],upgrade=bind(UPGRADE),consulted_sections=['10J','10K','10L','13A','41A0','41A','41B','41C','41D','72','78','87A'],
        phase0=dict(status='DEGRADED_PASS',scope='SCOPED_REPLAY_NO_SCANNER_NO_TDX_WRITES'),stage_contract='R10A_READBACK_THEN_R10B',
        acceptance='R10A exact governance readback required; R10B external audit pending',next_stage='UNIFIED_COMMIT_PUSH_STOP',permissions=PERMISSIONS))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle-dir',required=True);prepare(p.parse_args().bundle_dir)
