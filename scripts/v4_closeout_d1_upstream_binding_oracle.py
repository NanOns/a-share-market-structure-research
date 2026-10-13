"""Independent D1 upstream values, dated source identities and namespaces."""
import json
from decimal import Decimal
from collections import Counter
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from scripts.v4_closeout_core_uncovered_numeric_oracle import jsonlines
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json

def main():
    target=OUT/'D1_UPSTREAM_BINDING_ORACLE_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_PRIOR_BINDING_ORACLE')
    prep=json.loads((OUT/'SEALED_METADATA_CONSERVATION_R6_R3.json').read_bytes());candidate=json.loads(checked(ROOT,prep['candidate']).read_bytes());day=candidate['accepted_trade_date']
    diagnostic=json.loads(checked(ROOT,candidate['owners'][day]['diagnostic']).read_bytes());manifest=json.loads(checked(ROOT,diagnostic['structure_manifest']).read_bytes());owner=manifest['owner_inputs']
    entry=json.loads(checked(ROOT,manifest['entry']).read_bytes());binding=next(x for x in entry['frozen_contracts'] if 'field_registry' in x['path']);registry=json.loads(checked(ROOT,binding).read_bytes())['fields']
    from workbench_analysis.market_source_acquisition import official_sessions
    calendar=official_sessions(ROOT);previous=max(x for x in calendar if x<day)
    tables={k:{x['security_id']:x for x in jsonlines(checked(ROOT,owner[k]))} for k in ('core','prior_core','adjusted','profiles')}
    mapping={'ATR20':'atr20','CLV':'clv','MA20':'ma20','MA60':'ma60','amount_ratio20':'amount_ratio20','delta3':'rps5_delta3','prior_high20':'prior_high20','rel_market_1':'rel_market_1','ret1':'ret1','slope20':'slope20'}
    history={x['security_id']:next((b for b in x['bars'] if b['trade_date']==previous),None) for x in jsonlines(checked(ROOT,owner['history']))}
    runtime=next(x for x in manifest['artifacts'] if 'runtime_security.jsonl.gz' in x['path']);counts=Counter();errors=[];total_errors=0
    def check(sid,name,key,actual,wanted):
        nonlocal total_errors
        counts[key]+=1
        if actual!=wanted:
            total_errors+=1
            if len(errors)<100:errors.append(dict(security_id=sid,field=name,key=key,actual=actual,expected=wanted))
    for row in jsonlines(checked(ROOT,runtime)):
        sid=row['identity']['security_id'];facts=row['common_facts']
        for spec in registry:
            name=spec['field']
            if spec['field_role']!='UPSTREAM_ACCEPTED':continue
            value=None;source='core'
            if name in mapping:
                cell=tables['core'][sid]['fields'].get(mapping[name],{});value=cell.get('value') if cell.get('quality_state')=='OBSERVED' else None
            elif name in ('O','H','L','C','price_basis','adjustment_source_revision'):
                source='adjusted';item=tables[source].get(sid,{});value=item.get({'O':'open','H':'high','L':'low','C':'close'}.get(name,name)) if item.get('adjustment_readiness')=='READY' else None
            elif name in ('atr_prior_view','ma20_t_minus_1','prior_delta3'):
                source='prior_core';cell=tables[source][sid]['fields'].get({'atr_prior_view':'atr20','ma20_t_minus_1':'ma20','prior_delta3':'rps5_delta3'}[name],{});value=cell.get('value') if name=='prior_delta3' or cell.get('quality_state')=='OBSERVED' else None
            elif name in ('close_t_minus_1','prior_high_view'):
                source='history';bar=history[sid];value=bar['qfq_ohlc'][3 if name=='close_t_minus_1' else 1] if bar and bar['qfq_ohlc'] else None
            elif name=='near_high20_state':
                source='profiles';cell=tables[source][sid]['states'][name];value=cell.get('value') if not cell.get('unknown_reason') else None
            if value is not None and spec['data_type'] in ('number','integer'):value=str(Decimal(str(value)))
            for key,wanted in dict(value=value,quality='KNOWN' if value is not None else 'UNKNOWN',source_namespace='R4_CORRECTED_OWNER_V1',source_digest=owner[source]['sha256'],source_publication_id=owner[source]['sha256'],trade_date=previous if spec['time_role']=='T_MINUS_1' else day,time_role=spec['time_role'],producer_contract_id=spec['producer_contract_id']).items():check(sid,name,key,facts[name].get(key),wanted)
    result=dict(contract_id='V4_D1_CURRENT_UPSTREAM_BINDING_INDEPENDENT_ORACLE_R1',acceptance='PASS_D1_UPSTREAM_BINDING_SCOPE' if not total_errors else 'FAIL',T0=day,candidate=prep['candidate'],runtime=runtime,registry=binding,sources={k:owner[k] for k in ('core','prior_core','history','adjusted','profiles')},checks=dict(counts),check_count=sum(counts.values()),error_count=total_errors,first_errors=errors,producer_binder_imported=False,previous_machine_pass_reexecuted=False,scope='All declared upstream fields: value, quality, producer, source digest, namespace and time role. Local input digests remain separate.')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],checks=result['check_count'],errors=total_errors)))
if __name__=='__main__':main()
