"""Explicit corrected owner admission to unchanged V4-12/V4-04 kernels."""
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .corrected_owner_replay import load, checked, gzrows, gzwrite, ref, OUT, CONTRACT
from .market_source_acquisition import official_sessions, write
from .v4_12_structure_io import FrozenContracts, CandidateStore, digest
from .v4_12_breakout_snapshot import EpisodeBinder, EpisodeSnapshotMaterializer
from .v4_12_breakout_episode import BreakoutEpisodeEngine, episode_contract
from .v4_12_frozen_snapshot_v2 import load_contract
from .v4_12_input_binder import InputBinder


class CorrectedBinder(EpisodeBinder):
    """Bind only saved, hash-verified corrected outputs; never calculate factors here."""
    def __init__(self, contracts, day, cutoff, owner, profiles, status_rows):
        self.contracts=contracts;self.root=contracts.root;self.date=day;self.cutoff=datetime.fromisoformat(cutoff)
        self.calendar=official_sessions(self.root);self.previous=self.calendar[self.calendar.index(day)-1]
        self.fields={r['field']:deepcopy(r) for r in contracts.config['field_registry']['fields']}
        self.publications={};self.source_refs={}
        self.core={r['security_id']:r for r in gzrows(checked(self.root,owner['core']))}
        self.previous_core={r['security_id']:r for r in gzrows(checked(self.root,owner['prior_core']))}
        self.history={r['security_id']:{b['trade_date']:b for b in r['bars']} for r in gzrows(checked(self.root,owner['history']))}
        self.adjusted={r['security_id']:r for r in gzrows(checked(self.root,owner['adjusted']))}
        self.profiles={r['security_id']:r for r in profiles};self.status_rows=status_rows
        self.data={'component_artifacts':{'RAW_DAILY':owner['raw'],'ADJUSTED_DAILY':owner['adjusted']}}
        self.derivations=deepcopy(contracts.config['source_derivations_r2'])
        self.status_ref=owner['status'];self.derivations['dependency_ledger']['evaluable']['publications']={day:self.status_ref}
        self.owner=owner

    def source(self, binding):
        if binding['path'] not in self.publications:
            rows=self.status_rows if binding==self.status_ref else gzrows(checked(self.root,binding))
            self.publications[binding['path']]={r['security_id']:r for r in rows}
            self.source_refs[binding['path']]=binding
        return self.publications[binding['path']]

    def bind(self, sid, prior_snapshot=None, extra_namespaces=None):
        self.validate_namespaces(extra_namespaces);prior=self.prior(prior_snapshot,sid);self.bound_prior=prior
        facts={};core=self.core.get(sid,{}).get('fields',{});previous=self.previous_core.get(sid,{}).get('fields',{})
        adjusted=self.adjusted.get(sid,{});bs=self.history.get(sid,{});pb=bs.get(self.previous)
        mapping={'ATR20':'atr20','CLV':'clv','MA20':'ma20','MA60':'ma60','amount_ratio20':'amount_ratio20',
                 'delta3':'rps5_delta3','prior_high20':'prior_high20','rel_market_1':'rel_market_1','ret1':'ret1','slope20':'slope20'}
        for name,row in self.fields.items():
            role=row['field_role'];value=None;reason=None;binding=self.owner['core']
            if role=='D1_OUTPUT':continue
            if role=='FROZEN_PRIOR_D1':
                item=prior[0].get('facts',{}).get(name) if prior else None
                facts[name]=self.record(row,item['value'] if item and item['quality']=='KNOWN' else None,
                    'KNOWN' if item and item['quality']=='KNOWN' else 'UNKNOWN',
                    None if item and item['quality']=='KNOWN' else 'NO_ACCEPTED_PRIOR_D1_PUBLICATION',prior[1] if prior else None,self.previous)
                continue
            if role=='D1_LOCAL_DERIVATION':facts[name]=self.record(row,reason='LOCAL_REQUIRED_SOURCE_UNAVAILABLE');continue
            if name in mapping:
                item=core.get(mapping[name],{});value=item.get('value') if item.get('quality_state')=='OBSERVED' else None;reason=item.get('unknown_reason')
            elif name in ('O','H','L','C','price_basis','adjustment_source_revision'):
                field={'O':'open','H':'high','L':'low','C':'close'}.get(name,name)
                value=adjusted.get(field) if adjusted.get('adjustment_readiness')=='READY' else None;binding=self.owner['adjusted']
            elif name in ('atr_prior_view','ma20_t_minus_1'):
                item=previous.get('atr20' if name=='atr_prior_view' else 'ma20',{});value=item.get('value') if item.get('quality_state')=='OBSERVED' else None;binding=self.owner['prior_core']
            elif name in ('close_t_minus_1','prior_high_view'):
                value=pb['qfq_ohlc'][3 if name=='close_t_minus_1' else 1] if pb and pb['qfq_ohlc'] else None;binding=self.owner['history']
            elif name=='near_high20_state':
                item=self.profiles.get(sid,{}).get('states',{}).get(name,{});value=item.get('value') if not item.get('unknown_reason') else None;binding=self.owner['profiles']
            elif name=='prior_delta3':
                item=previous.get('rps5_delta3',{});value=item.get('value');binding=self.owner['prior_core']
            else:reason=row.get('blocked_reason') or 'NO_DECLARED_CORRECTED_PRODUCER'
            if value is not None and row['data_type'] in ('number','integer'):value=str(Decimal(str(value)))
            # Candidate availability is explicit; these facts do not become old accepted publications.
            row['source_namespace']='R4_CORRECTED_OWNER_V1';self.source_refs[binding['path']]=binding
            facts[name]=self.record(row,value,'KNOWN' if value is not None else 'UNKNOWN',None if value is not None else reason or 'CORRECTED_FIELD_UNAVAILABLE',binding,
                                    self.previous if row['time_role']=='T_MINUS_1' else self.date)
        self.local(facts,sid,prior)
        return facts

    def local(self, facts, sid, prior):
        InputBinder.local(self,facts,sid,prior)
        # Identity transform is proven only for the identical frozen basis pair.
        anchor=prior[0].get('anchor') if prior else None
        if anchor and (anchor['anchor_price_basis'],anchor['adjustment_source_revision']) == (
                facts['price_basis']['value'],facts['adjustment_source_revision']['value']):
            for name,value in (('alpha','1'),('beta','0')):
                facts[name]=self.record(self.fields[name],value,'KNOWN',pub=self.owner['adjusted'])


class CorrectedEpisodeEngine(BreakoutEpisodeEngine):
    def __init__(self, contracts, day, cutoff, owner, profiles, statuses):
        self.contracts=contracts;self.trade_date=day;self.cutoff=cutoff;self.revision='r1'
        self.binder=CorrectedBinder(contracts,day,cutoff,owner,profiles,statuses)
        self.state_contract,self.state_ref=load_contract(contracts)
        self.episode_contract,self.episode_ref=episode_contract(contracts)
        self.engineering_empty_seed=False


def materialize_profiles_structure(root):
    root=Path(root).resolve();out=root/OUT;replay=load(out/'CORE_REPLAY.json')
    if replay['acceptance']!='PASS_CORRECTED_CORE_NUMERIC_ORACLE':raise ValueError('CORRECTED_CORE_GATE_REQUIRED')
    write(out/'STRUCTURE_STAGE_ENTRY.json',dict(contract=ref(root,root/CONTRACT),upgrade_document='R4.1',
          prior_gate=ref(root,out/'CORE_REPLAY.json'),acceptance='IN_PROGRESS',next_stage='SECTOR_FOCUS_FORWARD_AND_RELEASE_QA'))
    from scripts.run_v4_04_full_market_candidate_r4 import build_row, CONTRACT_FILES
    from scripts import run_v4_04_full_market_candidate_r4 as builder
    from scripts.build_fp06_sector import periods
    from v4.market_regime_ui import RegimeUI
    from .v4_13_descendant_contracts import DescendantContracts
    from .v4_13_profile_runtime import copy_structure
    c13=DescendantContracts(root)
    c=FrozenContracts(root);sessions=official_sessions(root);receipts=[];prior=None
    cutoff=datetime.now(timezone.utc).isoformat()
    cd=digest({p:ref(root,root/p) for p in CONTRACT_FILES})
    for owner in replay['owners']:
        day=owner['trade_date'];folder=out/'owners'/day;factors=gzrows(checked(root,owner['core']))
        histories={r['security_id']:r['bars'] for r in gzrows(checked(root,owner['history']))}
        builder.CUTOFF=day;profiles=[];statuses=[]
        regime=RegimeUI('UNKNOWN','UNKNOWN',None,0,{'reason':'CORRECTED_MARKET_AXES_NOT_YET_BOUND'},'CORRECTED_MARKET_AXES_NOT_YET_BOUND')
        for factor in factors:
            sid=factor['security_id'];bs=histories[sid]
            actual={b['trade_date'] for b in bs};status=[(d,'ACTUAL_TRADED' if d in actual else 'UNKNOWN') for d in sessions if bs[0]['trade_date']<=d<=day]
            bars=[dict(trade_date=b['trade_date'],qfq_close=b['qfq_ohlc'][3] if b['qfq_ohlc'] else None,
                qfq_high=b['qfq_ohlc'][1] if b['qfq_ohlc'] else None,qfq_low=b['qfq_ohlc'][2] if b['qfq_ohlc'] else None,
                amount=b['amount'],adjusted_quality='READY' if b['qfq_ohlc'] else 'UNKNOWN') for b in bs]
            r=build_row(factor,bars,periods(bs,'WEEKLY',day),periods(bs,'MONTHLY',day),status,
                        {'source_security_key':factor['source_security_key']},owner['source_digest'],cd,sessions,regime)
            r.update(knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False);profiles.append(r)
            statuses.append(dict(security_id=sid,trade_date=day,actual_bar_present=day in actual,
                                 status='ACTUAL_TRADED' if day in actual else 'UNKNOWN',status_conflict=False))
        owner=dict(owner,profiles=gzwrite(root,folder/'profiles.jsonl.gz',profiles),status=gzwrite(root,folder/'status.jsonl.gz',statuses))
        engine=CorrectedEpisodeEngine(c,day,cutoff,owner,profiles,statuses)
        results=[]
        for factor in factors:
            sid=factor['security_id']
            # Newly listed identities have no predecessor row: absence stays UNKNOWN.
            use_prior=prior if prior and sid in previous_ids else None
            results.append(engine.evaluate(sid,use_prior))
        store=CandidateStore(root,folder.relative_to(root).as_posix()+'/structure')
        artifacts=[]
        for name,rs,compressed in [('runtime_security.jsonl.gz',results,True),('state_observations.jsonl.gz',[o for r in results for o in r['observations']],True),('anchors.jsonl',[a for r in results for a in r['anchors']],False),('events.jsonl',[a for r in results for a in r['events']],False),('transitions.jsonl',[a for r in results for a in r['transitions']],False)]:
            artifacts.append(store.jsonl(name,rs,compressed))
        manifest=store.json('runtime_manifest.json',dict(contract_id='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST',
             status='ENGINEERING_CANDIDATE_NOT_ACCEPTED',trade_date=day,revision='r1',available_at=cutoff,
             entry=c.entry_ref,contract_digest=c.digest,snapshot_contract=engine.state_ref,episode_contract=engine.episode_ref,
             artifacts=artifacts,prior=prior,scope='R4_CORRECTED_SOURCE_CANDIDATE',source_admission_contract=ref(root,root/CONTRACT),
             owner_inputs=owner,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_accepted=False,
             raw_fallback_count=0,provider_replacement_count=0,V4_11_candidate_substitution_count=0))
        snapshot=EpisodeSnapshotMaterializer(c,store).seal(results,manifest,cutoff)
        prior={'frozen_manifest_episode':snapshot};previous_ids={r['security_id'] for r in factors}
        counts={}
        projected=[dict(security_id=r['identity']['security_id'],trade_date=day,
                       fields=copy_structure(r,c13,dict(**artifacts[0],producer_contract_id='V4_12_R13_RUNTIME_CANDIDATE_MANIFEST')),
                       knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False) for r in results]
        for name in ('basic_breakout_state','basic_pullback_state','basic_recovery_state','support_state','structure_health'):
            cells=[r['fields'][name] for r in projected]
            known=sum(v.get('quality')=='KNOWN' and v.get('value') not in (None,'UNKNOWN') for v in cells)
            counts[name]=dict(known=known,unknown=len(results)-known)
        counts['relative_market_state']=dict(known=sum(r['states']['relative_market_state']['value']!='UNKNOWN' for r in profiles),unknown=sum(r['states']['relative_market_state']['value']=='UNKNOWN' for r in profiles))
        result=dict(owner=owner,structure_manifest=manifest,snapshot=snapshot,rows=len(results),counts=counts,
             advanced_projection=gzwrite(root,folder/'advanced_structure_projection.jsonl.gz',projected),
             anchors=sum(len(r['anchor_states']) for r in results),events=sum(len(r['events']) for r in results),
             prior_unknown_absence_preserved=True,acceptance='MATERIALIZED_CORRECTED_CANDIDATE_NOT_PRODUCTION')
        write(folder/'PROFILE_STRUCTURE_OWNER.json',result);receipts.append(result)
        print(__import__('json').dumps(dict(stage='PROFILE_STRUCTURE',day=day,anchors=result['anchors'],counts=counts)),flush=True)
    write(out/'PROFILE_STRUCTURE_REPLAY.json',dict(contract='V4_CORRECTED_OWNER_REPLAY_V1',owners=receipts,
          acceptance='REAL_MATERIALIZATION_COMPLETE_PENDING_INDEPENDENT_STRUCTURE_ORACLE',next_stage='SECTOR_FOCUS_FORWARD_AND_RELEASE_QA'))
    return receipts
