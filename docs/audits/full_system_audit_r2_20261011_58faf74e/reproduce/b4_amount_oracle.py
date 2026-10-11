import os,sys,json,gzip,zipfile,struct,hashlib,csv,io,collections,math,statistics
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
R=Path('G:/codex work/大A交易');B=Path('G:/codex_tmp/full_system_audit_r2_58faf74e');sys.path[:0]=[str(R/'src'),str(R)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(name,x):
 p=B/name;t=p.with_suffix('.tmp');t.write_bytes(json.dumps(x,ensure_ascii=False,indent=2).encode('utf8'));os.replace(t,p)
def loadref(ref):
 p=R/ref['path'];assert sha(p)==ref['sha256'];return p
head=json.loads((R/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes());receipt=json.loads(loadref(head['day_receipt']).read_bytes());replay=json.loads(loadref(receipt['numeric_core_oracle']).read_bytes());owner=replay['owners'][-1];package=loadref(owner['sources']['package']);core={}
with gzip.open(loadref(owner['core']),'rt',encoding='utf8') as f:core={r['security_id']:r for r in map(json.loads,f)}
provider=R/'reports/v4_baostock/runtime_acceptance/20261009/20261009T183516074200_raw_responses.json';bao=json.loads(provider.read_bytes());rows=[];counts=collections.Counter();ratio_checks=[];unknown=collections.Counter()
def f32(x):return struct.unpack('<f',struct.pack('<f',float(x)))[0]
with zipfile.ZipFile(package) as z:
 names={Path(n).name.lower():n for n in z.namelist()}
 assert len(bao['daily_rows'])==len({(r['code'],r['date']) for r in bao['daily_rows']})
 for row in bao['daily_rows']:
  assert row['date']=='2026-10-09' and row['adjustflag']=='3';key=row['code'].replace('.','');data=z.read(names[key+'.day']);native=next((v for v in struct.iter_unpack('<IIIIIfII',data) if v[0]==20261009),None)
  if native is None:
   rows.append(dict(key=key,trade_date=row['date'],status='NATIVE_ROW_ABSENT_PROVIDER_SUSPENDED' if row['tradestatus']=='0' else 'NATIVE_ROW_ABSENT_STATUS_UNEXPLAINED',bao_amount=row['amount'],tdx_amount=None,delta=None,volume_equal=None,amount_f32_equal=None));counts['NATIVE_ROW_ABSENT_PROVIDER_SUSPENDED' if row['tradestatus']=='0' else 'NATIVE_ROW_ABSENT_STATUS_UNEXPLAINED']+=1;continue
  exact=Decimal(row['amount']);actual=native[5];delta=Decimal(str(actual))-exact;direct=f32(exact)==actual;rounded=f32(exact.quantize(Decimal('1'),rounding=ROUND_HALF_UP))==actual;veq=Decimal(row['volume'])==native[6]
  category='DECIMAL_EXACT' if delta==0 else 'DIRECT_BINARY32' if direct else 'INTEGER_HALF_UP_BINARY32' if rounded else 'UNEXPLAINED_AMOUNT_DIFFERENCE'
  counts[category]+=1;counts['VOLUME_EXACT' if veq else 'VOLUME_DIFFERENCE']+=1
  rows.append(dict(key=key,trade_date=row['date'],status=category,bao_amount=row['amount'],tdx_amount=actual,delta=str(delta),volume_equal=veq,amount_f32_equal=direct))
with gzip.open(loadref(owner['history']),'rt',encoding='utf8') as f:
 for line in f:
  h=json.loads(line);sid=h['security_id'];cell=core[sid]['fields']['amount_ratio20'];bars=h['bars']
  if cell['quality_state']!='OBSERVED':unknown[cell.get('unknown_reason')]+=1;continue
  selected=[b for b in bars if b['trade_date']<='2026-10-09'][-21:];assert len(selected)==21 and selected[-1]['trade_date']=='2026-10-09'
  value=selected[-1]['amount']/statistics.fmean(b['amount'] for b in selected[:-1]);match=math.isclose(value,cell['value'],rel_tol=1e-10,abs_tol=1e-10)
  ratio_checks.append(dict(security_id=sid,window_start=selected[0]['trade_date'],window_end=selected[-1]['trade_date'],actual_count=21,expected=value,recorded=cell['value'],passed=match))
s=io.StringIO(newline='');writer=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows);p=B/'b4_cross_source_amount_differences.csv';t=p.with_suffix('.tmp');t.write_bytes(s.getvalue().encode());os.replace(t,p)
atomic('b4_amount_oracle.json',dict(contract='AUD_AMOUNT_A_06_INDEPENDENT_CROSS_SOURCE_UNIT_WINDOW_AUDIT_R2',issue='FA-012',status='PARTIAL_FORMAL_H21_OPEN',native_source=dict(path=owner['sources']['package']['path'],sha256=sha(package)),provider_source=dict(path=provider.relative_to(R).as_posix(),sha256=sha(provider),observed_at=bao['observed_at'],target_date=bao['target_date']),provider_rows=len(rows),cross_source_counts=dict(counts),ratio_population=len(core),ratio_observed_count=len(ratio_checks),ratio_failure_count=sum(not r['passed'] for r in ratio_checks),ratio_unknown_reasons=dict(unknown),ratio_rows=ratio_checks,semantics=dict(native_amount='RAW_FLOAT32_CNY_YUAN',provider_amount='RAW_ADJUSTFLAG_3_CNY_DECIMAL',native_volume='RAW_SHARES_UINT32',provider_volume='RAW_SHARES_DECIMAL',amount_adjustment='UNCHANGED_BY_PRICE_QFQ',stock_ratio='CURRENT / prior20 actual bars mean, dimensionless',sector_amount_a='H21 common accepted PIT members raw sumT / prior20 sum mean',formal_permission=False),limitations=['T0 cross-source representation agreement does not establish independent supplier economic truth.','Observed stock ratio eligibility remains frozen; all unknown states counted but not independently certified.','Full raw amount histories are independently verified in B2; provider cross-source only 2026-10-09.','Same H21 accepted PIT member ledger remains required and cannot be backfilled by this raw source agreement.']))
print(json.dumps(dict(cross_source_counts=dict(counts),ratio_count=len(ratio_checks),ratio_failures=sum(not r['passed'] for r in ratio_checks))))
