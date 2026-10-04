"""Additive atomic R31 contract/evidence builder. Historical files stay frozen."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '791543c3bdbd4b80b2679b447d257cc27dd504ad'
CONTRACT = 'config/v4_22_independent_audit_contract_v1.json'
UPGRADE = 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
AUTHORITY = 'docs/evidence/r31/V4_R30R1_V4_21_NATIVE_SESSION_REPAIR_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'
CAPS = ['STOCK_CORE', 'STOCK_SECTOR_DEPENDENT', 'SECTOR_STAGE', 'ROTATION', 'SECTOR_RISK_CHANGE']
TAG = 'codex/r31-independent-audit-contract-tested-source-20261004'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(name, value):
    assert name == CONTRACT or name.startswith(('reports/r31/', 'docs/evidence/r31/'))
    target = ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode('utf8')
    # Source documents are copied byte-for-byte. Generated text uses LF.
    staging = target.with_name(target.name + '.r31-staging')
    with staging.open('wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(staging, target)


def binding(name):
    p = ROOT / name
    b = dict(path=name, sha256=sha(p), bytes=p.stat().st_size)
    if p.suffix == '.json':
        identity = json.loads(p.read_bytes()).get('contract_id')
        if identity:
            b['contract_id'] = identity
    return b


DOMAIN_CHECKS = {
    'DATA': ['accepted Data Head', 'calendar/trade-date correctness', 'PIT source identity', 'Raw/Adjusted integrity', 'Universe/membership basis', 'capability-scoped degraded sources', 'no silent latest/mtime discovery'],
    'ALGORITHM': ['accepted algorithm contracts', 'field registry/producer/time semantics', 'AST/parameter identity where required', 'deterministic replay', 'no same-day feedback', 'no duplicate episode', 'revision idempotency', 'capability dependency graph'],
    'PUBLICATION': ['clock authority', 'source readiness', 'Observation Slot V2', 'exact daily-input authority', 'Shadow publication identity', 'state lineage', 'accepted session status/native authority', 'same-day revision', 'CAS'],
    'SHADOW': ['exact SHADOW_STABLE_PASS receipts', 'real PIT sessions only', 'model/parameter partition', '20 consecutive accepted-session semantics', 'no historical replay sample inflation', 'complete slot denominator/P0 log', 'accepted rollback drill'],
    'UI': ['V4-17 read-only Shadow UI engineering', 'same context token', 'no fallback', 'NO_REAL_SHADOW_DATA behavior', 'mixed Legacy/V4/Shadow module identity', 'Focus write permission', 'default UI source resolution', 'deep-link immutability', 'cache/session invalidation', 'V4-17 final real-publication acceptance'],
    'FORWARD': ['evidence lanes', 'native session authority', 'accepted-session denominator', 'event/cohort ledger', 'due/outcome ledger', 'right censor', 'model/parameter partitions', 'Shadow/Production continuity', 'gate readback ownership', 'complete Validation Cohort', 'controls/benchmarks', 'observed vs corrected revisions', 'exact FORWARD_GATE receipts', 'no new settlement owner'],
    'MIGRATION': ['prestate inheritance', 'open episode preservation', 'pending settlement ownership', 'user pin/manual work preservation', 'namespace mapping', 'cutover gap', 'idempotent replay', 'accepted migration rollback'],
    'CUTOVER': ['SHADOW_STABLE_PASS per capability', 'FORWARD_GATE per capability', 'MIGRATION_REPLAY_PASS per capability', 'required dependency permissions', 'production_permission receipt equality', 'Focus source route', 'default UI route', 'no GLOBAL V4 PASS'],
    'ROLLBACK': ['capability-scoped rollback', 'route CAS', 'accepted history preservation', 'pending settlement preservation', 'user pin/manual work preservation', 'Shadow/Production evidence retention', 'Legacy recovery path', 'cutover-gap reconciliation'],
    'GOVERNANCE': ['exact audited branch', 'exact tested source commit', 'immutable annotated tag', 'clean checkout proof', 'evidence-only post-test delta', 'open-item explicit disposition', 'independent oracle import isolation', 'FEP acceptance separately scoped'],
    'REGRESSION': ['complete inherited regression scope/no deselection', 'no new errors/skips/failures', 'R26-A01 separate historical debt', 'protected bytes and unrelated changes'],
}
OWNER_PATHS = {
    'DATA': ['data/v4/V4_DATA_ACCEPTED_HEAD.json', 'data/v4/V4_STAGE_ACCEPTED_HEAD.json'],
    'ALGORITHM': ['data/v4/V4_14_ACCEPTED_HEAD.json', 'data/v4/V4_15_ACCEPTED_HEAD.json'],
    'PUBLICATION': ['config/v4_16_clock_contract_v1.json', 'config/v4_16_observation_slot_contract_v2.json', 'config/v4_16_go_forward_input_authority_v1.json', 'reports/r25/DAILY_INPUT_REAL_GATE.json'],
    'SHADOW': ['config/v4_16_shadow_health_contract_v1.json', 'config/v4_19_focus_source_cutover_contract_v1.json'],
    'UI': ['config/v4_17_shadow_ui_contract_v1.json', 'config/v4_20_default_ui_cutover_contract_v1.json'],
    'FORWARD': ['config/v4_21_continued_forward_observation_contract_v1.json', 'config/v4_15_cohort_contract_v1.json', 'config/v4_15_due_planner_contract_v1.json', 'config/v4_15_outcome_status_contract_v1.json', 'config/v4_15_settlement_revision_contract_v1.json'],
    'MIGRATION': ['config/v4_18_migration_replay_contract_v1.json'],
    'CUTOVER': ['config/v4_19_focus_source_cutover_contract_v1.json', 'config/v4_20_default_ui_cutover_contract_v1.json'],
    'ROLLBACK': ['config/v4_18_migration_replay_contract_v1.json', 'config/v4_19_focus_source_cutover_contract_v1.json', 'config/v4_20_default_ui_cutover_contract_v1.json'],
    'GOVERNANCE': [AUTHORITY, UPGRADE],
    'REGRESSION': ['reports/r30r1/CLEAN_REGRESSION.json'],
}


def snapshot():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == BASE
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf8').split('\0')
    others = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode('utf8').split('\0')
    new = lambda n: n == CONTRACT or n.startswith(('reports/r31/', 'docs/evidence/r31/')) or n == 'tests/test_v4_22_independent_audit_contract.py'
    write('reports/r31/PROTECTED_BASELINE.json', dict(baseline=BASE, tracked={n:sha(ROOT/n) for n in tracked if n and (ROOT/n).is_file()}, unrelated={n:sha(ROOT/n) for n in others if n and not new(n)}))


def build():
    documents = []
    for name in ('V4_NEXT_ROUND_EXECUTION_MASTER_R31_20261004.md', 'V4_22_R31_INDEPENDENT_AUDIT_CONTRACT_DESIGN_TASK_20261004.md', 'V4_R30R1_V4_21_NATIVE_SESSION_REPAIR_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'):
        source = Path('D:/Users/lps/Desktop/阶段任务') / name
        target = 'docs/evidence/r31/' + name
        write(target, source.read_bytes())
        documents.append(dict(source=str(source), copy=target, sha256=sha(source)))
    write('reports/r31/STAGE_CONTRACT.json', dict(stage='V4-22/R31', mode='CONTRACT_DESIGN_ONLY', baseline=BASE, documents=documents, upgrade=binding(UPGRADE), upgrade_sections=['51A', '52A', '52B', '78/V4-22', '81.4'], allowed=[CONTRACT, 'reports/r31/*', 'docs/evidence/r31/*', 'tests/test_v4_22_independent_audit_contract.py'], acceptance='PENDING_LOCAL_CONTRACT_VALIDATION', next='STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT', temporary_root='F:/codex_tmp', business_writers_forbidden=True))
    authority = binding(AUTHORITY)
    current = json.loads((ROOT/'config/v4_21_continued_forward_observation_contract_v1.json').read_bytes())['current_state']
    assert current['REAL_SHADOW_OBSERVATIONS'] == 0 and current['R25'] == 'WAIT_ACCEPTED_DAILY_INPUT'
    slot = binding('config/v4_16_observation_slot_contract_v2.json')
    slot['accepted_statuses'] = ['ACCEPTED_ON_TIME']
    items = []
    domains = []
    for domain, checks in DOMAIN_CHECKS.items():
        owner = [binding(n) for n in OWNER_PATHS[domain]]
        domains.append(dict(domain='A22-'+domain, capability_scope=CAPS, authority_bindings=owner, optional=False, required_evidence_classes=['EXACT_ACCEPTED_AUTHORITY', 'INDEPENDENT_RAW_READBACK', 'INDEPENDENT_RECHECK']))
        for index, check in enumerate(checks, 1):
            historical = domain in ('DATA', 'ALGORITHM')
            status = 'NOT_VERIFIABLE' if historical or domain in ('GOVERNANCE', 'REGRESSION') or (domain=='UI' and index<10) else 'WAIT_REAL_EVIDENCE'
            items.append(dict(item_id=f'A22-{domain}-{index:02}', domain='A22-'+domain, check=check, capability_scope=CAPS, required_evidence=['EXACT_ACCEPTED_AUTHORITY', 'INDEPENDENT_RAW_READBACK', 'INDEPENDENT_RECHECK'] + ([] if historical or domain in ('GOVERNANCE','REGRESSION') or (domain=='UI' and index<10) else ['REAL_PIT_RUNTIME_RECEIPT']), authority=owner, current_status=status, blocking_scope=CAPS, disposition_rule='PASS_ONLY_AFTER_EXACT_SCOPED_INDEPENDENT_AUDIT; CONTRACT_DESIGN_OR_PRIOR_STAGE_ACCEPTANCE_IS_NOT_THIS_AUDIT', evidence_refs=owner, audit_execution='NOT_RUN_R31_CONTRACT_DESIGN_ONLY', accepted_fact_scope='HISTORICAL_ACCEPTED_HEAD_ONLY' if historical else 'ENGINEERING_DESIGN_ONLY' if domain=='UI' and index<10 else 'FUTURE_RUNTIME_AUDIT'))
    open_specs = [
        ('PUBLICATION','R25 WAIT_ACCEPTED_DAILY_INPUT','WAIT_REAL_EVIDENCE',CAPS),
        ('SHADOW','REAL_SHADOW_OBSERVATIONS = 0','WAIT_REAL_EVIDENCE',CAPS),
        ('UI','V4_17_FINAL_ACCEPTANCE = NOT_GRANTED','BLOCKED',CAPS),
        ('SHADOW','V4_17G = NOT_GRANTED','WAIT_REAL_EVIDENCE',CAPS),
        ('MIGRATION','MIGRATION_REPLAY_PASS = NOT_GRANTED','WAIT_REAL_EVIDENCE',CAPS),
        ('CUTOVER','production_permission[*] = false','BLOCKED',CAPS),
        ('CUTOVER','DEFAULT_UI_CUTOVER = false','BLOCKED',CAPS),
        ('FORWARD','REAL_CONTINUED_FORWARD_OBSERVATION = NOT_STARTED','WAIT_REAL_EVIDENCE',CAPS),
        ('REGRESSION','R26_A01 historical V3 regression debt (3 inherited failures)','OPEN_NONBLOCKING_DEBT',[]),
        ('FORWARD','R30R1_P2_LEDGER_REFERENTIAL_INTEGRITY_VECTOR','OPEN_NONBLOCKING_DEBT',[]),
    ]
    opens = [dict(item_id=f'OPEN-{i:02}', domain='A22-'+domain, capability_scope=CAPS if i!=9 else ['LEGACY_V3'], required_evidence=['EXPLICIT_DISPOSITION','EXACT_EVIDENCE','AUTHORITY','DATE_SOURCE','INDEPENDENT_RECHECK'], authority=authority, current_status=status, blocking_scope=blockers, description=description, disposition_rule='NO_AUTO_CLOSE; SEPARATE_SCOPE_AND_INDEPENDENT_ACCEPTANCE; OPEN-10_DISPOSITION_REQUIRED_BEFORE_FINAL_PROJECT_ACCEPTANCE' if i==10 else 'NO_AUTO_CLOSE; EXACT_AUTHORITY_AND_INDEPENDENT_RECHECK_REQUIRED', evidence_refs=[authority]+[binding(n) for n in OWNER_PATHS[domain]], current_disposition='OPEN; DESIGN_VECTOR_COVERAGE_IS_NOT_EXTERNAL_CLOSURE' if i==10 else 'CARRIED_UNCHANGED', date_source='2026-10-04/R30R1_EXTERNAL_AUDIT') for i,(domain,description,status,blockers) in enumerate(open_specs,1)]
    # Preserve the entire cross-stage audit owner registry including Amount A.
    cross = binding('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json')
    c = dict(contract_id='V4_22_INDEPENDENT_AUDIT_CONTRACT_V1', version='1.0.0', baseline=BASE, mode='CONTRACT_DESIGN_ONLY', status='LOCAL_CONTRACT_CANDIDATE_NOT_EXTERNAL_ACCEPTANCE', capabilities=CAPS, status_vocabulary=['PASS','FAIL','BLOCKED','NOT_VERIFIABLE','NOT_APPLICABLE','OPEN_NONBLOCKING_DEBT','WAIT_REAL_EVIDENCE'], status_semantics={'PASS':'EXACT_SCOPED_EVIDENCE_INDEPENDENTLY_RECHECKED','FAIL':'OBSERVED_CONTRACT_VIOLATION','BLOCKED':'EXPLICIT_PREREQUISITE_OR_AUTHORITY_BLOCKER','NOT_VERIFIABLE':'REQUIRED_CHECK_NOT_EXECUTED_OR_UNREADABLE_EVIDENCE','NOT_APPLICABLE':'EXPLICIT_AUTHORITY_JUSTIFIED_SCOPE_EXCLUSION_ONLY','OPEN_NONBLOCKING_DEBT':'SEPARATE_AUDIT_ITEM_WITH_NONBLOCKING_AUTHORITY; NEVER_PASS','WAIT_REAL_EVIDENCE':'NO_ACCEPTED_REAL_PIT_RUNTIME_RECEIPT_YET'}, item_required_fields=['item_id','domain','capability_scope','required_evidence','authority','current_status','blocking_scope','disposition_rule','evidence_refs'], audit_domains=domains, audit_items=items, open_items=opens, cross_stage_carry=dict(binding=cross, rule='PRESERVE_ALL_EXISTING_OPEN_ITEMS_AND_ACCEPTANCE_SCOPE; NO_CLOSURE_BY_R31', optional_FEP='SEPARATE_DOMAIN_AND_REGISTRY; NEVER_INHERIT_CORE_ACCEPTANCE; NO_READ_OR_WRITE_OF_UNRELATED_FEP_WORK'), evidence_classes=['EXACT_ACCEPTED_AUTHORITY','INDEPENDENT_RAW_READBACK','REAL_PIT_RUNTIME_RECEIPT','CONTRACT_DESIGN_SIMULATION','HISTORICAL_REPLAY','RECONSTRUCTED_ASOF','INDEPENDENT_RECHECK','EXACT_TESTED_SOURCE_PROOF'], authority_bindings={d['domain']:d['authority_bindings'] for d in domains}, shadow_session_owner=slot, production_session_owner=None, referential_integrity=dict(vectors=['A22-V421-REFINT-01','A22-V421-REFINT-02'], partition=list(('capability','evidence_lane','model_contract_id','parameter_digest','state_lineage_id')), orphan_result='BLOCKED_AFFECTED_SCOPE', accepted_native_parent='EXACT_ACCEPTED_AUTHORITY_AND_NATIVE_ACCEPTED_STATUS; PROJECTION_EVALUABLE_IS_SEPARATE', effect='INDEPENDENT_AUDIT_ONLY; NO_V4_21_BUSINESS_SEMANTICS_CHANGE'), independent_oracle=dict(path='reports/r31/audit_oracle.py', allowed_imports=['hashlib','json','pathlib'], forbidden_imports=['business writer','migration writer','cutover writer','production route writer','reports.r30.design_ledger','reports.r30r1.session_authority'], rules=['exact raw file readback','independent SHA256 and canonical digest','independent relation checks','exact authority path verification','no writes/grants/settlement calculations']), required_real_gates=['SHADOW_STABLE_PASS','FORWARD_GATE','MIGRATION_REPLAY_PASS','required_dependency_permissions','production_permission'], runtime_receipt_bindings={}, runtime_binding_rule='FUTURE_EXACT_EXTERNALLY_ACCEPTED_PER_CAPABILITY_OWNER_RECEIPTS_REQUIRED; EMPTY_NOW; NEVER_RECOMPUTE_OR_GRANT_REAL_GATES', final_verdict_formula=dict(all_required_blocking_items='PASS_WITH_EXACT_SCOPE_EVIDENCE_AND_INDEPENDENT_RECHECK', real_gates='EXACT_BOUND_EXTERNALLY_ACCEPTED_RECEIPTS_PER_CAPABILITY', unresolved_P0_P1='NONE', permissions='MATCH_EXACT_RECEIPTS_AND_DEPENDENCIES', governance='EXACT_BRANCH_TESTED_SOURCE_IMMUTABLE_ANNOTATED_TAG_CLEAN_CHECKOUT_EVIDENCE_ONLY_DELTA', open_item_rule='NO_AUTO_CLOSE; OPEN-10_EXPLICIT_DISPOSITION_REQUIRED_BEFORE_FINAL_ACCEPTANCE', allowed_nonfinal=['FINAL_AUDIT_NOT_READY','FINAL_AUDIT_BLOCKED','CAPABILITY_SCOPED_ACCEPTANCE'], no_global_partial_pass=True), tested_source_governance=dict(branch='codex/v4-system-reform', annotated_tag=TAG, clean_checkout_required=True, allowed_post_test_delta_prefixes=['reports/r31/','docs/evidence/r31/'], allowed_post_test_delta_suffixes=['.json','.xml','.txt','.md'], forbid_post_test_implementation_drift=True), current_state=current, implementation_entry='BLOCKED_WAIT_REAL_GATES', final_pass='NOT_GRANTED', V4_22_ACCEPTED_HEAD='NOT_CREATED', next_stage='STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT', protected_state=dict(stage_head=binding('data/v4/V4_STAGE_ACCEPTED_HEAD.json'), data_head=binding('data/v4/V4_DATA_ACCEPTED_HEAD.json'), radar_head=binding('data/v4/V4_15_ACCEPTED_HEAD.json'), accepted_head_absence=['data/v4/V4_'+str(i)+'_ACCEPTED_HEAD.json' for i in range(16,23)], no_business_writes=True, no_settlement_owner_change=True, no_Focus_UI_route_changes=True, no_real_counter_changes=True))
    c['audit_receipt_bindings'] = {}
    c['audit_receipt_binding_rule'] = 'FUTURE_EXACT_INDEPENDENT_AUDIT_RECEIPTS_BOUND_BY_ITEM_ID_AND_CANONICAL_SHA256; NO_SELF_ASSERTED_PASS'
    # OPEN-10 is nonblocking for contract design, but disposition is a final audit prerequisite.
    c['audit_items'].append(dict(item_id='A22-GOVERNANCE-OPEN10', domain='A22-GOVERNANCE', check='OPEN-10 explicit independent disposition before final acceptance', capability_scope=CAPS, required_evidence=['EXPLICIT_DISPOSITION','EXACT_EVIDENCE','INDEPENDENT_RECHECK'], authority=[authority], current_status='NOT_VERIFIABLE', blocking_scope=CAPS, disposition_rule='DESIGN_VECTORS_DO_NOT_CLOSE_EXTERNAL_ITEM', evidence_refs=[authority]))
    write(CONTRACT,c)
    write('reports/r31/AUDIT_DOMAIN_REGISTRY.json',dict(contract=binding(CONTRACT),domains=domains))
    write('reports/r31/OPEN_ITEM_REGISTRY.json',dict(items=opens,cross_stage_registry=cross,cross_stage_entries=json.loads((ROOT/cross['path']).read_bytes())['entries'],cross_stage_disposition='EXACT_CARRY_NO_MODIFICATION',FEP='OPTIONAL_SEPARATE_ACCEPTANCE_NOT_INHERITED'))
    matrix_names={'DATA_AUDIT_MATRIX':['DATA'],'ALGORITHM_AUDIT_MATRIX':['ALGORITHM'],'PUBLICATION_SHADOW_AUDIT_MATRIX':['PUBLICATION','SHADOW'],'UI_AUDIT_MATRIX':['UI'],'FORWARD_AUDIT_MATRIX':['FORWARD'],'MIGRATION_CUTOVER_AUDIT_MATRIX':['MIGRATION','CUTOVER'],'ROLLBACK_AUDIT_MATRIX':['ROLLBACK']}
    for name, domain_ids in matrix_names.items():
        write('reports/r31/'+name+'.json',dict(mode='CONTRACT_DESIGN_ONLY',items=[x for x in items if x['domain'][4:] in domain_ids],runtime_audit_executed=False))
    write('reports/r31/FINAL_VERDICT_FORMULA.json',dict(formula=c['final_verdict_formula'],runtime_receipt_bindings={},evaluated_current='FINAL_AUDIT_NOT_READY',V4_22_FINAL_PASS='NOT_GRANTED'))
    write('reports/r31/CURRENT_AUDIT_STATE.json',dict(state=current,external_predecessor='PASS_FINAL_NATIVE_SESSION_STATUS_AND_OWNER_BINDING_REPAIR',V4_21_CONTRACT_DESIGN='EXTERNALLY_ACCEPTED_SCOPED',V4_22_FINAL_AUDIT_ENTRY='BLOCKED_WAIT_REAL_GATES',V4_22_FINAL_PASS='NOT_GRANTED',V4_22_ACCEPTED_HEAD='NOT_CREATED',current_audit_verdict='FINAL_AUDIT_NOT_READY',next='STOP_WAIT_R31_INDEPENDENT_EXTERNAL_AUDIT'))


if __name__ == '__main__':
    import sys
    if '--snapshot' in sys.argv:
        snapshot()
    build()
