"""R4R2 startup admission successor. Inherits frozen runtime business methods."""
import json
from pathlib import Path
from scripts.v4_16_go_forward_shadow_runtime import RealShadowController as HistoricalController, dependency_digest, grant_digest
from scripts.v4_16_shadow_runtime import check, exact, utc, ClockPolicyResolver
from scripts.v4_16_go_forward_input_authority_r4r2 import GoForwardInputAuthority


import copy, hashlib, sqlite3
from scripts.v4_16_shadow_runtime import canonical, digest
from scripts.v4_16_capability_resolution_v2 import require_admission,validate_dependencies,validate_grant
from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController as HistoricalLaunchController
class OneSessionLaunchController(HistoricalLaunchController):
    def settle(self,*args,**kwargs):
        raise ValueError('DURABLE_SETTLEMENT_WORKER_REQUIRED')
INTEGRITY_TABLES=('integrity_calendar_v2','integrity_authority_v2','integrity_activation_v2','integrity_manifest_v2','integrity_slot_v2','integrity_publication_v2','integrity_event_v2','integrity_freeze_v2','integrity_enrollment_v2','integrity_admission_v2','integrity_due_v2','integrity_evaluation_source_v2','integrity_outcome_v2','integrity_state_v2')

class RealShadowController(HistoricalController):
    def __init__(self, root, simulation_dependencies=None):
        check(simulation_dependencies is None,'R4R2_REAL_CONTROLLER_SIMULATION_FORBIDDEN')
        self.root=Path(root).resolve()
        self.simulation=simulation_dependencies is not None
        path=simulation_dependencies or 'config/v4_16_runtime_dependencies_v6.json'
        if self.simulation:
            check((self.root/path).resolve().is_relative_to(self.root/'reports/r24r1/activation_simulation'), 'ISOLATED_SIMULATION_MANIFEST_REQUIRED')
        self.dependency_path=path
        self.dependency_bytes=(self.root/path).read_bytes()
        self.deps=json.loads(self.dependency_bytes)
        validate_dependencies(self.root,self.deps)
        self.activation=json.loads(exact(self.root,self.deps['activation']))
        # Nothing that observes source availability or opens storage precedes this.
        check(self.activation['runtime_authorized'] is True and self.activation['real_shadow_authorized'] is True,
              'REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION')
        check(self.activation['environment_class']==('ACTIVATION_SIMULATION' if self.simulation else 'REAL'),'AUTHORITY_ENVIRONMENT_MISMATCH')
        check(not any(self.activation[k] for k in ('production','focus','V4_16')),'NON_SHADOW_PERMISSION_FORBIDDEN')
        for binding in self.deps['bindings']: exact(self.root,binding)
        self.grant=self.activation['grant']
        validate_grant(self.deps,self.grant)
        check(self.grant is not None and set(self.activation['required_grant_fields'])<=self.grant.keys(),'INCOMPLETE_ACTIVATION_GRANT')
        require_admission(self.root,self.deps['capability_resolution'],self.grant['capability_scope'])
        acceptance=json.loads(exact(self.root,self.activation['external_acceptance']))
        check(acceptance['authority_digest']==grant_digest(self.activation),'EXTERNAL_AUTHORITY_DIGEST_MISMATCH')
        check(acceptance['decision']==('SIMULATION_ONLY_NOT_REAL_ACCEPTANCE' if self.simulation else 'PASS_REAL_SHADOW_ACTIVATION'), 'EXTERNAL_ACTIVATION_NOT_ACCEPTED')
        check(acceptance['authority_id']==self.activation['authority_id']==self.grant['authority_id'],'AUTHORITY_IDENTITY_MISMATCH')
        check(self.grant['rollback_identity']=='R24_APPEND_ONLY_STOP_V1','UNACCEPTED_ROLLBACK_IDENTITY')
        check(self.grant['runtime_dependency_contract_id']==self.deps['contract_id'] and self.grant['dependency_set_digest']==dependency_digest(self.deps),'DEPENDENCY_SET_MISMATCH')
        for key in ('clock','slot','storage','source_adapters','initialization_boundary'):
            check(self.grant[key]==self.deps[key],'UNACCEPTED_'+key.upper())
        self.storage=json.loads(exact(self.root,self.deps['storage']))
        self.adapters=json.loads(exact(self.root,self.deps['source_adapters']))
        self.boundary=json.loads(exact(self.root,self.deps['initialization_boundary']))
        self.sources=json.loads(exact(self.root,self.grant['source_authority']))
        check(self.sources['environment_class']==self.activation['environment_class'],'SOURCE_ENVIRONMENT_MISMATCH')
        check(self.sources['adapter_id']==self.adapters['adapter_id'],'UNACCEPTED_SOURCE_ADAPTER')
        check(self.sources['owner_heads']==self.deps['owner_heads'],'UNACCEPTED_OWNER_HEADS')
        check(set(self.adapters['mandatory_families'])<=self.sources['sources'].keys(),'MISSING_MANDATORY_SOURCE')
        self.clock=ClockPolicyResolver(self)
        self.authority=GoForwardInputAuthority(self.root,self.deps['go_forward_input'],self.grant['daily_input_authority'],self.grant,self.grant['daily_input_boundary'],self.simulation)
        check(utc(self.grant['daily_input_boundary'])<=utc(self.clock.resolve(self.grant['target_trade_date'],self.authority.sessions)['scheduled_cutoff_at']),'DAILY_BOUNDARY_AFTER_SLOT_CUTOFF')
        self.origin='ACTIVATION_SIMULATION' if self.simulation else 'PIT_OBSERVED'
        identity=self.grant['storage_identity']
        check(identity['namespace']=='SHADOW_V4' and identity['execution_mode']=='SHADOW' and identity['evidence_origin']==self.origin
              and identity['migration']==self.deps['migration'],'UNACCEPTED_STORAGE_IDENTITY')
        self.slot_fields=json.loads(exact(self.root,self.deps['slot']))['fields']
        self.guard()


    def verify_request(self, request):
        self.guard()
        g=self.grant
        check(request['trade_date']==g['target_trade_date'],'EXACT_TARGET_DAILY_INPUT_REQUIRED')
        check(all(self.sources['sources'][k]['binding']==self.authority.daily['sources'][k]['binding'] for k in self.adapters['mandatory_families']),'DAILY_SOURCE_BINDING_MISMATCH')
        check(request['trade_date'] in self.authority.sessions,'ACCEPTED_MARKET_SESSION_REQUIRED')
        check(request['trade_date']>=g['effective_trade_date'] and utc(request['accepted_at'])>=utc(g['effective_from']),'AUTHORITY_EFFECTIVE_DATE_MISMATCH')
        for key in ('model_contract_id','parameter_set_id','state_lineage_id'):
            check(request[key]==g[key],'WRONG_'+key.upper())
        caps=request['capabilities']
        check(caps and len(set(caps))==len(caps) and set(caps)<=set(g['capability_scope'])<=set(self.activation['allowed_capabilities']), 'UNGRANTED_CAPABILITY')
        require_admission(self.root,self.deps['capability_resolution'],caps)
        check(request.get('prior_namespace','SHADOW_V4')=='SHADOW_V4','CROSS_NAMESPACE_PRIOR')
        check(not request.get('raw_provider_fallback'),'NO_RAW_PROVIDER_FALLBACK')

    def database(self,path):
        self.guard()
        return SuccessorDatabase(self,path)

class SettlementObligationControllerR4R2:
    """Resume accepted obligations even when the current launch authority is off.

    Reads an already existing successor database and its exact accepted activation
    history. This controller cannot initialize storage or accept a publication.
    """
    def __init__(self,root,path,simulation=False,simulation_dependencies=None):
        self.root=Path(root).resolve()
        self.simulation=simulation
        self.origin='ACTIVATION_SIMULATION' if simulation else 'PIT_OBSERVED'
        check(simulation_dependencies is None or (simulation and (self.root/simulation_dependencies).resolve().is_relative_to(self.root/'reports/r24r1/activation_simulation')), 'ISOLATED_SETTLEMENT_FIXTURE_REQUIRED')
        self.dependency_path=simulation_dependencies or 'config/v4_16_runtime_dependencies_v6.json'
        self.dependency_bytes=(self.root/self.dependency_path).read_bytes()
        self.deps=json.loads(self.dependency_bytes)
        self.guard()
        if not simulation:validate_dependencies(self.root,self.deps)
        self.storage=json.loads(exact(self.root,self.deps['storage']))
        path=Path(path).resolve()
        allowed=(self.root/self.storage['simulation_root' if simulation else 'real_root']).resolve()
        check(allowed.is_relative_to(self.root) and path.is_relative_to(allowed) and path.exists(),'EXISTING_ACCEPTED_OBLIGATION_DATABASE_REQUIRED')
        conn=sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)
        try:
            check(conn.execute('SELECT environment,evidence_origin FROM storage_identity').fetchall()==[
                ('ACTIVATION_SIMULATION' if simulation else 'REAL',self.origin)],'OBLIGATION_STORAGE_IDENTITY')
            conn.execute('BEGIN')
            heads=conn.execute('SELECT authority_id FROM activation_head WHERE singleton=1').fetchall()
            check(len(heads)==1,'EXACT_ACTIVATION_HEAD_REQUIRED')
            authority_id=heads[0][0]
            rows=conn.execute("SELECT payload,digest FROM facts WHERE kind='activation' AND id=?",(authority_id,)).fetchall()
            check(len(rows)==1,'EXACT_ACTIVATION_HEAD_FACT_REQUIRED')
            raw,sha=rows[0]
            check(hashlib.sha256(raw.encode()).hexdigest()==sha,'ACTIVATION_HISTORY_DIGEST')
            accepted=json.loads(raw)
            check(accepted['authority_id']==authority_id,'ACTIVATION_HEAD_IDENTITY_MISMATCH')
            binding=accepted['authority_binding']
            check(conn.execute("SELECT count(*) FROM facts WHERE kind='enrollment'").fetchone()[0]>0,'NO_ACCEPTED_SETTLEMENT_OBLIGATIONS')
        finally:conn.close()
        self.accepted_activation_binding=binding
        self.settlement_only=True
        self.activation=json.loads(exact(self.root,binding))
        acceptance=json.loads(exact(self.root,self.activation['external_acceptance']))
        check(acceptance['authority_digest']==grant_digest(self.activation) and
              acceptance['decision']==('SIMULATION_ONLY_NOT_REAL_ACCEPTANCE' if simulation else 'PASS_REAL_SHADOW_ACTIVATION'),'UNACCEPTED_OBLIGATION_AUTHORITY')
        self.grant=self.activation['grant']
        validate_grant(self.deps,self.grant)
        check(self.deps['contract_id']=='V4_16_RUNTIME_DEPENDENCIES_V6','STALE_OBLIGATION_DEPENDENCY')
        check(self.grant['runtime_dependency_contract_id']==self.deps['contract_id'] and self.grant['dependency_set_digest']==dependency_digest(self.deps),'STALE_OBLIGATION_DEPENDENCY')
        check(self.activation['authority_id']==authority_id==self.grant['authority_id']==acceptance['authority_id'],'AUTHORITY_IDENTITY_MISMATCH')
        check(self.grant['storage_identity']['database_path']==path.relative_to(self.root).as_posix(),'OBLIGATION_DATABASE_NOT_BOUND')
        check(self.activation['environment_class']==('ACTIVATION_SIMULATION' if simulation else 'REAL'),'OBLIGATION_STORAGE_IDENTITY')
        identity=self.grant['storage_identity']
        check(all(identity[k]==v for k,v in dict(namespace='SHADOW_V4',execution_mode='SHADOW',evidence_origin=self.origin,migration=self.deps['migration']).items()),'OBLIGATION_STORAGE_IDENTITY')
        self.sources=json.loads(exact(self.root,self.grant['source_authority']))
        loader=GoForwardInputAuthority
        if simulation:
            from scripts.v4_16_go_forward_input_authority import GoForwardInputAuthority as loader
        self.authority=loader(self.root,self.deps['go_forward_input'],self.grant['daily_input_authority'],self.grant,self.grant['daily_input_boundary'],self.simulation)

    def guard(self):
        check((self.root/self.dependency_path).read_bytes()==self.dependency_bytes,'SETTLEMENT_DEPENDENCY_DRIFT')
        for binding in self.deps['bindings']:exact(self.root,binding)

    def verify_request(self,request):
        raise ValueError('SETTLEMENT_ONLY_CANNOT_ACCEPT_PUBLICATION')

    def database(self,path):
        self.guard()
        check(Path(path).exists(),'SETTLEMENT_ONLY_CANNOT_INITIALIZE_STORAGE')
        return SuccessorDatabase(self,path)

class SuccessorDatabase:
    def __init__(self,controller,path):
        self.controller=controller
        self.path=Path(path).resolve()
        allowed=controller.root/controller.storage['simulation_root' if controller.simulation else 'real_root']
        check(allowed.resolve().is_relative_to(controller.root) and self.path.is_relative_to(allowed.resolve()) and self.path.suffix=='.sqlite','STORAGE_IDENTITY_NOT_ACCEPTED')
        check(self.path==(controller.root/controller.grant['storage_identity']['database_path']).resolve(),'EXACT_STORAGE_IDENTITY_REQUIRED')
        if self.path.exists():
            existing=sqlite3.connect('file:'+self.path.as_posix()+'?mode=ro',uri=True)
            try:
                tables={r[0] for r in existing.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                check(tables<= {'storage_identity','facts','publication_heads','activation_head','settlement_queue_v2'} | set(INTEGRITY_TABLES),'ENGINEERING_OR_LEGACY_DATABASE_FORBIDDEN')
            finally:existing.close()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path,isolation_level=None)
        self.conn.executescript(exact(controller.root,controller.deps['migration']).decode())
        check(not self.conn.execute('SELECT count(*) FROM facts').fetchone()[0] or self.conn.execute("SELECT count(*) FROM sqlite_master WHERE name='integrity_slot_v2'").fetchone()[0], 'NONEMPTY_LEDGER_REQUIRES_AUDITED_INTEGRITY_MIGRATION')
        self.conn.executescript(exact(controller.root,controller.deps['queue_migration']).decode())
        self.conn.executescript(exact(controller.root,controller.deps['integrity_migration']).decode())
        for table in INTEGRITY_TABLES:
            for action in ('UPDATE','DELETE'):
                self.conn.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_INTEGRITY_REFERENCE'); END")
        for index,date in enumerate(controller.authority.sessions):
            self.conn.execute('INSERT OR IGNORE INTO integrity_calendar_v2 VALUES(?,?)',(index,date))
            check(self.conn.execute('SELECT trade_date FROM integrity_calendar_v2 WHERE session_no=?',(index,)).fetchone()==(date,),'CALENDAR_IDENTITY_DRIFT')
        self.conn.execute('INSERT OR IGNORE INTO integrity_authority_v2 VALUES(?,?)',(controller.activation['authority_id'],canonical(controller.deps['activation'] if not getattr(controller,'settlement_only',False) else controller.accepted_activation_binding)))
        env=controller.activation['environment_class']
        self.conn.execute('INSERT OR IGNORE INTO storage_identity VALUES(1,?,?)',(env,controller.origin))
        check(self.conn.execute('SELECT environment,evidence_origin FROM storage_identity').fetchall()==[(env,controller.origin)],'STORAGE_IDENTITY_MISMATCH')

    def append(self,kind,key,value):
        p=copy.deepcopy(value)
        p.update(namespace='SHADOW_V4',execution_mode='SHADOW',evidence_origin=self.controller.origin,
                 evidence_class='NOT_REAL_EVIDENCE' if self.controller.simulation else 'PIT_OBSERVED_REAL')
        raw=canonical(p)
        sha=hashlib.sha256(raw.encode()).hexdigest()
        old=self.conn.execute('SELECT digest FROM facts WHERE kind=? AND id=?',(kind,key)).fetchone()
        if old:
            check(old[0]==sha,'APPEND_ONLY_IDENTITY_CONFLICT')
        else:
            self.conn.execute('INSERT INTO facts VALUES(?,?,?,?,?,?,?)',(kind,key,'SHADOW_V4','SHADOW',self.controller.origin,raw,sha))
        return p

    def rows(self,kind):
        return [json.loads(r[0]) for r in self.conn.execute('SELECT payload FROM facts WHERE kind=? ORDER BY rowid',(kind,))]

    def get(self,kind,key):
        r=self.conn.execute('SELECT payload FROM facts WHERE kind=? AND id=?',(kind,key)).fetchone()
        check(r is not None,'MISSING_DURABLE_RECORD')
        return json.loads(r[0])

    def transaction(self,fn):
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            result=fn()
            self.conn.execute('COMMIT')
            return result
        except BaseException:
            self.conn.execute('ROLLBACK')
            raise

    def close(self):self.conn.close()


def accepted_future_authority(controller,daily_binding,boundary,cutoff):
    # Only an exact R4R2 bridge can select a future accepted head. No discovery.
    from datetime import datetime,timezone,timedelta
    check(cutoff<=datetime.now(timezone(timedelta(hours=8))).date().isoformat(),'FUTURE_SESSION_READ_FORBIDDEN')
    daily=json.loads(exact(controller.root,daily_binding))
    check(daily['target_trade_date']==cutoff,'EXACT_FUTURE_SESSION_REQUIRED')
    grant=dict(controller.grant,daily_input_authority=daily_binding,daily_input_digest=daily['daily_input_digest'],
               target_trade_date=cutoff,minimum_daily_input_revision=1)
    return GoForwardInputAuthority(controller.root,controller.deps['go_forward_input'],daily_binding,grant,boundary,False)

def settlement_cycle(db,daily_binding,boundary,cutoff,worker_id):
    from scripts.v4_16_settlement_worker_v2 import DurableSettlementWorker
    from workbench_analysis.v4_15_settlement import AcceptedPriceSource
    # Stop/UI/Focus state never filters already accepted due obligations.
    # A previously unknown future session must append a due revision, never rewrite a due fact.
    preview=json.loads(exact(db.controller.root,daily_binding))
    calendar=json.loads(exact(db.controller.root,preview['calendar']))
    sessions=[d['trade_date'] if isinstance(d,dict) else d for d in calendar['session_dates']]
    from workbench_analysis.v4_15_settlement import due_plan
    candidates=[]
    for enrollment in db.rows('enrollment'):
        check(enrollment['T0'] in sessions,'FROZEN_T0_MISSING_FROM_ACCEPTED_CALENDAR')
        for item in due_plan(sessions,enrollment['T0'],cutoff):
            if item['due_date'] is not None and item['due_date']<=cutoff:
                candidates.append(dict(item,enrollment_id=enrollment['enrollment_id'],frozen_t0=enrollment['frozen_t0']))
    if not candidates:return []
    try:
        authority=accepted_future_authority(db.controller,daily_binding,boundary,cutoff)
    except Exception as error:
        receipt=dict(cutoff=cutoff,daily_input_binding=daily_binding,backlog_reason=str(error),
            obligations=[dict(enrollment_id=d['enrollment_id'],horizon=d['horizon'],due_date=d['due_date']) for d in candidates],
            raw_provider_fallback=False,preserve_pending_obligations=True)
        db.transaction(lambda:db.append('settlement_backlog',digest(receipt),receipt))
        raise
    for index,date in enumerate(authority.sessions):
        db.conn.execute('INSERT OR IGNORE INTO integrity_calendar_v2 VALUES(?,?)',(index,date))
        check(db.conn.execute('SELECT trade_date FROM integrity_calendar_v2 WHERE session_no=?',(index,)).fetchone()==(date,),'CALENDAR_IDENTITY_DRIFT')
    source=authority.data['component_artifacts']['ADJUSTED_DAILY']
    worker=DurableSettlementWorker(db,worker_id)
    results=[]
    for item in candidates:
        original=db.get('due',digest([item['enrollment_id'],item['horizon']]))
        check(original['due_date'] is None or original['due_date']==item['due_date'],'FROZEN_DUE_SESSION_DRIFT')
        kind='due' if original['due_date'] is not None else 'due_revision'
        due_id=digest([item['enrollment_id'],item['horizon']]) if kind=='due' else digest([item['enrollment_id'],item['horizon'],item['due_date'],item['frozen_t0']])
        if kind=='due_revision':db.transaction(lambda:db.append(kind,due_id,item))
        key=worker.enqueue(due_id,source['sha256'],cutoff,due_kind=kind)
        results.append(worker.deliver(key,source['sha256'],authority,lambda:AcceptedPriceSource(authority,source),cutoff))
    return results
