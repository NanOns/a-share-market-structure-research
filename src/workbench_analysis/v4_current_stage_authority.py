"""Versioned current governance with explicit immutable V4-14 publication authority."""
import json
from pathlib import Path
from .v4_14_replay_io import exact,ref

class CurrentStageAuthority:
    def __init__(self,root,exact_reader=None):
        self.root=Path(root).resolve();self.portability_receipts=[]
        if exact_reader is None:
            from .v4_portable_exact import PortableExact
            exact_reader=PortableExact(self.root)
        self.exact_reader=exact_reader
        stage=json.loads((self.root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())
        self.is_v15=stage['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED'
        name='v4_current_stage_authority_v2.json' if self.is_v15 else 'v4_current_stage_authority_v1.json'
        self.contract=json.loads((self.root/'config'/name).read_bytes())
        if self.contract['V4_15_accepted'] is not self.is_v15:raise ValueError('CURRENT_ACCEPTANCE_COHERENCE')
        self.stage_ref=ref(self.root,self.contract['stage_namespace']);self.stage=json.loads(self.read(self.stage_ref))
        expected='V4_00_TO_V4_15_ACCEPTED' if self.is_v15 else 'V4_00_TO_V4_14_ACCEPTED'
        if self.stage['accepted_stage_range']!=expected or self.contract['accepted_stage_range']!=expected:raise ValueError('CURRENT_STAGE_MISMATCH')
        if self.stage['v4_14_entry']!='COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_REPLAY_GATE_B':raise ValueError('CURRENT_V4_14_ENTRY_INCOHERENT')
        entry_status='COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_RUNTIME' if self.is_v15 else 'CONTRACT_FREEZE_EXTERNALLY_ACCEPTED_RUNTIME_ENGINEERING_AUTHORIZED_AFTER_R20A'
        if self.stage['v4_15_entry']!=entry_status:raise ValueError('V4_15_ENTRY_INCOHERENT')
        self.head_ref=self.stage['v4_15_binding' if self.is_v15 else 'v4_14_binding']
        namespace='data/v4/V4_15_ACCEPTED_HEAD.json' if self.is_v15 else 'data/v4/V4_14_ACCEPTED_HEAD.json'
        if self.head_ref!=self.contract['current_head'] or self.head_ref['path']!=namespace:raise ValueError('EXACT_CURRENT_HEAD_REQUIRED')
        self.current_head=self.head_ref
        self.head=json.loads(self.read(self.head_ref));self.entry=json.loads(self.read(self.head['entry_contract']))
        if self.head['bindings']!=self.entry['bindings'] or self.head['capabilities']!=self.entry['capabilities']:raise ValueError('ACCEPTED_ENTRY_MISMATCH')
        if self.entry['accepted_head_namespace']!=namespace or self.head['stage']!=('V4-15' if self.is_v15 else 'V4-14'):raise ValueError('CURRENT_ENTRY_NAMESPACE')
        if self.head['HISTORICAL_PIT_EFFECTIVENESS']!='NOT_GRANTED':raise ValueError('PIT_NOT_GRANTED')
        if self.is_v15:
            if self.head['status']!='RUNTIME_ENGINEERING_PASS_CAPABILITY_SCOPED' or self.contract['V4_15_accepted'] is not True:raise ValueError('SCOPED_V4_15_REQUIRED')
            if self.head['CURRENT_REAL_MATURITY_EVIDENCE']!='NONE' or self.head['PROVED_HORIZONS']!=[] or self.head['UNPROVED_HORIZONS']!=[1,3,5,10,20] or self.head['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME']!='NOT_GRANTED_PENDING_MATURITY_EVIDENCE' or self.head['REALTIME_ACCEPTED_COHORT_MATURITY']!='NOT_GRANTED':raise ValueError('MATURITY_OVERCLAIM')
        elif self.head['status']!='ALGORITHM_STATE_REPLAY_DEGRADED_PASS' or self.head['ALGORITHM_STATE_REPLAY_PASS']!='DEGRADED_PASS_CAPABILITY_SCOPED':raise ValueError('SCOPED_V4_14_REQUIRED')
        for obj in [self.head,self.entry,self.contract]:
            if any(obj.get(k,False) is not False for k in ['production','shadow','focus','V4_16']):raise ValueError('PERMISSION_OVERCLAIM')
        if any(self.stage[k] is not False for k in ['production_permission','shadow_production_permission','focus_cutover_permission']):raise ValueError('STAGE_PERMISSION_OVERCLAIM')
        self.owners=self.contract['immutable_owner_heads']
        if set(self.owners)!=set('v4_%02d'%n for n in range(7,15)):raise ValueError('COMPLETE_IMMUTABLE_OWNER_SET_REQUIRED')
        if self.owners!={k:self.stage[k+'_binding'] for k in self.owners}:raise ValueError('OWNER_AUTHORITY_MISMATCH')
        for binding in self.owners.values():self.read(binding)
        self.replay_head_ref=self.owners['v4_14'];self.replay_head=json.loads(self.read(self.replay_head_ref))
        if self.is_v15 and self.contract['predecessor_v4_14']!=self.replay_head_ref:raise ValueError('EXPLICIT_REPLAY_PREDECESSOR_REQUIRED')
        self.predecessor_ref=self.owners['v4_13'];self.predecessor=json.loads(self.read(self.predecessor_ref))
        self.data_ref=self.contract['data_head'];self.data=json.loads(self.read(self.data_ref))
        if self.data['accepted_trade_date']!='2026-09-30' or self.head['bindings']['data_head']!=self.data_ref:raise ValueError('DATA_HEAD_UNCHANGED_REQUIRED')
        self.calendar_ref=self.contract['calendar'];self.calendar=json.loads(self.read(self.calendar_ref))
        if self.calendar_ref!=self.data['calendar']:raise ValueError('CALENDAR_AUTHORITY_MISMATCH')
        self.sessions=[s['trade_date'] if isinstance(s,dict) else s for s in self.calendar['session_dates']]
        self.identity_ref=self.contract['identity'];self.membership_ref=self.contract['membership']
        if self.identity_ref!=self.data['identity'] or self.membership_ref!=self.head['bindings']['membership']:raise ValueError('IDENTITY_MEMBERSHIP_AUTHORITY_MISMATCH')
        self.read(self.identity_ref);self.read(self.membership_ref)
        self.package_ref=self.contract['v4_15_contract_package'];self.package=json.loads(self.read(self.package_ref))
        self.contracts={Path(b['path']).stem.removeprefix('v4_15_').removesuffix('_v1'):json.loads(self.read(b)) for b in self.package['contracts']}
        self.external_audit_ref=self.contract['external_audit'];audit=self.read(self.external_audit_ref).decode('utf8')
        if ('PASS_FINAL_V4_15_RUNTIME_CANDIDATE_CAPABILITY_SCOPED' if self.is_v15 else 'EXTERNALLY_ACCEPTED_CONTRACT_SCOPE_RUNTIME_ENTRY_BLOCKED') not in audit:raise ValueError('R19_EXTERNAL_CONTRACT_ACCEPTANCE_REQUIRED')
        self.allowed_publications=[]
        seal=json.loads(self.read(self.replay_head['bindings']['runtime_seal']))
        self.allowed_publications=seal['replay_publications']
    def read(self,binding):
        # New promotion bytes use literal identity; historical registry stays immutable.
        if binding['path'] in ['data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_15_ACCEPTED_HEAD.json','config/v4_15_accepted_entry_contract_v1.json','config/v4_current_stage_authority_v2.json']:
            return exact(self.root,binding)
        if self.exact_reader is None:return exact(self.root,binding)
        raw,receipt=self.exact_reader.read(binding);self.portability_receipts.append(receipt);return raw
    def bindings(self):
        result=dict(current_v4_14=self.replay_head_ref,stage=self.stage_ref,data=self.data_ref,calendar=self.calendar_ref,membership=self.membership_ref,identity=self.identity_ref,owners=self.owners,contract_package=self.package_ref,external_audit=self.external_audit_ref)
        if self.is_v15:result.update(current_stage_head=self.current_head,replay_predecessor_v4_14=self.replay_head_ref,current_authority_contract=ref(self.root,'config/v4_current_stage_authority_v2.json'))
        return result
    def publication(self,binding):
        if binding not in self.allowed_publications:raise ValueError('PUBLICATION_NOT_SEALED_BY_ACCEPTED_V4_14')
        return json.loads(self.read(binding))

    def publication_authority(self):
        """Explicit immutable V4-14 source view; current governance remains V4-15."""
        from copy import copy
        view=copy(self);view.head_ref=self.replay_head_ref;view.head=self.replay_head
        return view
