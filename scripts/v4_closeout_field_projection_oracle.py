"""New full field projection scope, conserving independent immutable Owners.

Does not rerun accepted arithmetic or the already passed native six-field check.
"""
import json,os
from pathlib import Path
from collections import Counter
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from workbench_analysis.r43_owner_replay import checked
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
from scripts.r4_r3_consumer_trace import ConsumerTrace

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')
OMIT={'source_refs','source_identity','producer_identity','source_publications','input_digests','contract_refs','runtime_source_bindings'}

def display(value):
    if isinstance(value,dict):return {k:display(v) for k,v in value.items() if k not in OMIT}
    if isinstance(value,list):return [display(v) for v in value]
    return value

def main():
    folder=OUT/'FIELD_PROJECTION_ORACLE_R6_R1';folder.mkdir(exist_ok=False)
    preparation=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R1.json').read_bytes());candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes());day=candidate['accepted_trade_date']
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    bff=CoreProductBFFR1(OperationalSuccessorReaderV1(ROOT,candidate),NoLegacyFacts())
    sources={domain:rows(ROOT,candidate['owners'][day][domain]) for domain in ('core','profile','focus','sector','rotation','relative_sector')}
    keyed={d:{r.get('security_id',r.get('entity_id',r.get('sector_id'))):r for r in data} for d,data in sources.items()}
    registry={r['field_id']:r for name in ('v4_03_field_registry_v1.json','v4_04_field_registry_v2.json','v4_08_sector_field_registry_r5.json') for r in json.loads((ROOT/'config'/name).read_bytes())['fields']}
    checks=Counter();errors=[];error_count=0
    def check(condition,scope,**evidence):
        nonlocal error_count
        checks[scope]+=1
        if not condition:
            error_count+=1
            if len(errors)<100:errors.append(dict(scope=scope,**evidence))
    trace=ConsumerTrace(folder/'EXACT56_TRACE.json','Previously uncovered complete field projection, actual formal SELECT-only PG')
    trace.start()
    try:
        for domain in ('stocks','sectors'):
            projected=bff.project(domain,day)
            for row in projected:
                sid=row['entity_id'];expected={};binding={}
                if domain=='stocks':
                    p=keyed['profile'][sid];f=keyed['focus'].get(sid,{})
                    for group in ('fields','derived_fields','states'):
                        for k,v in p.get(group,{}).items():expected[k]=v;binding[k]=candidate['owners'][day]['profile']
                    for k in ('scenario','final_eligibility','maturity','health','validity','tracking'):
                        expected[k]=f.get(k,'UNKNOWN');binding[k]=candidate['owners'][day]['focus']
                    for k,v in keyed['core'][sid].get('fields',{}).items():
                        if k not in expected:expected[k]=v;binding[k]=candidate['owners'][day]['core']
                    for k in ('effective_event','transition_reasons','unknown_predicates','detector_statuses','prewatch_status'):
                        if k in f:expected[k]=f[k];binding[k]=candidate['owners'][day]['focus']
                    expected['relative_sector_state']=keyed['relative_sector'][sid];binding['relative_sector_state']=candidate['owners'][day]['relative_sector']
                    for k in ('open','high','low','close','amount','volume'):expected.pop(k,None)
                else:
                    expected.update(keyed['sector'][sid]['fields']);binding.update({k:candidate['owners'][day]['sector'] for k in expected})
                    for alias,k in (('sector_rs20','sector_rs20_pct'),('sector_rs5','sector_rs5_pct'),('seed_width','base_seed_width_adjusted')):
                        if k in expected:expected[alias]=expected[k];binding[alias]=candidate['owners'][day]['sector']
                for k,original in expected.items():
                    cell=row['fields'].get(k);details=dict(domain=domain,entity=sid,field=k)
                    check(cell is not None,'FIELD_PRESENT',**details)
                    if cell is None:continue
                    val=original.get('value') if isinstance(original,dict) and 'value' in original else original
                    check(cell.get('value')==display(val),'EXACT_OWNER_VALUE',expected=display(val),actual=cell.get('value'),**details)
                    check(cell.get('source_digest')==binding[k]['sha256'],'OWNER_SOURCE_DIGEST',**details)
                    alias={'sector_rs20':'sector_rs20_pct','sector_rs5':'sector_rs5_pct','seed_width':'base_seed_width_adjusted'}.get(k,k) if domain=='sectors' else k
                    unit=registry.get(alias,{}).get('unit')
                    if unit:check(cell.get('unit')==unit,'REGISTERED_UNIT',**details)
                    if isinstance(original,dict) and 'value' in original:
                        for key in ('window_start_trade_date','window_end_trade_date','actual_count','calendar_span','suspended_count','contract_id','parameter_set_id','input_digest','output_digest','evidence','n','k'):
                            if key in original:check(cell.get(key)==original[key],'WINDOW_AND_PARAMETER_SEMANTICS',key=key,**details)
                        quality=original.get('quality') or original.get('quality_state')
                        if quality:check(cell.get('quality')==quality,'EXPLICIT_OWNER_QUALITY',**details)
                        reason=original.get('reason') or original.get('reason_code') or original.get('unknown_reason')
                        if reason:check(cell.get('reason')==reason,'EXPLICIT_UNKNOWN_REASON',**details)
                    if val is None or val=='UNKNOWN':check(cell.get('quality')!='KNOWN' and bool(cell.get('reason')),'UNKNOWN_NOT_ZERO_OR_KNOWN',**details)
    finally:trace.close()
    result=dict(contract_id='V4_COMPLETE_CURRENT_FIELD_PROJECTION_ORACLE_R1',acceptance='PASS_SCOPED' if not error_count else 'FAIL',
        candidate=preparation['candidate'],T0=day,context_token=bff.api.token,checks=dict(checks),total_checks=sum(checks.values()),error_count=error_count,first_errors=errors,
        prior_native_six_field_checks_reexecuted=False,arithmetic_producers_reexecuted=False,publication=False,
        scope='All current stock Core/Profile/State/Focus and sector registered field values, unit, source, window, quality and UNKNOWN projection; independent arithmetic oracles reused separately')
    atomic_json(folder,folder/'RESULT.json',result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['total_checks'],errors=error_count)),flush=True)
    return int(bool(error_count))

if __name__=='__main__':raise SystemExit(main())
