"""Formalize independent infrastructure acceptance; authorize entry, never owners."""
import copy,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.formalize_source_authority_registry_r3 import protected_bindings,PERMISSIONS

AUDITED='699d3503d2d8ddbd37997441eec59308aec1990f'
AUDIT='V4_FIRST_BATCH_REGISTRY_R3_A10_R2_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md'
TASK='V4_A10_R2_ACCEPTANCE_FORMALIZATION_AND_A12_R2_ENTRY_TASK_20261001.md'
A12='V4_A12_R2_REAL_DATED_STATUS_ST_AUTHORITY_REPAIR_TASK_20261001.md'
DIR='docs/evidence/source_authority/'
ACCEPTED=['owner registry schema','governance trust root','exact owner hash verification',
    'external acceptance verification','formal consumer authorization verification','consumer scope verification',
    'historical mode verification','effective target scope verification','supplemental promotion guard','pending owner rejection','DM01/global gate consistency']
EXCLUDED=['no real source owner was authorized by A10-R2','existing formal owners have not been globally migrated',
    'A12 owner is not accepted','DM01 all-nine is not accepted','production/shadow/focus remain false']

def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def main():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==AUDITED
    for name in (AUDIT,TASK,A12):atomic_bytes(ROOT/DIR/name,(Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes())
    authority=dict(document=bind(DIR+AUDIT),audited_head=AUDITED)
    protected=protected_bindings()
    protected.extend(bind(p) for p in ['reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json',
        'data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json','data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R1.json'])
    atomic_json(ROOT/'reports/audits/R4_STAGE_ENTRY_R1.json',dict(contract_id='A10_R2_ACCEPTANCE_FORMALIZATION_AND_A12_R2_ENTRY_R1',
        task=bind(DIR+TASK),external_authority=authority,baseline_commit=AUDITED,protected_bindings=protected,
        permissions=PERMISSIONS,scope='FORMALIZATION_AND_ENTRY_ONLY_STOP_BEFORE_A12_IMPLEMENTATION',
        next_stage='Separately authorized A12 R2 main task; no owner promotion or DM01 execution'))
    r3='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R3.json'
    atomic_json(ROOT/'reports/audits/SOURCE_AUTHORITY_REGISTRY_R3_EXTERNAL_CONFIRMATION_R1.json',dict(
        contract_id='SOURCE_AUTHORITY_REGISTRY_R3_EXTERNAL_CONFIRMATION_R1',external_acceptance='PASS',
        external_authority=authority,registry=bind(r3),permissions=PERMISSIONS,
        evidence_bindings=[bind(p) for p in ['reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json',
            'reports/audits/V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json',
            'config/V4_01_HISTORICAL_IDENTITY_AUTHORITY_AMENDMENT_R1.json','reports/audits/R3_CLEAN_CHECKOUT_R1.json']]))
    a10='reports/audits/A10_R2_EXTERNAL_ACCEPTANCE_RECORD_R1.json'
    atomic_json(ROOT/a10,dict(contract_id='A10_R2_EXTERNAL_ACCEPTANCE_RECORD_R1',external_acceptance='PASS_INFRASTRUCTURE_SCOPE',
        scope='INFRASTRUCTURE_ONLY',formal_consumer_authorization=False,external_authority=authority,
        accepted=ACCEPTED,not_accepted=EXCLUDED,permissions=PERMISSIONS,
        evidence_bindings=[bind('reports/audits/A10_R2_'+suffix) for suffix in ['OWNER_GATE_AND_PENDING_SOURCE_EVIDENCE_R1.json',
            'CLEAN_CHECKOUT_R1.json','TARGETED_REGRESSION_R1.xml','NO_SYMBOL_SCAN_R1.json','STAGE_CLOSURE_R1.json']]))
    registry=copy.deepcopy(read(r3));registry.update(contract_id='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R4',
        extends=bind(r3),baseline_commit=AUDITED,external_authority=authority,authority=bind(DIR+TASK),
        status='A10_R2_EXTERNAL_ACCEPTANCE_FORMALIZED_A12_R2_IMPLEMENTATION_ENTRY_AUTHORIZED',
        OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS='DEFERRED_BEFORE_GLOBAL_MANDATORY_ADOPTION',
        global_mandatory_adoption_authorized=False,accepted_source_authority_owners=[])
    for entry in registry['entries']:
        wp=entry['work_package']
        if wp not in ['WP-A10-SOURCE-AUTHORITY-GOVERNANCE','WP-A12-V4-02-STATUS-ST-AUTHORITY','WP-A01-DM01']:continue
        previous=dict(status=entry['status'],implementation_status=entry['implementation_status'],external_acceptance=entry['external_acceptance'])
        if wp=='WP-A10-SOURCE-AUTHORITY-GOVERNANCE':
            entry.update(status='ACCEPTED_INFRASTRUCTURE_SCOPE',implementation_status='A10_R2_EXTERNAL_ACCEPTANCE_FORMALIZED',
                external_acceptance='PASS_INFRASTRUCTURE_SCOPE',formal_consumer_authorization=False,
                acceptance_scope='INFRASTRUCTURE_ONLY',accepted=ACCEPTED,not_accepted=EXCLUDED,
                status_path=a10,evidence=[bind(a10)],depends_on=[],next_step='Per-field/scoped owner bootstrap deferred; no global mandatory adoption')
        elif wp=='WP-A12-V4-02-STATUS-ST-AUTHORITY':
            entry.update(status='OPEN',implementation_status='A12_R2_IMPLEMENTATION_ENTRY_AUTHORIZED',external_acceptance='BLOCKED',
                formal_consumer_authorization=False,depends_on=[],task=bind(DIR+A12),
                next_step='A12 R2 main task separately; real source semantics and candidate only, no accepted owner registration')
        else:
            entry.update(status='OPEN',implementation_status='PARTIAL_ENGINEERING_PASS_FINAL_ALL_NINE_BLOCKED',
                external_acceptance='BLOCKED',formal_consumer_authorization=False,
                depends_on=['A12-R2_EXTERNAL_ACCEPTANCE','A12_ACCEPTED_OWNER_REGISTRATION'],
                next_step='A10 infrastructure prerequisite satisfied; wait for A12 external acceptance and owner registration')
        entry['transition']=dict(previous=previous,previous_status=previous['status'],new_status=entry['status'],
            acceptance_scope=entry.get('acceptance_scope','IMPLEMENTATION_ENTRY_ONLY_NO_OWNER_ACCEPTANCE'),
            capability_limitations=entry.get('not_accepted',entry.get('capability_limitations',[])),
            external_authority=authority,evidence_bindings=entry.get('evidence',[]),remaining_dependencies=entry['depends_on'])
    registry['entries'].append(dict(audit_id='OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS',
        work_package='WP-OWNER-REGISTRY-SCOPED-BOOTSTRAP',status='OPEN',
        implementation_status='DEFERRED_BEFORE_GLOBAL_MANDATORY_ADOPTION',external_acceptance=None,
        formal_consumer_authorization=False,scope=['OHLC/Amount/Volume','QFQ','Security Identity','Special Phase','Sector Membership'],
        evidence=[authority['document']],next_step='New per-field acceptance-scope task before global mandatory adoption or production/shadow',
        acceptance_independent_from_current_stage=True))
    registry['audit_count']=len(registry['entries']);registry['dependency_graph']={e['work_package']:e.get('depends_on',[]) for e in registry['entries']}
    atomic_json(ROOT/'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R4.json',registry)
    atomic_json(ROOT/'reports/audits/R4_ENGINEERING_GATES_R1.json',dict(status='PENDING_CLEAN_DETACHED',
        allowed_candidate_status='A10_R2_EXTERNAL_ACCEPTANCE_FORMALIZED_A12_R2_IMPLEMENTATION_ENTRY_AUTHORIZED',
        gates=dict(scope='PASS_ENGINEERING',owners_empty='PASS_ENGINEERING',historical_protection='PASS_ENGINEERING',clean='PENDING_CLEAN_DETACHED'),
        next_stage='STOP this entry card; separately execute supplied A12 R2 main task. DM01 and owner registration remain prohibited.'))
    print('A10 infrastructure acceptance formalized; R4 entry only; owners remain empty')

if __name__=='__main__':main()
