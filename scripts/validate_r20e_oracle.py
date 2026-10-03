"""Independent persisted E2E oracle; no runtime evaluator/resolver imports."""
import json,hashlib,math,subprocess
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
OUT='reports/r20e'
EVENT_KEYS=['model_contract_id','state_lineage_id','entity_type','entity_id','episode_id','event_type','event_trade_date']

def require(value,reason):
    if not value:raise ValueError(reason)
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def binding(raw):return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def stamp(v):return datetime.fromisoformat(v.replace('Z','+00:00'))
def near(a,b):return a is None and b is None or isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isfinite(a) and abs(a-b)<1e-10

def validate(producer=None,settlement=None,objects=None):
    overrides=objects or {}
    def obj(ref):
        p=(ROOT/ref['path']).resolve();require(p.is_relative_to(ROOT),'PATH_ESCAPE')
        raw=p.read_bytes();require(binding(raw)=={k:ref[k] for k in ['sha256','bytes']},'EXACT_PERSISTED_ARTIFACT')
        return overrides.get(ref['path'],json.loads(raw))
    p=producer or json.loads((ROOT/OUT/'PRODUCER_RECEIPT.json').read_bytes())
    t=settlement or json.loads((ROOT/OUT/'SETTLEMENT_RECEIPT.json').read_bytes())
    from scripts.validate_r20a_current import validate as current_gate
    current_gate()
    require(p['authority']['current_v4_14']['path']=='data/v4/V4_14_ACCEPTED_HEAD.json' and t['authority']==p['authority'],'CURRENT_V4_14_ONLY')
    require(p['pid']!=t['pid'] and stamp(p['end'])<=stamp(t['start']),'ACTUAL_PERSISTED_PROCESS_BOUNDARY')
    require(stamp(t['freeze_exact_readback_at'])<=stamp(t['first_future_source_open_at']),'T0_BEFORE_FUTURE_SOURCE_READ')
    require(not p['future_source_reads'] and p['T0_FROZEN_BEFORE_FUTURE_SOURCE_READ'],'PRODUCER_NO_FUTURE_READS')
    require(p['frozen_refs']==t['frozen_refs_after'],'FREEZE_BYTES_IMMUTABLE')
    require(not p['forbidden_feedback'] and not t['forbidden_feedback'] and not t['raw_provider_fallback'],'NO_FEEDBACK_OR_PROVIDER')
    require(set(p['input_channels'])=={'CURRENT_V4_14_ACCEPTED_AUTHORITY','SEALED_OWNER_PUBLICATION','EXPLICIT_ENGINEERING_VECTOR'},'INPUT_CHANNEL_CLOSURE')
    for r in p['frozen_refs']:obj(r)
    registry=json.loads((ROOT/'data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json').read_bytes())
    entries={e['path']:e for e in registry['entries']}
    receipts=p['portability_receipts']+t['portability_receipts']
    for receipt in receipts:
        e=entries.get(receipt['path']);mode=receipt['authority_mode'];request=receipt['requested_binding'];observed=receipt['observed_binding']
        if e:require(mode==e['mode'] and request in e['accepted_bindings'],'REGISTERED_ADMISSION')
        if receipt['normalization_applied']:
            require(e is not None and mode=='AUDITED_CRLF_LF_EQUIVALENT_TEXT' and e['source_kind']=='TEXT' and not e['lfs_object_identity'],'NO_BINARY_OR_UNREGISTERED_NORMALIZATION')
            require(observed in e['admitted_representations'] and receipt['normalization_kind']=='REGISTERED_CRLF_LF_ONLY','EXPLICIT_PORTABILITY_RECEIPT')
            raw=subprocess.check_output(['git','cat-file','blob',e['git_blob_oid']],cwd=ROOT)
            require(binding(raw)==e['git_blob_binding'],'INDEPENDENT_GIT_BLOB_PROOF')
            lf=raw.replace(b'\r\n',b'\n');representations=[raw,lf,lf.replace(b'\n',b'\r\n')]
            require(request in [binding(v) for v in representations] and observed in [binding(v) for v in representations],'AUDITED_ONLY_TEXT_EQUIVALENCE')
        else:require(observed==request,'LITERAL_IDENTITY_NO_HIDDEN_NORMALIZE')
    manifests=[obj(r) for r in p['publications']];first=manifests[0];revision=manifests[1];correction=manifests[2]
    require(first['logical_events']==revision['logical_events']==correction['logical_events'],'SAME_DAY_EVENT_IDENTITY')
    require(first['enrollments']==revision['enrollments'] and not correction['enrollments'],'CORRECTION_PRESERVES_FIRST_ENROLLMENT')
    require(any(d['status']=='NOT_APPLICABLE_NO_ACCEPTED_OWNER' for d in first['diagnostics']),'STOCK_WARM_NOT_APPLICABLE')
    for m in manifests:
        ledger=[obj(r) for r in m['daily_ledger']]
        require(len(ledger)==len({tuple(r[k] for k in ['model_contract_id','state_lineage_id','publication_id','entity_type','entity_id','signal_type']) for r in ledger}),'DAILY_LEDGER_UNIQUE_COMPLETE')
        require(all(r['display_rank'] is None and r['focus_activation_state'] is None for r in ledger),'FOCUS_UI_NOT_ENROLLMENT_INPUT')
        for er in m['logical_events']:
            event=obj(er);require(event['logical_event_id']==digest([event[k] for k in EVENT_KEYS]),'LOGICAL_EVENT_CANONICAL_ID')
        for er in m['enrollments']:
            e=obj(er);require(e['enrollment_id']==digest([e['logical_event_id'],e['cohort_namespace']]),'ENROLLMENT_CANONICAL_ID')
            require(e['T0']==obj(next(r for r in m['logical_events'] if obj(r)['logical_event_id']==e['logical_event_id']))['event_trade_date'],'EVENT_T0_FREEZE')
    require(len(p['first_enrollments'])==3,'ALL_SIGNAL_COHORT_NO_FOCUS_FILTER')
    frozen={obj(f)['enrollment_id']:(f,obj(f)) for f in p['freezes']+p['real_freezes']}
    for enid,(fr,f) in frozen.items():
        e=obj(f['enrollment']);require(e['T0']==f['T0'],'CORRECTION_NO_RESET_T0')
        snapshot=obj(f['snapshot']);universe=snapshot['universe']
        for name in ('market','sector'):
            basket=f[name];members=basket['members']
            eligible=[r for r in universe if r['research_eligible'] is True]
            signal=next(r for r in universe if r['security_id']==f['signal_id'])
            expected=eligible if name=='market' else [r for r in eligible if r['security_id']!=f['signal_id'] and signal.get('primary_industry') and r.get('primary_industry')==signal['primary_industry']]
            require([m['security_id'] for m in members]==sorted(r['security_id'] for r in expected),'BENCHMARK_FROZEN_CONSTITUENTS')
            require(all(near(m['weight'],1/len(members)) and near(m['fixed_shares'],m['weight']/m['reference']) for m in members),'FIXED_INITIAL_WEIGHTS_NO_REWEIGHT')
            require(basket['constituent_policy']=='FIXED_ORIGINAL_WEIGHTS_NO_REWEIGHT','NO_REWEIGHT_POLICY')
        controls=f['controls'];content={k:v for k,v in controls.items() if k!='assignment_digest'}
        require(controls['assignment_digest']==digest(content),'CONTROL_ASSIGNMENT_IDENTITY')
        if f['T0']=='2026-08-31':
            require(controls['A']['status']=='NOT_AVAILABLE','NO_INVENTED_LEGACY')
            require(controls['B']['control_entity_ids']==['S','CNF','INV'],'CONTROL_B_FROZEN_SAME_DAY_COUNT')
            require(set(controls['C']['control_entity_ids'])=={'A','B','C'},'NO_FUTURE_CONTROL_REFILL')
    require(t['same_source_counts']['before']==t['same_source_counts']['after'],'SAME_SOURCE_IDEMPOTENT')
    calendar=obj(p['authority']['calendar']);sessions=[r['trade_date'] if isinstance(r,dict) else r for r in calendar['session_dates']]
    sources={r['sha256']:obj(r)['rows'] for r in t['future_sources']}
    outcomes=[obj(r) for r in t['outcomes']];groups={};absolute=market_unavailable=sector_unavailable=0
    for outcome in outcomes:
        enid=outcome['enrollment_id'];fr,f=frozen[enid];n=outcome['horizon'];index=sessions.index(f['T0']);due=sessions[index+n] if index+n<len(sessions) else None
        require(outcome['due_date']==due and n in (1,3,5,10,20),'ACCEPTED_SESSION_DUE_NO_MOVE')
        require(outcome['frozen_t0']==fr and outcome['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','OUTCOME_NOT_T0_AUTHORITY')
        if outcome['outcome_status']=='PENDING':
            require(due is None or due>outcome['report_cutoff'],'GENUINELY_NOT_DUE_PENDING');require(not outcome['price_path'],'PENDING_NO_FUTURE_READ')
        else:
            prices=sources[outcome['evaluation_source']['sha256']];sid=f['signal_id'];dates=sessions[index+1:index+n+1];rows=[prices.get(sid,{}).get(date,{}) for date in dates]
            require([r['trade_date'] for r in outcome['price_path']]==dates,'FUTURE_PATH_EXCLUDES_T0')
            require(all(r['evaluation_basis_date']==due for r in outcome['price_path']),'ONE_EVALUATION_BASIS')
            reference=f['comparison_reference'];closes=[r['close'] for r in rows];peak=reference;dd=0
            for close in closes:peak=max(peak,close);dd=min(dd,close/peak-1)
            expected=[closes[-1]/reference-1,max([reference]+[r['high'] for r in rows])/reference-1,min([reference]+[r['low'] for r in rows])/reference-1,dd]
            require(all(near(outcome[k],value) for k,value in zip(('R_N','MFE_N','MAE_N','PATH_MDD_CLOSE_N'),expected)),'INDEPENDENT_FORWARD_FORMULAS')
            absolute+=1
            for name in ('market','sector'):
                b=outcome[name+'_benchmark'];basket=f[name];coverage=contribution=0
                for member in basket['members']:
                    row=prices.get(member['security_id'],{}).get(due,{})
                    if row.get('close') is not None:coverage+=member['weight'];contribution+=member['weight']*row['close']/member['reference']
                require(near(b['benchmark_endpoint_coverage'],coverage) and near(b['benchmark_missing_weight'],1-coverage) and near(b['observed_contribution'],contribution),'INDEPENDENT_ORIGINAL_WEIGHT_VALUATION')
                require(b['marked_permission'] is False and b['relative_market_return_marked'] is None,'UNFROZEN_MARKED_THRESHOLDS_DENIED')
                if coverage<1:
                    require(b['return'] is None and b['relative_return'] is None,'PARTIAL_NO_RENORMALIZATION')
                    if name=='market':market_unavailable+=1
                    else:sector_unavailable+=1
        groups.setdefault((enid,n),{})[outcome['outcome_revision_id']]=outcome
    require(absolute and market_unavailable and sector_unavailable,'ABSOLUTE_SURVIVES_RELATIVE_DEGRADATION')
    for values in groups.values():
        ordered=sorted(values.values(),key=lambda r:r['evaluation_revision'])
        require([r['evaluation_revision'] for r in ordered]==list(range(1,len(ordered)+1)),'APPEND_ONLY_REVISION_SEQUENCE')
        require(len({r['evaluation_source']['sha256'] for r in ordered})==len(ordered),'NO_SAME_SOURCE_DUPLICATE_REVISION')
    for viewref in t['readbacks']:
        view=obj(viewref);enid=obj(view['frozen_t0'])['enrollment_id']
        for horizon,row in view['FIRST_OBSERVED'].items():
            values=sorted(groups[(enid,int(horizon))].values(),key=lambda r:r['evaluation_revision']);firstobserved=next((r for r in values if r['outcome_status']!='PENDING'),values[0])
            require(row==firstobserved and view['LATEST_CORRECTED'][str(horizon)]==values[-1],'FIRST_OBSERVED_IMMUTABLE_LATEST_APPEND')
    cross=obj(p['crossed']);require(cross['ITT_RETAINED'] and cross['assignment_digest']==obj(cross['frozen_t0'])['controls']['assignment_digest'],'CROSSING_NO_REDRAW')
    competing=[obj(r) for r in p['competing']]
    require({'CONFIRMED','INVALIDATED'}<=set(r['competing_event'] for r in competing) and all(r['price_settlement_continues'] for r in competing),'COMPETING_OUTCOME_SETTLEMENT_CONTINUES')
    real=obj(p['real_publication']);require(real['source_publication']['path'].startswith('reports/v4_14_replay_r18/real/'),'REAL_SEALED_PUBLICATION')
    require(real['complete_owner_rows']==5224 and p['real_freezes'] and t['real_outcomes'],'REAL_PERSISTED_TRAJECTORY')
    real_enrollment=obj(p['real_enrollment']);real_prices=obj(t['real_source'])
    require(real_enrollment['comparison_reference_source']==t['real_source'],'REAL_EXACT_T0_QUOTE_AUTHORITY')
    quote=next(row for row in real_prices['rows'] if row['security_id']==real_enrollment['entity_id'] and row['trade_date']==real_enrollment['T0'])
    require(quote['adjustment_readiness']=='READY' and near(float(quote['close']),real_enrollment['comparison_reference']) and quote['adjustment_source_revision']==real_enrollment['adjustment_identity'],'REAL_SOURCE_BACKED_T0_REFERENCE')
    for freeze_ref in p['real_freezes']:
        f=obj(freeze_ref);snapshot=obj(f['snapshot'])
        require(snapshot['source']==t['real_source'] and snapshot['research_universe_quality']=='UNKNOWN_ACCEPTED_RESEARCH_ELIGIBILITY_NOT_PROJECTED','NO_QUOTE_TO_RESEARCH_UNIVERSE_UPGRADE')
        require(f['market']['quality']=='UNKNOWN_UNAVAILABLE' and not f['market']['members'] and all(not f['controls'][k]['control_entity_ids'] for k in ('A','B','C')),'UNKNOWN_REAL_MEMBERSHIP_FAIL_CLOSED')
    require(all(obj(r)['outcome_status']=='PENDING' and obj(r)['evidence_class']=='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED' for r in t['real_outcomes']),'REAL_SCOPE_NO_FUTURE_OR_PIT_CLAIM')
    require(t['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED','NO_HISTORICAL_PIT_CLAIM')
    return dict(R20E_V4_15_FULL_PERSISTED_E2E='PASS_LOCAL',R20E_INDEPENDENT_ORACLE='PASS_LOCAL',REAL_ACCEPTED_SOURCE_V4_15='PASS_CAPABILITY_SCOPED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',V4_15_ACCEPTED_HEAD='NOT_CREATED',V4_STAGE_ACCEPTED_HEAD='V4_00_TO_V4_14_ACCEPTED',V4_DATA_ACCEPTED_HEAD='2026-09-30',Production=False,Shadow=False,Focus=False,V4_16=False,absolute_settlements_verified=absolute,market_unavailable_absolute_survives=market_unavailable,sector_unavailable_absolute_survives=sector_unavailable,portability_receipts_verified=len(receipts),producer_pid=p['pid'],settlement_pid=t['pid'],NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')

if __name__=='__main__':
    from scripts.r20_io import atomic
    result=validate();atomic(OUT+'/INDEPENDENT_E2E_GATE.json',result);print(json.dumps(result))
