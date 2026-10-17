"""Formal post-promotion contract reader; the Accepted Head is the authority."""
from pathlib import Path
import json
from copy import deepcopy
from .v4_13_io import FrozenContracts,exact,digest
HEAD='data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json'
MANIFEST_SHA='a02e7918826627c2b496d89e546d3f5a408e4c68a1a89bc93946e152e7ca42ec'

def _pg_exact(root,binding):
    """Resolve an accepted contract revision from the shared PG source registry."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound
    result=read_bound(root,binding['path'],binding['sha256'])
    raw=result['raw']
    size=binding.get('bytes',binding.get('byte_count',binding.get('actual_byte_count')))
    if size is not None and len(raw)!=size:raise ValueError('ACCEPTED_SOURCE_BYTES_MISMATCH')
    return raw


def _pg_historical_archive(root,binding):
    """Resolve one frozen historical namespace to its exact PG archive binding."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_bound,read_path
    from .historical_stage_governance_r17 import REGISTRY
    registry=read_path(root,REGISTRY)['value']
    row=next((item for key in ('entries','source_archives','static_byte_archives')
              for item in registry.get(key,[])
              if (item.get('original_namespace',{}).get('path'),
                  item.get('original_namespace',{}).get('sha256'))==(binding.get('path'),binding.get('sha256'))),None)
    if row is None:raise ValueError('UNREGISTERED_HISTORICAL_PG_BINDING')
    original=row['original_namespace'];archive=row['archive']
    if any(binding[k]!=original['bytes'] for k in ('bytes','byte_count') if k in binding):
        raise ValueError('HISTORICAL_PG_NAMESPACE_BYTES_INVALID')
    if archive['sha256']!=binding['sha256'] or archive['bytes']!=original['bytes']:
        raise ValueError('HISTORICAL_PG_ARCHIVE_IDENTITY_INVALID')
    raw=read_bound(root,archive['path'],archive['sha256'])['raw']
    if len(raw)!=archive['bytes']:
        raise ValueError('HISTORICAL_PG_ARCHIVE_BYTES_INVALID')
    return dict(binding,path=archive['path'],sha256=archive['sha256'],bytes=archive['bytes'])

class AcceptedContracts(FrozenContracts):
    def __init__(self,root):
        self.root=Path(root)
        from scripts.validate_r17r1_active_closure import validate_pg
        try: validate_pg(self.root)
        except (AssertionError, KeyError, TypeError) as error: raise ValueError('ACTIVE_CONTRACT_FAMILY_CLOSURE_REQUIRED') from error
        from workbench_db.v4_historical_source_ingress_pg_r1 import read_path
        stage=read_path(self.root,'data/v4/V4_STAGE_ACCEPTED_HEAD.json')['value']
        if stage['accepted_stage_range']!='V4_00_TO_V4_13_ACCEPTED' or stage['v4_13_binding']['path']!=HEAD:raise ValueError('FORMAL_V4_13_ACCEPTED_AUTHORITY_REQUIRED')
        head=json.loads(_pg_exact(self.root,stage['v4_13_binding']))
        if head['external_acceptance']!='EXTERNALLY_ACCEPTED_ENGINEERING_SCOPE' or any(head[k] for k in ['production','shadow','focus','global_mandatory_adoption']):raise ValueError('ACCEPTED_ENGINEERING_SCOPE_REQUIRED')
        if head['candidate']['sha256']!=MANIFEST_SHA:raise ValueError('EXACT_AUDITED_R6_REQUIRED')
        if head['audited_sealed_head']!='f12315bf8e3142aa44e9068c5895004c35c4e23c' or head['tested_runtime_source']!='d370788688c7e1be0fe2e3c9b0b160d93374b4ee' or head['external_authority']['sha256']!='652621971b019a383d387cef2ba40b78eb1000993b55bb6418f5378c80c52222':raise ValueError('EXTERNAL_AUTHORITY_IDENTITY_CHANGED')
        _pg_exact(self.root,head['external_authority'])
        gate=json.loads(_pg_exact(self.root,head['r17a_gate']))
        if gate['R17A_CROSS_STAGE_GOVERNANCE_REPAIR']!='PASS' or head['ALGORITHM_STATE_REPLAY_PASS']!='NOT_GRANTED' or head['capabilities']['V4_13_REAL_SIGNAL_CAPABILITY']!='DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY':raise ValueError('FORMAL_ACCEPTANCE_GATE_OR_CAPABILITY_OVERCLAIM')
        candidate=json.loads(_pg_exact(self.root,head['candidate']))
        entry=json.loads(_pg_exact(self.root,head['formal_entry_contract']))
        if entry['authority_namespace']!=HEAD or entry['amendment_receipt_presence_is_authority'] or head['historical_lineage']['original_publication_contract_refs']!=candidate['contract_refs'] or entry['contract_refs']!=head['contract_refs']:raise ValueError('ACCEPTED_PACKAGE_BINDING_MISMATCH')
        self.refs=head['contract_refs'];self.digest=digest(self.refs)
        if self.digest!=head['contract_digest'] or head['historical_lineage']['original_publication_contract_digest']!=candidate['contract_digest']:raise ValueError('ACCEPTED_PACKAGE_DIGEST_MISMATCH')
        self.config={Path(r['path']).stem.removeprefix('v4_13_').rsplit('_v',1)[0]:json.loads(_pg_exact(self.root,r)) for r in self.refs}
        projection=self.config['projection']
        if projection['version']!='1.2.0' or projection['supersedes']['path']!='config/v4_13_projection_v1_1.json':raise ValueError('PROJECTION_V1_2_LINEAGE_REQUIRED')
        predecessor=json.loads(_pg_exact(self.root,projection['supersedes']))
        if predecessor['contract_id']!=projection['contract_id']:raise ValueError('PROJECTION_FAMILY_CHANGED')
        self.owner_refs=self.config['loo_context']['accepted_owner_bindings']
        self.owners={k:json.loads(_pg_exact(self.root,r)) for k,r in self.owner_refs.items()}
        self.dependencies={k:json.loads(_pg_exact(self.root,r)) for k,r in self.config['loo_context']['accepted_sector_dependencies'].items()}
        for k in ['native_producer','rotation_producer','b2_producer']:_pg_exact(self.root,self.owners['V4_08'][k])
        _pg_exact(self.root,self.config['loo_context']['relative_state']['owner'])
        self.authority=head;self.authority_ref=stage['v4_13_binding']
        # Only the filesystem location of the historical moving namespace is
        # resolved. Frozen contract bytes, identities and business rules stay exact.
        from .historical_stage_governance_r17 import REGISTRY
        original=self.config['membership_consumer_route']['stage_binding']
        archive=_pg_historical_archive(self.root,original)
        exact(self.root,archive)
        self.frozen_config=deepcopy(self.config)
        self.config['membership_consumer_route']['stage_binding']=archive
        self.binding_resolution_receipt=dict(original_namespace=original,archive=archive,registry_path=REGISTRY,scope='EXACT_HISTORICAL_PROMOTION_BINDING_ONLY',current_authority=self.authority_ref)

class CurrentOwnerContracts(FrozenContracts):
    """Read immutable V4-13 contracts through the accepted successor authority."""
    def __init__(self,root):
        from .v4_current_stage_authority import CurrentStageAuthority
        from scripts.validate_r17r1_active_closure import validate_pg
        from .historical_stage_governance_r17 import REGISTRY
        authority=CurrentStageAuthority(root)
        self.root=authority.root;head=authority.predecessor
        if authority.predecessor_ref['path']!=HEAD or head['candidate']['sha256']!=MANIFEST_SHA:
            raise ValueError('EXACT_ACCEPTED_V4_13_PREDECESSOR_REQUIRED')
        try:validate_pg(self.root)
        except (AssertionError,KeyError,TypeError) as error:raise ValueError('ACTIVE_CONTRACT_FAMILY_CLOSURE_REQUIRED') from error
        entry=json.loads(authority.read(head['formal_entry_contract']))
        if entry['authority_namespace']!=HEAD or entry['contract_refs']!=head['contract_refs']:
            raise ValueError('ACCEPTED_PACKAGE_BINDING_MISMATCH')
        self.refs=head['contract_refs'];self.digest=digest(self.refs)
        if self.digest!=head['contract_digest'] or self.digest!=entry['contract_digest']:
            raise ValueError('ACCEPTED_PACKAGE_DIGEST_MISMATCH')
        self.config={Path(r['path']).stem.removeprefix('v4_13_').rsplit('_v',1)[0]:json.loads(authority.read(r)) for r in self.refs}
        self.owner_refs=self.config['loo_context']['accepted_owner_bindings']
        self.owners={k:json.loads(authority.read(r)) for k,r in self.owner_refs.items()}
        self.dependencies={k:json.loads(authority.read(r)) for k,r in self.config['loo_context']['accepted_sector_dependencies'].items()}
        from .v4_13_descendant_contracts import DescendantContracts
        historical=DescendantContracts(root)
        if historical.refs!=self.refs or historical.digest!=self.digest:
            raise ValueError('CURRENT_AND_DESCENDANT_CONTRACT_IDENTITY_MISMATCH')
        for key in ('native_producer','rotation_producer','b2_producer'):historical._historical_exact(self.owners['V4_08'][key])
        self.historical_source_resolutions=historical.resolutions
        authority.read(self.config['loo_context']['relative_state']['owner'])
        self.authority=head;self.authority_ref=authority.predecessor_ref
        self.frozen_config=deepcopy(self.config)
        original=self.config['membership_consumer_route']['stage_binding']
        archive=_pg_historical_archive(self.root,original)
        exact(self.root,archive)
        self.config['membership_consumer_route']['stage_binding']=archive
        self.binding_resolution_receipt=dict(original_namespace=original,archive=archive,registry_path=REGISTRY,
            scope='EXACT_HISTORICAL_PROMOTION_BINDING_ONLY',current_authority=authority.stage_ref)

def current_contracts(root):
    """Stage-aware regression/entry selection; no informal post-promotion fallback."""
    from workbench_db.v4_historical_source_ingress_pg_r1 import read_path
    stage=read_path(root,'data/v4/V4_STAGE_ACCEPTED_HEAD.json')['value']
    if stage['accepted_stage_range']=='V4_00_TO_V4_13_ACCEPTED':return AcceptedContracts(root)
    if stage['accepted_stage_range']=='V4_00_TO_V4_12_ACCEPTED':return FrozenContracts(root)
    if stage['accepted_stage_range'] in ('V4_00_TO_V4_14_ACCEPTED','V4_00_TO_V4_15_ACCEPTED'):return CurrentOwnerContracts(root)
    raise ValueError('UNAUTHORIZED_V4_13_STAGE')
