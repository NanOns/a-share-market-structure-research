"""Real accepted-input history, independent oracle and unchanged downstream diff."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json
import gzip
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import binding,digest,immutable_json,read_bound,publish,delta
from v4.stock_prewatch import write_immutable_gzip_jsonl,load_accepted,build as stock_build
from v4.base_seed import _load_accepted_source_context,build_candidate_from_records

def oracle_scores(returns, universe):
    """Independent pairwise oracle; does not call sorted-group producer."""
    finite={sid:value for sid in universe if (value:=returns.get(sid)) is not None}
    n=len(finite)
    return {sid:None if sid not in finite or n<2 else 100*(sum(v<finite[sid] for v in finite.values())+.5*(sum(v==finite[sid] for v in finite.values())-1))/(n-1) for sid in universe}

def main():
    import pyarrow.parquet as pq
    from workbench_analysis.dm01_accepted_chain_v1 import validate_head_v2
    entry=json.loads((ROOT/'reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json').read_text(encoding='utf8'))
    timestamp=entry['observed_at']
    head=json.loads((ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_text(encoding='utf8'))
    validate_head_v2(ROOT,head)
    chain_ref=binding(ROOT,ROOT/'data/v4/DM01_A01_R3_ACCEPTED_CHAIN_20260924_20260930_R1.json')
    chain=read_bound(ROOT,chain_ref);context=read_bound(ROOT,chain['source_context'])
    sessions=context['calendar']['session_dates'];targets=['2026-09-22','2026-09-23','2026-09-24','2026-09-28','2026-09-29','2026-09-30']
    history_parent=read_bound(ROOT,context['parent']['components']['ADJUSTED_DAILY'])
    historical_ref=history_parent['accepted_source_bindings'][0]
    historical_path=ROOT/historical_ref['path']
    if binding(ROOT,historical_path)['sha256']!=historical_ref['sha256']: raise ValueError('A02_HISTORICAL_SOURCE_HASH')
    begin=sessions[sessions.index(targets[0])-20]
    columns=['canonical_security_id','source_security_key','trade_date','qfq_close','qfq_mul','qfq_add','adjusted_quality','trading_status','adjustment_source_revision']
    data=pq.read_table(historical_path,columns=columns,filters=[('trade_date','>=',int(begin.replace('-',''))),('trade_date','<=',20260924)]).to_pylist()
    bars={}
    for row in data:
        text=str(row['trade_date']);day=text[:4]+'-'+text[4:6]+'-'+text[6:]
        bars[(row['canonical_security_id'],day)]=dict(security_id=row['canonical_security_id'],trade_date=day,source_security_key=row['source_security_key'],close=str(row['qfq_close']) if row['qfq_close'] is not None else None,mul=str(row['qfq_mul']),add=str(row['qfq_add']),quality=row['adjusted_quality'],state=row['trading_status'],adjustment_revision=row['adjustment_source_revision'])
    source_refs=[historical_ref,chain_ref,chain['source_context'],context['calendar']['binding'],context['identity']['binding'],binding(ROOT,ROOT/'data/v4/V4_DATA_ACCEPTED_HEAD.json')]
    universes={}
    for node in chain['nodes']:
        adj=node['components']['ADJUSTED_DAILY'];identity=node['components']['IDENTITY_UNIVERSE'];status=node['components']['TRADING_STATUS']
        refs=[dict(path=r['artifact_path'],sha256=r['artifact_sha256'],bytes=r['artifact_bytes']) for r in (adj,identity,status)]
        source_refs+=refs
        rows=read_bound(ROOT,refs[0])['rows']; ids=read_bound(ROOT,refs[1])['rows'];statuses=read_bound(ROOT,refs[2])['rows']
        day=node['trade_date'];universes[day]=sorted(r['security_id'] for r in ids if r.get('identity_status')=='IDENTITY_BOUND' and r.get('board_scope') in ('STAR','SH_MAIN','SZ_MAIN','CHINEXT'))
        for row in rows:
            bars[(row['security_id'],day)]=dict(security_id=row['security_id'],trade_date=day,source_security_key=row['source_security_key'],close=row['close'],mul=row['qfq_mul'],add=row['qfq_add'],quality=row['adjustment_readiness'],state='ACTUAL_TRADED',adjustment_revision=row['adjustment_source_revision'])
        for row in statuses:
            key=(row['security_id'],day)
            if key not in bars and row.get('trading_status')=='SUSPENDED': bars[key]=dict(security_id=row['security_id'],trade_date=day,source_security_key=row['source_security_key'],close=None,mul=None,add=None,quality='READY',state='SUSPENDED',adjustment_revision=None)
    identity=context['identity']['records']
    for day in targets:
        if day not in universes:
            universes[day]=sorted({r['security_id'] for r in identity if r.get('board_scope') in ('STAR','SH_MAIN','SZ_MAIN','CHINEXT') and r.get('security_type')=='A_STOCK' and r.get('list_date') and r['list_date']<=day and (not r.get('delist_date') or r['delist_date']>day) and (not r.get('symbol_effective_from') or r['symbol_effective_from']<=day) and (not r.get('symbol_effective_to') or r['symbol_effective_to']>=day)})
    frozen=list(sorted(bars.values(),key=lambda r:(r['trade_date'],r['security_id'])))
    directory=ROOT/'data/v4/a02_rps_history_r1'
    raw_path=directory/('REAL_BOUNDED_PRICE_INPUT_'+digest(frozen)+'.jsonl.gz')
    write_immutable_gzip_jsonl(raw_path,frozen)
    publications={}; publication_refs={}; input_refs={}; delta_refs={}; independent=[]; previous=None
    contract=dict(contract_id='V4_RPS_PIT_HISTORY_V1',version='1.0.0',status='FROZEN_CANDIDATE',score_contract='RPS_MIDRANK_V1',formula='100 * (less + 0.5 * (equal - 1)) / (N - 1)',horizons=[5,20],parameters=dict(min_evaluable_universe=2),return_contract='CROSS_SECTION_SESSION_WINDOW_V1',return_formula='close[T]/close[T-N]-1; actual endpoints; unknown intermediate states fail closed',warmup=dict(insufficient_history='INSUFFICIENT_SESSION_HISTORY',T_minus_1='T_MINUS_1_PUBLICATION_MISSING',T_minus_3='T_MINUS_3_PUBLICATION_MISSING',calendar_gap='UNEXPLAINED_DATA_GAP',calendar_revision='CALENDAR_REVISION',universe_revision='UNIVERSE_AUTHORITY_REVISION',new_member='PRIOR_UNIVERSE_MEMBER_MISSING'),membership_policy='Date-effective cross-sections bind separate member digests; same identity authority permits continuing members; new members remain UNKNOWN for missing prior.',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_availability_proven=False,publication_policy='Immutable create-if-absent; externally accepted inputs do not externally accept derived RPS candidates.',consumer_policy='V4-07 runtime reads bound score artifacts only; no raw-history recalculation; candidate amendment cannot enter formal consumer before independent external acceptance.',price_coordinate_policy='Endpoint affine coefficients must match; mismatch is UNKNOWN, no adjustment reinterpretation.',runtime_bindings=[binding(ROOT,ROOT/'src/v4/rps_pit_history_a02_v1.py'),binding(ROOT,ROOT/'src/v4/factors/core.py'),binding(ROOT,ROOT/'src/v4/base_seed.py'),binding(ROOT,ROOT/'src/v4/stock_prewatch.py')],production=False,shadow=False,focus_cutover=False)
    immutable_json(ROOT/'config/a02_rps_pit_history_v1.json',contract)
    algorithm_identity=digest(dict(contract='RPS_MIDRANK_V1',parameters=contract['parameters'],source=binding(ROOT,ROOT/'src/v4/factors/core.py')))
    for day in targets:
        members=universes[day];returns={str(h):{} for h in (5,20)};endpoint={};index=sessions.index(day)
        for sid in members:
            endpoint[sid]={}
            for h in (5,20):
                window=sessions[max(0,index-h):index+1];rows=[bars.get((sid,d)) for d in window]; first=rows[0];last=rows[-1]; reason=None
                if len(window)<h+1: reason='INSUFFICIENT_SESSION_HISTORY'
                elif first is None or last is None or first['state']!='ACTUAL_TRADED' or last['state']!='ACTUAL_TRADED': reason='MISSING_OR_SUSPENDED_ENDPOINT'
                elif any(r is None or r['state'] not in ('ACTUAL_TRADED','SUSPENDED') for r in rows): reason='UNEXPLAINED_DATA_GAP'
                elif any(r['quality']!='READY' for r in rows): reason='ADJUSTMENT_UNKNOWN'
                elif Decimal(first['mul'])!=Decimal(last['mul']) or Decimal(first['add'])!=Decimal(last['add']): reason='MIXED_ADJUSTMENT_IDENTITY'
                elif Decimal(first['close'])<=0 or Decimal(last['close'])<=0: reason='INVALID_PRICE'
                value=None if reason else float(last['close'])/float(first['close'])-1
                returns[str(h)][sid]=value
                endpoint[sid][str(h)]=dict(start_session=window[0],end_session=day,window_digest=digest(rows),start=first,end=last,unknown_reason=reason)
        inp=dict(trade_date=day,data_authority=dict(accepted_through=head['accepted_trade_date'],head=source_refs[5],chain=chain_ref),universe_identity=dict(producer_sha=context['identity']['binding']['sha256'],members_digest=digest(members),policy=contract['membership_policy']),calendar_identity=context['calendar']['publication_id'],cutoff_timestamp=timestamp,algorithm_identity=algorithm_identity,source_revision=digest(source_refs),sessions=sessions,universe=members,returns=returns,endpoint_evidence=endpoint,source_bindings=dict(bounded_price_rows=binding(ROOT,raw_path),accepted_sources=source_refs))
        input_path=directory/('INPUT_'+day+'_'+digest(inp)+'.json');immutable_json(input_path,inp);input_refs[day]=binding(ROOT,input_path)
        publication=publish(inp,previous); pubpath=directory/('PUBLICATION_'+day+'_'+publication['logical_digest']+'.json');immutable_json(pubpath,publication)
        publications[day]=publication;publication_refs[day]=binding(ROOT,pubpath);previous=publication_refs[day]
        mismatch=0
        for h in (5,20):
            oracle=oracle_scores(returns[str(h)],members)
            mismatch+=sum(row[f'rps{h}']['value']!=oracle[row['security_id']] for row in publication['rows'])
        independent.append(dict(trade_date=day,score_values_checked=2*len(members),rank_mismatches=mismatch,unknown_reasons=dict(Counter(e[str(h)]['unknown_reason'] for e in endpoint.values() for h in (5,20) if e[str(h)]['unknown_reason']))))
    delta_mismatches=0
    for day in targets:
        for offset in (1,3):
            index=sessions.index(day);prior=publications.get(sessions[index-offset]) if index>=offset else None
            rows=delta(publications[day],prior,offset,sessions)
            priors={r['security_id']:r for r in prior['rows']} if prior else {}
            for row in rows:
                now=next(r for r in publications[day]['rows'] if r['security_id']==row['security_id'])
                for h in (5,20):
                    field=row['fields'][f'rps{h}_delta{offset}'];old=priors.get(row['security_id'],{}).get(f'rps{h}',{}).get('value');current=now[f'rps{h}']['value']
                    expected=None if field['unknown_reason'] else current-old
                    delta_mismatches+=field['value']!=expected
            path=directory/f'DELTA_{day}_T_MINUS_{offset}_{digest(rows)}.json';immutable_json(path,dict(trade_date=day,offset=offset,rows=rows));delta_refs[f'{day}:T-{offset}']=binding(ROOT,path)
    replay=downstream_replay(publications,delta_refs,timestamp,directory)
    evidence=dict(contract_id='A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R1',baseline_head=entry['baseline_commit'],audit='V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01',status='A02_PRIOR_RPS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',batch_status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',contract=binding(ROOT,ROOT/'config/a02_rps_pit_history_v1.json'),shared_entry=binding(ROOT,ROOT/'reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json'),publications=publication_refs,inputs=input_refs,deltas=delta_refs,independent_rank_oracle=independent,independent_delta_mismatches=delta_mismatches,downstream_replay=replay,real_input_proof='Accepted R7 bounded history plus exact externally accepted DM01 chain, date-effective accepted identity projection and accepted calendar.',historical_first_availability_proven=False,AS_RECORDED=False,first_computable_publication='2026-09-22',first_delta1_publication='2026-09-23',first_delta3_publication='2026-09-28',warmup_rule='No source outside frozen publications is reconstructed by the consumer; 9/22 missing priors remain UNKNOWN.',formal_consumer_enabled=False,accepted_head_changed=False,production=False,shadow=False,focus_cutover=False,remaining_external_gate='Independent external audit of candidate RPS chain and V4-05/V4-07/V4-09 amendment; current accepted outputs remain immutable.',engineering_gate='PASS' if not delta_mismatches and all(not r['rank_mismatches'] for r in independent) else 'BLOCKED')
    immutable_json(ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R1.json',evidence)
    print(json.dumps(dict(status=evidence['status'],rank_mismatch=sum(r['rank_mismatches'] for r in independent),delta_mismatch=delta_mismatches,seed_counts=replay['new_seed_counts'],stock_business_changed=replay['stock_business_changed'])))

def downstream_replay(publications,delta_refs,timestamp,directory,revision='R1'):
    oldcontext,cores,factors=_load_accepted_source_context(ROOT)
    oldseed=build_candidate_from_records(cores,factors,oldcontext,created_at=timestamp)
    v409ctx,_,_,_,package=load_accepted(ROOT)
    oldstock=stock_build(cores,factors,oldseed['rows'],v409ctx,package)
    day=oldcontext['trade_date'];deltas=read_bound(ROOT,delta_refs[day+':T-3']);idx={r['security_id']:r for r in deltas['rows']}
    newcores=deepcopy(cores);newfactors=deepcopy(factors)
    profile_namespace='A02_V405_AMENDMENT_CANDIDATE_R2:'+digest(dict(source=oldcontext['profile_row_publication_id'],rps=publications[day]['logical_digest']))
    seed_namespace='A02_V407_AMENDMENT_CANDIDATE_R2:'+digest(dict(source=oldcontext['publication_id'],profile=profile_namespace))
    for core,factor in zip(newcores,newfactors):
        sid=core['security_id']; field=deepcopy(factor['fields']['rps5_delta3']);value=idx.get(sid,{}).get('fields',{}).get('rps5_delta3',dict(value=None,quality_state='UNKNOWN',unknown_reason='PRIOR_UNIVERSE_MEMBER_MISSING'))
        field.update(value=value['value'],quality_state=value['quality_state'],unknown_reason=value['unknown_reason'],available_at=timestamp,input_digest=digest(value),output_digest=digest(dict(value=value['value'],lineage=value)),window_identity=digest(dict(lineage=value,publication=publications[day]['logical_digest'])))
        factor['fields']['rps5_delta3']=field;core['primitive_quality']['rps5_delta3']=deepcopy(field)
        # This is a new amendment candidate, with actual present availability.
        factor['formal_publication_at']=timestamp;core['formal_publication_at']=timestamp
        if revision=='R2':
            for row in (core,factor):
                row['original_accepted_publication_id']=row.get('publication_id')
                row['publication_id']=profile_namespace
                row['candidate_only']=True
                row['a02_rps_publication_digest']=publications[day]['logical_digest']
    corepath=directory/f'V4_05_CORE_AMENDMENT_CANDIDATE_{revision}.jsonl.gz';factorpath=directory/f'V4_05_FACTOR_AMENDMENT_CANDIDATE_{revision}.jsonl.gz'
    write_immutable_gzip_jsonl(corepath,newcores);write_immutable_gzip_jsonl(factorpath,newfactors)
    newcontext=deepcopy(oldcontext);core_digest=digest(newcores);newcontext['core_logical_digest']=core_digest
    newcontext['source_bindings'].update(core_logical_digest=core_digest,core_profile_artifact_sha256=binding(ROOT,corepath)['sha256'],full_scope_factors_artifact_sha256=binding(ROOT,factorpath)['sha256'],full_scope_factors_logical_digest=digest(newfactors))
    newcontext['source_bindings']['candidate_amendment_only']=True
    if revision=='R2':
        newcontext['publication_id']=seed_namespace;newcontext['profile_row_publication_id']=profile_namespace
        newcontext['source_bindings'].update(publication_id=seed_namespace,profile_row_publication_id=profile_namespace,original_accepted_publication_id=oldcontext['publication_id'])
    newseed=build_candidate_from_records(newcores,newfactors,newcontext,created_at=timestamp)
    stockcontext=deepcopy(v409ctx);stockcontext['core_logical_digest']=core_digest;stockcontext['knowledge_cutoff']=timestamp
    if revision=='R2':
        stockcontext['source_publication_id']=seed_namespace;stockcontext['profile_row_publication_id']=profile_namespace
    stockcontext['source_bindings'].update(core_profile=binding(ROOT,corepath),factors=binding(ROOT,factorpath),core_logical_digest=core_digest,seed_logical_digest=newseed['logical_digest'],candidate_amendment_only=True)
    newstock=stock_build(newcores,newfactors,newseed['rows'],stockcontext,package)
    seeds=directory/f'V4_07_FULL_AMENDMENT_REPLAY_{revision}.jsonl.gz'; stocks=directory/f'V4_09_FULL_AMENDMENT_REPLAY_{revision}.jsonl.gz'
    write_immutable_gzip_jsonl(seeds,[dict(security_id=a['security_id'],old=a,new=b) for a,b in zip(oldseed['rows'],newseed['rows'])])
    write_immutable_gzip_jsonl(stocks,[dict(security_id=a['security_id'],old=a,new=b) for a,b in zip(oldstock,newstock)])
    seed_business=['base_seed_state','matched_seed_paths','domain_states','waiting_for','invalid_if','quality','quality_codes','seed_participation_annotation']
    stock_business=['base_seed_state','mandatory_core_quality_ready','raw_qualification','emergence_axis','structure_quality_axis','risk_axis','priority_bucket','priority_sort_key','waiting_for','quality']
    diff=[]
    for package_name,old,new,fields in [('V4_07',oldseed['rows'],newseed['rows'],seed_business),('V4_09',oldstock,newstock,stock_business)]:
        for a,b in zip(old,new):
            changed={k:dict(old=a[k],new=b[k]) for k in fields if a[k]!=b[k]}
            diff.append(dict(package=package_name,security_id=a['security_id'],business_changes=changed))
    diffpath=directory/f'FULL_BUSINESS_DIFF_{revision}.jsonl.gz';write_immutable_gzip_jsonl(diffpath,diff)
    return dict(scope='Full 5222 accepted 9/28 identities; old UNKNOWN branch and real RPS candidate amendment inputs; algorithms and parameters frozen.',actual_available_at=timestamp,amendment_not_accepted=True,seed_rows=len(newseed['rows']),stock_rows=len(newstock),seed_business_changed=sum(bool(r['business_changes']) for r in diff if r['package']=='V4_07'),stock_business_changed=sum(bool(r['business_changes']) for r in diff if r['package']=='V4_09'),old_seed_counts=oldseed['state_counts'],new_seed_counts=newseed['state_counts'],artifacts=[binding(ROOT,p) for p in (corepath,factorpath,seeds,stocks,diffpath)],source_context=oldcontext,new_seed_context=newcontext,new_stock_context=stockcontext,parameter_bindings=[binding(ROOT,ROOT/'config/v4_07_parameter_set_v1.json'),binding(ROOT,ROOT/'config/v4_09_parameter_set_v1.json')])

if __name__=='__main__': main()
