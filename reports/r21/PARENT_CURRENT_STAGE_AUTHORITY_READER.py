"""Current V4-14 governance authority; never invokes historical stage validators."""
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
        self.contract=json.loads((self.root/'config/v4_current_stage_authority_v1.json').read_bytes())
        self.stage_ref=ref(self.root,self.contract['stage_namespace']);self.stage=json.loads(self.read(self.stage_ref))
        if self.stage['accepted_stage_range']!='V4_00_TO_V4_14_ACCEPTED':raise ValueError('CURRENT_STAGE_MUST_BE_V4_14')
        if self.stage['v4_14_entry']!='COMPLETED_EXTERNALLY_ACCEPTED_CAPABILITY_SCOPED_REPLAY_GATE_B':raise ValueError('CURRENT_V4_14_ENTRY_INCOHERENT')
        if self.stage['v4_15_entry']!='CONTRACT_FREEZE_EXTERNALLY_ACCEPTED_RUNTIME_ENGINEERING_AUTHORIZED_AFTER_R20A':raise ValueError('V4_15_ENGINEERING_ENTRY_REQUIRED')
        self.head_ref=self.stage['v4_14_binding']
        if self.head_ref!=self.contract['current_head'] or self.head_ref['path']!='data/v4/V4_14_ACCEPTED_HEAD.json':raise ValueError('EXACT_CURRENT_V4_14_REQUIRED')
        self.head=json.loads(self.read(self.head_ref));self.entry=json.loads(self.read(self.head['entry_contract']))
        if self.head['status']!='ALGORITHM_STATE_REPLAY_DEGRADED_PASS' or self.head['ALGORITHM_STATE_REPLAY_PASS']!='DEGRADED_PASS_CAPABILITY_SCOPED' or self.head['HISTORICAL_PIT_EFFECTIVENESS']!='NOT_GRANTED':raise ValueError('CAPABILITY_SCOPED_REPLAY_REQUIRED')
        if self.head['bindings']!=self.entry['bindings'] or self.head['capabilities']!=self.entry['capabilities']:raise ValueError('ACCEPTED_ENTRY_MISMATCH')
        if self.entry['accepted_head_namespace']!=self.head_ref['path'] or self.head['stage']!='V4-14':raise ValueError('CURRENT_ENTRY_NAMESPACE')
        for obj in [self.head,self.entry,self.contract]:
            if any(obj.get(k,False) is not False for k in ['production','shadow','focus','V4_15_runtime','V4_15_accepted','V4_16']):raise ValueError('PERMISSION_OVERCLAIM')
        if any(self.stage[k] is not False for k in ['production_permission','shadow_production_permission','focus_cutover_permission']):raise ValueError('STAGE_PERMISSION_OVERCLAIM')
        if (self.root/'data/v4/V4_15_ACCEPTED_HEAD.json').exists():raise ValueError('V4_15_ACCEPTED_HEAD_FORBIDDEN')
        self.owners=self.contract['immutable_owner_heads']
        if set(self.owners)!=set('v4_%02d'%n for n in range(7,15)):raise ValueError('COMPLETE_IMMUTABLE_OWNER_SET_REQUIRED')
        if self.owners!={k:self.stage[k+'_binding'] for k in self.owners}:raise ValueError('OWNER_AUTHORITY_MISMATCH')
        for binding in self.owners.values():self.read(binding)
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
        if 'EXTERNALLY_ACCEPTED_CONTRACT_SCOPE_RUNTIME_ENTRY_BLOCKED' not in audit:raise ValueError('R19_EXTERNAL_CONTRACT_ACCEPTANCE_REQUIRED')
        self.allowed_publications=[]
        seal=json.loads(self.read(self.head['bindings']['runtime_seal']))
        self.allowed_publications=seal['replay_publications']
    def read(self,binding):
        if self.exact_reader is None:return exact(self.root,binding)
        raw,receipt=self.exact_reader.read(binding);self.portability_receipts.append(receipt);return raw
    def bindings(self):
        return dict(current_v4_14=self.head_ref,stage=self.stage_ref,data=self.data_ref,calendar=self.calendar_ref,membership=self.membership_ref,identity=self.identity_ref,owners=self.owners,contract_package=self.package_ref,external_audit=self.external_audit_ref)
    def publication(self,binding):
        if binding not in self.allowed_publications:raise ValueError('PUBLICATION_NOT_SEALED_BY_ACCEPTED_V4_14')
        return json.loads(self.read(binding))
