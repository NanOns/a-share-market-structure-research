"""Formal post-promotion contract reader; the Accepted Head is the authority."""
from pathlib import Path
import json
from copy import deepcopy
from .v4_13_io import FrozenContracts,exact,digest
HEAD='data/v4/V4_13_ACCEPTED_HEAD.json'
MANIFEST_SHA='a02e7918826627c2b496d89e546d3f5a408e4c68a1a89bc93946e152e7ca42ec'
class AcceptedContracts(FrozenContracts):
    def __init__(self,root):
        self.root=Path(root)
        stage=json.loads((self.root/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())
        if stage['accepted_stage_range']!='V4_00_TO_V4_13_ACCEPTED' or stage['v4_13_binding']['path']!=HEAD:raise ValueError('FORMAL_V4_13_ACCEPTED_AUTHORITY_REQUIRED')
        head=json.loads(exact(self.root,stage['v4_13_binding']))
        if head['external_acceptance']!='EXTERNALLY_ACCEPTED_ENGINEERING_SCOPE' or any(head[k] for k in ['production','shadow','focus','global_mandatory_adoption']):raise ValueError('ACCEPTED_ENGINEERING_SCOPE_REQUIRED')
        if head['candidate']['sha256']!=MANIFEST_SHA:raise ValueError('EXACT_AUDITED_R6_REQUIRED')
        if head['audited_sealed_head']!='f12315bf8e3142aa44e9068c5895004c35c4e23c' or head['tested_runtime_source']!='d370788688c7e1be0fe2e3c9b0b160d93374b4ee' or head['external_authority']['sha256']!='652621971b019a383d387cef2ba40b78eb1000993b55bb6418f5378c80c52222':raise ValueError('EXTERNAL_AUTHORITY_IDENTITY_CHANGED')
        exact(self.root,head['external_authority'])
        gate=json.loads(exact(self.root,head['r17a_gate']))
        if gate['R17A_CROSS_STAGE_GOVERNANCE_REPAIR']!='PASS' or head['ALGORITHM_STATE_REPLAY_PASS']!='NOT_GRANTED' or head['capabilities']['V4_13_REAL_SIGNAL_CAPABILITY']!='DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY':raise ValueError('FORMAL_ACCEPTANCE_GATE_OR_CAPABILITY_OVERCLAIM')
        candidate=json.loads(exact(self.root,head['candidate']))
        entry=json.loads(exact(self.root,head['formal_entry_contract']))
        if entry['authority_namespace']!=HEAD or entry['amendment_receipt_presence_is_authority'] or head['contract_refs']!=candidate['contract_refs'] or entry['contract_refs']!=head['contract_refs']:raise ValueError('ACCEPTED_PACKAGE_BINDING_MISMATCH')
        self.refs=head['contract_refs'];self.digest=digest(self.refs)
        if self.digest!=head['contract_digest'] or self.digest!=candidate['contract_digest']:raise ValueError('ACCEPTED_PACKAGE_DIGEST_MISMATCH')
        self.config={Path(r['path']).stem.removeprefix('v4_13_').rsplit('_v',1)[0]:json.loads(exact(self.root,r)) for r in self.refs}
        projection=self.config['projection']
        if projection['version']!='1.2.0' or projection['supersedes']['path']!='config/v4_13_projection_v1_1.json':raise ValueError('PROJECTION_V1_2_LINEAGE_REQUIRED')
        predecessor=json.loads(exact(self.root,projection['supersedes']))
        if predecessor['contract_id']!=projection['contract_id']:raise ValueError('PROJECTION_FAMILY_CHANGED')
        self.owner_refs=self.config['loo_context']['accepted_owner_bindings']
        self.owners={k:json.loads(exact(self.root,r)) for k,r in self.owner_refs.items()}
        self.dependencies={k:json.loads(exact(self.root,r)) for k,r in self.config['loo_context']['accepted_sector_dependencies'].items()}
        for k in ['native_producer','rotation_producer','b2_producer']:exact(self.root,self.owners['V4_08'][k])
        exact(self.root,self.config['loo_context']['relative_state']['owner'])
        self.authority=head;self.authority_ref=stage['v4_13_binding']
        # Only the filesystem location of the historical moving namespace is
        # resolved. Frozen contract bytes, identities and business rules stay exact.
        from .historical_stage_governance_r17 import resolve,REGISTRY
        original=self.config['membership_consumer_route']['stage_binding']
        resolved=resolve(self.root,original)
        archive=dict(original,path=resolved.relative_to(self.root).as_posix())
        exact(self.root,archive)
        self.frozen_config=deepcopy(self.config)
        self.config['membership_consumer_route']['stage_binding']=archive
        self.binding_resolution_receipt=dict(original_namespace=original,archive=archive,registry_path=REGISTRY,scope='EXACT_HISTORICAL_PROMOTION_BINDING_ONLY',current_authority=self.authority_ref)

def current_contracts(root):
    """Stage-aware regression/entry selection; no informal post-promotion fallback."""
    stage=json.loads((Path(root)/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())
    if stage['accepted_stage_range']=='V4_00_TO_V4_13_ACCEPTED':return AcceptedContracts(root)
    if stage['accepted_stage_range']=='V4_00_TO_V4_12_ACCEPTED':return FrozenContracts(root)
    raise ValueError('UNAUTHORIZED_V4_13_STAGE')
