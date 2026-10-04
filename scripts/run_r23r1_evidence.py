"""Versioned repair evidence; previous R23 evidence is never overwritten."""
import shutil,uuid
from pathlib import Path
from scripts.run_r23_engineering import positive
from scripts.r23r1_io import *
from scripts.validate_r23r1_runtime import inspect_database,protected
from scripts.validate_r23_runtime import negative_matrix
from tests.test_r23r1_runtime import mutated_database

def run():
    result=positive('r23r1_evidence_'+uuid.uuid4().hex)
    destination=ROOT/'reports/r23r1/persisted/positive.sqlite'
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(result['database'],destination)
    result['database']='reports/r23r1/persisted/positive.sqlite'
    result['database_binding']=ref(result['database'])
    atomic('reports/r23r1/POSITIVE_E2E_ENGINEERING.json',result)
    oracle=inspect_database(destination)
    oracle['database_binding']=ref(result['database'])
    atomic('reports/r23r1/INDEPENDENT_RUNTIME_ORACLE.json',oracle)
    for name in ('SLOT_CONTRACT_FIELD_GATE','SLOT_VISIBILITY_AGGREGATION_ORACLE','SLOT_REVISION_GATE','OBSERVATION_SUPERSEDES_GATE','RECEIPT_TIMESTAMP_HYGIENE_GATE'):
        atomic('reports/r23r1/'+name+'.json',dict(oracle,gate=name))
    negatives=[]
    for number in range(25,33):
        path=destination.parent/('N%02d.sqlite'%number)
        if path.exists():raise ValueError('EVIDENCE_ALREADY_EXISTS')
        mutated_database(destination,path,number)
        try:inspect_database(path)
        except ValueError as error:rejection=str(error)
        else:raise AssertionError('NEGATIVE_NOT_REJECTED')
        item=dict(case='N%02d'%number,status='PASS_LOCAL',rejection=rejection,database_binding=ref(path.relative_to(ROOT).as_posix()),row_digests_recomputed=True,test_only_corruption=True)
        negatives.append(item);atomic('reports/r23r1/persisted/N%02d.json'%number,item)
    atomic('reports/r23r1/NEGATIVE_E2E_MATRIX.json',dict(status='PASS_LOCAL',prior_immutable_evidence=negative_matrix(),repair_cases=negatives,count=32))
    atomic('reports/r23r1/PROTECTED_BYTES.json',protected())
    audits=[ref(p.relative_to(ROOT).as_posix()) for p in sorted((ROOT/'docs/evidence/r23r1').glob('*.md'))]
    atomic('reports/r23r1/STAGE_CONTRACT_AND_AUDIT_ITEMS.json',dict(baseline=BASE,authority=audits,stage_contract=ref('config/v4_16_r23r1_slot_runtime_policy_v1.json'),items=[dict(id='R23-SLOT-01',scope='Persisted Slot V2 fields and frozen visibility',status='CLOSED_LOCAL_PENDING_EXTERNAL_AUDIT',evidence=ref('reports/r23r1/SLOT_CONTRACT_FIELD_GATE.json')),dict(id='R23-OBSERVATION-LINEAGE-P1',scope='Shadow wrapper same-day supersedes lineage',status='CLOSED_LOCAL_PENDING_EXTERNAL_AUDIT',evidence=ref('reports/r23r1/OBSERVATION_SUPERSEDES_GATE.json'))],runtime_authorized=False,real_shadow_authorized=False,NEXT='STOP_WAIT_R23R1_INDEPENDENT_EXTERNAL_AUDIT'))
    print(oracle)
if __name__=='__main__':run()
