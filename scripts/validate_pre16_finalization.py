"""Independent exact external acceptance and mechanical transition gate."""
import hashlib,json,subprocess
from copy import deepcopy
from scripts.r22_io import ROOT,BASE,HEAD,CONFIG,ACCEPT,AUDIT,OLD_HEAD,OLD_CONFIG,read,baseline,ref
from scripts.validate_pre16_governance import require,exact
AUDIT_SHA='80f9d86e8eba67125cab4708256e0b0f6d3f14c1206db2650e616465e8e72fc5'

def validate(root=ROOT,head=None,accepted=None):
    h=read(HEAD,root) if head is None else head;a=read(ACCEPT,root) if accepted is None else accepted
    b=ref(AUDIT,root);require(b['sha256']==AUDIT_SHA,'EXACT_FINAL_EXTERNAL_AUDIT')
    require(a['external_authority']==b and a['external_decision']=='PASS_FINAL_CANONICAL_BLOCK_SCOPE_REPAIR','EXACT_FINAL_EXTERNAL_DECISION')
    require(a['contract_id']=='V4_PRE16_GOVERNANCE_ACCEPTED_HEAD_R1' and a['version']=='1.0.0' and a['status']=='EXTERNALLY_ACCEPTED_GOVERNANCE_ONLY' and a['grant']=='PRE16_GOVERNANCE_ACCEPTANCE_ONLY; R22 CONTRACT ENTRY SUBJECT TO INDEPENDENT FORMALIZATION GATE','GOVERNANCE_ACCEPTANCE_NOT_RUNTIME')
    require(a['Stage']=='V4_00_TO_V4_15_ACCEPTED' and a['Data']=='2026-09-30','ACCEPTANCE_STAGE_DATA_SCOPE')
    require(a['audited_remote_head']==a['execution_baseline']==BASE,'EXACT_AUDITED_HEAD')
    source='dabb5eb2fcdd4b52cfa4d9d684f9d9a9786c42bf';tag='refs/tags/codex/pre16-gov-r1-1-tested-source-20261004-r1'
    require(a['tested_source']==source and a['tested_tag']==tag,'EXACT_TESTED_SOURCE_TAG')
    require(subprocess.check_output(['git','rev-parse',tag+'^{commit}'],cwd=root).decode().strip()==source,'IMMUTABLE_TESTED_REF')
    require(subprocess.run(['git','merge-base','--is-ancestor',source,BASE],cwd=root,capture_output=True).returncode==0,'AUDITED_TESTED_ANCESTRY')
    old=json.loads(baseline(OLD_HEAD,root));old_c=json.loads(baseline(OLD_CONFIG,root))
    require(exact(a['audited_head'],root)==baseline(OLD_HEAD,root) and exact(a['audited_config'],root)==baseline(OLD_CONFIG,root),'AUDITED_V1_BYTES')
    require(exact(a['candidate_seal'],root)==baseline('reports/pre16_governance_r1_1/PRE16_GOV_R1_1_CANDIDATE_SEAL.json',root),'AUDITED_R11_SEAL')
    closed={'GOV_PRE16_01':'EXTERNALLY_ACCEPTED_CLOSED','GOV_PRE16_02':'EXTERNALLY_ACCEPTED_CLOSED'}
    require(a['closed_findings']==h['governance_findings']==closed,'ONLY_TWO_GOVERNANCE_DISPOSITIONS')
    require(h['external_acceptance']==ref(ACCEPT,root) and h['supersedes_current_head']==ref(OLD_HEAD,root),'EXACT_ACCEPTANCE_SUCCESSOR')
    require(set(h['entries'])==set(old['entries']),'NO_CAPABILITY_ITEM_MUTATION')
    for key,e in old['entries'].items():
        expected=deepcopy(e)
        if key=='GOV_PRE16_01':
            expected.update(current_state='EXTERNALLY_ACCEPTED_CLOSED',blocking_scope='NONE',blocks_v4_16_contract_entry=False,blocks_v4_16_runtime_activation=False,blocks_affected_capability_in_shadow=False,blocks_production_cutover_for_scope=False,blocks_engineering_stage=False,blocks_shadow_entry=False,blocks_production_cutover=False,external_acceptance=ref(ACCEPT,root))
        require(h['entries'][key]==expected,'MECHANICAL_ONLY_'+key)
    mutable={'contract_id','version','execution_baseline','status','supersedes_current_head','GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS','V4_16_entry','NEXT','entries'}
    for key,value in old.items():
        if key not in mutable:require(h[key]==value,'GOVERNANCE_CORE_KEEP_'+key)
    require(h['contract_id']=='V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V2' and h['version']=='2.0.0' and h['execution_baseline']==BASE and h['status']=='EXTERNALLY_ACCEPTED_FORMALIZED','FORMALIZED_SUCCESSOR_ONLY')
    require(h['GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS']==[] and not any(e['blocks_v4_16_contract_entry'] or e['blocks_v4_16_runtime_activation'] for e in h['entries'].values()),'GLOBAL_HOLD_CLOSED_NOT_PERMISSION')
    c=read(CONFIG,root);require(c['current_head']==ref(HEAD,root) and json.loads(exact(c['current_head'],root))==h and c['external_acceptance']==ref(ACCEPT,root),'UNIQUE_FORMALIZED_CURRENT_AUTHORITY')
    require(c['contract_id']=='V4_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_V2' and c['version']=='2.0.0' and c['execution_baseline']==BASE,'EXACT_V2_CURRENT_CONFIG')
    for key,value in old_c.items():
        if key not in ['contract_id','version','execution_baseline','current_head','supersedes_current_config']:require(c[key]==value,'CONFIG_CORE_KEEP_'+key)
    require(c['supersedes_current_config']==ref(OLD_CONFIG,root) and c['declared_global_contract_entry_blockers']==[],'CONFIG_SUCCESSOR_EXACT')
    for obj in [a,h,c]:require(all(obj[k] is False for k in ['production','shadow','focus','V4_16']),'NO_RUNTIME_OR_CUTOVER_PERMISSION')
    protected=json.loads(baseline('reports/pre16_governance_r1_1/PROTECTED_BYTES.json',root))['bindings']
    for p in protected:exact(p,root)
    require(subprocess.check_output(['git','diff',BASE,'--name-only','--','src','reports/r20','reports/r20r1','reports/r20r1r1','reports/r20r1r2','reports/r21','reports/pre16_governance_r1_1'],cwd=root)==b'','BUSINESS_AND_ACCEPTED_EVIDENCE_KEEP')
    existing=set(subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=root).decode('utf8').splitlines())
    changed=set(subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=root).decode('utf8').splitlines())
    require((changed & existing)<={'.gitattributes'},'ALL_EXISTING_BASELINE_ARTIFACTS_KEEP')
    require(read('data/v4/V4_STAGE_ACCEPTED_HEAD.json',root)['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED' and read('data/v4/V4_DATA_ACCEPTED_HEAD.json',root)['accepted_trade_date']=='2026-09-30','STAGE_DATA_KEEP')
    require(not (root/'data/v4/V4_16_ACCEPTED_HEAD.json').exists(),'NO_V4_16_ACCEPTED_HEAD')
    return dict(PRE16_EXTERNAL_ACCEPTANCE_FORMALIZATION='PASS_LOCAL',PRE16_GOVERNANCE='EXTERNALLY_ACCEPTED_FORMALIZED',GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS=[],V4_10_TO_V4_15='PASS_KEEP_NO_REOPEN',protected_bindings=protected,Production=False,Shadow=False,Focus=False,V4_16=False)

if __name__=='__main__':
    print(json.dumps({k:v for k,v in validate().items() if k!='protected_bindings'}))
