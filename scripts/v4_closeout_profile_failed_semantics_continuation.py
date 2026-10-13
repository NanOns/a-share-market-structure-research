"""Continue precisely the 18 original failed clauses; no accepted output rewrite."""
import json
from pathlib import Path
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_04_machine_executor_v4 import execute_rule,CONTRACT_ID
from v4.profile_core import extension_risk
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    target=OUT/'PROFILE_FAILED_SEMANTICS_CONTINUATION_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_FAILED_SEMANTICS_CONTINUATION')
    original=json.loads((OUT/'PROFILE_UNKNOWN_GUARD_DISCREPANCY_R6_R1.json').read_bytes())
    contract=json.loads(checked(ROOT,original['contract']).read_bytes())
    p={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}
    checks=[];corrections=[]
    for item in original['affected']:
        key='COMPRESSION_STATE_V1' if item['field']=='compression_state' else 'EXTENSION_RISK_V1'
        expected=execute_rule(contract['rules'],key,item['evidence'],p)
        actual=item['actual'] if item['field']=='compression_state' else extension_risk(item['evidence']).value
        checks.append(dict(security_id=item['security_id'],field=item['field'],expected=expected,new_actual=actual,passed=actual==expected))
        if actual!=item['actual']:corrections.append(dict(security_id=item['security_id'],field=item['field'],old=item['actual'],new=actual,severe_extension_old=None,severe_extension_new=actual=='EXTREME'))
    if len(checks)!=18 or len(corrections)!=6:raise ValueError('FAILED_SEMANTIC_SCOPE_CHANGED')
    repo=Path(__file__).resolve().parents[1]
    result=dict(contract_id='V4_PROFILE_FAILED_SEMANTICS_BOUNDED_CONTINUATION_R1',acceptance='PASS_CORRECTION_PROPOSAL_ONLY' if all(c['passed'] for c in checks) else 'FAIL',candidate=original['candidate'],T0=original['T0'],checks=checks,corrections=corrections,previous_pass_reexecuted=0,sealed_outputs_changed=False,native_pg_changed=False,publication_ready=False,independent_machine_contract=CONTRACT_ID,source=ref(repo,repo/'src/v4/profile_core.py'),verifier=ref(repo,repo/'scripts/v4_04_machine_executor_v4.py'),design=ref(ROOT,ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md'),scope='12 original verifier guard failures resolved; 6 actual extension outputs require versioned bounded Profile/consumer correction before release. Existing sealed candidate retains its original producing Source identity.')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=len(checks),corrections=len(corrections))))

if __name__=='__main__':main()
