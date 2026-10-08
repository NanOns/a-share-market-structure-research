"""Read-only live Focus/Forward and independent ex-day affine sample audit."""
import collections
import json
import sys
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_three_day_repair_r1 import OUT,load
from scripts.fp01_evidence import write,ref
from tdx.gbbq_reader import read_gbbq


def main():
    joint=load('config/v4_joint_release_authority_v1.json');manifest=load(joint['snapshot']['manifest']['path'])
    focus=manifest['domain_features']['focus'];forward=manifest['domain_features']['forward'];target=focus['trade_date']
    market=load(load('config/v4_market_operational_authority_v1.json')['market']['path'])
    raw={d:{r['security_id']:r for r in load(market['sources'][d+':RAW_DAILY']['path'])['rows']} for d in ('2026-09-29','2026-09-30')}
    gbbq=market['sources']['gbbq'];events=list(read_gbbq(ROOT/gbbq['path']))
    counts=collections.Counter();samples=[];failures=[]
    with localcontext() as ctx:
        ctx.prec=40
        for episode in focus['episodes']:
            for o in episode['observations']:counts[o['trade_date']]+=1
            sid=episode['entity_id']
            if episode['T0']!='2026-09-29' or sid not in raw['2026-09-29'] or sid not in raw['2026-09-30']:continue
            symbol=raw['2026-09-30'][sid]['source_security_key']
            effective=sorted([e for e in events if e.security_id==symbol and e.category==1 and e.event_date==20260930],key=lambda e:e.source_record_index)
            if not effective:continue
            price=Decimal(str(raw['2026-09-29'][sid]['close']));steps=[]
            for e in effective:
                cash,rights_price,bonus,rights=[Decimal(str(v)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP) for v in (e.c1,e.c2,e.c3,e.c4)]
                m=(Decimal(10)+bonus+rights)/10;c=(cash-rights*rights_price)/10
                before=price;price=(price-c)/m
                steps.append(dict(record_index=e.source_record_index,raw_parameters=dict(cash=str(cash),rights_price=str(rights_price),bonus=str(bonus),rights=str(rights)),m=str(m),c=str(c),before=str(before),after=str(price)))
            anchor=price.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
            expected=Decimal(str(raw['2026-09-30'][sid]['close']))/anchor-1
            obs=next((o for o in episode['observations'] if o['trade_date']==target),None)
            actual=(obs or {}).get('price_path',{}).get('metrics',{}).get('return_close')
            ok=actual is not None and abs(expected-Decimal(actual))<Decimal('1e-20')
            samples.append(dict(security_id=sid,symbol=symbol,episode_id=episode['episode_id'],steps=steps,
                rounded_anchor=str(anchor),raw_target_close=raw['2026-09-30'][sid]['close'],expected_return=str(expected),actual_return=actual,result='PASS' if ok else 'FAIL'))
            if not ok:failures.append(sid)
    plans=forward['plans'];due=[p for p in plans if p.get('due_date') and p['due_date']<=target]
    write(OUT/'C_FOCUS_FORWARD_TEMPORAL_ORACLE.json',dict(source=joint['snapshot']['manifest'],focus_observations_by_day=dict(counts),
        independent_affine_samples=samples,gbbq=ref(gbbq['path']),failures=failures,
        forward=dict(enrollments=len(forward['enrollments']),plans=len(plans),due=len(due),
            states=dict(collections.Counter(p['outcome_status'] for p in plans)),frozen_T0_count=len(forward['t0_freezes']),
            result='PASS_PENDING_NO_DUE' if not due and all(p['outcome_status']=='PENDING' for p in plans) else 'REVIEW'),
        result='PASS_SCOPED_AFFINE_AND_TEMPORAL' if not failures else 'FAIL',full_focus_event_matrix=False,
        focus_path_never_counted_as_forward_settlement=True,live_authority_changed=False))
    print(json.dumps(dict(samples=len(samples),failures=failures,due=len(due),observations=dict(counts))))


if __name__=='__main__':main()
