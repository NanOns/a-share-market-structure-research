"""Explicit audit-status metadata reader; grants no runtime or stage permissions."""
from pathlib import Path
from scripts.validate_pre16_governance import validate,verify_blocking,read,ROOT,HEAD,CONTRACT
from copy import deepcopy

class CurrentAuditStatus:
    def __init__(self,root=ROOT):
        self.root=Path(root).resolve()
        self.validation=validate(self.root)
        self.contract=read(CONTRACT,self.root)
        self.head=read(HEAD,self.root)

    def entry(self,audit_id):
        verify_blocking(self.head,self.root)
        return deepcopy(self.head['entries'][audit_id])

    def canonical_entry(self,issue_id):
        verify_blocking(self.head,self.root)
        entry=self.head['entries'][issue_id]
        return deepcopy(self.head['entries'][entry['canonical_issue_id']])

    def _blockers(self,field):
        """Sorted canonical issue IDs, deduplicated; no permission inference."""
        verify_blocking(self.head,self.root)
        return sorted(k for k,e in self.head['entries'].items() if e['alias_of'] is None and e[field])

    def global_contract_entry_blockers(self):
        return self._blockers('blocks_v4_16_contract_entry')

    def runtime_activation_blockers(self):
        return self._blockers('blocks_v4_16_runtime_activation')

    def capability_shadow_blockers(self):
        return self._blockers('blocks_affected_capability_in_shadow')

    def production_cutover_blockers(self):
        return self._blockers('blocks_production_cutover_for_scope')

    def stage_permission(self):
        return False
