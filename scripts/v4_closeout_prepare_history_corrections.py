"""Correct actual dated QFQ defects, preserving existing PG history and coverage."""
import argparse,json,gzip,hashlib,os
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal,ROUND_HALF_UP
from collections import defaultdict
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_db.v4_history_corrections_pg_v2 import prepare

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
    if not a.label.isalnum():raise ValueError('VERSIONED_HISTORY_CORRECTION_REQUIRED')
    report=OUT/('HISTORY_CORRECTIONS_'+a.label+'.json')
    if report.exists():raise ValueError('PRESERVE_PRIOR_CORRECTIONS')
    conservation_path=OUT/('HISTORY_PROJECTION_CONSERVATION_'+a.label+'.json')
    raw=conservation_path.read_bytes();conservation=json.loads(raw)
    archive=ROOT/'data/v4/independent_oracles/history_projection'/hashlib.sha256(raw).hexdigest()/'RESULT.json'
    from workbench_analysis.tdx_official_daily_source import _atomic_write
    if archive.exists():
        if archive.read_bytes()!=raw:raise ValueError('IMMUTABLE_PROJECTION_CONFLICT')
    else:_atomic_write(archive,raw,tdx_root=Path('D:/new_tdx'))
    replay=json.loads(checked(ROOT,conservation['source_replay']).read_bytes())
    gbbq=replay['owners'][0]['sources']['gbbq'];classification=ref(ROOT,ROOT/'config/v4_02_gbbq_price_impact_classification_v1.json')
    dispositions=json.loads(checked(ROOT,classification).read_bytes())['dispositions']
    # Reuse the independently verified decoder implementation as input IO;
    # no bulk decoder test or comparison is rerun. New arithmetic covers only
    # bars excluded by the newer moving source window.
    from scripts.v4_closeout_independent_gbbq import decode
    actions=defaultdict(list)
    for event in decode(checked(ROOT,gbbq).read_bytes()):actions[event.security_id.upper()].append(event)
    identity_binding=replay['owners'][0]['sources']['identity']
    identities={r['security_id']:r['source_security_key'].upper() for r in json.loads(checked(ROOT,identity_binding).read_bytes())['rows']}
    authority=json.loads((ROOT/'config/core_product_read_authority_r1.json').read_bytes())
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[1]]
    records=[];indices={}
    for row in conservation['dates']:
        day=row['T0'];cutoff=int(day.replace('-',''));manifest=json.loads(checked(ROOT,authority['dates'][day]).read_bytes())
        if row['previous']!=manifest['source_bindings']['history'] or set(row['differences_by_field'])-{'qfq_ohlc'}:
            raise ValueError('QFQ_ONLY_CORRECTION_SCOPE_REQUIRED')
        if len(row['first_differences'])!=row['differences']:raise ValueError('ALL_CORRECTION_DIFFERENCES_REQUIRED')
        corrections=[dict(security_id=x['security_id'],trade_date=x['day'],previous=x['previous'],current=x['current']) for x in row['first_differences']]
        coverage={x['security_id']:set(x['old_only']) for x in row['coverage_differences']}
        if any(x['new_only'] for x in row['coverage_differences']):raise ValueError('UNEXPECTED_NEW_HISTORY_COVERAGE')
        prefix_checks=0;prefix_corrections=0;seen=set()
        with gzip.open(checked(ROOT,row['previous']),'rt',encoding='utf8') as stream:
            for line in stream:
                item=json.loads(line);sid=item['security_id'];symbol=identities[sid]
                for bar in item['bars']:
                    if bar['trade_date'] not in coverage.get(sid,set()):continue
                    seen.add((sid,bar['trade_date']));bar_day=int(bar['trade_date'].replace('-',''))
                    relevant=[e for e in actions[symbol] if bar_day<e.event_date<=cutoff]
                    blocked=any(dispositions.get(str(e.category),{}).get('formal_disposition') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT') for e in relevant)
                    values=[F(str(value)) for value in bar['raw_ohlc']]
                    for event in sorted((e for e in relevant if e.category==1),key=lambda e:(e.event_date,e.source_record_index)):
                        cash,price,bonus,rights=[F(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) for value in (event.c1,event.c2,event.c3,event.c4)]
                        if 10+bonus+rights<=0:raise ValueError('PREFIX_UNSUPPORTED_EVENT_PARAMETERS')
                        values=[(v-(cash-rights*price)/10)/((10+bonus+rights)/10) for v in values]
                    exact=None if blocked else [float(F((2*(v*100).numerator+(v*100).denominator)//(2*(v*100).denominator),100)) for v in values]
                    prefix_checks+=4
                    if bar['qfq_ohlc']!=exact:
                        corrections.append(dict(security_id=sid,trade_date=bar['trade_date'],previous=bar['qfq_ohlc'],current=exact));prefix_corrections+=1
        expected={(sid,d) for sid,dates in coverage.items() for d in dates}
        if seen!=expected:raise ValueError('PREFIX_SOURCE_DENOMINATOR_MISMATCH')
        sources=dict(previous_history=row['previous'],current_exact_history=row['current'],projection_conservation=ref(ROOT,archive),gbbq=gbbq,classification=classification,identity=identity_binding)
        indices[day]=prepare(ROOT,manifest['history_index'],corrections,sources)
        records.append(dict(T0=day,common_date_corrections=row['differences'],prefix_bars=len(seen),prefix_checks=prefix_checks,prefix_corrections=prefix_corrections,total_corrected_bars=len(corrections)))
        print(json.dumps(records[-1]),flush=True)
    result=dict(contract_id='V4_DATED_HISTORY_EXACT_CORRECTION_PREPARATION_R1',acceptance='PASS_PREPARATION_ONLY',indices=indices,records=records,
        input_conservation=ref(ROOT,archive),old_pg_history_mutated=False,history_coverage_preserved=True,publication=False,
        prior_full_aggregation_tests_repeated=False,scope='Small QFQ corrections; original PG history remains immutable; real reader verification and current field scope remain required')
    atomic_json(OUT,report,result)

if __name__=='__main__':main()
