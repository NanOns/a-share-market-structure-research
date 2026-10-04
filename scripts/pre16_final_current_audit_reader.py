"""Explicit V2 formalized authority for R22; V1 remains historical evidence."""
from copy import deepcopy
from scripts.r22_io import ROOT,HEAD,read
from scripts.validate_pre16_finalization import validate

class FinalCurrentAuditStatus:
    def __init__(self,root=ROOT):
        self.root=root;self.validation=validate(root);self.head=read(HEAD,root)
    def canonical_entry(self,issue_id):
        validate(self.root,head=self.head)
        e=self.head['entries'][issue_id]
        return deepcopy(self.head['entries'][e['canonical_issue_id']])
    def global_contract_entry_blockers(self):return [] if validate(self.root,head=self.head) else None
    def _blockers(self,field):
        validate(self.root,head=self.head)
        return sorted(k for k,e in self.head['entries'].items() if e['alias_of'] is None and e[field])
    def runtime_activation_blockers(self):return self._blockers('blocks_v4_16_runtime_activation')
    def capability_shadow_blockers(self):return self._blockers('blocks_affected_capability_in_shadow')
    def production_cutover_blockers(self):return self._blockers('blocks_production_cutover_for_scope')
    def stage_permission(self):return False
