"""Independent previously uncovered known current Profile primitive arithmetic."""
import json
from collections import Counter
from scripts.v4_closeout_core_uncovered_numeric_oracle import ROOT,OUT,jsonlines,average
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    target=OUT/'PROFILE_KNOWN_PRIMITIVE_ORACLE_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_PRIOR_PRIMITIVE_ORACLE')
    prep=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R2.json').read_bytes())
    candidate=json.loads(checked(ROOT,prep['candidate']).read_bytes());day=candidate['accepted_trade_date']
    receipt=json.loads(checked(ROOT,candidate['day_receipt']).read_bytes())
    replay=json.loads(checked(ROOT,receipt['numeric_core_oracle']).read_bytes())
    owner=next(x for x in replay['owners'] if x['trade_date']==day)
    parameters={r['parameter_id']:r['value'] for r in json.loads((ROOT/'config/v4_04_parameter_set_v1.json').read_bytes())['parameters']}
    checks=Counter();unknown=Counter();errors=[]
    for history,core,profile in zip(jsonlines(checked(ROOT,owner['history'])),jsonlines(checked(ROOT,owner['core'])),jsonlines(checked(ROOT,candidate['owners'][day]['profile']))):
        sid=history['security_id']
        if sid!=core['security_id'] or sid!=profile['security_id']:raise ValueError('PRIMITIVE_INPUT_ALIGNMENT')
        bars=history['bars'];current=bars[-1] if bars and bars[-1]['trade_date']==day else None
        fields=core['fields']
        for name,cell in profile['derived_fields'].items():
            if cell['value'] is None:
                unknown[name]+=1
                continue
            if current is None or not current['qfq_ohlc']:raise ValueError('KNOWN_PRIMITIVE_MISSING_CURRENT_BAR')
            close=current['qfq_ohlc'][3]
            if name=='ma10':
                window=bars[-10:]
                if len(window)!=10 or not all(b['qfq_ohlc'] for b in window):raise ValueError('KNOWN_MA10_INPUT')
                expected=average(b['qfq_ohlc'][3] for b in window)
            elif name=='pos250':
                window=bars[-250:]
                if len(window)!=250 or not all(b['qfq_ohlc'] for b in window):raise ValueError('KNOWN_POS250_INPUT')
                high=max(b['qfq_ohlc'][1] for b in window);low=min(b['qfq_ohlc'][2] for b in window)
                expected=(close-low)/(high-low)
            elif name in ('bias20_atr','dist_high20_atr'):
                numerator=close-fields['ma20']['value'] if name=='bias20_atr' else fields['prior_high20']['value']-close
                expected=numerator/fields['atr20']['value']
            elif name=='minimum_liquidity':
                window=bars[-21:-1]
                if len(window)!=20:raise ValueError('KNOWN_LIQUIDITY_INPUT')
                threshold=parameters['V4_04_MINIMUM_LIQUIDITY_CNY']
                expected=average(b['amount'] for b in window)>=threshold
            else:raise ValueError('UNDECLARED_DAILY_PRIMITIVE')
            checks[name]+=1
            if expected!=cell['value']:errors.append(dict(security_id=sid,field=name,actual=cell['value'],expected=expected))
    result=dict(contract_id='V4_CURRENT_KNOWN_PROFILE_PRIMITIVE_INDEPENDENT_ARITHMETIC_R1',acceptance='PASS_KNOWN_SCOPE' if not errors else 'FAIL',candidate=prep['candidate'],T0=day,history=owner['history'],profile=candidate['owners'][day]['profile'],checks=dict(checks),check_count=sum(checks.values()),unknown_not_arithmetically_accepted=dict(unknown),errors=errors,scope='Known five daily primitive arithmetic only; calendar/status UNKNOWN window completeness remains separate; previously passed MA20/ATR20 reused, producers not imported or reexecuted',verifier=ref(__import__('pathlib').Path(__file__).resolve().parents[1],__import__('pathlib').Path(__file__).resolve()))
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['check_count'],errors=len(errors))))

if __name__=='__main__':main()
