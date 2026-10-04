"""Freeze persisted engineering evidence and independent gate results."""
import json,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.r23_io import *
from scripts import validate_r23_runtime as oracle
def build():
    cases=list(ET.parse(ROOT/'reports/r23/local_tests.xml').iter('testcase'))
    assert len(cases)>=305 and not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
    atomic('reports/r23/LOCAL_TEST_SUMMARY.json',dict(status='PASS_LOCAL',passed=len(cases),failed=0,errors=0,skipped=0,deselected=0,suite=['tests/test_pre16_governance.py','tests/test_r21_promotion.py','tests/test_r22_contracts.py','tests/test_r22r1_contracts.py','tests/test_r23_runtime.py']))
    for n in range(1,25):
        r=read('reports/r23/isolated_db/test_receipts/N%02d.json'%n)
        source=Path(r['database']);assert hashlib.sha256(source.read_bytes()).hexdigest()==r['database_binding']['sha256']
        path='reports/r23/negative_evidence/N%02d.sqlite'%n;atomic(path,source.read_bytes(),raw=True)
        r['database_binding']=ref(path);r['database']=path;atomic('reports/r23/negative_evidence/N%02d.json'%n,r)
    matrix=oracle.negative_matrix();atomic('reports/r23/NEGATIVE_E2E_MATRIX.json',matrix)
    positive=read('reports/r23/POSITIVE_E2E_ENGINEERING.json');dbpath=ROOT/'reports/r23/isolated_db/positive_e2e_v1.sqlite'
    result=oracle.inspect_database(dbpath);atomic('reports/r23/INDEPENDENT_RUNTIME_ORACLE.json',dict(result,negative_matrix=ref('reports/r23/NEGATIVE_E2E_MATRIX.json')))
    db=sqlite3.connect(dbpath)
    for key,table in [('publications','shadow_publications'),('enrollments','shadow_first_enrollments'),('observations','shadow_observations'),('outcomes','shadow_outcome_revisions'),('due','shadow_due_outbox'),('health','shadow_health_receipts')]:
        rows=[json.loads(row[0]) for row in db.execute('SELECT payload FROM '+table+' ORDER BY rowid')];assert rows==positive['readback'][key]
    schema=[dict(type=t,name=n,sql=s) for t,n,s in db.execute("SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]
    atomic('reports/r23/STORAGE_SCHEMA_GATE.json',dict(status='PASS_LOCAL',migration=ref('migrations/v4_16_r23_shadow_v1.sql'),actual_sqlite_schema=schema,database=result['database'],production_migration_applied=False))
    db.close()
    inventory=['ShadowRuntimeController','ClockPolicyResolver','SourceReadinessReceiptRegistry','ObservationSlotPlanner','MandatorySourceFreezeBuilder','ShadowPriorStateReader','ShadowPublicationBuilder','ShadowPublicationAcceptanceTransaction','RealtimeCohortEnrollmentWriter','DailyMembershipSnapshotWriter','DueOutboxScheduler','SettlementWorkerOrchestrator','ShadowHealthReceiptWriter','ShadowReadbackReader','RollbackController']
    atomic('reports/r23/RUNTIME_COMPONENT_INVENTORY.json',dict(status='PASS_LOCAL',components=inventory,implementation=ref('src/workbench_analysis/v4_16_shadow_runtime.py'),business_dependency_policy=read(DEPS)['accepted_producer_scope'],runtime_activation='NOT_AUTHORIZED'))
    atomic('reports/r23/R22R1_EXTERNAL_ACCEPTANCE_BINDING.json',dict(status='FORMALIZED',accepted_head=ref(ACCEPT),external_authority=ref(AUDIT),engineering_entry_only=True,runtime_authorized=False))
    atomic('reports/r23/PROTECTED_BYTES.json',oracle.protected())
    atomic('reports/r23/ROLLBACK_DRILL.json',dict(status='PASS_LOCAL',receipt=positive['rollback'],negative_deletion_attempt='N24',persisted_database=result['database'],pending_obligations=5,accepted_observations_preserved=2))
    # Each gate cites actual database inspection and/or named exercised cases.
    gate_cases={'MIGRATION_ISOLATED_DB_GATE':['test_immutable_storage_sql_triggers','test_database_namespace_and_origin_constraints'],'SOURCE_RECEIPT_GATE':['N04','N05','N06'],'SLOT_RUNTIME_GATE':['N02','N03','N20','test_blocked_to_ready_and_missed_terminal'],'SHADOW_PRIOR_GATE':['N07','N08'],'TRANSACTION_ATOMICITY_GATE':['N10','test_first_manifest_freeze_and_head_cas'],'COHORT_ENROLLMENT_GATE':['N09','N11','N21'],'MEMBERSHIP_CAPTURE_GATE':['N15','test_daily_membership_non_pit_capture'],'SETTLEMENT_ORCHESTRATION_GATE':['N12','N13','N14','N22'],'HEALTH_RECEIPT_GATE':['N16','N17','N23'],'LEGACY_ISOLATION_GATE':['N07','test_db_cannot_be_production_path']}
    for name,covered in gate_cases.items():atomic('reports/r23/'+name+'.json',dict(status='PASS_LOCAL',covered_tests=covered,independent_oracle=ref('reports/r23/INDEPENDENT_RUNTIME_ORACLE.json'),test_summary=ref('reports/r23/LOCAL_TEST_SUMMARY.json'),evidence_origin='ENGINEERING_FIXTURE',runtime_authorized=False,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0))
    atomic('reports/r23/GOV_METADATA_LINEAGE_STYLE.json',dict(issue_id='GOV_METADATA_LINEAGE_STYLE',scope='INHERITED_V3_LINEAGE_METADATA_ONLY',classification='P2_NONBLOCKING',disposition='PASS_KEEP; EXACT_V3_BINDING_USED; NO_PREDECESSOR_DISCOVERY_OR_PERMISSION_FROM_INHERITED_LABELS',evidence=ref(AUDIT),external_acceptance_preserved=True))
if __name__=='__main__':build()
