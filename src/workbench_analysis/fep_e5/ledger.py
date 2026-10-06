"""FEP-only PostgreSQL append-only engineering ledger and atomic scoped head CAS."""
import json
from pathlib import Path
from psycopg import sql
from psycopg.types.json import Jsonb
from . import contracts as c

SCHEMA='fep_e5_engineering'
TABLES=('models','prediction_slots','slot_model_bindings','permission_keys','prediction_runs','predictions','projections',
    'slot_receipts','acceptance_receipts','activations','deployment_receipts','deployment_heads','priority_projection','protocols')

class Ledger:
    def __init__(self,pg):self.pg=pg
    def install(self):
        with self.pg.transaction():self.pg.execute(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
    def get(self,table,key):
        c.require(table in TABLES,'LEDGER_TABLE_NOT_ALLOWED')
        row=self.pg.execute(sql.SQL('select payload from {}.{} where id=%s').format(sql.Identifier(SCHEMA),sql.Identifier(table)),(key,)).fetchone()
        return row[0] if row else None
    def rows(self,table):
        c.require(table in TABLES,'LEDGER_TABLE_NOT_ALLOWED')
        return [r[0] for r in self.pg.execute(sql.SQL('select payload from {}.{} order by id').format(sql.Identifier(SCHEMA),sql.Identifier(table)))]
    def put(self,table,key,payload,**columns):
        c.write_target(SCHEMA);c.require(table in TABLES and table!='deployment_heads','IMMUTABLE_TABLE_REQUIRED')
        old=self.get(table,key)
        if old is not None:
            c.require(c.logical(old)==c.logical(payload),'APPEND_ONLY_IDEMPOTENCY_CONFLICT');return old
        names=['id',*columns,'payload'];values=[key,*columns.values(),Jsonb(payload)]
        self.pg.execute(sql.SQL('insert into {}.{} ({}) values ({})').format(sql.Identifier(SCHEMA),sql.Identifier(table),
            sql.SQL(',').join(map(sql.Identifier,names)),sql.SQL(',').join(sql.Placeholder() for _ in names)),values)
        return payload
    @staticmethod
    def identity_columns(payload):
        return dict(scope=payload['scope_id'],observation_scope=payload['observation_scope'],target=payload['target_id'],
            horizon=payload['horizon'],feature=payload['feature_contract_id'],namespace=payload['namespace'])
    def register_model(self,model):
        c.require(model.get('champion') is False,'CHAMPION_FORBIDDEN')
        with self.pg.transaction():return self.put('models',model['model_id'],model,**self.identity_columns(model))
    def plan(self,slot):
        slot=dict(slot,slot_id=c.slot_identity(slot))
        with self.pg.transaction():return self.put('prediction_slots',slot['slot_id'],slot,**self.identity_columns(slot))
    def bind(self,slot_id,model_id):
        slot=self.get('prediction_slots',slot_id);model=self.get('models',model_id)
        c.require(slot is not None and model is not None,'MISSING_MODEL_OR_SLOT');c.compatible(slot,model)
        record=dict(slot_id=slot_id,model_id=model_id,model_set_id=model['model_set_id'],model_selection_cutoff=slot['model_selection_cutoff'])
        with self.pg.transaction():return self.put('slot_model_bindings',slot_id,record,model_id=model_id,**self.identity_columns(slot))
    def grant(self,model_id,capability='SHADOW_INFERENCE'):
        model=self.get('models',model_id);c.require(model is not None,'MISSING_MODEL');key=c.permission_request(model,capability)
        key['grant_id']=c.logical(key)
        with self.pg.transaction():self.put('permission_keys',key['grant_id'],key,model_id=model_id,capability=capability)
        return key
    def cas(self,grant_id,request_id,expected_version,action,effective_at,*,fail_after_receipt=False):
        grant=self.get('permission_keys',grant_id);c.require(grant is not None,'EXACT_PERMISSION_REQUIRED')
        c.require(action in ('ALLOW','REVOKE'),'ACTIVATION_ACTION')
        from datetime import datetime,timezone
        c.require(c.utc(effective_at)<=datetime.now(timezone.utc),'FUTURE_ACTIVATION_FORBIDDEN')
        key={k:grant[k] for k in c.GRANT if k!='model_set_id'};head_id=c.logical(key)
        request=dict(grant_id=grant_id,request_id=request_id,expected_version=expected_version,action=action,effective_at=effective_at,head_id=head_id)
        with self.pg.transaction():
            self.pg.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(head_id,))
            previous=self.get('deployment_receipts',request_id)
            if previous is not None:c.exact(previous['request'],request,'CAS_REQUEST');return previous
            head=self.get('deployment_heads',head_id);version=head['version'] if head else 0
            c.require(version==expected_version,'CAS_VERSION_CONFLICT')
            if action=='REVOKE':c.require(head is not None and head['grant_id']==grant_id,'REVOKE_NONCURRENT_GRANT')
            activation_id=c.logical(request);receipt=dict(request=request,activation_id=activation_id,version=version+1,previous_activation_id=head['activation_id'] if head else None)
            self.put('activations',activation_id,dict(request,activation_id=activation_id),grant_id=grant_id)
            self.put('deployment_receipts',request_id,receipt)
            if fail_after_receipt:raise ValueError('E5_INJECTED_HEAD_UPDATE_FAILURE')
            payload=dict(key,head_id=head_id,version=version+1,grant_id=grant_id,activation_id=activation_id,action=action,effective_at=effective_at)
            self.pg.execute("set local fep_e5.cas='on'")
            self.pg.execute('insert into fep_e5_engineering.deployment_heads values (%s,%s,%s) on conflict(id) do update set version=excluded.version,payload=excluded.payload',
                (head_id,version+1,Jsonb(payload)))
            return receipt
    def allowed(self,model_id,key,at):
        model=self.get('models',model_id)
        if model is None or key.get('capability')!='SHADOW_INFERENCE':return False
        if key!=c.permission_key(model,'SHADOW_INFERENCE'):return False
        grant_id=c.logical(key);head_id=c.logical({k:v for k,v in key.items() if k!='model_set_id'});head=self.get('deployment_heads',head_id)
        return bool(head and head['grant_id']==grant_id and head['action']=='ALLOW' and c.utc(head['effective_at'])<=c.utc(at))
    def rollback(self,model_id,request_id,at,*,delete_history=False):
        c.require(not delete_history,'ROLLBACK_DELETE_FORBIDDEN');model=self.get('models',model_id)
        key=c.permission_key(model,'SHADOW_INFERENCE');head=self.get('deployment_heads',c.logical({k:v for k,v in key.items() if k!='model_set_id'}))
        c.require(head is not None,'ROLLBACK_MISSING_HEAD')
        return self.cas(c.logical(key),request_id,head['version'],'REVOKE',at)
    def inventory(self):
        return {table:self.pg.execute(sql.SQL('select count(*) from {}.{}').format(sql.Identifier(SCHEMA),sql.Identifier(table))).fetchone()[0] for table in TABLES}
