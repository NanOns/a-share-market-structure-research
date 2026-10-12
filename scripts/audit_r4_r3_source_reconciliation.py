"""Independent full-row provider reconciliation; preserve every disagreement."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];workspace=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
OUT=ROOT/'docs/audits/r4_r3_consumers_20261011/SOURCE_DERIVATION_R1'
freeze_path=next((workspace/'data/v4/dynamic_daily_sources/daily_freezes/2026-10-09').glob('*.json'))
freeze=json.loads(freeze_path.read_bytes());binding=freeze['tdx'];path=Path(binding['path'])
if not path.is_absolute():path=workspace/path
raw=path.read_bytes()
if hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('SOURCE_BYTES_CHANGED')
native=json.loads(raw)['target_bars'];daily=freeze['normalized']['daily']['rows']
bycode={r['source_security_key'].upper():r for r in native}
active={r['code'].upper() for r in daily if r.get('tradestatus')=='1'}
mismatches=[];compared=0;reasons=Counter()
for row in daily:
    code=row['code'].upper();bar=bycode.get(code)
    if row.get('tradestatus')=='1' and bar:
        for field in ('open','high','low','close','volume'):
            compared+=1
            left=Decimal(str(row[field]));right=Decimal(str(bar[field]))
            if left!=right:
                reasons[field]+=1;mismatches.append(dict(code=code,field=field,baostock=str(left),tdx=str(right),delta=str(left-right),baostock_row=row,tdx_row=bar))
    elif row.get('tradestatus')=='1':reasons['ACTIVE_MISSING_TDX']+=1
    elif bar:reasons['SUSPENDED_WITH_TDX_BAR']+=1
result=dict(contract_id='R4_R3_FULL_NATIVE_SOURCE_RECONCILIATION_ORACLE',daily_rows=len(daily),native_rows=len(native),unique_daily_codes=len({r['code'] for r in daily}),unique_native_codes=len(bycode),compared_values=compared,mismatch_categories=dict(reasons),active_without_tdx=sorted(active-set(bycode)),tdx_without_active_daily=sorted(set(bycode)-active),all_numeric_mismatches=mismatches,freeze_sha256=hashlib.sha256(freeze_path.read_bytes()).hexdigest(),tdx_source_sha256=binding['sha256'],status='FULL_ROW_RECONCILIATION_PASS' if not reasons and active==set(bycode) else 'SOURCE_DISAGREEMENT_OPEN',production_changed=False,no_source_values_overwritten=True)
with (OUT/'INDEPENDENT_FULL_RECONCILIATION_R1.json').open('x',encoding='utf8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({k:result[k] for k in ('daily_rows','native_rows','compared_values','mismatch_categories','status')}))
