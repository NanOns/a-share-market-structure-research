"""Mechanical constructor successor, preserving accepted business methods."""
import inspect
from scripts.full_chain_repair_io import ROOT,write
from scripts.v4_16_go_forward_shadow_runtime import SettlementObligationController,RealShadowController,RealShadowDatabase

def build():
    source=(ROOT/'scripts/v4_16_go_forward_shadow_runtime_r4r2.py').read_text(encoding='utf8')
    source=source.replace('config/v4_16_runtime_dependencies_v4.json','config/v4_16_runtime_dependencies_v5.json')
    source=source.replace("        acceptance=json.loads(exact(self.root,self.activation['external_acceptance']))", "        require_admission(self.root,self.deps['capability_resolution'],self.grant['capability_scope'])\n        acceptance=json.loads(exact(self.root,self.activation['external_acceptance']))",1)
    verify=inspect.getsource(RealShadowController.verify_request).replace("check(not set(caps)&set(self.deps['blocked_capabilities']),'BLOCKED_CAPABILITY')","require_admission(self.root,self.deps['capability_resolution'],caps)")
    source+='\n'+verify+'\n    def database(self,path):\n        self.guard()\n        return SuccessorDatabase(self,path)\n'
    settlement=inspect.getsource(SettlementObligationController).replace('class SettlementObligationController:', 'class SettlementObligationControllerR4R2:').replace('config/v4_16_runtime_dependencies_v3.json','config/v4_16_runtime_dependencies_v5.json').replace('return RealShadowDatabase(self,path)','return SuccessorDatabase(self,path)')
    settlement=settlement.replace('def __init__(self,root,path,simulation=False):','def __init__(self,root,path,simulation=False,simulation_dependencies=None):')
    settlement=settlement.replace("        self.dependency_path='config/v4_16_runtime_dependencies_v5.json'", "        check(simulation_dependencies is None or (simulation and (self.root/simulation_dependencies).resolve().is_relative_to(self.root/'reports/r24r1/activation_simulation')), 'ISOLATED_SETTLEMENT_FIXTURE_REQUIRED')\n        self.dependency_path=simulation_dependencies or 'config/v4_16_runtime_dependencies_v5.json'")
    settlement=settlement.replace('        self.authority=GoForwardInputAuthority(', "        loader=GoForwardInputAuthority\n        if simulation:\n            from scripts.v4_16_go_forward_input_authority import GoForwardInputAuthority as loader\n        self.authority=loader(")
    settlement=settlement.replace("        self.grant=self.activation['grant']", "        self.grant=self.activation['grant']\n        check(self.deps['contract_id']=='V4_16_RUNTIME_DEPENDENCIES_V5','STALE_OBLIGATION_DEPENDENCY')\n        check(self.grant['runtime_dependency_contract_id']==self.deps['contract_id'] and self.grant['dependency_set_digest']==dependency_digest(self.deps),'STALE_OBLIGATION_DEPENDENCY')")
    source+='\n'+settlement
    database=inspect.getsource(RealShadowDatabase).replace('class RealShadowDatabase:', 'class SuccessorDatabase:')
    database=database.replace("tables<= {'storage_identity','facts','publication_heads','activation_head'}", "tables<= {'storage_identity','facts','publication_heads','activation_head','settlement_queue_v2'} | set(INTEGRITY_TABLES)")
    database=database.replace("        env=controller.activation['environment_class']", "        check(not self.conn.execute('SELECT count(*) FROM facts').fetchone()[0] or self.conn.execute(\"SELECT count(*) FROM sqlite_master WHERE name='integrity_slot_v2'\").fetchone()[0], 'NONEMPTY_LEDGER_REQUIRES_AUDITED_INTEGRITY_MIGRATION')\n        self.conn.executescript(exact(controller.root,controller.deps['queue_migration']).decode())\n        self.conn.executescript(exact(controller.root,controller.deps['integrity_migration']).decode())\n        for table in INTEGRITY_TABLES:\n            for action in ('UPDATE','DELETE'):\n                self.conn.execute(f\"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'IMMUTABLE_INTEGRITY_REFERENCE'); END\")\n        for index,date in enumerate(controller.authority.sessions):\n            self.conn.execute('INSERT OR IGNORE INTO integrity_calendar_v2 VALUES(?,?)',(index,date))\n            check(self.conn.execute('SELECT trade_date FROM integrity_calendar_v2 WHERE session_no=?',(index,)).fetchone()==(date,),'CALENDAR_IDENTITY_DRIFT')\n        self.conn.execute('INSERT OR IGNORE INTO integrity_authority_v2 VALUES(?,?)',(controller.activation['authority_id'],canonical(controller.deps['activation'] if not getattr(controller,'settlement_only',False) else controller.accepted_activation_binding)))\n        env=controller.activation['environment_class']")
    source+='\n'+database
    source+='''

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
'''
    imports='''
import copy, hashlib, sqlite3
from scripts.v4_16_shadow_runtime import canonical, digest
from scripts.v4_16_capability_resolution import require_admission
from scripts.v4_16_go_forward_shadow_runtime import OneSessionLaunchController as HistoricalLaunchController
class OneSessionLaunchController(HistoricalLaunchController):
    def settle(self,*args,**kwargs):
        raise ValueError('DURABLE_SETTLEMENT_WORKER_REQUIRED')
INTEGRITY_TABLES=('integrity_calendar_v2','integrity_authority_v2','integrity_activation_v2','integrity_manifest_v2','integrity_slot_v2','integrity_publication_v2','integrity_event_v2','integrity_freeze_v2','integrity_enrollment_v2','integrity_admission_v2','integrity_due_v2','integrity_evaluation_source_v2','integrity_outcome_v2','integrity_state_v2')
'''
    source=source.replace('class RealShadowController(HistoricalController):',imports+'\nclass RealShadowController(HistoricalController):')
    source=source.replace("        self.activation=json.loads(exact(self.root,binding))", "        self.accepted_activation_binding=binding\n        self.settlement_only=True\n        self.activation=json.loads(exact(self.root,binding))")
    write('scripts/v4_16_go_forward_shadow_runtime_r4r3.py',source.encode(),raw=True)

if __name__=='__main__':build()
