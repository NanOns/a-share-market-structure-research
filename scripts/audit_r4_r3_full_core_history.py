"""Independent raw ZIP and rational event-price checks for every owner history bar."""
from pathlib import Path
from collections import Counter,defaultdict,deque
from decimal import Decimal,ROUND_HALF_UP
from fractions import Fraction
from bisect import bisect_right
import gzip,hashlib,json,struct,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tdx.gbbq_reader import read_gbbq
workspace=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
generation=sys.argv[1]
if len(generation)!=64 or any(c not in '0123456789abcdef' for c in generation):raise ValueError('EXACT_OWNER_GENERATION_REQUIRED')
folder=workspace/'data/v4/dynamic_daily_owners/2026-10-09'/generation/'owner_v3'
run_id=sys.argv[2] if len(sys.argv)>2 else 'SOURCE_DERIVATION_R12'
if not run_id.startswith('SOURCE_DERIVATION_R') or not run_id.replace('_','').isalnum():raise ValueError('VERSIONED_ORACLE_RUN_ID_REQUIRED')
output=ROOT/'docs/audits/r4_r3_consumers_20261011'/run_id/'FULL_HISTORY_INDEPENDENT_R1.json'
if output.exists():raise ValueError('EXISTING_ORACLE_EVIDENCE_MUST_BE_PRESERVED')
def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):value.update(block)
    return value.hexdigest()
bindings=[]
def bound(ref):
    path=(workspace/ref['path']).resolve()
    if not path.is_relative_to(workspace) or sha(path)!=ref['sha256']:raise ValueError('ORACLE_EXACT_SOURCE_BINDING_INVALID')
    bindings.append(dict(path=ref['path'],sha256=ref['sha256']))
    return path
document=json.loads((folder/'CORE_REPLAY.json').read_bytes());owners=document['owners']
sources=owners[0]['sources'];identity=json.loads(bound(sources['identity']).read_bytes())['rows']
rank={row['security_id']:index for index,row in enumerate(identity)}
actions=defaultdict(list)
for event in read_gbbq(bound(sources['gbbq'])):actions[event.security_id.lower()].append(event)
policy=json.loads((workspace/'config/v4_02_gbbq_price_impact_classification_v1.json').read_bytes())['dispositions']
streams=[];heads=[];counts=Counter();mismatches=[]
for owner in owners:
    stream=gzip.open(bound(owner['history']),'rt',encoding='utf8');streams.append(stream)
    heads.append(json.loads(next(stream)))
maximum=int(max(owner['trade_date'] for owner in owners).replace('-',''))
def rounded(value):
    n,r=divmod(abs(value.numerator)*100,value.denominator);n+=int(2*r>=value.denominator)
    return float(Decimal(('-' if value<0 and n else '')+str(n//100)+'.'+str(n%100).zfill(2)))
def coefficients(events,target):
    eligible=sorted([e for e in events if e.category==1 and e.event_date<=target],key=lambda e:(e.event_date,e.source_record_index))
    # Each suffix is recomputed chronologically from literal event parameters.
    # This does not import the production factor composer or its coefficients.
    suffix=[]
    for start in range(len(eligible)+1):
        a,b=Fraction(1),Fraction(0)
        for event in eligible[start:]:
            cash,rights_price,bonus,rights=[Fraction(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) for v in (event.c1,event.c2,event.c3,event.c4)]
            d=10+bonus+rights
            if d<=0:raise ValueError('ORACLE_INVALID_ACTION_DENOMINATOR')
            a,b=10*a/d,(10*b-cash+rights*rights_price)/d
        suffix.append((a,b))
    return [e.event_date for e in eligible],suffix
try:
    with zipfile.ZipFile(bound(sources['package'])) as package:
        index={}
        for name in package.namelist():
            parts=name.lower().replace('\\','/').split('/');market=next((p for p in parts if p in ('sh','sz','bj')),None)
            if market and parts[-1].endswith('.day'):
                code=market+'.'+parts[-1][-10:-4]
                if code in index:raise ValueError('ORACLE_DUPLICATE_RAW_ZIP_SECURITY')
                index[code]=name
        for position,item in enumerate(identity):
            sid=item['security_id'];code=item['source_security_key'].lower();selected=[]
            for number,head in enumerate(heads):
                if head is not None and rank.get(head['security_id'],-1)<position:raise ValueError('ORACLE_HISTORY_ORDER_OR_IDENTITY_INVALID')
                if head is not None and head['security_id']==sid:
                    selected.append((owners[number],head))
                    line=next(streams[number],None);heads[number]=json.loads(line) if line else None
            if not selected:continue
            if code not in index:raise ValueError('ORACLE_RAW_PACKAGE_SECURITY_MISSING')
            native=deque(maxlen=420)
            for raw in struct.iter_unpack('<IIIIIfII',package.read(index[code])):
                counts['source_binary_records_read']+=1
                if raw[0]<=maximum:native.append(raw)
            raw_by_day={row[0]:row for row in native}
            for owner,history in selected:
                target=int(owner['trade_date'].replace('-',''));dates,prepared=coefficients(actions[code],target)
                barriers=[e.event_date for e in actions[code] if e.event_date<=target and policy.get(str(e.category),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')]
                counts['history_security_rows']+=1
                for bar in history['bars']:
                    day=int(bar['trade_date'].replace('-',''));raw=raw_by_day.get(day);counts['history_bars']+=1
                    if raw is None or day>target:raise ValueError('ORACLE_HISTORY_DAY_OUTSIDE_RAW_SOURCE')
                    for actual,integer in zip(bar['raw_ohlc'],raw[1:5]):
                        counts['raw_ohlc_values']+=1
                        if Fraction(str(actual))!=Fraction(integer,100):mismatches.append(dict(sid=sid,target=target,day=day,field='RAW_OHLC_SOURCE'))
                    blocked=any(day<event for event in barriers)
                    if blocked:
                        counts['independently_verified_unknown_bars']+=1
                        if bar['qfq_ohlc'] is not None:mismatches.append(dict(sid=sid,target=target,day=day,field='UNSUPPORTED_ACTION_NOT_DEGRADED'))
                        continue
                    if bar['qfq_ohlc'] is None:mismatches.append(dict(sid=sid,target=target,day=day,field='UNEXPECTED_QFQ_ABSENCE'));continue
                    a,b=prepared[bisect_right(dates,day)]
                    for actual,integer in zip(bar['qfq_ohlc'],raw[1:5]):
                        expected=rounded(a*Fraction(integer,100)+b);counts['adjusted_ohlc_values']+=1
                        if actual!=expected:mismatches.append(dict(sid=sid,target=target,day=day,field='QFQ_EXACT_RATIONAL',expected=expected,actual=actual))
            if position%250==0:print(json.dumps(dict(phase='FULL_HISTORY_ORACLE',identities=position,counts=dict(counts),mismatches=len(mismatches))),flush=True)
    if any(head is not None for head in heads):raise ValueError('ORACLE_UNCONSUMED_HISTORY_ROWS')
    result=dict(contract_id='R4_R3_ALL_ACTUAL_CORE_HISTORY_RAW_AND_RATIONAL_ORACLE_R1',
        counts=dict(counts),mismatches=mismatches,source_bindings=bindings,
        producer_scope='Every bar in all five actual Core history artifacts; current declared 420-bar producer history window',
        independent_reference='Direct native ZIP integer cents and chronological rational event recurrence; no production factor builder',
        acceptance='SCOPED_FULL_HISTORY_ORACLE_PASS' if not mismatches else 'SCOPED_FULL_HISTORY_ORACLE_FAIL',
        full_56_consumer_acceptance='OPEN',full_semantic_acceptance='OPEN',production_changed=False)
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(acceptance=result['acceptance'],counts=dict(counts),mismatches=len(mismatches))))
finally:
    for stream in streams:stream.close()
