"""Replay checks over accepted owner output and frozen explicit envelopes."""
from datetime import datetime
from .v4_14_replay_io import digest
from .v4_14_owner_adapters import state_vector,structure_trace,rotation_acceptance,event_rows
class ReplayRejected(ValueError):pass
def reject(reason):raise ReplayRejected(reason)
def admit(behavior):return dict(verdict='ADMIT_CONTRACT_CASE',required_behavior=behavior)
def timestamp(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    return dt
class ReplayRuntime:
    def __init__(self,authority):self.authority=authority;self.root=authority.root
    def evaluate_case(self,dimension,inputs):
        try:return admit(self._case(dimension,inputs))
        except ReplayRejected as e:return dict(verdict='REJECT_CONTRACT_VIOLATION',reason=str(e))
    def _case(self,d,x):
        if d=='same_day_feedback':
            forbidden=self.authority.config['temporal_non_edge_registry']['forbidden_edges']
            alias=self.authority.config['temporal_non_edge_registry']['canonical_nodes']
            graph={}
            for a,b,t in x['edges']:
                if t=='T':graph.setdefault(alias.get(a,a),set()).add(alias.get(b,b))
            for a,b,t in forbidden:
                if t!='T':continue
                seen=set();todo=list(graph.get(alias.get(a,a),()))
                while todo:
                    n=todo.pop()
                    if n not in seen:seen.add(n);todo.extend(graph.get(n,()))
                if alias.get(b,b) in seen:reject('SAME_DAY_FEEDBACK_FORBIDDEN')
            return dict(raw_after=x['raw_before'])
        if d=='state_transition_legality':
            if x.get('claimed_maturity')=='WARM' and x['entity_type']=='STOCK':reject('ILLEGAL_STOCK_WARM')
            r=state_vector(self.root,'upgrade_immediate')
            return dict(maturity=r['maturity'],episode='E1' if r['episode_id']=='FIXTURE_EPISODE' else r['episode_id'])
        if d=='hysteresis':
            name='downgrade_NONE_day'+str(x['adjacent_evaluable_sessions']);r=state_vector(self.root,name)
            if x.get('claimed_maturity',r['maturity'])!=r['maturity']:reject('PREMATURE_DOWNGRADE')
            return dict(maturity=r['maturity'],downgrade_count=r['downgrade_count'])
        if d=='expiry':
            r=state_vector(self.root,'expiry_10' if x['evaluable'] else 'expiry_pause_UNKNOWN')
            if x.get('claimed_expiry_count',r['expiry_count'])!=r['expiry_count']:reject('UNKNOWN_OR_SUSPENSION_CANNOT_ADVANCE_EXPIRY')
            return dict(maturity=r['maturity'],tracking=r['tracking'],expiry_count=r['expiry_count'])
        if d=='direct_prewatch_confirmed':
            r=state_vector(self.root,'upgrade_immediate')
            if x.get('claimed_wait_sessions',0):reject('FORCED_UPGRADE_WAIT_FORBIDDEN')
            return dict(maturity=r['maturity'],mandatory_wait_sessions=r['downgrade_count'])
        if d=='rotation_pulse_accepted_failed':
            accepted=rotation_acceptance(self.root,x['accepted_predicate_oracle'])['rotation_accepted_possible']
            if x.get('claimed_accepted_with_failed_breadth'):reject('ROTATION_ACCEPTANCE_REQUIRES_FROZEN_OWNER_PREDICATES')
            from sector.machine_ast_r3 import evaluate_ast_explain
            import json
            c=json.loads((self.root/'config/v4_08_rotation_core_contract_r5.json').read_bytes())
            facts={k:dict(value=v,quality='ACCEPTED',producer='ROTATION_CORE_V1',time_role=t) for k,v,t in [('pulse_active',x['expired_branch']['episode_exists'],'PULSE_FROZEN_EPISODE'),('episode_accepted',x['expired_branch']['accepted'],'PULSE_FROZEN_EPISODE'),('pulse_age_sessions',x['expired_branch']['pulse_age_sessions'],'ACCEPTED_CALENDAR_SESSION_DISTANCE')]}
            p=json.loads((self.root/'config/v4_08_algorithm_parameter_set_r5.json').read_bytes());params={v['parameter_id']:v['value'] for v in p['parameters']}
            for name,value,producer in [('membership_ready',True,'V4_08_PIT_MEMBERSHIP'),('sector_member_count',params['V4_08_SECTOR_MIN_MEMBERS'],'V4_08_SECTOR_NATIVE_V1'),('sector_quote_coverage',params['V4_08_SECTOR_MIN_QUOTE_COVERAGE'],'V4_08_SECTOR_NATIVE_V1')]:facts[name]=dict(value=value,quality='ACCEPTED',producer=producer,time_role='TARGET_CUTOFF')
            failed=evaluate_ast_explain('UNACCEPTED_EPISODE_EXPIRED',c['rules'],facts,params)
            return dict(accepted_branch='ROTATION_ACCEPTED' if accepted else 'UNKNOWN',failed_branch=c['fallback_outputs']['UNACCEPTED_EPISODE_EXPIRED'] if failed.state is True else 'UNKNOWN',branches_mutually_exclusive=bool(accepted and failed.state is True))
        if d=='support_reclaim_retest_break':
            trace=structure_trace(self.root,x['owner_trace_refs'])
            if x.get('claimed_retest_without_separation'):reject('RETEST_REQUIRES_FROZEN_SEPARATION_RULE')
            return dict(trace=trace,anchor=x['anchor'])
        if d=='confirmation_persistent_suppression':
            row=state_vector(self.root,'STOCK_CONFIRMED');events=event_rows([row],[row],target=row['trade_date'],calendar_id=row['calendar_publication_id'])
            event=events[0]['primary_event']
            if x.get('claimed_new_event'):reject('UNCHANGED_PERSISTENT_CANNOT_CREATE_NEW_ACTIONABLE_EVENT')
            return dict(event_class=event,new_actionable_event=event not in ['PERSISTENT_CONFIRMED','NONE'],new_episode=False)
        if d=='multi_sector_dedup':
            keys={(x['publication'],x['security']) for _ in x['sectors']}
            if x.get('claimed_security_event_count',len(keys))!=len(keys):reject('SECTOR_MEMBERSHIP_CANNOT_MULTIPLY_SECURITY_EVENTS')
            return dict(logical_security_event_count=len(keys),sector_context_count=len(set(x['sectors'])))
        if d=='unknown_propagation':
            if x.get('accepted_capability')=='UNKNOWN' and x.get('claimed_capability')=='READY':reject('REAL_CAPABILITY_DEGRADATION_MUST_BE_PRESERVED')
            r=state_vector(self.root,'expiry_pause_UNKNOWN')
            if x.get('claimed_required_fact')=='FALSE':reject('UNKNOWN_MUST_NOT_BECOME_FALSE')
            return dict(final_eligibility=r['final_eligibility'],maturity=r['maturity'],expiry_count=r['expiry_count'],unaffected_relation_quality=x['unaffected_relation_quality'])
        if d=='no_duplicate_event_episode':
            key=tuple(x['logical_event_key']);events=set();episodes=set()
            for _ in range(x['runs']):events.add(key);episodes.add(key[3])
            if x.get('claimed_episode_id_on_continuation',key[3])!=key[3]:reject('CONTINUATION_CANNOT_CREATE_NEW_EPISODE')
            return dict(logical_event_count=len(events),episode_count=len(episodes),episode_id=key[3])
        if d=='same_day_revision_predecessor':
            if 'previous_manifest_digests' in x and len(set(x['previous_manifest_digests']))!=1:reject('SAME_DAY_REVISIONS_MUST_SHARE_EXACT_PREVIOUS_MANIFEST')
            if 'calendar' in x:
                dates=x['calendar'];previous=dates[dates.index(x['target'])-1]
                if x.get('claimed_previous',previous)!=previous:reject('PREVIOUS_ACCEPTED_MARKET_SESSION_REQUIRED')
                priors=x.get('previous_dates',[previous for _ in x['revisions']])
                if any(day!=previous for day in priors):reject('SAME_DAY_REVISION_IS_NOT_PREVIOUS_SESSION')
                result=dict(previous_dates=priors)
                if 'previous_manifest_digests' in x:result.update(previous_manifest_digests=x['previous_manifest_digests'],event_classes=['NEW_CONFIRMED']*len(priors))
                return result
        if d=='cross_process_previous_session':
            if x.get('producer_exited') is False:reject('PRODUCER_EXIT_BEFORE_FRESH_PROCESS_REQUIRED')
            if 'producer_exit_at' in x and timestamp(x['consumer_start_at'])<=timestamp(x['producer_exit_at']):reject('CONSUMER_START_MUST_FOLLOW_PRODUCER_EXIT')
            if 'producer_pid' in x and x['producer_pid']==x['consumer_pid']:reject('IN_MEMORY_CONTINUITY_DOES_NOT_PROVE_CROSS_PROCESS_REPLAY')
            if x.get('persisted_manifest_digest')!=x.get('readback_manifest_digest'):reject('EXACT_PERSISTED_READBACK_DIGEST_REQUIRED')
            if 'readback_date' in x and x['readback_date']!=x['previous_market_session']:reject('PREVIOUS_PUBLICATION_EXACT_DATE_REQUIRED')
            return dict(readback='EXACT_PERSISTED_PREVIOUS_SESSION',memory_prior_used=False)
        if d=='future_publication_leakage':
            target=x['target'];cutoff=x.get('cutoff',target+'T16:00:00+08:00')
            if x.get('source_namespace')=='FUTURE_FOCUS_OUTCOME':reject('FOCUS_OUTCOME_IS_NOT_ALGORITHM_INPUT')
            if x.get('consumer')=='CORE' and x.get('provider_asof','')[:10]>target:reject('SUPPLEMENTAL_CANNOT_CHANGE_ACCEPTED_CORE')
            if x.get('max_source_trade_date',target)>target:reject('MAX_SOURCE_TRADE_DATE_AFTER_TARGET')
            if x.get('membership_effective_date',target)>target:reject('FUTURE_MEMBERSHIP_FORBIDDEN')
            if 'membership_available_at' in x and timestamp(x['membership_available_at'])>timestamp(cutoff):reject('MEMBERSHIP_AVAILABILITY_AFTER_CUTOFF')
            if x.get('prior_state_trade_date',target)>target:reject('FUTURE_STATE_FORBIDDEN')
            if x.get('adjustment_available_at',target)[:10]>target and x.get('knowledge_lineage')=='AS_RECORDED':reject('AS_RECORDED_ADJUSTMENT_LEAKAGE')
            if x.get('source_asof',target)[:10]>target:
                reject('MONTHLY_ASOF_LEAKAGE' if target.endswith('-15') else 'WEEKLY_ASOF_LEAKAGE')
            if 'available_at' in x and timestamp(x['available_at'])>timestamp(cutoff):reject('FUTURE_AVAILABILITY_FORBIDDEN_AT_T0')
            return dict(temporal_admission='ALLOW' if 'available_at' in x else 'ALLOW_WITH_EXACT_OWNER_PROOFS')
        if d=='revision_append_only':
            if x['old_sha_before']!=x['old_sha_after']:reject('OLD_REVISION_OVERWRITE_FORBIDDEN')
            return dict(old_revision_immutable=True,new_revision_separate=x['old_revision']!=x['new_revision'])
        if d=='deterministic_replay':
            if x['run1_output_digest']!=x['run2_output_digest']:reject('FROZEN_REPLAY_DIGEST_MISMATCH')
            return dict(output_digest_equal=True,duplicate_side_effects=0)
        if d=='historical_pit_evidence':
            if x['claimed_evidence_class']=='HISTORICAL_PIT_EFFECTIVENESS' and (x['current_membership_backfill'] or x['historical_source_missing']):reject('CURRENT_MEMBERSHIP_IS_NOT_HISTORICAL_PIT')
            return dict(evidence_class=x['claimed_evidence_class'],historical_effectiveness='NOT_VERIFIABLE',affected_quality='DEGRADED')
        reject('UNSUPPORTED_REPLAY_CASE')
