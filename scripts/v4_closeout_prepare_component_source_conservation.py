"""Bind current 604-source scope without retagging original numerical generation."""
import hashlib,json
from pathlib import Path
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_component_source_conservation_v2 import CONTRACT,KEY,PROFILE,verify
from workbench_analysis.tdx_official_daily_source import _atomic_write

def main():
    target=OUT/'COMPONENT_SOURCE_CONSERVATION_R6_R1.json'
    if target.exists():raise ValueError('PRESERVE_COMPONENT_SOURCE_CONSERVATION')
    preparation=json.loads((OUT/'NATIVE_PROFILE_DEPENDENT_PREPARATION_R6_R1.json').read_bytes());candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes())
    folder=checked(ROOT,candidate['owners'][candidate['accepted_trade_date']]['focus']).parents[3]
    reuse=json.loads((folder/'CORE_PROFILE_REUSE_RECEIPT_R1.json').read_bytes());checkpoint=json.loads(checked(ROOT,reuse['checkpoint']).read_bytes());old=next(b for b in checkpoint['unchanged_component_sources'] if b['path']==PROFILE)
    raw=(ROOT/PROFILE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=old['sha256']:raise ValueError('ORIGINAL_PROFILE_SOURCE_BYTES_REQUIRED')
    source=ROOT/'data/v4/component_source_conservation_v2'/old['sha256']/PROFILE
    if source.exists() and source.read_bytes()!=raw:raise ValueError('PRESERVE_ORIGINAL_PROFILE_SOURCE_ARCHIVE')
    if not source.exists():_atomic_write(source,raw,tdx_root=Path('D:/new_tdx'))
    policy=json.loads((ROOT/'config/operational_daily_exact_release_policy_v2.json').read_bytes());evidence_folder=ROOT/'data/v4/component_source_conservation_v2'/'evidence_r1';evidence={}
    for name,filename in dict(profile_changed_function_oracle='EXTENSION_CHANGED_SCOPE_SIX_DATES_R6_R1.json',d2_branch_oracle='BOUNDED_D2_UNKNOWN_BRANCH_ORACLE_R6_R2.json',forward_branch_conservation='BOUNDED_FORWARD_SEMANTIC_CORRECTION_R6_R1.json',native_dependent_consumers='NATIVE_DEPENDENT_CONSUMER_READBACK_R6_R1.json').items():
        destination=evidence_folder/filename;raw=(OUT/filename).read_bytes()
        if destination.exists() and destination.read_bytes()!=raw:raise ValueError('PRESERVE_ORIGINAL_COMPONENT_EVIDENCE')
        if not destination.exists():_atomic_write(destination,raw,tdx_root=Path('D:/new_tdx'))
        evidence[name]=ref(ROOT,destination)
    receipt=dict(contract_id=CONTRACT,acceptance='PASS_COMPONENT_CONSERVATION_AND_BOUNDED_PROFILE_CORRECTION',input_candidate=preparation['candidate'],original_checkpoint=reuse['checkpoint'],original_profile_source=ref(ROOT,source),current_component_bindings=policy['component_source_bindings'],profile_correction_authority=candidate['native_profile_semantic_corrections'],unchanged_component_count=603,changed_function='extension_risk',bounded_numeric_corrections=27,original_full_numerical_producers_reexecuted=False,publication=False,**evidence)
    path=ROOT/'data/v4/component_source_conservation_v2'/'CONSERVATION_R1.json';atomic_json(ROOT,path,receipt);candidate[KEY]=ref(ROOT,path)
    verify(ROOT,candidate,policy)
    prepared=path.with_name('CANDIDATE_WITH_COMPONENT_CONSERVATION_R1.json');atomic_json(ROOT,prepared,candidate)
    result=dict(contract_id=CONTRACT,acceptance=receipt['acceptance'],candidate=ref(ROOT,prepared),receipt=ref(ROOT,path),sources=604,unchanged_sources=603,bounded_profile_corrections=27,publication=False,full_numeric_gate='STILL_PENDING_UNCOVERED_SCOPES')
    atomic_json(OUT,target,result);print(json.dumps(dict(acceptance=result['acceptance'],sources=604,unchanged=603)))

if __name__=='__main__':main()
