"""Continue only retained failed chart pages; reuse every completed PASS check."""
import json,os,hashlib
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from scripts.r4_r3_consumer_trace import ConsumerTrace

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    original=OUT/'SEALED_BFF_R6_FIELD_CONTINUATION/RESULT.json';previous=json.loads(original.read_bytes())
    folder=OUT/'SEALED_BFF_R6_FAILED_CHART_CONTINUATION_R1';folder.mkdir(exist_ok=False)
    source_root=Path(__file__).resolve().parents[1]
    source_trace=json.loads(original.with_name('EXACT56_TRACE.json').read_bytes())
    if any(not row['source_unchanged_during_run'] or hashlib.sha256((source_root/row['path']).read_bytes()).hexdigest()!=row['source_sha256'] for row in source_trace['rows']):raise ValueError('REUSE_SOURCE_CHANGED')
    candidate=json.loads(checked(ROOT,previous['candidate']).read_bytes())
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate);bff=CoreProductBFFR1(api,NoLegacyFacts());records=[];errors=[]
    trace=ConsumerTrace(folder/'EXACT56_TRACE.json','Only three failed corrected chart pagination checks; all other PASS checks retained')
    trace.start()
    try:
        for item in previous['errors']:
            if item['scope']!='CORRECTED_DATED_CHART' or item['code']!=200 or item['match']:raise ValueError('EXACT_PAGINATION_FAILURE_SCOPE_REQUIRED')
            difference=item['difference'];code,data=bff.chart(item['T0'],difference['security_id'],dict(period='D',price_basis='QFQ',limit='200',offset='400'))
            match=[bar for bar in data.get('items',[]) if bar['trade_date']==difference['day']]
            passed=code==200 and len(match)==1 and [match[0][name] for name in ('open','high','low','close')]==difference['current']
            record=dict(T0=item['T0'],security_id=difference['security_id'],bar_date=difference['day'],actual=match,expected=difference['current'],passed=passed)
            records.append(record)
            if not passed:errors.append(record)
    finally:trace.close()
    result=dict(contract_id='V4_BFF_FAILED_PAGINATION_CONTINUATION_R1',acceptance='PASS_BFF_SCOPED' if not errors else 'FAIL',
        source_result=ref(OUT,original),candidate=previous['candidate'],reused_pass_checks=previous['checks']-len(previous['errors']),
        continued_checks=len(records),records=records,errors=errors,publication=False,
        cause='Affected early February bar lay in the third 200-row page; first two pages did not cover it. No source or product fix required.',
        scope='Retained six BFF entries, 31,272 native source-to-PG scalars and 67 corrected chart checks; execute only three failed pagination checks')
    atomic_json(folder,folder/'RESULT.json',result);print(json.dumps(dict(acceptance=result['acceptance'],reused_pass_checks=result['reused_pass_checks'],continued_checks=len(records),errors=len(errors))),flush=True)

if __name__=='__main__':main()
