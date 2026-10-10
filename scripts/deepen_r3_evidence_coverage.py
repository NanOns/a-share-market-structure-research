"""Close field-level evidence indexing and exact historical evidence gaps."""
from immediate_r3_common import *
from deepen_r3_lineage import symbol
from collections import defaultdict,Counter
D=OUT/'11_DEEPENING'

def main():
    h=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=h['accepted_trade_date']
    alg=load(OUT/'02_P0_ALG/P0_ALG_ORACLE_RESULT.json');up=load(OUT/'09_CONTINUATION/UPSTREAM_ORACLE_RESULT.json')
    rows=[]
    for artifact,data in [(OUT/'02_P0_ALG/P0_ALG_ORACLE_RESULT.json',alg),(OUT/'09_CONTINUATION/UPSTREAM_ORACLE_RESULT.json',up)]:
        groups=defaultdict(list)
        for index,r in enumerate(data['results']):groups[(r.get('domain','UPSTREAM_NUMERIC'),r['field'])].append((index,r))
        for (domain,field),checks in groups.items():
            if domain in ('UPSTREAM_NUMERIC','UNKNOWN_WINDOW_ENDPOINT'):
                oracle=OUT/'09_CONTINUATION/UPSTREAM_INDEPENDENT_ORACLE.py';fn='formulas';producer='src/v4/factors/core.py';inputfile=OUT/'09_CONTINUATION/UPSTREAM_ORACLE_INPUT.json';family='core'
            else:
                oracle=OUT/'02_P0_ALG/P0_ALG_FULL_RECURSION_ORACLE.py';fn={'D0_RAW':'d0_features','D0_CLASSIFIER':'classifier','D2_RECURSION':'state_step'}.get(domain,'main')
                producer='src/workbench_analysis/today_research_factors_v3_3.py' if domain=='D0_RAW' else 'src/v4/target_fact_producers_r4.py' if domain=='D0_CLASSIFIER' else 'src/v4/research_state.py' if domain=='D2_RECURSION' else 'src/workbench_analysis/tdx_sector_retro_r43.py'
                inputfile=OUT/'02_P0_ALG/P0_ALG_ORACLE_INPUT.json';family='prewatch' if domain.startswith('D0') else 'focus' if domain=='D2_RECURSION' else 'relative_sector' if domain=='LOO' else 'sector' if domain=='NATIVE' else 'rotation'
            rows.append(dict(field=field,comparison_domain=domain,independent_formula=symbol(oracle,fn),producer=binding(producer),
              input_binding=binding(inputfile),result_binding=binding(artifact),result_array_indices=[checks[0][0],checks[-1][0]],
              count=len(checks),failures=sum(not r['passed'] for _,r in checks),first_actual_comparison=checks[0][1],
              output_owners={d:ref[family] for d,ref in h['owners'].items() if family in ref},
              formula_scope='WINDOW_OR_ENDPOINT_NULL_ONLY_NOT_EXACT_SOURCE_REASON' if domain=='UNKNOWN_WINDOW_ENDPOINT' else 'EXACT_NAMED_EQUATION_OR_STATE_RULE',
              prior_state='EXACT_INPUT_PRIOR_STATE_BINDING' if domain=='D2_RECURSION' else None,
              historical_first_available=None,PIT_scope='CORRECTED_REPLAY_NOT_AS_RECORDED',
              API_BINDING='ONLY_BOUND_FIELDS_IN_EXACT_FIELD_SOURCE_CONSUMER_MATRIX',UI_BEHAVIOR='ONLY_BROWSER_QA_DECLARED_FIELDS'))
    write(D/'ALG_FIELD_COVERAGE_MATRIX.json',dict(contract='R3_ALG_FIELD_FORMULA_LINEAGE_V2',fields=rows,
      total_inherited_comparisons=sum(r['count'] for r in rows),new_numeric_comparisons=0,
      baseline_counts_not_added_as_new_run=True,
      separate_domains=dict(full_LOO_rank_episode='NOT_PUBLISHED_IN_CURRENT_OPERATIONAL_OWNER; requires separate accepted publication',
        real_reentry='NOT_OBSERVED',exact_all_detector_source_reason='NOT_ALL_PROVED_BY_NUMERIC_NULL_CHECKS')))
    inventory=[]
    for d,sources in h['source_registry'].items():
        membership=load(sources['membership']);capture=load(sources['freeze']) if sources.get('freeze') else None
        for family,owner in h['owners'][d].items():
            inventory.append(dict(trade_date=d,family=family,owner=owner,membership_source=sources['membership'],
              member_asof=membership['member_set_asof'],member_sources=membership['sources'],identity_source=membership['identity_source'],
              source_capture_binding=sources.get('freeze'),source_capture_at=capture.get('observed_at') if capture else None,
              ingest_log_status='EXACT_FREEZE_OBSERVATION_EXISTS_NOT_HISTORICAL_FIRST_AVAILABILITY' if capture else 'NO_PER_DATE_INGEST_LOG_BOUND_IN_OPERATIONAL_HEAD',
              lifecycle=sources['lifecycle'],AS_RECORDED=False,historical_first_available=None,
              PIT_scope='LATEST_MEMBER_RETRO' if family in ('sector','rotation','relative_sector','seed') else 'CORRECTED',
              strict_historical_verdict='NOT_VERIFIABLE',missing_originals=['historical first-capture receipt at T0','historically observed effective-date membership' if family in ('sector','rotation','relative_sector','seed') else 'historical immutable source-availability receipt']))
    strict=load('data/v4/V4_DATA_ACCEPTED_HEAD.json');cal=load(strict['calendar'])['session_dates'];base='2026-09-30';idx=cal.index(base);window=cal[idx-20:idx+1]
    actual_membership_dates=[load(p)['target_trade_date'] for p in (ROOT/'data/v4/a04_go_forward_r3/observations').glob('*.json')]
    write(D/'PIT_ORIGINAL_INGEST_AND_MISSING_DAYS.json',dict(contract='R3_PIT_DEEP_INVENTORY_V1',items=inventory,
      strict_head=binding('data/v4/V4_DATA_ACCEPTED_HEAD.json'),strict_scope_expanded=False,
      formal_Amount_A_h21=dict(target=base,calendar=strict['calendar'],required_sessions=window,actual_membership_observation_dates=actual_membership_dates,missing_sessions=[d for d in window if d not in actual_membership_dates]),
      limitations='Present ingestion records prove actual later capture only; never backdate first availability'))
    write(D/'MEMBER27_USER_SCOPE_DISPOSITION.json',dict(contract='R3_USER_SCOPE_EXCLUSIONS_V2',
      BSE=dict(count=26,status='USER_DEFERRED',source='Latest user instruction'),
      SZ001235=dict(count=1,status='USER_EXCLUDED_REPORTED_DELISTED',reason='User explicitly states already delisted',
        verification='USER_PROVIDED_FACT_NOT_INDEPENDENT_DATED_IDENTITY_AUTHORITY',prior_local_feed_evidence=binding(OUT/'09_CONTINUATION/SZ001235_LOCAL_DATA_DISPOSITION.json')),
      source_rows_retained=True,accepted_pool_changed=False,active_identity_work_this_round=0))
    print('indexed algorithm fields',len(rows),'PIT rows',len(inventory))
if __name__=='__main__':main()
