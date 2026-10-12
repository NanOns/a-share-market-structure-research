"""Hash-bound R4 candidate D0/D2 and real Focus/Forward replay.

Uses the exact legacy scanner and R5 candidate reducer. New source admission is
local to this explicit corrected namespace; no accepted authority is rewritten.
"""
import gzip
import json
import math
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .r43_owner_replay import load, checked, gzrows, gzwrite, ref, OUT
from .market_source_acquisition import write, official_sessions
from .tdx_official_daily_source import _atomic_write
from .research_features import build_stock_research_features, ResearchFeatureContext
from v4.target_fact_producers_r4 import produce
from v4 import confirmation as d0
from v4 import confirmation_d2_candidate_r5 as d2
from v4.stock_prewatch import load_package, evaluate
from v4.state_identity import digest
from market_calendar.trading_calendar import StockTimeline
from normalize.universe_recent import qualifies_normal_universe


def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list):return [clean(v) for v in x]
    if x is pd.NA or isinstance(x,float) and not math.isfinite(x):return None
    if hasattr(x,'item'):return clean(x.item())
    return x


def confirmation(values):
    _,manifest,_,machine,scanner=d0.package();legacy=scanner(values);evidence=[];matches=[];unknown=[]
    for scenario in machine['scenario_priority']:
        branch=legacy[d0.SCENARIO_KEYS[scenario]];checks=branch['checks']
        reasons=[k+':UNKNOWN' for k,v in checks.items() if v is None]
        if scenario=='TREND_CONTINUE':reasons.append('CURRENT_WITH_LOO_BREADTH_SUPPORT:SAME_DAY_DOWNSTREAM_DIAGNOSTIC_ONLY')
        state='UNKNOWN' if reasons else 'TRUE' if branch['eligible'] is True else 'FALSE'
        if state=='TRUE':matches.append(scenario)
        unknown.extend(scenario+':'+r for r in reasons)
        evidence.append(dict(scenario=scenario,status=state,checks=checks,unknown_reasons=reasons))
    return dict(confirmation_status='TRUE' if matches else 'UNKNOWN' if unknown else 'FALSE',
         primary_scenario=matches[0] if matches else None,matched_scenarios=matches,
         scenario_evidence=evidence,source_sha256=manifest['legacy_source']['sha256'])


def materialize_focus(root):
    root=Path(root).resolve();out=root/OUT;replay=load(out/'PROFILE_STRUCTURE_REPLAY.json');sectors=load(root/'docs/evidence/r4_3_four_session_closeout_20261009/sector_v3/SECTOR_REPLAY.json')
    sessions=official_sessions(root);cutoff=datetime.now(timezone.utc).isoformat();prior=None;prior_pid=None;days={};receipts=[]
    contract=out/'FOCUS_STAGE_CONTRACT_V1.json'
    write(contract,dict(contract_id='V4_R4_CORRECTED_D0_D2_FOCUS_FORWARD_V1',task='R4.3',
        source_admission='Exact R4 sealed owner files; corrected candidate only',
        D0='Original scanner/parameters/priority and UNKNOWN-dominant wrapper',
        D2='Unchanged R5 candidate reducer and full field/temporal/publication validator',
        focus='Original membership/path/outcome kernels; independent corrected namespace',
        accepted=False,AS_RECORDED=False,production_admission=False,
        exact_business_AST=d2.adapter_ast_evidence()))
    membership=load(checked(root,load(out/'SOURCE_BINDINGS.json')['sources']['latest_tdx_member_snapshot']))
    metadata={k:membership[k] for k in ('membership_mode','taxonomy','membership_snapshot_id','membership_observed_at','member_set_asof','knowledge_lineage','AS_RECORDED','PIT_ELIGIBLE','HISTORICAL_FIRST_AVAILABLE_PROVEN','production_eligible_scope','survivorship_bias_risk')}
    cfg=load(root/'config/research_attention_v3.yaml');package=load_package(root)
    cal=dict(session_dates=sessions,sessions=[dict(trade_date=d,session_index=i) for i,d in enumerate(sessions)],
          lineage_id='R4_OFFICIAL_MASTER_CALENDAR',producer_contract_id='MARKET_CALENDAR_V1')
    cal['publication_id']='R4_CALENDAR:'+digest(cal);write(out/'FOCUS_CALENDAR.json',cal)
    acquisition=load(root/'docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json')
    sources=load(out/'SOURCE_BINDINGS.json')['sources'];pathstatus={};allbars={};native={};mainline_context={}
    for item,sector in zip(replay['owners'],sectors['owners']):
        owner=item['owner'];day=owner['trade_date'];folder=out/'owners'/day
        factors=gzrows(checked(root,owner['core']));profiles={r['security_id']:r for r in gzrows(checked(root,owner['profiles']))}
        seeds={r['security_id']:r for r in gzrows(checked(root,sector['seed']))}
        relative_rows={r['security_id']:r for r in gzrows(checked(root,sector['relative_sector']))}
        mainline_context[day]={sid:dict(**metadata,trade_date=day,relative_sector_state=r['value'],quality=r['quality'],reason=r['reason'],selected_sector_id=r.get('selected_sector_id'),all_member_sector_ids=[m['sector_id'] for m in r.get('memberships',[])],source_refs=[sector['relative_sector'],sources['latest_tdx_member_snapshot']],meaning='TDX industry/concept LOO association for retrospective research; not historical T0 selection') for sid,r in relative_rows.items()}
        history={r['security_id']:r['bars'] for r in gzrows(checked(root,owner['history']))}
        rs=[];rawfeatures=[];windows={};window=sessions[max(0,sessions.index(day)-119):sessions.index(day)+1]
        for factor in factors:
            sid=factor['security_id'];by={b['trade_date']:b for b in history[sid]};slots=[]
            for date in window:
                b=by.get(date,{});q=b.get('qfq_ohlc');r=b.get('raw_ohlc')
                slot=dict(date=date,session_index=sessions.index(date),has_actual_bar=q is not None,raw_actual_bar=r is not None,
                    amount=b.get('amount'),volume=b.get('volume'),anchor_cutoff=day,is_synthetic_fill=False,
                    adjustment_basis_id=factor['price_basis_id'],price_basis='TDX_NATIVE_AFFINE_QFQ')
                for i,k in enumerate(('open','high','low','close')):
                    slot[k]=q[i] if q else None;slot['raw_'+k]=r[i] if r else None
                slots.append(slot)
                rawfeatures.append(dict(security_id=sid,trade_date=date,adj_close=slot['close'],raw_amount=slot['amount'],
                   has_actual_bar=r is not None,price_basis='TDX_NATIVE_QFQ',
                   adjustment_status='VERIFIED_REPRODUCIBLE_TDX_NATIVE' if q else 'UNKNOWN',
                   project_price_basis='FORWARD_ADJUSTED',adjustment_version=factor['price_basis_id']))
            windows[sid]=slots;f=factor['fields'];prior3=sessions[sessions.index(day)-3]
            rs.append(dict(security_id=sid,trade_date=day,rps5=f['rps5']['value'],rps20=f['rps20']['value']))
            # Endpoint reconstructed from the saved original score and its exact delta;
            # this is arithmetic readback, not an independently observed new score.
            rs.append(dict(security_id=sid,trade_date=prior3,
                rps5=f['rps5']['value']-f['rps5_delta3']['value'] if f['rps5']['value'] is not None and f['rps5_delta3']['value'] is not None else None,rps20=None))
        features=build_stock_research_features(pd.DataFrame(rawfeatures),pd.DataFrame(rs),window,
            ResearchFeatureContext('R4','R4:'+day,owner['source_digest'],'NO_SECTOR_SUBSTITUTION',cal['publication_id'],day),
            liquidity20_amount_gte=cfg['thresholds']['stock_signals']['risk']['liquidity20_amount_gte'])
        features={r['security_id']:clean(r) for r in features.to_dict('records')};factrows=[];calculations=[];statusrows=[]
        for factor in factors:
            sid=factor['security_id'];f=factor['fields'];p=profiles[sid];feature=features[sid]
            for key in ('rps5','rps20','rps5_delta3'):feature[key]=f[key]['value']/100 if f[key]['value'] is not None else None
            observed=frozenset(int(b['trade_date'].replace('-','')) for b in history[sid])
            timeline=StockTimeline(sid,min(observed),max(observed),len(observed),observed,file_exists=True,structurally_valid=True,current_member=True)
            normal,normal_evidence=qualifies_normal_universe(timeline,[int(d.replace('-','')) for d in window])
            values,signals=produce(windows[sid][-27:],feature,normal_universe=normal,identity_compatible=True,parameters=cfg)
            values.update(security_id=sid,trade_date=day);confirmed=confirmation(values)
            damage=f['core_price_damage']['value'];seed=seeds[sid]['base_seed_state']
            pf=dict(base_seed_state=seed,mandatory_core_quality_ready='TRUE' if seed!='UNKNOWN' and isinstance(damage,bool) else 'UNKNOWN',
                delta3=f['rps5_delta3']['value'],priority_lineage_failures=[],
                **{k:p['states'][k]['value'] for k in ('compression_state','ma_structure_state','core_extension_risk')})
            prewatch=evaluate(pf,package);actual=values['actual_bar'];index=sessions.index(day)
            statusrows.append(dict(security_id=sid,trade_date=day,status='ACTUAL_TRADED' if actual else 'UNKNOWN',actual_bar_present=actual,status_conflict=False))
            valueset=dict(CONFIRMED=confirmed['confirmation_status'],PREWATCH=prewatch['raw_qualification'],SEED=seed,
                core_price_damage='TRUE' if damage is True else 'FALSE' if damage is False else 'UNKNOWN',
                delta3=f['rps5_delta3']['value'] if f['rps5_delta3']['value'] is not None else 'UNKNOWN',
                risk=p['states']['core_extension_risk']['value'],scenario=confirmed['primary_scenario'] or 'UNKNOWN',
                suspended='FALSE' if actual else 'UNKNOWN')
            fields={}
            for name,definition in d2.candidate_policy()['fields'].items():
                applicable='STOCK' not in definition['not_applicable_entity_types']
                state='IMPLEMENTED' if definition['implemented'] and applicable else 'NOT_IMPLEMENTED' if applicable else 'NOT_APPLICABLE'
                if name in ('frozen_invalidation','episode_invalidation_contract_id') and (prior is None or sid not in prior):state='NOT_APPLICABLE'
                sourceindex=index if definition['time_role']=='T' else index-1
                fields[name]=d2.candidate_envelope(name,valueset.get(name,'UNKNOWN'),state,session_index=sourceindex,
                      trade_date=sessions[sourceindex],system_available_at=cutoff,publication_id='TEMP')
                fields[name].pop('publication_id')
            factrows.append(dict(entity_id=sid,entity_type='STOCK',fields=fields))
            calculations.append(clean(dict(security_id=sid,trade_date=day,confirmation=confirmed,prewatch=prewatch,
                    target_values=values,signals=signals,normal_evidence=normal_evidence)))
        manifest=d2.seal_fact_manifest(dict(contract_id='V4_R4_CORRECTED_STATE_INPUT_FACT_PUBLICATION_V1',
            trade_date=day,calendar_publication_id=cal['publication_id'],rows=factrows,
            source_bindings=[owner['core'],owner['profiles'],owner['history'],sector['seed']],accepted=False,AS_RECORDED=False))
        pid=manifest['publication_id'];entities={(r['entity_id'],r['entity_type']):r for r in factrows}
        context=dict(calendar=cal,manifests={pid:(manifest,entities)},prior_publication=None if prior is None else dict(publication_id=prior_pid),prior_rows=prior or {})
        inputs=[]
        for row in factrows:
            fields={k:dict(v,publication_id=pid if v['status']=='IMPLEMENTED' else None) for k,v in row['fields'].items()}
            inputs.append(d2.input_skeleton(entity_id=row['entity_id'],trade_date=day,session_index=sessions.index(day),cutoff=cutoff,
                calendar_manifest=cal,fields=fields,prior_state=(prior or {}).get(row['entity_id']),prior_publication_id=prior_pid))
        # This validator checks every published field, prior row, date, digest and cutoff.
        # Source-set authorization belongs to the new R4 contract above, not the old R5 seals.
        reducer=d2.extracted_runtime()[0];rows=[reducer(x,ledger=context) for x in inputs]
        for row in rows:d2.validate_candidate_output(row)
        publication=dict(**metadata,contract_id='V4_R4_CORRECTED_D2_PUBLICATION_V1',rows=rows,accepted=False,
            source_contract=ref(root,contract),fact_manifest_digest=digest(manifest))
        prior_pid='R4_D2:'+digest(publication);publication['publication_id']=prior_pid;prior={r['entity_id']:r for r in rows};days[day]=rows
        path=folder/'corrected_d2.json.gz';_atomic_write(path,gzip.compress(json.dumps(publication,ensure_ascii=False,sort_keys=True).encode(),mtime=0),tdx_root=Path('D:/new_tdx'))
        for r in calculations:r.update(metadata);r['research_mainline_context']=mainline_context[day].get(r['security_id'])
        for r in factrows:r.update(metadata)
        calc=gzwrite(root,folder/'corrected_d0_prewatch.jsonl.gz',calculations)
        fact=gzwrite(root,folder/'corrected_state_input_facts.jsonl.gz',factrows)
        write(folder/'focus_status.json',dict(rows=statusrows));pathstatus[day]=ref(root,folder/'focus_status.json')
        for sid,bars in history.items():
            for bar in bars:
                if bar['trade_date']==day:
                    allbars[(sid,day)]=dict(bar,symbol=sid)
        native[day]=dict(contract_id='R2_V4_FOCUS_NATIVE_CORE_FACTS_V1',trade_date=day,price_basis='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',factors=owner['core'],profiles=owner['profiles'])
        receipt=dict(trade_date=day,rows=len(rows),D0=dict(Counter(r['confirmation']['confirmation_status'] for r in calculations)),
             PREWATCH=dict(Counter(r['prewatch']['raw_qualification'] for r in calculations)),
             D2_freshness=dict(Counter(r['state_freshness'] for r in rows)),D2=ref(root,path),facts=fact,calculations=calc)
        receipts.append(receipt);print(json.dumps(dict(stage='D0_D2',**{k:v for k,v in receipt.items() if k in ('trade_date','rows','D0','PREWATCH','D2_freshness')})),flush=True)
    series=out/'focus_actual_bars.sqlite';temporary=Path('E:/codex_tmp/r43_focus_actual_bars.sqlite');temporary.parent.mkdir(parents=True,exist_ok=True)
    if temporary.exists():temporary.unlink()
    with sqlite3.connect(temporary) as db:
        db.execute('CREATE TABLE bars(security TEXT,day TEXT,payload TEXT,PRIMARY KEY(security,day))')
        db.executemany('INSERT INTO bars VALUES(?,?,?)',[(sid,day,json.dumps(b)) for (sid,day),b in allbars.items()])
    _atomic_write(series,temporary.read_bytes(),tdx_root=Path('D:/new_tdx'))
    for owner in native.values():owner['series']=ref(root,series)
    bindings=dict(series=ref(root,series),calendar=ref(root,out/'FOCUS_CALENDAR.json'),gbbq=sources['gbbq'],
          classification=ref(root,root/'config/v4_02_gbbq_price_impact_classification_v1.json'),status=pathstatus,native_core=native)
    from focus_tracker.v4_native_core_adapter import AcceptedPaths,enriched_project
    projection=enriched_project(days,AcceptedPaths(root,bindings))
    for episode in projection['episodes']:
        episode.update(metadata)
        episode['research_mainline_context']=mainline_context.get(episode['start_date'],{}).get(episode['entity_id'])
        for observation in episode['observations']:
            observation.update(metadata);observation['research_mainline_context']=mainline_context.get(observation['trade_date'],{}).get(episode['entity_id'])
        for outcome in episode['outcomes']:
            outcome.update(metadata);outcome['research_mainline_context']=mainline_context.get(outcome['trade_date'],{}).get(episode['entity_id'])
        for anchor in episode['anchors']:anchor.update(metadata)
    projection['research_mainline_source_bindings']=[s['relative_sector'] for s in sectors['owners']]
    projection.update(**metadata,contract_id='V4_R4_CORRECTED_FOCUS_FORWARD_CANDIDATE_V1',source_bindings=bindings,
         production_admission=False)
    path=out/'CORRECTED_FOCUS_FORWARD.json.gz'
    _atomic_write(path,gzip.compress(json.dumps(projection,ensure_ascii=False,sort_keys=True).encode(),mtime=0),tdx_root=Path('D:/new_tdx'))
    result=dict(owners=receipts,focus=ref(root,path),episodes=len(projection['episodes']),events=len(projection['events']),
          outcomes=dict(Counter(o['outcome_status'] for e in projection['episodes'] for o in e['outcomes'])),
          production_admission=False,next_stage='INDEPENDENT_QA_AND_SCOPED_RELEASE_GATE')
    write(out/'FOCUS_FORWARD_REPLAY.json',result);return result
