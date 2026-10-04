"""Repository-wide pinned baseline scan plus explicit reviewed reference classes."""
import json,subprocess
from scripts.pre16_governance_io import ROOT,BASE,R1,ref
NEEDLE='V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1'
def scan(root=ROOT):
    # Require a token boundary: R10/R13/R15 are not R1 consumers.
    cmd=['git','grep','-n','-I','-E',NEEDLE+'([^0-9A-Za-z_]|$)',BASE,'--']
    r=subprocess.run(cmd,cwd=root,capture_output=True);assert r.returncode in [0,1]
    rows=[]
    for line in r.stdout.decode('utf8').splitlines():
        _,path,number,text=line.split(':',3)
        if path.startswith('src/'):
            category='UNKNOWN';reason='Requires explicit runtime data-flow review; never auto-dismiss source hits.'
        elif path.startswith('config/') or path=='data/v4/V4_STAGE_ACCEPTED_HEAD.json':
            category='GOVERNANCE_REFERENCE_ONLY';reason='Historical protected_bindings / Stage provenance metadata, not current status permission.'
        elif path.startswith(('docs/','reports/','tests/','scripts/','data/')):
            category='HISTORICAL_EVIDENCE_ONLY';reason='Versioned historical evidence, archived entry/seal/validator or test; not live business status selection.'
        else:category='UNKNOWN';reason='Unclassified baseline reference.'
        rows.append(dict(path=path,line=int(number),classification=category,reason=reason,excerpt=text[:320]))
    # Indirect consumers read field_rules and owner authority, never protected registry statuses.
    indirect=['src/workbench_analysis/dm01_source_boundary_r2.py','src/workbench_analysis/source_authority_accepted_owners_v1.py','src/workbench_analysis/source_authority_producers_r3.py','src/workbench_analysis/source_authority_producers_r4.py','src/workbench_analysis/source_authority_governance_r1.py','src/workbench_analysis/v4_current_stage_authority.py']
    reviewed=[]
    for path in indirect:
        text=(root/path).read_text(encoding='utf8');assert NEEDLE not in text and 'open_audit_registry' not in text
        reviewed.append(dict(binding=ref(path,root),classification='GOVERNANCE_REFERENCE_ONLY',data_flow='Explicit accepted owner / field_rules / current-head inputs; does not interpret historical registry status or protected_bindings as current audit permissions.'))
    counts={k:sum(x['classification']==k for x in rows) for k in ['HISTORICAL_EVIDENCE_ONLY','GOVERNANCE_REFERENCE_ONLY','CURRENT_RUNTIME_CONSUMER','UNKNOWN']}
    return dict(contract_id='PRE16_STALE_R1_CONSUMER_SCAN_V1',execution_baseline=BASE,scope='ALL_TRACKED_BASELINE_TEXT_FILES; UNRELATED_UNTRACKED_WORK_NOT_AN_AUTHORITY',command=cmd,matches=rows,counts=counts,indirect_runtime_data_flow_review=reviewed,current_runtime_consumers=0,unresolved=len([x for x in rows if x['classification']=='UNKNOWN']),repair_required=bool(counts['CURRENT_RUNTIME_CONSUMER'] or counts['UNKNOWN']),no_latest_discovery=True)
