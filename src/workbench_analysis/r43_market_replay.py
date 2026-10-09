"""Executable market/rotation candidate kernels with explicit local blockers."""
from collections import defaultdict, Counter
import hashlib,json
from pathlib import Path
from statistics import fmean, median
from .r43_owner_replay import load, checked, gzrows, gzwrite, ref, OUT
from .market_source_acquisition import official_sessions, write
from .v4_13_descendant_contracts import DescendantContracts
from sector.rotation_r5 import advance_rotation, evaluate_b0, resolve_package
from v4.factors.native import market_axis_primitives, market_trend_axis
from v4.market_regime_ui import project
from dataclasses import asdict


def materialize_market(root):
    root=Path(root).resolve();out=root/OUT;profiles=load(out/'PROFILE_STRUCTURE_REPLAY.json')
    sessions=official_sessions(root);c=DescendantContracts(root);dep=c.dependencies
    param,registry=resolve_package(dep['rotation_contract'],dep['parameter_set'],
         checked(root,c.config['loo_context']['accepted_sector_dependencies']['parameter_set']).read_bytes(),dep['field_registry'])
    write(out/'MARKET_STAGE_ENTRY.json',dict(task='R4.3',contract='R4_CORRECTED_MARKET_ROTATION_V1',
        accepted=False,prior_rotation='No accepted corrected episode; execute original UNKNOWN-preserving gate',
        price_limit_owner='R43_RECONSTRUCTED_DAILY_PRICE_LIMIT_V1 actual frozen isST/rules/raw; intraday remains unobservable',next_stage='INDEPENDENT_QA'))
    from .r43_daily_price_limits import materialize_daily_limits
    limits_receipts=materialize_daily_limits(root)
    limit_sources={r['trade_date']:r['artifact'] for r in limits_receipts}
    limits={d:{r['security_id']:r['limit_state'] for r in gzrows(checked(root,binding)) if r['limit_state'] in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT')} for d,binding in limit_sources.items()}
    receipts=[]
    for item in profiles['owners']:
        owner=item['owner'];day=owner['trade_date'];folder=out/'owners'/day
        factors={r['security_id']:r for r in gzrows(checked(root,owner['core']))}
        hist={r['security_id']:{b['trade_date']:b for b in r['bars']} for r in gzrows(checked(root,owner['history']))}
        prior3=sessions[sessions.index(day)-3];previous=sessions[sessions.index(day)-1]
        comparisons=[];amounts=[]
        for sid,f in factors.items():
            bars=hist[sid]
            def ret(d):
                a=bars.get(d,{}).get('qfq_ohlc');b=bars.get(sessions[sessions.index(d)-1],{}).get('qfq_ohlc')
                return a[3]/b[3]-1 if a and b and b[3]>0 else None
            a,b=ret(day),ret(prior3)
            if a is not None and b is not None:comparisons.append((a,b))
            ar=f['fields']['amount_ratio20']['value']
            if ar is not None:amounts.append(ar)
        # Endpoint membership is explicitly intersected with the saved historic owner.
        historical=load(root/'config/v4_market_operational_authority_v1.json')['market']
        market=load(checked(root,historical));membership=market['sources']['historical_universe']
        members=defaultdict(set)
        for r in gzrows(checked(root,membership)):
            if r.get('board_scope') in ('SH_MAIN','SZ_MAIN','STAR','CHINEXT'):members[r['trade_date']].add(r['security_id'])
        for old in profiles['owners']:
            if old['owner']['trade_date']<=day:
                members[old['owner']['trade_date']]={r['security_id'] for r in gzrows(checked(root,old['owner']['core']))}
        universe=members.get(prior3,set())
        if not universe:
            previous_owner=next((x['owner'] for x in profiles['owners'] if x['owner']['trade_date']==prior3),None)
            if previous_owner:universe={r['security_id'] for r in gzrows(checked(root,previous_owner['core']))}
        common=set(factors)&universe
        comparisons=[]
        for sid in common:
            bars=hist[sid]
            def ret(d):
                a=bars.get(d,{}).get('qfq_ohlc');b=bars.get(sessions[sessions.index(d)-1],{}).get('qfq_ohlc')
                return a[3]/b[3]-1 if a and b and b[3]>0 else None
            a,b=ret(day),ret(prior3)
            if a is not None and b is not None:comparisons.append((a,b))
        breadth=fmean(int(a>0)-int(b>0) for a,b in comparisons) if comparisons else None
        current_limits=limits[day];previous_limits=limits.get(previous,{})
        limit_common=set(current_limits)&set(previous_limits)
        limit_coverage=len(current_limits)/len(factors)
        stress_ratio=sum(v=='LIMIT_DOWN' for v in current_limits.values())/len(current_limits) if current_limits else None
        prior_stress=sum(previous_limits[s]=='LIMIT_DOWN' for s in limit_common)/len(limit_common) if limit_common else None
        same_current_stress=sum(current_limits[s]=='LIMIT_DOWN' for s in limit_common)/len(limit_common) if limit_common else None
        source_digest=hashlib.sha256(json.dumps(dict(core_owner=owner['source_digest'],current_limits=limit_sources[day],prior_limits=limit_sources.get(previous),producer=ref(root,Path(__file__))),sort_keys=True).encode()).hexdigest()
        identity=dict(trade_date=day,market_calendar_id='R4_OFFICIAL',market_snapshot_id=owner['source_digest'],
              adjustment_basis_id=owner['source_digest'],input_source_digest=source_digest)
        axes=market_axis_primitives(breadth=breadth,participation=median(amounts) if amounts else None,
              limit_coverage=limit_coverage,stress_ratio=stress_ratio,prior_stress_ratio=prior_stress,stress_change_current_ratio=same_current_stress,
              stress_change_current_provided=True,**identity)
        prefixpath=root/'reports/v4_03/staging/V4_03_MARKET_REFERENCE_PATH_CANDIDATE_R3.jsonl.gz'
        prefix=[r for r in gzrows(prefixpath) if r['trade_date']<=day]
        levels=[r['level'] for r in prefix];level=levels[-1];bridge=[]
        policy=load(root/'config/v4_market_path_successor_contract_v1.json')
        for d in sessions[sessions.index(prefix[-1]['trade_date'])+1:sessions.index(day)+1]:
            prev=sessions[sessions.index(d)-1];start=members.get(prev,set());returns=[]
            for sid in sorted(start):
                bars=hist.get(sid,{})
                a=bars.get(d,{}).get('qfq_ohlc');b=bars.get(prev,{}).get('qfq_ohlc')
                if a and b and b[3]>0:returns.append(a[3]/b[3]-1)
            coverage=len(returns)/len(start) if start else 0
            change=fmean(returns) if returns and coverage>=policy['minimum_bridge_coverage'] else None
            level=level*(1+change) if level is not None and change is not None else None
            levels.append(level);bridge.append(dict(trade_date=d,start_trade_date=prev,start_members=len(start),evaluable=len(returns),coverage=coverage,level=level))
        def ma(values):return fmean(values) if len(values)==20 and all(x is not None for x in values) else None
        trend=market_trend_axis(index_close=level,index_ma20=ma(levels[-20:]),index_ma20_t_minus_5=ma(levels[-25:-5]),**identity)
        row=dict(trade_date=day,trend_axis=trend['trend_axis'],**{k:axes[k] for k in ('breadth_axis','participation_axis','stress_level','stress_change')})
        regime=asdict(project([row])[day])
        write(folder/'market_owner_candidate_v2.json',dict(trade_date=day,axes=axes,trend=trend,regime=regime,
              breadth_common_count=len(common),breadth_evaluable=len(comparisons),comparison_trade_date=prior3,
              input_bindings=[owner['core'],owner['history'],membership,ref(root,prefixpath),limit_sources[day]]+([limit_sources[previous]] if previous in limit_sources else []),AS_RECORDED=False,accepted=False,
              index_successor_bridge=bridge,trend_blocker=None if level is not None else 'INCOMPLETE_DATED_INDEX_BRIDGE',stress_blocker=None if stress_ratio is not None else 'NO_ACCEPTED_DATED_DAILY_LIMIT_OBSERVATIONS',stress_change_blocker=None if limit_common else 'NO_SAME_MEMBER_PRIOR_DAILY_LIMIT_OWNER',daily_limit_coverage=limit_coverage,daily_limit_known=len(current_limits),stress_same_member_count=len(limit_common),intraday_touch='NOT_OBSERVABLE_FROM_DAILY'))
        receipts.append(dict(trade_date=day,market=ref(root,folder/'market_owner_candidate_v2.json'),knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,PIT_ELIGIBLE=False))
    write(out/'MARKET_REPLAY.json',dict(owners=receipts,acceptance='EXECUTED_FIELD_LOCAL_OBSERVABILITY_GAPS',production_admission=False))
    return receipts
