"""Four-date operational TDX reprojection, retaining original numeric kernels."""
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from copy import deepcopy
from sector.native_r5 import build_native
from sector.rotation_r5 import advance_rotation, evaluate_b0, resolve_package
from .v4_13_descendant_contracts import DescendantContracts
from .v4_13_loo_runtime import relative_sector
from .corrected_owner_replay import load, checked, gzrows, gzwrite, ref, OUT
from .market_source_acquisition import write, official_sessions
from .tdx_member_retro_r43 import EVIDENCE, capture, metadata, validate_snapshot, digest
from .rotation_reconstructed_r43 import advance as advance_reconstructed
from v4.base_seed import _normalize_facts,evaluate_facts,_known,_unknown


def run(root):
    root=Path(root).resolve();out=root/EVIDENCE;target=out/'sector_v3';s=capture(root)
    members=validate_snapshot(s,root);meta=lambda d:metadata(s,d)
    replay=load(out/'owner_v3/PROFILE_STRUCTURE_REPLAY.json');old=load(root/OUT/'SECTOR_REPLAY.json')
    params=load(root/'config/v4_08_algorithm_parameter_set_r5.json');p={x['parameter_id']:x['value'] for x in params['parameters']}
    c=DescendantContracts(root);dep=c.dependencies
    rotation_params,_=resolve_package(dep['rotation_contract'],dep['parameter_set'],checked(root,c.config['loo_context']['accepted_sector_dependencies']['parameter_set']).read_bytes(),dep['field_registry'])
    sessions=official_sessions(root);receipts=[];history={};oracles=[]
    write(out/'W4_STAGE_CONTRACT.json',dict(contract_id='TDX_LATEST_MEMBER_RETRO_SECTOR_V1',upgrade='R4.3 W4',
        contract=ref(root,root/'config/v4_tdx_latest_member_retro_sector_r43_v1.json'),
        source=ref(root,out/'MEMBER_SNAPSHOT_S.json'),kernel=ref(root,root/'src/sector/native_r5.py'),
        relative_aggregation='ALL memberships required KNOWN; select best original RELATIVE_STATE_V1 state by frozen precedence then sector_id; retain every original kernel envelope',
        production_scope='DATED_OPERATIONAL_RESEARCH_REPROJECTION_ONLY',strict_pit=False,acceptance='IN_PROGRESS',next_stage='INDEPENDENT_NUMERIC_QA'))
    for item in replay['owners']:
        owner=item['owner'];day=owner['trade_date'];folder=target/day
        factors={r['security_id']:r for r in gzrows(checked(root,owner['core']))};profiles={r['security_id']:r for r in gzrows(checked(root,owner['profiles']))}
        raw={r['security_id']:r for r in gzrows(checked(root,owner['raw']))};adjusted={r['security_id']:r for r in gzrows(checked(root,owner['adjusted']))}
        # Exact preserved stock-only Seed values were independently replayed in R4.2.1.
        oldsector=next(r for r in old['owners'] if r['trade_date']==day);seedbinding=oldsector['seed']
        seedrows=gzrows(checked(root,seedbinding));seed={r['security_id']:True if r['base_seed_state']=='TRUE' else False if r['base_seed_state']=='FALSE' else None for r in seedrows}
        savedseed={r['security_id']:r['base_seed_state'] for r in seedrows}
        priorcore={r['security_id']:r for r in gzrows(checked(root,owner['prior_core']))}
        stockhist={r['security_id']:{b['trade_date']:b for b in r['bars']} for r in gzrows(checked(root,owner['history']))}
        board_counts=dict(Counter(r['board_scope'] for r in factors.values()));prior_day=sessions[sessions.index(day)-1]
        seedparams=load(root/'config/v4_07_parameter_set_v1.json');seedmatched=0;newseedrows=[];seedchanges=[];oldseedbinding=seedbinding
        for sid,f in factors.items():
            profile=dict(profiles[sid],historical_as_recorded_claim=False)
            facts=_normalize_facts(profile,f,dict(trade_date=day,expected_board_counts=board_counts,profile_row_publication_id=profile['publication_id']))
            pc=priorcore.get(sid,{}).get('fields',{}).get('ma20',{});pb=stockhist[sid].get(prior_day)
            facts['ma20_t_minus_1']=_known(pc['value']) if pc.get('quality_state')=='OBSERVED' else _unknown('EXACT_PRIOR_CORE_MA20_UNKNOWN')
            facts['close_t_minus_1']=_known(pb['qfq_ohlc'][3]) if pb and pb['qfq_ohlc'] else _unknown('EXACT_PRIOR_ADJUSTED_CLOSE_UNKNOWN')
            result=evaluate_facts(facts,seedparams);state=result['base_seed_state']
            if state!=savedseed[sid]:seedchanges.append(dict(security_id=sid,old=savedseed[sid],new=state,reason='New verified dated Profile source adaptation; no member input'))
            else:seedmatched+=1
            newseedrows.append(dict(security_id=sid,trade_date=day,**result,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,stock_only=True))
        seedbinding=gzwrite(root,folder/'base_seed.jsonl.gz',newseedrows)
        seed={r['security_id']:True if r['base_seed_state']=='TRUE' else False if r['base_seed_state']=='FALSE' else None for r in newseedrows}
        current={}
        for sid,f in factors.items():
            fields={k:dict(value=v.get('value'),quality='ACCEPTED' if v.get('quality_state')=='OBSERVED' else 'UNKNOWN',max_source_date=day) for k,v in f['fields'].items()}
            close=adjusted.get(sid,{}).get('close');ma=f['fields']['ma20']['value']
            for key,value in [('amount',raw.get(sid,{}).get('amount')),('close',close),('close_minus_ma20',close-ma if close is not None and ma is not None else None),('mdd20',profiles[sid]['derived_fields'].get('mdd20',{}).get('value'))]:
                fields[key]=dict(value=value,quality='ACCEPTED' if value is not None else 'UNKNOWN',max_source_date=day)
            current[sid]=dict(trade_date=day,fields=fields,price_basis_id=f['price_basis_id'])
        eligible=[];excluded=[];groups=defaultdict(list);allgroups=defaultdict(list)
        for m in members:
            allgroups[m['sector_id']].append(m)
            reason='UNMAPPED_IDENTITY' if not m['security_id'] else 'NOT_LISTED_AT_TARGET' if not m['list_date'] or m['list_date']>day else 'DELISTED_AT_TARGET' if m['delist_date'] and m['delist_date']<=day else 'NO_TARGET_CANONICAL_IDENTITY' if m['security_id'] not in factors else None
            if reason:excluded.append(dict(**m,reason=reason));continue
            row=dict(m,snapshot_id=s['membership_snapshot_id'],target_trade_date=day,**meta(day))
            eligible.append(row);groups[m['sector_id']].append(m['security_id'])
        sources=dict(core=owner['core'],profiles=owner['profiles'],membership_snapshot=ref(root,out/'MEMBER_SNAPSHOT_S.json'),seed=seedbinding)
        prior={};prior_members={};prior_dates={};prior_native={};prior_seed={}
        histrows={r['security_id']:{b['trade_date']:b for b in r['bars']} for r in gzrows(checked(root,owner['history']))}
        for k in (1,3):
            d=sessions[sessions.index(day)-k]
            if d in history:
                h=history[d];prior[k]=h['current'];prior_members[k]=h['groups'];prior_dates[k]=d;prior_native[k]=h['native'];prior_seed[k]=h['seed']
            else:
                # Recompute real price endpoints before the four-day window
                # from the sealed actual history, never fabricate episode state.
                endpoint={};idx=sessions.index(d)
                for sid,bars in histrows.items():
                    fields={};close=bars.get(d,{}).get('qfq_ohlc')
                    close=close[3] if close else None
                    for n in (1,5,20,60):
                        before=bars.get(sessions[idx-n],{}).get('qfq_ohlc');value=close/before[3]-1 if close is not None and before and before[3]>0 else None
                        fields['ret'+str(n)]=dict(value=value,quality='ACCEPTED' if value is not None else 'UNKNOWN',max_source_date=d)
                    window=[bars.get(date,{}) for date in sessions[idx-19:idx+1]]
                    closes=[b['qfq_ohlc'][3] for b in window if b.get('qfq_ohlc')]
                    ma=sum(closes)/20 if len(closes)==20 else None
                    for field,value in [('close',close),('close_minus_ma20',close-ma if close is not None and ma is not None else None),('amount',bars.get(d,{}).get('amount'))]:
                        fields[field]=dict(value=value,quality='ACCEPTED' if value is not None else 'UNKNOWN',max_source_date=d)
                    endpoint[sid]=dict(trade_date=d,fields=fields,price_basis_id=factors[sid]['price_basis_id'])
                endpoint_members=[dict(m,target_trade_date=d,trade_date=d) for m in eligible if m['list_date']<=d and (not m['delist_date'] or m['delist_date']>d)]
                endpoint_groups=defaultdict(list)
                for m in endpoint_members:endpoint_groups[m['sector_id']].append(m['security_id'])
                prior[k]=endpoint;prior_members[k]=dict(endpoint_groups);prior_dates[k]=d
                endpoint_native=[]
                for derived_parent in (False,True):
                    scope=[m for m in endpoint_members if ('DERIVED_PARENT' in m['source'])==derived_parent]
                    endpoint_native.extend(build_native(scope,endpoint,target=d,snapshot_id=s['membership_snapshot_id'],publication_id='R43_ENDPOINT:'+d,
                        parameter_set=params,source_bindings=sources,seed={},seed_capability=False))
                prior_native[k]={n['sector_id']:n for n in endpoint_native}
        pid='R43_TDX_RETRO:'+digest(dict(day=day,s=s['member_digest'],sources=sources,params=params))
        natives=[]
        for derived_parent in (False,True):
            # Parent hierarchy is a separately ranked explanatory population;
            # it never changes the original leaf industry/mainline ranks.
            scope=[m for m in eligible if ('DERIVED_PARENT' in m['source'])==derived_parent]
            natives.extend(build_native(scope,current,target=day,snapshot_id=s['membership_snapshot_id'],publication_id=pid,parameter_set=params,
                source_bindings=sources,prior=prior,prior_memberships=prior_members,prior_date=prior_dates,prior_sector_rows=prior_native,
                seed=seed,seed_capability=True,prior_seed=prior_seed))
        for n in natives:
            n.update(meta(day));ids=n['member_ids'];allm=allgroups[n['sector_id']]
            n.update(current_member_count=len(allm),target_date_eligible_count=len(ids),quoted_count=sum(sid in raw for sid in ids),unmapped_count=sum(not m['security_id'] for m in allm),
                industry_level='PARENT_DERIVED' if all('DERIVED_PARENT' in m['source'] for m in allm) else 'LEAF' if n['sector_type']=='INDUSTRY' else 'CONCEPT',
                primary_industry_rank_eligible=not all('DERIVED_PARENT' in m['source'] for m in allm),
                missing_bar_reason=dict(Counter('NO_RAW_BAR_STATUS_REQUIRED' for sid in ids if sid not in raw)))
            for field in n['fields'].values():field.update(meta(day));field['quality']='PROXY_RECONSTRUCTED' if field['value'] is not None else 'UNKNOWN'
        native_checks=0
        for n in natives:
            for field,source,predicate in [('breadth_ret1','ret1',lambda x:x>0),('ma20_width','close_minus_ma20',lambda x:x>0)]:
                values=[current[sid]['fields'][source]['value'] for sid in n['member_ids'] if current[sid]['fields'][source]['value'] is not None and current[sid]['fields'][source]['quality']=='ACCEPTED']
                expected=sum(predicate(v) for v in values)/len(values) if values else None
                assert n['fields'][field]['value']==expected
                native_checks+=1
        # Preserve accepted numeric quality for the unchanged rotation evaluator.
        computational=deepcopy(natives)
        for n in computational:
            for f in n['fields'].values():
                if f['value'] is not None:f['quality']='ACCEPTED'
        rotations=[];nativeby={r['sector_id']:r for r in computational}
        previous=sessions[sessions.index(day)-1];prev=history.get(previous)
        for n in computational:
            strict=advance_rotation(n,current,prior_publication=None,prior_members=prev['groups'].get(n['sector_id']) if prev else None,
                prior_core=prev['current'] if prev else {},calendar_sessions=sessions,contract=dep['rotation_contract'],registry=dep['field_registry'],parameters=rotation_params,seed_truth=seed,seed_capability=True)
            r=advance_reconstructed(n,current,previous=prev['rotation'].get(n['sector_id']) if prev else None,
                prior_native=prior_native.get(1,{}).get(n['sector_id']),prior_members=prior_members.get(1,{}).get(n['sector_id']),
                prior_core=prior.get(1,{}),prior_date=previous,calendar_sessions=sessions,contract=dep['rotation_contract'],registry=dep['field_registry'],parameters=rotation_params,seed_truth=seed)
            r.update(meta(day))
            for field in r['fields'].values():field.update(meta(day))
            rotations.append(dict(sector_id=n['sector_id'],rotation=r,strict_historical_rotation=strict,b0=evaluate_b0(n,dep['b0_contract'],rotation_params),**meta(day)))
        bystock=defaultdict(list)
        for m in eligible:bystock[m['security_id']].append(m['sector_id'])
        loo=[];oracle_sectors=set();oracle_types=Counter()
        for sid in sorted(factors):
            f=factors[sid]['fields'];profile=profiles[sid];stock={k:f.get(k,{}).get('value') for k in ('rps5','rps20','rps20_delta3')}
            stock.update(stock_ret1=f['ret1']['value'],stock_ret5=f['ret5']['value'],compression_state=profile['states']['compression_state']['value'],ma_structure_state=profile['states']['ma_structure_state']['value'])
            contexts=[]
            # Stock formal relative-sector contexts use original leaf industry
            # and all concepts; explanatory parent hierarchy is separately shown.
            for sector in sorted(x for x in bystock[sid] if not all('DERIVED_PARENT' in m['source'] for m in allgroups[x])):
                others=[x for x in groups[sector] if x!=sid]
                known={k:[current[x]['fields'][k]['value'] for x in others if current[x]['fields'][k]['quality']=='ACCEPTED' and current[x]['fields'][k]['value'] is not None] for k in ('ret1','ret5')}
                n=dict(rank_eligible=len(others)>=p['V4_08_SECTOR_MIN_MEMBERS'] and bool(others) and len(known['ret1'])/len(others)>=p['V4_08_SECTOR_MIN_QUOTE_COVERAGE'],fields={'sector_rs'+k[3:]:dict(value=median(v) if v else None) for k,v in known.items()})
                value=relative_sector(stock,current[sid],day,n)
                contexts.append(dict(sector_id=sector,excluded_target_id=sid,non_target_member_count=len(others),**value,**meta(day)))
                typ=sector.split(':')[0]
                if oracle_types[typ]<5 and sector not in oracle_sectors:
                    sample=[m for m in eligible if m['sector_id']==sector and m['security_id']!=sid]
                    oracle=build_native(sample,{x:current[x] for x in others},target=day,snapshot_id=s['membership_snapshot_id'],publication_id=pid+':ORACLE',parameter_set=params,source_bindings=sources,seed={x:seed[x] for x in others},seed_capability=True)[0]
                    assert n['rank_eligible']==oracle['rank_eligible']
                    assert all(n['fields'][k]['value']==oracle['fields'][k]['value'] for k in ('sector_rs1','sector_rs5'))
                    independent={}
                    for k,values in known.items():
                        values=sorted(values);length=len(values)
                        expected=None if not length else values[length//2] if length%2 else (values[length//2-1]+values[length//2])/2
                        assert expected==n['fields']['sector_rs'+k[3:]]['value'];independent[k]=expected
                    oracles.append(dict(trade_date=day,security_id=sid,sector_id=sector,others=len(others),values=n['fields'],independent_sorted_middle=independent,
                        t_minus_1=sessions[sessions.index(day)-1],t_minus_3=sessions[sessions.index(day)-3],passed=True))
                    oracle_sectors.add(sector)
                    oracle_types[typ]+=1
            knownall=bool(contexts) and all(c['quality']=='KNOWN' for c in contexts)
            order={state:i for i,state in enumerate(('ACTIVE_EMERGENCE','LEADING_ACCELERATING','LEADING_STABLE','IMPROVING','PASSIVE_RESILIENCE','NEUTRAL','WEAKENING','LAGGING'))}
            chosen=min(contexts,key=lambda x:(order.get(x['value'],99),x['sector_id'])) if knownall else None
            value=chosen['value'] if chosen else None
            loo.append(dict(security_id=sid,value=value if knownall else None,quality='KNOWN' if knownall else 'UNKNOWN',reason=None if knownall else 'REQUIRED_TDX_LOO_CONTEXT_UNKNOWN',
                memberships=contexts,selected_sector_id=chosen['sector_id'] if chosen else None,
                aggregation_contract='TDX_MULTIMEMBERSHIP_ALL_KNOWN_BEST_RELATIVE_STATE_V1',**meta(day)))
        looby={r['security_id']:r for r in loo};enriched=[]
        for sid,profile in profiles.items():
            row=deepcopy(profile);relative=looby[sid]
            row['states']['relative_sector_state']=dict(value=relative['value'] if relative['quality']=='KNOWN' else 'UNKNOWN',
                quality='PROXY_RECONSTRUCTED' if relative['quality']=='KNOWN' else 'UNKNOWN',reason_code=relative['reason'],
                selected_sector_id=relative['selected_sector_id'],producer_contract_id=relative['aggregation_contract'],**meta(day))
            row['tdx_sector_memberships']=relative['memberships'];row['tdx_membership_lineage']=meta(day)
            row['profile_enrichment_contract_id']='R43_TDX_OPERATIONAL_RELATIVE_PROFILE_ENRICHMENT_V1'
            enriched.append(row)
        receipt=dict(**meta(day),publication_id=pid,source_bindings=sources,
            native=gzwrite(root,folder/'native.jsonl.gz',natives),relative_sector=gzwrite(root,folder/'relative_sector_loo.jsonl.gz',loo),
            enriched_profiles=gzwrite(root,folder/'profiles_with_tdx_relative.jsonl.gz',enriched),
            rotation=gzwrite(root,folder/'rotation.jsonl.gz',rotations),seed=seedbinding,
            excluded_members=gzwrite(root,folder/'excluded_members.jsonl.gz',excluded),membership_count=len(eligible),sector_count=len(natives),
            known_fields=dict(Counter(k for n in natives for k,f in n['fields'].items() if f['value'] is not None)),
            stock_only_seed_reuse=dict(old_binding=oldseedbinding,new_binding=seedbinding,new_core=owner['core'],new_profiles=owner['profiles'],numerical_matches=seedmatched,rows=len(factors),changes=seedchanges),
            independent_native_width_breadth_checks=native_checks,
            relative_sector_known=sum(r['quality']=='KNOWN' for r in loo),rotation_counts=dict(Counter(r['rotation']['output_state'] for r in rotations)),b0_counts=dict(Counter(r['b0']['output_state'] for r in rotations)))
        receipts.append(receipt);history[day]=dict(current=current,groups=dict(groups),native=nativeby,seed=seed,rotation={r['sector_id']:r['rotation'] for r in rotations})
        print(day,len(natives),receipt['relative_sector_known'],flush=True)
    result=dict(owners=receipts,source_snapshot=ref(root,out/'MEMBER_SNAPSHOT_S.json'),oracle=oracles,acceptance='FOUR_DAY_RETRO_SECTOR_PASS',strict_historical_pit='NOT_GRANTED',production_admission='INDEPENDENT_QA_REQUIRED')
    write(target/'SECTOR_REPLAY.json',result);write(out/'06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json',result)
    return result

