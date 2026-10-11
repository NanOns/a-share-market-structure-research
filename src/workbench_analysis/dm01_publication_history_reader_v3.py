"""Current authority plus exact historical views; private validator dependencies."""
from pathlib import Path
from types import FunctionType
from . import dm01_publication_history_reader_v2 as base
from .historical_stage_governance_r17 import STAGE,resolve,registry
from .v4_current_stage_authority import CurrentStageAuthority

CONTRACT='R4_R3_CURRENT_AUTHORITY_EXACT_PUBLICATION_HISTORY_V3'
STAGE_SHA='f7607601de402f2b2bdada84dffdefbacad7f9f66e252c57dfdf045060e90e99'

class Resolver(base.HistoricalBindingResolver):
    def __init__(self,root):
        super().__init__(root)
        self.authority=CurrentStageAuthority(root)

    def resolve(self,logical_path,expected_sha=None):
        name=str(logical_path).replace('\\','/')
        # Validate namespace before selecting any archive.
        physical=super().resolve(logical_path)
        if name==STAGE:
            if expected_sha is not None and expected_sha!=STAGE_SHA:raise ValueError('PUBLICATION_STAGE_ARCHIVE_HASH_MISMATCH')
            return resolve(self.root,dict(path=STAGE,sha256=STAGE_SHA))
        if name=='tests/v4_09/test_stock_prewatch.py':
            row=next(r for r in registry(self.root)['source_archives'] if r['original_namespace']['path']==name)
            ref=row['original_namespace']
            if expected_sha is not None and expected_sha!=ref['sha256']:raise ValueError('PUBLICATION_SOURCE_ARCHIVE_HASH_MISMATCH')
            return resolve(self.root,ref,source=True)
        return super().resolve(logical_path,expected_sha) if expected_sha is not None else physical

def validators(root):
    namespace=dict(base.injected_validators.__globals__,HistoricalBindingResolver=Resolver)
    fn=FunctionType(base.injected_validators.__code__,namespace,base.injected_validators.__name__,base.injected_validators.__defaults__,base.injected_validators.__closure__)
    fn.__kwdefaults__=base.injected_validators.__kwdefaults__
    return fn(root)

def scoped(result,resolver):
    value=base._scope(result,resolver)
    return dict(value,current_authority_contract=CONTRACT,current_stage_binding=resolver.authority.stage_ref,
        current_permission_granted=False,engineering_source_qualification='PENDING_EXTERNAL_ACCEPTANCE')

def validate_v4_09_history(*,project_root):
    resolver,v9,_=validators(project_root);return scoped(v9.validate(),resolver)

def validate_v4_10_history(candidate=None,*,project_root):
    resolver,_,v10=validators(project_root);return scoped(v10.validate(candidate),resolver)

def validate_v4_09_history_head(candidate,global_head,receipt,*,project_root):
    resolver,v9,_=validators(project_root);return scoped(v9.validate_head(candidate,global_head,receipt),resolver)
