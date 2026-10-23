"""Explainable daily research queue; never a probability or trade signal."""
import math
from .operational_risk_v1 import _value,_cell

CONTRACT='V4_DAILY_RESEARCH_PRIORITY_R1'

def _numeric(row,key):
    cell=_cell(row,key);value=cell.get('value')
    if (not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value)
            or cell.get('quality') not in ('KNOWN','OBSERVED','RECONSTRUCTED','PROXY_RECONSTRUCTED')):
        return None
    return float(value)


def _dated_sector_state(row, key, day):
    """Admit lifecycle states only with dated, quality-qualified producer proof."""
    cell=((row or {}).get('fields') or {}).get(key)
    if not isinstance(cell,dict):return None,'MISSING'
    value=cell.get('value');source=cell.get('source')
    if value is None or value=='UNKNOWN':return None,'UNKNOWN'
    if cell.get('quality') not in ('KNOWN','OBSERVED','RECONSTRUCTED'):return None,'INVALID_QUALITY'
    if cell.get('as_of')!=day:return None,'INVALID_DATE'
    if not isinstance(source,dict) or not all(source.get(name) for name in
            ('input_digest','producer_sha256','parameter_sha256','source_bindings')):
        return None,'INVALID_PROVENANCE'
    return value,None


def _dated_number(row, key, day, *, positive=False, minimum=None, maximum=None, minimum_exclusive=False):
    """Read a finite, quality-admitted metric at the requested T0."""
    fields=(row or {}).get('fields') or {}
    if key not in fields:
        return None, 'MISSING'
    cell=fields[key]
    if not isinstance(cell,dict):
        return None, 'INVALID_TYPE'
    value=cell.get('value')
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value):
        return None, 'INVALID_NUMERIC'
    if cell.get('quality') not in ('KNOWN','OBSERVED','RECONSTRUCTED','PROXY_RECONSTRUCTED'):
        return None, 'INVALID_QUALITY'
    if cell.get('as_of') not in (None, day) or (row or {}).get('trade_date') not in (None, day):
        return None, 'INVALID_DATE'
    if positive and value <= 0:
        return None, 'OUT_OF_RANGE'
    if ((minimum is not None and (value <= minimum if minimum_exclusive else value < minimum))
            or (maximum is not None and value > maximum)):
        return None, 'OUT_OF_RANGE'
    return float(value), None

def build_priority(day,token,stocks,sectors,market,stock_source,sector_source,parameter_digest):
    sector_rows=[];sector_state={}
    for row in sectors:
        fields=row.get('fields') or {};life=fields.get('maturity',{});health=fields.get('health',{})
        rs5,rs5_issue=_dated_number(row,'sector_rs5',day)
        rs20,rs20_issue=_dated_number(row,'sector_rs20',day)
        rotation_cell=fields.get('output_state')
        rotation=rotation_cell.get('value') if isinstance(rotation_cell,dict) else None
        maturity,maturity_issue=_dated_sector_state(row,'maturity',day)
        sector_health,health_issue=_dated_sector_state(row,'health',day)
        unknown=[]
        for name,val in (('maturity',maturity),('health',sector_health),('sector_rs5',rs5),('sector_rs20',rs20),('rotation',rotation)):
            if val is None or val=='UNKNOWN':unknown.append(name)
        invalid=[name for name,issue in (('maturity',maturity_issue),('health',health_issue))
                 if issue not in (None,'MISSING','UNKNOWN')]
        invalid.extend(name for name,issue in (('sector_rs5',rs5_issue),('sector_rs20',rs20_issue))
                       if issue not in (None,'MISSING'))
        for name,value,allowed in (
            ('maturity',maturity,{'MATURE','DEVELOPING','EARLY','NONE'}),
            ('health',sector_health,{'NONE','WATCH','WEAKENING','DAMAGED'}),
            ('rotation',rotation,{'ROTATION_IN','ROTATION_ACCEPTED','ROTATION_EXPANDING',
                'ROTATION_REACCELERATING','ROTATION_PULSE','ROTATION_OUT','ROTATION_FAILED','NONE'})):
            if value not in (None,'UNKNOWN') and value not in allowed:invalid.append(name)
        if isinstance(rotation_cell,dict) and rotation not in (None,'UNKNOWN') and (rotation_cell.get('quality') not in ('KNOWN','OBSERVED','RECONSTRUCTED','PROXY_RECONSTRUCTED')
                or rotation_cell.get('as_of') not in (None,day)):
            invalid.append('rotation')
        if invalid:
            sector_state[row['entity_id']]=dict(priority_state='NOT_RANKABLE',rank=None,score=None,
                unknown_inputs=unknown,invalid_inputs=invalid,exclusion_reason='INVALID_INPUT',
                exclusion_reasons=['INVALID_INPUT_'+','.join(sorted(invalid))])
            continue
        if unknown:
            sector_state[row['entity_id']]=dict(priority_state='NOT_RANKABLE',rank=None,score=None,unknown_inputs=unknown,
                exclusion_reason='MISSING_INPUT',exclusion_reasons=['MISSING_INPUT_'+','.join(unknown)])
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
        fields=row.get('fields') or {}
        damage_cell=fields.get('core_price_damage')
        damage=(damage_cell.get('value') if isinstance(damage_cell,dict) else None)
        invalid=[]
        if not isinstance(damage_cell,dict):
            invalid.append('core_price_damage')
        elif damage_cell.get('quality') not in ('KNOWN','OBSERVED','RECONSTRUCTED') or not isinstance(damage,(bool,)):
            invalid.append('core_price_damage')
        elif damage_cell.get('as_of') not in (None,day):
            invalid.append('core_price_damage')
        metrics={}
        for name,kwargs in (
            ('close',dict(positive=True)),('prior_low20',dict(positive=True)),
            ('rps20',dict(minimum=0,maximum=100)),('rps20_delta3',dict(minimum=-100,maximum=100)),
            ('ret5',dict(minimum=-1,minimum_exclusive=True)),('pos60',dict(minimum=0,maximum=1)),
        ):
            metrics[name],issue=_dated_number(row,name,day,**kwargs)
            if issue and issue!='MISSING':invalid.append(name)
        close=metrics['close'];low=metrics['prior_low20'];rps20=metrics['rps20']
        delta=metrics['rps20_delta3'];ret5=metrics['ret5'];pos60=metrics['pos60']
        missing=[name for name in ('close','prior_low20','rps20','rps20_delta3','ret5','pos60')
                 if name not in fields]
        # Missing values and invalid values stay distinct and neither may earn
        # a neutral score. Keep every failed predicate for auditability.
        exclusion_reasons=[]
        close_basis=(fields.get('close') or {}).get('adjustment_basis')
        low_basis=(fields.get('prior_low20') or {}).get('adjustment_basis')
        if not close_basis or not low_basis or close_basis!=low_basis:
            invalid.append('price_coordinate:close,prior_low20')
        if invalid: exclusion_reasons.append('INVALID_INPUT_'+','.join(sorted(set(invalid))))
        if missing: exclusion_reasons.append('MISSING_INPUT_'+','.join(missing))
        if damage is True: exclusion_reasons.append('STRUCTURE_DAMAGED')
        if delta is not None and delta<=0: exclusion_reasons.append('RELATIVE_STRENGTH_NOT_IMPROVING')
        if ret5 is not None and ret5<=0: exclusion_reasons.append('FIVE_SESSION_RETURN_NOT_POSITIVE')
        if pos60 is not None and pos60>=0.95: exclusion_reasons.append('EXTENDED_POSITION')
        if damage is False and not invalid and not missing and not exclusion_reasons:
            pass
        else:
            primary=('MISSING_INPUT' if missing else 'INVALID_INPUT' if invalid else
                     'STRUCTURE_DAMAGED' if damage is True else
                     'RELATIVE_STRENGTH_NOT_IMPROVING' if delta is not None and delta<=0 else
                     'FIVE_SESSION_RETURN_NOT_POSITIVE' if ret5 is not None and ret5<=0 else
                     'EXTENDED_POSITION' if pos60 is not None and pos60>=0.95 else 'INVALID_INPUT')
            stock_state[row['entity_id']]=dict(priority_state='NOT_RANKABLE',rank=None,score=None,
                unknown_inputs=missing,invalid_inputs=sorted(set(invalid)),
                exclusion_reason=primary,exclusion_reasons=exclusion_reasons)
            continue
        # Archived input values are metrics, not qualified trading eligibility.
        # Avoid already extended names and damaged structures in this review queue.
        if missing or damage is not False or delta<=0 or ret5<=0 or pos60>=0.95:
            reason=('MISSING_'+','.join(missing) if missing else 'STRUCTURE_DAMAGED' if damage is True else
                    'RELATIVE_STRENGTH_NOT_IMPROVING' if delta<=0 else 'FIVE_SESSION_RETURN_NOT_POSITIVE' if ret5<=0 else 'EXTENDED_POSITION')
            stock_state[row['entity_id']]=dict(priority_state='NOT_RANKABLE',rank=None,score=None,unknown_inputs=missing,
                exclusion_reason=reason)
            continue
        distance=max(0.0,min(1.0,(close-low)/low))
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
