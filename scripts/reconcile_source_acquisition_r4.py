"""Independent four-session reconciliation of real R4 acquisition receipts."""
import csv
import io
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.market_source_acquisition import digest, now, write, freeze_membership_observation, is_stock_code, corrected_candidate
from workbench_analysis.tdx_official_daily_source import _atomic_write

OUT=ROOT/'docs/evidence/source_acquisition_r4_20261009'
def load(path):return json.loads(Path(path).read_bytes())
def main():
    capture=load(OUT/'capture/acquisition.json')
    dates=capture['dates']; entry=load(OUT/'00_R4_ENTRY_HEAD_AND_EXISTING_SOURCE_CONTRACT.json')
    head=load(ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json')
    identity=load(ROOT/head['component_artifacts']['IDENTITY_UNIVERSE']['path'])['rows']
    ids={r['source_security_key'].lower():r['security_id'] for r in identity}
    legacy=list(csv.DictReader((ROOT/'docs/evidence/three_day_repair_r1_20261008/THREE_DAY_SOURCE_DIFF.csv').open(encoding='utf-8-sig')))
    baseline={(r['trade_date'],r['symbol'].lower()):r for r in legacy}
    from tdx.gbbq_reader import read_gbbq
    gbbq_path=Path('D:/new_tdx/T0002/hq_cache/gbbq')
    gbbq_bytes=gbbq_path.read_bytes();gbbq_hash=digest(gbbq_bytes);gbbq_events=read_gbbq(gbbq_path)
    gbbq_classes=load(ROOT/'config/v4_02_gbbq_price_impact_classification_v1.json')['dispositions']
    event_index={}
    for e in gbbq_events:event_index.setdefault(e.security_id.lower(),[]).append(e)
    write(OUT/'GBBQ_LIVE_READ_RECEIPT.json',dict(path=str(gbbq_path),sha256=digest(gbbq_bytes),
        records=len(gbbq_events),observed_at=now(),latest_event_date=max(e.event_date for e in gbbq_events),
        target_filter='event_date <= target; future records excluded from every target calculation',
        per_date={d:dict(eligible_events=sum(e.event_date<=int(d.replace('-','')) for e in gbbq_events),
                         excluded_future_events=sum(e.event_date>int(d.replace('-','')) for e in gbbq_events)) for d in dates},
        admission='SOURCE_READ_NOT_NEW_QFQ_ACCEPTANCE'))
    canonical={}
    for path in sorted({r['source'] for r in legacy}):
        for r in load(ROOT/path)['rows']:canonical[r['trade_date'],r['source_security_key'].lower()]=r
    batch={}; history={}; factors={}; universes={}; query_by_key={}
    for q in capture['queries']:
        query_by_key[q['method'],json.dumps(q['params'],sort_keys=True)]=q
        if not q.get('path'):continue
        payload=load(q['path']);rows=payload.get('rows',[]);m=q['method'];p=q['params']
        if m=='query_daily_history_k_AStock':
            for r in rows:batch[p['date'],r['code'].lower()]=r
        elif m=='query_history_k_data_plus':
            for r in rows:history[r['date'],r['code'].lower(),p['adjustflag']]=r
        elif m=='query_adjust_factor':factors[p['code']]=rows
        elif m=='query_all_stock':universes[p['day']]=rows
    matrix=[];oracle=[];summary={};gap_results=[]
    for day in dates:
        codes={code for (d,code) in batch if d==day}|{code for (d,code) in canonical if d==day}
        # Provider universe and known identity are separate observations. Never clone Sep30 counts into Oct08.
        codes|={r['code'].lower() for r in universes.get(day,[]) if is_stock_code(r['code'])}
        stats=Counter()
        for code in sorted(codes):
            old=baseline.get((day,code));can=canonical.get((day,code));b=batch.get((day,code)) or history.get((day,code,'3'))
            local=capture['local'].get(code,{});bar=local.get('bars',{}).get(day)
            q=history.get((day,code,'2'));f=factors.get(code)
            suspended=(b or {}).get('tradestatus')=='0'
            prior_unknown=old and old['reason']=='UNSUPPORTED_OR_UNPROVED_ADJUSTMENT'
            blockers=sorted({e.category for e in event_index.get(code,[]) if e.event_date<=int(day.replace('-','')) and
                             gbbq_classes.get(str(e.category),{}).get('formal_disposition') in ('PRICE_AFFECTING_UNSUPPORTED','UNKNOWN_PRICE_IMPACT')})
            decision=('TRADING_SUSPENSION_NO_BAR' if suspended and not can else
                      'QFQ_FACTOR_UNAVAILABLE' if prior_unknown else
                      'RAW_BAR_NOT_CAPTURED' if not can and not bar else 'TDX_ACCEPTED_PRESERVED')
            if day=='2026-10-08' and b and not suspended:decision='BAOSTOCK_AVAILABLE_NOT_BOUND'
            row=dict(security_id=ids.get(code,'UNMAPPED_PROVIDER_IDENTITY'),source_security_key=code,trade_date=day,
                local_tdx='LOCAL_FOUND' if bar else 'TDX_SOURCE_STALE' if local.get('last_date') else 'LOCAL_FILE_ABSENT',
                official_tdx='LIVE_PACKAGE_REJECTED' if day=='2026-10-08' else 'LIVE_METADATA_NEWER_THAN_TARGET',
                accepted_tdx_raw=bool(can),baostock_raw='BAOSTOCK_FOUND' if b else 'NOT_RECEIVED',
                baostock_qfq='BAOSTOCK_FOUND' if q else 'NOT_QUERIED',
                baostock_adjust_factor='BAOSTOCK_FOUND' if f else 'PROVIDER_EMPTY_CONFIRMED' if code in factors else 'NOT_QUERIED',
                requested_at=capture['requested_at'], response_status='RECEIVED' if b else 'COVERAGE_INSUFFICIENT',
                provider_date=(b or {}).get('date'),source_revision=digest(json.dumps(b,sort_keys=True).encode()) if b else None,
                hash=(can or {}).get('source_digest') or (bar or {}).get('hash'),unit='CNY/share;shares;CNY',
                price_basis_id='TDX_RAW' if can or bar else 'BAOSTOCK_RAW_V1' if b else 'UNKNOWN',
                error_type='QFQ_TARGET_COORDINATE_NOT_PROVEN' if prior_unknown or day=='2026-10-08' else None,
                decision=decision,accepted_corrected=False,strict_PIT=False)
            row['local_gbbq_blocking_categories']=json.dumps(blockers)
            row['gbbq_source_revision']=gbbq_hash
            matrix.append(row)
            stats['source_received']+=bool(b);stats['canonical_tdx_raw_count']+=bool(can);stats['local_target_bars']+=bool(bar)
            stats['suspended_no_bar']+=suspended and not can;stats['full_universe_count']+=1
            stats['qfq_observation_received']+=bool(q);stats['qfq_capability_unknown']+=bool(prior_unknown) if day!='2026-10-08' else bool(b and not suspended)
            stats['gbbq_blocked_security_count']+=bool(blockers) and bool(b) and not suspended
            stats['raw_gap']+=not(can or bar or b) and not suspended;stats['canonical_raw_not_captured']+=not(can or bar) and not suspended
            stats['known_unknown']+=not(can or bar) or bool(prior_unknown)
            if old:gap_results.append(dict(**row,old_reason=old['reason'],before='QFQ_CAPABILITY_UNPROVEN' if prior_unknown else 'EXPECTED_NO_BAR',
                                           fetched=bool(b),usable_corrected=False,residual_unknown=bool(prior_unknown),
                                           exact_blocker='NATIVE_AFFINE_COORDINATE_AND_FACTOR_CHAIN_NOT_ACCEPTED' if prior_unknown else 'EXPECTED_NO_BAR'))
            if b and can:
                diffs={k:str(Decimal(str(b[k]))-Decimal(str(can[k]))) for k in ('open','high','low','close','volume','amount') if str(b.get(k,'')).strip()}
                oracle.append(dict(trade_date=day,code=code,category='LEGACY_QFQ_GAP' if prior_unknown else 'OVERLAP',
                                   deltas=diffs,TDX_hash=can.get('source_digest'),source_basis='RAW_TO_RAW',
                                   acceptance='DIAGNOSTIC_NO_ACCEPTED_SOURCE_TOLERANCE'))
            h=history.get((day,code,'3'))
            if b and h:
                oracle.append(dict(trade_date=day,code=code,category='BATCH_VS_HISTORY_RAW',
                    deltas={k:str(Decimal(str(b[k]))-Decimal(str(h[k]))) for k in ('open','high','low','close')},
                    qfq_observed=bool(q),qfq_native_coordinate='UNPROVEN'))
            if q and h:
                oracle.append(dict(trade_date=day,code=code,category='RAW_VS_PROVIDER_QFQ',
                    ohlc_ratios={k:str(Decimal(str(q[k]))/Decimal(str(h[k]))) if Decimal(str(h[k])) else None for k in ('open','high','low','close')},
                    source_anchor='PROVIDER_ANCHOR_NOT_TDX_NATIVE_AFFINE_PROOF',
                    source_factor_count=len(f or []),gbbq_blocking_categories=blockers))
        relevant=[q for q in capture['queries'] if q['params'].get('date',q['params'].get('day'))==day]
        per_security_requests=[q for q in capture['queries'] if q['params'].get('start_date','9999')<=day<=q['params'].get('end_date','0000') and not q.get('error','').startswith('PermissionError:')]
        summary[day]=dict(stats,official_session=True,source_requested=len(relevant)+len(per_security_requests),accepted=0,owner_ready=False,
            live_readback='LAST_GOOD_2026_09_30',identity_stock_count='NOT_VERIFIABLE' if day=='2026-10-08' else len(codes),
            industry_concept_membership_count='NOT_VERIFIABLE',gbbq_ready='NOT_VERIFIABLE',market_owner_ready=False,
            core_profile_ready=False,structure_known_count='NOT_VERIFIABLE',rotation_known_count='NOT_VERIFIABLE',
            accepted_head_before='2026-09-30',accepted_head_after=head['accepted_trade_date'],
            live_context_token='READBACK_IN_09',real_request_count=len(relevant)+len(per_security_requests),request_count_semantics='SHARED_RANGE_CALLS_COUNT_FOR_EACH_COVERED_DATE;DO_NOT_SUM_ROWS',
            first_acquired_at=min((q['received_at'] for q in relevant if q.get('received_at')),default=None),
            data_head_candidate='STAGING_OBSERVATIONS_ONLY',before=176 if day!='2026-10-08' else 'NO_ACCEPTED_OWNER',
            fetched=stats['source_received'],usable_corrected=0,residual_unknown=stats['qfq_capability_unknown'],
            exact_blocker='TDX_EDGE_HTML;NO_ACCEPTED_NATIVE_QFQ_CHAIN;OWNER_ADMISSION_PENDING')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(matrix[0]));writer.writeheader();writer.writerows(matrix)
    _atomic_write(OUT/'02_FOUR_SESSION_PER_SECURITY_SOURCE_MATRIX.csv',stream.getvalue().encode('utf8'),tdx_root=Path('D:/new_tdx'))
    write(OUT/'02_FOUR_SESSION_SUMMARY.json',summary)
    write(OUT/'03_FOUR_SESSION_QFQ_GAP_RECAPTURE_AND_ADJUSTMENT_ORACLE.json',dict(
        status='PARTIAL_NOT_COMPLETE',legacy_rows=gap_results,legacy_qfq_count=sum(r['before']=='QFQ_CAPABILITY_UNPROVEN' for r in gap_results),
        oracle_comparisons=oracle,scope='INDEPENDENT_DECIMAL_RAW_DIFFERENCES;QFQ_COORDINATE_NOT_ADMITTED',dates=summary))
    write(OUT/'BAOSTOCK_SHARED_BUDGET_READBACK.json',load(ROOT/'reports/v4_baostock/request_ledger.json'))
    write(OUT/'04_BAOSTOCK_LIVE_RUNTIME_AND_HISTORICAL_QUERY_RECEIPTS.json',dict(sdk=capture['sdk'],sessions=capture['session_attempts'],queries=capture['queries']))
    write(OUT/'CORRECTED_FALLBACK_CANDIDATES.json',dict(status='STAGED_NOT_ADMITTED',rows=[
        dict(security_code=code,trade_date=day,candidate=corrected_candidate(None,row,
            identity_verified=False,session_verified=True,overlap_verified=False,
            tolerance_accepted=False,coordinate_verified=False))
        for (day,code),row in sorted(batch.items()) if day=='2026-10-08'],
        reason='Provider identity/date is observed; dated canonical identity, accepted overlap tolerance and target coordinate are not yet admitted'))
    persistence_errors=[q for q in capture['queries'] if q.get('error','').startswith('PermissionError:') and q.get('metadata',{}).get('error_code')=='0']
    write(OUT/'REQUEST_LEDGER_CLASSIFICATION_CORRECTION.json',dict(original_receipts_preserved=True,
        corrections=[dict(method=q['method'],params=q['params'],requested_at=q['requested_at'],
                          corrected_classification='PROVIDER_SUCCESS_LOCAL_CHECKPOINT_PERMISSION_ERROR',provider_error=False)
                     for q in persistence_errors],
        count_authority='BAOSTOCK_SHARED_BUDGET_READBACK.json; query receipt entries include a local persistence diagnostic and are not request counts'))
    roots=load(ROOT/'config/dm01_go_forward_runtime_contract_r4.json')['read_only_tdx_roots']
    membership=freeze_membership_observation(ROOT,OUT/'capture',dates,roots)
    membership['provider_queries']=[q for q in capture['queries'] if q['method']=='query_stock_industry']
    membership['status']='OBSERVATIONS_FROZEN_EFFECTIVE_DATE_NOT_PROVEN'
    write(OUT/'05_HISTORICAL_SECTOR_MEMBERSHIP_PROVIDER_DISCOVERY.json',membership)
    write(OUT/'06_SOURCE_POLICY_V1_MIGRATION_AND_FIELD_ADMISSION.json',dict(policy=load(ROOT/'config/v4_market_source_fallback_policy_v1.json'),
        legacy_digests_preserved={p:digest((ROOT/p).read_bytes())==sha for p,sha in entry['preserved'].items()},
        status='STAGING_IMPLEMENTED_PRODUCTION_NOT_ADMITTED',next_stage='NATIVE_COORDINATE_ORACLE_AND_OWNER_ADMISSION'))
    daily=OUT/'daily_run/2026-10-08/source_readiness_receipt_r2.json'
    write(OUT/'07_DM01_20261008_INCREMENT_AND_HISTORICAL_REPAIR_E2E.json',dict(
        new_session_increment=load(daily) if daily.exists() else 'NOT_RUN',
        historical_corrected_repair='ACQUISITION_EXECUTED_OWNER_REBUILD_NOT_COMPLETE',
        OCT08_FULL_SOURCE_CAPTURE='BAOSTOCK_CAPTURED_TDX_BLOCKED',OCT08_DAILY_INCREMENT='BLOCKED_SOURCE_CAPTURE',
        OCT08_OWNER_MATERIALIZATION='NOT_PASSED',OCT08_SCOPED_READBACK='LAST_GOOD_ONLY'))
    runtime=[]
    from workbench_analysis.v4_13_accepted_contract_package import current_contracts
    from workbench_analysis.v4_13_input_binder import AcceptedInputBinder
    from workbench_analysis.v4_13_loo_runtime import LOOContextRuntime
    for day in dates:
        try:
            contracts=current_contracts(ROOT);binder=AcceptedInputBinder(contracts,day,now());binder.load_structure()
            sid=next(iter(binder.by_security), next(iter(ids.values())))
            result=LOOContextRuntime(contracts).compute(binder,sid,'r4-probe')
            runtime.append(dict(trade_date=day,membership_complete=binder.membership_complete,source_current_count=len(binder.current),
                structure_count=len(binder.structure),sample_security=sid,relative_sector_state=result['relative_sector_state'],
                counters=binder.counters,status='REAL_RUNTIME_INVOKED_INPUT_CAPABILITY_DEGRADED'))
        except Exception as exc:runtime.append(dict(trade_date=day,status='RUNTIME_PROBE_BLOCKED',error=f'{type(exc).__name__}:{exc}'))
    write(OUT/'08_STRUCTURAL_OWNER_AFTER_SOURCE_REPAIR.json',dict(status='NOT_COMPLETE',
        runtime_implementation_exists=True,probes=runtime,
        reason='New observations cannot bypass accepted membership/Core/previous D1 owner bindings',
        calendar_correction=dict(sep30_T_minus_3='2026-09-24',oct08_T_minus_1='2026-09-30',oct08_T_minus_3='2026-09-28')))
    preserved={p:digest((ROOT/p).read_bytes())==sha for p,sha in entry['preserved'].items()}
    readback=[]
    import urllib.request
    for route in ('/api/v4/context','/api/operations/status'):
        try:
            with urllib.request.urlopen('http://127.0.0.1:28765'+route,timeout=10) as r:payload=json.loads(r.read())
            readback.append(dict(route=route,status='READ',payload=payload))
        except Exception as exc:readback.append(dict(route=route,status='NOT_VERIFIABLE',error=str(exc)))
    token=next((r['payload'].get('context_token') for r in readback if r.get('payload',{}).get('context_token')),None)
    context_payload=next((r['payload'] for r in readback if r.get('payload',{}).get('context_token')), {})
    if context_payload:
        summary['2026-09-30']['market_owner_ready']=True
        summary['2026-09-30']['core_profile_ready']=True
        summary['2026-09-30']['core_profile_count']=context_payload['counts']['stocks']
        member_head=load(ROOT/'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')
        summary['2026-09-30']['industry_concept_membership_count']=sum(member_head['formal_rows_by_type'].values())
    live=ROOT/'reports/v4_dm01/2026-10-08/source_readiness_receipt_r2.json'
    if live.exists():
        e2e=load(OUT/'07_DM01_20261008_INCREMENT_AND_HISTORICAL_REPAIR_E2E.json')
        e2e['normal_daily_entry_run']=load(live)
        e2e['normal_daily_entry_receipt']=load(ROOT/'reports/v4_production_cutover_20261007/DAILY_REFRESH_LATEST_RECEIPT.json')
        write(OUT/'07_DM01_20261008_INCREMENT_AND_HISTORICAL_REPAIR_E2E.json',e2e)
    for day in summary:
        summary[day]['live_context_token']=token or 'NOT_VERIFIABLE'
        summary[day]['gbbq_ready']='READ_PARSED_ADMISSION_PENDING'
        summary[day]['baostock_daily_count']=summary[day]['source_received']
        summary[day]['qfq_gap']=summary[day]['qfq_capability_unknown']
    write(OUT/'02_FOUR_SESSION_SUMMARY.json',summary)
    write(OUT/'09_SCOPED_RELEASE_OR_SAFE_BLOCKER_READBACK.json',dict(status='BLOCKED_SAFE_LAST_GOOD',preserved=preserved,
        promoted=False,readback=readback,acceptance='NO_NEW_OWNER_OR_SUCCESSOR_ACCEPTANCE',next_stage='TDX_CAPTURE_AND_NATIVE_QFQ_OWNER_REPAIR'))
    print(json.dumps(dict(matrix_rows=len(matrix),oracle_comparisons=len(oracle),legacy_rows=len(gap_results),preserved=preserved)))

if __name__=='__main__':main()
