"""R2 execution entry, exact authority capture and protected baseline readback."""
from pathlib import Path
import subprocess,json,hashlib
from scripts.next_round_bundle_r1 import ROOT,bind,read,write,atomic_bytes,exact,sha,verify_protected as verify_previous
from datetime import datetime,timezone
BASELINE='66ef2e342dd339cc9795c2d1fd774b8edec4c345'
P='reports/next_round_r2/';DOCROOT='docs/evidence/next_round_r2/'
AUDIT=DOCROOT+'V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md'
MASTER=DOCROOT+'V4_NEXT_ROUND_EXECUTION_MASTER_R2_20261001.md'
TASKS=['V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md','V4_NEXT_ROUND_EXECUTION_MASTER_R2_20261001.md',
 'V4_11_R2_AMR20_AMOUNT_A_SEMANTIC_REPAIR_TASK_20261001.md','V4_A02_ACCEPTANCE_FORMALIZATION_AND_DOWNSTREAM_AMENDMENT_TASK_R1_20261001.md',
 'V4_A04_R3_AMOUNT_A_FORMAL_AUTHORITY_CLOSURE_TASK_20261001.md','V4_A05_ACCEPTANCE_AND_V4_08_B2_CAPABILITY_AMENDMENT_TASK_R1_20261001.md',
 'V4_PARALLEL_SCOPED_ACCEPTANCE_FORMALIZATION_A03_A06_A07_OWNER_READER_TASK_R1_20261001.md']

def verify_protected():
    verify_previous();entry=read(P+'BATCH_STAGE_ENTRY_R1.json')
    representations=read('reports/next_round_r1/BATCH_PROTECTED_REPRESENTATIONS_R1.json')['representations']
    for ref in entry['protected_baseline']:
        try:exact(ref)
        except ValueError:
            alternate=next((x for x in representations if x['original_binding']==ref),None)
            if not alternate:raise
            raw=exact(alternate['original_bytes_archive']).read_bytes();current=exact(alternate['git_representation']).read_bytes()
            if raw.replace(b'\r\n',b'\n')!=current:raise ValueError('EXACT_BASELINE_REPRESENTATION_MISMATCH')
    return entry

def prepare():
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=BASELINE:raise ValueError('R2_EXACT_BASELINE_REQUIRED')
    verify_previous()
    for name in TASKS:
        raw=(Path('D:/Users/lps/Desktop/阶段任务/新建文件夹')/name).read_bytes();p=ROOT/(DOCROOT+name)
        if p.exists() and p.read_bytes()!=raw:raise ValueError('TASK_SOURCE_CHANGED')
        if not p.exists():atomic_bytes(DOCROOT+name,raw)
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');gate=validate_head_v2(ROOT,data)
    paths={p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4').glob('*HEAD*.json')}
    paths.update(['data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json','reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json',
       'reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R11_CANDIDATE.json','config/v4_migration_allocation_registry_r2.json',
       'src/workbench_db/migrations/v4_postgres/026_confirmation_events_candidate_r1.sql','config/v4_11_entry_contracts_r1.json'])
    records=[]
    for path in ['src/v4/confirmation.py','tests/v4_11/test_confirmation.py']:
        raw=(ROOT/path).read_bytes();archive='data/v4/source_evidence/next_round_r2_baseline/'+path
        atomic_bytes(archive,raw);records.append(dict(original_binding=bind(path),original_bytes_archive=bind(archive)))
    write(P+'BASELINE_RUNTIME_ARCHIVE_R1.json',dict(baseline_commit=BASELINE,archives=records))
    entry=dict(contract_id='V4_NEXT_ROUND_EXECUTION_STAGE_ENTRY_R2',baseline_commit=BASELINE,authority=bind(AUDIT),master=bind(MASTER),
        task_bindings=[bind(DOCROOT+n) for n in TASKS],protected_baseline=[bind(p) for p in sorted(paths)],
        baseline_tracked_paths=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True,encoding='utf8').splitlines(),
        phase0=dict(status='DEGRADED_PASS',scope='ACCEPTED_DATA_INPUT_PREFLIGHT',accepted_data_head=gate),
        stage_contract='MASTER_R2_P0_V4_11_SEMANTIC_REPAIR_FIRST',execution_acceptance='AUTHORIZED_REPAIR_AND_EXPLICIT_SCOPED_FORMALIZATIONS',
        permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False),
        DataHead='KEEP_2026-09-30',StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',v4_12_authorized=False,
        next_stage='STOP_AFTER_COMMIT_PUSH_WAIT_FOR_INDEPENDENT_EXTERNAL_REAUDIT',observed_at_utc=datetime.now(timezone.utc).isoformat())
    write(P+'BATCH_STAGE_ENTRY_R1.json',entry);verify_protected();return entry
if __name__=='__main__':print(json.dumps(dict(status=prepare()['phase0']['status'])))
