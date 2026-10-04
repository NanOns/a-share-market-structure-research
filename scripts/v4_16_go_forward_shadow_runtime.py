"""R24R1 go-forward successor. Committed authority disabled; no CLI/env grants.

Simulation uses an explicit isolated dependency manifest and a distinct database
origin. No engineering fixture is ever admitted to real storage.
"""
import copy
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from scripts.v4_16_shadow_runtime import canonical, digest, check, exact, utc, ClockPolicyResolver
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority
from workbench_analysis.v4_16_go_forward_authority import GoForwardInputAuthority
from scripts.v4_16_real_owner_projection_v1 import RealOwnerProjectionV1
from workbench_analysis.v4_15_settlement import SettlementRuntime, AcceptedPriceSource, VectorPriceSource, due_plan

def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def dependency_digest(deps):
    return digest({k:v for k,v in deps.items() if k not in ('activation','bindings')} | {
        'bindings':[b for b in deps['bindings'] if b != deps['activation']]})

def grant_digest(authority):
    return digest({k:v for k,v in authority.items() if k != 'external_acceptance'})

class RealShadowController:
    def __init__(self, root, simulation_dependencies=None):
        self.root=Path(root).resolve()
        self.simulation=simulation_dependencies is not None
        path=simulation_dependencies or 'config/v4_16_runtime_dependencies_v3.json'
        if self.simulation:
            check((self.root/path).resolve().is_relative_to(self.root/'reports/r24r1/activation_simulation'), 'ISOLATED_SIMULATION_MANIFEST_REQUIRED')
        self.dependency_path=path
        self.dependency_bytes=(self.root/path).read_bytes()
        self.deps=json.loads(self.dependency_bytes)
        self.activation=json.loads(exact(self.root,self.deps['activation']))
        # Nothing that observes source availability or opens storage precedes this.
        check(self.activation['runtime_authorized'] is True and self.activation['real_shadow_authorized'] is True,
              'REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION')
        check(self.activation['environment_class']==('ACTIVATION_SIMULATION' if self.simulation else 'REAL'),'AUTHORITY_ENVIRONMENT_MISMATCH')
        check(not any(self.activation[k] for k in ('production','focus','V4_16')),'NON_SHADOW_PERMISSION_FORBIDDEN')
        for binding in self.deps['bindings']: exact(self.root,binding)
        self.grant=self.activation['grant']
        check(self.grant is not None and set(self.activation['required_grant_fields'])<=self.grant.keys(),'INCOMPLETE_ACTIVATION_GRANT')
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

    def guard(self):
        check((self.root/self.dependency_path).read_bytes()==self.dependency_bytes,'DEPENDENCY_MANIFEST_DRIFT')
        check(json.loads(exact(self.root,self.deps['activation']))==self.activation,'ACTIVATION_DRIFT')
        for binding in self.deps['bindings']:exact(self.root,binding)

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
        check(not set(caps)&set(self.deps['blocked_capabilities']),'BLOCKED_CAPABILITY')
        check(request.get('prior_namespace','SHADOW_V4')=='SHADOW_V4','CROSS_NAMESPACE_PRIOR')
        check(not request.get('raw_provider_fallback'),'NO_RAW_PROVIDER_FALLBACK')

    def database(self,path):
        self.guard()
        return RealShadowDatabase(self,path)

class RealShadowDatabase:
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
                check(tables<= {'storage_identity','facts','publication_heads','activation_head'},'ENGINEERING_OR_LEGACY_DATABASE_FORBIDDEN')
            finally:existing.close()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path,isolation_level=None)
        self.conn.executescript(exact(controller.root,controller.deps['migration']).decode())
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

class RealSourceReadinessAdapter:
    """Only acquisition assigns clocks. A request cannot supply first_observed_at."""
    def __init__(self,db):self.db=db
    def acquire(self,family,trade_date,binding,clock=None,**metadata):
        c=self.db.controller
        c.guard()
        check(not metadata,'CALLER_BACKDATED_READINESS_FORBIDDEN')
        check(clock is None or c.simulation,'REAL_CLOCK_OVERRIDE_FORBIDDEN')
        clock=clock or now
        accepted=c.sources['sources'].get(family)
        check(accepted is not None and accepted['binding']==binding,'NO_RAW_PROVIDER_FALLBACK')
        check(accepted['target_trade_date']==trade_date,'SOURCE_TARGET_DATE_MISMATCH')
        first=clock()
        raw=exact(c.root,binding)
        payload=json.loads(raw)
        check(c.simulation or payload.get('evidence_class') in ('REALTIME_ACCEPTED_SOURCE','PIT_OBSERVED'), 'NON_PIT_SOURCE_FORBIDDEN')
        check(c.simulation or not payload.get('radar_owner_events'),'ENGINEERING_OWNER_EVENTS_FORBIDDEN')
        integrity=clock()
        system=clock()
        created=clock()
        check(utc(first)<=utc(integrity)<=utc(system)<=utc(created),'READINESS_ORDER')
        key=digest([family,trade_date,binding])
        prior=[p for p in self.db.rows('receipt') if p['receipt_id']==key]
        if prior:return prior[0]
        p=dict(receipt_id=key,source_family=family,source_identity=accepted['source_identity'],
          source_revision=accepted['source_revision'],source_digest=hashlib.sha256(raw).hexdigest(),
          first_observed_at=first,integrity_passed_at=integrity,system_available_at=system,created_at=created,
          target_trade_date=trade_date,provider=accepted['provider'],receipt_kind=c.adapters['receipt_kind'],
          accepted_source_authority=c.grant['source_authority'],consumed_binding=binding)
        return self.db.append('receipt',key,p)

class RealArtifactStore:
    def __init__(self,db):self.db=db
    def append(self,kind,identity,payload):
        key=digest([kind,identity])
        self.db.append('artifact',key,dict(kind=kind,value=payload))
        raw=canonical(payload).encode()
        return dict(path='sqlite:'+key,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    def read(self,binding):
        if binding['path'].startswith('sqlite:'):
            value=self.db.get('artifact',binding['path'][7:])['value']
            raw=canonical(value).encode()
            check(hashlib.sha256(raw).hexdigest()==binding['sha256'] and len(raw)==binding['bytes'],'ARTIFACT_DIGEST')
            return value
        check(binding in [v['binding'] for v in self.db.controller.sources['sources'].values()], 'ACCEPTED_SOURCE_ONLY')
        return json.loads(exact(self.db.controller.root,binding))
    def refs(self,kind):
        out=[]
        for p in self.db.rows('artifact'):
            if p['kind']==kind:
                raw=canonical(p['value']).encode()
                key=self.db.conn.execute("SELECT id FROM facts WHERE kind='artifact' AND payload=?",(canonical(p),)).fetchone()[0]
                out.append(dict(path='sqlite:'+key,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
        return out

class SettlementObligationController:
    """Resume accepted obligations even when the current launch authority is off.

    Reads an already existing successor database and its exact accepted activation
    history. This controller cannot initialize storage or accept a publication.
    """
    def __init__(self,root,path,simulation=False):
        self.root=Path(root).resolve()
        self.simulation=simulation
        self.origin='ACTIVATION_SIMULATION' if simulation else 'PIT_OBSERVED'
        self.dependency_path='config/v4_16_runtime_dependencies_v3.json'
        self.dependency_bytes=(self.root/self.dependency_path).read_bytes()
        self.deps=json.loads(self.dependency_bytes)
        self.guard()
        self.storage=json.loads(exact(self.root,self.deps['storage']))
        path=Path(path).resolve()
        allowed=(self.root/self.storage['simulation_root' if simulation else 'real_root']).resolve()
        check(allowed.is_relative_to(self.root) and path.is_relative_to(allowed) and path.exists(),'EXISTING_ACCEPTED_OBLIGATION_DATABASE_REQUIRED')
        conn=sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)
        try:
            check(conn.execute('SELECT environment,evidence_origin FROM storage_identity').fetchall()==[
                ('ACTIVATION_SIMULATION' if simulation else 'REAL',self.origin)],'OBLIGATION_STORAGE_IDENTITY')
            rows=conn.execute("SELECT payload,digest FROM facts WHERE kind='activation'").fetchall()
            check(bool(rows),'NO_ACCEPTED_ACTIVATION_HISTORY')
            for raw,sha in rows:check(hashlib.sha256(raw.encode()).hexdigest()==sha,'ACTIVATION_HISTORY_DIGEST')
            binding=json.loads(rows[-1][0])['authority_binding']
            check(conn.execute("SELECT count(*) FROM facts WHERE kind='enrollment'").fetchone()[0]>0,'NO_ACCEPTED_SETTLEMENT_OBLIGATIONS')
        finally:conn.close()
        self.activation=json.loads(exact(self.root,binding))
        acceptance=json.loads(exact(self.root,self.activation['external_acceptance']))
        check(acceptance['authority_digest']==grant_digest(self.activation) and
              acceptance['decision']==('SIMULATION_ONLY_NOT_REAL_ACCEPTANCE' if simulation else 'PASS_REAL_SHADOW_ACTIVATION'),'UNACCEPTED_OBLIGATION_AUTHORITY')
        self.grant=self.activation['grant']
        check(self.grant['storage_identity']['database_path']==path.relative_to(self.root).as_posix(),'OBLIGATION_DATABASE_NOT_BOUND')
        self.sources=json.loads(exact(self.root,self.grant['source_authority']))
        self.authority=GoForwardInputAuthority(self.root,self.deps['go_forward_input'],self.grant['daily_input_authority'],self.grant,self.grant['daily_input_boundary'],self.simulation)

    def guard(self):
        check((self.root/self.dependency_path).read_bytes()==self.dependency_bytes,'SETTLEMENT_DEPENDENCY_DRIFT')
        for binding in self.deps['bindings']:exact(self.root,binding)

    def verify_request(self,request):
        raise ValueError('SETTLEMENT_ONLY_CANNOT_ACCEPT_PUBLICATION')

    def database(self,path):
        self.guard()
        check(Path(path).exists(),'SETTLEMENT_ONLY_CANNOT_INITIALIZE_STORAGE')
        return RealShadowDatabase(self,path)

class OneSessionLaunchController:
    def __init__(self,db):self.db=db
    def prior(self,request):
        c=self.db.controller
        d=request['trade_date']
        i=c.authority.sessions.index(d)
        check(i>0,'NO_PREVIOUS_ACCEPTED_SESSION')
        previous=c.authority.sessions[i-1]
        same_slot=digest([request[k] for k in ('model_contract_id','state_lineage_id','trade_date')])
        same_day=[p for p in self.db.rows('publication') if p['slot_id']==same_slot]
        if same_day:
            original=min(same_day,key=lambda p:p['revision'])
            return self.db.get('manifest',original['source_manifest_digest'])['prior']
        states=[p for p in self.db.rows('state') if p['trade_date']==previous and
                p['model_contract_id']==request['model_contract_id'] and p['state_lineage_id']==request['state_lineage_id']]
        if states:return max(states,key=lambda p:p['revision'])
        check(not self.db.rows('state') and d==c.grant['first_trade_date'],'PREVIOUS_SHADOW_SESSION_GAP')
        seed=json.loads(exact(c.root,c.grant['predecessor']))
        check(seed.get('publication_id')!='R23_ISOLATED_SEED' and seed.get('evidence_origin')!='ENGINEERING_FIXTURE','ENGINEERING_SEED_FORBIDDEN')
        check(seed['evidence_class'] in c.boundary['predecessor_evidence_classes'],'UNACCEPTED_INITIALIZATION_CLASS')
        check(seed['trade_date']==previous and seed['namespace']=='SHADOW_V4','BOUNDARY_PREDECESSOR_MISMATCH')
        for k in ('model_contract_id','parameter_set_id','state_lineage_id'):
            check(seed[k]==request[k],'BOUNDARY_IDENTITY_MISMATCH')
        return dict(boundary_contract=c.deps['initialization_boundary'],accepted_predecessor=c.grant['predecessor'],
                    trade_date=previous,initialization={k:seed[k] for k in c.boundary['initialization_fields']},
                    unknown={k:'UNKNOWN' for k in c.boundary['unknown_fields']},counts_as_prior_real_observation=False)

    def run(self,request,clock=None,fail_at=None):
        c=self.db.controller
        c.verify_request(request)
        accepted_days=[d for d in self.db.rows('daily_input') if d['target_trade_date']==request['trade_date']]
        check(not accepted_days or c.authority.daily['revision']>=max(d['revision'] for d in accepted_days),'DAILY_REVISION_ROLLBACK')
        check(all(d['revision']!=c.authority.daily['revision'] or d['daily_input_digest']==c.authority.daily['daily_input_digest'] for d in accepted_days),'DAILY_REVISION_CONFLICT')
        check(clock is None or c.simulation,'REAL_CLOCK_OVERRIDE_FORBIDDEN')
        clock=clock or now
        if not c.simulation:
            current_time=clock()
            from datetime import timedelta
            check(utc(current_time).astimezone(timezone(timedelta(hours=8))).date().isoformat()==request['trade_date'],'REAL_REQUEST_DATE_MISMATCH')
            check(utc(current_time)>=utc(c.grant['effective_from']),'AUTHORITY_NOT_YET_EFFECTIVE')
        check(not self.db.rows('control'),'SHADOW_STOPPED')
        r=copy.deepcopy(request)
        slot_id=digest([r[k] for k in ('model_contract_id','state_lineage_id','trade_date')])
        revision=r.get('revision',1)
        pid=digest([slot_id,revision])
        prior_publications=[p for p in self.db.rows('publication') if p['publication_id']==pid]
        if prior_publications:
            check(prior_publications[0]['request_digest']==digest(r),'PUBLICATION_REVISION_CONFLICT')
            return prior_publications[0]
        # Readiness is an acquisition fact, retained even if publication rolls
        # back. BEGIN IMMEDIATE locks the day's plan before observing sources.
        def acquire():
            validate_daily_revision(self.db,c.authority.daily)
            active=self.db.conn.execute('SELECT authority_id FROM activation_head WHERE singleton=1').fetchone()
            check((active is None and c.grant['expected_prior_activation_head'] is None) or
                  (active is not None and active[0] in (c.activation['authority_id'],c.grant['expected_prior_activation_head'])),'ACTIVATION_HEAD_CAS_CONFLICT')
            self.prior(r)
            check(not any(p['slot_id']==slot_id for p in self.db.rows('missed_slot')),'MISSED_SLOT_CANNOT_UPGRADE')
            self.db.append('slot_plan',slot_id,dict(slot_id=slot_id,trade_date=r['trade_date'],model_contract_id=r['model_contract_id'],state_lineage_id=r['state_lineage_id']))
            times=c.clock.resolve(r['trade_date'],c.authority.sessions)
            receipts=[]
            adapter=RealSourceReadinessAdapter(self.db)
            for family in c.adapters['mandatory_families']:
                check(family in c.sources['sources'],'MISSING_MANDATORY_SOURCE')
                receipts.append(adapter.acquire(family,r['trade_date'],c.sources['sources'][family]['binding'],clock=clock))
            return times,receipts
        times,receipts=self.db.transaction(acquire)
        provider=max(p['first_observed_at'] for p in receipts)
        system=max(p['system_available_at'] for p in receipts)
        if utc(system)>utc(times['scheduled_cutoff_at']):
            self.db.transaction(lambda:self.db.append('missed_slot',slot_id,dict(slot_id=slot_id,slot_status='MISSED_OBSERVATION_SLOT',trade_date=r['trade_date'])))
            return dict(slot_status='MISSED_OBSERVATION_SLOT')
        def accept():
            validate_daily_revision(self.db,c.authority.daily)
            active=self.db.conn.execute('SELECT authority_id FROM activation_head WHERE singleton=1').fetchone()
            if not active:
                check(c.grant['expected_prior_activation_head'] is None,'ACTIVATION_HEAD_CAS_CONFLICT')
                self.db.conn.execute('INSERT INTO activation_head VALUES(1,?)',(c.activation['authority_id'],))
            elif active[0]!=c.activation['authority_id']:
                check(active[0]==c.grant['expected_prior_activation_head'],'ACTIVATION_HEAD_CAS_CONFLICT')
                count=self.db.conn.execute('UPDATE activation_head SET authority_id=? WHERE singleton=1 AND authority_id=?',
                    (c.activation['authority_id'],active[0])).rowcount
                check(count==1,'ACTIVATION_HEAD_CAS_CONFLICT')
            self.db.append('activation',c.activation['authority_id'],dict(authority_binding=c.deps['activation'],
                authority_id=c.activation['authority_id'],expected_prior_activation_head=c.grant['expected_prior_activation_head']))
            current=self.db.conn.execute('SELECT publication_id,revision FROM publication_heads WHERE slot_id=?',(slot_id,)).fetchone()
            check(revision==(current[1]+1 if current else 1) and r.get('expected_head')==(current[0] if current else None),'PUBLICATION_HEAD_CAS_CONFLICT')
            check(not any(p['slot_id']==slot_id and p['slot_status']=='MISSED_OBSERVATION_SLOT' for p in self.db.rows('missed_slot')),'MISSED_SLOT_CANNOT_UPGRADE')
            prior=self.prior(r)
            start=clock()
            manifest=dict(trade_date=r['trade_date'],model_contract_id=r['model_contract_id'],parameter_set_id=r['parameter_set_id'],
              state_lineage_id=r['state_lineage_id'],receipt_ids=[p['receipt_id'] for p in receipts],
              source_bindings=[p['consumed_binding'] for p in receipts],prior=prior,
              capability_scope=sorted(r['capabilities']),clock=times,dependency_manifest=c.dependency_path,
              calendar_identity=c.authority.calendar_ref,universe_identity=c.authority.identity_ref,
              membership_identity=c.authority.membership_ref,owner_heads=c.deps['owner_heads'],
              daily_input_authority=c.grant['daily_input_authority'],daily_input_digest=c.grant['daily_input_digest'],immutable_data_head=c.deps['accepted_data'],current_audit_head=c.deps['current_audit_head'])
            mid=digest(manifest)
            self.db.append('manifest',mid,manifest)
            store=CandidateArtifactStore(self.db)
            radar=RealOwnerProjectionV1(c.authority.publication_authority(),store)
            owner_binding=c.sources['sources']['OWNER_OUTPUT']['binding']
            owner=store.read(owner_binding)
            check(owner['trade_date']==r['trade_date'],'OWNER_DATE_MISMATCH')
            for row in owner['rows']:
                check(row['entity_type']=='STOCK','UNGRANTED_SECTOR_CAPABILITY')
                check(row['entity_id'] in c.authority.universe,'OWNER_OUTSIDE_ACCEPTED_UNIVERSE')
                for key in ('model_contract_id','parameter_set_id','state_lineage_id'):
                    check(row[key]==r[key],'OWNER_IDENTITY_MISMATCH')
                check(c.simulation or not row.get('radar_owner_events'),'ENGINEERING_EVENT_FORBIDDEN')
            metadata=dict(source_correction=revision>1)
            # V4-15 owns event identity/projection/control semantics. R24 admission
            # promotes only this transaction's timely, exact accepted sources.
            radar_ref=radar._project(owner['rows'],owner.get('events',[]),owner.get('profiles',{}),
                r['trade_date'],pid,owner_binding,'ACTIVATION_SIMULATION' if c.simulation else 'REALTIME_ACCEPTED_SOURCE',metadata,[owner_binding])
            projected=store.read(radar_ref)
            settlement=SettlementRuntime(c.authority,store)
            enrolled=[]
            for binding in projected['enrollments']:
                enrollment=store.read(binding)
                old=[p for p in self.db.rows('enrollment') if p['logical_event_id']==enrollment['logical_event_id']]
                if old:
                    enrolled.append(old[0]);continue
                check(revision==1 and not r.get('force_new_original'),'SECOND_ORIGINAL_ENROLLMENT_FORBIDDEN')
                eid=cohort_identity(c.authority.contracts['cohort_contract'],dict(enrollment,cohort_namespace='FIRST_OBSERVED'))
                enrollment.update(enrollment_id=eid,cohort_namespace='FIRST_OBSERVED',slot_id=slot_id,admission_role='REALTIME_COHORT_ACCEPTANCE',owner_logical_event=enrollment['logical_event_id'],source_manifest_digest=mid,visibility_receipt_ids=[p['receipt_id'] for p in receipts],
                    slot_status='ACCEPTED_ON_TIME',T0=r['trade_date'],FIRST_OBSERVED=eid,observation_deadline=times['observation_deadline'])
                enrollment.update(benchmark_ids={k:digest([eid,k.upper()]) for k in ('market','sector')},
                    control_assignment_ids={k:digest([eid,k]) for k in ('A','B','C')})
                eref=store.append('enrollment_real',eid,enrollment)
                frozen=settlement.freeze_t0(eref,c.sources['sources']['T0_SNAPSHOT']['binding'])
                enrolled.append(dict(enrollment,frozen_t0=frozen))
            check(not r.get('force_new_original'),'SECOND_ORIGINAL_ENROLLMENT_FORBIDDEN')
            for binding in projected['observations']:
                obs=store.read(binding)
                old=[p for p in self.db.rows('observation') if p['logical_event_id']==obs['logical_event_id'] and p['slot_id']==slot_id]
                previous=max(old,key=lambda p:p['revision']) if old else None
                expected=previous['observation_id'] if previous else None
                check(r.get('supersedes_observation',expected)==expected,'INVALID_SUPERSEDES_CHAIN')
                self.db.append('observation',obs['observation_id'],dict(obs,slot_id=slot_id,revision=revision,
                   shadow_publication_id=pid,supersedes_observation=expected))
            if fail_at=='cohort':raise ValueError('INJECTED_TRANSACTION_FAILURE')
            for e in enrolled:
                for due in due_plan(c.authority.sessions,e['T0'],r['trade_date']):
                    self.db.append('due',digest([e['enrollment_id'],due['horizon']]),dict(due,enrollment_id=e['enrollment_id'],frozen_t0=e['frozen_t0']))
            finish=clock()
            accepted=clock()
            check(utc(provider)<=utc(system)<=utc(times['scheduled_cutoff_at']) and utc(system)<=utc(start)<=utc(finish)<=utc(accepted)<=utc(times['observation_deadline']),'MISSED_OBSERVATION_SLOT')
            slot={k:None for k in c.slot_fields}
            slot.update({k:r[k] for k in ('trade_date','model_contract_id','parameter_set_id','state_lineage_id')})
            slot.update(times,source_provider_available_at=provider,system_available_at=system,
               computation_started_at=start,computation_finished_at=finish,accepted_at=accepted,
               execution_mode='SHADOW',namespace='SHADOW_V4',slot_status='ACCEPTED_ON_TIME',publication_id=pid,
               core_revision=pid,source_manifest_digest=mid,capability_scope=sorted(r['capabilities']),slot_id=slot_id,
               revision=revision,visibility_receipt_ids=[p['receipt_id'] for p in receipts])
            check(all(slot[k] is not None for k in c.slot_fields),'NULL_SLOT_FIELD')
            slot.update(quality_contract=json.loads(exact(c.root,c.deps['slot_runtime_policy']))['contract_id'],
                field_quality={k:'KNOWN' for k in c.slot_fields})
            self.db.append('slot',digest([slot_id,revision]),slot)
            for e in enrolled:
                if not any(old['enrollment_id']==e['enrollment_id'] for old in self.db.rows('enrollment')):
                    e.update(accepted_at=accepted,observation_slot=dict(slot_id=slot_id,revision=revision),cohort_acceptance='ACCEPTED_REALTIME_WITH_SLOT')
                    self.db.append('enrollment',e['enrollment_id'],e)
            validate_admission(self.db,slot,enrolled,projected,store)
            self.db.append('daily_input',digest([c.authority.daily['daily_input_id'],c.authority.daily['revision']]),dict(c.authority.daily,authority_binding=c.grant['daily_input_authority']))
            self.db.append('health',pid,dict(publication_id=pid,clock_compliance=True,legacy_mutated=False,
               REAL_SHADOW_OBSERVATIONS=0 if c.simulation else len(self.db.rows('publication'))+1,
               PIT_OBSERVED_REAL_SAMPLES=0 if c.simulation else len(self.db.rows('enrollment'))))
            pub=self.db.append('publication',pid,dict(publication_id=pid,slot_id=slot_id,revision=revision,
               trade_date=r['trade_date'],source_manifest_digest=mid,request_digest=digest(r),radar_publication=radar_ref))
            self.db.append('state',pid,dict(trade_date=r['trade_date'],publication_id=pid,revision=revision,
                model_contract_id=r['model_contract_id'],state_lineage_id=r['state_lineage_id'],owner_state=owner_binding))
            if current:
                count=self.db.conn.execute('UPDATE publication_heads SET publication_id=?,revision=? WHERE slot_id=? AND publication_id=? AND revision=?',(pid,revision,slot_id,*current)).rowcount
                check(count==1,'PUBLICATION_HEAD_CAS_CONFLICT')
            else:self.db.conn.execute('INSERT INTO publication_heads VALUES(?,?,?)',(slot_id,pid,revision))
            if fail_at=='head':raise ValueError('INJECTED_TRANSACTION_FAILURE')
            check(self.db.get('publication',pid)==pub,'PUBLICATION_READBACK_FAILED')
            return pub
        return self.db.transaction(accept)

    def stop(self):
        return self.db.transaction(lambda:self.db.append('control','STOP',dict(stop_new_acceptance=True,
            preserve_accepted_observations=True,preserve_pending_obligations=True,legacy_mutated=False)))

    def settle(self,enrollment_id,horizon,source,cutoff):
        c=self.db.controller
        due=self.db.get('due',digest([enrollment_id,horizon]))
        check(due['due_date'] is not None and due['due_date']<=cutoff,'PRE_DUE_FUTURE_READ_FORBIDDEN')
        c.guard()
        check(type(source) is AcceptedPriceSource or (c.simulation and type(source) is VectorPriceSource),'NO_RAW_PROVIDER_FALLBACK')
        if type(source) is AcceptedPriceSource:
            check(source.binding==c.authority.data['component_artifacts']['ADJUSTED_DAILY'],'UNACCEPTED_FUTURE_ENDPOINT')
        else:
            accepted=c.sources.get('future_binding')
            check(source.binding==accepted and json.loads(exact(c.root,accepted))['rows']==source.rows,'UNACCEPTED_SIMULATED_FUTURE_ENDPOINT')
        def commit():
            store=CandidateArtifactStore(self.db)
            settlement=SettlementRuntime(c.authority,store)
            refs=settlement.settle(due['frozen_t0'],source,cutoff,horizons=(horizon,))
            return [self.db.append('outcome',store.read(b)['outcome_revision_id'],store.read(b)) for b in refs]
        return self.db.transaction(commit)


def cohort_identity(contract, enrollment):
    check(contract['contract_id']=='COHORT_V1' and contract['enrollment_key']==['logical_event_id','cohort_namespace'],'ACCEPTED_COHORT_KEY_REQUIRED')
    return digest([enrollment[k] for k in contract['enrollment_key']])

def validate_daily_revision(db,daily):
    accepted=[d for d in db.rows('daily_input') if d['target_trade_date']==daily['target_trade_date']]
    check(not accepted or daily['revision']>=max(d['revision'] for d in accepted),'DAILY_REVISION_ROLLBACK')
    check(all(d['revision']!=daily['revision'] or d['daily_input_digest']==daily['daily_input_digest'] for d in accepted),'DAILY_REVISION_CONFLICT')

class CandidateArtifactStore(RealArtifactStore):
    def append(self,kind,key,value):
        if kind=='enrollment':
            value=dict(value,admission_role='CANDIDATE_ENROLLMENT_TEMPLATE',cohort_acceptance='NOT_COHORT_ACCEPTANCE')
        return super().append(kind,key,value)

def validate_admission(db,slot,enrollments,projected,store):
    # All writes are provisional inside the same transaction until this succeeds.
    check(slot['slot_status']=='ACCEPTED_ON_TIME','ADMISSION_REQUIRES_ACCEPTED_SLOT')
    events={store.read(b)['logical_event_id']:store.read(b) for b in projected['logical_events']}
    for e in enrollments:
        if e['T0']!=slot['trade_date']:continue  # Preserve previous original identity.
        if any(a['enrollment_id']==e['enrollment_id'] for a in db.rows('realtime_admission')):continue
        check(e['logical_event_id'] in events,'ADMISSION_REQUIRES_EXACT_OWNER_EVENT')
        check(events[e['logical_event_id']]['event_trade_date']==e['T0'],'RECONSTRUCTED_EVENT_CANNOT_UPGRADE')
        check(e['enrollment_id']==cohort_identity(db.controller.authority.contracts['cohort_contract'],e),'COHORT_IDENTITY_MISMATCH')
        e['observation_slot']=dict(slot_id=slot['slot_id'],revision=slot['revision'])
        # Existing fact payload is immutable: the persisted admission links the
        # accepted slot independently, rather than rewriting an enrollment.
        db.append('realtime_admission',e['enrollment_id'],dict(enrollment_id=e['enrollment_id'],
            logical_event_id=e['logical_event_id'],cohort_namespace=e['cohort_namespace'],
            accepted_at=slot['accepted_at'],observation_slot=e['observation_slot'],
            source_manifest_digest=slot['source_manifest_digest'],visibility_receipt_ids=slot['visibility_receipt_ids'],
            owner_event=events[e['logical_event_id']],admission_role='REALTIME_COHORT_ACCEPTANCE'))
