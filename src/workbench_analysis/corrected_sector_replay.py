"""Separate dated CSRC memberships and unchanged sector/Base-Seed/LOO kernels."""
import inspect
import json
from collections import Counter, defaultdict
from pathlib import Path
from .corrected_owner_replay import load, checked, gzrows, gzwrite, ref, OUT, CONTRACT
from .market_source_acquisition import write, official_sessions
from .v4_13_descendant_contracts import DescendantContracts
from .v4_13_loo_runtime import relative_sector
from sector.native_r5 import build_native
from v4.base_seed import _normalize_facts, evaluate_facts, _known, _unknown


def dated_industry_memberships(root, day, universe):
    root=Path(root);acquisition=load(root/'docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json')
    query=next(q for q in acquisition['queries'] if q['method']=='query_stock_industry' and q['params']=={'date':day})
    payload=load(query['path']);rows=payload['rows'];result=[];revision=query['source_revision']
    for row in rows:
        code=row['code'].lower()
        if code not in universe or not row.get('industry'):continue
        if not row.get('updateDate') or row['updateDate']>day:raise ValueError('FUTURE_OR_UNDATED_INDUSTRY_REVISION')
        if row['industryClassification']!='证监会行业分类':raise ValueError('INDUSTRY_TAXONOMY_MISMATCH')
        result.append(dict(security_id=universe[code],sector_id='BAO_CSRC:'+row['industry'].split()[0],
            sector_type='INDUSTRY',taxonomy='BAOSTOCK_CSRC_INDUSTRY',industry_name=row['industry'],
            snapshot_id=revision,target_trade_date=day,provider_revision_date=row['updateDate'],
            source_revision_id=revision,membership_basis='DATE_EFFECTIVE_RECONSTRUCTED',
            historical_first_available='UNKNOWN',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
    if len(result)!=len({r['security_id'] for r in result}):raise ValueError('DUPLICATE_DATED_INDUSTRY_MEMBER')
    return result, query


def materialize_sectors(root):
    root=Path(root).resolve();out=root/OUT;replay=load(out/'PROFILE_STRUCTURE_REPLAY.json');receipts=[];history={}
    write(out/'SECTOR_STAGE_ENTRY.json',dict(contract=ref(root,root/'config/v4_dated_membership_source_policy_v1.json'),
          upgrade_document='R4.1',acceptance='IN_PROGRESS',next_stage='LOO_FOCUS_FORWARD_INDEPENDENT_QA'))
    import baostock
    source=inspect.getsource(baostock.query_stock_industry).encode()
    from .tdx_official_daily_source import _atomic_write
    _atomic_write(out/'QUERY_STOCK_INDUSTRY_SDK_SOURCE.py',source,tdx_root=Path('D:/new_tdx'))
    params=load(root/'config/v4_08_algorithm_parameter_set_r5.json');seedparams=load(root/'config/v4_07_parameter_set_v1.json')
    sessions=official_sessions(root)
    for result in replay['owners']:
        owner=result['owner'];day=owner['trade_date'];folder=out/'owners'/day
        factors=gzrows(checked(root,owner['core']));profiles=gzrows(checked(root,owner['profiles']))
        profileby={r['security_id']:r for r in profiles};factorby={r['security_id']:r for r in factors}
        raw={r['security_id']:r for r in gzrows(checked(root,owner['raw']))};adjusted={r['security_id']:r for r in gzrows(checked(root,owner['adjusted']))}
        previous={r['security_id']:r for r in gzrows(checked(root,owner['prior_core']))}
        prior_date_value=sessions[sessions.index(day)-1]
        histories={r['security_id']:{b['trade_date']:b for b in r['bars']} for r in gzrows(checked(root,owner['history']))}
        current={};seed={};seedrows=[]
        for sid,f in factorby.items():
            p=profileby[sid];p=dict(p,historical_as_recorded_claim=False)
            context=dict(trade_date=day,expected_board_counts=dict(Counter(r['board_scope'] for r in factors)),profile_row_publication_id=p['publication_id'])
            facts=_normalize_facts(p,f,context)
            pc=previous.get(sid,{}).get('fields',{}).get('ma20',{})
            pb=histories.get(sid,{}).get(prior_date_value)
            facts['ma20_t_minus_1']=_known(pc['value']) if pc.get('quality_state')=='OBSERVED' else _unknown('EXACT_PRIOR_CORE_MA20_UNKNOWN')
            facts['close_t_minus_1']=_known(pb['qfq_ohlc'][3]) if pb and pb['qfq_ohlc'] else _unknown('EXACT_PRIOR_ADJUSTED_CLOSE_UNKNOWN')
            s=evaluate_facts(facts,seedparams)
            seed[sid]=True if s['base_seed_state']=='TRUE' else False if s['base_seed_state']=='FALSE' else None
            seedrows.append(dict(security_id=sid,trade_date=day,**s,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
            fields={k:dict(value=v.get('value'),quality='ACCEPTED' if v.get('quality_state')=='OBSERVED' else 'UNKNOWN',max_source_date=day) for k,v in f['fields'].items()}
            fields['amount']=dict(value=raw.get(sid,{}).get('amount'),quality='ACCEPTED' if sid in raw else 'UNKNOWN',max_source_date=day)
            fields['close']=dict(value=adjusted.get(sid,{}).get('close'),quality='ACCEPTED' if adjusted.get(sid,{}).get('adjustment_readiness')=='READY' else 'UNKNOWN',max_source_date=day)
            close=fields['close']['value'];ma=f['fields']['ma20']['value']
            fields['close_minus_ma20']=dict(value=close-ma if close is not None and ma is not None else None,quality='ACCEPTED' if close is not None and ma is not None else 'UNKNOWN',max_source_date=day)
            mdd=p['derived_fields'].get('mdd20',{})
            fields['mdd20']=dict(value=mdd.get('value'),quality='ACCEPTED' if mdd.get('quality')=='OBSERVED' else 'UNKNOWN',max_source_date=day)
            current[sid]=dict(trade_date=day,fields=fields,price_basis_id=f['price_basis_id'])
        universe={r['source_security_key'].lower():r['security_id'] for r in factors}
        memberships,query=dated_industry_memberships(root,day,universe)
        binding=gzwrite(root,folder/'dated_csrc_memberships.jsonl.gz',memberships)
        sources=dict(core=owner['core'],profiles=owner['profiles'],membership=binding,policy=ref(root,root/'config/v4_dated_membership_source_policy_v1.json'))
        prior={};prior_members={};prior_date={};prior_native={};prior_seed={}
        for k in (1,3):
            d=sessions[sessions.index(day)-k]
            if d in history:
                h=history[d];prior[k]=h['current'];prior_members[k]=h['groups'];prior_date[k]=d;prior_native[k]=h['native'];prior_seed[k]=h['seed']
        native=build_native(memberships,current,target=day,snapshot_id=query['source_revision'],publication_id=binding['sha256'],
             parameter_set=params,source_bindings=sources,prior=prior,prior_memberships=prior_members,prior_date=prior_date,
             prior_sector_rows=prior_native,seed=seed,seed_capability=True,prior_seed=prior_seed)
        groups=defaultdict(list)
        for r in memberships:groups[r['sector_id']].append(r['security_id'])
        # Independent membership means no reuse of self-including sector medians.
        loo=[];oracle=[]
        from statistics import median
        for ordinal,sid in enumerate(sorted(factorby)):
            member=next((m for m in memberships if m['security_id']==sid),None)
            if member is None:
                loo.append(dict(security_id=sid,trade_date=day,value=None,quality='UNKNOWN',reason='DATED_CSRC_INDUSTRY_UNAVAILABLE'));continue
            sector=member['sector_id'];others=[s for s in groups[sector] if s!=sid]
            # Use the original complete cross-section producer after exclusion.
            excluded=[m for m in memberships if m['sector_id']==sector and m['security_id']!=sid]
            context=build_native(excluded,{s:current[s] for s in others},target=day,
                 snapshot_id=query['source_revision'],publication_id=binding['sha256']+':LOO:'+sid,
                 parameter_set=params,source_bindings=sources,seed={s:v for s,v in seed.items() if s!=sid},seed_capability=True)
            row=next((r for r in context if r['sector_id']==sector),None)
            if ordinal < 30:
                full=build_native([m for m in memberships if m['security_id']!=sid],
                     {s:v for s,v in current.items() if s!=sid},target=day,
                     snapshot_id=query['source_revision'],publication_id=binding['sha256']+':ORACLE:'+sid,
                     parameter_set=params,source_bindings=sources,seed={s:v for s,v in seed.items() if s!=sid},seed_capability=True)
                original=next(r for r in full if r['sector_id']==sector)
                if any(row['fields'][k]['value']!=original['fields'][k]['value'] for k in ('sector_rs1','sector_rs5')) or row['rank_eligible']!=original['rank_eligible']:
                    raise ValueError('GROUP_LOCAL_RELATIVE_INPUT_DIFFERS_FROM_FULL_CROSS_SECTION')
            f=factorby[sid]['fields'];p=profileby[sid]
            stock={k:f.get(k,{}).get('value') for k in ('rps5','rps20','rps20_delta3')}
            stock.update(stock_ret1=f['ret1']['value'],stock_ret5=f['ret5']['value'],
                 compression_state=p['states']['compression_state']['value'],ma_structure_state=p['states']['ma_structure_state']['value'])
            value=relative_sector(stock,current[sid],day,row)
            loo.append(dict(security_id=sid,trade_date=day,sector_id=sector,excluded_target_id=sid,
                 non_target_member_ids=others,taxonomy='BAOSTOCK_CSRC_INDUSTRY',**value,
                 membership_basis='DATE_EFFECTIVE_RECONSTRUCTED',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False))
            if row and len(oracle)<30:
                valid=[current[s]['fields']['ret5']['value'] for s in others if current[s]['fields']['ret5']['quality']=='ACCEPTED']
                actual=row['fields']['sector_rs5']['value'];expected=median(valid) if valid else None
                # Coverage gates can legitimately make a numeric median unavailable.
                oracle.append(dict(sid=sid,sector=sector,target_removed=sid not in row['member_ids'],
                     expected_median=expected,actual=actual,pass_=actual is None or abs(actual-expected)<1e-12))
            if ordinal and ordinal%500==0:print(json.dumps(dict(stage='LOO_PROGRESS',date=day,completed=ordinal,total=len(factorby))),flush=True)
        receipt=dict(trade_date=day,taxonomy='BAOSTOCK_CSRC_INDUSTRY',membership=binding,
             membership_count=len(memberships),sector_count=len(native),query=query,
             native=gzwrite(root,folder/'csrc_sector_native.jsonl.gz',native),seed=gzwrite(root,folder/'base_seed.jsonl.gz',seedrows),
             relative_sector=gzwrite(root,folder/'csrc_relative_sector_loo.jsonl.gz',loo),
             known_fields=dict(Counter(k for r in native for k,v in r['fields'].items() if v.get('value') is not None)),
             relative_sector_known=sum(r['quality']=='KNOWN' for r in loo),oracle=oracle,
             original_tdx_concept_membership='ACCEPTED_20260930_ONLY; OTHER_DATES_UNPROVEN',
             source_taxonomy_substitution=False,production_admission=False)
        receipt['relative_only_optimization']='Original per-group kernel; rs1/rs5 and eligibility checked against full exclusion cross-section on first 30 identities; cross-section percentiles are not consumed by relative_sector.'
        write(folder/'SECTOR_OWNER.json',receipt);receipts.append(receipt)
        history[day]=dict(current=current,groups=dict(groups),native={r['sector_id']:r for r in native},seed=seed)
        print(json.dumps(dict(stage='SECTOR_LOO',date=day,sectors=len(native),members=len(memberships),known=receipt['relative_sector_known'])),flush=True)
    write(out/'SECTOR_REPLAY.json',dict(owners=receipts,acceptance='CORRECTED_CSRC_TAXONOMY_ONLY',next_stage='INDEPENDENT_QA_AND_SCOPED_RELEASE_GATE'))
    return receipts
