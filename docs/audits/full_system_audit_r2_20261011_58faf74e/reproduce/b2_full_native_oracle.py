"""Independent B2 numeric audit. No project algorithm imports; immutable key is input."""
import os,sys,json,gzip,hashlib,struct,zipfile,ast,bisect,math,time,collections
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP,localcontext
from fractions import Fraction
os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',PYTHONDONTWRITEBYTECODE='1')
ROOT=Path('G:/codex work/大A交易');BASE=Path('G:/codex_tmp/full_system_audit_r2_58faf74e');sys.path.insert(0,str(BASE/'deps'))
import numpy as np
started=time.time();inputs=[];counts={};errors=[];samples=[];unknown=collections.Counter()
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(ref):
 p=ROOT/ref['path'];got=digest(p);assert got==ref['sha256'],('INPUT_HASH',str(p));inputs.append(dict(ref,verified_sha256=got));return p
def atomic(name,value):
 p=BASE/name;t=p.with_suffix('.tmp');t.write_bytes(json.dumps(value,ensure_ascii=False,indent=2).encode('utf8'));os.replace(t,p)
def check(g,sid,f,e,a,tol=1e-10):
 ok=(e is None and a is None) or (isinstance(e,(int,float)) and isinstance(a,(int,float)) and math.isfinite(float(a)) and math.isclose(float(e),float(a),rel_tol=tol,abs_tol=tol)) or (isinstance(e,(bool,str)) and e==a)
 counts.setdefault(g,dict(pass_count=0,fail_count=0));counts[g]['pass_count' if ok else 'fail_count']+=1
 if not ok and len(errors)<200:errors.append(dict(group=g,entity=sid,field=f,expected=e,actual=a))
 if len(samples)<40:samples.append(dict(group=g,entity=sid,field=f,expected=e,actual=a,passed=ok))
def vector(g,sid,f,e,a):
 assert e.shape==a.shape,(sid,f,e.shape,a.shape)
 good=np.isclose(e,a,rtol=1e-10,atol=1e-10,equal_nan=False);p=int(good.sum());n=int(good.size-p);counts.setdefault(g,dict(pass_count=0,fail_count=0));counts[g]['pass_count']+=p;counts[g]['fail_count']+=n
 if n and len(errors)<200:errors.append(dict(group=g,entity=sid,field=f,failed_count=n,first_indices=np.flatnonzero(~good)[:10].tolist()))
head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes());receipt=json.loads(read(head['day_receipt']).read_bytes());replay=json.loads(read(receipt['numeric_core_oracle']).read_bytes());owners=replay['owners'];source=owners[-1]['sources'];package=read(source['package']);gbbq=read(source['gbbq']);classified=ROOT/'config/v4_02_gbbq_price_impact_classification_v1.json';dispositions=json.loads(classified.read_bytes())['dispositions'];inputs.append(dict(path=str(classified.relative_to(ROOT)),sha256=digest(classified),bytes=classified.stat().st_size))
keyfile=ROOT/'src/tdx/_gbbq_key.py';tree=ast.parse(keyfile.read_text('utf-8-sig'));hexkey=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GBBQ_KEY_HEX' for t in n.targets));keys=np.frombuffer(bytes.fromhex(hexkey),dtype='<u4');assert len(keys)>=1042;P=keys[:18];S=keys[18:1042].reshape(4,256);inputs.append(dict(path=str(keyfile.relative_to(ROOT)),sha256=digest(keyfile),bytes=keyfile.stat().st_size))
blob=gbbq.read_bytes();declared=struct.unpack_from('<I',blob)[0];assert len(blob)==4+29*declared
records=np.frombuffer(blob[4:],dtype=np.uint8).reshape(declared,29).copy();blocks=records[:,:24].copy().reshape(-1,8);words=blocks.view('<u4').reshape(-1,2);left=words[:,0].copy();right=words[:,1].copy()
# Standard inverse Feistel formulation; unlike the project's current/previous scalar recurrence.
for round_index in range(17,1,-1):
 left ^= P[round_index];a=(left>>24)&255;b=(left>>16)&255;c=(left>>8)&255;d=left&255
 f=((S[0,a]+S[1,b])^S[2,c])+S[3,d];right ^= f;left,right=right,left
left,right=right,left;right ^= P[1];left ^= P[0];clear=np.column_stack([left,right]).astype('<u4').view(np.uint8).reshape(declared,24);records[:,:24]=clear
atomic('gbbq_independent_decode.json',dict(contract='INDEPENDENT_VECTOR_FEISTEL_GBBQ_R2',record_count=declared,raw_sha256=digest(gbbq),key_schedule_sha256=digest(keyfile),clear_records_sha256=hashlib.sha256(records.tobytes()).hexdigest(),block_count=declared*3,algorithm='16-round inverse Feistel with independent vector state formulation',key_is_shared_immutable_input=True,not_vendor_truth_certificate=True))
events=collections.defaultdict(list);categories=collections.Counter();markets=collections.Counter()
for i,row in enumerate(records):
 raw=row.tobytes();m=raw[0];code=raw[1:8].rstrip(b'\0').decode('ascii');date=struct.unpack_from('<I',raw,8)[0];cat=raw[12];params=struct.unpack_from('<ffff',raw,13);key={0:'sz',1:'sh',2:'bj'}.get(m,'unknown')+code
 events[key].append((date,i,cat,params));categories[cat]+=1;markets[m]+=1
for key in events:events[key].sort(key=lambda e:(e[0],e[1]))
cores={};expected_returns={};calendar=None
for owner in owners:
 with gzip.open(read(owner['core']),'rt',encoding='utf8') as f:cores[owner['trade_date']]={r['security_id']:r for r in map(json.loads,f)}
 expected_returns[owner['trade_date']]={n:{} for n in (1,3,5,20)}
latest=owners[-1]['trade_date'];sid_keys={sid:r['source_security_key'].lower().replace('.','') for sid,r in cores[latest].items()};hist=read(owners[-1]['history'])
def price(value,bar_date,target,evs):
 v=Fraction(int(value),100)
 for ex,idx,cat,params in evs:
  if cat!=1 or not bar_date<ex<=target:continue
  cash,rp,bonus,rights=[Fraction(Decimal(str(x)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) for x in params]
  v=(v*10-cash+rp*rights)/(10+bonus+rights)
 cents=v*100
 rounded=(2*cents.numerator+cents.denominator)//(2*cents.denominator) if cents>=0 else -((2*(-cents.numerator)+cents.denominator)//(2*cents.denominator))
 return rounded/100
with zipfile.ZipFile(package) as z:
 names={Path(n).name.lower():n for n in z.namelist()};assert 'sh000001.day' in names
 ib=z.read(names['sh000001.day']);calendar=sorted(set(r[0] for r in struct.iter_unpack('<IIIIIfII',ib) if r[0]<=int(latest.replace('-',''))));calendar_sha=hashlib.sha256(json.dumps(calendar).encode()).hexdigest()
 bad=z.testzip();assert bad is None,('ZIP_CRC',bad);print('GBBQ_DECODE_AND_FULL_ZIP_CRC_PASS',declared,len(names),flush=True)
 # One stream through all current native security histories. No adjusted-history coefficients consumed.
 with gzip.open(hist,'rt',encoding='utf8') as f:
  for ordinal,line in enumerate(f,1):
   history=json.loads(line);sid=history['security_id'];key=sid_keys[sid];nativebytes=z.read(names[key+'.day']);native=list(struct.iter_unpack('<IIIIIfII',nativebytes));bydate={r[0]:r for r in native};evs=events[key];bars=history['bars'];dates=[int(b['trade_date'].replace('-','')) for b in bars]
   actual=np.array([b['raw_ohlc']+[b['amount'],b['volume']] for b in bars],dtype=float);raw=np.array([[*(v/100 for v in bydate[d][1:5]),bydate[d][5],bydate[d][6]] for d in dates],dtype=float);vector('ALL_CURRENT_NATIVE_RAW',sid,'OHLC_AMOUNT_VOLUME',raw,actual)
   target=int(latest.replace('-',''));adjusted=[];recorded=[]
   blocked_events=[e for e in evs if e[0]<=target and dispositions.get(str(e[2]),{}).get('formal_disposition','UNKNOWN_PRICE_IMPACT') in ('UNKNOWN_PRICE_IMPACT','PRICE_AFFECTING_UNSUPPORTED')]
   for d,b in zip(dates,bars):
    barriers=any(d<e[0] for e in blocked_events)
    check('ALL_CURRENT_ADJUSTMENT_AVAILABILITY',sid,str(d),b['qfq_ohlc'] is None,barriers)
    if not barriers:
     adjusted.append([price(v,d,target,evs) for v in bydate[d][1:5]]);recorded.append(b['qfq_ohlc'])
   if adjusted:
    ea=np.array(adjusted);aa=np.array(recorded);before=len(errors);vector('ALL_CURRENT_INDEPENDENT_QFQ',sid,'OHLC_EXACT_RATIONAL_EVENT_RECURRENCE',ea,aa)
    if len(errors)>before:
     good_dates=[b['trade_date'] for d,b in zip(dates,bars) if not any(d<e[0] for e in blocked_events)]
     errors[-1]['differences']=[dict(trade_date=good_dates[i],column=['open','high','low','close'][j],exact_rational=ea[i,j],recorded=aa[i,j],source_key=key) for i,j in zip(*np.where(~np.isclose(ea,aa,rtol=1e-10,atol=1e-10)))][:30]
   for day,cs in cores.items():
    if sid not in cs:continue
    row=cs[sid];t=int(day.replace('-',''));endidx=bisect.bisect_left(calendar,t);assert calendar[endidx]==t
    for n in (1,3,5,20):
     field=row['fields']['ret'+str(n)]
     if field['quality_state']!='OBSERVED':unknown[(day,'ret'+str(n),field.get('unknown_reason'))]+=1;continue
     startday=calendar[endidx-n];check('ALL_FIVE_SESSION_WINDOW',day+':'+sid,'ret'+str(n),str(startday),field['window_start_trade_date'].replace('-',''))
     if t not in bydate or startday not in bydate:
      check('ALL_FIVE_NATIVE_RETURN',day+':'+sid,'ret'+str(n),float('nan'),field['value']);continue
     numerator=price(bydate[t][4],t,t,evs);denominator=price(bydate[startday][4],startday,t,evs);value=numerator/denominator-1
     expected_returns[day][n][sid]=value;check('ALL_FIVE_NATIVE_RETURN',day+':'+sid,'ret'+str(n),value,field['value'])
   if ordinal%500==0:print('FULL_POPULATION_PROGRESS',ordinal,'failed',sum(c['fail_count'] for c in counts.values()),flush=True)
for day,cs in cores.items():
 for n in (5,20):
  returns=expected_returns[day][n];ordered=sorted(returns.values());N=len(ordered)
  for sid,row in cs.items():
   value=returns.get(sid);rank=None if value is None or N<2 else 100*(bisect.bisect_left(ordered,value)+.5*(bisect.bisect_right(ordered,value)-bisect.bisect_left(ordered,value)-1))/(N-1)
   check('ALL_FIVE_RPS_FROM_NATIVE',day+':'+sid,'rps'+str(n),rank,row['fields']['rps'+str(n)]['value'])
out=dict(contract='FULL_NATIVE_PRICE_ADJUSTMENT_RETURN_RPS_B2_R2',audited_head='58faf74e0a108bff74dcafd4e2bbca854fc67cd3',inputs=inputs,counts=counts,errors=errors,samples=samples,unknown_return_reasons=[dict(day=k[0],field=k[1],reason=k[2],count=v) for k,v in unknown.items()],stock_count=len(cores[latest]),sessions=list(cores),gbbq_record_count=declared,gbbq_category_counts=dict(categories),gbbq_market_counts=dict(markets),all_zip_members_crc_pass=True,native_calendar_sha256=calendar_sha,elapsed_seconds=time.time()-started,limitations=['GBBQ immutable key schedule shared input; independent vector inverse Feistel, no audited decoder import.','Raw source snapshot is later reconstructed and NOT historical first available/PIT.','Return population eligibility is frozen OBSERVED field quality; independent eligibility/identity/PIT not proved by rank parity.','Current full QFQ exact rational recurrence independently decoded events; upstream economic event truth not independently sourced.','Five-session independent returns use native index actual session dates, not all five full historical field formulas.'])
atomic('b2_full_native_oracle.json',out);print(json.dumps(dict(counts=counts,errors=errors[:5],elapsed_seconds=out['elapsed_seconds']),ensure_ascii=False),flush=True);sys.exit(1 if any(c['fail_count'] for c in counts.values()) else 0)
