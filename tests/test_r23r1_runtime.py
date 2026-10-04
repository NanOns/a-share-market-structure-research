"""Persisted repair proof and independently rejected semantic corruptions."""
import ast,copy,inspect,json,sqlite3,uuid
from pathlib import Path
import pytest
from scripts.run_r23_engineering import prepare,positive,request,receipt
from scripts.v4_16_shadow_runtime import ObservationSlotPlanner,SourceReadinessReceiptRegistry
from scripts import validate_r23r1_runtime as oracle
from scripts.r23r1_io import ROOT,atomic,ref

@pytest.fixture(scope='module')
def persisted():
    result=positive('r23r1_test_'+uuid.uuid4().hex)
    return Path(result['database'])

def corrupt(records,number):
    slots=[s for s in records['shadow_observation_slots'] if s['slot_status']=='ACCEPTED_ON_TIME'];s=slots[1]
    obs=records['shadow_observations']
    if number==25:del s['parameter_set_id']
    if number==26:s['source_provider_available_at']='2026-09-28T12:58:00Z'
    if number==27:s['system_available_at']='2026-09-28T12:58:00Z'
    if number==28:s['source_manifest_digest']='0'*64
    if number==29:s['capability_scope']=['UNGRANTED_SCOPE']
    if number==30:obs[1]['supersedes_observation']=None
    if number==31:obs[0]['logical_event_id']='DIFFERENT_EVENT'
    if number==32:obs[0]['supersedes_observation']=obs[1]['observation_id']
    # Keep quality consistent: semantic corruption must fail beyond row hashing.
    fields=json.loads((ROOT/'config/v4_16_observation_slot_contract_v2.json').read_bytes())['fields']
    s['field_quality']={k:('NOT_YET_AVAILABLE' if s.get(k) is None else 'KNOWN') for k in fields if k in s}

def mutated_database(source,destination,number):
    destination.parent.mkdir(parents=True,exist_ok=True)
    src=sqlite3.connect(source);dst=sqlite3.connect(destination);src.backup(dst);src.close()
    for name, in dst.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():dst.execute('DROP TRIGGER '+name)
    records=oracle.load(source);corrupt(records,number)
    for table in ('shadow_observation_slots','shadow_observations'):
        ids=dst.execute('SELECT id FROM '+table+' ORDER BY rowid').fetchall()
        for (key,),value in zip(ids,records[table]):
            payload=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
            dst.execute('UPDATE '+table+' SET payload=?,digest=? WHERE id=?',(payload,oracle.hash_value(value),key))
    dst.commit();dst.close()
    return destination

def test_positive_complete_persisted_oracle(persisted):
    result=oracle.inspect_database(persisted)
    assert result['required_slot_field_count']==18 and result['missing_slot_fields']==[]

@pytest.mark.parametrize('number',range(25,33))
def test_independent_rejects_semantic_corruption(persisted,tmp_path,number):
    path=mutated_database(persisted,tmp_path/('N%02d.sqlite'%number),number)
    with pytest.raises(ValueError):oracle.inspect_database(path)

def test_capability_scope_absent(persisted):
    records=oracle.load(persisted);del records['shadow_observation_slots'][-1]['capability_scope']
    with pytest.raises(ValueError,match='MISSING_SLOT_FIELD'):oracle.inspect_records(records)

def test_nonaccepted_states_complete_and_missed_preserves_timing():
    c,db=prepare();planner=ObservationSlotPlanner(db);r=request(c)
    planned=planner.plan(r);assert planned['slot_status']=='PLANNED'
    assert planned['accepted_at'] is None and planned['field_quality']['accepted_at']=='NOT_YET_AVAILABLE'
    missing=copy.deepcopy(r);missing['receipt_ids']=['MISSING'];blocked=planner.record(missing)
    assert blocked['slot_status']=='BLOCKED_SOURCE_NOT_READY' and blocked['system_available_at'] is None
    late=receipt(c,'owner','R23_OWNER_LATE','OWNER_OUTPUT','LATE')
    late['system_available_at']=late['created_at']='2026-09-28T13:00:01Z'
    SourceReadinessReceiptRegistry(db).register(late,c.registry['bindings']['owner'])
    r['receipt_ids']=['R23_OWNER_LATE','R23_SNAPSHOT_1'];missed=planner.record(r)
    assert missed['slot_status']=='MISSED_OBSERVATION_SLOT' and missed['system_available_at']==late['system_available_at']
    fields=c.slot_runtime_policy['slot_contract'];assert fields==c.deps['slot']
    for s in (planned,blocked,missed):planner.validate(s)
    assert planner.record(request(c))==missed
    db.close()

def test_receipt_creation_before_visibility_rejected():
    c,db=prepare();r=receipt(c,'owner','R23_OWNER_LATE','OWNER_OUTPUT','LATE')
    r['system_available_at']='2026-09-28T13:00:01Z'
    before=db.rows('shadow_source_readiness_receipts')
    with pytest.raises(ValueError,match='READINESS_ORDER'):SourceReadinessReceiptRegistry(db).register(r,c.registry['bindings']['owner'])
    assert db.rows('shadow_source_readiness_receipts')==before;db.close()

def test_oracle_has_no_writer_import():
    tree=ast.parse(inspect.getsource(oracle))
    imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    assert not any('shadow_runtime' in n or 'run_r23_engineering' in n for n in imports)

def test_protected_baseline():assert oracle.protected()['status']=='PASS_LOCAL'
