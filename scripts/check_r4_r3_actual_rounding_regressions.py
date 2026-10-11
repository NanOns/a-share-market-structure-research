"""Reproduce every retained full-history mismatch from hash-bound native inputs."""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
from fractions import Fraction
import hashlib,json,struct,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tdx.gbbq_reader import read_gbbq
from workbench_analysis.exact_operational_core_candidate_r3 import transform_window
workspace=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
evidence=ROOT/'docs/audits/r4_r3_consumers_20261011/SOURCE_DERIVATION_R12/FULL_HISTORY_INDEPENDENT_R1.json'
output=ROOT/'docs/audits/r4_r3_consumers_20261011/ACTUAL_80_ROUNDING_REGRESSIONS_R1.json'
if output.exists():raise ValueError('IMMUTABLE_REGRESSION_EVIDENCE_EXISTS')
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()
def bound(binding):
    path=(workspace/binding['path']).resolve()
    if not path.is_relative_to(workspace) or sha(path)!=binding['sha256']:raise ValueError('REGRESSION_SOURCE_HASH_MISMATCH')
    return path
old=json.loads(evidence.read_bytes())
generation='a82823f8782b9758713a710fd52f8ffc8d3668b6344a2e27b48f8f660abacf02'
owners=json.loads((workspace/'data/v4/dynamic_daily_owners/2026-10-09'/generation/'owner_v3/CORE_REPLAY.json').read_bytes())['owners']
sources=owners[0]['sources']
identity={row['security_id']:row['source_security_key'].lower() for row in json.loads(bound(sources['identity']).read_bytes())['rows']}
actions=defaultdict(list)
for event in read_gbbq(bound(sources['gbbq'])):actions[event.security_id.lower()].append(event)
classification=workspace/'config/v4_02_gbbq_price_impact_classification_v1.json'
policy=json.loads(classification.read_bytes())['dispositions']
rows=[];cache={}
with zipfile.ZipFile(bound(sources['package'])) as archive:
    names={}
    for name in archive.namelist():
        parts=name.lower().replace('\\','/').split('/');leaf=parts[-1]
        market=next((p for p in parts if p in ('sh','sz','bj')),None)
        if market and leaf.endswith('.day'):names[market+'.'+leaf[-10:-4]]=name
    for failure in old['mismatches']:
        code=identity[failure['sid']];target=failure['target'];day=failure['day']
        if code not in cache:cache[code]=list(struct.iter_unpack('<IIIIIfII',archive.read(names[code])))
        raw=[bar for bar in cache[code] if bar[0]<=target][-420:]
        transformed=transform_window(raw,actions[code],policy,str(target)[:4]+'-'+str(target)[4:6]+'-'+str(target)[6:])
        actual=next(bar for bar in transformed if int(bar['trade_date'].replace('-',''))==day)
        original=next(bar for bar in raw if bar[0]==day)
        expected=[]
        for value in original[1:5]:
            price=Fraction(value,100)
            for event in sorted(actions[code],key=lambda e:(e.event_date,e.source_record_index)):
                if event.category!=1 or not day<event.event_date<=target:continue
                cash,rp,bonus,rights=[Fraction(Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) for x in (event.c1,event.c2,event.c3,event.c4)]
                price=(10*price-cash+rights*rp)/(10+bonus+rights)
            cents,remainder=divmod(abs(price.numerator)*100,price.denominator)
            cents+=int(2*remainder>=price.denominator)
            expected.append(float(Decimal(cents)/100*(-1 if price<0 else 1)))
        rows.append(dict(retained_failure=failure,raw_ohlc_cents=list(original[1:5]),candidate=actual['qfq_ohlc'],independent=expected,
            pass_all_four=actual['qfq_ohlc']==expected,retained_expected_present=failure['expected'] in expected))
result=dict(contract='R4_R3_ACTUAL_80_ROUNDING_REGRESSIONS_R1',retained_oracle_sha256=sha(evidence),sources=sources,
    classification_sha256=sha(classification),candidate_source_sha256=sha(ROOT/'src/workbench_analysis/exact_operational_core_candidate_r3.py'),
    denominator=len(old['mismatches']),rows=rows,status='SCOPED_PASS' if all(r['pass_all_four'] and r['retained_expected_present'] for r in rows) else 'FAIL',
    full_history_candidate_acceptance='PENDING_SEPARATE_FULL_WINDOW_RUN',all_56_consumer_acceptance='OPEN',production_changed=False)
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(status=result['status'],denominator=result['denominator'])),flush=True)
