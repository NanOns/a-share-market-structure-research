"""Retain full failures and certify only the 77/20 original-node fixture repairs."""
from pathlib import Path
import gzip,hashlib,json,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'docs/audits/r4_r3_scope_20261011'
OUT=BASE/'NATIVE_FIXTURE_REPAIR_PACKAGE_R1';OUT.mkdir(exist_ok=False)
full='V4_BASELINE_FULL_GUARDED_20261011T214750'
def sha(blob):return hashlib.sha256(blob).hexdigest()
def nodes(path):
    return {c.get('classname')+'::'+c.get('name'):('FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS') for c in ET.parse(path).findall('.//testcase')}
baseline=nodes(BASE/(full+'.xml'));closures=[]
for name,count in [('V413_NORMAL_GIT_ENV_R4',77),('FEP_SIGNAL_NATIVE_R4',20)]:
    current=nodes(BASE/(name+'.xml'));modules={n.split('::')[0] for n in current}
    original={n for n in baseline if n.split('::')[0] in modules}
    if set(current)!=original or len(current)!=count or any(s!='PASS' for s in current.values()):raise ValueError('ORIGINAL_FULL_MODULE_DENOMINATOR_NOT_PASSED')
    closures.append(dict(evidence=name,original_nodes=count,missing=[],extra=[],all_passed=True))
negative=json.loads((BASE/'FEP_SIGNAL_PRODUCTION_NEGATIVE_R4_RESULT.json').read_bytes())
if negative['exit_code']!=3 or 'R3_EXACT_ENGINEERING_FIXTURE_PREDECESSOR_REQUIRED' not in (BASE/'FEP_SIGNAL_PRODUCTION_NEGATIVE_R4_RAW.log').read_text():raise ValueError('PRODUCTION_CAPABILITY_NEGATIVE_NOT_OBSERVED')
names=[full+'.xml',full+'.log',full+'_RESULT.json',full+'_SOURCE_BINDINGS.json',full+'_INDEPENDENT_RESULT.json',
 'FEP_SIGNAL_NATIVE_R1_RAW.log','FEP_SIGNAL_NATIVE_R2_RAW.log','FEP_SIGNAL_NATIVE_R3.xml','FEP_SIGNAL_NATIVE_R3_RAW.log',
 'FEP_SIGNAL_NATIVE_R4.xml','FEP_SIGNAL_NATIVE_R4_RAW.log','FEP_SIGNAL_NATIVE_R4_INTENTS.jsonl',
 'V413_NORMAL_GIT_ENV_R4.xml','V413_NORMAL_GIT_ENV_R4_RAW.log','V413_NORMAL_GIT_ENV_R4_INTENTS.jsonl',
 'FEP_SIGNAL_PRODUCTION_NEGATIVE_R3_RAW.log','FEP_SIGNAL_PRODUCTION_NEGATIVE_R4_RAW.log','FEP_SIGNAL_PRODUCTION_NEGATIVE_R4_RESULT.json',
 'FEP_SIGNAL_BASELINE32_FIXTURE_RECEIPT_R1.json','FEP_SIGNAL_BASELINE32_MARKER_RECEIPT_R1.json','FEP_SIGNAL_ACTUAL_FRESH_BASELINE32_RECEIPT_R1.json']
records=[]
for name in names:
    blob=(BASE/name).read_bytes();packed=gzip.compress(blob,mtime=0);path=OUT/(name+'.gz');path.write_bytes(packed)
    if gzip.decompress(packed)!=blob:raise ValueError('LOSSLESS_RAW_EVIDENCE_REQUIRED')
    records.append(dict(original=name,raw_sha256=sha(blob),raw_bytes=len(blob),archive=path.name,archive_sha256=sha(packed)))
sources=['tests/test_full_chain_fep_db.py','tests/v4_native_isolation_plugin_r4.py','scripts/run_fep_e5_r1r1b.py',
 'scripts/prepare_r4_r3_signal_baseline_fixtures.py','scripts/mark_r4_r3_signal_baseline_fixtures.py','scripts/prepare_r4_r3_actual_fresh_signal_fixture.py']
result=dict(contract='R4_R3_ORIGINAL_NATIVE_FIXTURE_REPAIR_PACKAGE_R1',parent_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    source_files=[dict(path=p,sha256=sha((ROOT/p).read_bytes())) for p in sources],scoped_closures=closures,
    negative_production_grant_rejected=negative,raw_evidence=records,full_baseline_counts=dict(PASS=4487,FAIL=201,ERROR=98,SKIP=3),
    preserved_original_baseline_nodes=4568,original_nodes_in_full_run=4567,exact_legacy_ast_deselected=1,
    bounded_acceptance='ORIGINAL_77_PLUS_20_FIXTURE_MATRIX_PASS',full_legal_denominator='OPEN',all_56_consumers='OPEN',all_semantics='OPEN',
    full_system_acceptance='EXTERNAL_ACCEPTANCE_BLOCKED',production_changed=False,
    limitations=['77-node repair is an environment-scope correction, not new numerical acceptance.','20-node matrix uses native engineering 032 baselines cloned separately from actual fresh and upgrade sources.','All 201 full-run failures and 98 errors remain in raw evidence; later scoped fixes do not retroactively change full-run outcomes.'])
(OUT/'SEAL.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(acceptance=result['bounded_acceptance'],raw_archives=len(records))))
