"""P0-02 residual acceptance: exact persisted head and queue identity."""
import copy
import hashlib
import pytest
from unittest.mock import patch
from tests.test_full_chain_repair import shadow, future
from scripts.full_chain_repair_io import ROOT
from scripts.v4_16_shadow_runtime import canonical,digest
from scripts.v4_16_settlement_worker_v2 import DurableSettlementWorker
from scripts.v4_16_go_forward_shadow_runtime_r4r3 import SuccessorDatabase,SettlementObligationControllerR4R2

@pytest.fixture
def accepted():
    from scripts.r24r1_simulation import prepare,controller,SimulationClock
    from scripts.r24r1_io import ref,atomic,read
    from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController,grant_digest
    def v5(authority,deps,sources,seed):
        deps['contract_id']='V4_16_RUNTIME_DEPENDENCIES_V5'
        deps['bindings']=[ref(b['path']) for b in deps['bindings']]
        deps.update(queue_migration=ref('migrations/v4_16_settlement_queue_v2.sql'),integrity_migration=ref('migrations/v4_16_real_shadow_integrity_v2.sql'))
    x=prepare(changes=v5);c=controller(x);db=SuccessorDatabase(c,ROOT/x['database'])
    OneSessionLaunchController(db).run(x['request'],clock=SimulationClock())
    a=c.activation['authority_id'];b=a+'_B'
    authority=copy.deepcopy(c.activation);authority['authority_id']=b;authority['grant']['authority_id']=b
    authority['grant']['expected_prior_activation_head']=a
    authority['external_acceptance']=atomic(x['base']+'/acceptance_b.json',dict(authority_id=b,authority_digest=grant_digest(authority),decision='SIMULATION_ONLY_NOT_REAL_ACCEPTANCE'))
    binding=atomic(x['base']+'/authority_b.json',authority)
    db.conn.execute('INSERT INTO integrity_authority_v2 VALUES(?,?)',(b,canonical(binding)))
    db.transaction(lambda:db.append('activation',b,dict(authority_id=b,authority_binding=binding,expected_prior_activation_head=a)))
    try:yield db,x,a,b,binding
    finally:db.close()

@pytest.mark.parametrize('case',['A01','A02','A03','A04','A05','A06','payload_identity','acceptance_identity'])
def test_activation_head_exact(accepted,case):
    db,x,a,b,binding=accepted
    selected=a if case=='A02' else b
    db.conn.execute('UPDATE activation_head SET authority_id=?',(selected,))
    if case=='A03':db.conn.execute('DELETE FROM activation_head')
    if case=='A04':db.conn.execute("UPDATE activation_head SET authority_id='MISSING'")
    if case in ('A05','A06','payload_identity'):
        # Corruption fixture bypasses append-only guard only in this disposable simulation.
        db.conn.execute('DROP TRIGGER no_fact_update')
        p=db.get('activation',b)
        if case=='A06':p['authority_binding']=dict(binding,sha256='0'*64)
        if case=='payload_identity':p['authority_id']='WRONG'
        raw=canonical(p);sha='0'*64 if case=='A05' else hashlib.sha256(raw.encode()).hexdigest()
        db.conn.execute("UPDATE facts SET payload=?,digest=? WHERE kind='activation' AND id=?",(raw,sha,b))
    if case=='acceptance_identity':
        from scripts.r24r1_io import read,atomic
        authority=read(binding['path']);acceptance=read(authority['external_acceptance']['path'])
        acceptance['authority_id']='WRONG'
        atomic(authority['external_acceptance']['path'],acceptance)
    if case in ('A01','A02'):
        resumed=SettlementObligationControllerR4R2(ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])
        assert resumed.activation['authority_id']==selected
        assert len(db.rows('activation'))==2
    else:
        with pytest.raises(ValueError):SettlementObligationControllerR4R2(ROOT,db.path,simulation=True,simulation_dependencies=x['manifest'])

@pytest.mark.parametrize('case',['Q01','Q02','Q03','Q04','Q05'])
def test_queue_exact_idempotency(shadow,case):
    db,x=shadow;authority,source=future(db);worker=DurableSettlementWorker(db,'R1R1')
    due=next(d for d in db.rows('due') if d['horizon']==1);due_id=digest([due['enrollment_id'],1]);sha=source.binding['sha256']
    if case in ('Q02','Q03'):
        key=worker.queue_identity(due,db.get('enrollment',due['enrollment_id']))
        if case=='Q02':
            other=next(d for d in db.rows('due') if d['horizon']!=1)
            other_id=digest([other['enrollment_id'],other['horizon']])
            db.conn.execute("INSERT INTO settlement_queue_v2(queue_key,evaluation_source_digest,due_kind,due_id,status) VALUES(?,?,?,?,'READY')",(key,sha,'due',other_id))
        if case=='Q03':
            # Malformed persisted queue fixture: bypass insert references, not the application guard.
            db.conn.execute('PRAGMA foreign_keys=OFF')
            db.conn.execute("INSERT INTO settlement_queue_v2(queue_key,evaluation_source_digest,due_kind,due_id,status) VALUES(?,?,?,?,'READY')",(key,sha,'due_revision',due_id))
            db.conn.execute('PRAGMA foreign_keys=ON')
        before=worker.row(key,sha)
        with pytest.raises(ValueError,match='QUEUE_IDEMPOTENCY_CONFLICT'):worker.enqueue(due_id,sha,'2026-10-09')
        assert worker.row(key,sha)==before
        return
    if case=='Q04':
        key=worker.enqueue(due_id,sha,'2026-10-09');original=db.get
        count=0
        def corrupt_readback(kind,key):
            nonlocal count
            value=original(kind,key)
            if kind=='enrollment':
                count+=1
                if count==2:value=dict(value,state_lineage_id='CORRUPTED_FROZEN_IDENTITY')
            return value
        with patch.object(db,'get',corrupt_readback):
            with pytest.raises(ValueError,match='QUEUE_IDEMPOTENCY_CONFLICT'):worker.enqueue(due_id,sha,'2026-10-09')
        assert db.conn.execute('SELECT count(*) FROM settlement_queue_v2').fetchone()[0]==1
        return
    key=worker.enqueue(due_id,sha,'2026-10-09');before=worker.row(key,sha)
    assert worker.enqueue(due_id,sha,'2026-10-09')==key and worker.row(key,sha)==before
    if case=='Q05':
        result=worker.deliver(key,sha,authority,lambda:source,'2026-10-09')
        source.binding=dict(source.binding,sha256=digest('R1R1_CORRECTED_SIMULATION'))
        authority.data['component_artifacts']['ADJUSTED_DAILY']=source.binding
        revised_sha=source.binding['sha256'];assert worker.enqueue(due_id,revised_sha,'2026-10-09')==key
        revised=worker.deliver(key,revised_sha,authority,lambda:source,'2026-10-09')
        assert revised['evaluation_revision']==2 and revised['first_observed_id']==result['outcome_revision_id']
        assert db.conn.execute('SELECT count(*) FROM settlement_queue_v2').fetchone()[0]==2
