"""Seal bounded real-input corrections without closing the whole V4 audit."""
from pathlib import Path
import gzip,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_consumers_20261011/EXACT_CORE_REGRESSION_PACKAGE_R1'
OUT.mkdir(exist_ok=False)
paths=['config/v4_operational_core_exact_candidate_r3.json','src/workbench_analysis/exact_operational_core_candidate_r3.py',
 'src/workbench_analysis/native_source_reconciliation_r3.py','src/workbench_analysis/operational_daily_executor_v1.py',
 'src/workbench_analysis/operational_daily_ready_owner_v2.py','src/workbench_analysis/operational_owner_adapter_v1.py',
 'src/workbench_analysis/r43_owner_replay.py','src/workbench_analysis/r43_focus_replay.py',
 'scripts/run_r4_r3_actual_source_derivation.py','scripts/audit_r4_r3_full_core_history.py',
 'scripts/check_r4_r3_actual_rounding_regressions.py','scripts/r4_r3_consumer_trace.py',
 'tests/test_v4_exact_operational_core_r3.py','tests/test_v4_native_source_scope_r3.py']
evidence=['SOURCE_DERIVATION_R12/FULL_HISTORY_INDEPENDENT_R1.json','ACTUAL_80_ROUNDING_REGRESSIONS_R1.json',
 'ACTUAL_80_ROUNDING_REGRESSIONS_R1_RAW.log','EXACT_OPERATIONAL_CORE_R1.xml','EXACT_OPERATIONAL_CORE_R2.xml',
 'EXACT_OPERATIONAL_CORE_R3.xml','EXACT_OPERATIONAL_CORE_R3_RAW.log','SOURCE_DERIVATION_R12/RESULT.json',
 'SOURCE_DERIVATION_R12_RAW.log','NATIVE_SOURCE_SCOPE_R5.xml']
def sha(blob):return hashlib.sha256(blob).hexdigest()
records=[]
for relative in evidence:
    path=OUT.parent/relative;blob=path.read_bytes()
    destination=OUT/(relative.replace('/','__')+'.gz')
    packed=gzip.compress(blob,mtime=0);destination.write_bytes(packed)
    if gzip.decompress(packed)!=blob:raise ValueError('LOSSLESS_EVIDENCE_FAILED')
    records.append(dict(original=str(path.relative_to(ROOT)),raw_sha256=sha(blob),raw_bytes=len(blob),
        archive=str(destination.relative_to(ROOT)),archive_sha256=sha(packed)))
candidate=json.loads((OUT.parent/'ACTUAL_80_ROUNDING_REGRESSIONS_R1.json').read_bytes())
if candidate['status']!='SCOPED_PASS' or candidate['denominator']!=80:raise ValueError('ACTUAL_REGRESSION_GATE_FAILED')
result=dict(contract='R4_R3_EXACT_CORE_REAL_INPUT_CORRECTION_PACKAGE_R1',
    parent_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    source_files=[dict(path=p,sha256=sha((ROOT/p).read_bytes())) for p in paths],raw_evidence=records,
    bounded_conditions=dict(all_retained_80_failures_reproduced=True,all_four_candidate_prices_independently_checked=True,
        literal_and_adversarial_tests=11,source_scope_tests=10,old_failures_retained=True,production_unchanged=True),
    bounded_acceptance='SCOPED_REAL_INPUT_ROUNDING_REGRESSIONS_PASS',
    full_history_candidate_acceptance='OPEN_RUNNING_R13',full_legal_denominator='OPEN',all_56_consumers='OPEN',
    all_semantic_gates='OPEN',postgresql_all_entrances='OPEN',external_acceptance='BLOCKED',
    remaining_engineering=['Complete R13 actual consumers and independent full history oracle','Resolve all retained full-baseline failures and certify full legal denominator','Complete live PostgreSQL consumers and whole semantics'],
    separate_external_gates=['Contemporaneous real trading-day capture','Mature sample windows','Explicit deployment authorization'])
(OUT/'SEAL.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(acceptance=result['bounded_acceptance'],evidence_archives=len(records))))
