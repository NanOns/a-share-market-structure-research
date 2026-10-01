"""Record A13 candidate disposition while preserving independent audit openness."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
P='reports/audits/A13_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
    receipt=read(P+'NOTICE_REMOVAL_ADMISSION_COUNTERFACTUAL_R1.json')
    assert receipt['status']=='PASS_NO_BUSINESS_IMPACT_CANDIDATE' and not receipt['BUSINESS_REBUILD_REQUIRED']
    ledger=copy.deepcopy(read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R6.json'))
    ledger.update(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R7',
        extends=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R6.json'),
        authority=bind('docs/evidence/source_authority/V4_A13_OFFICIAL_NOTICE_EVENT_SEMANTICS_RETROSPECTIVE_TASK_R1_20261001.md'))
    bindings=[bind(P+'FULL_NOTICE_AND_CAPTURE_MANIFEST_INVENTORY_R1.json'),
        bind(P+'CONSUMER_INVENTORY_R1.json'),bind(P+'NOTICE_REMOVAL_ADMISSION_COUNTERFACTUAL_R1.json'),
        bind('data/v4/source_evidence/a13/OFFICIAL_NOTICE_EVENT_SEMANTICS_AMENDMENT_R1.json')]
    item=next(e for e in ledger['entries'] if e.get('audit_id')=='OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS')
    item.update(status='OPEN',implementation_status='A13_SEMANTICS_CANDIDATE_PENDING_EXTERNAL_REAUDIT',
        implementation_work_package='WP-A13-OFFICIAL-NOTICE-EVENT-SEMANTICS',external_acceptance='PENDING',
        formal_consumer_authorization=False,evidence=item['evidence']+bindings,
        next_step='Independent A13 external acceptance; default business heads KEEP; semantic candidate grants no trading truth')
    atomic_json(ROOT/'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R7.json',ledger)
    atomic_json(ROOT/(P+'ENGINEERING_GATES_R1.json'),dict(
        allowed_candidate_status='A13_OFFICIAL_NOTICE_EVENT_SEMANTICS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
        gates={'FULL_NOTICE_INVENTORY':'PASS_ENGINEERING','UNCHANGED_ADMISSION_COUNTERFACTUAL':'PASS_ENGINEERING',
            'FULL_DOWNSTREAM_BUSINESS_DIGEST':'PASS_ENGINEERING','RUNTIME_SEMANTIC_NEGATIVES':'PENDING_CLEAN_DETACHED',
            'EXTERNAL_NOTICE_ACCEPTANCE':'PENDING_INDEPENDENT_EXTERNAL_AUDIT'},
        evidence_bindings=bindings,next_stage='Independent A13 external reaudit; audit remains OPEN; no business head movement'))
    print('A13 evidence candidate recorded; audit OPEN')
if __name__=='__main__':main()
