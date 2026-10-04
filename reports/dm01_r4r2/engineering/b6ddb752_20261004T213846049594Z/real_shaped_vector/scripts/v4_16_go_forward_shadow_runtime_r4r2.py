"""R4R2 startup admission successor. Inherits frozen runtime business methods."""
import json
from pathlib import Path
from scripts.v4_16_go_forward_shadow_runtime import RealShadowController as HistoricalController, dependency_digest, grant_digest
from scripts.v4_16_shadow_runtime import check, exact, utc, ClockPolicyResolver
from scripts.v4_16_go_forward_input_authority_r4r2 import GoForwardInputAuthority

class RealShadowController(HistoricalController):
    def __init__(self, root, simulation_dependencies=None):
        check(simulation_dependencies is None,'R4R2_REAL_CONTROLLER_SIMULATION_FORBIDDEN')
        self.root=Path(root).resolve()
        self.simulation=simulation_dependencies is not None
        path=simulation_dependencies or 'config/v4_16_runtime_dependencies_v4.json'
        if self.simulation:
            check((self.root/path).resolve().is_relative_to(self.root/'reports/r24r1/activation_simulation'), 'ISOLATED_SIMULATION_MANIFEST_REQUIRED')
        self.dependency_path=path
        self.dependency_bytes=(self.root/path).read_bytes()
        self.deps=json.loads(self.dependency_bytes)
        self.activation=json.loads(exact(self.root,self.deps['activation']))
        # Nothing that observes source availability or opens storage precedes this.
        check(self.activation['runtime_authorized'] is True and self.activation['real_shadow_authorized'] is True,
              'REAL_SHADOW_NOT_AUTHORIZED_BEFORE_CONSUMPTION')
        check(self.activation['environment_class']==('ACTIVATION_SIMULATION' if self.simulation else 'REAL'),'AUTHORITY_ENVIRONMENT_MISMATCH')
        check(not any(self.activation[k] for k in ('production','focus','V4_16')),'NON_SHADOW_PERMISSION_FORBIDDEN')
        for binding in self.deps['bindings']: exact(self.root,binding)
        self.grant=self.activation['grant']
        check(self.grant is not None and set(self.activation['required_grant_fields'])<=self.grant.keys(),'INCOMPLETE_ACTIVATION_GRANT')
        acceptance=json.loads(exact(self.root,self.activation['external_acceptance']))
        check(acceptance['authority_digest']==grant_digest(self.activation),'EXTERNAL_AUTHORITY_DIGEST_MISMATCH')
        check(acceptance['decision']==('SIMULATION_ONLY_NOT_REAL_ACCEPTANCE' if self.simulation else 'PASS_REAL_SHADOW_ACTIVATION'), 'EXTERNAL_ACTIVATION_NOT_ACCEPTED')
        check(acceptance['authority_id']==self.activation['authority_id']==self.grant['authority_id'],'AUTHORITY_IDENTITY_MISMATCH')
        check(self.grant['rollback_identity']=='R24_APPEND_ONLY_STOP_V1','UNACCEPTED_ROLLBACK_IDENTITY')
        check(self.grant['runtime_dependency_contract_id']==self.deps['contract_id'] and self.grant['dependency_set_digest']==dependency_digest(self.deps),'DEPENDENCY_SET_MISMATCH')
        for key in ('clock','slot','storage','source_adapters','initialization_boundary'):
            check(self.grant[key]==self.deps[key],'UNACCEPTED_'+key.upper())
        self.storage=json.loads(exact(self.root,self.deps['storage']))
        self.adapters=json.loads(exact(self.root,self.deps['source_adapters']))
        self.boundary=json.loads(exact(self.root,self.deps['initialization_boundary']))
        self.sources=json.loads(exact(self.root,self.grant['source_authority']))
        check(self.sources['environment_class']==self.activation['environment_class'],'SOURCE_ENVIRONMENT_MISMATCH')
        check(self.sources['adapter_id']==self.adapters['adapter_id'],'UNACCEPTED_SOURCE_ADAPTER')
        check(self.sources['owner_heads']==self.deps['owner_heads'],'UNACCEPTED_OWNER_HEADS')
        check(set(self.adapters['mandatory_families'])<=self.sources['sources'].keys(),'MISSING_MANDATORY_SOURCE')
        self.clock=ClockPolicyResolver(self)
        self.authority=GoForwardInputAuthority(self.root,self.deps['go_forward_input'],self.grant['daily_input_authority'],self.grant,self.grant['daily_input_boundary'],self.simulation)
        check(utc(self.grant['daily_input_boundary'])<=utc(self.clock.resolve(self.grant['target_trade_date'],self.authority.sessions)['scheduled_cutoff_at']),'DAILY_BOUNDARY_AFTER_SLOT_CUTOFF')
        self.origin='ACTIVATION_SIMULATION' if self.simulation else 'PIT_OBSERVED'
        identity=self.grant['storage_identity']
        check(identity['namespace']=='SHADOW_V4' and identity['execution_mode']=='SHADOW' and identity['evidence_origin']==self.origin
              and identity['migration']==self.deps['migration'],'UNACCEPTED_STORAGE_IDENTITY')
        self.slot_fields=json.loads(exact(self.root,self.deps['slot']))['fields']
        self.guard()

