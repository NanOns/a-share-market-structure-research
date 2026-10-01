"""Seal G01–G22 against tested code and separately bound engineering evidence."""
from datetime import datetime,timezone
from pathlib import Path
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.promote_v4_09_accepted_head import bind,validate
BASELINE='db6319856468c6788c9dd656da3992e569a64572'
PREFIX='reports/v4_10/V4_10_R1_2_'
STATUS='V4_10_R1_2_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT'
EVIDENCE=['CONTRACT_FREEZE','PRIOR_LINEAGE_ACCEPTANCE','MODEL_BOUNDARY_ACCEPTANCE','INPUT_PROVENANCE_ACCEPTANCE',
    'INPUT_MANIFEST_SHAPE_ACCEPTANCE','CONTROLLED_PUBLISHER_ACCEPTANCE','MACHINE_VECTOR_COVERAGE','INDEPENDENT_POSTCHECK',
    'SCHEMA_MIGRATION_RECEIPT','ISOLATED_REGRESSION','NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN','CLEAN_CHECKOUT_RECEIPT']
def git(*args):return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True).stdout
def read(path):return json.loads((ROOT/path).read_text(encoding='utf8'))
def main():
    r={n:read(PREFIX+n+'.json') for n in EVIDENCE}
    assert all(v['status'].startswith('PASS') for v in r.values())
    freeze=r['CONTRACT_FREEZE'];post=r['INDEPENDENT_POSTCHECK'];schema=r['SCHEMA_MIGRATION_RECEIPT'];clean=r['CLEAN_CHECKOUT_RECEIPT'];reg=r['ISOLATED_REGRESSION'];scan=r['NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN']
    tested=clean['tested_commit'];assert schema['tested_commit']==reg['tested_commit']==tested
    for b in freeze['bindings'].values():assert bind(b['path'])==b
    for b in freeze['protected_bindings']:assert bind(b['path'])==b
    original=git('ls-tree','-r','--name-only',BASELINE).decode('utf8').splitlines()
    protected=[p for p in original if p.startswith(('data/v4/','reports/v4_09/','reports/v4_10/','config/v4_09_','config/v4_10_','docs/audits/')) or p in
        ['src/v4/stock_prewatch.py','src/workbench_db/migrations/v4_postgres/022_v4_10_research_state_interface.sql',
        'src/workbench_db/migrations/v4_postgres/023_v4_10_research_state_lineage_hardening.sql',
        'src/workbench_db/migrations/v4_postgres/rollback/022_v4_10_research_state_interface.sql',
        'src/workbench_db/migrations/v4_postgres/rollback/023_v4_10_research_state_lineage_hardening.sql']]
    changed=git('diff','--name-only',BASELINE).decode('utf8').splitlines();assert not set(changed)&set(protected)
    exact_paths=[p for p in protected if not p.startswith(('data/v4/','docs/audits/'))]
    for path in exact_paths:assert (ROOT/path).read_bytes()==git('show',BASELINE+':'+path),path
    sources=[p for p in git('diff','--name-only',BASELINE,tested).decode('utf8').splitlines() if p.startswith(('src/','scripts/','tests/','config/'))]
    for path in sources:assert (ROOT/path).read_bytes()==git('show',tested+':'+path),path
    promotion=validate();assert promotion['status']=='PASS'
    original_vectors=read('config/v4_10_machine_vectors_r1_1.json')['vectors'];current_vectors=read('config/v4_10_machine_vectors_r1_2.json')['vectors']
    assert len(original_vectors)==149 and len(current_vectors)==post['vector_count']
    assert all(a.get('expected')==b.get('expected') and a.get('expected_error')==b.get('expected_error') and a['id']==b['id'] for a,b in zip(original_vectors,current_vectors))
    contract=read('config/v4_10_research_state_contract_r1_2.json');policy=read('config/v4_10_input_provenance_r1_2.json');params=read('config/v4_10_parameter_set_r1_2.json')
    assert all(params[k]==v for k,v in dict(downgrade_sessions=2,expiry_sessions=10,expiry_improvement_pp=3,health_deadband_pp=3).items())
    node='tests/v4_09/test_stock_prewatch.py::test_production_and_v4_09_acceptance_stay_disabled'
    sql=post['sql_probes'];passed=lambda n:r[n]['status']=='PASS'
    gates={
        'G01_V4_09_unchanged':promotion['status']=='PASS',
        'G02_prior_content_identity':passed('PRIOR_LINEAGE_ACCEPTANCE'),
        'G03_calendar_lineage':passed('PRIOR_LINEAGE_ACCEPTANCE'),
        'G04_input_manifest_shape':passed('INPUT_MANIFEST_SHAPE_ACCEPTANCE'),
        'G05_real_old_current_boundary':passed('MODEL_BOUNDARY_ACCEPTANCE'),
        'G06_noop_rejected':sql['direct_sql_noop_boundary'],
        'G07_implemented_status_authority':passed('INPUT_PROVENANCE_ACCEPTANCE'),
        'G08_implemented_unknown_publication':passed('INPUT_PROVENANCE_ACCEPTANCE'),
        'G09_true_not_suppressed':passed('INPUT_PROVENANCE_ACCEPTANCE'),
        'G10_not_implemented_missing_owner_only':passed('INPUT_PROVENANCE_ACCEPTANCE'),
        'G11_not_applicable_scope':sql['direct_sql_not_applicable_scope'],
        'G12_ordinary_direct_insert_denied':sql['ordinary_semantic_forge_insert_blocked'] and sql['ordinary_publication_insert_blocked'],
        'G13_controlled_publisher_positive':sql['controlled_publisher_positive_path'],
        'G14_DB_identity_lineage':all(schema['direct_sql_probes'].values()),
        'G15_022_023_unchanged':all(schema['checks'][n+'_byte_identical'] for n in ['022_v4_10_research_state_interface.sql','023_v4_10_research_state_lineage_hardening.sql']),
        'G16_024_exact_rollback':all(schema['checks'].values()),
        'G17_original_149_expectations':r['MACHINE_VECTOR_COVERAGE']['original_r1_1_vector_count']==149,
        'G18_new_negative_vectors':post['mismatch_count']==0 and not post['missing_coverage'],
        'G19_clean_detached_regression':clean['status']=='PASS_CLEAN_DETACHED_CHECKOUT' and clean['detached_head'] and not clean['git_status_before'] and not clean['git_status_after'] and not reg['summary']['failures'] and not reg['summary']['errors'],
        'G20_no_new_deselect':reg['deselected_exact_nodes']==[node],
        'G21_permissions_false':contract['permissions']==dict(production=False,shadow=False,focus_cutover=False),
        'G22_accepted_head_absent':not (ROOT/'data/v4/V4_10_ACCEPTED_HEAD.json').exists(),
        'NO_SYMBOL':scan['status']=='PASS' and scan['hard_gated_equity_symbol_hits']==0 and not scan['unclassified_paths']}
    assert all(gates.values()),gates
    registry=read('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json')
    assert registry['governance_only'] and all(e['status']=='OPEN' and e['external_acceptance'] is None for e in registry['entries'])
    manifest=dict(contract_id='V4_10_R1_2_STAGE_CANDIDATE_MANIFEST',status=STATUS,created_at_utc=datetime.now(timezone.utc).isoformat(),
        baseline_commit=BASELINE,tested_implementation_commit=tested,authority=freeze['authority'],repair_task=freeze['repair_task'],stage_entry=freeze['stage_entry'],
        disposition=bind('docs/evidence/V4_10_R1_2_REPAIR_DISPOSITION_20261001.md'),contracts=freeze['bindings'],
        supersedes_candidate=freeze['previous_candidate'],supersedes_business_contract=False,business_contract='RESEARCH_STATE_V1',
        source_implementation_bindings=[bind(p) for p in sources],evidence_bindings={n:bind(PREFIX+n+'.json') for n in EVIDENCE},
        original_protected_bindings=[bind(p) for p in exact_paths],protected_head_bindings=freeze['protected_bindings'],
        protected_original_git_tree=dict(baseline_commit=BASELINE,paths=protected,changed_paths=[],strategy='Historical data/audits retain Git identity with existing LFS/newline filters; scoped heads/runtime/contracts/reports/migrations additionally exact-byte verified'),
        acceptance_gates={k:'PASS' for k in gates},business_thresholds={k:params[k] for k in ['downgrade_sessions','expiry_sessions','expiry_improvement_pp','health_deadband_pp']},
        vector_count=post['vector_count'],regression_summary=reg['summary'],historical_test_supersession=dict(deselected_exact_node=node,new_deselects=[]),
        fixture_supersession='Original 149 expectations unchanged; two no-op positive inputs become authentic OLD fixtures under R1.2. No-op itself is now rejected.',
        old_source_authority='Independent V0 frozen golden producer + immutable DB owner import; not a caller-relabeled current output',
        controlled_publisher='NOLOGIN authorized producer role; publish_state accepts inputs, executes reducer/validation and emits attestation; DB independently guards identity/lineage',
        accepted_fixture_scope='Disposable engineering gate fixtures only; no actual market signal acceptance, production credentials or future detector integration',
        cross_stage_registry=bind('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json'),open_audits=[dict(audit_id=e['audit_id'],status=e['status']) for e in registry['entries']],
        known_missing_inputs={k:dict(owner=v['producer_contract_id'],value='UNKNOWN') for k,v in policy['fields'].items() if not v['implemented']},
        v4_09_keep_accepted=promotion,production_permission=False,shadow_production_permission=False,focus_cutover_permission=False,
        accepted_head_written=False,external_acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT',stop_here=True,
        next_stage='STOP for independent R1.2 external reaudit; V4-11 remains BLOCKED. Cross-stage work packages have independent entries/gates.')
    atomic_json(ROOT/(PREFIX+'STAGE_CANDIDATE_MANIFEST.json'),manifest)
    summary=reg['summary'];lines=['# V4-10 R1.2 closure','',STATUS,'',f'Tested implementation: `{tested}`.',
        f'Clean detached regression: {summary["passed"]} passed / {summary["skipped"]} skipped / 0 failures / 0 errors; only the existing authorized historical node deselected.',
        f'{post["vector_count"]} static vectors PASS. Original 149 expected values retained with explicit fixture adaptation. G01–G22 and no-symbol PASS.',
        '', 'Real OLD→CURRENT authority, no-op rejection, implemented-status authority, trusted TRUE suppression defenses, controlled publisher/ordinary reader permission separation, legacy row readback, append-only/revisions and exact 024 schema/role/grant rollback all pass.',
        '', 'Original 022/023, R1/R1.1 configurations/reports, V4-09 runtime and accepted heads remain unchanged. Business thresholds remain 2/10/3/3. No production/shadow/Focus permission; V4-10 Accepted Head is absent.',
        '', 'Independent V0 source is a frozen engineering golden, not a market acceptance claim. Accepted migration correctly stays UNKNOWN until required detector owners arrive; no fake enrollment. Only the trusted owner imports source authority; publisher credentials are not provisioned to ordinary applications.',
        '', 'Cross-stage master first-entry package e368f87 separately records nine OPEN work packages and A01/A08/A09 implementation entries. It does not claim capability repairs or external acceptance.',
        '', '| Gate | Result |','| --- | --- |',*[f'| {k} | PASS |' for k in gates],
        '', 'STOP for independent external R1.2 reaudit. V4-11 remains blocked; a push is not external acceptance.', '']
    atomic_bytes(ROOT/(PREFIX+'CLOSURE.md'),'\n'.join(lines).encode('utf8'))
    atomic_json(ROOT/(PREFIX+'EXTERNAL_REAUDIT_HANDOFF.json'),dict(status=STATUS,tested_implementation_commit=tested,
        manifest=bind(PREFIX+'STAGE_CANDIDATE_MANIFEST.json'),closure=bind(PREFIX+'CLOSURE.md'),acceptance_gates=manifest['acceptance_gates'],
        vector_count=post['vector_count'],regression_summary=summary,external_acceptance=manifest['external_acceptance'],stop_here=True,next_stage=manifest['next_stage'],
        production_permission=False,shadow_production_permission=False,focus_cutover_permission=False))
    print(json.dumps(dict(status=STATUS,tested_commit=tested,vector_count=post['vector_count'],regression=summary,gates=len(gates))))
if __name__=='__main__':main()
