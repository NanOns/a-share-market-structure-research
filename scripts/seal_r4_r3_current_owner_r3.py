"""Seal exact current-owner regression and unrestricted input-recovery evidence."""
from pathlib import Path
from collections import Counter
import hashlib,gzip,json,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/audits/r4_r3_scope_20261011'
def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):value.update(block)
    return value.hexdigest()
files=[]
for prefix in ('V413_CURRENT_OWNER_R1','V413_CURRENT_OWNER_R2','V413_CURRENT_OWNER_R3','UNLIMITED_RECOVERY_R1','UNLIMITED_OWNER_INPUT_RECOVERY_R1'):
    files.extend(p for p in OUT.glob(prefix+'*') if p.suffix!='.gz')
seals=[]
files.append(OUT/'FROZEN_FIXTURE_COPY_RECEIPT_20261011T135139.json')
files.append(OUT/'FROZEN_FIXTURE_COPY_RECEIPT_20261011T133620.json')
for source in sorted(set(files)):
    destination=source.with_name(source.name+'.gz')
    if not destination.exists():
        with source.open('rb') as origin,destination.open('xb') as target:
            with gzip.GzipFile(fileobj=target,mode='wb',mtime=0) as compressed:
                for block in iter(lambda:origin.read(1048576),b''):compressed.write(block)
    value=hashlib.sha256()
    with gzip.open(destination,'rb') as compressed:
        for block in iter(lambda:compressed.read(1048576),b''):value.update(block)
    if value.hexdigest()!=sha(source):raise ValueError('RAW_SEAL_CONFLICT')
    seals.append(dict(raw=source.relative_to(ROOT).as_posix(),sha256=sha(source),bytes=source.stat().st_size,
        lossless=destination.relative_to(ROOT).as_posix(),lossless_sha256=sha(destination)))
counts={}
for name,expected in [('V413_CURRENT_OWNER_R3',49),('UNLIMITED_RECOVERY_R1',1)]:
    rows=ET.parse(OUT/(name+'.xml')).findall('.//testcase')
    counts[name]=dict(Counter(next((label for tag,label in [('failure','FAIL'),('error','ERROR'),('skipped','SKIP')] if row.find(tag)is not None),'PASS') for row in rows))
    if counts[name]!={'PASS':expected}:raise ValueError('SCOPED_EXPECTED_COUNTS_MISMATCH')
sources=['src/workbench_analysis/v4_13_accepted_contract_package.py','src/workbench_analysis/v4_13_descendant_contracts.py',
    'scripts/hydrate_r4_r3_scope_fixtures.py','tests/test_v4_current_owner_contracts_r3.py','tests/test_r4_r3_input_recovery.py']
receipt=dict(contract_id='R4_R3_CURRENT_OWNER_AND_UNLIMITED_RECOVERY_SCOPED_SEAL_R3',
    base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    sources={p:sha(ROOT/p) for p in sources},independent_raw_counts=counts,evidence=seals,
    numerical_reference='Original 45 literal projection/provenance/independent-category tests retained; four current-authority negatives added',
    input_reference='Actual 101 MiB source copy compared by complete independent SHA, existing conflicting accepted file unchanged',
    closure='Current V4-13 owner entry beneath verified V4-14/15 authority and removal of imposed copy-size caps only',
    full_legal_denominator='OPEN',full_source_derivation='RUNNING_NOT_ACCEPTED',full_56_consumers='OPEN',production_changed=False)
(OUT/'CURRENT_OWNER_AND_UNLIMITED_RECOVERY_SEAL_R3.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
print(json.dumps(counts))
