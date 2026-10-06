"""At-least-once durable CAS delivery, fenced leases and append-only outcomes."""
import json
import time
from scripts.v4_16_shadow_runtime import check, digest
from scripts.v4_16_go_forward_shadow_runtime import CandidateArtifactStore
from workbench_analysis.v4_15_settlement import AcceptedPriceSource, VectorPriceSource
from workbench_analysis.v4_15_settlement_successor import SettlementRuntime

class DurableSettlementWorker:
    def __init__(self,db,owner,lease_seconds=60):
        check(isinstance(owner,str) and bool(owner) and 0<lease_seconds<=3600,'INVALID_QUEUE_WORKER')
        self.db=db;self.owner=owner;self.lease=lease_seconds

    def enqueue(self,due_id,evaluation_source_digest,cutoff,*,due_kind='due'):
        check(due_kind in ('due','due_revision'),'INVALID_DUE_KIND')
        due=self.db.get(due_kind,due_id)
        check(due['due_date'] is not None and due['due_date']<=cutoff,'PRE_DUE_FUTURE_READ_FORBIDDEN')
        check(isinstance(evaluation_source_digest,str) and len(evaluation_source_digest)==64 and all(c in '0123456789abcdef' for c in evaluation_source_digest),'INVALID_EVALUATION_DIGEST')
        enrollment=self.db.get('enrollment',due['enrollment_id'])
        key=self.queue_identity(due,enrollment)
        def enqueue_exact():
            self.db.conn.execute('INSERT OR IGNORE INTO settlement_queue_v2(queue_key,evaluation_source_digest,due_kind,due_id,status) VALUES(?,?,?,?,\'READY\')',(key,evaluation_source_digest,due_kind,due_id))
            row=self.row(key,evaluation_source_digest)
            check(tuple(row[k] for k in ('queue_key','evaluation_source_digest','due_kind','due_id'))==(key,evaluation_source_digest,due_kind,due_id),'QUEUE_IDEMPOTENCY_CONFLICT')
            frozen_due=self.db.get(row['due_kind'],row['due_id'])
            frozen_enrollment=self.db.get('enrollment',frozen_due['enrollment_id'])
            check(self.queue_identity(frozen_due,frozen_enrollment)==row['queue_key'],'QUEUE_IDEMPOTENCY_CONFLICT')
        self.db.transaction(enqueue_exact)
        return key

    @staticmethod
    def queue_identity(due,enrollment):
        check(due['namespace']==enrollment['namespace']=='SHADOW_V4' and due['enrollment_id']==enrollment['enrollment_id'] and due['frozen_t0']==enrollment['frozen_t0'],'QUEUE_IDEMPOTENCY_CONFLICT')
        return digest([enrollment['namespace'],enrollment['model_contract_id'],enrollment['state_lineage_id'],enrollment['enrollment_id'],due['horizon'],due['due_date'],'FORWARD_PRICE_PATH_V1'])

    def row(self,key,source_digest):
        cursor=self.db.conn.execute('SELECT * FROM settlement_queue_v2 WHERE queue_key=? AND evaluation_source_digest=?',(key,source_digest))
        row=cursor.fetchone();check(row is not None,'MISSING_DURABLE_QUEUE')
        return dict(zip([d[0] for d in cursor.description],row))

    def claim(self,key,source_digest):
        now=time.time()
        def claim():
            row=self.row(key,source_digest)
            if row['status']=='ACKED':return None
            if row['status']=='SETTLED':return dict(row,readback_only=True)
            if row['status']=='CLAIMED' and row['lease_until']>now:return None
            count=self.db.conn.execute("UPDATE settlement_queue_v2 SET status='CLAIMED',claim_owner=?,claim_version=claim_version+1,claim_at=?,lease_until=?,retry_count=retry_count+CASE WHEN status='CLAIMED' THEN 1 ELSE 0 END,backlog_reason=CASE WHEN status='CLAIMED' THEN 'EXPIRED_CLAIM_RECOVERED' ELSE backlog_reason END WHERE queue_key=? AND evaluation_source_digest=? AND claim_version=?",(self.owner,now,now+self.lease,key,source_digest,row['claim_version'])).rowcount
            check(count==1,'QUEUE_CAS_CONFLICT')
            return self.row(key,source_digest)
        return self.db.transaction(claim)

    def acknowledge(self,key,source_digest):
        def ack():
            row=self.row(key,source_digest)
            if row['status']=='ACKED':return self.db.get('outcome',row['accepted_outcome_revision'])
            check(row['status']=='SETTLED','ACK_BEFORE_ACCEPTED_RESULT')
            result=self.db.get('outcome',row['accepted_outcome_revision'])
            self.db.conn.execute("UPDATE settlement_queue_v2 SET status='ACKED',ack_at=?,backlog_reason=NULL WHERE queue_key=? AND evaluation_source_digest=? AND status='SETTLED'",(time.time(),key,source_digest))
            return result
        return self.db.transaction(ack)

    def deliver(self,key,source_digest,authority,source_factory,cutoff,fail_at=None):
        claim=self.claim(key,source_digest)
        if claim is None:
            row=self.row(key,source_digest)
            return self.db.get('outcome',row['accepted_outcome_revision']) if row['status']=='ACKED' else None
        if claim.get('readback_only'):return self.acknowledge(key,source_digest)
        if fail_at=='claim':raise RuntimeError('INJECTED_CRASH_AFTER_CLAIM')
        due=self.db.get(claim['due_kind'],claim['due_id'])
        try:
            check(due['due_date'] is not None and due['due_date']<=cutoff,'PRE_DUE_FUTURE_READ_FORBIDDEN')
            self.db.controller.guard()
            if not self.db.controller.simulation:
                from scripts.v4_16_go_forward_input_authority_r4r2 import GoForwardInputAuthority
                check(type(authority) is GoForwardInputAuthority,'R4R2_ACCEPTED_FUTURE_AUTHORITY_REQUIRED')
                authority.validate_bridge(authority.root,authority.daily,self.db.controller.deps['go_forward_input'])
            check(authority.daily['target_trade_date']==cutoff and due['due_date'] in authority.sessions,'EXACT_ACCEPTED_FUTURE_SESSION_REQUIRED')
            source=source_factory() # Never read/create a price source before due admission.
            check(type(source) is AcceptedPriceSource or (self.db.controller.simulation and type(source) is VectorPriceSource),'NO_RAW_PROVIDER_FALLBACK')
            check(source.binding==authority.data['component_artifacts']['ADJUSTED_DAILY'] and source.binding['sha256']==source_digest,'EXACT_FUTURE_EVALUATION_SOURCE_REQUIRED')
            if type(source) is AcceptedPriceSource:
                check(not self.db.controller.simulation,'REAL_SOURCE_IN_SIMULATION_FORBIDDEN')
                check(json.loads(authority.read(source.binding))['contract_id']=='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3','ACCEPTED_FUTURE_SOURCE_CONTRACT')
            def settle():
                row=self.row(key,source_digest)
                check(row['status']=='CLAIMED' and row['claim_owner']==self.owner and row['claim_version']==claim['claim_version'] and row['lease_until']>time.time(),'QUEUE_CLAIM_LOST')
                store=CandidateArtifactStore(self.db)
                if 'integrity_evaluation_source_v2' in {r[0] for r in self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
                    from scripts.v4_16_shadow_runtime import canonical
                    self.db.conn.execute('INSERT OR IGNORE INTO integrity_evaluation_source_v2 VALUES(?,?)',(source_digest,canonical(source.binding)))
                refs=SettlementRuntime(authority,store).settle(due['frozen_t0'],source,cutoff,horizons=(due['horizon'],))
                check(len(refs)==1,'EXACT_SINGLE_OUTCOME_REQUIRED')
                result=store.read(refs[0]);check(result['outcome_status']!='PENDING','DUE_OUTCOME_STILL_PENDING')
                result=self.db.append('outcome',result['outcome_revision_id'],result)
                self.db.conn.execute("UPDATE settlement_queue_v2 SET status='SETTLED',accepted_outcome_revision=?,lease_until=NULL WHERE queue_key=? AND evaluation_source_digest=?",(result['outcome_revision_id'],key,source_digest))
                return result
            result=self.db.transaction(settle)
        except Exception as error:
            self.db.transaction(lambda:self.db.conn.execute("UPDATE settlement_queue_v2 SET status='READY',claim_owner=NULL,lease_until=NULL,retry_count=retry_count+1,backlog_reason=? WHERE queue_key=? AND evaluation_source_digest=? AND status='CLAIMED' AND claim_owner=? AND claim_version=?",(str(error),key,source_digest,self.owner,claim['claim_version'])))
            raise
        if fail_at=='result':raise RuntimeError('INJECTED_CRASH_AFTER_RESULT')
        return self.acknowledge(key,source_digest)
