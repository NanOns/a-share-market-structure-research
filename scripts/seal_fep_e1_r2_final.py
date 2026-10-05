"""Derive E1 engineering candidate exit from exact local gates; no acceptance grant."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from scripts.validate_r25_preflight import protected,selection
from workbench_analysis.fep_e1.contracts import atomic_json

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/fep_e1_r2_final'


def read(name):return json.loads((REPORT/name).read_bytes())


def binding(path):
    raw=path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def run():
    entry=read('ENTRY_BASELINE.json')
    for ref in entry['protected']+entry['pass_keep']:
        assert binding(ROOT/ref['path'])==ref,ref['path']
    for name in ('FEATURE_OWNER_ADAPTER_GATE.json','ENGINEERING_SNAPSHOT_READBACK.json','PASS_KEEP_DATABASE_READBACK.json'):
        assert read(name)['status']=='PASS',name
    targeted=read('TARGETED_SUMMARY.json');regression=read('SCOPED_REGRESSION_SUMMARY.json')
    assert not regression['introduced_active_failures'] and regression['full_final_run']
    assert all(not v['exit_code'] for v in targeted['databases'].values())
    assert read('REAL_FIRST_OBSERVED_GATE.json')['status']=='NOT_GRANTED_WAIT_REAL_SESSION'
    successor_cases=[c for c in ET.parse(REPORT/'repair_unit.xml').findall('.//testcase')
                     if c.attrib['classname']=='tests.fep.test_v4_18_namespace_successor']
    assert len(successor_cases)==2 and all(c.find('failure') is None and c.find('error') is None for c in successor_cases)
    atomic_json(REPORT/'V4_18_V1_1_SUCCESSOR_TEST_GATE.json',dict(status='PASS',
                test='tests/fep/test_v4_18_namespace_successor.py',current_sql_inventory_complete=True,
                fep_declarations=33,predecessor_unchanged=True,migration_execution='NOT_GRANTED',production_cutover=False,accepted_head='NOT_CREATED'))
    atomic_json(REPORT/'R25_WAIT_READBACK.json',dict(status='PASS',protected=protected(ROOT),selection=selection(ROOT)))
    atomic_json(REPORT/'INDEPENDENT_AUDIT_ITEMS.json',dict(items=[
        dict(audit_id='FEP_E1_FEATURE_MAPPING_CONTRACT_CONFLICT',status='CLOSED_ENGINEERING_SCOPE_BY_R2_AUTHORITY',
             scope='Historical/reconstructed 47-field owner adapter; real current admission remains separate',
             evidence='FEATURE_47_FIELD_READBACK.json',acceptance='5222 exact historical owner rows x 47 envelopes; real FIRST_OBSERVED NOT_GRANTED'),
        dict(audit_id='FEP_E1_R1_R25_HISTORICAL_GUARD_CONTRACT_CONFLICT',status='CLOSED_LOCAL',
             scope='Restore exact pre-FEP test; successor test is additive',evidence='R25_WAIT_READBACK.json',
             acceptance='protected PASS, WAIT and both acceptance-seal/current-state tests pass in full run'),
        dict(audit_id='FEP_E1_LEGACY_MIGRATION_REGISTRATION_GAP',status='OPEN_EXISTING_INFRASTRUCTURE_DEBT',
             scope='Historical 014..027 registration',evidence='../fep_e1/INDEPENDENT_AUDIT_ITEMS.json',acceptance='Separate owner repair'),
        dict(audit_id='FEP_E1_BASELINE_52_FAILURES',status='OPEN_EXISTING_OWNER_DEBT',
             scope='43 registered plus 9 independently reproduced baseline failures',evidence='SCOPED_REGRESSION_SUMMARY.json',
             acceptance='Not relabeled E1 PASS; separate owner-stage remediation')]))
    result=dict(V4_15E1_R2_FINAL_RECONCILIATION='PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',
                V4_15E1_FEP_LOCAL_IMPLEMENTATION='PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',
                FEP_DATABASE_ENGINEERING='PASS_LOCAL',FEP_DATASET_ENGINEERING='PASS_LOCAL_ENGINEERING',
                FEP_FEATURE_MAPPING='47_OF_47_ENGINEERING_READY',FEP_FEATURE_MAPPING_ENGINEERING='PASS',FEP_FEATURE_COUNT=47,
                FEP_REAL_FIRST_OBSERVED_ENTRY='NOT_GRANTED_WAIT_REAL_SESSION',FEP_REAL_MATURED_LABEL_EVIDENCE='NOT_GRANTED',
                R25='WAIT_ACCEPTED_DAILY_INPUT',introduced_active_failures=0,FEP_MODEL_ENGINEERING='NOT_STARTED',
                FEP_MODEL_DISPLAY='UNGRANTED',FEP_PRIORITY_USE='UNGRANTED',FEP_PRODUCTION='UNGRANTED',
                E2='NOT_AUTHORIZED_UNTIL_EXTERNAL_AUDIT',NEXT='STOP_WAIT_FINAL_E1_EXTERNAL_AUDIT')
    atomic_json(REPORT/'LOCAL_ACCEPTANCE_MATRIX.json',result)
    atomic_json(REPORT/'PROTECTED_STATE_READBACK.json',dict(status='PASS',heads=entry['protected'],
                pass_keep=entry['pass_keep'],Production=False,Shadow=False,Focus=False,
                FEP_E1_ACCEPTED_HEAD='NOT_CREATED',V4_16_ACCEPTED_HEAD='NOT_CREATED',PRIORITY_V1='UNCHANGED'))
    f=targeted['databases']['fep_e1_fresh'];u=targeted['databases']['fep_e1_upgrade']
    text=f'''# FEP E1 R2 final reconciliation

Baseline: `7474fb25c93286b0224635b77033451a81955ae1`.
Authority: `V4_15E1_R2_FINAL_OWNER_AND_GOVERNANCE_REPAIR_TASK_20261005.md`.

**PASS_LOCAL_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT**.
Next: **STOP_WAIT_FINAL_E1_EXTERNAL_AUDIT**. E2 remains unauthorized.

Path A uses the exact accepted historical V4-03 full-scope owner dated
2026-09-24. Its 5222 rows contain all 47 accepted field envelopes. The adapter
copies values, quality, source/input digests and window identities without
factor formulas or aliases. All seven relative/RPS fields are present in the
accepted historical owner. UNKNOWN remains an explicit envelope, never imputed.
The existing incomplete 2026-09-30 owner is not rewritten or promoted.

One reproducible engineering observation/snapshot consumes the 47-field adapter.
Its exact dependency manifest binds the owner head/artifact, source row digest,
algorithm/parameter/feature contracts, calendar, universe and adjustment source
identities. Binary upstream inputs are exact-hash checked and bound through
readback receipts. RECONSTRUCTED_ASOF/REPLAY only; AS_RECORDED/FIRST_OBSERVED=false.
The local capture receipt proves present engineering readability; it does not
substitute wall-clock time for historical first availability. The engineering
slot ceiling is a read boundary; prediction/model deadlines remain disabled.
Repeated reads of the same capture give the same feature digest.

The original V4-18 test was restored to git blob
`26369110c8ea35b9c1d216df17d11f981047fcef`. V1 and V1.1 contract bytes remain
unchanged. A new additive successor test covers all current SQL declarations,
including 33 explicit FEP REFERENCE engineering declarations. V4-18 execution,
production cutover and accepted head remain ungranted/absent.
The exact obsolete V1 inventory node is registered SUPERSEDED_PRE_FEP_NAMESPACE_ASSERTION,
and is not counted as PASS. No R25 preflight or dependency bytes were patched.
protected() passes and selection() returns WAIT_ACCEPTED_DAILY_INPUT.

Minimal real PostgreSQL replay/readback retains unchanged 028–031 migrations,
33 tables, 32 guards, role/search_path, CAS/rollback/idempotency and equal
fresh/upgrade schema identities. No database rebuild was performed.
Fresh targeted: {f['passed']} passed / {f['skipped']} skipped / 0 failures.
Upgrade targeted: {u['passed']} passed / {u['skipped']} skipped / 0 failures.
Full final scoped regression after all changes: {regression['passed']} passed,
{regression['skipped']} skipped, {len(regression['current_failed_nodes'])} existing failures,
0 introduced active failures. Existing debt: 43 registered + 9 independently
reproduced baseline nodes. The only two deselections are the governed pre-seal
R4 assertion and the newly governed pre-FEP V1 inventory assertion.
Raw logs/XML and exact candidate bindings are retained.

Current real labels remain pending, CURRENT_REAL_MATURITY_EVIDENCE=NONE,
PROVED_HORIZONS=[]. The three-time authority and raw external design receipt
remain exact PASS_KEEP. No label recomputation, real training binding, model
training, production/Shadow/Focus or model display/priority grant occurred.
Accepted Stage/Data/owner heads are unchanged; FEP E1/V4-16 heads were not created.
TDX is read-only and untouched. Isolated E: PostgreSQL instances are stopped,
with data and raw logs retained. Unrelated untracked work is preserved.
'''
    tmp=REPORT/'COMPLETION_REPORT.md.tmp';tmp.write_text(text,encoding='utf8',newline='\n');os.replace(tmp,REPORT/'COMPLETION_REPORT.md')
    atomic_json(REPORT/'COMPLETION_EXIT.json',result)
    names=['config/fep_feature_owner_contract_v1.json','src/workbench_analysis/fep_e1/feature_owner.py',
           'scripts/build_fep_e1_r2_engineering_owner.py','scripts/run_fep_e1_r2_retest.py',
           'scripts/seal_fep_e1_r2_final.py','tests/fep/test_feature_owner.py',
           'tests/fep/test_v4_18_namespace_successor.py','tests/test_v4_18_migration_contract.py']
    paths=[ROOT/n for n in names]+[p for p in REPORT.rglob('*') if p.is_file()
                    and p.name!='FEP_E1_R2_CANDIDATE_SEAL.json' and not p.name.endswith('.tmp')]
    atomic_json(REPORT/'FEP_E1_R2_CANDIDATE_SEAL.json',dict(
                contract_id='FEP_E1_R2_CANDIDATE_SEAL_V1',baseline=entry['baseline'],
                status=result['V4_15E1_R2_FINAL_RECONCILIATION'],external_accepted=False,
                permissions=dict(production=False,shadow=False,focus=False,model_display=False,priority_use=False),
                next=result['NEXT'],evidence_and_implementation=[binding(p) for p in sorted(set(paths))]))


if __name__=='__main__':run()
