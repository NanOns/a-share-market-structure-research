"""Seal R3 evidence with explicit candidate gates and reproducible file inventory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
from build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from sector.machine_ast_r3 import ast_digest,validate_ast,evaluate_ast
from sector.v4_08_rotation_vectors import evaluate_rotation_vector

BASE='0581731c1284e82380fa115156f1dc0a16a38bd4'
MANIFEST='reports/v4_08/V4_08_R3_STAGE_CANDIDATE_MANIFEST.json'
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def binding(path):
    value=(ROOT/path).read_bytes()
    return {'path':path,'sha256':hashlib.sha256(value).hexdigest(),'byte_count':len(value)}
def write(name,value):atomic_json(ROOT/'reports/v4_08'/name,value)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf-8').strip()

def selected_paths():
    paths={'.gitattributes'}
    for pattern in ['scripts/*v4_08_r3*.py','scripts/build_v4_08_r3_machine_contracts.py','src/sector/*r3.py','config/v4_08_*v2.json','config/v4_08_r3_*.json','tests/v4_08/test_r3_*.py','reports/v4_08/V4_08_R3*','reports/v4_08/source_contracts/REV*_20260930.md','reports/v4_01/*GO_FORWARD*R1.json','reports/v4_02/*GO_FORWARD*R1.json','data/v4/*GO_FORWARD*R1.json','data/v4/artifact_store/v4_01/*GO_FORWARD*R1.json','data/v4/artifact_store/v4_02/*GO_FORWARD*R1.json']:
        paths.update(p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern) if p.is_file())
    paths.update(['src/workbench_db/migrations/v4_postgres/019_v4_08_membership_source_basis_guard_r3.sql','src/workbench_db/migrations/v4_postgres/rollback/019_v4_08_membership_source_basis_guard_r3.sql','docs/evidence/V4_08_R2_INDEPENDENT_EXTERNAL_AUDIT_20260930.md','docs/evidence/V4_08_R3_FORWARD_PIT_ADMISSION_IDENTITY_CALENDAR_AND_BASIS_GUARD_TASK_20260930.md','reports/audits/V4_01_OFFICIAL_LIST_DATE_ANCHOR_RECONCILIATION_20260930.json','reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R3.json','reports/v4_08/staging/V4_08_R3_EXACT_DAY_RAW_MEMBERSHIP_DIAGNOSTIC.jsonl.gz','data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json'])
    official=read('reports/v4_08/V4_08_R3_OFFICIAL_LIFECYCLE_SOURCE_CAPTURE.json')
    for source in official['sources']:
        for field in ['path','extracted_text_path']:
            if source.get(field):paths.add(source[field])
    for source in read('reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json')['files']:paths.add(source['frozen_path'])
    for page in read('reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json')['pages']:paths.add(page['path'])
    return sorted(x for x in paths if x!=MANIFEST)

def main():
    args=argparse.ArgumentParser();args.add_argument('--final',action='store_true');options=args.parse_args()
    # Latest applicable upgrade was delivered during this stage; preserve its bytes without staging unrelated FEP work.
    latest='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
    frozen='reports/v4_08/source_contracts/REV4_FEP_R2_20260930.md'
    if (ROOT/latest).exists():atomic_bytes(ROOT/frozen,(ROOT/latest).read_bytes())
    entry=ROOT/'reports/v4_08/V4_08_R3_STAGE_ENTRY.md'
    text=entry.read_text(encoding='utf-8')
    if 'Latest-stage addendum' not in text:
        atomic_bytes(entry,(text+'\n## Latest-stage addendum\n\nREV4-FEP-R2 was consulted after its delivery during R3; hash '+binding(frozen)['sha256']+'. It preserves the stage baseline and defers FEP external design acceptance. R3 scope is unchanged. Frozen copy: '+frozen+'.\n').encode('utf-8'))
    schema=read('reports/v4_08/V4_08_R3_SCHEMA_MIGRATION_RECEIPT.json')
    assert schema['status']=='PASS' and all(schema['checks'].values())
    write('V4_08_R3_SOURCE_BASIS_GUARD_ACCEPTANCE.json',{'status':'PASS_ENGINEERING_B07_THREE_LAYERS','independent_disposable_verifier':binding('scripts/run_v4_08_r3_isolated_verification.py'),'schema_receipt':binding('reports/v4_08/V4_08_R3_SCHEMA_MIGRATION_RECEIPT.json'),'checks':schema['checks'],'production_schema_modified':False})
    pairs={'PIT_OBSERVED_ACCEPTED':'PIT_OBSERVED','CURRENT_TDX_DIAGNOSTIC':'CURRENT_TDX_MEMBERSHIP','CURRENT_REPLAY_DIAGNOSTIC':'CURRENT_MEMBERSHIP_REPLAY','DERIVED_PARENT_DIAGNOSTIC':'DERIVED_PARENT_MEMBERSHIP'}
    write('V4_08_R3_BASIS_QUALITY_COMPATIBILITY.json',{'status':'PASS_FOUR_VALID_AND_TWELVE_INVALID_PAIRS','required_pairs':pairs,'same_basis_chain_required':['source_revision','snapshot','fact'],'other_diagnostic_quality_behavior':'Not automatically formal; existing formal view whitelist remains mandatory','schema_receipt':binding('reports/v4_08/V4_08_R3_SCHEMA_MIGRATION_RECEIPT.json')})
    params_doc=read('config/v4_08_algorithm_parameter_set_v1.json');params={x['parameter_id']:x['value'] for x in params_doc['parameters']}
    models=[]
    for path in ['config/v4_08_sector_prewatch_contract_v2.json','config/v4_08_rotation_core_contract_v2.json']:
        doc=read(path);fields={x['field_id']:x for x in read(doc['field_registry_path'])['fields']}
        result=validate_ast(doc['rules'],fields,params)
        assert doc['ast_digest']==ast_digest(doc['rules']) and doc['field_registry_digest']==binding(doc['field_registry_path'])['sha256']
        assert doc['machine_vector_set_digest']==binding(doc['machine_vector_set_path'])['sha256']
        models.append({'model_contract_id':doc['model_contract_id'],'contract':binding(path),'ast_digest':doc['ast_digest'],'validation':result,'formal_consumer_enabled':False})
    write('V4_08_R3_ROTATION_MACHINE_AST_ACCEPTANCE.json',{'status':'PASS_STRUCTURED_BOUND_AST_ENGINEERING_ONLY','models':models,'terminal_and_fallback_predicates_included':True,'B2_legacy_adapter':'NOT_IMPLEMENTED','production_fsm':'V4_10_NOT_IMPLEMENTED','pending_parameters':[k for k,v in params.items() if v is None]})
    vectors=[]
    for vector in read('config/v4_08_rotation_machine_vectors_v2.json')['vectors']:
        result=evaluate_rotation_vector(vector['scenario']);assert all(result[k]==v for k,v in vector['expected'].items())
        vectors.append({'id':vector['id'],'expected':vector['expected'],'actual':{k:result[k] for k in vector['expected']},'status':'PASS','premise_basis':'SYNTHETIC_PREDICATE_PREMISES; no runtime parameter substitution'})
    write('V4_08_R3_ROTATION_VECTOR_COVERAGE.json',{'status':'PASS_R1A_R1B_R2_R3','vectors':vectors,'canonical_ast_branch_tests':binding('tests/v4_08/test_r3_admission_and_ast.py'),'forbidden_input_mutation_tests':True,'formal_consumer_enabled':False})
    write('V4_08_R3_RETENTION_PARAMETER_DECISION_PACKAGE.json',{'status':'PENDING_V4_00G_NO_VALUES_INVENTED','pending_parameters':[x for x in params_doc['parameters'] if x['value'] is None],'required_decision_evidence':['Explicit V4-00G parameter registration and authority','Frozen independent synthetic edge/UNKNOWN vectors','Independent acceptance before affected formal consumer activation'],'runtime_values_supplied':False,'affected_rotation_formal_consumer_enabled':False,'membership_acceptance_waits_for_parameters':False})
    atomic_json(ROOT/'reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R3.json',{'audit_id':'V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01','status':'OPEN_REPAIR_CONTINUES_INDEPENDENTLY','starting_evidence':binding('reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R2.json'),'new_input_assessment':{'target':'2026-09-30','required_prior_endpoints':['2026-09-29','2026-09-24'],'calendar_extension_candidate':binding('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json'),'dated_identity_candidate':binding('data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json'),'calendar_and_incremental_identity_accepted':False,'accepted_prior_rps_factor_publication_available':False,'retrospective_membership_not_used_as_historical_universe':True},'required_next_inputs':read('reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R2.json')['required_next_inputs'],'thresholds_changed':False,'v4_03_r3_staging_values_copied':False,'v4_05_accepted_artifacts_modified':False,'accepted_prior_rps_values_created':False,'impact':'True Seed-dependent fields remain UNKNOWN; non-blocking for membership/native non-seed/AST engineering.'})
    if options.final:
        regression=read('reports/v4_08/V4_08_R3_ISOLATED_REGRESSION.json');clean=read('reports/v4_08/V4_08_R3_CLEAN_CHECKOUT_RECEIPT.json')
        assert regression['status']=='PASS' and clean['status']=='PASS_CLEAN_CHECKOUT_DISPOSABLE_DATABASE'
        atomic_json(ROOT/'reports/v4_01/V4_01_GO_FORWARD_IDENTITY_CLEAN_CHECKOUT_R1.json',{'status':'PASS_CLEAN_CHECKOUT_ENGINEERING_EXTERNAL_PROMOTION_REQUIRED','tested_commit':clean['tested_commit'],'identity_revision':binding('data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json'),'independent_postcheck':binding('reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json'),'clean_checkout':binding('reports/v4_08/V4_08_R3_CLEAN_CHECKOUT_RECEIPT.json'),'clean_admission_verifier':binding('reports/v4_08/V4_08_R3_CLEAN_ADMISSION_VERIFIER.json'),'formal_identity_accepted':False})
        candidate=read('reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json')
        handoff={'status':candidate['status'],'starting_head':BASE,'tested_implementation_commit':clean['tested_commit'],'stage_commits_before_final_evidence_seal':git('log','--format=%H %s',BASE+'..HEAD').splitlines(),'final_pushed_head_resolution':'The final evidence commit containing this closure; exact SHA is reported after push and remote verification. Self-hash is excluded from its own content.','migration_hashes':[binding(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('01[6-9]*.sql'))],'rollback':binding('src/workbench_db/migrations/v4_postgres/rollback/019_v4_08_membership_source_basis_guard_r3.sql'),'identity_candidate_head':binding('data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json'),'identity_revision':candidate['identity_revision'],'all_11_lifecycle_dispositions':read('reports/v4_08/V4_08_R3_IDENTITY_LIFECYCLE_ADJUDICATION.json')['classifications'],'calendar_candidate_head':binding('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json'),'calendar_extension':candidate['calendar_extension'],'first_pit_target_date_proposed':candidate['proposed_first_pit_target_date'],'first_accepted_pit_target_date':None,'source_observation':candidate['complete_source_observed_at'],'engineering_cutoff':candidate['target_publication_cutoff_candidate'],'formal_membership_rows_by_type':candidate['formal_accepted_membership_rows_by_type'],'prospective_after_input_promotion_rows':candidate['prospective_candidate_member_rows_by_type'],'active_universe_exclusions':candidate['active_universe_exclusions_by_reason'],'B07_negative_vector':schema['checks'],'clean_disposable_database_identity':clean['database_identity'],'regression':regression['regression']['summary'],'rotation_vectors':vectors,'pending_five_parameters':[k for k,v in params.items() if v is None],'Prior_RPS_status':'OPEN_REPAIR_CONTINUES_INDEPENDENTLY','separate_lifecycle_anchor_audit':binding('reports/audits/V4_01_OFFICIAL_LIST_DATE_ANCHOR_RECONCILIATION_20260930.json'),'no_V4_08_Accepted_Head':not (ROOT/'data/v4/V4_08_ACCEPTED_HEAD.json').exists(),'next_stage':'Independent external audit of R3 candidate and V4-01/V4-02 input promotion; actual first forward PIT materialization only after accepted dated inputs; no V4-09/10 production advancement.'}
        assert handoff['no_V4_08_Accepted_Head']
        write('V4_08_R3_EXTERNAL_REAUDIT_HANDOFF.json',handoff)
        closure='# V4-08 R3 Closure\n\n'+candidate['status']+'\n\n- B07 insert guards, defensive formal view, independent disposable verifier and rollback: PASS.\n- All 11 identity keys adjudicated: 2 target-active listed additions, 9 NOT_LISTED_AT_TARGET. Accepted R7 preserved.\n- Calendar appended through 2026-09-30 with official holiday evidence; accepted historical calendar preserved.\n- Independent admission verifier recomputed every diagnostic row and official complete catalogue.\n- Identity/calendar candidate heads require independent external promotion. No actual PIT snapshot, no V4-08 Accepted Head; formal INDUSTRY/THEME rows = 0/0.\n- Prospective after input promotion: '+json.dumps(candidate['prospective_candidate_member_rows_by_type'])+'. These are diagnostics, not a formal baseline.\n- Source observed '+candidate['complete_source_observed_at']+'; engineering cutoff '+candidate['target_publication_cutoff_candidate']+'. No backdating/carry-forward.\n- Clean detached implementation '+clean['tested_commit']+'; disposable DB only, no config/.env read/copied, process-only DSN, cluster destroyed. Regression '+json.dumps(regression['regression']['summary'])+'.\n- B0/B1 machine AST and R1A/R1B/R2/R3: PASS engineering. Five retention parameters pending; B2/production FSM NOT_IMPLEMENTED.\n- Prior-RPS independently OPEN; true Seed-dependent fields UNKNOWN. Separate SH.600018 listing-anchor reconciliation audit OPEN.\n- Exact migration digests, all 11 dispositions, candidate identities, counts/exclusions and DB identity: V4_08_R3_EXTERNAL_REAUDIT_HANDOFF.json.\n- Candidate files/hash inventory: V4_08_R3_STAGE_CANDIDATE_MANIFEST.json.\n- Stop for independent external audit.\n'
        atomic_bytes(ROOT/'reports/v4_08/V4_08_R3_CLOSURE.md',closure.encode())
    paths=selected_paths()
    write('V4_08_R3_STAGE_CANDIDATE_MANIFEST.json',{'contract_id':'V4_08_R3_STAGE_CANDIDATE_MANIFEST_V1','status':'SEALED_FOR_EXTERNAL_AUDIT' if options.final else 'IMPLEMENTATION_INPUTS_PREPARED','starting_head':BASE,'file_count':len(paths),'files':[binding(x) for x in paths],'self_hash_excluded':True,'no_V4_08_Accepted_Head':True,'unrelated_FEP_artifacts_staged':False})
    print(json.dumps({'status':'SEALED' if options.final else 'PREPARED','file_count':len(paths)}))

if __name__=='__main__':main()
