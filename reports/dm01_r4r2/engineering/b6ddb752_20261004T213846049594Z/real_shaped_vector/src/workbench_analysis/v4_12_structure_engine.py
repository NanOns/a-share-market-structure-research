"""Scoped D1 engine: frozen AST, exact registry binder and candidate outputs only."""
from __future__ import annotations
from decimal import Decimal
from .v4_12_ast_runtime import ASTEngine,Result,known,missing
from .v4_12_structure_io import digest
from .v4_12_input_binder import InputBinder
from .v4_12_anchor_runtime import create_anchor,create_event,coordinate_view

class SessionLedger:
    """Unique-date observation ledger driven by the frozen counter contract/AST.

    Revisions evaluate against the previous calendar date, never their own date.
    This object holds engineering candidate history, not an accepted publication.
    """
    def __init__(self,contracts,available_date,calendar,anchor_id,baseline_history=None):
        self.contracts=contracts;self.available=available_date;self.calendar=calendar;self.anchor_id=anchor_id
        self.history=dict(baseline_history or {})
        counter=contracts.config['time_counter_contract']
        if counter['unique_count_key']!=['anchor_id','observation_trade_date'] or counter['definitions']['post_creation_evaluable_sessions']['consecutive'] is not False:
            raise ValueError('STOP_WITH_CONTRACT_GAP:COUNTER_DOMAIN')
    def observe(self,date,revision,evaluable,values):
        earlier=sorted(d for d in self.history if d<date);prior=self.history[earlier[-1]] if earlier else None
        previous=max((d for d in self.calendar if d<date),default=None) if self.calendar is not None else None
        age=None if self.calendar is None else sum(self.available<d<=date for d in set(self.calendar))
        eligible={d for d,r in self.history.items() if self.available<d<date and r['evaluable'] is True}
        if evaluable is True and date>self.available:eligible.add(date)
        inputs={**values,'post_creation_market_sessions':age,'post_creation_evaluable_sessions':len(eligible),
            'evaluable':evaluable,'prior_adjacent_evaluable':bool(prior and earlier[-1]==previous and prior['evaluable'] is True),
            'prior_held_count':prior['held_count'] if prior else 0,'prior_breach_count':prior['breach_count'] if prior else 0,
            'prior_recovery_held_count':prior['recovery_held_count'] if prior else 0,
            'prior_support_state':prior['preserved_state'] if prior else 'IDLE','prior_test_count':prior['test_count'] if prior else 0}
        ast=ASTEngine(self.contracts.config,inputs)
        outputs={name:ast.target(name) for name in ['support','acceptance','held_count','breach_count','recovery_held_count','next_test_count','separated_sessions']}
        support=outputs['support'].value
        preserved=prior['preserved_state'] if prior and (support is None or support=='UNKNOWN') else support
        test_count=0 if date==self.available else prior['test_count'] if evaluable is not True and prior else outputs['next_test_count'].value
        self.history[date]=dict(evaluable=evaluable,held_count=outputs['held_count'].value,breach_count=outputs['breach_count'].value,
            recovery_held_count=outputs['recovery_held_count'].value,test_count=test_count,preserved_state=preserved,
            revision=revision,anchor_id=self.anchor_id)
        return dict(market_age=age,evaluable_count=len(eligible),held_count=outputs['held_count'].value,breach_count=outputs['breach_count'].value,
            support=support,acceptance=outputs['acceptance'].value,stale=evaluable is not True or age is None,
            preserved_support_state=preserved,previous_session_state_ref=earlier[-1] if earlier else None,
            recovery_held_count=outputs['recovery_held_count'].value,test_count=test_count,separated_sessions=outputs['separated_sessions'].value)

class StructureEngine:
    def __init__(self,contracts,trade_date,cutoff,revision='r1'):
        self.contracts=contracts;self.trade_date=trade_date;self.cutoff=cutoff;self.revision=revision
        self.binder=InputBinder(contracts,trade_date,cutoff)
    def evaluate(self,security_id,prior_snapshot=None,extra_namespaces=None):
        facts=self.binder.bind(security_id,prior_snapshot,extra_namespaces)
        return self.evaluate_context(security_id,facts,self.binder.bound_prior,create=True)
    def evaluate_context(self,security_id,facts,bound_prior=None,create=False,creation_filter=None):
        """One owning episode overlay; caller owns cardinality and active projection."""
        ast=ASTEngine(self.contracts.config,facts);input_digest=digest(facts)
        prior_ref=bound_prior[1] if bound_prior else None
        bound=bound_prior[0] if bound_prior else None
        bound_anchor=bound.get('anchor') if bound else None
        anchor_ref=dict(anchor_id=bound_anchor['anchor_id'],artifact=prior_ref) if bound_anchor else None
        event_ref=dict(event_id=bound_anchor['source_event_id'],artifact=prior_ref) if bound_anchor else None
        machines={}
        for name in self.contracts.config['machine_ast']['machines']:
            result=ast.target(name);record=result.record()
            record.update(state=result.value if result.value is not None else 'UNKNOWN',input_digest=input_digest,contract_digest=self.contracts.digest,
                parameter_set_id=self.contracts.config['parameter_set']['parameter_set_id'],prior_state_ref=prior_ref,source_event_ref=event_ref,anchor_ref=anchor_ref)
            machines[name]=record
        retention=ast.target('retention_value');record=retention.record()
        if retention.value=='NOT_APPLICABLE':record.update(value=None,quality='NOT_APPLICABLE',reason=['NONPOSITIVE_DENOMINATOR'])
        record.update(state=str(retention.value) if retention.value is not None else 'UNKNOWN',input_digest=input_digest,contract_digest=self.contracts.digest,
            parameter_set_id=self.contracts.config['parameter_set']['parameter_set_id'],prior_state_ref=prior_ref,source_event_ref=event_ref,anchor_ref=anchor_ref)
        machines['retention']=record
        derived={}
        for row in self.contracts.config['field_registry']['fields']:
            if row['field_role']=='D1_LOCAL_DERIVATION' and row['field'] in self.contracts.config['machine_ast']['definitions']:
                result=ast.target(row['field']);derived[row['field']]=result.record()
        anchors=[];events=[];construction=[]
        for spec in self.contracts.config['anchor_schema']['types'] if create else []:
            if creation_filter is not None and not creation_filter(spec):
                construction.append(dict(anchor_type=spec['anchor_type'],quality='KNOWN',reason='BREAKOUT_EPISODE_CREATION_GUARD'));continue
            if spec.get('blocked_reason'):
                construction.append(dict(anchor_type=spec['anchor_type'],quality='UNKNOWN',reason=spec['blocked_reason']));continue
            qualified=ast.target(spec['creation_rule'])
            if qualified.value is not True:
                construction.append(dict(anchor_type=spec['anchor_type'],quality=qualified.quality,reason=list(qualified.reasons),qualified=qualified.value));continue
            # Exact accepted raw/affine inputs are needed for immutable raw coordinates.
            data=self.binder.data;raw_ref=data['component_artifacts']['RAW_DAILY'];adjusted_ref=data['component_artifacts']['ADJUSTED_DAILY']
            raw=self.binder.source(raw_ref).get(security_id);adjusted=self.binder.source(adjusted_ref).get(security_id)
            lower,upper=ast.target(spec['lower']),ast.target(spec['upper'])
            if not raw or not adjusted or lower.unknown or upper.unknown or 'qfq_mul' not in adjusted or Decimal(adjusted['qfq_mul'])<=0:
                construction.append(dict(anchor_type=spec['anchor_type'],quality='UNKNOWN',reason='UNKNOWN_ACCEPTED_RAW_ANCHOR_COORDINATE_UNAVAILABLE'));continue
            mul,add=Decimal(adjusted['qfq_mul']),Decimal(adjusted['qfq_add'])
            bounds=((lower.value-add)/mul,(upper.value-add)/mul)
            values={n:fact['value'] for n,fact in facts.items()};event_id=digest(dict(security_id=security_id,date=self.trade_date,revision=self.revision,anchor_type=spec['anchor_type'],input_digest=input_digest))
            anchor=create_anchor(self.contracts,spec['anchor_type'],security_id,self.trade_date,self.cutoff,values,event_id,input_digest,bounds,raw_ref,
                dict(mul=str(mul),add=str(add),accepted_adjustment_publication=adjusted_ref))
            anchors.append(anchor);events.append(create_event(self.contracts,anchor,self.revision))
        identity=dict(security_id=security_id,trade_date=self.trade_date,revision=self.revision)
        health=self.contracts.config['output_schema']['structure_health_mapping']
        envelope=dict(active_anchor_id=bound_anchor['anchor_id'] if bound_anchor else None,
            anchor_view_asof_t=coordinate_view(bound_anchor,facts['price_basis']['value'],facts['adjustment_source_revision']['value'],self.trade_date,self.revision) if bound_anchor else None,
            basic_breakout_state=machines['breakout']['state'],
            basic_pullback_state=machines['pullback']['state'],basic_recovery_state=machines['recovery']['state'],
            structure_health=health.get(machines['support']['state'],health['default']),structure_events=events,
            support_state=machines['support']['state'],acceptance_state=machines['acceptance']['state'],impulse_retention_1=None,impulse_retention_3=None,
            retest_count=None,unknown_reasons=sorted({reason for result in machines.values() for reason in result['reason']}),
            stale=any(r['quality']=='UNKNOWN' for r in machines.values()),last_known_support_state=facts.get('prior_support_state',{}).get('value'),
            invalidation_facts=None,contract_id=self.contracts.config['structure_event_contract']['contract_id'],
            parameter_set_digest=self.contracts.refs['parameter_set']['sha256'],source_publication_bindings=sorted(self.binder.source_refs.values(),key=lambda r:r['path']),
            output_digest='',observation_date=self.trade_date,cutoff=self.cutoff,price_basis=facts['price_basis']['value'] or 'UNKNOWN',
            adjustment_source_revision=facts['adjustment_source_revision']['value'] or 'UNKNOWN')
        if retention.value is not None and isinstance(retention.value,Decimal):
            age=facts['post_creation_market_sessions']['value']
            for label,param in [('impulse_retention_1','retention_horizon_one'),('impulse_retention_3','retention_horizon_three')]:
                target=next(r['value'] for r in self.contracts.config['parameter_set']['parameters'] if r['parameter_id']==param)
                if age==target:envelope[label]=float(retention.value)
        test=ast.target('next_test_count')
        if not bound_anchor and anchors:
            # Initial counter state belongs to a newly created Anchor, with no
            # post-creation test sessions. It cannot inherit a synthetic/display test.
            test=known(0);derived['next_test_count']=test.record()
        envelope['retest_count']=int(test.value) if test.quality=='KNOWN' else None
        support=machines['support']
        prior_last=bound.get('last_known_support_state') if bound else facts.get('prior_support_state',{}).get('value')
        envelope['last_known_support_state']=support['value'] if support['quality']=='KNOWN' else prior_last
        hard=ast.target('hard_invalidated');episode=ast.target('episode_invalidated')
        if hard.value is True or episode.value is True:
            envelope['invalidation_facts']=[dict(episode_owns_anchor=facts['episode_owns_anchor'],deep_breach=ast.target('deep_breach').record(),
                breach_count=ast.target('breach_count').record(),threshold=dict(parameter_id='support_break_consecutive_sessions',value=str(ast.parameters['support_break_consecutive_sessions'].value),parameter_set_digest=self.contracts.refs['parameter_set']['sha256']),
                threshold_result=ast.evaluate({'op':'ge','args':[{'field':'breach_count'},{'parameter_id':'support_break_consecutive_sessions'}]},'invalidation_projection').record(),
                prior_hard_invalidated=facts['prior_hard_invalidated'],hard_invalidated=hard.record(),episode_invalidated=episode.record(),anchor_ref=anchor_ref,event_ref=event_ref)]
        elif hard.quality==episode.quality=='KNOWN':envelope['invalidation_facts']=[]
        else:envelope['invalidation_facts']=None
        envelope['output_digest']=digest({k:v for k,v in envelope.items() if k!='output_digest'})
        from jsonschema import Draft202012Validator
        Draft202012Validator(self.contracts.config['output_schema']['schema']).validate(envelope)
        row=dict(identity=identity,security_id=security_id,trade_date=self.trade_date,revision=self.revision,namespace='D1_CANDIDATE',
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,prior_D1_history_status='NO_ACCEPTED_PRIOR_D1_PUBLICATION' if not prior_ref else 'EXACT_FROZEN_PRIOR_D1_BOUND',
            contract_digest=self.contracts.digest,entry_digest=self.contracts.entry_ref['sha256'],input_digest=input_digest,
            outputs=machines,derived=derived,anchor_construction=construction,prior_state_ref=prior_ref,stale=any(r['quality']=='UNKNOWN' for r in machines.values()))
        row['frozen_output_envelope']=envelope
        projection_quality=dict(retest_count=test.record(),invalidation_facts=dict(quality='KNOWN' if envelope['invalidation_facts'] is not None else 'UNKNOWN',reason=sorted(set(hard.reasons+episode.reasons)) if envelope['invalidation_facts'] is None else []),
            last_known_support_state=dict(quality='KNOWN' if envelope['last_known_support_state'] not in [None,'UNKNOWN'] else 'UNKNOWN',reason=[] if envelope['last_known_support_state'] not in [None,'UNKNOWN'] else ['NO_KNOWN_SUPPORT_HISTORY']))
        row['projection_quality']=projection_quality
        observation_ref=dict(observation_digest=digest(row),identity=identity)
        state_observations=[dict(identity={**identity,'machine':name},contract_id='V4_12_STATE_OBSERVATION_CANDIDATE',security_id=security_id,trade_date=self.trade_date,revision=self.revision,machine=name,
            observation_ref=observation_ref,**r) for name,r in machines.items()]
        transitions=[]
        for name,r in machines.items():
            previous=bound.get('state_observations',{}).get(name) if bound else None
            if name=='retention' or not previous or previous['quality']!='KNOWN' or r['quality']!='KNOWN' or previous['value']==r['value']:continue
            transitions.append(dict(identity={**identity,'machine':name},logical_transition_id=digest(dict(security_id=security_id,machine=name,trade_date=self.trade_date,prior_snapshot_id=bound['snapshot_id'])),
                security_id=security_id,machine=name,trade_date=self.trade_date,revision=self.revision,from_state=previous['value'],to_state=r['value'],
                prior_session_state_ref=prior_ref,current_observation_ref=observation_ref,transition_kind='KNOWN_STATE_CHANGE',quality='KNOWN',reason=r['reason'],
                same_day_revision_is_prior=False,anchor_ref=r['anchor_ref'],event_ref=r['source_event_ref'],contract_digest=self.contracts.digest,input_digest=input_digest))
        return dict(observation=row,bindings=dict(identity=identity,fields=facts),anchors=anchors,events=events,transitions=transitions,state_observations=state_observations,bound_prior=bound)
