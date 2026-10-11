"""Independent raw JUnit recount and lossless evidence seals."""
from pathlib import Path
import gzip,hashlib,json,subprocess,xml.etree.ElementTree as ET
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
files=[]
for prefix in ('FEP_CANONICAL_EXECUTION_R1','FEP_CANONICAL_EXECUTION_R2','FEP_CANONICAL_EXECUTION_R3','FEP_CANONICAL_DRILLS_R1','FEP_CANONICAL_DRILLS_R2'):
    for path in sorted(OUT.glob(prefix+'*')):
        if path.suffix=='.gz':continue
        raw=path.read_bytes();compressed=gzip.compress(raw,mtime=0)
        target=path.with_name(path.name+'.gz')
        if target.exists() and gzip.decompress(target.read_bytes())!=raw:raise ValueError('EXISTING_EVIDENCE_SEAL_CONFLICT')
        if not target.exists():target.write_bytes(compressed)
        files.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=sha(raw),lossless_gzip=target.relative_to(ROOT).as_posix(),gzip_sha256=sha(target.read_bytes())))
cases=ET.parse(OUT/'FEP_CANONICAL_EXECUTION_R3.xml').findall('.//testcase')
counts=Counter(next((label for tag,label in [('failure','FAIL'),('error','ERROR'),('skipped','SKIP')] if case.find(tag) is not None),'PASS') for case in cases)
if counts!={'PASS':263}:raise ValueError('CANONICAL_SCOPED_RESULT_NOT_PASS')
sources=['scripts/run_fep_e5_r1r1b.py','scripts/prepare_r4_r3_fep_fixtures.py','scripts/run_r4_r3_canonical_drills.py','tests/v4_native_isolation_plugin_r4.py','tests/fep_e5/test_e5_reconstruction.py','tests/fep_e5/test_e5_metadata_binding.py','tests/fep_e5/test_canonical_authority_read.py']
value=dict(contract_id='R4_R3_CANONICAL_SCOPED_EXECUTION_SEAL_R1',base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),actual_source_sha256={p:sha((ROOT/p).read_bytes()) for p in sources},independent_junit_counts=dict(counts),raw_case_records=len(cases),evidence=files,production_changed=False,REAL_OOS=False,FIRST_OBSERVED=False,global_engineering_state='OPEN',closure='Only canonical reconstruction/metadata/authority scope; full legal baseline and other consumers remain OPEN')
(OUT/'FEP_CANONICAL_SCOPED_SEAL_R1.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(counts=dict(counts),sealed_files=len(files))))
