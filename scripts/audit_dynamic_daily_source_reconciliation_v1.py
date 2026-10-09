"""Independent dated-source evidence, not successor producer admission."""
from pathlib import Path
from collections import Counter
import json,sys,struct
from decimal import Decimal,ROUND_HALF_UP
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.r43_operational_sources import checked,date_valid_identity,ref
from workbench_analysis.baostock_runtime_acceptance import load_runtime_acceptance_manifest
from workbench_analysis.baostock_dm01_sdk_schema_v2 import normalize_response
from workbench_analysis.baostock_supplemental import package_metadata
from workbench_analysis.baostock_daily_update_source import DAILY_METHOD
from workbench_analysis.scoped_successor_r421 import atomic,canonical

OUT=ROOT/'docs/evidence/dynamic_daily_20261009'
if __name__=='__main__':
    head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    dated='2026-10-08'
    extraction=json.loads((OUT/'DD02_REAL_TDX_EXTRACTION.json').read_bytes())
    binding=extraction['extraction']['artifact'];p=Path(binding['path'])
    from workbench_analysis.scoped_successor_r421 import sha
    assert sha(p)==binding['sha256']
    native=json.loads(p.read_bytes())['target_bars']
    lifecycle=json.loads(checked(ROOT,head['owners'][dated]['lifecycle']).read_bytes())
    identity=json.loads(checked(ROOT,lifecycle['identity']).read_bytes())['rows']
    bycode={r.get('source_security_key',r.get('symbol','')).upper():r for r in identity if r.get('security_id')}
    manifest_path=ROOT/'reports/v4_baostock/runtime_acceptance/20261008/accepted_runtime_manifest.json'
    manifest=load_runtime_acceptance_manifest(manifest_path,project_root=ROOT)
    raw_path=ROOT/manifest['smoke_receipt']['path'];raw_path=raw_path.with_name(raw_path.name.replace('_live_smoke_receipt.json','_raw_responses.json'))
    raw=json.loads(raw_path.read_bytes())
    rows,meta=normalize_response(raw['daily_rows'],raw['daily_metadata'],target=dated,sdk=package_metadata(),
        contract=json.loads((ROOT/'config/baostock_dm01_sdk_schema_adapter_v2.json').read_bytes()),method=DAILY_METHOD)
    bars={r['source_security_key']:r for r in native}
    if len(bars)!=len(native):raise ValueError('NATIVE_DUPLICATE_SOURCE_SECURITY')
    counts=Counter();anomalies=[];amounts=[];observations=[]
    for row in rows:
        code=row['code'].upper();i=bycode.get(code);bar=bars.get(code)
        valid=date_valid_identity(i,dated)
        if not valid:counts['identity_unknown']+=1;anomalies.append(dict(code=code,reason='DATED_IDENTITY_UNKNOWN'))
        state='ACTUAL_BAR' if bar else 'CONFIRMED_SUSPENSION' if row['tradestatus']=='0' else 'DATA_GAP'
        counts[state]+=1
        observations.append(dict(source_security_key=code,security_id=i['security_id'] if valid else None,
            trade_date=dated,state=state,identity_status='DATE_VALID' if valid else 'UNKNOWN',isST=row['isST']))
        if not bar:
            if row['tradestatus']!='0':anomalies.append(dict(code=code,reason='MISSING_ACTUAL_BAR'))
            continue
        if row['tradestatus']=='0':anomalies.append(dict(code=code,reason='SUSPENDED_PROVIDER_HAS_TDX_BAR'))
        mismatch={field:dict(tdx=bar[field],bao=row[field]) for field in ['open','high','low','close','volume']
                  if float(row[field])!=float(bar[field])}
        if mismatch:anomalies.append(dict(code=code,reason='OHLCV_MISMATCH',fields=mismatch))
        left,right=float(bar['amount']),float(row['amount'])
        represented=struct.unpack('<f',struct.pack('<f',right))[0]
        if left!=right:
            counts['amount_decimal_differs_from_native_float32']+=1
            amounts.append(dict(code=code,tdx_float32=left,bao_decimal=row['amount'],
                same_when_bao_encoded_as_native_float32=represented==left,
                candidate_integer_yuan_then_float32_matches=struct.unpack('<f',struct.pack('<f',
                    float(Decimal(row['amount']).quantize(Decimal('1'),rounding=ROUND_HALF_UP))))[0]==left))
        if represented!=left:counts['amount_not_explained_by_float32']+=1
    bao_codes={r['code'].upper() for r in rows}
    outside=[dict(source_security_key=c,identity_known=c in bycode,
                  evidence='NOT_IN_TARGET_BAOSTOCK_DAILY_UNIVERSE; NOT_AUTOMATIC_DELISTING')
             for c in sorted(set(bars)-bao_codes)]
    result=dict(contract_id='DYNAMIC_DAILY_SOURCE_RECONCILIATION_AUDIT_V1',target_session=dated,
        evidence_kind='REAL_FROZEN_PROVIDER_RESPONSES_AND_NATIVE_BARS',counts=dict(counts),
        tdx_extracted_count=len(native),baostock_daily_count=len(rows),
        dated_identity_binding=lifecycle['identity'],tdx=ref(ROOT,p),baostock=ref(ROOT,raw_path),
        runtime_manifest=ref(ROOT,manifest_path),observations=observations,anomalies=anomalies,
        excluded_native_outside_target_universe=outside,
        status='BLOCKED_SOURCE_RECONCILIATION' if anomalies else 'SOURCE_IDENTITY_OHLCV_RECONCILED_SCOPED',
        amount_audit='DD_A05_INDEPENDENT_AMOUNT_REPRESENTATION_AUDIT',
        complete_source_admission=False,derived_ready=False,published=False,
        next_stage='DATED_GBBQ_REVISION_AND_FULL_NUMERIC_SUCCESSOR_WITH_PERIOD_OWNERS')
    atomic(OUT/'DD03_SOURCE_RECONCILIATION_AUDIT.json',canonical(result))
    atomic(OUT/'DD_A05_AMOUNT_REPRESENTATION_AUDIT.json',canonical(dict(
        contract_id='DD_A05_AMOUNT_REPRESENTATION_AUDIT_V1',scope='All 10/08 matched native and BaoStock daily rows',
        evidence=dict(tdx=ref(ROOT,p),baostock=ref(ROOT,raw_path)),differences=amounts,
        acceptance='INDEPENDENT_NOT_GRANTED',gate_effect='SEPARATE_AUDIT_NOT_GLOBAL_OWNER_PASS',
        rule='Exact native IEEE754 float32 representation checked separately; no arbitrary tolerance or canonical price substitution',
        candidate_encoding='ROUND_HALF_UP_TO_INTEGER_CNY_THEN_IEEE754_FLOAT32',
        candidate_encoding_is_inference=True,universal_source_contract_acceptance='NOT_GRANTED',
        candidate_encoding_mismatch_count=sum(not r['candidate_integer_yuan_then_float32_matches'] for r in amounts))))
    print(json.dumps(dict(status=result['status'],counts=dict(counts),anomaly_count=len(anomalies),outside_universe=len(outside))))
