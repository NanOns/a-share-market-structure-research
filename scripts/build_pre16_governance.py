"""PRE16 R1.1 rebuild: repair only canonical identity and scoped blockers."""
import json,os,subprocess
from copy import deepcopy
from pathlib import Path
from scripts.pre16_governance_io import ROOT,HEAD,CONTRACT,ref
REPAIR_BASE='0109d7f6c8b9f4cea6cde32b2342e4b6d4e0526b'
OUT='reports/pre16_governance_r1_1/'
INPUT='reports/pre16_governance/r1_1_inputs/'
AUDIT_NAME='V4_PRE16_GOVERNANCE_INDEPENDENT_EXTERNAL_AUDIT_R1_20261004.md'

def write(path,value,root=ROOT,raw=False):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root) or not (path in [HEAD,CONTRACT] or path.startswith(OUT) or path=='docs/audits/V4_PRE16_GOV_R1_1_CANONICAL_BLOCK_SCOPE_20261004.md'):raise ValueError('REPAIR_GOVERNANCE_OUTPUT_ONLY')
    data=value if raw else (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
    if p.exists() and p.read_bytes()==data:return ref(path,root)
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
    with tmp.open('wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    os.replace(tmp,p);return ref(path,root)

def prior(path,root=ROOT):return subprocess.check_output(['git','show',REPAIR_BASE+':'+path],cwd=root)

def build(root=ROOT):
    old=json.loads(prior(HEAD,root));h=deepcopy(old)
    # The evidence namespace preserves literal bytes across autocrlf checkouts.
    write(OUT+'.gitattributes',b'* -text\n',root,raw=True)
    write(OUT+'PREVIOUS_CURRENT_HEAD.json',prior(HEAD,root),root,raw=True)
    write(OUT+'PREVIOUS_CURRENT_CONFIG.json',prior(CONTRACT,root),root,raw=True)
    protected=json.loads(prior('reports/pre16_governance/PROTECTED_BYTES.json',root))
    for b in protected['bindings']:
        if ref(b['path'],root)!=b:raise ValueError('PROTECTED_BYTES_CHANGED')
    write(OUT+'PROTECTED_BYTES.json',dict(status='PASS_LOCAL',baseline=REPAIR_BASE,bindings=protected['bindings'],literal_before_after=True),root)
    entries=h['entries']
    for key,e in entries.items():
        global_hold=key=='GOV_PRE16_01'
        shadow_hold=key in ['A04_H21_CONSUMER','A04_HISTORICAL_AMOUNT_A','A08_CURRENT_RUNTIME']
        caps={'GOV_PRE16_01':['V4_16_CONTRACT_ENTRY','V4_16_RUNTIME_ACTIVATION'], 'A04_H21_CONSUMER':['AMOUNT_A_H21_FORMAL_CONSUMER'], 'A04_HISTORICAL_AMOUNT_A':['HISTORICAL_AMOUNT_A_FORMAL_CONSUMER'], 'A08_CURRENT_RUNTIME':['V4_09_N01_CURRENT_RUNTIME_PREWATCH']}.get(key,[key])
        e.update(canonical_issue_id=key,alias_of=None,blocking_scope='GLOBAL_STAGE' if global_hold else 'CAPABILITY_ONLY',blocks_v4_16_contract_entry=global_hold,blocks_v4_16_runtime_activation=global_hold,blocks_affected_capability_in_shadow=shadow_hold,blocks_production_cutover_for_scope=True,affected_capabilities=caps)
        e['blocks_engineering_stage']=global_hold
        e['blocks_shadow_entry']=global_hold or shadow_hold
    alias=entries['AUD_A04_AMOUNT_A_FORWARD_CONSUMER'];canonical=entries['A04_H21_CONSUMER']
    alias['alias_provenance']=dict(scope=alias['scope'],limitations=alias['limitations'],capability_dimensions=alias['capability_dimensions'])
    for key in ['canonical_issue_id','current_state','scope','limitations','capability_dimensions','blocking_scope','blocks_v4_16_contract_entry','blocks_v4_16_runtime_activation','blocks_affected_capability_in_shadow','blocks_production_cutover_for_scope','affected_capabilities','blocks_engineering_stage','blocks_shadow_entry','blocks_production_cutover','requires_real_observation_accumulation','formal_consumer_permission_granted_by_this_head']:
        alias[key]=deepcopy(canonical[key])
    alias['alias_of']='A04_H21_CONSUMER'
    h.update(version='1.1.0',execution_baseline=REPAIR_BASE,prior_execution_baseline=old['execution_baseline'],supersedes_current_head=ref(OUT+'PREVIOUS_CURRENT_HEAD.json',root),repair_authority={n:ref(INPUT+n,root) for n in [AUDIT_NAME,'V4_PRE16_GOVERNANCE_R1_1_CANONICAL_BLOCK_SCOPE_REPAIR_TASK_20261004.md','V4_NEXT_ROUND_EXECUTION_MASTER_PRE16_GOV_R1_1_20261004.md']},GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS=['GOV_PRE16_01'])
    h['blocking_schema']=dict(legacy_blocks_shadow_entry='blocks_v4_16_runtime_activation OR blocks_affected_capability_in_shadow; true does not imply global Shadow block',legacy_blocks_engineering_stage='blocks_v4_16_contract_entry',legacy_blocks_production_cutover='blocks_production_cutover_for_scope',runtime_activation_dependency='Only GOV_PRE16_01 is a declared global activation hold in this authority. Future contracts must explicitly bind required capabilities; A08 remains blocked for its capability, without inventing an unfrozen global dependency.',permission='Blocker queries never grant permission; stage_permission remains false')
    write(HEAD,h,root)
    c=json.loads(prior(CONTRACT,root));c.update(version='1.1.0',execution_baseline=REPAIR_BASE,current_head=ref(HEAD,root),supersedes_current_config=ref(OUT+'PREVIOUS_CURRENT_CONFIG.json',root),blocking_schema=h['blocking_schema'],alias_rule='One canonical issue; aliases resolve deterministically and cannot override state or blocking semantics')
    write(CONTRACT,c,root)
    write(OUT+'CANONICAL_ISSUE_MAP.json',dict(status='READY_FOR_INDEPENDENT_ORACLE',map={k:dict(canonical_issue_id=e['canonical_issue_id'],alias_of=e['alias_of']) for k,e in entries.items()},canonical_count=35,reference_count=1),root)
    fields=['blocking_scope','blocks_v4_16_contract_entry','blocks_v4_16_runtime_activation','blocks_affected_capability_in_shadow','blocks_production_cutover_for_scope','affected_capabilities','canonical_issue_id','alias_of']
    write(OUT+'BLOCKING_SCOPE_MATRIX.json',dict(entries={k:{f:e[f] for f in fields} for k,e in entries.items()},GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS=['GOV_PRE16_01']),root)
    write(OUT+'CURRENT_STATUS_REBUILD.json',dict(status='READY_FOR_INDEPENDENT_ORACLE',baseline=REPAIR_BASE,head=ref(HEAD,root),config=ref(CONTRACT,root),previous_head=ref(OUT+'PREVIOUS_CURRENT_HEAD.json',root),core='PASS_KEEP',AMOUNT_A_H21='ONE_CANONICAL_CURRENT_ISSUE',V4_10_TO_V4_15='PASS_KEEP_NO_REOPEN',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT'),root)
    print('R1.1 rebuilt 36 references / 35 canonical issues; protected bytes unchanged')
if __name__=='__main__':build()
