"""Independent bound observation-window metadata; conserved numeric values."""
import hashlib
import json
import os
from pathlib import Path
from v4_closeout_core_availability_oracle_r1 import ROOT, OUT, inputs, load, rows


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def main():
    target = OUT/'WINDOW_METADATA.json'
    if target.exists():raise ValueError('PRESERVE_CORE_WINDOW_METADATA')
    previous = load(OUT/'RESULT.json')
    if previous['acceptance']!='PASS_CORE_AVAILABILITY_SCOPE':raise ValueError('CORE_AVAILABILITY_REQUIRED')
    prep,candidate,day,owner,dates,histories,suspended,status_refs=inputs()
    counts,errors,error_count={},[],0
    for row in rows(ROOT/owner['core']['path']):
        sid,fields=row['security_id'],row['fields']
        first,bars,ledger=histories[sid]
        basis,source=row['price_basis_id'],owner['source_digest']
        def state(date):
            bar=bars.get(date)
            return 'ACTUAL' if bar and bar['qfq_ohlc'] else 'ADJUSTMENT_UNKNOWN' if bar else 'CONFIRMED_SUSPENSION' if (sid,date) in suspended else 'UNKNOWN'
        def technical(size,prior=False):
            available=ledger[:-1] if prior else ledger
            if not available:return []
            if not prior and state(available[-1]) in ('UNKNOWN','ADJUSTMENT_UNKNOWN'):return available[-1:]
            observed=0
            for index in range(len(available)-1,-1,-1):
                if state(available[index]) in ('UNKNOWN','ADJUSTMENT_UNKNOWN'):return available[index:]
                if state(available[index])=='ACTUAL':
                    observed+=1
                    if observed==size:return available[index:]
            # Immutable CORE_FACTOR_V1 records an empty unfulfilled technical
            # window. Availability/shortage reasons were independently checked.
            return []
        windows={}
        for n in (5,20,60):
            for prefix in ('ma','hhv','llv'):windows[prefix+str(n)]=technical(n)
            for prefix in ('prior_high','prior_low'):windows[prefix+str(n)]=technical(n,True)
        for n in (5,20):
            for prefix in ('amount_ratio','volume_ratio'):windows[prefix+str(n)]=[*technical(n,True),day]
            windows['atr'+str(n)]=technical(n+1)
        windows.update(tr=technical(2),slope20=technical(25),slope60=technical(70),hh_progress=technical(10),ll_progress=technical(10),clv=technical(1),prior60_percentile=[*technical(60,True),day])
        for n in (1,3,5,20):
            window=dates[-n-1:] if len([d for d in dates if d>=first])>=n+1 else [d for d in dates if d>=first]
            windows['ret'+str(n)]=window
            if n in (5,20):windows['vol'+str(n)]=window
        expected={}
        for name,window in windows.items():
            kind='CROSS_SECTION_SESSION_WINDOW_V1' if name.startswith(('ret','vol')) and not name.startswith('volume') else 'TECHNICAL_BAR_WINDOW_V1'
            observations=[(date,state(date),basis if state(date)=='ACTUAL' else None,source if state(date)=='ACTUAL' else None) for date in window]
            cell=fields[name]
            expected[name]=dict(value=cell['value'],quality_state=cell['quality_state'],unknown_reason=cell['unknown_reason'],window_identity=digest([kind,name,sid,observations]),window_start_trade_date=window[0] if window else None,window_end_trade_date=window[-1] if window else None,calendar_span=len(window),actual_count=sum(state(d)=='ACTUAL' for d in window),suspended_count=sum(state(d)=='CONFIRMED_SUSPENSION' for d in window),input_digest=digest([(d,source if state(d)=='ACTUAL' else state(d)) for d in window]),contract_id='CORE_FACTOR_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1')
        deps={'pos60':['llv60','hhv60','llv60','hhv60'],'range_ratio':['hhv5','hhv20','llv5','llv20'],'atr_ratio':['atr5','atr20'],'vol_ratio':['vol5','vol20'],'core_price_damage':['prior_low20','atr20','ret1']}
        for name,names in deps.items():
            dependencies=[expected[n] for n in names];cell=fields[name]
            starts=[d['window_start_trade_date'] for d in dependencies if d['window_start_trade_date']]
            ends=[d['window_end_trade_date'] for d in dependencies if d['window_end_trade_date']]
            expected[name]=dict(value=cell['value'],quality_state=cell['quality_state'],unknown_reason=cell['unknown_reason'],window_identity=digest(['CORE_FACTOR_V1',name,sid,[d['window_identity'] for d in dependencies]]),window_start_trade_date=min(starts) if starts else None,window_end_trade_date=max(ends) if ends else None,calendar_span=max(d['calendar_span'] for d in dependencies),actual_count=max(d['actual_count'] for d in dependencies),suspended_count=max(d['suspended_count'] for d in dependencies),input_digest=digest([d['input_digest'] for d in dependencies]),contract_id='CORE_FACTOR_V1',parameter_set_id='V4_03_CORE_FACTOR_PARAMETER_SET_V1')
        if len(expected)!=39:raise ValueError('CORE_WINDOW_FIELD_DENOMINATOR')
        for name,payload in expected.items():
            payload['output_digest']=digest(payload)
            for key,wanted in payload.items():
                if key in ('value','quality_state','unknown_reason'):continue
                counts[key]=counts.get(key,0)+1
                if fields[name].get(key)!=wanted:
                    error_count+=1
                    if len(errors)<100:errors.append(dict(security_id=sid,field=name,key=key,actual=fields[name].get(key),expected=wanted))
    result=dict(contract_id='V4_CORE_CURRENT_OBSERVATION_WINDOW_METADATA_ORACLE_R1',acceptance='PASS_CORE_WINDOW_METADATA_SCOPE' if not error_count else 'FAIL',T0=day,candidate=prep['candidate'],core=owner['core'],history=owner['history'],status_sources=status_refs,checks=counts,check_count=sum(counts.values()),error_count=error_count,first_errors=errors,
        reused_availability_receipt=dict(path=str(OUT/'RESULT.json'),sha256=hashlib.sha256((OUT/'RESULT.json').read_bytes()).hexdigest()),known_numerical_arithmetic_reexecuted=False,previous_availability_checks_reexecuted=False,primary_core_module_imported=False,publication_ready=False,
        scope='39 Core fields: observation window identities, temporal endpoints, counts, source/coordinate input digests and output digests. Value/quality/reason arithmetic and availability use their preserved independent receipts.')
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2),encoding='utf-8');os.replace(temporary,target)
    print(json.dumps(dict(acceptance=result['acceptance'],checks=result['check_count'],errors=error_count)))
    return bool(error_count)


if __name__=='__main__':raise SystemExit(main())
