"""Seal the repair candidate only after the clean detached engineering gates pass."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.promote_v4_09_accepted_head import bind,validate

BASELINE='14db3ef521d34b366bf5a22bad2a3564838ce8bf'
STATUS='V4_10_R1_1_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT'
PREFIX='reports/v4_10/V4_10_R1_1_'
EVIDENCE=['CONTRACT_FREEZE','PRIOR_LINEAGE_ACCEPTANCE','MODEL_BOUNDARY_ACCEPTANCE',
    'INPUT_PROVENANCE_ACCEPTANCE','INPUT_MANIFEST_SHAPE_ACCEPTANCE','MACHINE_VECTOR_COVERAGE',
    'INDEPENDENT_POSTCHECK','SCHEMA_MIGRATION_RECEIPT','ISOLATED_REGRESSION',
    'NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN','CLEAN_CHECKOUT_RECEIPT']
OPEN_AUDITS=['AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01','AUD-V4-09-DB-CONSUMER-IDENTITY-N02',
    'V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01','AUD-AMOUNT-A-06','DM01_REAL_INCREMENTAL_BUILDERS',
    'LEGACY_VALID_MEMBER_EXACT_PRODUCER','FORWARD_PIT_HISTORY_ACCUMULATION',
    'V4-06-BAOSTOCK-BINDING-TOLERANCE-01','HISTORICAL_AS_RECORDED_ADJUSTED_PRICE']

def git_bytes(*args):
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True).stdout

def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))

def main():
    reports={name:read(PREFIX+name+'.json') for name in EVIDENCE}
    if not all(r['status'].startswith('PASS') for r in reports.values()):raise ValueError('ALL_REPAIR_EVIDENCE_MUST_PASS')
    clean=reports['CLEAN_CHECKOUT_RECEIPT'];tested=clean['tested_commit']
    for name in ['SCHEMA_MIGRATION_RECEIPT','ISOLATED_REGRESSION']:
        if reports[name]['tested_commit']!=tested:raise ValueError('TESTED_COMMIT_MISMATCH')
    freeze=reports['CONTRACT_FREEZE'];post=reports['INDEPENDENT_POSTCHECK'];coverage=reports['MACHINE_VECTOR_COVERAGE']
    for b in freeze['bindings'].values():
        if bind(b['path'])!=b:raise ValueError('CONTRACT_BINDING_CHANGED')
    baseline_paths=git_bytes('ls-tree','-r','--name-only',BASELINE).decode('utf8').splitlines()
    protected=[p for p in baseline_paths if p.startswith(('reports/v4_10/','reports/v4_09/','config/v4_09_',
        'docs/audits/','data/v4/')) or (p.startswith('config/v4_10_') and p.endswith('_v1.json')) or
        p in ['src/v4/stock_prewatch.py','src/v4/base_seed.py','src/v4/sector_native.py',
            'src/workbench_db/migrations/v4_postgres/022_v4_10_research_state_interface.sql',
            'src/workbench_db/migrations/v4_postgres/rollback/022_v4_10_research_state_interface.sql']]
    changed_worktree=git_bytes('diff','--name-only',BASELINE).decode('utf8').splitlines()
    if set(protected)&set(changed_worktree):raise ValueError('PROTECTED_GIT_TREE_CHANGED')
    # Historical data uses Git LFS and text filters. Preserve its Git identity;
    # compare stage-protected heads and the audited R1/V4-09 evidence as exact bytes.
    exact_paths=[p for p in protected if not p.startswith(('data/v4/','docs/audits/'))]
    for path in exact_paths:
        if (ROOT/path).read_bytes()!=git_bytes('show',BASELINE+':'+path):raise ValueError('PROTECTED_ORIGINAL_CHANGED:'+path)
    for b in freeze['protected_bindings']:
        if bind(b['path'])!=b:raise ValueError('PROTECTED_HEAD_BYTES_CHANGED')
    changed=git_bytes('diff','--name-only',BASELINE,tested).decode('utf8').splitlines()
    sources=[p for p in changed if p.startswith(('src/','scripts/','tests/','config/')) and p!='scripts/seal_v4_10_r1_1_candidate.py']
    for path in sources:
        if (ROOT/path).read_bytes()!=git_bytes('show',tested+':'+path):raise ValueError('TESTED_SOURCE_CHANGED:'+path)
    promotion=validate()
    if promotion['status']!='PASS':raise ValueError('V4_09_KEEP_ACCEPTED_FAILED')
    contract=read('config/v4_10_research_state_contract_r1_1.json')
    params=read('config/v4_10_parameter_set_r1_1.json')
    policy=read('config/v4_10_input_provenance_r1_1.json')
    permissions=contract['permissions']
    summary=reports['ISOLATED_REGRESSION']['summary']
    schema=reports['SCHEMA_MIGRATION_RECEIPT'];scan=reports['NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN']
    authorized_node='tests/v4_09/test_stock_prewatch.py::test_production_and_v4_09_acceptance_stay_disabled'
    if reports['ISOLATED_REGRESSION']['deselected_exact_nodes']!=[authorized_node]:raise ValueError('UNAUTHORIZED_DESELECT')
    if any(params[k]!=v for k,v in dict(downgrade_sessions=2,expiry_sessions=10,expiry_improvement_pp=3,health_deadband_pp=3).items()):raise ValueError('BUSINESS_THRESHOLD_CHANGED')
    gates={
        'G01_V4_09_accepted_head_unchanged':promotion['status']=='PASS',
        'G02_prior_full_schema_authenticity':reports['PRIOR_LINEAGE_ACCEPTANCE']['status']=='PASS',
        'G03_prior_content_address_identity':reports['PRIOR_LINEAGE_ACCEPTANCE']['status']=='PASS',
        'G04_prior_calendar_lineage':reports['PRIOR_LINEAGE_ACCEPTANCE']['status']=='PASS',
        'G05_model_boundary_authorized_manifest':reports['MODEL_BOUNDARY_ACCEPTANCE']['status']=='PASS',
        'G06_state_changing_field_provenance':reports['INPUT_PROVENANCE_ACCEPTANCE']['status']=='PASS',
        'G07_frozen_invalidation_fail_closed':not policy['fields']['frozen_invalidation']['implemented'] and reports['INPUT_PROVENANCE_ACCEPTANCE']['status']=='PASS',
        'G08_followup_completion_owner_gate':not policy['fields']['followup_complete']['implemented'] and reports['INPUT_PROVENANCE_ACCEPTANCE']['status']=='PASS',
        'G09_input_manifest_canonical_shape':reports['INPUT_MANIFEST_SHAPE_ACCEPTANCE']['status']=='PASS',
        'G10_DB_payload_publication_identity':all(schema['direct_sql_probes'].values()),
        'G11_independent_negative_vectors':post['mismatch_count']==0 and not post['missing_coverage'],
        'G12_original_semantic_vectors':coverage['original_semantic_vector_count']==98 and coverage['status']=='PASS',
        'G13_append_only_revision_rollback':all(schema['checks'].values()),
        'G14_no_symbol':scan['status']=='PASS' and scan['hard_gated_equity_symbol_hits']==0 and not scan['unclassified_paths'],
        'G15_clean_detached_full_regression':clean['status']=='PASS_CLEAN_DETACHED_CHECKOUT' and clean['detached_head'] and not clean['git_status_before'] and not clean['git_status_after'] and not summary['failures'] and not summary['errors'],
        'G16_production_shadow_focus_false':permissions==dict(production=False,shadow=False,focus_cutover=False),
        'G17_V4_10_accepted_head_absent':not (ROOT/'data/v4/V4_10_ACCEPTED_HEAD.json').exists()}
    if not all(gates.values()):raise ValueError(gates)
    missing={name:dict(status='NOT_IMPLEMENTED',value='UNKNOWN',owner=p['producer_contract_id']) for name,p in policy['fields'].items() if not p['implemented']}
    manifest=dict(contract_id='V4_10_R1_1_STAGE_CANDIDATE_MANIFEST',status=STATUS,created_at_utc=datetime.now(timezone.utc).isoformat(),
        baseline_commit=BASELINE,tested_implementation_commit=tested,business_contract='RESEARCH_STATE_V1',
        engineering_interface_contract='V4_10_STATE_REDUCER_INTERFACE_R1_1',canonicalization_contract='V4_10_CANONICAL_JSON_R1_1',
        supersedes_candidate=bind('reports/v4_10/V4_10_STAGE_CANDIDATE_MANIFEST.json'),supersedes_business_contract=False,
        authority=freeze['authority'],repair_task=freeze['repair_task'],stage_entry=freeze['stage_entry'],
        disposition=bind('docs/evidence/V4_10_R1_1_REPAIR_DISPOSITION_20261001.md'),contracts=freeze['bindings'],
        source_implementation_bindings=[bind(p) for p in sources],evidence_bindings={n:bind(PREFIX+n+'.json') for n in EVIDENCE},
        original_protected_bindings=[bind(p) for p in exact_paths],protected_head_bindings=freeze['protected_bindings'],
        protected_original_git_tree=dict(baseline_commit=BASELINE,paths=protected,changed_paths=[],
            historical_data_identity='Git tree unchanged, accounting for existing LFS and newline checkout filters; stage-protected heads additionally exact-byte checked'),
        evidence_packaging_source=bind('scripts/seal_v4_10_r1_1_candidate.py'),
        evidence_packaging_revision='Post-regression seal correction handles pre-existing historical LFS/newline filters; tested reducer, migration, configs and regression code unchanged',
        acceptance_gates={g:'PASS' for g in gates},business_thresholds={k:params[k] for k in ['downgrade_sessions','expiry_sessions','expiry_improvement_pp','health_deadband_pp']},
        vector_count=post['vector_count'],regression_summary=summary,historical_test_supersession=dict(deselected_exact_node=authorized_node,new_deselects=[]),
        db_choice='A_DATABASE_CANONICAL_IDENTITY_AND_LINEAGE_GUARD',trusted_issuer='Engineering ledger DB owner only; API callers and ordinary result writers cannot register immutable input manifests',
        accepted_fixture_scope='Disposable owner-issued engineering gate fixtures, NOT real market-data acceptance or upstream producer integration',
        known_missing_inputs=missing,accepted_entity_scope=policy['entity_scope'],open_audits=[dict(audit_id=a,status='OPEN_UNCHANGED') for a in OPEN_AUDITS],
        v4_09_keep_accepted=promotion,external_acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT',accepted_head_written=False,
        production_permission=False,shadow_production_permission=False,focus_cutover_permission=False,
        next_stage='STOP_FOR_INDEPENDENT_EXTERNAL_REAUDIT; V4-11 BLOCKED until separate acceptance and promotion/entry authority',stop_here=True)
    atomic_json(ROOT/(PREFIX+'STAGE_CANDIDATE_MANIFEST.json'),manifest)
    lines=['# V4-10 R1.1 repair closure — 2026-10-01','',STATUS,'',
        f'Tested implementation: `{tested}`. Baseline: `{BASELINE}`.',
        f'Clean detached required-family regression: {summary["passed"]} passed, {summary["skipped"]} skipped, {summary["failures"]} failed, {summary["errors"]} errors. The sole authorized historical node remains deselected; no new deselect.',
        f'{post["vector_count"]} static vectors PASS, including the original 98 semantic vectors. B01–B06 repair checks, direct SQL attacks, append-only/revision/rollback and no-symbol PASS.',
        '', 'Business RESEARCH_STATE_V1 and 2/10/3/3 thresholds remain unchanged. R1.1 supersedes the R1 engineering candidate only. Original R1 configurations, reports, migration 022 and V4-09 accepted evidence remain byte-identical.',
        '', 'The immutable engineering ledger owner is the trusted issuer. Accepted-mode tests use disposable gate fixtures, not accepted market signals. Missing V4-11/V4-12/settlement producers yield NOT_IMPLEMENTED/UNKNOWN; stock WARM remains NOT_APPLICABLE. Sector adapters remain gated by owner and entity scope.',
        '', 'Production, shadow and Focus permissions remain false. V4-10 Accepted Head is absent. V4-09 KEEP_ACCEPTED / NO_REOPEN. N01/N02 and all historical capability audits retain independent OPEN states.',
        '', '| Gate | Result |','| --- | --- |',*[f'| {g} | PASS |' for g in gates],
        '', '## Bound evidence','',*[f'- `{n}`: `{bind(PREFIX+n+".json")["sha256"]}`' for n in EVIDENCE],
        '', '## Next stage','', 'STOP for independent external repair reaudit. A Git push does not establish external acceptance or authorize V4-11. After an explicit PASS, promotion/entry is a separate authorized stage.', '']
    atomic_bytes(ROOT/(PREFIX+'CLOSURE.md'),'\n'.join(lines).encode('utf8'))
    atomic_json(ROOT/(PREFIX+'EXTERNAL_REAUDIT_HANDOFF.json'),dict(status=STATUS,tested_implementation_commit=tested,
        manifest=bind(PREFIX+'STAGE_CANDIDATE_MANIFEST.json'),closure=bind(PREFIX+'CLOSURE.md'),vector_count=post['vector_count'],
        regression_summary=summary,acceptance_gates=manifest['acceptance_gates'],external_acceptance=manifest['external_acceptance'],
        production_permission=False,shadow_production_permission=False,focus_cutover_permission=False,stop_here=True,next_stage=manifest['next_stage']))
    print(json.dumps(dict(status=STATUS,tested_commit=tested,gates=len(gates),vector_count=post['vector_count'],regression=summary)))

if __name__=='__main__':main()
