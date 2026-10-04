"""Engineering-only persisted E2E driver. No current market data consumption."""
import copy,json,uuid
from scripts.r23_io import *
from workbench_analysis.v4_16_shadow_runtime import *

def receipt(controller,key,receipt_id,family,revision='R1'):
    return dict(receipt_id=receipt_id,receipt_kind='ACCEPTED_LOCAL_OBSERVATION_ACQUISITION',source_family=family,source_identity='R23_'+family,source_revision=revision,source_digest=controller.registry['bindings'][key]['sha256'],first_observed_at='2026-09-28T12:59:00Z',system_available_at='2026-09-28T12:59:00Z',integrity_passed_at='2026-09-28T12:59:00Z',accepted=True,integrity_pass=True,target_trade_date='2026-09-28',created_at='2026-09-28T12:59:00Z',evidence_origin='ENGINEERING_FIXTURE')
def request(controller,revision=1):
    key='owner' if revision==1 else 'owner_revision'
    return dict(model_contract_id='RESEARCH_STATE_V1',state_lineage_id='R23_ENGINEERING_LINEAGE',parameter_set_id=controller.registry['parameter_set_id'],trade_date='2026-09-28',revision=revision,receipt_ids=['R23_OWNER_1' if revision==1 else 'R23_OWNER_2','R23_SNAPSHOT_1'],owner_fixture=controller.registry['bindings'][key],snapshot_fixture=controller.registry['bindings']['snapshot'],fixture_key=key,owner_heads=controller.deps['owner_heads'],computation_started_at='2026-09-28T13:01:00Z',computation_finished_at='2026-09-28T13:59:00Z',accepted_at='2026-09-28T14:00:00Z',capabilities=['PURE_CORE_STOCK'])
def prepare(name=None,root=ROOT):
    c=ShadowRuntimeController(root);db=c.database(Path(root)/'reports/r23/isolated_db'/((name or uuid.uuid4().hex)+'.sqlite'))
    db.append('shadow_state_heads','R23_ISOLATED_SEED',c.fixture('seed'))
    registry=SourceReadinessReceiptRegistry(db)
    for key,rid,family,rev in [('owner','R23_OWNER_1','OWNER_OUTPUT','R1'),('snapshot','R23_SNAPSHOT_1','T0_SNAPSHOT','R1'),('owner_revision','R23_OWNER_2','OWNER_OUTPUT','R2')]:registry.register(receipt(c,key,rid,family,rev),c.registry['bindings'][key])
    return c,db
def positive(name=None,root=ROOT):
    c,db=prepare(name,root);tx=ShadowPublicationAcceptanceTransaction(db)
    r=request(c);plan=ObservationSlotPlanner(db).record(r)
    first=tx.accept(r);before=ShadowReadbackReader(db).read();assert tx.accept(r)==first;assert ShadowReadbackReader(db).read()==before
    original=copy.deepcopy(before['enrollments']);revised=tx.accept(request(c,2));assert db.rows('shadow_first_enrollments')==original
    e=original[0];worker=SettlementWorkerOrchestrator(db)
    reads=[]
    for key in ['future','future_correction']:
        binding=c.registry['bindings'][key];source=VectorPriceSource(c.fixture(key)['rows'],binding)
        worker.run(e['enrollment_id'],1,source,'2026-09-29');reads.extend(source.read_log)
    final=ShadowReadbackReader(db).read();assert len(final['outcomes'])==2
    stop=RollbackController(db).stop();assert db.rows('shadow_first_enrollments')==original
    # Pending obligations and settlement remain available after stopping acceptance.
    binding=c.registry['bindings']['future_correction'];source=VectorPriceSource(c.fixture('future_correction')['rows'],binding)
    worker.run(e['enrollment_id'],1,source,'2026-09-29')
    db.close()
    return dict(database=str(db.path),first_publication=first['publication_id'],revision_publication=revised['publication_id'],readback=final,source_reads=reads,rollback=stop,idempotent_rerun=True,evidence_origin='ENGINEERING_FIXTURE',REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0)
if __name__=='__main__':
    result=positive();atomic('reports/r23/POSITIVE_E2E_ENGINEERING.json',result);print(json.dumps(dict(database=result['database'],publications=len(result['readback']['publications']),outcomes=len(result['readback']['outcomes']))))
