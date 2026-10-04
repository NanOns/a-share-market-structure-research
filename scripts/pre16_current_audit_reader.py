"""Explicit audit-status metadata reader; grants no runtime or stage permissions."""
from pathlib import Path
from scripts.validate_pre16_governance import validate,read,ROOT,HEAD,CONTRACT

class CurrentAuditStatus:
    def __init__(self,root=ROOT):
        self.root=Path(root).resolve()
        self.validation=validate(self.root)
        self.contract=read(CONTRACT,self.root)
        self.head=read(HEAD,self.root)

    def entry(self,audit_id):
        from copy import deepcopy
        return deepcopy(self.head['entries'][audit_id])

    def stage_permission(self):
        return False
