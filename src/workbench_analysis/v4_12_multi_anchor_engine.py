"""Security -> all owning episodes -> independent frozen AST -> active display projection."""
from copy import deepcopy
from .v4_12_structure_engine import StructureEngine
from .v4_12_structure_io import digest
from .v4_12_ast_runtime import ASTEngine
from .v4_12_multi_anchor_state import project_state,active_selector
from .v4_12_frozen_snapshot_v2 import InputBinderV2,load_contract

class MultiAnchorEngine(StructureEngine):
    def __init__(self,c,date,cutoff,revision='r1'):
        super().__init__(c,date,cutoff,revision);self.binder=InputBinderV2(c,date,cutoff);self.state_contract,self.state_ref=load_contract(c)
    def overlay(self,common,state,prior_ref,security_id):
        facts=deepcopy(common)
        for n,r in self.binder.fields.items():
            if r['field_role']=='FROZEN_PRIOR_D1':
                item=state['facts'][n];facts[n]=self.binder.record(r,item['value'],item['quality'],item['reason'],prior_ref,self.binder.previous)
        # Reuse registered one-anchor local derivations, with a single explicit
        # owning context. This context never becomes the security active selector.
        context={**state,'snapshot_id':prior_ref['row_digest']}
        self.binder.local(facts,security_id,(context,prior_ref))
        support=ASTEngine(self.contracts.config,facts).target('support')
        facts['support_today']=self.binder.record(self.binder.fields['support_today'],support.value,support.quality,list(support.reasons))
        return facts,context
    def evaluate(self,security_id,prior_snapshot=None,extra_namespaces=None):
        self.binder.validate_namespaces(extra_namespaces)
        prior=self.binder.prior(prior_snapshot,security_id)
        common=self.binder.bind(security_id,None)
        # Common upstream values and authority are fixed before any episode overlay.
        base=self.evaluate_context(security_id,common,None,create=True)
        global_outputs={n:base['observation']['outputs'][n] for n in self.state_contract['global_machines'] if n in base['observation']['outputs']}
        prior_ref=prior[1] if prior else None;states={};transitions=[];observations=[];contexts=[]
        if prior:
            for machine,current in global_outputs.items():
                previous=prior[0]['global_state_observations'].get(machine)
                if previous and previous['quality']==current['quality']=='KNOWN' and previous['value']!=current['value']:
                    transitions.append(dict(identity={**base['observation']['identity'],'machine':machine,'anchor_id':None},logical_transition_id=digest(dict(security_id=security_id,anchor_id=None,machine=machine,trade_date=self.trade_date)),
                        security_id=security_id,anchor_id=None,event_id=None,machine=machine,trade_date=self.trade_date,revision=self.revision,from_state=previous['value'],to_state=current['value'],
                        prior_session_state_ref=prior_ref,current_observation_ref=dict(observation_digest=digest(base['observation']),identity=base['observation']['identity']),transition_kind='KNOWN_STATE_CHANGE',quality='KNOWN',reason=current['reason'],
                        same_day_revision_is_prior=False,anchor_ref=None,event_ref=None,contract_digest=self.contracts.digest,input_digest=base['observation']['input_digest']))
        for old in prior[0]['anchor_states'] if prior else []:
            overlay,context=self.overlay(common,old,prior_ref,security_id)
            evaluated=self.evaluate_context(security_id,overlay,(context,prior_ref),create=False)
            state=project_state(self.state_contract,self.contracts,old['anchor'],old['event'],common,evaluated,old)
            states[state['anchor_id']]=state;contexts.append(evaluated['observation'])
            for record in evaluated['state_observations']:
                if record['machine'] not in self.state_contract['per_anchor_machines']:continue
                observations.append(dict(**record,anchor_id=state['anchor_id'],event_id=state['event']['event_id']))
            for record in evaluated['transitions']:
                if record['machine'] not in self.state_contract['per_anchor_machines']:continue
                record=deepcopy(record);record.update(anchor_id=state['anchor_id'],event_id=state['event']['event_id'],identity={**record['identity'],'anchor_id':state['anchor_id']},
                    logical_transition_id=digest(dict(security_id=security_id,anchor_id=state['anchor_id'],machine=record['machine'],trade_date=self.trade_date)))
                transitions.append(record)
        events={e['event_id']:e for e in base['events']}
        for anchor in base['anchors']:
            event=events[anchor['source_event_id']]
            if anchor['anchor_id'] in states:
                if states[anchor['anchor_id']]['anchor']!=anchor or states[anchor['anchor_id']]['event']!=event:raise ValueError('IMMUTABLE_ANCHOR_CONFLICT')
                continue
            state=project_state(self.state_contract,self.contracts,anchor,event,common);states[state['anchor_id']]=state
            for machine,record in state['state_observations'].items():observations.append(dict(identity={**base['observation']['identity'],'anchor_id':state['anchor_id'],'machine':machine},security_id=security_id,trade_date=self.trade_date,revision=self.revision,anchor_id=state['anchor_id'],event_id=event['event_id'],machine=machine,**record))
        ordered=sorted(states.values(),key=lambda s:s['anchor_id']);selection=active_selector(self.state_contract,self.contracts,ordered,common,self.trade_date,self.revision)
        selected=states.get(selection['active_anchor_id']);projection={n:deepcopy(selected['output_envelope'].get(n)) if selected else None for n in self.state_contract['security_projection']}
        projection['active_anchor_id']=selection['active_anchor_id']
        if not selected:
            for n in ['support_state','acceptance_state','basic_pullback_state','basic_recovery_state']:projection[n]='UNKNOWN'
        projection.update(active_anchor_selection_quality=selection['quality'],active_anchor_selection_reason=selection['reason'],projection_quality='KNOWN' if selected else 'UNKNOWN',reason=selection['reason'])
        for machine,record in global_outputs.items():observations.append(dict(identity={**base['observation']['identity'],'machine':machine,'anchor_id':None},anchor_id=None,event_id=None,security_id=security_id,trade_date=self.trade_date,revision=self.revision,machine=machine,**record))
        return dict(identity=base['observation']['identity'],common_facts=common,common_F0_bind_count=1,global_state_observations=global_outputs,anchor_states=ordered,active_selection=selection,active_projection=projection,
            prior_state_ref=prior_ref,contexts=contexts,creation_observation=base['observation'],anchors=base['anchors'],events=base['events'],observations=observations,transitions=transitions)
