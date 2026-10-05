"""Seal measured E1R1 output; incomplete owner evidence cannot produce PASS."""
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

from workbench_analysis.fep_e1.contracts import atomic_json

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/fep_e1_r1_repair'


def read(name):
    return json.loads((REPORT / name).read_bytes())


def binding(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest())


def run():
    regression = read('SCOPED_REGRESSION_SUMMARY.json')
    targeted = read('TARGETED_TEST_SUMMARY.json')
    feature = read('FEATURE_OWNER_MAPPING_GATE.json')
    cases = ET.parse(REPORT/'repair_unit.xml').findall('.//testcase')
    assert all(c.find('failure') is None and c.find('error') is None for c in cases)
    atomic_json(REPORT/'LABEL_TIME_NEGATIVE_MATRIX.json', dict(
        status='PASS_ENGINEERING', evidence_class='ENGINEERING_FIXTURE',
        vectors=[dict(node=c.attrib['classname']+'::'+c.attrib['name'],status='PASS')
                 for c in cases if 'test_r1_label_time' in c.attrib['classname']]))
    time_gate=read('LABEL_TIME_AUTHORITY_GATE.json')
    time_gate.update(status='PASS_ENGINEERING',negative_matrix=binding(REPORT/'LABEL_TIME_NEGATIVE_MATRIX.json'))
    atomic_json(REPORT/'LABEL_TIME_AUTHORITY_GATE.json',time_gate)
    atomic_json(REPORT/'TARGETED_SUMMARY.json', targeted)
    database = read('PASS_KEEP_DATABASE_READBACK.json')
    database['fresh_upgrade'] = targeted
    atomic_json(REPORT/'PASS_KEEP_DATABASE_READBACK.json',database)
    matrix = dict(WP_A='PASS_EXACT_RAW_EXTERNAL_DESIGN_RECEIPT',
                  WP_B='BLOCKED_FEP_E1_FEATURE_MAPPING_CONTRACT_CONFLICT',
                  WP_C='PASS_ENGINEERING_FAIL_CLOSED_REAL_PENDING',
                  WP_D='PASS_NAMESPACE_SUCCESSOR_NO_MIGRATION_GRANT',
                  PASS_KEEP_DATABASE='PASS_LOCAL_ISOLATED_ENGINEERING',
                  SCOPED_REGRESSION=regression['status'],
                  introduced_active_failures=regression['introduced_active_failures'],
                  V4_15E1_R1_REPAIR='BLOCKED', V4_15E1_FEP_LOCAL_IMPLEMENTATION='BLOCKED',
                  FEP_DATABASE_ENGINEERING='PASS_LOCAL_ISOLATED_ENGINEERING',
                  FEP_DATASET_ENGINEERING='BLOCKED_REAL_FEATURE_OWNER_AUTHORITY',
                  FEP_STOCK_ENTRY_CORE_DATA_PATH='NOT_READY_REAL_ADMISSION',
                  FEP_E1_FEATURE_MAPPING_COMPLETE='BLOCKED',
                  FEP_E1_DATASET_COMPLETE_FEATURE_SIDE=False,
                  FEP_REAL_MATURED_LABEL_EVIDENCE='NOT_GRANTED',
                  FEP_MODEL_ENGINEERING='NOT_STARTED',FEP_MODEL_DISPLAY='UNGRANTED',
                  FEP_PRIORITY_USE='UNGRANTED',FEP_PRODUCTION='UNGRANTED',
                  E2='NOT_AUTHORIZED',NEXT='STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION')
    atomic_json(REPORT/'LOCAL_ACCEPTANCE_MATRIX.json',matrix)
    atomic_json(REPORT/'INDEPENDENT_AUDIT_ITEMS.json',dict(items=[
        dict(audit_id='FEP_E1_FEATURE_MAPPING_CONTRACT_CONFLICT',status='OPEN_BLOCKING_P0',
             scope='47-field current ENTRY accepted owner admission',
             evidence='FEATURE_MAPPING_CONTRACT_CONFLICT.json',acceptance='47/47 exact owner mappings'),
        dict(audit_id='FEP_E1_R1_R25_HISTORICAL_GUARD_CONTRACT_CONFLICT',status='OPEN_CROSS_STAGE_BLOCKING',
             scope='R25 historical guard and exact-bound dependency successor',
             evidence='R25_HISTORICAL_GUARD_CONTRACT_CONFLICT.json',acceptance='Zero introduced regression failures with original WAIT and permissions preserved'),
        dict(audit_id='FEP_E1_CONTRACT_CONFLICT_THREE_TIME_SOURCE',status='CLOSED_ENGINEERING_REAL_PENDING',
             scope='Additive label time authority, no real maturity grant',evidence='LABEL_TIME_AUTHORITY_GATE.json',
             acceptance='T2/T5/T6 PIT and negative matrix PASS; real pending creates no binding'),
        dict(audit_id='FEP_E1_CONTRACT_CONFLICT_V4_18_NAMESPACE_INVENTORY',status='CLOSED_LOCAL',
             scope='33 explicit FEP declarations in versioned successor',evidence='V4_18_NAMESPACE_SUCCESSOR_GATE.json',
             acceptance='Undeselected inventory test PASS; V1 unchanged and no V4-18 execution grant'),
        dict(audit_id='FEP_E1_EXTERNAL_DESIGN_RAW_RECEIPT',status='CLOSED_EXACT_RAW',
             scope='External design evidence provenance',evidence='EXTERNAL_DESIGN_RECEIPT_READBACK.json',
             acceptance='14019 bytes / cd279e26... exact receipt'),
        dict(audit_id='FEP_E1_LEGACY_MIGRATION_REGISTRATION_GAP',status='OPEN_EXISTING_INFRASTRUCTURE_DEBT',
             scope='Historical 014..027 registration',evidence='../fep_e1/INDEPENDENT_AUDIT_ITEMS.json',
             acceptance='Separately scoped owner repair; not changed by E1R1'),
        dict(audit_id='FEP_E1_BASELINE_52_FAILURES',status='OPEN_EXISTING_OWNER_DEBT',
             scope='43 registered plus 9 independently reproduced baseline failures',
             evidence='SCOPED_REGRESSION_SUMMARY.json',acceptance='Separate owner-stage acceptance')]))
    fresh = targeted['databases']['fep_e1_fresh']
    upgrade = targeted['databases']['fep_e1_upgrade']
    report = f'''# FEP E1R1 blocker repair completion

Baseline: `e4ea913d8926e904e55cbf16993ec63c0e90b031`.
Task: `V4_15E1_R1_BLOCKER_REPAIR_TASK_20261005.md`.

Local exit: **BLOCKED**. Next: **STOP_WAIT_EXTERNAL_REPAIR_DISPOSITION**.
This delivery does not grant external acceptance or E2 entry.

WP-A closed: formal external design receipt copied exactly, 14019 bytes and SHA256
`cd279e26fb9753eb1e333c7554f9f06393c9232ee44ff7be6d86e2f2f65d178e`.
Original candidate seal retained and receipt bindings updated.

WP-B remains blocked. Historical V4-03 paths exist for all 47 fields. Explicit
current sealed Core owner inventory covers 5224 rows and proves 40 reconstructed
value/quality/digest/window/available_at paths. Missing current fields:
{', '.join(feature['current_core_missing_fields'])}.
V4-12 explicitly marks rel_market_1 UNKNOWN because the exact target-date V4-03
factor publication is not bound. Reconstructed engineering owner inputs cannot
manufacture current FIRST_OBSERVED ENTRY identity. No aliases, latest/mtime
availability, reduced field contract, or incomplete real snapshot was admitted.
Discovery samples of other owners are identified as samples, not full-market
proof. Full inventory proof covers the exact current Core owner artifact.

WP-C closed for engineering: versioned additive V4-15 label-time authority and
adapter use exact allocated row/receipt identities. Source time consumes every
registered fact, maturity requires full window and quality, revision visibility
is independently enforced. T3 and T5 reject; T6 admits the isolated fixture.
The five current real pending rows have NOT_PROVEN times and no training binding.
CURRENT_REAL_MATURITY_EVIDENCE=NONE; PROVED_HORIZONS=[]. No label recomputation.

WP-D namespace inventory closed: immutable V1 retained, V1.1 explicitly adds all
33 FEP declarations as REFERENCE engineering namespace, no migration/cutover
grant. The original inventory test reads the successor and passes undeselected.

A newly exposed cross-stage conflict remains: R25 protects all historical tracked
bytes, including the exact V4-18 test that this task authorizes changing. Its
preflight source is itself exact-bound; an in-place guard patch was not retained.
Independent audit item FEP_E1_R1_R25_HISTORICAL_GUARD_CONTRACT_CONFLICT records the
exact cause and requires versioned owner reconciliation. No old V4-16 dependency
or accepted head was rewritten to hide this failure.

Validation: fresh PostgreSQL {fresh['passed']} passed / {fresh['skipped']} skipped;
upgrade {upgrade['passed']} passed / {upgrade['skipped']} skipped. 33 tables,
32 immutable guards, role/search_path/CAS concurrency/rollback and existing
40 negative-vector semantics remain verified; migrations 028–031 unchanged.
Repair unit/static gate: {len(cases)} passed.
Scoped regression: {regression['passed']} passed, {regression['skipped']} skipped,
{len(regression['full_run_failed_nodes'])} full-run failures. A focused governance
retest closes the sample-identity-in-config failure after moving sample records
to evidence. Active failures: {len(regression['current_failed_nodes'])}, including
52 existing debts. Full-run counts are retained without fabricating a full rerun.
Introduced active nodes: {regression['introduced_active_failures']}.
Only the previously governed superseded R4 node remains deselected.

All protected accepted heads retain exact bytes. Production/Shadow/Focus=false;
MODEL_DISPLAY/PRIORITY_USE/FEP_PRODUCTION=UNGRANTED. E1/V4-16 accepted heads absent.
The two new PostgreSQL instances are isolated on E:, stopped after evidence capture;
data and raw logs retained. Main fresh/upgrade FEP tables remain empty. TDX untouched.

Evidence: LOCAL_ACCEPTANCE_MATRIX.json, SCOPED_REGRESSION_SUMMARY.json,
PASS_KEEP_DATABASE_READBACK.json, FEATURE_MAPPING_CONTRACT_CONFLICT.json,
R25_HISTORICAL_GUARD_CONTRACT_CONFLICT.json and candidate seal in this directory.
'''
    tmp=REPORT/'COMPLETION_REPORT.md.tmp'
    tmp.write_text(report,encoding='utf8',newline='\n')
    os.replace(tmp,REPORT/'COMPLETION_REPORT.md')
    atomic_json(REPORT/'COMPLETION_EXIT.json',matrix)
    names=['config/fep_feature_source_map_v1.json','config/fep_entry_observation_timing_v1.json','config/v4_15_fep_label_time_authority_v1.json',
           'config/v4_18_migration_replay_contract_v1_1.json','src/workbench_analysis/v4_15_fep_label_time.py',
           'src/workbench_analysis/fep_e1/labels.py','tests/fep/test_r1_label_time.py',
           'tests/test_v4_18_migration_contract.py','scripts/readback_fep_e1_r1_repair.py',
           'scripts/run_fep_e1_r1_retest.py','scripts/seal_fep_e1_r1_repair.py',
           'reports/fep_e1/DESIGN_AUTHORITY_READBACK.json','reports/fep_e1/FEP_E1_CANDIDATE_SEAL.json',
           'docs/evidence/fep_e1/V4_2_2_FEP_R2_EXTERNAL_DESIGN_ACCEPTANCE_20260930.md']
    paths=[ROOT/n for n in names]+[p for p in REPORT.rglob('*') if p.is_file()
            and p.name!='FEP_E1_R1_REPAIR_CANDIDATE_SEAL.json' and not p.name.endswith('.tmp')]
    atomic_json(REPORT/'FEP_E1_R1_REPAIR_CANDIDATE_SEAL.json',dict(
        contract_id='FEP_E1_R1_REPAIR_CANDIDATE_SEAL_V1',baseline='e4ea913d8926e904e55cbf16993ec63c0e90b031',
        status='BLOCKED', external_accepted=False, dataset_complete=False,
        permissions=dict(production=False,shadow=False,focus=False,model_display=False,priority_use=False),
        next=matrix['NEXT'],evidence_and_implementation=[binding(p) for p in sorted(set(paths))]))


if __name__ == '__main__':
    run()
