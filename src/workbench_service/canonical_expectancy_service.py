"""Explicit read-only canonical API; immutable context and current scoped permission."""
from workbench_analysis.fep_e1.contracts import digest

class CanonicalExpectancyReadAPI:
    def __init__(self, pg):self.pg=pg
    def bootstrap(self, slot):
        row=self.pg.execute("""select p.prediction_id,p.slot_id,p.model_set_id,p.model_id,p.run_id,p.snapshot_id,
            p.output_digest,s.feature_digest,s.quality_digest,r.authority_kind,r.publication_id,r.reconstruction_authority_id
            from fep.predictions p join fep.snapshots s using(snapshot_id) join fep.prediction_runs r using(run_id)
            where p.slot_id=%s and p.revision=1""",(slot,)).fetchall()
        if len(row)!=1:return dict(status='NOT_READY')
        keys=('prediction_id','slot_id','model_set_id','model_id','run_id','snapshot_id','output_digest','feature_digest','quality_digest','authority_kind','publication_id','reconstruction_authority_id')
        token=dict(zip(keys,row[0]));token['context_digest']=digest(token)
        return dict(status='CONTEXT_READY_CANONICAL_HISTORICAL',context=token,production=False)
    def projection(self, slot, token, *, diagnostic=False, mode='HISTORICAL_AS_OF'):
        bootstrap=self.bootstrap(slot)
        if bootstrap.get('context')!=token:return dict(status='CONTEXT_MISMATCH')
        if mode!='HISTORICAL_AS_OF':return dict(status='NOT_APPLICABLE_ENTRY_IS_NOT_TODAY_DAILY')
        row=self.pg.execute("""select p.outputs,exists(select 1 from fep.deployment_heads h
            join fep.activations a on a.activation_id=h.activation_id join fep.permission_keys k on k.grant_id=h.grant_id
            join fep.model_set_members m on m.model_set_id=k.model_set_id and m.role=k.model_role
            where h.scope_id=p.scope_id and h.target_id=p.target_id and h.horizon=p.horizon
            and h.feature_contract_id=p.feature_contract_id and h.model_set_id=p.model_set_id
            and h.capability='SHADOW_INFERENCE' and a.action='ALLOW' and a.effective_at<=clock_timestamp()
            and m.model_id=p.model_id and m.scope_id=p.scope_id and m.target_id=p.target_id and m.horizon=p.horizon
            and m.feature_contract_id=p.feature_contract_id)
            from fep.predictions p where p.prediction_id=%s""",(token['prediction_id'],)).fetchone()
        allowed=bool(row and row[1] and diagnostic)
        return dict(status='ENGINEERING_DIAGNOSTIC' if allowed else 'NOT_ENABLED_MODEL_DISPLAY_UNGRANTED',axes=row[0]['axes'] if allowed else None,
            projection_state=row[0]['projection_state'],diagnostic=allowed,MODEL_DISPLAY='UNGRANTED',PRIORITY_USE='UNGRANTED',
            REAL_DAILY_PRIORITY_SHADOW='NOT_GRANTED',FIRST_OBSERVED=False,REAL_OOS=False,production=False,authority_kind=token['authority_kind'])
    def priority(self):return dict(status='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE',v2_active=False,REAL_PRIORITY_SHADOW='NOT_GRANTED')
