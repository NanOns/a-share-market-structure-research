"""Create isolated successor templates; never modify accepted R24 modules."""
from pathlib import Path

def build():
    p=Path('scripts/v4_16_real_shadow_runtime.py').read_text()
    replacements={
        'R24 one-session successor':'R24R1 go-forward successor',
        'config/v4_16_runtime_dependencies_v2.json':'config/v4_16_runtime_dependencies_v3.json',
        'reports/r24/activation_simulation':'reports/r24r1/activation_simulation',
        'from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority':'from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority\nfrom workbench_analysis.v4_16_go_forward_authority import GoForwardInputAuthority',
        'self.authority=CurrentStageAuthority(self.root)':"self.authority=GoForwardInputAuthority(self.root,self.deps['go_forward_input'],self.grant['daily_input_authority'],self.grant,self.grant['daily_input_boundary'],self.simulation)",
        "accepted_data_head=c.deps['accepted_data']":"daily_input_authority=c.grant['daily_input_authority'],daily_input_digest=c.grant['daily_input_digest'],immutable_data_head=c.deps['accepted_data']",
        'store=RealArtifactStore(self.db)':'store=CandidateArtifactStore(self.db)',
        "eid=digest([enrollment['logical_event_id'],'SHADOW_V4_FIRST_OBSERVED'])":"eid=cohort_identity(c.authority.contracts['cohort_contract'],dict(enrollment,cohort_namespace='FIRST_OBSERVED'))",
        "cohort_namespace='FIRST_OBSERVED',slot_id=slot_id,":"cohort_namespace='FIRST_OBSERVED',slot_id=slot_id,admission_role='REALTIME_COHORT_ACCEPTANCE',owner_logical_event=enrollment['logical_event_id'],source_manifest_digest=mid,visibility_receipt_ids=[p['receipt_id'] for p in receipts],",
        "enrolled.append(self.db.append('enrollment',eid,dict(enrollment,frozen_t0=frozen)))":"enrolled.append(dict(enrollment,frozen_t0=frozen))",
        "self.db.append('slot',digest([slot_id,revision]),slot)":"self.db.append('slot',digest([slot_id,revision]),slot)\n            for e in enrolled:\n                if not any(old['enrollment_id']==e['enrollment_id'] for old in self.db.rows('enrollment')):\n                    e.update(accepted_at=accepted,observation_slot=dict(slot_id=slot_id,revision=revision),cohort_acceptance='ACCEPTED_REALTIME_WITH_SLOT')\n                    self.db.append('enrollment',e['enrollment_id'],e)\n            validate_admission(self.db,slot,enrolled,projected,store)\n            self.db.append('daily_input',digest([c.authority.daily['daily_input_id'],c.authority.daily['revision']]),dict(c.authority.daily,authority_binding=c.grant['daily_input_authority']))",
        'c.verify_request(request)':"c.verify_request(request)\n        accepted_days=[d for d in self.db.rows('daily_input') if d['target_trade_date']==request['trade_date']]\n        check(not accepted_days or c.authority.daily['revision']>=max(d['revision'] for d in accepted_days),'DAILY_REVISION_ROLLBACK')\n        check(all(d['revision']!=c.authority.daily['revision'] or d['daily_input_digest']==c.authority.daily['daily_input_digest'] for d in accepted_days),'DAILY_REVISION_CONFLICT')",
        'g=self.grant':"g=self.grant\n        check(request['trade_date']==g['target_trade_date'],'EXACT_TARGET_DAILY_INPUT_REQUIRED')\n        check(all(self.sources['sources'][k]['binding']==self.authority.daily['sources'][k]['binding'] for k in self.adapters['mandatory_families']),'DAILY_SOURCE_BINDING_MISMATCH')",
        'self.clock=ClockPolicyResolver(self)':"check(set(self.adapters['mandatory_families'])<=self.sources['sources'].keys(),'MISSING_MANDATORY_SOURCE')\n        self.clock=ClockPolicyResolver(self)",
        'def acquire():':'def acquire():\n            validate_daily_revision(self.db,c.authority.daily)',
        'def accept():':'def accept():\n            validate_daily_revision(self.db,c.authority.daily)',
        "check(row['entity_type']=='STOCK','UNGRANTED_SECTOR_CAPABILITY')":"check(row['entity_type']=='STOCK','UNGRANTED_SECTOR_CAPABILITY')\n                check(row['entity_id'] in c.authority.universe,'OWNER_OUTSIDE_ACCEPTED_UNIVERSE')",
        "self.origin='ACTIVATION_SIMULATION' if self.simulation else 'PIT_OBSERVED'":"check(utc(self.grant['daily_input_boundary'])<=utc(self.clock.resolve(self.grant['target_trade_date'],self.authority.sessions)['scheduled_cutoff_at']),'DAILY_BOUNDARY_AFTER_SLOT_CUTOFF')\n        self.origin='ACTIVATION_SIMULATION' if self.simulation else 'PIT_OBSERVED'",
    }
    for old,new in replacements.items():
        assert old in p,old
        p=p.replace(old,new)
    p+='''

def cohort_identity(contract, enrollment):
    check(contract['contract_id']=='COHORT_V1' and contract['enrollment_key']==['logical_event_id','cohort_namespace'],'ACCEPTED_COHORT_KEY_REQUIRED')
    return digest([enrollment[k] for k in contract['enrollment_key']])

def validate_daily_revision(db,daily):
    accepted=[d for d in db.rows('daily_input') if d['target_trade_date']==daily['target_trade_date']]
    check(not accepted or daily['revision']>=max(d['revision'] for d in accepted),'DAILY_REVISION_ROLLBACK')
    check(all(d['revision']!=daily['revision'] or d['daily_input_digest']==daily['daily_input_digest'] for d in accepted),'DAILY_REVISION_CONFLICT')

class CandidateArtifactStore(RealArtifactStore):
    def append(self,kind,key,value):
        if kind=='enrollment':
            value=dict(value,admission_role='CANDIDATE_ENROLLMENT_TEMPLATE',cohort_acceptance='NOT_COHORT_ACCEPTANCE')
        return super().append(kind,key,value)

def validate_admission(db,slot,enrollments,projected,store):
    # All writes are provisional inside the same transaction until this succeeds.
    check(slot['slot_status']=='ACCEPTED_ON_TIME','ADMISSION_REQUIRES_ACCEPTED_SLOT')
    events={store.read(b)['logical_event_id']:store.read(b) for b in projected['logical_events']}
    for e in enrollments:
        if e['T0']!=slot['trade_date']:continue  # Preserve previous original identity.
        if any(a['enrollment_id']==e['enrollment_id'] for a in db.rows('realtime_admission')):continue
        check(e['logical_event_id'] in events,'ADMISSION_REQUIRES_EXACT_OWNER_EVENT')
        check(events[e['logical_event_id']]['event_trade_date']==e['T0'],'RECONSTRUCTED_EVENT_CANNOT_UPGRADE')
        check(e['enrollment_id']==cohort_identity(db.controller.authority.contracts['cohort_contract'],e),'COHORT_IDENTITY_MISMATCH')
        e['observation_slot']=dict(slot_id=slot['slot_id'],revision=slot['revision'])
        # Existing fact payload is immutable: the persisted admission links the
        # accepted slot independently, rather than rewriting an enrollment.
        db.append('realtime_admission',e['enrollment_id'],dict(enrollment_id=e['enrollment_id'],
            logical_event_id=e['logical_event_id'],cohort_namespace=e['cohort_namespace'],
            accepted_at=slot['accepted_at'],observation_slot=e['observation_slot'],
            source_manifest_digest=slot['source_manifest_digest'],visibility_receipt_ids=slot['visibility_receipt_ids'],
            owner_event=events[e['logical_event_id']],admission_role='REALTIME_COHORT_ACCEPTANCE'))
'''
    Path('scripts/v4_16_go_forward_shadow_runtime.py').write_text(p,encoding='utf8',newline='\n')

if __name__=='__main__':build()
