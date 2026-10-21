"""Bounded, post-hoc market axes from date-bound candidate Owners (NON_PIT)."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

from v4.factors.native import market_axis_primitives, candidate_threshold


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _checked(root, ref):
    root=Path(root).resolve();path=(root/ref['path']).resolve()
    if root not in path.parents:raise ValueError('R7_MARKET_STRESS_OWNER_PATH_ESCAPES_ROOT')
    raw=path.read_bytes()
    if len(raw)!=ref.get('bytes',len(raw)) or hashlib.sha256(raw).hexdigest()!=ref['sha256']:
        raise ValueError('R7_MARKET_STRESS_OWNER_BYTES_OR_SHA_MISMATCH')
    return path


def _read_rows(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:return [json.loads(line) for line in stream]


def candidate_breadth_formula_comparison(comparison, *, boundary):
    """Expose signed-SIGN and positive-indicator breadth on identical pairs."""
    if not isinstance(boundary,(int,float)) or isinstance(boundary,bool) or not math.isfinite(boundary) or boundary<0:
        raise ValueError('R7_BREADTH_THRESHOLD_INVALID')
    rows=list(comparison)
    if not rows:
        return dict(evaluable=0,threshold=boundary,threshold_parameter_id='V4_03_MARKET_BREADTH_AXIS',
            signed=dict(value=None,classification='UNKNOWN',formula='MEAN(SIGN(r_t)-SIGN(r_t_minus_3))'),
            positive_indicator=dict(value=None,classification='UNKNOWN',formula='MEAN(I(r_t>0)-I(r_t_minus_3>0))'),
            difference=None,zero_current=0,zero_comparison=0)
    sign_value=sum((1 if now>0 else -1 if now<0 else 0)-
                   (1 if old>0 else -1 if old<0 else 0) for now,old in rows)/len(rows)
    positive_value=sum((1 if now>0 else 0)-(1 if old>0 else 0) for now,old in rows)/len(rows)
    classify=lambda value:('IMPROVING' if value>boundary else 'DETERIORATING' if value< -boundary else 'STABLE')
    return dict(evaluable=len(rows),threshold=boundary,threshold_parameter_id='V4_03_MARKET_BREADTH_AXIS',
        signed=dict(value=sign_value,classification=classify(sign_value),formula='MEAN(SIGN(r_t)-SIGN(r_t_minus_3))'),
        positive_indicator=dict(value=positive_value,classification=classify(positive_value),formula='MEAN(I(r_t>0)-I(r_t_minus_3>0))'),
        difference=sign_value-positive_value,zero_current=sum(now==0 for now,_ in rows),
        zero_comparison=sum(old==0 for _,old in rows))


def _limit_owner(root,candidate,day):
    owner=candidate.get('owners',{}).get(day,{})
    expected=owner.get('raw',{}).get('path','')
    match=re.search(r'dynamic_daily_owners[/\\]'+re.escape(day)+r'[/\\]([^/\\]+)',expected)
    if not match:raise ValueError('R7_MARKET_STRESS_DATED_CANDIDATE_OWNER_ID_MISSING:'+day)
    candidate_owner_id=match.group(1);raw_ref=owner.get('raw') or {}
    if len(str(raw_ref.get('sha256',''))) != 64:raise ValueError('R7_MARKET_STRESS_CANDIDATE_RAW_BINDING_MISSING:'+day)
    matches=[]
    for receipt_path in Path(root).glob('r5_daily_limit_materialization_*/'+day+'/DAILY_PRICE_LIMIT_REPLAY.json'):
        receipt_bytes=receipt_path.read_bytes();receipt=json.loads(receipt_bytes)
        for row in receipt.get('owners',[]):
            source=row.get('baostock_source') or {}
            if (row.get('trade_date')!=day or source.get('trade_date')!=day or
                    source.get('candidate_owner_id')!=candidate_owner_id):
                continue
            _checked(root,source)
            binding=row.get('artifact') or {}
            _checked(root,binding)
            matches.append((binding,row,receipt_path,hashlib.sha256(receipt_bytes).hexdigest()))
    unique={(x[0].get('sha256'),x[0].get('bytes'),
             x[1]['baostock_source'].get('sha256'),x[1]['baostock_source'].get('bytes'),
             json.dumps(x[1].get('counts',{}),sort_keys=True,separators=(',',':'))) for x in matches}
    if len(unique)!=1:raise ValueError('R7_MARKET_STRESS_LIMIT_OWNER_NOT_UNIQUE_OR_SOURCE_MISMATCH:'+day)
    selected=sorted(matches,key=lambda x:(x[3],str(x[2])))[0]
    selected[1]['_receipt_sha256s']=sorted({x[3] for x in matches})
    return selected


def candidate_market_stress_identity(root,candidate):
    """Content-verify cached inputs so same-token candidate replacement misses cache."""
    root=Path(root);t0=candidate['accepted_trade_date']
    if t0>'2026-10-14':raise ValueError('R7_MARKET_STRESS_CUTOFF_EXCEEDED')
    rows=[]
    for day in ('2026-10-12','2026-10-13','2026-10-14'):
        if day not in candidate.get('owners',{}) or day>t0:continue
        owner=candidate['owners'][day];market=_checked(root,owner['market'])
        limit,receipt,_,_=_limit_owner(root,candidate,day);limit_path=_checked(root,limit)
        core_path=_checked(root,owner['core'])
        stat=lambda path:(path.stat().st_size,path.stat().st_mtime_ns)
        rows.append(dict(day=day,core_sha256=owner['core']['sha256'],core_stat=stat(core_path),
            market_sha256=owner['market']['sha256'],market_stat=stat(market),
            limit_sha256=limit['sha256'],limit_stat=stat(limit_path),
            raw_source_sha256=receipt['baostock_source']['sha256'],receipt_sha256s=receipt['_receipt_sha256s']))
    source=dict(contract='R7_CANDIDATE_MARKET_STRESS_V2',T0=t0,
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        parameter_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'config/v4_03_parameter_set_v1.json').read_bytes()).hexdigest(),
        inputs=rows)
    return hashlib.sha256(_canonical(source)).hexdigest()


def _market_axes_from_owner(root,candidate,day,core_binding,market_binding,core_rows):
    market_path=_checked(root,market_binding);market=json.loads(market_path.read_bytes())
    if market.get('trade_date')!=day or market.get('AS_RECORDED') is not False or market.get('accepted') is not False:
        raise ValueError('R7_MARKET_OWNER_DATE_OR_AUTHORITY_MISMATCH:'+day)
    bindings=market.get('input_bindings',[])
    bound={Path(ref['path']).name:ref for ref in bindings}
    history_ref=bound.get('history.jsonl.gz')
    membership_ref=next((ref for ref in bindings if 'historical_universe' in Path(ref['path']).name),None)
    if not history_ref or not membership_ref or bound.get(Path(core_binding['path']).name)!=core_binding:
        raise ValueError('R7_MARKET_OWNER_REQUIRED_INPUT_BINDING_MISSING:'+day)
    history_rows=_read_rows(_checked(root,history_ref))
    history={r['security_id']:{b['trade_date']:b for b in r.get('bars',[])} for r in history_rows}
    membership_rows=_read_rows(_checked(root,membership_ref))
    from workbench_analysis.market_source_acquisition import official_sessions
    sessions=[session for session in official_sessions(Path(root)) if session<=day]
    index=sessions.index(day);prior3=sessions[index-3] if index>=3 else None
    if prior3 is None or market.get('comparison_trade_date')!=prior3:
        raise ValueError('R7_MARKET_BREADTH_COMPARISON_SESSION_MISMATCH:'+day)
    predecessor=candidate.get('owners',{}).get(prior3,{}).get('core')
    if predecessor:
        universe={r['security_id'] for r in _read_rows(_checked(root,predecessor)) if r.get('security_id')}
    else:
        universe={r['security_id'] for r in membership_rows if r.get('trade_date')==prior3 and
                  r.get('board_scope') in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT')}
    current={r['security_id']:r for r in core_rows if r.get('security_id') in universe}
    comparison=[]
    for sid in current:
        bars=history.get(sid,{})
        def ret(d):
            pos=sessions.index(d)
            if pos<1:return None
            today=bars.get(d,{}).get('qfq_ohlc');previous=bars.get(sessions[pos-1],{}).get('qfq_ohlc')
            if not today or not previous or len(today)<4 or len(previous)<4:return None
            close,prior_close=today[3],previous[3]
            if (not isinstance(close,(int,float)) or isinstance(close,bool) or
                    not isinstance(prior_close,(int,float)) or isinstance(prior_close,bool) or
                    not math.isfinite(close) or not math.isfinite(prior_close) or close<=0 or prior_close<=0):
                return None
            return close/prior_close-1
        now,old=ret(day),ret(prior3)
        if now is not None and old is not None:comparison.append((now,old))
    # The existing implementation is the positive-indicator definition. Keep
    # it for the recorded-axis parity check while exposing the distinct SIGN
    # definition for independent S02 contract adjudication.
    breadth_metrics=candidate_breadth_formula_comparison(comparison,
        boundary=candidate_threshold('market_breadth_axis'))
    breadth_positive=breadth_metrics['positive_indicator']['value']
    formula_comparison=dict(breadth_metrics)
    formula_comparison.update(contract='S02_BREADTH_FORMULA_COMPARISON_R1',
        positive_indicator={**breadth_metrics['positive_indicator'],'definition':'I(r>0) in {0,1}','zero_return':'0'},
        signed={**breadth_metrics['signed'],'definition':'SIGN(r) in {-1,0,1}','zero_return':'0'},
        adjudication='OPEN_SOURCE_CONTRACT_REVIEW_REQUIRED')
    amounts=[]
    for row in core_rows:
        fact=(row.get('fields') or {}).get('amount_ratio20') or {};value=fact.get('value')
        if fact.get('quality_state')=='OBSERVED' and isinstance(value,(int,float)) and not isinstance(value,bool):amounts.append(value)
    participation=statistics.median(amounts) if amounts else None
    return breadth_positive,participation,dict(comparison_trade_date=prior3,universe_count=len(universe),
        current_members=len(current),breadth_evaluable=len(comparison),participation_evaluable=len(amounts),
        breadth_formula='MEAN(POSITIVE_INDICATOR(RET1_T)-POSITIVE_INDICATOR(RET1_T_MINUS_3))',
        breadth_formula_comparison=formula_comparison,
        return_window=dict(current_return='close_t / close_t_minus_1 - 1',
            comparison_return='close_t_minus_3 / close_t_minus_4 - 1',
            coordinate='QFQ_OHLC',missing_policy='EXCLUDE_FROM_EVALUABLE_COMPARISON',
            source='BOUND_MARKET.history.jsonl.gz',as_of=day),
        participation_formula='MEDIAN(CORE.amount_ratio20 WHERE quality_state=OBSERVED)',
        market_owner_binding=market_binding,history_binding=history_ref,membership_binding=membership_ref,
        comparison_membership_binding=predecessor or membership_ref,
        recorded_breadth_axis=market.get('axes',{}).get('breadth_axis'),
        recorded_participation_axis=market.get('axes',{}).get('participation_axis'))


def build_candidate_market_stress(root,candidate):
    """Recalculate available market axes from verified date-bound candidate inputs."""
    root=Path(root);t0=candidate['accepted_trade_date']
    if t0>'2026-10-14':raise ValueError('R7_MARKET_STRESS_CUTOFF_EXCEEDED')
    dates=[d for d in ('2026-10-12','2026-10-13','2026-10-14') if d in candidate.get('owners',{}) and d<=t0]
    outputs={};owners={}
    for day in dates:
        limit_binding,receipt_owner,receipt_path,receipt_sha=_limit_owner(root,candidate,day)
        states_rows=_read_rows(_checked(root,limit_binding));states={r['security_id']:r['limit_state'] for r in states_rows}
        valid={sid:value for sid,value in states.items() if value in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')}
        core_binding=candidate['owners'][day]['core'];core_rows=_read_rows(_checked(root,core_binding))
        universe={row['security_id'] for row in core_rows if row.get('security_id')};common=set(valid)&universe
        coverage=len(common)/len(universe) if universe else None
        stress=sum(valid[sid]=='LIMIT_DOWN' for sid in common)/len(common) if common else None
        index=candidate['published_sessions'].index(day)
        prior_day=candidate['published_sessions'][index-1] if index>0 else None;prior_valid=None
        if prior_day and prior_day in ('2026-10-12','2026-10-13','2026-10-14'):
            prior_binding,prior_owner,_,_=_limit_owner(root,candidate,prior_day)
            prior_rows=_read_rows(_checked(root,prior_binding));prior_states={r['security_id']:r['limit_state'] for r in prior_rows}
            comparable=common&{sid for sid,state in prior_states.items() if state in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')}
            if comparable:
                prior_valid=dict(day=prior_day,ratio=sum(prior_states[s]=='LIMIT_DOWN' for s in comparable)/len(comparable),
                    current_ratio=sum(valid[s]=='LIMIT_DOWN' for s in comparable)/len(comparable),common_count=len(comparable),owner=prior_binding)
        market_binding=candidate['owners'][day].get('market') or {}
        breadth,participation,axis_inputs=_market_axes_from_owner(root,candidate,day,core_binding,market_binding,core_rows)
        source_identity=dict(day=day,core=core_binding,limits=limit_binding,receipt_sha256s=receipt_owner['_receipt_sha256s'],
            source=receipt_owner['baostock_source'],market=market_binding,axis_inputs=axis_inputs,prior=prior_valid)
        source_digest=hashlib.sha256(_canonical(source_identity)).hexdigest()
        axes=market_axis_primitives(breadth=breadth,participation=participation,limit_coverage=coverage,
            stress_ratio=stress,prior_stress_ratio=prior_valid['ratio'] if prior_valid else None,
            stress_change_current_ratio=prior_valid['current_ratio'] if prior_valid else None,
            stress_change_current_provided=bool(prior_valid),trade_date=day,market_calendar_id='V4_OFFICIAL',
            market_snapshot_id=market_binding.get('sha256') or core_binding['sha256'],
            adjustment_basis_id=core_binding['sha256'],input_source_digest=source_digest)
        if (axis_inputs['recorded_breadth_axis']!=axes['breadth_axis'] or
                axis_inputs['recorded_participation_axis']!=axes['participation_axis']):
            raise ValueError('R7_MARKET_AXIS_RECALCULATION_MISMATCH:'+day)
        outputs[day]=dict(T0=day,stress_level=axes['stress_level'],stress_change=axes['stress_change'],
            breadth_axis=axes['breadth_axis'],participation_axis=axes['participation_axis'],
            trend_axis=dict(value='UNKNOWN',quality='SOURCE_INCOMPLETE',reason='BOUND_MARKET_RELATIVE_REFERENCE_PATH_NOT_PROVEN',
                contract_id='MARKET_REGIME_TREND_WEAK_ERRATUM_V1'),
            composite_regime_status='NOT_PUBLISHED_V4_03',status='CANDIDATE_POST_HOC',
            AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False,known_count=len(common),universe_count=len(universe),
            limit_coverage=coverage,limit_state_counts={name:sum(states.get(sid)==name for sid in common)
                for name in ('NOT_LIMIT','LIMIT_UP','LIMIT_DOWN')},unknown_count=sum(states.get(sid)=='UNKNOWN' for sid in universe),
            suspended_count=sum(states.get(sid)=='SUSPENDED' for sid in universe),
            capture_observed_at=receipt_owner['baostock_source']['capture_observed_at'],limit_owner=limit_binding,
            limit_receipt_path=str(receipt_path),limit_receipt_sha256=receipt_sha,raw_source=receipt_owner['baostock_source'],
            core_owner=core_binding,market_owner=market_binding,axis_inputs=axis_inputs,breadth_value=breadth,
            participation_value=participation,prior_comparison=prior_valid,input_digest=axes['input_digest'],
            output_digest=axes['output_digest'],source_digest=source_digest,contract_id=axes['contract_id'],
            parameter_set_id=axes['parameter_set_id'])
        owners[day]=dict(receipt_path=str(receipt_path),limit=limit_binding,raw=receipt_owner['baostock_source'],core=core_binding)
    return dict(contract_id='R7_CANDIDATE_MARKET_STRESS_PREVIEW_V2',T0=t0,status='READY' if outputs else 'SOURCE_INCOMPLETE',
        input_authority='EXPLICIT_SUCCESSOR_CANDIDATE_PLUS_POST_HOC_DATED_BAOSTOCK',market_stress=outputs,source_owners=owners,
        trend_axis_status='UNKNOWN_REFERENCE_PATH_NOT_COMPLETE_AT_T0',
        composite_regime_status='NOT_PUBLISHED_V4_03',AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False)
