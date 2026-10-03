"""Exact accepted replay authority; no latest discovery or source fallback."""
from pathlib import Path
import json
from .v4_14_replay_io import exact,ref,digest
NAMES=['replay_gate_b_contract','replay_case_registry','temporal_non_edge_registry','quality_degradation','machine_vectors']
class ReplayAuthority:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.external_audit_ref=dict(path='docs/evidence/r18/V4_R17R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md',sha256='9a8cc8c92599d6aa843e1fdb9eefe498361ba37b55dd2091c13c6eb75f403d43',bytes=3583)
        audit=exact(self.root,self.external_audit_ref).decode('utf8')
        if 'PASS_FULL_CONTRACT_AUTHORITY_CLOSURE' not in audit or 'AUTHORIZED_NEXT_SCOPED_ENGINEERING' not in audit:raise ValueError('REPLAY_RUNTIME_NOT_EXTERNALLY_AUTHORIZED')
        from scripts.validate_r17r1_active_closure import validate,walk
        try:validate(self.root)
        except (AssertionError,KeyError) as e:raise ValueError('REPLAY_ACTIVE_AUTHORITY_INVALID') from e
        self.refs=[ref(self.root,'config/v4_14_'+n+'_v1_1.json') for n in NAMES]
        self.config={n:json.loads(exact(self.root,r)) for n,r in zip(NAMES,self.refs)}
        self.stage_ref=ref(self.root,'data/v4/V4_STAGE_ACCEPTED_HEAD.json');self.stage=json.loads(exact(self.root,self.stage_ref))
        self.head_ref=self.stage['v4_13_binding'];self.head=json.loads(exact(self.root,self.head_ref))
        self.closure_ref=self.head['active_family_closure'];families=json.loads(exact(self.root,self.closure_ref))['families']
        for r,o in zip(self.refs,self.config.values()):families[o['contract_id']]=dict(active=r)
        try:
            for o in self.config.values():walk(o,families,self.root)
        except AssertionError as e:raise ValueError('REPLAY_SUPERSEDED_AUTHORITY') from e
        for o in self.config.values():
            if o['version']!='1.1.0' or o['accepted_v4_13_authority']!=self.head_ref or o['active_family_closure']!=self.closure_ref:raise ValueError('REPLAY_PACKAGE_AUTHORITY_MISMATCH')
        self.package_digest=digest(self.refs)
        self.data_ref=ref(self.root,'data/v4/V4_DATA_ACCEPTED_HEAD.json');self.data=json.loads(exact(self.root,self.data_ref))
        self.calendar_ref=self.data['calendar'];self.calendar=json.loads(exact(self.root,self.calendar_ref))
        self.owners={k:self.stage[k+'_binding'] for k in ['v4_07','v4_08','v4_09','v4_10','v4_11','v4_12','v4_13']}
        for r in self.owners.values():exact(self.root,r)
        self.membership_ref=ref(self.root,'data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json');exact(self.root,self.membership_ref)
    def previous(self,target):
        sessions=self.calendar['session_dates'];dates=[s['trade_date'] if isinstance(s,dict) else s for s in sessions]
        if target not in dates or dates.index(target)==0:raise ValueError('REPLAY_EXACT_PREVIOUS_MARKET_SESSION_REQUIRED')
        return dates[dates.index(target)-1]
    def bindings(self):return dict(amended_v4_13=self.head_ref,contract_package=self.refs,active_family_closure=self.closure_ref,data=self.data_ref,stage=self.stage_ref,calendar=self.calendar_ref,membership=self.membership_ref,owners=self.owners,external_audit=self.external_audit_ref)
