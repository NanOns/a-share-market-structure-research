"""Frozen Basic Breakout episode orchestration; all business rules remain in AST."""
from copy import deepcopy
from .v4_12_multi_anchor_engine import MultiAnchorEngine
from .v4_12_structure_io import digest,exact_json,file_ref
from .v4_12_ast_runtime import ASTEngine

EPISODE_PATH='config/v4_12_breakout_episode_contract_v1.json'
def episode_contract(c):
    ref=file_ref(c.root,EPISODE_PATH)
    gate=exact_json(c.root,file_ref(c.root,'reports/v4_12_runtime_r13/R13A_CONTRACT_LOCAL_GATE.json'))
    if gate['status']!='PASS' or gate['contract']!=ref:raise ValueError('R13A_CONTRACT_GATE_REQUIRED')
    return exact_json(c.root,ref),ref

def validate_episodes(row):
    episodes=row['breakout_episodes'];ids=[e['breakout_episode_id'] for e in episodes]
    if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_EPISODE_ID')
    states={s['anchor_id']:s for s in row['anchor_states']}
    for e in episodes:
        owner=states.get(e['owning_anchor_id'])
        if not owner or owner['anchor']['anchor_type']!='PRIOR_HIGH' or owner['event']['event_id']!=e['event_id'] or e['security_id']!=row['security_id']:raise ValueError('BREAKOUT_OWNER_MISMATCH')
        if e['breakout_episode_id']!=digest(dict(security_id=e['security_id'],event_id=e['event_id'],owning_anchor_id=e['owning_anchor_id'])):raise ValueError('EPISODE_ID_MISMATCH')
        if e['created_trade_date']==row['trade_date'] and e['state'] in ['TESTING','BREAKOUT_ACCEPTED']:raise ValueError('CREATION_DAY_SELF_CONFIRM')
        if e['created_trade_date']<row['trade_date'] and not e['prior_episode_ref']:raise ValueError('EPISODE_PREDECESSOR_REQUIRED')
    active=[e for e in episodes if e['validity']=='ACTIVE']
    if len(active)>1 or row['active_breakout_episode_id']!=(active[0]['breakout_episode_id'] if active else None):raise ValueError('MULTIPLE_ACTIVE_BREAKOUT_EPISODES')
    return True

class BreakoutEpisodeEngine(MultiAnchorEngine):
    def __init__(self,c,date,cutoff,revision='r1',engineering_empty_seed=False):
        super().__init__(c,date,cutoff,revision)
        from .v4_12_breakout_snapshot import EpisodeBinder
        self.binder=EpisodeBinder(c,date,cutoff)
        self.episode_contract,self.episode_ref=episode_contract(c)
        self.engineering_empty_seed=engineering_empty_seed
    def evaluate_context(self,sid,facts,bound_prior=None,create=False,creation_filter=None):
        if not create:return super().evaluate_context(sid,facts,bound_prior,False)
        detector=deepcopy(facts)
        allowed=self._absence_quality=='KNOWN' and self._active_episode is None
        detector['prior_breakout_exists']=self.binder.record(self.binder.fields['prior_breakout_exists'],False if allowed else None,'KNOWN' if allowed else 'UNKNOWN',None if allowed else 'NO_KNOWN_EMPTY_BREAKOUT_EPISODE',self._prior_ref,self.binder.previous)
        decision=ASTEngine(self.contracts.config,detector).target(self.episode_contract['machine'].removeprefix('FROZEN_'))
        # The frozen machine's higher-priority UNKNOWN gate also governs creation;
        # a raw trigger alone cannot bypass missing evaluability/context.
        qualified=allowed and decision.quality=='KNOWN' and decision.value=='BREAKOUT_TENTATIVE'
        result=super().evaluate_context(sid,detector,None,True,lambda spec:spec['creation_rule']!=self.episode_contract['creation_rule'].removeprefix('FROZEN_') or qualified)
        if self._active_episode:
            owner=next(s for s in self._prior_row['anchor_states'] if s['anchor_id']==self._active_episode['owning_anchor_id'])
            overlay,context=self.overlay(facts,owner,self._prior_ref,sid)
            overlay['prior_breakout_exists']=self.binder.record(self.binder.fields['prior_breakout_exists'],self._active_episode['validity']=='ACTIVE','KNOWN',None,self._prior_ref,self.binder.previous)
            lifecycle=super().evaluate_context(sid,overlay,(context,self._prior_ref),False)
            result['observation']['outputs']['breakout']=lifecycle['observation']['outputs']['breakout']
            self._breakout_input=overlay
        else:self._breakout_input=detector
        return result
    def evaluate(self,sid,prior_snapshot=None,extra_namespaces=None):
        prior=self.binder.prior(prior_snapshot,sid)
        self._prior_row=prior[0] if prior else None;self._prior_ref=prior[1] if prior else None
        if prior:validate_episodes(prior[0])
        history=deepcopy(prior[0]['breakout_episodes']) if prior else []
        self._active_episode=next((e for e in history if e['breakout_episode_id']==prior[0]['active_breakout_episode_id']),None) if prior else None
        self._absence_quality=prior[0]['breakout_episode_set_quality'] if prior else ('KNOWN' if self.engineering_empty_seed else 'UNKNOWN')
        r=super().evaluate(sid,prior_snapshot,extra_namespaces)
        current=r['global_state_observations']['breakout'];state=current['state'];active=self._active_episode
        created=[s for s in r['anchor_states'] if s['created_this_session'] and s['anchor']['anchor_type']==self.episode_contract['owning_anchor_type']]
        if active and created:raise ValueError('DUPLICATE_BREAKOUT_CREATION')
        if not active and created:
            if len(created)!=1 or self._absence_quality!='KNOWN' or state!='BREAKOUT_TENTATIVE':raise ValueError('UNPROVEN_BREAKOUT_CREATION')
            owner=created[0]
            active=dict(breakout_episode_id=digest(dict(security_id=sid,event_id=owner['event']['event_id'],owning_anchor_id=owner['anchor_id'])),event_id=owner['event']['event_id'],security_id=sid,owning_anchor_id=owner['anchor_id'],created_trade_date=self.trade_date,state=state,quality=current['quality'],validity='ACTIVE',prior_episode_ref=None,last_observation_ref=None)
            history.append(active)
        elif active:
            old=active;active=deepcopy(old);history=[active if e['breakout_episode_id']==active['breakout_episode_id'] else e for e in history]
            active.update(state=state,quality=current['quality'],validity='TERMINAL' if state in self.episode_contract['terminal_states'] else 'ACTIVE',prior_episode_ref=dict(snapshot=self._prior_ref,breakout_episode_id=active['breakout_episode_id'],episode_digest=digest(old)))
        if active:active['last_observation_ref']=dict(observation_digest=digest(current),identity=r['identity'],input_digest=digest(self._breakout_input))
        # Preserve detector-only observation changes. Any episode state uses the
        # explicit owning identity below, never the parent's null global owner.
        r['transitions']=[t for t in r['transitions'] if t['machine']!='breakout' or (active is None and t['from_state'] in ['APPROACHING','NO_BREAKOUT'] and t['to_state'] in ['APPROACHING','NO_BREAKOUT'])]
        previous=self._active_episode
        if active and previous and previous['quality']==current['quality']=='KNOWN' and previous['state']!=state:
            r['transitions'].append(dict(**r['identity'],machine='breakout',breakout_episode_id=active['breakout_episode_id'],episode_id=active['breakout_episode_id'],event_id=active['event_id'],owning_anchor_id=active['owning_anchor_id'],anchor_id=active['owning_anchor_id'],from_state=previous['state'],to_state=state,prior_session_state_ref=self._prior_ref,quality='KNOWN',transition_kind='KNOWN_STATE_CHANGE',same_day_revision_is_prior=False,logical_transition_id=digest(dict(security_id=sid,breakout_episode_id=active['breakout_episode_id'],machine='breakout',trade_date=self.trade_date))))
        for o in r['observations']:
            if o['machine']=='breakout':o.update(anchor_id=active['owning_anchor_id'] if active else None,event_id=active['event_id'] if active else None,breakout_episode_id=active['breakout_episode_id'] if active else None)
        projection=dict(basic_breakout_state=state,breakout_episode_id=active['breakout_episode_id'] if active else None,breakout_owner_anchor_id=active['owning_anchor_id'] if active else None,breakout_projection_quality=current['quality'],breakout_projection_reason=current['reason'])
        r.update(projection);r['active_projection'].update(projection)
        r.update(breakout_episodes=history,active_breakout_episode_id=active['breakout_episode_id'] if active and active['validity']=='ACTIVE' else None,breakout_episode_set_quality='KNOWN' if history or self._absence_quality=='KNOWN' else 'UNKNOWN',episode_contract=self.episode_ref,breakout_input_bindings=self._breakout_input)
        validate_episodes(dict(**r['identity'],anchor_states=r['anchor_states'],breakout_episodes=history,active_breakout_episode_id=r['active_breakout_episode_id']))
        return r
