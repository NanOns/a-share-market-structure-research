import sys,json,hashlib,gzip,struct,zipfile
from pathlib import Path
from decimal import Decimal,localcontext
from fractions import Fraction
B=Path('G:/codex_tmp/full_system_audit_r2_58faf74e');R=Path('G:/codex work/大A交易');sys.path.insert(0,str(R/'src'))
s=(B/'b2_full_native_oracle.py').read_text(encoding='utf8');ns={};exec(s[:s.index('cores={};')],ns)
from tdx.gbbq_reader import decrypt_block,decode_record
from adjustment.tdx_adjustment import build_affine_factors,xrxd_from_gbbq
blob=ns['blob'];records=ns['records'];h=hashlib.sha256()
for i in range(ns['declared']):
 raw=blob[4+29*i:4+29*(i+1)];clear=b''.join(decrypt_block(raw[j:j+8]) for j in (0,8,16))+raw[24:];h.update(clear)
assert h.hexdigest()==hashlib.sha256(records.tobytes()).hexdigest()
results=[];out=json.loads((B/'b2_full_native_oracle.json').read_bytes());diffs=[(e['entity'],d) for e in out['errors'] for d in e.get('differences',[])];wanted={sid for sid,d in diffs}
head=json.loads((R/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes());receipt=json.loads((R/head['day_receipt']['path']).read_bytes());replay=json.loads((R/receipt['numeric_core_oracle']['path']).read_bytes());owner=replay['owners'][-1];hist={}
with gzip.open(R/owner['history']['path'],'rt',encoding='utf8') as f:
 for line in f:
  row=json.loads(line)
  if row['security_id'] in wanted:hist[row['security_id']]={b['trade_date']:b for b in row['bars']}
for sid,d in diffs:
 date=int(d['trade_date'].replace('-',''));col=['open','high','low','close'].index(d['column']);bar=hist[sid][d['trade_date']];v=Fraction(Decimal(str(bar['raw_ohlc'][col])));eventrows=[];events=[]
 for ex,idx,cat,params in ns['events'][d['source_key']]:
  if not date<ex<=20261009 or cat!=1:continue
  rec=decode_record(blob[4+29*idx:4+29*(idx+1)],source='SHA_BOUND_NATIVE_GBBQ',record_index=idx);evt=xrxd_from_gbbq(rec);events.append(evt);cash,rp,bonus,rights=map(Fraction,[evt.cash_dividend_per_10,evt.rights_price,evt.bonus_transfer_per_10,evt.rights_ratio_per_10]);v=(v*10-cash+rp*rights)/(10+bonus+rights);eventrows.append(evt.as_dict())
 factor=build_affine_factors([date,20261009],events)[date]
 results.append(dict(sid=sid,**d,raw_price=bar['raw_ohlc'][col],rational_unrounded=str(v),exact_mid_cent=(v*100).denominator==2,production_replay=float(factor.qfq_price(Decimal(str(bar['raw_ohlc'][col])))),coefficient_mul=str(factor.qfq_mul),coefficient_add=str(factor.qfq_add),affine_unrounded_ambient28=str(factor.qfq_mul*Decimal(str(bar['raw_ohlc'][col]))+factor.qfq_add),events=eventrows))
(B/'b2_rounding_counterexamples.json').write_text(json.dumps(dict(contract='INDEPENDENT_EXACT_HALF_UP_COUNTEREXAMPLE_R2',decoder_full_digest_parity=True,clear_sha256=h.hexdigest(),count=len(results),rows=results,all_production_replay_matches_recorded=all(r['production_replay']==r['recorded'] for r in results),all_exact_mid_cent=all(r['exact_mid_cent'] for r in results),not_vendor_economic_truth=True),ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(results[:2],ensure_ascii=False));print('count',len(results),'all exact tie',all(r['exact_mid_cent'] for r in results))
