"""Lossless actual runtime evidence and independent scoped JUnit recount."""
from pathlib import Path
import gzip,hashlib,json,subprocess,xml.etree.ElementTree as ET
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_integration_20261011'
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
paths=list(OUT.glob('PG_VERIFIER_BATCH_R1*'))+list(OUT.glob('CAPACITY_DETAIL_7cb0ad62*'))
paths+=list(OUT.glob('CAPACITY_DETAIL_CONTINUATION_R[45]_RAW.log'))
records=[]
for path in sorted(set(paths)):
    if path.suffix=='.gz':continue
    target=path.with_name(path.name+'.gz')
    if not target.exists():
        with path.open('rb') as source,target.open('xb') as output:
            with gzip.GzipFile(fileobj=output,mode='wb',mtime=0) as zipped:
                for block in iter(lambda:source.read(1024*1024),b''):zipped.write(block)
    digest=hashlib.sha256()
    with gzip.open(target,'rb') as zipped:
        for block in iter(lambda:zipped.read(1024*1024),b''):digest.update(block)
    if digest.hexdigest()!=sha(path):raise ValueError('LOSSLESS_SEAL_MISMATCH')
    records.append(dict(path=path.relative_to(ROOT).as_posix(),raw_sha256=sha(path),raw_bytes=path.stat().st_size,
        gzip_path=target.relative_to(ROOT).as_posix(),gzip_sha256=sha(target)))
cases=ET.parse(OUT/'PG_VERIFIER_BATCH_R1.xml').findall('.//testcase')
counts=Counter(next((name for tag,name in [('failure','FAIL'),('error','ERROR'),('skipped','SKIP')] if row.find(tag)is not None),'PASS') for row in cases)
if counts!={'PASS':31}:raise ValueError('VERIFIER_TEST_RESULT_MISMATCH')
runtime=json.loads((OUT/'CAPACITY_DETAIL_7cb0ad62_RESULT.json').read_bytes())
if runtime['status']!='SCOPED_CONTENT_ORACLE_PASS' or len(runtime['rows'])!=2:raise ValueError('RUNTIME_RESULT_MISMATCH')
sources=['src/workbench_db/v4_snapshot_pg_r2.py','scripts/audit_r4_r3_capacity_detail.py']
receipt=dict(contract_id='R4_R3_CAPACITY_AND_COMPLETE_CONTENT_VERIFIER_SEAL_R3',
    base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    source_sha256={p:sha(ROOT/p) for p in sources},independent_counts=dict(counts),evidence=records,
    runtime_result='CAPACITY_DETAIL_7cb0ad62_RESULT.json',closure='Full-content integrity and two-T0 workload execution only',
    capacity_acceptance='OPEN_NO_APPROVED_THRESHOLD',full_legal_denominator='OPEN',all_56_consumers='OPEN',production_changed=False)
(OUT/'CAPACITY_VERIFIER_SEAL_R3.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(counts=dict(counts),sealed_files=len(records))))
