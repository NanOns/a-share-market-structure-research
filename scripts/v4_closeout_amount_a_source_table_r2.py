"""Separate 136 provider differences and 12 missing native bars, no re-arithmetic."""
import csv,hashlib,json
from pathlib import Path
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT=Path('G:/codex work/v4-production-20261012')
WORK=Path('G:/codex_tmp/v4_full_closeout_20261012')
OUT=Path(__file__).resolve().parents[1]/'docs/audits/v4_full_closeout_20261012/continuation_20261013/AMOUNT_A_SOURCE_AUDIT_R2'

def main():
    if (OUT/'RESULT.json').exists():raise ValueError('PRESERVE_AMOUNT_SOURCE_TABLE')
    oracle=json.loads((WORK/'NATIVE_AMOUNT_ORACLE_R1.json').read_bytes())
    assert oracle['acceptance']=='PASS' and oracle['provider_parity']['acceptance']=='FAIL' and not oracle['errors']
    freeze=json.loads(checked(ROOT,oracle['freeze']).read_bytes())
    native_path=Path(freeze['tdx']['path'])
    if not native_path.is_absolute():native_path=ROOT/native_path
    assert native_path.resolve().drive.upper()=='G:'
    native_bytes=native_path.read_bytes()
    assert hashlib.sha256(native_bytes).hexdigest()==freeze['tdx']['sha256']
    native=json.loads(native_bytes)
    native_keys={row['source_security_key'].upper() for row in native['target_bars']}
    daily=freeze['normalized']['daily']['rows'];bao={row['code'].upper():row for row in daily}
    missing=sorted(set(bao)-native_keys)
    assert len(oracle['provider_parity']['differences'])==136 and len(missing)==12
    rows=[]
    for item in oracle['provider_parity']['differences']:
        rows.append(dict(security=item['security'],classification='DIFFERENT_FLOAT32_PROVIDER_REPRESENTATION',native_amount=item['native_amount'],native_float32_bytes=item['native_float32_bytes'],baostock_amount=item['baostock_amount'],trade_status=bao[item['security']]['tradestatus'],resolution='NATIVE_CNY_PRIMARY_UNCHANGED; CROSS_PROVIDER_EQUALITY_NOT_GRANTED; CAUSE_NOT_INFERRED',production_blocker=False))
    for code in missing:
        assert bao[code]['tradestatus']=='0'
        rows.append(dict(security=code,classification='SUSPENDED_NO_NATIVE_TARGET_BAR',native_amount='',native_float32_bytes='',baostock_amount=bao[code]['amount'],trade_status='0',resolution='NO_ACTUAL_NATIVE_QUOTE; NO_ZERO_SUBSTITUTION_FOR_CURRENT_PRICE; STATUS_BOUNDARY_RETAINED',production_blocker=False))
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'SOURCE_DIFFERENCES.csv').open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result=dict(audit_item_id='M10_AMOUNT_A_FA012',contract_id='V4_AMOUNT_A_FULL_PROVIDER_DIFFERENCE_CLASSIFICATION_R2',acceptance='PASS_NATIVE_SOURCE_CONTRACT_AND_COMPLETE_DIFFERENCE_CLASSIFICATION',scope='Source provenance, preserved exact native DAY byte oracle and suspended missing-bar boundary; no cross-provider parity or universal Amount A grant',target=oracle['target'],source_freeze=oracle['freeze'],tdx=freeze['tdx'],original_oracle=dict(path=str(WORK/'NATIVE_AMOUNT_ORACLE_R1.json'),sha256=hashlib.sha256((WORK/'NATIVE_AMOUNT_ORACLE_R1.json').read_bytes()).hexdigest()),counts=oracle['provider_parity']['counts'],rows=len(rows),table_sha256=hashlib.sha256((OUT/'SOURCE_DIFFERENCES.csv').read_bytes()).hexdigest(),native_primary_replaced=False,tolerance_used=False,original_provider_parity='FAIL_PRESERVED',arithmetic_reexecuted=False,production_blocker=False,remaining_watch='Provider-specific cause remains unasserted; consumers must retain declared native CNY provenance and separate source contract')
    atomic_json(OUT,OUT/'RESULT.json',result);print(json.dumps({'acceptance':result['acceptance'],'rows':len(rows),'counts':result['counts']}))

if __name__=='__main__':main()
