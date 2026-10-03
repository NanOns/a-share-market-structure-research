"""Moving-head governance only; no Accepted Head rewriting."""
from scripts.r20_io import *
STAGE='data/v4/V4_STAGE_ACCEPTED_HEAD.json'
def repair():
    original=subprocess.check_output(['git','show',BASE+':'+STAGE],cwd=ROOT)
    if (ROOT/STAGE).read_bytes()!=original:raise ValueError('EXACT_R20_BASELINE_STAGE_REQUIRED')
    atomic('reports/r20a/PARENT_STAGE_HEAD.json',original,raw=True)
    stage=json.loads(original)
    stage.update(v4_14_entry='COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_REPLAY_GATE_B',v4_15_entry='CONTRACT_FREEZE_EXTERNALLY_ACCEPTED_RUNTIME_ENGINEERING_AUTHORIZED_AFTER_R20A')
    atomic(STAGE,stage)
    data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    contract=dict(contract_id='V4_CURRENT_STAGE_AUTHORITY_V1',version='1.0.0',input_commit=BASE,stage_namespace=STAGE,accepted_stage_range='V4_00_TO_V4_14_ACCEPTED',current_head=stage['v4_14_binding'],immutable_owner_heads={k:stage[k+'_binding'] for k in ['v4_07','v4_08','v4_09','v4_10','v4_11','v4_12','v4_13','v4_14']},data_head=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json'),calendar=data['calendar'],identity=data['identity'],membership=ref('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json'),v4_15_contract_package=ref('config/v4_15_contract_package_v1.json'),external_audit=ref('docs/evidence/r20/V4_R19_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md'),parent_stage=ref('reports/r20a/PARENT_STAGE_HEAD.json'),production=False,shadow=False,focus=False,V4_15_accepted=False,V4_16=False,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',reader='CURRENT_V4_14_ROOT_WITH_EXPLICIT_DEPENDENCY_INJECTION',historical_reader='EXPLICIT_ARCHIVED_HISTORICAL_CONTEXT_ONLY',portability='LITERAL_EXACT_DEFAULT_OR_EXPLICIT_R20B_PORTABLE_READER_INJECTION_NO_HIDDEN_NORMALIZATION')
    atomic('config/v4_current_stage_authority_v1.json',contract)
if __name__=='__main__':repair()
