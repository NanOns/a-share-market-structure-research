"""V3 descriptive candidate reader; permission is never inferred from blockers."""
from copy import deepcopy
from scripts.r22r1_io import ROOT,HEAD,read
from scripts.validate_r22r1_contracts import normalize_compare
class NormalizedCurrentAuditStatus:
    def __init__(self,root=ROOT):self.root=root;normalize_compare(root)
    def canonical_entry(self,key):
        normalize_compare(self.root);h=read(HEAD,self.root);return deepcopy(h['entries'][h['entries'][key]['canonical_issue_id']])
    def blockers(self,field):
        normalize_compare(self.root);h=read(HEAD,self.root)
        return sorted(k for k,e in h['entries'].items() if e['alias_of'] is None and e[field])
    def stage_permission(self):return False
