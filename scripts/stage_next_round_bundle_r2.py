"""Explicit batch-only staging and content manifest; preserve unrelated changes."""
from pathlib import Path
import subprocess
from scripts.next_round_bundle_r2 import ROOT,P,read,write,bind,atomic_bytes,verify_protected

DIRECTORIES=['docs/evidence/next_round_r2','reports/next_round_r2','reports/audits/next_round_r2','reports/audits/a04_r3',
 'reports/v4_11/candidate_r2','data/v4/confirmation_candidates_r2','data/v4/a02_accepted_amendments_r1',
 'data/v4/a05_b2_amendment_r1','data/v4/a05_b2_amendment_r2','data/v4/a05_b2_amendment_r3',
 'data/v4/a03_scoped_acceptance_r1','data/v4/a04_go_forward_r3','data/v4/source_evidence/a04_r3',
 'data/v4/source_evidence/next_round_r2_baseline','tests/v4_a04_r3','tests/v4_a02_a05_formal_r1','tests/v4_parallel_scoped_formalization_r1']
FILES=['.gitattributes','src/v4/confirmation.py','tests/v4_11/test_confirmation.py','tests/v4_11/test_persistence.py','tests/v4_11/test_semantic_r2.py',
 'src/sector/a05_b2_scoped_amendment_r1.py','src/v4/a02_a05_external_acceptance_r1.py',
 'src/workbench_analysis/amount_a_go_forward_r3.py','src/workbench_analysis/amount_a_source_binding_r3_1.py',
 'src/workbench_analysis/parallel_scoped_acceptance_r1.py',
 'src/workbench_db/migrations/v4_postgres/027_confirmation_stock_amr20_semantic_r2.sql',
 'src/workbench_db/migrations/v4_postgres_rollbacks/027_confirmation_stock_amr20_semantic_r2.sql',
 'data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json','data/v4/SCOPED_ACCEPTED_OWNER_BOOTSTRAP_R1.json',
 'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R12_FORMALIZATION.json']
CONFIGS=['a04_amount_a_go_forward_r3','a04_amount_a_namespace_r3','a04_amount_a_source_admission_r3_1',
 'historical_publication_reader_accepted_history_only_r1','v4_11_confirmation_detector_contract_r2',
 'v4_11_legacy_extraction_manifest_r2','v4_11_stock_amr20_semantic_erratum_r2','v4_migration_allocation_registry_r3']
SCRIPTS=['allocate_v4_migration_r3','build_v4_11_semantic_candidate_r2','formalize_a02_a05_accepted_producers_r1',
 'formalize_parallel_scoped_acceptance_r1','formalize_parallel_scoped_acceptance_r2','next_round_bundle_r2',
 'prepare_v4_11_semantic_repair_r2','replay_a02_accepted_rps_amendments_r1',
 'replay_a05_b2_current_snapshot_amendment_r1','replay_a05_b2_current_snapshot_amendment_r2','replay_a05_b2_current_snapshot_amendment_r3',
 'run_a04_go_forward_r3','run_a04_go_forward_r3_1','seal_a02_a05_formal_handoff_r1','seal_a04_go_forward_r3',
 'v4_11_candidate_inputs_r2','verify_a02_a05_formal_amendment_readback_r1','verify_next_round_bundle_clean_r2',
 'verify_v4_11_semantics_r2','seal_v4_11_semantic_candidate_r2','seal_next_round_bundle_r2','stage_next_round_bundle_r2']
DOCS=['A02_EXTERNAL_FORMALIZATION_AMENDMENT_CLOSURE_R1_20261001',
 'A04_R3_AMOUNT_A_SCOPED_CANDIDATE_CLOSURE_20261001','A05_EXTERNAL_FORMALIZATION_B2_AMENDMENT_CLOSURE_R1_20261001',
 'PARALLEL_SCOPED_ACCEPTANCE_FORMALIZATION_R1_20261001','PARALLEL_SCOPED_ACCEPTANCE_NO_SYMBOL_SUPPLEMENT_R2_20261001',
 'NEXT_ROUND_R2_CANDIDATE_CLOSURE_20261001']

def selected():
    paths=set(FILES+[f'config/{x}.json' for x in CONFIGS]+[f'scripts/{x}.py' for x in SCRIPTS]+[f'docs/audits/{x}.md' for x in DOCS])
    for directory in DIRECTORIES:
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT/directory).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp'))
    missing=[p for p in paths if not (ROOT/p).is_file()]
    if missing:raise ValueError('BATCH_FILE_MISSING:'+str(missing))
    return sorted(paths)

def main():
    verify_protected();paths=selected();attrs=ROOT/'.gitattributes'
    original=attrs.read_bytes();archive='data/v4/source_evidence/next_round_r2_baseline/.gitattributes'
    if not (ROOT/archive).exists():atomic_bytes(archive,original)
    lines=[d+'/** -text' for d in DIRECTORIES if d.startswith(('data/','reports/','docs/evidence/'))]
    lines+=['data/v4/a02_accepted_amendments_r1/*.gz filter=lfs diff=lfs merge=lfs -text']
    # Exact runtime evidence is read byte-for-byte. Only new batch text with CRLF
    # needs a per-file rule; baseline attributes and source files are untouched.
    lines += [p+' -text' for p in paths if p!='.gitattributes' and b'\r\n' in (ROOT/p).read_bytes()
        and not any(p.startswith(d+'/') for d in DIRECTORIES)]
    block='\n# R2 scoped formalization and semantic repair exact-byte artifacts\n'+'\n'.join(sorted(set(lines)))+'\n'
    if block.encode() not in original:atomic_bytes('.gitattributes',original+block.encode())
    paths=selected()
    manifest_path=P+'BATCH_CANDIDATE_ARTIFACT_MANIFEST_R1.json'
    refs=[bind(p) for p in paths if p!=manifest_path]
    write(manifest_path,dict(contract_id='V4_NEXT_ROUND_R2_ARTIFACT_MANIFEST',artifacts=refs,
        manifest_self_excluded=True,scope='AUTHORIZED_R2_BATCH_ONLY',external_acceptance=False))
    paths=selected()
    for start in range(0,len(paths),60):subprocess.run(['git','add','-f','--',*paths[start:start+60]],cwd=ROOT,check=True)
    staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode('utf8').split('\0')
    if set(filter(None,staged))!=set(paths):raise ValueError('STAGED_PATHS_OUTSIDE_EXPLICIT_BATCH')
    verify_protected();print(dict(staged_files=len(paths),manifest=bind(manifest_path)))

if __name__=='__main__':main()
