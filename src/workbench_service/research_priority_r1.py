"""Explainable daily research queue; never a probability or trade signal."""
from .operational_risk_v1 import _value,_cell

CONTRACT='V4_DAILY_RESEARCH_PRIORITY_R1'

def _numeric(row,key):
    cell=_cell(row,key);value=cell.get('value')
    if not isinstance(value,(int,float)) or isinstance(value,bool) or cell.get('quality') in ('UNKNOWN','SOURCE_INCOMPLETE','DATA_UNAVAILABLE'):
        return None
    return float(value)

def build_priority(day,token,stocks,sectors,market,stock_source,sector_source,parameter_digest):
    sector_rows=[];sector_state={}
    for row in sectors:
        fields=row.get('fields') or {};life=fields.get('maturity',{});health=fields.get('health',{})
        rs5=_numeric(row,'sector_rs5');rs20=_numeric(row,'sector_rs20')
        rotation=_value(row,'output_state');maturity=life.get('value');sector_health=health.get('value')
        unknown=[]
        for name,val in (('maturity',maturity),('health',sector_health),('sector_rs5',rs5),('sector_rs20',rs20),('rotation',rotation)):
            if val is None or val=='UNKNOWN':unknown.append(name)
        if unknown:
            sector_state[row['entity_id']]=dict(priority_state='NOT_RANKABLE',rank=None,score=None,unknown_inputs=unknown)
            continue
        score=(4 if rotation in ('ROTATION_IN','ROTATION_ACCEPTED','ROTATION_EXPANDING','ROTATION_REACCELERATING') else
               2 if rotation=='ROTATION_PULSE' else 0)
        score+=({'MATURE':4,'DEVELOPING':3,'EARLY':1,'NONE':0}.get(maturity,0))
        score+=({'NONE':2,'WATCH':1,'WEAKENING':0,'DAMAGED':-3}.get(sector_health,-3))
        score+=int(rs5>0)+int(rs20>0)
        reasons=[f'ROTATION_{rotation}',f'MATURITY_{maturity}',f'HEALTH_{sector_health}',
                 'RS5_POSITIVE' if rs5>0 else 'RS5_NONPOSITIVE','RS20_POSITIVE' if rs20>0 else 'RS20_NONPOSITIVE']
        candidate=dict(entity_id=row['entity_id'],sector_id=row['entity_id'],display_name=row.get('display_name'),
            symbol=row.get('symbol'),priority_state='RANKABLE',score=score,reasons=reasons,unknown_inputs=[],
            facts=dict(rotation=rotation,maturity=maturity,health=sector_health,sector_rs5=rs5,sector_rs20=rs20),
            source=sector_source,href='/v4/research/sectors/'+row['entity_id'])
        sector_rows.append(candidate);sector_state[row['entity_id']]=candidate
    sector_rows.sort(key=lambda r:(-r['score'],-r['facts']['sector_rs5'],-r['facts']['sector_rs20'],r['entity_id']))
    for rank,row in enumerate(sector_rows,1):row['rank']=rank

    stock_rows=[];stock_state={}
    for row in stocks:
        damage=_value(row,'core_price_damage');rps20=_numeric(row,'rps20');delta=_numeric(row,'rps20_delta3')
        ret5=_numeric(row,'ret5');pos60=_numeric(row,'pos60');low=_numeric(row,'prior_low20')
        missing=[name for name,val in (('core_price_damage',damage),('rps20',rps20),('rps20_delta3',delta),('ret5',ret5),('pos60',pos60),('prior_low20',low)) if val is None]
        # Archived input values are metrics, not qualified trading eligibility.
        # Avoid already extended names and damaged structures in this review queue.
        if missing or damage is not False or delta<=0 or ret5<=0 or pos60>=0.95:
            reason=('MISSING_'+','.join(missing) if missing else 'STRUCTURE_DAMAGED' if damage is True else
                    'RELATIVE_STRENGTH_NOT_IMPROVING' if delta<=0 else 'FIVE_SESSION_RETURN_NOT_POSITIVE' if ret5<=0 else 'EXTENDED_POSITION')
            stock_state[row['entity_id']]=dict(priority_state='NOT_RANKABLE',rank=None,score=None,unknown_inputs=missing,
                exclusion_reason=reason)
            continue
        distance=max(0.0,min(1.0,(row.get('fields',{}).get('close',{}).get('value',low)-low)/max(abs(low),1e-9)))
        score=4+min(4,delta*100)+min(2,ret5*100)+max(0,2-distance*10)
        reasons=['CORE_STRUCTURE_INTACT','RPS20_DELTA3_POSITIVE','RET5_POSITIVE','NOT_EXTENDED',
                 'DISTANCE_FROM_PRIOR_LOW20_OBSERVED']
        candidate=dict(entity_id=row['entity_id'],display_name=row.get('display_name'),symbol=row.get('symbol'),
            priority_state='RANKABLE',score=round(score,6),reasons=reasons,unknown_inputs=[],
            facts=dict(core_price_damage=damage,rps20=_numeric(row,'rps20'),rps20_delta3=delta,ret5=ret5,pos60=pos60,
                       prior_low20=low,distance_from_prior_low20=distance),source=stock_source,
            href='/v4/research/stocks/'+row['entity_id'])
        stock_rows.append(candidate);stock_state[row['entity_id']]=candidate
    stock_rows.sort(key=lambda r:(-r['score'],-r['facts']['rps20_delta3'],-r['facts']['ret5'],r['entity_id']))
    for rank,row in enumerate(stock_rows,1):row['rank']=rank
    market_status=(market or {}).get('regime_publication_status','NOT_AVAILABLE')
    return dict(contract_id=CONTRACT,version='1.0.0',T0=day,context_token=token,
        market_permission=dict(status='FACT_ONLY_NO_FORMAL_PERMISSION',source_status=market_status,
            reason='FOUR_AXIS_FACTS_DO_NOT_ESTABLISH_ACCEPTED_COMPOSITE_PERMISSION'),
        sectors=dict(total=len(sectors),rankable=len(sector_rows),not_rankable=len(sectors)-len(sector_rows),
            items=sector_rows[:10],all_items=sector_rows,
            not_rankable_examples=[{'entity_id':k,**v} for k,v in sorted(sector_state.items()) if v['priority_state']=='NOT_RANKABLE'][:20],
            not_rankable_rows=[{'entity_id':k,**v} for k,v in sorted(sector_state.items()) if v['priority_state']=='NOT_RANKABLE'],source=sector_source),
        stocks=dict(total=len(stocks),rankable=len(stock_rows),not_rankable=len(stocks)-len(stock_rows),
            items=stock_rows[:30],all_items=stock_rows,
            not_rankable_examples=[{'entity_id':k,**v} for k,v in sorted(stock_state.items()) if v['priority_state']=='NOT_RANKABLE'][:20],
            not_rankable_rows=[{'entity_id':k,**v} for k,v in sorted(stock_state.items()) if v['priority_state']=='NOT_RANKABLE'],source=stock_source),
        rule=dict(contract_id=CONTRACT,parameter_digest=parameter_digest,market_permission='UNACCEPTED_FACTS_ONLY; NO SCORE WEIGHT',
            sector='Rotation state + reconstructed maturity/health + RS5/RS20; rank by score, RS5, RS20, entity id',
            stock='core_price_damage=false + improving rps20_delta3 + positive ret5 + pos60<0.95 + prior_low20 available; score uses bounded deltas/return/distance',
            missing_inputs='NOT_RANKABLE with field-level input names; no neutral imputation',
            scope='Research review order only; not probability, advice, execution authorization, or return claim',
            deduplication='one row per security_id or sector_id; stable entity_id tiebreaker',
            freshness='current as-of facts and accepted daily deltas only; excludes positive but non-improving/extended stock rows'),
        source_bindings=dict(stock=stock_source,sector=sector_source),parameter_digest=parameter_digest,
        AS_RECORDED=False,PIT_ELIGIBLE=False,probability_claims=False,trading=False)
