"""Reconstructed dated daily-close limits from saved isST and audited rules."""
from decimal import Decimal
from pathlib import Path
from collections import Counter, defaultdict
from tdx.gbbq_reader import read_gbbq
from .limit_rules import LimitStateService
from .special_price_phases import SpecialPhaseEventStore,PhasePolicyRegistry,resolve_event_phase
from .r43_owner_replay import OUT,load,checked,gzrows,gzwrite,ref
from .market_source_acquisition import official_sessions,write

def materialize_daily_limits(root):
    root=Path(root).resolve();out=root/OUT;core=load(out/'CORE_REPLAY.json');sessions=official_sessions(root)
    trace=load(out.parent/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json')
    rules_binding=ref(root,root/'config/v4_02_price_limit_rules_r3.json');rules=load(checked(root,rules_binding))
    for rule in rules['rules']:
        if rule.get('source_capture_path'):
            checked(root,dict(path=rule['source_capture_path'],sha256=rule['source_capture_sha256']))
    service=LimitStateService(rules['rules']);policy_binding=ref(root,root/'config/special_price_phase_policy_r6.json')
    policy=PhasePolicyRegistry(load(checked(root,policy_binding)))
    event_binding=ref(root,root/'data/v4/bootstrap/special_price_phase_events_r4.jsonl')
    store=SpecialPhaseEventStore.from_jsonl(checked(root,event_binding));identities=load(checked(root,core['owners'][0]['sources']['identity']))['rows']
    identities={r['security_id']:r for r in identities};events=defaultdict(list)
    for e in read_gbbq(checked(root,core['owners'][0]['sources']['gbbq'])):
        if e.category==1:events[e.security_id.lower()].append(e.event_date)
    contract=out/'DAILY_PRICE_LIMIT_CONTRACT_V1.json'
    write(contract,dict(contract_id='R43_RECONSTRUCTED_DAILY_PRICE_LIMIT_V1',task='R4.3 W5',identity='Accepted canonical board and dated saved BaoStock native isST; never infer ST from code or current name',reference='Saved native preclose must equal preceding official raw close; ex-right day unavailable official ex-reference remains UNKNOWN',daily_observable=['close_limit_up','close_limit_down','daily_high_equals_limit_up','daily_low_equals_limit_down','one_price_limit_bar'],intraday='NOT_OBSERVABLE_FROM_DAILY',legal_rules=rules_binding,AS_RECORDED=False,PIT_ELIGIBLE=False,production_admission=False,acceptance='IN_PROGRESS',next_stage='INDEPENDENT_DATED_LIMIT_QA'))
    receipts=[]
    for owner,item in zip(core['owners'],trace['dates']):
        day=owner['trade_date'];previous=sessions[sessions.index(day)-1];bao=load(checked(root,item['baostock']))
        source_rows={r['code'].lower():r for r in bao['rows']};raw={r['security_id']:r for r in gzrows(checked(root,owner['raw']))};histories={r['security_id']:{b['trade_date']:b for b in r['bars']} for r in gzrows(checked(root,owner['history']))};records=[]
        for sid,bars in histories.items():
            identity=identities[sid];code=identity['source_security_key'].lower();provider=source_rows.get(code,{});bar=raw.get(sid);board=policy.standard_rule_key(day,identity['board_scope']);phase,event=resolve_event_phase(store,sid,day,sessions,policy,identity['board_scope'])
            listing=identity.get('list_date');listed_sessions=[d for d in sessions if listing and listing<=d<=day]
            if listing and len(listed_sessions)<=5 and listed_sessions:phase_name='IPO_FIRST_5_TRADING_DAYS'
            else:phase_name=phase.value
            previous_bar=bars.get(previous);reference_ok=False
            try:reference_ok=bool(previous_bar and Decimal(provider.get('preclose','0'))==Decimal(str(previous_bar['raw_ohlc'][3])))
            except Exception:pass
            risk='RISK_WARNING' if provider.get('isST')=='1' else 'NORMAL' if provider.get('isST')=='0' else 'UNKNOWN'
            inputs=dict(security_id=sid,trade_date=day,exchange=board[0] if board else '',board=board[1] if board else '',risk_status=risk,listing_phase=phase_name,suspended=bar is None and provider.get('tradestatus')=='0',reference_status='KNOWN' if reference_ok else 'UNKNOWN',quote_prev_close=provider.get('preclose'),close=bar['close'] if bar else None,ex_rights_reference_unknown=int(day.replace('-','')) in events[code])
            state=service.evaluate(inputs);state['trade_date']=day
            state.update(source_security_key=code,board_scope=identity['board_scope'],native_isST=provider.get('isST'),listing_phase=phase_name,source_refs=[owner['raw'],owner['history'],item['baostock'],owner['sources']['identity'],rules_binding,policy_binding,event_binding],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,PIT_ELIGIBLE=False,intraday_touch='NOT_OBSERVABLE_FROM_DAILY')
            up=state['limit_up_price'];down=state['limit_down_price'];known=state['limit_state'] in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT')
            if known and bar:
                state.update(daily_high_equals_limit_up=Decimal(str(bar['high']))==up,daily_low_equals_limit_down=Decimal(str(bar['low']))==down,one_price_limit_bar=bar['open']==bar['high']==bar['low']==bar['close'] and state['limit_state'] in ('LIMIT_UP','LIMIT_DOWN'))
            else:state.update(daily_high_equals_limit_up=None,daily_low_equals_limit_down=None,one_price_limit_bar=None)
            for k in ('limit_up_price','limit_down_price'):state[k]=str(state[k]) if state[k] is not None else None
            records.append(state)
        artifact=gzwrite(root,out/'owners'/day/'daily_price_limits_v1.jsonl.gz',records)
        receipts.append(dict(trade_date=day,artifact=artifact,rows=len(records),counts=dict(Counter(r['limit_state'] for r in records)),unknown_reasons=dict(Counter(r['reason'] for r in records if r['limit_state']=='UNKNOWN')),limit_coverage=sum(r['limit_state'] in ('LIMIT_UP','LIMIT_DOWN','NOT_LIMIT') for r in records)/len(records),daily_observable_known=sum(r['daily_high_equals_limit_up'] is not None for r in records)))
    write(out/'DAILY_PRICE_LIMIT_REPLAY.json',dict(contract=ref(root,contract),owners=receipts,acceptance='EXECUTED_DATED_DAILY_CLOSE_AND_EXTREMA_LIMIT_OBSERVATIONS',production_admission=False))
    return receipts
