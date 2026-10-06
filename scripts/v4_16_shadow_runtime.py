"""V4-16 engineering orchestration and gated R24 real entry dispatch.

Every database is isolated; durable artifacts have SHADOW_V4 namespace and
ENGINEERING_FIXTURE origin. The committed real authority rejects before storage.
Accepted business semantics are delegated to exact V4-15 implementations.
"""
import copy,hashlib,json,sqlite3
from pathlib import Path
from datetime import datetime,date,time,timezone,timedelta
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_15_radar_cohort import RadarCohortRuntime
from workbench_analysis.v4_15_settlement import SettlementRuntime,VectorPriceSource,AcceptedPriceSource,due_plan

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def check(ok,reason):
    if not ok:raise ValueError(reason)
def utc(value):
    check(isinstance(value,str) and value.endswith('Z'),'UTC_RFC3339_REQUIRED')
    return datetime.fromisoformat(value.replace('Z','+00:00'))
def exact(root,binding):
    p=(root/binding['path']).resolve();check(p.is_relative_to(root),'DEPENDENCY_ESCAPE')
    raw=p.read_bytes();check(len(raw)==binding.get('bytes',binding.get('byte_count')) and hashlib.sha256(raw).hexdigest()==binding['sha256'],'EXACT_DEPENDENCY_MISMATCH')
    return raw

class ShadowRuntimeController:
    MODES={'CONTRACT_TEST','ENGINEERING_FIXTURE','DRY_RUN_NO_ACCEPT','REAL_SHADOW'}
    def __new__(cls, root, mode='ENGINEERING_FIXTURE', **kwargs):
        if mode == 'REAL_SHADOW':
            path = kwargs.get('simulation_dependencies')
            if path is None:
                from scripts.v4_16_go_forward_shadow_runtime_r4r3 import RealShadowController
                return RealShadowController(root, **kwargs)
            if str(path).startswith('reports/r24r1/activation_simulation/'):
                from scripts.v4_16_go_forward_shadow_runtime import RealShadowController
                return RealShadowController(root, **kwargs)
            from scripts.v4_16_real_shadow_runtime import RealShadowController
            return RealShadowController(root, **kwargs)
        return super().__new__(cls)
    def __init__(self,root,mode='ENGINEERING_FIXTURE'):
        self.root=Path(root).resolve();check(mode in self.MODES,'UNKNOWN_MODE')
        self.mode=mode
        # Real entry is dispatched by __new__ to the separately contracted
        # successor. This initializer owns only the historical engineering path.
        check(mode!='REAL_SHADOW','REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION')
        self.deps=json.loads((self.root/'config/v4_16_runtime_dependencies_v1.json').read_bytes())
        self.activation=json.loads(exact(self.root,self.deps['activation']))
        check(self.activation['runtime_authorized'] is False and self.activation['real_shadow_authorized'] is False,'CANDIDATE_ACTIVATION_MUST_BE_DISABLED')
        for binding in self.deps['bindings']:exact(self.root,binding)
        self.slot_runtime_policy=json.loads(exact(self.root,dict(path='config/v4_16_r23r1_slot_runtime_policy_v1.json',sha256='427798478357a7411b8f969d3acc7f9220145900e16ade8f0f041dfffa83b4c4',bytes=1150)))
        from workbench_analysis.v4_portable_exact import PortableExact
        portable=PortableExact(self.root)
        self.portability_receipts=[]
        for binding in self.deps['owner_heads'].values():
            _,receipt=portable.read(binding);self.portability_receipts.append(receipt)
        self.registry=json.loads(exact(self.root,self.deps['fixture_registry']))
        self.clock=ClockPolicyResolver(self)
        self.authority=CurrentStageAuthority(self.root)
    def guard(self,write=False):
        activation=json.loads(exact(self.root,self.deps['activation']))
        check(not activation['runtime_authorized'] and not activation['real_shadow_authorized'],'ACTIVATION_DRIFT')
        check(self.mode!='REAL_SHADOW','REAL_SHADOW_NOT_AUTHORIZED')
        if write:check(self.mode in ('CONTRACT_TEST','ENGINEERING_FIXTURE'),'DRY_RUN_NO_ACCEPT')
    def fixture(self,key):
        self.guard();return json.loads(exact(self.root,self.registry['bindings'][key]))
    def database(self,path):
        self.guard(write=True);return ShadowDatabase(self,path)

class ClockPolicyResolver:
    def __init__(self,controller):
        self.c=controller;self.binding=controller.deps['clock'];self.policy=json.loads(exact(controller.root,self.binding))
        check(self.policy['timezone']=='Asia/Shanghai' and self.policy['scheduled_source_cutoff_local']=='21:00:00' and self.policy['observation_publication_deadline_local']=='22:30:00','CLOCK_MISMATCH')
    def resolve(self,trade_date,sessions):
        check(trade_date in sessions,'ACCEPTED_MARKET_SESSION_REQUIRED')
        d=date.fromisoformat(trade_date);tz=timezone(timedelta(hours=8))
        return {k:datetime.combine(d,time(h,m),tz).astimezone(timezone.utc).isoformat().replace('+00:00','Z') for k,h,m in [('scheduled_cutoff_at',21,0),('observation_deadline',22,30)]}

class ShadowDatabase:
    TABLES={'shadow_source_readiness_receipts','shadow_observation_slots','shadow_source_freeze_manifests','shadow_publications','shadow_state_heads','shadow_observations','shadow_first_enrollments','shadow_membership_snapshots','shadow_due_outbox','shadow_outcome_revisions','shadow_health_receipts','shadow_artifacts','shadow_transaction_receipts','shadow_control_receipts','shadow_runtime_operations'}
    def __init__(self,controller,path):
        controller.guard(write=True);self.controller=controller
        self.path=Path(path).resolve();allowed=controller.root/'reports/r23/isolated_db'
        check(self.path.is_relative_to(allowed.resolve()) and self.path.suffix=='.sqlite','ISOLATED_ENGINEERING_DB_ONLY')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path,isolation_level=None,timeout=10)
        self.conn.execute('PRAGMA foreign_keys=ON');self.conn.execute('PRAGMA journal_mode=DELETE')
        sql=exact(controller.root,controller.deps['migration']).decode()
        self.conn.executescript(sql)
    def append(self,table,identity,payload):
        self.controller.guard(write=True);check(table in self.TABLES,'SHADOW_TABLE_ONLY')
        check(payload.get('evidence_origin','ENGINEERING_FIXTURE')!='PIT_OBSERVED','ENGINEERING_CANNOT_CLAIM_PIT')
        check(all(payload.get(k,0)==0 for k in ('REAL_SHADOW_OBSERVATIONS','PIT_OBSERVED_REAL_SAMPLES')),'ENGINEERING_CANNOT_INCREMENT_REAL_COUNTER')
        value=canonical(payload);sha=hashlib.sha256(value.encode()).hexdigest()
        old=self.conn.execute('SELECT digest FROM '+table+' WHERE id=?',(identity,)).fetchone()
        if old:check(old[0]==sha,'APPEND_ONLY_IDENTITY_CONFLICT');return identity
        self.conn.execute('INSERT INTO '+table+'(id,namespace,evidence_origin,payload,digest) VALUES(?,?,?,?,?)',(identity,'SHADOW_V4','ENGINEERING_FIXTURE',value,sha));return identity
    def rows(self,table):
        check(table in self.TABLES,'SHADOW_TABLE_ONLY');return [json.loads(r[0]) for r in self.conn.execute('SELECT payload FROM '+table+' ORDER BY rowid')]
    def get(self,table,key):
        row=self.conn.execute('SELECT payload FROM '+table+' WHERE id=?',(key,)).fetchone();check(row is not None,'MISSING_DURABLE_RECORD');return json.loads(row[0])
    def transaction(self,fn):
        self.controller.guard(write=True);self.conn.execute('BEGIN IMMEDIATE')
        try:value=fn();self.conn.execute('COMMIT');return value
        except BaseException:self.conn.execute('ROLLBACK');raise
    def close(self):self.conn.close()

class SqlArtifactStore:
    """Accepted V4-15 store protocol inside the same SQLite transaction."""
    def __init__(self,db):self.db=db
    def append(self,kind,identity,payload):
        key=identity if isinstance(identity,str) and len(identity)==64 else digest(identity)
        identity=digest([kind,key]);body=dict(kind=kind,key=key,value=payload)
        self.db.append('shadow_artifacts',identity,body)
        raw=canonical(payload).encode();return dict(path='sqlite:'+identity,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    def read(self,binding):
        if binding['path'].startswith('sqlite:'):
            value=self.db.get('shadow_artifacts',binding['path'][7:])['value'];raw=canonical(value).encode()
            check(hashlib.sha256(raw).hexdigest()==binding['sha256'] and len(raw)==binding['bytes'],'ARTIFACT_DIGEST');return value
        allowed=self.db.controller.registry['bindings'].values();check(binding in allowed,'EXPLICIT_FIXTURE_BINDING_ONLY')
        return json.loads(exact(self.db.controller.root,binding))
    def refs(self,kind):
        result=[]
        for row in self.db.conn.execute('SELECT id,payload FROM shadow_artifacts ORDER BY rowid'):
            p=json.loads(row[1])
            if p['kind']==kind:
                raw=canonical(p['value']).encode();result.append(dict(path='sqlite:'+row[0],sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
        return result

class SourceReadinessReceiptRegistry:
    def __init__(self,db):self.db=db
    def register(self,receipt,consumed_binding):
        r=copy.deepcopy(receipt)
        required={'receipt_id','receipt_kind','source_family','source_identity','source_revision','source_digest','first_observed_at','system_available_at','integrity_passed_at','accepted','integrity_pass','target_trade_date','created_at'}
        check(required<=r.keys(),'MISSING_READINESS_RECEIPT')
        check(r['receipt_kind'] in ('FIRST_ACCEPTED_PROVIDER_READINESS_OBSERVATION','ACCEPTED_LOCAL_OBSERVATION_ACQUISITION'),'RECEIPT_KIND')
        check(r.get('evidence_origin')=='ENGINEERING_FIXTURE','ENGINEERING_RECEIPT_ONLY')
        check(r['source_digest']==consumed_binding['sha256'],'SOURCE_DIGEST_MISMATCH')
        check(consumed_binding in self.db.controller.registry['bindings'].values(),'NO_RAW_PROVIDER_FALLBACK')
        raw=exact(self.db.controller.root,consumed_binding)
        check(r['accepted'] is True and r['integrity_pass'] is True,'SOURCE_NOT_ACCEPTED')
        first,system,integrity,created=(utc(r[k]) for k in ('first_observed_at','system_available_at','integrity_passed_at','created_at'))
        check(first<=integrity<=system<=created,'READINESS_ORDER')
        check(r.get('provider_at',r['first_observed_at'])==r['first_observed_at'],'BACKDATED_READINESS')
        # Engineering first observation is independently frozen in the fixture registry.
        expected=self.db.controller.registry['readiness_observations'].get(r['receipt_id'])
        check(expected==r['first_observed_at'],'BACKDATED_OR_UNREGISTERED_READINESS')
        r['consumed_binding']=consumed_binding
        self.db.append('shadow_source_readiness_receipts',r['receipt_id'],r);return r['receipt_id']

class ObservationSlotPlanner:
    def __init__(self,db):self.db=db
    def validate(self,slot):
        fields=json.loads(exact(self.db.controller.root,self.db.controller.deps['slot']))['fields']
        check(set(fields)<=slot.keys(),'MISSING_SLOT_FIELD')
        check(slot['execution_mode']=='SHADOW' and slot['namespace']=='SHADOW_V4','SLOT_NAMESPACE')
        check(slot['parameter_set_id']==self.db.controller.registry['parameter_set_id'],'PARAMETER_CHANGE_WITHOUT_NEW_IDENTITY')
        check(slot['capability_scope']==sorted(set(slot['capability_scope'])),'SLOT_SCOPE')
        check(slot['field_quality']=={k:('NOT_YET_AVAILABLE' if slot[k] is None else 'KNOWN') for k in fields},'SLOT_FIELD_QUALITY')
        if slot['slot_status']=='ACCEPTED_ON_TIME':
            check(all(slot[k] is not None for k in fields),'NULL_ACCEPTED_SLOT_FIELD')
            check(slot['core_revision']==slot['publication_id'],'CORE_REVISION_IDENTITY')
            provider,system,cutoff,start,finish,accepted,deadline=(utc(slot[k]) for k in ('source_provider_available_at','system_available_at','scheduled_cutoff_at','computation_started_at','computation_finished_at','accepted_at','observation_deadline'))
            check(provider<=system<=cutoff and system<=start<=finish<=accepted<=deadline,'SLOT_TIME_ORDER')
        return slot
    def quality(self,slot):
        fields=json.loads(exact(self.db.controller.root,self.db.controller.deps['slot']))['fields']
        slot['quality_contract']='V4_16_R23R1_SLOT_RUNTIME_POLICY_V1'
        slot['field_quality']={k:('NOT_YET_AVAILABLE' if slot[k] is None else 'KNOWN') for k in fields}
        return self.validate(slot)
    def visibility(self,slot,receipt_ids):
        receipts=[]
        for key in receipt_ids:
            try:receipts.append(self.db.get('shadow_source_readiness_receipts',key))
            except ValueError as error:
                if str(error)!='MISSING_DURABLE_RECORD':raise
        for field,source in [('source_provider_available_at','first_observed_at'),('system_available_at','system_available_at')]:
            slot[field]=max((r[source] for r in receipts),key=utc,default=None)
        slot['visibility_receipt_ids']=[r['receipt_id'] for r in receipts]
        slot['visibility_complete']=len(receipts)==len(receipt_ids) and bool(receipt_ids)
    def plan(self,request):
        check(isinstance(request.get('capabilities'),list) and bool(request['capabilities']) and all(isinstance(k,str) and k for k in request['capabilities']),'EXPLICIT_CAPABILITY_SCOPE_REQUIRED')
        identity=[request[k] for k in ('model_contract_id','state_lineage_id','trade_date')]
        times=self.db.controller.clock.resolve(request['trade_date'],self.db.controller.authority.sessions)
        for k,v in times.items():check(request.get(k,v)==v,'CLOCK_MISMATCH')
        fields=json.loads(exact(self.db.controller.root,self.db.controller.deps['slot']))['fields']
        slot=dict.fromkeys(fields)
        slot.update(slot_id=digest(identity),**dict(zip(('model_contract_id','state_lineage_id','trade_date'),identity)),**times,parameter_set_id=request['parameter_set_id'],execution_mode='SHADOW',namespace='SHADOW_V4',capability_scope=sorted(set(request.get('capabilities',[]))),slot_status='PLANNED',evidence_origin='ENGINEERING_FIXTURE')
        self.visibility(slot,request.get('receipt_ids',[]))
        return self.quality(slot)
    def ready(self,slot,receipt_ids):
        if not receipt_ids:return 'BLOCKED_SOURCE_NOT_READY'
        for key in receipt_ids:
            r=self.db.get('shadow_source_readiness_receipts',key)
            check(r['target_trade_date']==slot['trade_date'],'SOURCE_TRADE_DATE_MISMATCH')
            if utc(r['system_available_at'])>utc(slot['scheduled_cutoff_at']):return 'MISSED_OBSERVATION_SLOT'
        return 'PLANNED'
    def record(self,request):
        slot=self.plan(request)
        try:state=self.ready(slot,request['receipt_ids'])
        except ValueError as error:
            if str(error)=='MISSING_DURABLE_RECORD':state='BLOCKED_SOURCE_NOT_READY'
            else:raise
        history=[p for p in self.db.rows('shadow_observation_slots') if p['slot_id']==slot['slot_id'] and p['slot_status']!='ACCEPTED_ON_TIME']
        if any(p['slot_status']=='MISSED_OBSERVATION_SLOT' for p in history):state='MISSED_OBSERVATION_SLOT'
        existing=next((p for p in history if p['slot_status']==state),None)
        if existing:return existing
        slot.update(slot_status=state,revision=-len(history),sample_class='ENGINEERING_ONLY')
        self.quality(slot)
        self.db.append('shadow_observation_slots',digest([slot['slot_id'],state]),slot);return slot

class ShadowPriorStateReader:
    def __init__(self,db):self.db=db
    def read(self,slot,namespace='SHADOW_V4'):
        check(namespace=='SHADOW_V4','LEGACY_PRIOR_FORBIDDEN')
        sessions=self.db.controller.authority.sessions;i=sessions.index(slot['trade_date']);check(i>0,'SEPARATE_ACCEPTED_INITIALIZATION_REQUIRED')
        prev=sessions[i-1]
        previous_slot=digest([slot['model_contract_id'],slot['state_lineage_id'],prev])
        head=self.db.conn.execute('SELECT publication_id FROM shadow_publication_heads WHERE slot_id=?',(previous_slot,)).fetchone()
        if head:
            publication=self.db.get('shadow_publications',head[0]);state=self.db.get('shadow_state_heads',head[0])
            check(publication['trade_date']==prev and state['trade_date']==prev,'PREVIOUS_SHADOW_HEAD_IDENTITY')
            return state
        # Separate engineering boundary, never an initialization authority for real Shadow.
        seed=self.db.controller.fixture('seed')
        check(seed['trade_date']==prev and seed['model_contract_id']==slot['model_contract_id'] and seed['state_lineage_id']==slot['state_lineage_id'],'GAP_FAIL_CLOSED')
        stored=self.db.conn.execute('SELECT payload FROM shadow_state_heads WHERE id=?',('R23_ISOLATED_SEED',)).fetchone()
        check(stored is not None and json.loads(stored[0])==seed,'GAP_FAIL_CLOSED')
        return seed

class MandatorySourceFreezeBuilder:
    def __init__(self,db):self.db=db
    def build(self,slot,request,prior):
        receipts=[self.db.get('shadow_source_readiness_receipts',k) for k in request['receipt_ids']]
        check({r['source_family'] for r in receipts}=={'OWNER_OUTPUT','T0_SNAPSHOT'},'MANDATORY_SOURCE_SET_INCOMPLETE')
        check(len(receipts)==2,'MANDATORY_SOURCE_SET_EXACT')
        for r in receipts:check(r['consumed_binding']==request['owner_fixture' if r['source_family']=='OWNER_OUTPUT' else 'snapshot_fixture'],'CONSUMED_SOURCE_NOT_FROZEN')
        for r in receipts:check(r['target_trade_date']==slot['trade_date'] and utc(r['system_available_at'])<=utc(slot['scheduled_cutoff_at']),'FUTURE_OR_LATE_SOURCE')
        head=self.db.controller.authority
        freeze=dict(trade_date=slot['trade_date'],calendar_identity=head.calendar_ref,universe_identity=head.identity_ref,membership_identity=head.membership_ref,mandatory_source_receipt_ids=request['receipt_ids'],mandatory_source_digests=[r['source_digest'] for r in receipts],optional_source_receipts=request.get('optional_receipts',[]),model_contract_id=slot['model_contract_id'],parameter_set_id=request['parameter_set_id'],state_lineage_id=slot['state_lineage_id'],prior_session_state_head=prior,scheduled_cutoff_at=slot['scheduled_cutoff_at'],observation_deadline=slot['observation_deadline'],evidence_origin='ENGINEERING_FIXTURE')
        freeze['source_manifest_digest']=digest(freeze);return freeze

class AcceptedBusinessProducerAdapter:
    """Exact owner output fixtures; executable unchanged accepted V4-15 adapters.

V4-10..14 live Shadow producer capabilities are not fabricated: this disabled
candidate accepts only version-bound immutable engineering owner output fixtures.
"""
    def __init__(self,db):
        self.db=db;self.store=SqlArtifactStore(db);self.authority=db.controller.authority.publication_authority()
        self.radar=RadarCohortRuntime(self.authority,self.store)
        self.settlement=SettlementRuntime(db.controller.authority,self.store)
    def project(self,request):
        check(not set(request.get('capabilities',[]))&set(self.db.controller.deps['blocked_capabilities']),'BLOCKED_A04_A08_CAPABILITY')
        check(request.get('owner_heads')==self.db.controller.deps['owner_heads'],'VERSIONED_OWNER_BINDING_REQUIRED')
        check(request.get('raw_provider_fallback') is not True,'NO_RAW_PROVIDER_FALLBACK')
        check(not any(request.get(k) for k in ('ui_exclusion','focus_filter','fep_prediction','increment_real_counter')),'FORBIDDEN_FEEDBACK_OR_REAL_COUNTER')
        fixture_binding=request['owner_fixture'];check(fixture_binding==self.db.controller.registry['bindings'][request['fixture_key']],'EXACT_OWNER_FIXTURE_REQUIRED')
        fixture=self.store.read(fixture_binding)
        for row in fixture['rows']:
            check(row['model_contract_id']==request['model_contract_id'] and row['state_lineage_id']==request['state_lineage_id'],'MODEL_LINEAGE_MISMATCH')
            check(row['parameter_set_id']==request['parameter_set_id'],'PARAMETER_IDENTITY_MISMATCH')
        check(len({(r['entity_type'],r['entity_id']) for r in fixture['rows']})==len(fixture['rows']),'DUPLICATE_OWNER_ENTITY')
        check(fixture['trade_date']==request['trade_date'],'OWNER_DATE_MISMATCH')
        radar_ref=self.radar.engineering_fixture(fixture_binding);return self.store.read(radar_ref),radar_ref
    def accepted_producer(self,stage):
        """Version-bound callable wiring; caller supplies accepted owner inputs.

        The disabled runtime does not synthesize missing business capabilities.
        Engineering E2E uses frozen owner outputs rather than live inputs.
        """
        self.db.controller.guard()
        check(stage in self.db.controller.deps['owner_heads'],'VERSIONED_OWNER_REQUIRED')
        if stage=='v4_10':
            from src.v4.stock_prewatch import evaluate
            return evaluate
        if stage=='v4_11':
            from src.v4.confirmation import detect_confirmation
            return detect_confirmation
        if stage=='v4_12':
            from workbench_analysis.v4_12_structure_engine import StructureEngine
            return StructureEngine
        if stage=='v4_13':
            from workbench_analysis.v4_13_profile_runtime import ProfileRuntime
            return ProfileRuntime
        if stage=='v4_14':
            from workbench_analysis.v4_14_precall_runtime import replay
            return replay

class RealtimeCohortEnrollmentWriter:
    def __init__(self,db,adapter):self.db=db;self.adapter=adapter
    def write(self,radar,request,slot):
        result=[]
        for binding in radar['enrollments']:
            enrollment=self.adapter.store.read(binding)
            old=self.db.conn.execute('SELECT payload FROM shadow_first_enrollments WHERE id=?',(enrollment['enrollment_id'],)).fetchone()
            if old:
                p=json.loads(old[0]);check(p['T0']==enrollment['T0'],'T0_IMMUTABLE');result.append(p);continue
            if request.get('revision',1)>1:
                # A same-day correction may add observations but never a second original.
                existing=[p for p in self.db.rows('shadow_first_enrollments') if p['slot_id']==slot['slot_id']]
                check(not existing,'CORRECTION_NEW_ORIGINAL_FORBIDDEN')
            freeze_ref=self.adapter.settlement.freeze_t0(binding,request['snapshot_fixture'])
            value=dict(enrollment,slot_id=slot['slot_id'],frozen_t0=freeze_ref,evidence_origin='ENGINEERING_FIXTURE',FIRST_OBSERVED=enrollment['enrollment_id'])
            self.db.append('shadow_first_enrollments',enrollment['enrollment_id'],value);result.append(value)
            self.db.append('shadow_runtime_operations',enrollment['enrollment_id'],dict(operation='T0_BENCHMARK_CONTROL_FROZEN',enrollment_id=enrollment['enrollment_id'],frozen_t0=freeze_ref,evidence_origin='ENGINEERING_FIXTURE'))
        return result

class DailyMembershipSnapshotWriter:
    def __init__(self,db):self.db=db
    def write(self,request):
        members=request.get('membership',[])
        for row in members:
            check(row.get('membership_basis')=='ENGINEERING_FIXTURE' and row.get('evidence_origin')=='ENGINEERING_FIXTURE','MEMBERSHIP_REPLAY_CANNOT_CLAIM_PIT')
            check(row['trade_date']==request['trade_date'],'MEMBERSHIP_DATE')
            for k in ('sector_id','security_id','observed_at','system_available_at','source_revision','source_digest','membership_quality'):check(k in row,'MEMBERSHIP_FIELD')
            check(utc(row['observed_at'])<=utc(row['system_available_at']),'MEMBERSHIP_VISIBILITY')
            cutoff=self.db.controller.clock.resolve(request['trade_date'],self.db.controller.authority.sessions)['scheduled_cutoff_at']
            if utc(row['system_available_at'])>utc(cutoff):return 'SECTOR_SCOPE_UNKNOWN_PURE_CORE_CONTINUES'
            self.db.append('shadow_membership_snapshots',digest([row['sector_id'],row['security_id'],row['trade_date'],row['source_revision']]),row)
        return 'ENGINEERING_ONLY' if members else 'SECTOR_SCOPE_UNKNOWN_PURE_CORE_CONTINUES'

class DueOutboxScheduler:
    def __init__(self,db):self.db=db
    def write(self,enrollments):
        for e in enrollments:
            for due in due_plan(self.db.controller.authority.sessions,e['T0'],e['T0']):
                p=dict(due,enrollment_id=e['enrollment_id'],frozen_t0=e['frozen_t0'],evidence_origin='ENGINEERING_FIXTURE')
                self.db.append('shadow_due_outbox',digest([e['enrollment_id'],due['horizon']]),p)

class ShadowHealthReceiptWriter:
    def __init__(self,db):self.db=db
    def write(self,publication_id,slot,membership_status):
        p=dict(publication_id=publication_id,slot_id=slot['slot_id'],publication_success=True,source_quality='ENGINEERING_ONLY',temporal_leakage=False,state_integrity=True,duplicate_episode=False,settlement_backlog=len(self.db.rows('shadow_due_outbox')),clock_compliance=True,model_identity=slot['model_contract_id'],capability_states={k:'BLOCKED_AFFECTED_SCOPE' for k in self.db.controller.deps['blocked_capabilities']},membership_status=membership_status,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,SHADOW_STABLE='NOT_GRANTED',PROVISIONAL_FORWARD_EVIDENCE='NOT_GRANTED',FORWARD_SUPPORTED='NOT_GRANTED',evidence_origin='ENGINEERING_FIXTURE')
        self.db.append('shadow_health_receipts',publication_id,p);return p
    def failure(self,identity,reason,capability='PURE_CORE_STOCK'):
        p=dict(publication_success=False,reason=reason,capability=capability,source_quality='UNKNOWN',clock_compliance=False,REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,SHADOW_STABLE='NOT_GRANTED',PROVISIONAL_FORWARD_EVIDENCE='NOT_GRANTED',FORWARD_SUPPORTED='NOT_GRANTED',evidence_origin='ENGINEERING_FIXTURE')
        self.db.append('shadow_health_receipts',identity,p);return p

class ShadowPublicationBuilder:
    def __init__(self,db):self.db=db
    def build(self,request):
        check(request['parameter_set_id']==self.db.controller.registry['parameter_set_id'],'PARAMETER_CHANGE_WITHOUT_NEW_IDENTITY')
        check(request.get('clock_binding',self.db.controller.deps['clock'])==self.db.controller.deps['clock'],'CLOCK_POLICY_CHANGE_WITHOUT_NEW_VERSION')
        slot=ObservationSlotPlanner(self.db).plan(request)
        check(not any(p['slot_id']==slot['slot_id'] and p['slot_status']=='MISSED_OBSERVATION_SLOT' for p in self.db.rows('shadow_observation_slots')),'MISSED_SLOT_CANNOT_BE_UPGRADED')
        readiness=ObservationSlotPlanner(self.db).ready(slot,request['receipt_ids'])
        check(readiness=='PLANNED',readiness)
        prior=ShadowPriorStateReader(self.db).read(slot,request.get('prior_namespace','SHADOW_V4'))
        freeze=MandatorySourceFreezeBuilder(self.db).build(slot,request,prior)
        latest=max(utc(self.db.get('shadow_source_readiness_receipts',i)['system_available_at']) for i in request['receipt_ids'])
        start,finish,accepted=(utc(request[k]) for k in ('computation_started_at','computation_finished_at','accepted_at'))
        check(latest<=start<=finish<=accepted<=utc(slot['observation_deadline']),'MISSED_OR_INVALID_COMPUTATION_TIME')
        return slot,prior,freeze

class ShadowPublicationAcceptanceTransaction:
    def __init__(self,db):self.db=db
    def accept(self,request,fail_at=None):
        self.db.controller.guard(write=True)
        check(not self.db.rows('shadow_control_receipts'),'SHADOW_STOPPED_RESTART_REQUIRES_AUTHORITY')
        request=copy.deepcopy(request);revision=request.get('revision',1)
        publication_id=digest([request['model_contract_id'],request['state_lineage_id'],request['trade_date'],revision])
        old=self.db.conn.execute('SELECT payload FROM shadow_publications WHERE id=?',(publication_id,)).fetchone()
        if old:
            p=json.loads(old[0]);check(p['request_digest']==digest(request),'PUBLICATION_REVISION_CONFLICT');return p
        def transaction():
            slot,prior,freeze=ShadowPublicationBuilder(self.db).build(request)
            current=self.db.conn.execute('SELECT publication_id,revision FROM shadow_publication_heads WHERE slot_id=?',(slot['slot_id'],)).fetchone()
            check((current is None and revision==1) or (current is not None and revision==current[1]+1),'PUBLICATION_HEAD_CAS_FAILED')
            check(request.get('expected_head',current[0] if current else None)==(current[0] if current else None),'PUBLICATION_HEAD_CAS_FAILED')
            self.db.append('shadow_source_freeze_manifests',freeze['source_manifest_digest'],freeze)
            adapter=AcceptedBusinessProducerAdapter(self.db);radar,radar_ref=adapter.project(request)
            check(not request.get('force_new_original'),'CORRECTION_NEW_ORIGINAL_FORBIDDEN')
            enrollments=RealtimeCohortEnrollmentWriter(self.db,adapter).write(radar,request,slot)
            for obs_ref in radar['observations']:
                obs=adapter.store.read(obs_ref)
                previous=[p for p in self.db.rows('shadow_observations') if p['logical_event_id']==obs['logical_event_id'] and p['slot_id']==slot['slot_id']]
                predecessor=max(previous,key=lambda p:p['revision']) if previous else None
                check(predecessor is None or predecessor['revision']<revision,'OBSERVATION_REVISION_ORDER')
                expected=predecessor['observation_id'] if predecessor and obs['source_correction'] else None
                check(obs.get('supersedes_observation') in (None,expected),'OBSERVATION_PREDECESSOR_MISMATCH')
                self.db.append('shadow_observations',obs['observation_id'],dict(obs,slot_id=slot['slot_id'],revision=revision,shadow_publication_id=publication_id,supersedes_observation=expected,evidence_origin='ENGINEERING_FIXTURE'))
            if fail_at=='cohort':raise ValueError('INJECTED_TRANSACTION_FAILURE')
            DueOutboxScheduler(self.db).write(enrollments)
            membership=DailyMembershipSnapshotWriter(self.db).write(request)
            slot.update(slot_status='ACCEPTED_ON_TIME',sample_class='ENGINEERING_ONLY',accepted_at=request['accepted_at'],publication_id=publication_id,revision=revision)
            slot.update(core_revision=publication_id,source_manifest_digest=freeze['source_manifest_digest'],computation_started_at=request['computation_started_at'],computation_finished_at=request['computation_finished_at'])
            slot['evaluated_request']=copy.deepcopy(request)
            ObservationSlotPlanner(self.db).quality(slot)
            self.db.append('shadow_observation_slots',digest([slot['slot_id'],revision]),slot)
            health=ShadowHealthReceiptWriter(self.db).write(publication_id,slot,membership)
            p=dict(publication_id=publication_id,slot_id=slot['slot_id'],revision=revision,request_digest=digest(request),source_manifest_digest=freeze['source_manifest_digest'],prior_session_state_head=prior,radar_publication=radar_ref,trade_date=slot['trade_date'],accepted_at=request['accepted_at'],evidence_origin='ENGINEERING_FIXTURE',enrollment_ids=[e['enrollment_id'] for e in enrollments])
            self.db.append('shadow_publications',publication_id,p)
            state=dict(trade_date=slot['trade_date'],model_contract_id=slot['model_contract_id'],state_lineage_id=slot['state_lineage_id'],publication_id=publication_id,revision=revision,owner_output_binding=request['owner_fixture'],evidence_origin='ENGINEERING_FIXTURE')
            self.db.append('shadow_state_heads',publication_id,state)
            if current:
                count=self.db.conn.execute('UPDATE shadow_publication_heads SET publication_id=?,revision=? WHERE slot_id=? AND publication_id=? AND revision=?',(publication_id,revision,slot['slot_id'],current[0],current[1])).rowcount;check(count==1,'PUBLICATION_HEAD_CAS_FAILED')
            else:self.db.conn.execute('INSERT INTO shadow_publication_heads VALUES(?,?,?)',(slot['slot_id'],publication_id,revision))
            if fail_at=='head':raise ValueError('INJECTED_TRANSACTION_FAILURE')
            self.db.append('shadow_transaction_receipts',publication_id,dict(publication_id=publication_id,state='COMMIT_VISIBLE',atomic_entities=['manifest','publication','state','cohort','due','health','head'],evidence_origin='ENGINEERING_FIXTURE'))
            return p
        return self.db.transaction(transaction)

class SettlementWorkerOrchestrator:
    def __init__(self,db):self.db=db
    def run(self,enrollment_id,horizon,source,cutoff,redraw=False):
        self.db.controller.guard(write=True);check(not redraw,'CONTROL_BENCHMARK_REDRAW_FORBIDDEN')
        e=self.db.get('shadow_first_enrollments',enrollment_id)
        due=self.db.get('shadow_due_outbox',digest([enrollment_id,horizon]))
        check(due['due_date'] is not None and due['due_date']<=cutoff,'PRE_DUE_FUTURE_READ_FORBIDDEN')
        if type(source) is AcceptedPriceSource:
            check(source.binding==self.db.controller.authority.data['component_artifacts']['ADJUSTED_DAILY'],'UNACCEPTED_FUTURE_DATA_HEAD')
        else:
            check(type(source) is VectorPriceSource,'NO_RAW_PROVIDER_FALLBACK')
            check(source.binding in self.db.controller.registry['bindings'].values(),'UNACCEPTED_FUTURE_DATA_HEAD')
            payload=json.loads(exact(self.db.controller.root,source.binding))
            check(payload['rows']==source.rows,'FUTURE_SOURCE_DIGEST_MISMATCH')
        def transaction():
            adapter=AcceptedBusinessProducerAdapter(self.db)
            before=len(source.read_log)
            self.db.append('shadow_runtime_operations',digest([enrollment_id,horizon,source.binding]),dict(operation='ACCEPTED_ENGINEERING_FUTURE_READ',enrollment_id=enrollment_id,horizon=horizon,evaluation_source=source.binding,evidence_origin='ENGINEERING_FIXTURE'))
            refs=adapter.settlement.settle(e['frozen_t0'],source,cutoff,horizons=(horizon,))
            for binding in refs:
                outcome=adapter.store.read(binding)
                self.db.append('shadow_outcome_revisions',outcome['outcome_revision_id'],dict(outcome,evidence_origin='ENGINEERING_FIXTURE',future_read_count=len(source.read_log)-before))
            return adapter.settlement.readback(e['frozen_t0'],cutoff)
        return self.db.transaction(transaction)

class ShadowReadbackReader:
    def __init__(self,db):self.db=db
    def read(self):
        return dict(publications=self.db.rows('shadow_publications'),enrollments=self.db.rows('shadow_first_enrollments'),observations=self.db.rows('shadow_observations'),outcomes=self.db.rows('shadow_outcome_revisions'),health=self.db.rows('shadow_health_receipts'),due=self.db.rows('shadow_due_outbox'),REAL_SHADOW_OBSERVATIONS=0,PIT_OBSERVED_REAL_SAMPLES=0,namespace='SHADOW_V4',evidence_origin='ENGINEERING_FIXTURE')

class RollbackController:
    def __init__(self,db):self.db=db
    def stop(self,delete_observations=False):
        self.db.controller.guard(write=True);check(not delete_observations,'ROLLBACK_DELETE_FORBIDDEN')
        p=dict(stop_new_acceptance=True,preserve_accepted_artifacts=True,preserve_pending_obligations=True,legacy_mutated=False,reader_selection='LEGACY_UNCHANGED',restart_requires='NEW_EXPLICIT_ACCEPTED_AUTHORITY',evidence_origin='ENGINEERING_FIXTURE')
        self.db.append('shadow_control_receipts','STOP_SHADOW',p);return p
    def restart(self):raise ValueError('RESTART_NOT_AUTHORIZED')
