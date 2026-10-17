"""Explicit engineering HTTP capability over native PG history and frozen GBBQ.

This handler is never selected by default startup or accepted authority.
"""
from dataclasses import asdict
from datetime import date as CalendarDate
from decimal import Decimal
import hashlib,json
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from .core_product_server_r1 import make_product_handler
from .core_product_bff_r1 import dated_product_manifest,CoreProductBFFR1
from .stock_views import aggregate
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_analysis.r43_owner_replay import checked
from workbench_db.v4_history_pg_r1 import read
from adjustment.tdx_adjustment_v0_3 import build_affine_factors,xrxd_from_gbbq
from adjustment.exact_factor_transport_r1 import ExactFactorTransport
from adjustment.exact_ohlc_consumer_r1 import consume_exact_ohlc
from tdx.gbbq_reader import read_gbbq
from v4.factors.core import Bar,Observation,compute_core
from v4 import profile_core
from v4.profile_primitives import derive_daily
from workbench_analysis.market_source_acquisition import official_sessions
from focus_tracker.exact_path_candidate_r3 import exact_path_receipt

CONTRACT='V4_EXACT_PG_CHART_CORE_CANDIDATE_R3'
PATH='/api/v4/candidate/exact-chart'

def candidate(root,query,*,engineering_enable=False):
    if engineering_enable is not True:raise ValueError('EXACT_ENGINEERING_CAPABILITY_DISABLED')
    period=query.get('period','D');limit=int(query.get('limit',120));offset=int(query.get('offset',0))
    if period not in ('D','W','M') or not 1<=limit<=200 or offset<0:raise ValueError('EXACT_CHART_QUERY_INVALID')
    root=Path(root).resolve()
    if root.drive.upper()!='G:' or 'codex_tmp' not in root.parts:
        raise ValueError('EXACT_ENGINEERING_ISOLATION_REQUIRED')
    api=accepted_api(root)
    if query.get('context_token')!=api.token:raise ValueError('CONTEXT_TOKEN_MISMATCH')
    day=query.get('trade_date',api.candidate['accepted_trade_date']);sid=query.get('security_id')
    if day not in api.candidate['owners'] or not sid:raise ValueError('EXACT_DATED_IDENTITY_REQUIRED')
    from .native_product_catalog_v3 import load as load_product_catalog
    authority=load_product_catalog(root,api.candidate)
    manifest=dated_product_manifest(root,authority,day,candidate=api.candidate)
    if not manifest or manifest.get('authority_scope')!='ISOLATED_ENGINEERING_ONLY':
        raise ValueError('EXACT_ENGINEERING_AUTHORITY_REQUIRED')
    history=read(root,manifest['history_index'],day,sid)
    if not history:return 404,dict(contract_id=CONTRACT,status='NOT_FOUND')
    source=api.candidate['source_registry'][day]['gbbq'];source_path=checked(root,source)
    blob=source_path.read_bytes();source_digest=hashlib.sha256(blob).hexdigest()
    identity=CoreProductBFFR1(api,None).resolve_dated_object('stocks',day,sid)
    symbol=identity.get('symbol') if identity else None
    if not symbol:raise ValueError('EXACT_HISTORY_SOURCE_SYMBOL_REQUIRED')
    basis=int(day.replace('-',''));events=[e for e in read_gbbq(source_path) if e.security_id.upper()==symbol.upper() and e.event_date<=basis]
    dispositions=json.loads((root/'config/v4_02_gbbq_price_impact_classification_v1.json').read_bytes())['dispositions']
    blocked=[e for e in events if dispositions.get(str(e.category),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')]
    factors=build_affine_factors([int(b['trade_date'].replace('-','')) for b in history]+[basis],
        [xrxd_from_gbbq(e) for e in events if e.category==1])
    bars=[];observations=[];raw_receipts=[];path_rows={}
    for original in history:
        date=original['trade_date'];date_int=int(date.replace('-',''))
        prices=None;receipt=None;reason=None
        if any(date_int<event.event_date for event in blocked):reason='BLOCKED_ADJUSTMENT_EVENT'
        else:
            row=dict(security_id=symbol.upper(),trade_date=date_int,**dict(zip(('open','high','low','close'),map(str,original['raw_ohlc']))))
            wire=ExactFactorTransport(symbol.upper(),basis,source_digest,factors[date_int]).to_dict()
            receipt=consume_exact_ohlc(row,wire,source_bytes=blob,security_id=symbol.upper(),basis_date=basis)
            path_rows[CalendarDate.fromisoformat(original['trade_date'])]=dict(has_actual_bar=True,exact_factor=wire,
                **{'raw_'+name:row[name] for name in ('open','high','low','close')})
            if receipt['quality']=='READY':prices={k:float(v) for k,v in receipt['prices'].items()}
            else:reason=receipt['quality']
        bar=dict(trade_date=date,**(prices or dict.fromkeys(('open','high','low','close'))),
            amount=original['amount'],volume=original['volume'],quality='KNOWN' if prices else 'UNKNOWN',reason=reason)
        bars.append(bar)
        observations.append(Observation(date,'ACTUAL' if prices else 'ADJUSTMENT_UNKNOWN',
            Bar(**prices,amount=bar['amount'],volume=bar['volume'],adjustment_basis_id=CONTRACT+':'+day,
                source_digest=hashlib.sha256(json.dumps(dict(event_source=source_digest,
                    history_logical_digest=manifest['history_index']['logical_digest'],row=original),sort_keys=True,separators=(',',':')).encode()).hexdigest()) if prices else None))
        if receipt:raw_receipts.append(receipt)
    # Never silently compress missing market sessions into a valid return window.
    by_day={observation.trade_date:observation for observation in observations}
    observations=[by_day.get(date,Observation(date,'UNKNOWN')) for date in official_sessions(root)
        if history[0]['trade_date']<=date<=day]
    data=aggregate(bars,period);end=max(0,len(data)-offset);items=data[max(0,end-limit):end]
    core=compute_core(observations,sid)
    path_sessions=[CalendarDate.fromisoformat(observation.trade_date) for observation in observations[-21:]]
    focus_path=exact_path_receipt(sessions=path_sessions,rows=path_rows,source_bytes=blob,
        security_id=symbol.upper(),basis_date=basis)
    profile_inputs={key:factor.value for key,factor in core.items() if factor.quality_state=='OBSERVED'}
    profile_inputs['close']=bars[-1]['close']
    primitive_bars=[dict(trade_date=bar['trade_date'],qfq_close=bar['close'],qfq_high=bar['high'],
        qfq_low=bar['low'],amount=bar['amount'],adjusted_quality='READY' if bar['quality']=='KNOWN' else 'UNKNOWN') for bar in bars]
    statuses=[(observation.trade_date,'ACTUAL_TRADED' if observation.state=='ACTUAL' else 'UNKNOWN') for observation in observations]
    primitive=derive_daily(primitive_bars,{key:asdict(value) for key,value in core.items()},statuses,day,
        [observation.trade_date for observation in observations])
    profile_inputs.update({key:value.value for key,value in primitive.items() if value.quality=='OBSERVED'})
    # Unsupported supplemental / cross-sectional inputs stay missing, never
    # injected with synthetic RPS, liquidity, membership or calendar evidence.
    states={name:asdict(function(profile_inputs)) for name,function in (
        ('trend_state',profile_core.trend),('position_state',profile_core.position),
        ('ma_structure_state',profile_core.ma_structure),('compression_state',profile_core.compression),
        ('core_participation_result',profile_core.participation),('core_extension_risk',profile_core.extension_risk))}
    for horizon in (20,60):
        states['near_high'+str(horizon)+'_state']=asdict(profile_core.near_high(profile_inputs,horizon))
        states['drawdown'+str(horizon)+'_state']=asdict(profile_core.drawdown(profile_inputs,horizon))
    for name in ('amount','volume'):
        states[name+'_state']=asdict(profile_core.ratio_state(profile_inputs,name+'_ratio20'))
    return 200,dict(contract_id=CONTRACT,status='READY',T0=day,context_token=api.token,
        production_accepted=False,PIT_ELIGIBLE=False,knowledge_lineage='RECONSTRUCTED',
        source_binding=source,history_index=manifest['history_index'],security_id=sid,symbol=symbol,
        price_basis='QFQ_V0_3_EXACT_CANDIDATE',period=period,total=len(data),items=items,
        period_owner_admission='NOT_GRANTED_DIAGNOSTIC_BUCKET_ONLY' if period!='D' else 'ISOLATED_CANDIDATE',
        core={k:asdict(v) for k,v in core.items()},profile_primitives={k:asdict(v) for k,v in primitive.items()},profile_states=states,focus_path=focus_path,
        exact_transport_count=len(raw_receipts),exact_transport_digest=hashlib.sha256(json.dumps(raw_receipts,sort_keys=True,separators=(',',':')).encode()).hexdigest())

def make_exact_candidate_handler(root,jobs,*,engineering_enable=False):
    base=make_product_handler(root,jobs)
    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path!=PATH:return super().do_GET()
            try:
                params=parse_qs(parsed.query,keep_blank_values=True)
                if any(len(values)!=1 for values in params.values()):raise ValueError('DUPLICATE_PARAMETER')
                code,data=candidate(root,{key:value[0] for key,value in params.items()},engineering_enable=engineering_enable)
                return self.send(code,data)
            except (ValueError,KeyError,OSError) as exc:return self.send(400,dict(code='EXACT_CANDIDATE_FAILED',reason=str(exc)))
            except Exception as exc:
                import psycopg
                if isinstance(exc,(psycopg.Error,RuntimeError)):
                    return self.send(503,dict(code='V4_PG_UNAVAILABLE',reason='PG_REQUIRED_NO_FALLBACK'))
                raise
    return Handler
