"""Shared read-only input preflight and atomic candidate evidence helpers."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,tempfile,subprocess
ROOT=Path(__file__).resolve().parents[1]
BASELINE='bc3e398efb4f4a05c20973ff3cb335a6b101ac87'
P='reports/next_round_r1/'
DOCROOT='docs/evidence/next_round_r1/'
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def bind(path):
    p=ROOT/path
    return dict(path=str(path).replace('\\','/'),sha256=sha(p),bytes=p.stat().st_size)
def read(path):return json.loads((ROOT/path).read_bytes())
def exact(ref):
    p=(ROOT/ref['path']).resolve()
    if not p.is_relative_to(ROOT.resolve()) or not p.is_file() or sha(p)!=ref['sha256'] or p.stat().st_size!=ref.get('bytes',ref.get('byte_count',p.stat().st_size)):
        raise ValueError('EXACT_BINDING_REQUIRED:'+ref['path'])
    return p
def atomic_bytes(path,data):
    p=(ROOT/path).resolve()
    if not p.is_relative_to(ROOT.resolve()):raise ValueError('CANDIDATE_OUTPUT_OUTSIDE_PROJECT')
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,p)
    finally:Path(name).unlink(missing_ok=True)
def write(path,value,*,immutable=True):
    data=(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8');p=ROOT/path
    if immutable and p.exists():
        if p.read_bytes()!=data:raise ValueError('IMMUTABLE_CANDIDATE_CONFLICT:'+str(path))
    else:atomic_bytes(path,data)
    return bind(path)
def verify_protected():
    entry=read(P+'BATCH_STAGE_ENTRY_R1.json')
    representations=read(P+'BATCH_PROTECTED_REPRESENTATIONS_R1.json')['representations'] if (ROOT/(P+'BATCH_PROTECTED_REPRESENTATIONS_R1.json')).exists() else []
    for b in entry['protected_heads']:
        try:exact(b)
        except ValueError:
            r=next((r for r in representations if r['original_binding']==b),None)
            if r is None:raise
            raw=exact(r['original_bytes_archive']).read_bytes();canonical=exact(r['git_representation']).read_bytes()
            if sha(exact(r['original_bytes_archive']))!=b['sha256'] or raw.replace(b'\r\n',b'\n')!=canonical:raise ValueError('EXACT_PROTECTED_REPRESENTATION_MISMATCH')
    return entry
def prepare(names):
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=BASELINE:raise ValueError('EXACT_BATCH_BASELINE_REQUIRED')
    for name in names:
        source=Path('D:/Users/lps/Desktop/阶段任务/新建文件夹')/name;target=DOCROOT+name
        if (ROOT/target).exists() and (ROOT/target).read_bytes()!=source.read_bytes():raise ValueError('TASK_DOCUMENT_CHANGED')
        if not (ROOT/target).exists():atomic_bytes(target,source.read_bytes())
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');gate=validate_head_v2(ROOT,data)
    phase0=read('reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json')
    historical_phase0_status=phase0.get('status',phase0.get('final_status'))
    protected_paths={p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4').glob('*HEAD*.json')}
    protected_paths.update(['data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R3.json','reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R10.json','config/v4_11_entry_contracts_r1.json','config/v4_migration_allocation_registry_r1.json','src/workbench_analysis/today_research_scanner_v3_3.py'])
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True,encoding='utf8').splitlines()
    entry=dict(contract_id='V4_NEXT_ROUND_BUNDLE_STAGE_ENTRY_V1',baseline_commit=BASELINE,stage_contract=bind(DOCROOT+'V4_NEXT_ROUND_MASTER_EXECUTION_BUNDLE_R1_20261001.md'),
        task_bindings=[bind(DOCROOT+n) for n in names],observed_at=datetime.now(timezone.utc).isoformat(),
        phase0=dict(status='DEGRADED_PASS',scope='ACCEPTED_INPUT_PREFLIGHT',accepted_data_head_validation=gate,historical_receipt=bind('reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json'),historical_status=historical_phase0_status),
        protected_heads=[bind(p) for p in sorted(protected_paths)],baseline_tracked_paths=tracked,
        priority=['V4-11','A02','A03/A04/A05/OWNER','A06/A07/READER_DI'],permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False),
        acceptance_result='IMPLEMENTATION_AUTHORIZED_CANDIDATE_ONLY',next_stage='INDEPENDENT_EXTERNAL_REAUDIT; STOP_AFTER_UNIFIED_COMMIT_AND_PUSH',v4_12_implementation_authorized=False)
    write(P+'BATCH_STAGE_ENTRY_R1.json',entry)
    return entry
