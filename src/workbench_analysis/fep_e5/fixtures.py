"""Clearly synthetic candidate-day vectors; never real model/OOS/activation evidence."""
from . import contracts as c

def priority_protocol():return dict(contract_id='PRIORITY_V2_SHADOW_E5_V1',layer_keys=list(c.LAYER),fep_tuple=['return_expectancy_desc','stable_entity_id'],K=3,default_enabled=False,real_enabled=False)

def fixture():
    day='2026-10-06';pool=[];predictions={}
    for i in range(7):
        entity='TEST_ONLY:'+str(i);risk='EXTREME' if i==6 else 'LOW'
        events=['INVALIDATED','RISK_CHANGE','HIGH_EXTENSION'] if i==6 else []
        row=dict(entity_id=entity,trade_date=day,eligible=i!=6,priority_rank=i+1 if i!=6 else None,display_rank=i+1,
            priority_bucket='A' if i<6 else 'RISK_CHANGE',emergence='HIGH',structure='HIGH',delta3=12.,risk=risk,
            days_since_improvement=0,prior20_amount=1000.,PREWATCH=i!=6,CONFIRMED=False,State='UNCHANGED',
            Radar='UNCHANGED',Validation_Cohort='UNCHANGED',Focus='UNCHANGED',risk_events=events)
        pool.append(row)
        if i==3:continue
        predictions[entity]=dict(entity_id=entity,scope_id='FEP_STOCK_DAILY_CORE',observation_scope='DAILY_LANDMARK',trade_date=day,
            snapshot_trade_date=day,slot_trade_date=day,accepted_trade_date=day,model_id=None if i==4 else 'FIXTURE_MODEL',
            quality_state='OBSERVED',support_state='SUPPORTED',OOD_state='REJECTED' if i==5 else 'PASS_FIXTURE',
            axes=dict(return_expectancy=float(i+1),relative_expectancy=None,risk_expectancy=10. if i==6 else .01,structure_expectancy=None,
                confidence_support='FIXTURE',OOD='FIXTURE'),prediction_evidence='ENGINEERING_FIXTURE',synthetic_only=True,
            FIRST_OBSERVED=False,REAL_OOS=False,PROMOTION_EVIDENCE=False)
    risk_events=[dict(entity_id=pool[6]['entity_id'],events=pool[6]['risk_events'])]
    return pool,predictions,day,risk_events
