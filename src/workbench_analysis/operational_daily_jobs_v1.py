"""Durable daily jobs with default-on backend scheduling and explicit gates."""
from datetime import datetime,timedelta
from pathlib import Path
import json,sqlite3,threading,uuid
import hashlib
from .operational_daily_calendar_v2 import gap_plan,SHANGHAI
from .operational_daily_storage_v1 import output_path,exclusive_lock

CONTRACT='V4_OPERATIONAL_DAILY_JOBS_V1'
RETRY_TIMES=['19:05','19:35','20:05','20:35','21:05','22:05']
TERMINAL={'PUBLISHED_FULL','PROBE_COMPLETE','NOOP_ALREADY_CURRENT','FAILED_TERMINAL','CANCELLED'}


class DailyJobs:
    def __init__(self,root,executor=None,clock=None):
        self.root=Path(root).resolve();self.clock=clock or (lambda:datetime.now(SHANGHAI))
        self.executor=executor;self.stop=threading.Event();self.thread=None;self.worker_error=None
        self.active_job_id=None
        self.policy_binding=None
        if (self.root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').is_file():
            policy_path=self.root/'config/read_only_operational_daily_release_policy_v1_1.json'
            policy=json.loads(policy_path.read_bytes())
            if policy.get('contract_id')!='READ_ONLY_OPERATIONAL_DAILY_RELEASE_POLICY_V1_1' or any(
                policy.get(key) is not False for key in ['historical_PIT_permission','automated_trading_permission','algorithm_upgrade_permission']):
                raise ValueError('DAILY_POLICY_SCOPE_INVALID')
            task=(self.root/policy['task_contract']['path']).resolve()
            if not task.is_relative_to(self.root) or hashlib.sha256(task.read_bytes()).hexdigest()!=policy['task_contract']['sha256']:
                raise ValueError('DAILY_POLICY_TASK_BINDING_INVALID')
            self.policy_binding=dict(path=policy_path.relative_to(self.root).as_posix(),sha256=hashlib.sha256(policy_path.read_bytes()).hexdigest())
        self.path=output_path(self.root,self.root/'runtime/dynamic_daily/jobs.sqlite3')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS scheduler_policy(id INTEGER PRIMARY KEY, enabled INTEGER, revision INTEGER, updated_at TEXT);
                INSERT OR IGNORE INTO scheduler_policy VALUES(1,1,1,'DEFAULT_AUTO_ON');
                CREATE TABLE IF NOT EXISTS scheduler_dispatch(target TEXT PRIMARY KEY,job_id TEXT);
                CREATE TABLE IF NOT EXISTS scheduler_attempts(target TEXT, attempt_ordinal INTEGER,
                  job_id TEXT UNIQUE,old_job_id TEXT,source_revision TEXT,reason TEXT,created_at TEXT,
                  PRIMARY KEY(target,attempt_ordinal));
                CREATE TABLE IF NOT EXISTS scheduler_rearm(target TEXT PRIMARY KEY,revision TEXT,reason TEXT);
                CREATE TABLE IF NOT EXISTS update_jobs(job_id TEXT PRIMARY KEY, trigger TEXT, mode TEXT,
                  through_date TEXT,status TEXT,created_at TEXT,finished_at TEXT,idempotency_key TEXT UNIQUE,error TEXT);
                CREATE TABLE IF NOT EXISTS update_job_days(job_id TEXT,trade_date TEXT,state TEXT,
                  attempt_count INTEGER DEFAULT 0,next_retry_at TEXT,source_checks TEXT DEFAULT '{}',
                  PRIMARY KEY(job_id,trade_date));
                CREATE TABLE IF NOT EXISTS update_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  job_id TEXT,timestamp TEXT,stage TEXT,event_code TEXT,safe_detail TEXT);
            ''')

    def rearm(self,target,revision,reason='OPERATOR_REARM'):
        """Explicit authorized recovery; never inferred from a user cancellation."""
        if not revision or not reason:raise ValueError('REARM_EVIDENCE_REQUIRED')
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO scheduler_rearm VALUES(?,?,?)',(target,revision,reason))
            self.event(db,None,'REARM',reason,dict(target=target,revision=revision))

    def source_revision(self,target):
        """Local immutable validated freezes only; no network request per tick."""
        from .source_readiness_v2 import source_readiness
        folder=self.root/'data/v4/dynamic_daily_sources/source_readiness'/target
        revisions=[]
        for path in folder.glob('*.json'):
            try:
                record=json.loads(path.read_bytes())
                verdict=source_readiness(target,self.clock(),record['sources'])
                if verdict['source_ready'] and record['source_revision_id']==verdict['source_revision_id']:
                    revisions.append(record['source_revision_id'])
            except (OSError,ValueError,KeyError,TypeError):continue
        # Accepted provider caches can change before a combined readiness record
        # exists. Freeze their byte identities; the executor must still reverify
        # all three sources and downstream QA before deriving/publishing.
        manifest=self.root/'reports/v4_baostock/runtime_acceptance'/target.replace('-','')/'accepted_runtime_manifest.json'
        if manifest.is_file():revisions.append(hashlib.sha256(manifest.read_bytes()).hexdigest())
        return hashlib.sha256(json.dumps(sorted(revisions)).encode()).hexdigest() if revisions else None

    def dispatch(self,plan):
        target=plan['requested_through_date'];revision=self.source_revision(target)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT enabled FROM scheduler_policy WHERE id=1').fetchone()[0]:return
            old=db.execute('SELECT job_id FROM scheduler_dispatch WHERE target=?',(target,)).fetchone()
            previous=self.job(old['job_id']) if old else None
            rearm=db.execute('SELECT * FROM scheduler_rearm WHERE target=?',(target,)).fetchone()
            cancelled_days={r[0] for r in db.execute("SELECT d.trade_date FROM update_job_days d JOIN update_jobs j USING(job_id) WHERE j.status IN ('CANCELLED','CANCEL_REQUESTED')")}
            if cancelled_days.intersection(plan['missing_sessions']) and not rearm:return
            history=db.execute('SELECT * FROM scheduler_attempts WHERE target=? ORDER BY attempt_ordinal DESC LIMIT 1',(target,)).fetchone()
            if previous:
                if previous['status'] not in {'FAILED_TERMINAL','QA_BLOCKED','CANCELLED','CANCELLED_SYSTEM','INTERRUPTED'}:return
                if not history:
                    db.execute('INSERT INTO scheduler_attempts VALUES(?,?,?,?,?,?,?)',
                        (target,1,old['job_id'],None,revision,'LEGACY_DISPATCH_IMPORTED',previous['created_at']))
                    history=db.execute('SELECT * FROM scheduler_attempts WHERE target=?',(target,)).fetchone()
                if previous['status']=='CANCELLED' and not rearm:return
                changed=revision is not None and revision!=history['source_revision']
                if not rearm and not changed and previous['status'] not in {'CANCELLED_SYSTEM','INTERRUPTED'}:return
                if history['attempt_ordinal']>=8 and not rearm:return
            active=db.execute("SELECT job_id FROM update_jobs WHERE mode='CATCH_UP' AND status NOT IN ('PUBLISHED_FULL','NOOP_ALREADY_CURRENT','FAILED_TERMINAL','QA_BLOCKED','CANCELLED','CANCELLED_SYSTEM','INTERRUPTED') LIMIT 1").fetchone()
            if active:
                job=active['job_id']
            else:
                ordinal=history['attempt_ordinal']+1 if history else 1
                job=uuid.uuid4().hex
                db.execute('INSERT INTO update_jobs VALUES(?,?,?,?,?,?,?,?,?)',
                    (job,'SCHEDULER','CATCH_UP',target,'QUEUED',self.clock().isoformat(),None,'AUTO:'+target+':'+str(ordinal),None))
                for day in plan['missing_sessions']:
                    db.execute('INSERT INTO update_job_days(job_id,trade_date,state,next_retry_at) VALUES(?,?,?,?)',
                        (job,day,'QUEUED' if day in plan['eligible_sessions'] else 'SCHEDULED',
                         None if day in plan['eligible_sessions'] else day+'T18:35:00+08:00'))
                db.execute('INSERT INTO scheduler_attempts VALUES(?,?,?,?,?,?,?)',
                    (target,ordinal,job,old['job_id'] if old else None,revision,rearm['reason'] if rearm else 'SOURCE_REVISION_OR_SYSTEM_RECOVERY',self.clock().isoformat()))
                self.event(db,job,'CALENDAR_GAP_PLAN','GAP_PLANNED',plan)
            db.execute('INSERT OR REPLACE INTO scheduler_dispatch VALUES(?,?)',(target,job))
            db.execute('DELETE FROM scheduler_rearm WHERE target=?',(target,))

    def connect(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        return db

    def settings(self,enabled=None):
        with self.connect() as db:
            if enabled is not None:
                if not isinstance(enabled,bool):raise ValueError('ENABLED_BOOLEAN_REQUIRED')
                db.execute('UPDATE scheduler_policy SET enabled=?,revision=revision+1,updated_at=? WHERE id=1',
                           (int(enabled),self.clock().isoformat()))
                self.event(db,None,'SETTINGS','AUTO_RESUMED' if enabled else 'AUTO_PAUSED_BY_USER',{})
            row=dict(db.execute('SELECT * FROM scheduler_policy WHERE id=1').fetchone())
        return dict(contract_id='READ_ONLY_OPERATIONAL_DAILY_RELEASE_POLICY_V1_1',
            auto_enabled=bool(row['enabled']),revision=row['revision'],updated_at=row['updated_at'],
            first_check='18:35',timezone='Asia/Shanghai',retry_times=RETRY_TIMES,
            service_alive=self.thread is not None and self.thread.is_alive(),
            operational_mode='AUTO_ON' if row['enabled'] else 'AUTO_PAUSED_BY_USER',
            permission_scope='READ_ONLY_OPERATIONAL_RESEARCH',publication_ready=(json.loads((self.root/self.policy_binding['path']).read_bytes()).get('publication_ready',False) if self.policy_binding else False),
            policy_binding=self.policy_binding)

    def event(self,db,job,stage,code,detail):
        db.execute('INSERT INTO update_events(job_id,timestamp,stage,event_code,safe_detail) VALUES(?,?,?,?,?)',
                   (job,self.clock().isoformat(),stage,code,json.dumps(detail,ensure_ascii=False)))

    def enqueue(self,through_date=None,mode='CATCH_UP',trigger='MANUAL',key=None):
        if mode not in {'CATCH_UP','PROBE'}:raise ValueError('MODE_NOT_ALLOWED')
        plan=gap_plan(self.root,self.clock(),through_date)
        if plan['status']=='CALENDAR_COVERAGE_EXHAUSTED':raise ValueError('OFFICIAL_CALENDAR_COVERAGE_EXHAUSTED')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT job_id,mode,through_date FROM update_jobs WHERE idempotency_key=?',(key,)).fetchone() if key else None
            if prior:
                if prior['mode']!=mode or prior['through_date']!=plan['requested_through_date']:
                    raise ValueError('IDEMPOTENCY_KEY_SCOPE_CONFLICT')
                return prior['job_id']
            prior=db.execute("SELECT job_id FROM update_jobs WHERE mode=? AND through_date=? AND status NOT IN ('PUBLISHED_FULL','PROBE_COMPLETE','NOOP_ALREADY_CURRENT','FAILED_TERMINAL','QA_BLOCKED','CANCELLED') ORDER BY created_at LIMIT 1",(mode,plan['requested_through_date'])).fetchone()
            if prior:return prior['job_id']
            job=uuid.uuid4().hex
            db.execute('INSERT INTO update_jobs VALUES(?,?,?,?,?,?,?,?,?)',
                (job,trigger,mode,plan['requested_through_date'],'QUEUED',self.clock().isoformat(),None,key,None))
            for day in (plan['missing_sessions'] or [plan['last_good_trade_date']] if mode=='PROBE' else plan['missing_sessions']):
                db.execute('INSERT INTO update_job_days(job_id,trade_date,state,next_retry_at) VALUES(?,?,?,?)',
                    (job,day,'QUEUED' if day in plan['eligible_sessions'] else 'SCHEDULED',
                     None if day in plan['eligible_sessions'] else day+'T18:35:00+08:00'))
            self.event(db,job,'CALENDAR_GAP_PLAN','GAP_PLANNED',plan)
        return job

    def job(self,job):
        with self.connect() as db:
            row=db.execute('SELECT * FROM update_jobs WHERE job_id=?',(job,)).fetchone()
            if not row:raise ValueError('JOB_NOT_FOUND')
            days=[dict(x) for x in db.execute('SELECT * FROM update_job_days WHERE job_id=? ORDER BY trade_date',(job,))]
        for day in days:day['source_checks']=json.loads(day['source_checks'])
        return dict(row)|dict(days=days)

    def events(self,job,after=0):
        self.job(job)
        with self.connect() as db:
            return [dict(x) for x in db.execute('SELECT * FROM update_events WHERE job_id=? AND event_id>? ORDER BY event_id LIMIT 100',(job,after))]

    def status(self):
        plan=gap_plan(self.root,self.clock())
        with self.connect() as db:
            row=db.execute('SELECT job_id FROM update_jobs ORDER BY created_at DESC LIMIT 1').fetchone()
            active=db.execute("SELECT job_id FROM update_jobs WHERE mode='CATCH_UP' AND status NOT IN ('PUBLISHED_FULL','NOOP_ALREADY_CURRENT','FAILED_TERMINAL','CANCELLED') ORDER BY created_at LIMIT 1").fetchone()
            last_catch_up=db.execute("SELECT job_id FROM update_jobs WHERE mode='CATCH_UP' ORDER BY created_at DESC LIMIT 1").fetchone()
        active_record=self.job(active['job_id']) if active else None
        retry_times=[d['next_retry_at'] for d in (active_record or {}).get('days',[]) if d['next_retry_at']]
        if retry_times:
            plan['next_trigger_at']=min(retry_times+([plan['next_trigger_at']] if plan.get('next_trigger_at') else []))
        return dict(plan,settings=self.settings(),last_job=self.job(row['job_id']) if row else None,
                    active_job=active_record,
                    last_catch_up_job=self.job(last_catch_up['job_id']) if last_catch_up else None,
                    worker_error=self.worker_error,last_good_preserved=True)

    def retry(self,job):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT status FROM update_jobs WHERE job_id=?',(job,)).fetchone()
            if not row:raise ValueError('JOB_NOT_FOUND')
            if row['status'] in {'RUNNING','PUBLISHING'}:raise ValueError('JOB_ACTIVE')
            db.execute("UPDATE update_job_days SET state='QUEUED',next_retry_at=NULL WHERE job_id=? AND state NOT IN ('PUBLISHED','PROBED')",(job,))
            db.execute("UPDATE update_jobs SET status='QUEUED',error=NULL,finished_at=NULL WHERE job_id=?",(job,))
            self.event(db,job,'RETRY','RETRY_FAILED_ONLY',{})
        return job

    def cancel(self,job):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT status FROM update_jobs WHERE job_id=?',(job,)).fetchone()
            if not row:raise ValueError('JOB_NOT_FOUND')
            if row['status'] in TERMINAL:return job
            if row['status'] not in {'RUNNING','PUBLISHING'}:
                db.execute("UPDATE update_jobs SET status='CANCELLED',finished_at=? WHERE job_id=?",(self.clock().isoformat(),job))
                db.execute("UPDATE update_job_days SET state='CANCELLED' WHERE job_id=? AND state NOT IN ('PUBLISHED','PROBED')",(job,))
                self.event(db,job,'CANCEL','CANCELLED',dict(boundary='No in-flight executor'))
                return job
            db.execute("UPDATE update_jobs SET status='CANCEL_REQUESTED' WHERE job_id=?",(job,))
            self.event(db,job,'CANCEL','CANCEL_REQUESTED',dict(boundary='Finish current immutable capture; stop before publication'))
        return job

    def publication_cancelled(self):
        if not self.active_job_id:return False
        with self.connect() as db:
            row=db.execute('SELECT status FROM update_jobs WHERE job_id=?',(self.active_job_id,)).fetchone()
        return bool(row and row['status'] in {'CANCEL_REQUESTED','CANCELLED'})

    def checkpoint(self,day,stage,detail):
        if not self.active_job_id:return
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE update_job_days SET state=?,source_checks=? WHERE job_id=? AND trade_date=?',
                (stage,json.dumps(detail),self.active_job_id,day))
            self.event(db,self.active_job_id,stage,'IMMUTABLE_STAGE_CHECKPOINT',dict(trade_date=day,**detail))

    def next_retry(self,day,attempt):
        now=self.clock()
        attempt_date=now.astimezone(SHANGHAI).date().isoformat()
        dates=[datetime.fromisoformat(attempt_date+'T'+t+':00+08:00') for t in RETRY_TIMES]
        dates.append(datetime.fromisoformat(attempt_date+'T07:35:00+08:00')+timedelta(days=1))
        return next((d.isoformat() for d in dates if d>now),None) if attempt<=7 else None

    def tick(self):
        # The kernel lock is released even when the process crashes. WAL records
        # the durable checkpoint; only unaccepted days can be replayed.
        with exclusive_lock(self.root,self.root/'runtime/dynamic_daily/worker.lock'):
            if self.settings()['auto_enabled']:
                plan=gap_plan(self.root,self.clock())
                if plan['missing_sessions'] and plan['eligible_sessions']:
                    self.dispatch(plan)
            with self.connect() as db:
                row=db.execute("SELECT job_id FROM update_jobs WHERE status NOT IN ('PUBLISHED_FULL','PROBE_COMPLETE','NOOP_ALREADY_CURRENT','FAILED_TERMINAL','CANCELLED','QA_BLOCKED') AND (trigger!='SCHEDULER' OR ?) ORDER BY CASE WHEN mode='PROBE' THEN 0 ELSE 1 END,created_at LIMIT 1",(self.settings()['auto_enabled'],)).fetchone()
            if not row:return
            job=self.job(row['job_id'])
            self.active_job_id=job['job_id']
            if job['status']=='CANCEL_REQUESTED':
                with self.connect() as db:
                    db.execute("UPDATE update_jobs SET status='CANCELLED',finished_at=? WHERE job_id=?",(self.clock().isoformat(),job['job_id']))
                    db.execute("UPDATE update_job_days SET state='CANCELLED' WHERE job_id=? AND state NOT IN ('PUBLISHED','PROBED')",(job['job_id'],))
                    self.event(db,job['job_id'],'CANCEL','CANCELLED',{})
                return
            if not job['days']:
                with self.connect() as db:
                    db.execute("UPDATE update_jobs SET status='NOOP_ALREADY_CURRENT',finished_at=? WHERE job_id=?",(self.clock().isoformat(),job['job_id']))
                return
            for day in job['days']:
                if day['state'] in {'PUBLISHED','PROBED'}:continue
                if job['trigger']=='SCHEDULER' and not self.settings()['auto_enabled']:return
                if self.publication_cancelled():return
                if job['mode']!='PROBE':
                    if day['next_retry_at'] and datetime.fromisoformat(day['next_retry_at'])>self.clock():return
                    if self.clock()<datetime.fromisoformat(day['trade_date']+'T18:35:00+08:00'):return
                with self.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    current=db.execute('SELECT status FROM update_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
                    if current['status'] in {'CANCEL_REQUESTED','CANCELLED'}:return
                    db.execute("UPDATE update_jobs SET status='RUNNING',finished_at=NULL WHERE job_id=?",(job['job_id'],))
                    db.execute("UPDATE update_job_days SET state='SOURCE_CHECKING',attempt_count=attempt_count+1 WHERE job_id=? AND trade_date=?",(job['job_id'],day['trade_date']))
                    self.event(db,job['job_id'],'SOURCE_PREFLIGHT','ATTEMPT_STARTED',dict(trade_date=day['trade_date']))
                try:
                    result=self.executor(day['trade_date'],job['mode']) if self.executor else dict(
                        status='QA_BLOCKED',reason='DATED_SUCCESSOR_PRODUCER_NOT_ADMITTED')
                except Exception as exc:
                    code=str(exc).split(':',1)[0]
                    safe=code if code and len(code)<=100 and all(c.isupper() or c.isdigit() or c=='_' for c in code) else type(exc).__name__
                    blocked=safe in {'NEW_CANONICAL_IDENTITY_REQUIRED','DATED_SOURCE_RECONCILIATION_FAILED','DAILY_ALGORITHM_ADMISSION_NOT_READY',
                                     'FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED','FULL_CORE_NUMERIC_ORACLE_FAILED',
                                     'FULL_PERIOD_NUMERIC_ORACLE_FAILED'}
                    waiting_tdx=safe=='FALLBACK_LOCAL_ACTUAL_TARGET_ABSENT'
                    result=dict(status='WAIT_TDX' if waiting_tdx else 'QA_BLOCKED' if blocked else 'FAILED_RETRYABLE',reason='SOURCE_EXECUTION_'+safe)
                state=result['status']; retry=None
                if self.publication_cancelled() and state!='PUBLISHED':state='CANCELLED'
                if state not in {'PUBLISHED','PROBED','QA_BLOCKED','FAILED_TERMINAL','CANCELLED'}:
                    retry=self.next_retry(day['trade_date'],day['attempt_count']+1)
                    if retry is None:state='FAILED_TERMINAL'
                with self.connect() as db:
                    db.execute('UPDATE update_job_days SET state=?,next_retry_at=?,source_checks=? WHERE job_id=? AND trade_date=?',
                        (state,retry,json.dumps(result),job['job_id'],day['trade_date']))
                    job_state='QUEUED' if state in {'PUBLISHED','PROBED'} else state
                    db.execute("UPDATE update_jobs SET status=CASE WHEN status='CANCEL_REQUESTED' AND ?='QUEUED' THEN status ELSE ? END,error=? WHERE job_id=?",
                        (job_state,job_state,result.get('reason'),job['job_id']))
                    self.event(db,job['job_id'],'DAY_RECEIPT',state,dict(trade_date=day['trade_date'],**result))
                if state not in {'PUBLISHED','PROBED'}:return
            with self.connect() as db:
                db.execute('UPDATE update_jobs SET status=?,finished_at=? WHERE job_id=?',
                    ('PROBE_COMPLETE' if job['mode']=='PROBE' else 'PUBLISHED_FULL',self.clock().isoformat(),job['job_id']))

    def start(self):
        def work():
            while not self.stop.is_set():
                try:self.tick();self.worker_error=None
                except Exception as exc:self.worker_error='WORKER_'+type(exc).__name__
                self.stop.wait(15)
        self.thread=threading.Thread(target=work,name='operational-daily-worker',daemon=True);self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=2)
