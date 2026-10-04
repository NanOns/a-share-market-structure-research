"""Versioned real-calendar successor of the accepted V4-15 projection.

Only the historical demonstration date ceiling is removed. Accepted calendar
membership remains mandatory. Event/revision/control semantics are identical.
"""
from workbench_analysis.v4_15_radar_cohort import RadarCohortRuntime, identity, LEDGER_KEY, EVENT_KEY, EVENTS, _time
from workbench_analysis.v4_14_replay_io import digest

class RealOwnerProjectionV1(RadarCohortRuntime):
    def _project(self,rows,events,profiles,date,pid,publication_ref,evidence,metadata,source_refs):
        if date not in self.authority.sessions:raise ValueError('ACCEPTED_CALENDAR_DATE_REQUIRED')
        forbidden={'qualification_source','focus_filter','ui_top_k_filter','future_source','fep_prediction','reset_T0','redraw_controls'}
        if any(metadata.get(k) for k in forbidden):raise ValueError('FORBIDDEN_FEEDBACK_OR_MUTATION')
        state=metadata.get('observation_state','ASSERTED')
        if state not in {'ASSERTED','RETRACTED','CORRECTED'}:raise ValueError('INVALID_OBSERVATION_STATE')
        event_map={}
        for e in events:event_map.setdefault((e['entity_type'],e['entity_id']),[]).append(e)
        ledger=[];logical=[];observations=[];enrollments=[];diagnostics=[]
        seen=set()
        for row in sorted(rows,key=lambda r:(r['entity_type'],r['entity_id'])):
            entity=(row['entity_type'],row['entity_id'])
            if entity in seen:raise ValueError('DUPLICATE_OWNER_ENTITY')
            seen.add(entity)
            if row['entity_type'] not in {'STOCK','SECTOR'}:raise ValueError('ENTITY_NAMESPACE_REQUIRED')
            if row.get('future_source') or row.get('fep_prediction') or row.get('qualification_source') in {'Focus','UI Top-K','Forward outcome','FEP prediction'}:raise ValueError('FORBIDDEN_FEEDBACK_OR_MUTATION')
            for fact in row.get('input_provenance',{}).values():
                if fact.get('source_field_payload',{}).get('trade_date',date)>date:raise ValueError('FUTURE_FACT_AT_T0')
            lineage=row.get('state_lineage_id',row.get('model_namespace',evidence))
            base={k:row[k] for k in ['entity_type','entity_id']}
            base.update(model_contract_id=row.get('model_contract_id','RESEARCH_STATE_V1'),state_lineage_id=lineage,
                        publication_id=pid,signal_type=row.get('maturity','UNKNOWN'),trade_date=date,
                        eligibility_state=row.get('final_eligibility','UNKNOWN'),episode_id=row.get('episode_id'),
                        source_publication=publication_ref,source_provenance=source_refs,max_source_trade_date=date,
                        display_rank=None,focus_activation_state=None,focus_activation_reason=None)
            if base['entity_type']=='STOCK' and base['signal_type']=='WARM':
                diagnostics.append(dict(entity_id=base['entity_id'],status='NOT_APPLICABLE_NO_ACCEPTED_OWNER'));continue
            owner_events=[]
            for e in event_map.get(entity,[]):
                for typ in e.get('event_types',[e.get('event_type','NONE')]):
                    mapped={'CONFIRMATION_INVALIDATED':'INVALIDATION'}.get(typ,typ)
                    if mapped in EVENTS:owner_events.append((mapped,e))
            # PREWATCH enrollment is an explicit accepted reducer ENROLLED transition,
            # not a detector recalculation or a diff against whichever row was latest.
            if 'ENROLLED' in row.get('transition_reasons',[]) and row.get('maturity')=='PREWATCH':
                owner_events.append(('REENTRY_PREWATCH' if row.get('parent_episode_id') else 'FIRST_PREWATCH',row))
            if row.get('radar_owner_events'):
                if evidence!='ENGINEERING_SYNTHETIC':raise ValueError('FIXTURE_ONLY_OWNER_EVENT_ADAPTER')
                owner_events.extend((e,row) for e in row['radar_owner_events'])
            if base['eligibility_state']=='TRUE' or owner_events:
                base['ledger_id']=identity(base,LEDGER_KEY)
                base['priority_bucket']='RISK_INVALIDATION' if any(t=='INVALIDATION' for t,e in owner_events) else 'ELIGIBLE'
                base['priority_rank']=None;base['eligibility_rank']=None
                ledger.append(self.store.append('daily_ledger',base['ledger_id'],base))
            for typ,event in sorted({t:ev for t,ev in owner_events}.items()):
                if typ not in EVENTS:raise ValueError('UNREGISTERED_OWNER_EVENT')
                if typ=='UPGRADE_TO_WARM' and base['entity_type']=='STOCK':
                    diagnostics.append(dict(entity_id=base['entity_id'],status='NOT_APPLICABLE_NO_ACCEPTED_OWNER'));continue
                if not row.get('episode_id'):raise ValueError('OWNER_EPISODE_REQUIRED')
                evt={k:base[k] for k in EVENT_KEY if k not in {'event_type','event_trade_date'}}
                evt.update(event_type=typ,event_trade_date=event.get('event_trade_date',event.get('trade_date',date)))
                eid=identity(evt,EVENT_KEY);evt['logical_event_id']=eid
                if evt['event_trade_date']>date:raise ValueError('FUTURE_EVENT_AT_T0')
                # Same-day revision may not invent a replacement episode.
                for oldref in self.store.refs('logical_event'):
                    old=self.store.read(oldref)
                    if all(old[k]==evt[k] for k in EVENT_KEY if k!='episode_id') and old['episode_id']!=evt['episode_id']:
                        if not row.get('formal_owner_new_episode'):raise ValueError('ILLEGAL_SAME_DAY_EPISODE_REVISION')
                logical.append(self.store.append('logical_event',eid,evt))
                obs={'logical_event_id':eid,'publication_id':pid,'observation_state':state,'source_correction':bool(metadata.get('source_correction')),
                     'supersedes_observation':metadata.get('supersedes_observation'),'source_publication':publication_ref,
                     'why_now':self._explanation(row,event,publication_ref),'conflict':self._conflict(row,publication_ref)}
                obs['observation_id']=identity(obs,['logical_event_id','publication_id'])
                observations.append(self.store.append('event_observation',obs['observation_id'],obs))
                if typ=='INVALIDATION' or base['eligibility_state']!='TRUE' or state!='ASSERTED' or base['signal_type'] in {'SEED','NEAR_MISS'}:continue
                namespace='ENGINEERING_SYNTHETIC' if evidence=='ENGINEERING_SYNTHETIC' else 'RECONSTRUCTED_ASOF'
                # Real-time admission needs accepted slot/deadline evidence; caller
                # annotations alone can never promote historical reconstructed input.
                slot=metadata.get('accepted_observation_slot')
                deadline=None
                if evidence=='REALTIME_ACCEPTED_SOURCE' and slot:
                    if slot not in source_refs:raise ValueError('OBSERVATION_SLOT_NOT_ACCEPTED_PUBLICATION_DEPENDENCY')
                    slot_payload=json.loads(self.authority.read(slot))
                    if any(slot_payload[k]!=base[k] for k in ['model_contract_id','state_lineage_id']) or slot_payload['trade_date']!=date or _time(slot_payload['observed_at'])>_time(slot_payload['deadline']):raise ValueError('MISSED_OBSERVATION_SLOT')
                    deadline=slot_payload['deadline']
                    namespace='FIRST_OBSERVED'
                if metadata.get('source_correction'):namespace='CORRECTED'
                enid=identity(dict(logical_event_id=eid,cohort_namespace=namespace),['logical_event_id','cohort_namespace'])
                existing=[r for r in self.store.refs('enrollment') if self.store.read(r)['enrollment_id']==enid]
                if existing:enrollments.extend(existing);continue
                profile=profiles.get(base['entity_id'],{})
                reference=row.get('comparison_reference')
                enrollment=dict(enrollment_id=enid,cohort_namespace=namespace,T0=evt['event_trade_date'],logical_event_id=eid,
                    model_contract_id=evt['model_contract_id'],state_lineage_id=evt['state_lineage_id'],entity_type=evt['entity_type'],entity_id=evt['entity_id'],episode_id=evt['episode_id'],signal_type=typ,
                    source_publication=publication_ref,source_digest=publication_ref['sha256'],parameter_digest=self.parameter_ref['sha256'] if row.get('parameter_set_id')==self.parameters['parameter_set_id'] else None,
                    parameter_identity_quality='KNOWN' if row.get('parameter_set_id')==self.parameters['parameter_set_id'] else 'UNKNOWN',parameter_source=self.parameter_ref if row.get('parameter_set_id')==self.parameters['parameter_set_id'] else None,
                    contract_digest=self.authority.package_ref['sha256'],signal_reference=row.get('signal_reference'),comparison_reference=reference,
                    benchmark_ids={'market':digest([enid,'MARKET']),'sector':digest([enid,'SECTOR'])},
                    control_assignment_ids={k:digest([enid,k]) for k in ['A','B','C']},
                    calendar_identity=self.authority.calendar_ref,adjustment_identity=row.get('adjustment_identity','UNKNOWN_ACCEPTED_SOURCE_REFERENCE_UNAVAILABLE'),
                    evidence_class=evidence,observation_slot=slot,observation_deadline=deadline,accepted_at=row.get('cutoff'),comparison_reference_source=row.get('comparison_reference_source'),t0_transform=row.get('t0_transform'),
                    eligibility_source=publication_ref,primary_industry=profile.get('fields',{}).get('primary_industry',{}).get('value',row.get('primary_industry')),
                    settlement_continues=True,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
                enrollments.append(self.store.append('enrollment',enid,enrollment))
        manifest=dict(contract_id='V4_15_RADAR_COHORT_ENGINEERING_V1',trade_date=date,publication_id=pid,source_publication=publication_ref,
                      authority=self.authority.bindings(),daily_ledger=ledger,logical_events=logical,observations=observations,enrollments=enrollments,
                      complete_owner_rows=len(rows),diagnostics=diagnostics,evidence_class=evidence,production=False,shadow=False,focus=False,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED')
        return self.store.append('radar_publication',digest([pid,'RADAR_V1']),manifest)
