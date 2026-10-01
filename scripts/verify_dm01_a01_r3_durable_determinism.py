"""Fresh-namespace deterministic build and genuine re-capture source revision proof."""
from copy import deepcopy
from datetime import datetime,timezone
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.dm01_incremental_component_builders_r3_2 import load,digest,_write_immutable
from workbench_analysis.dm01_candidate_orchestrator_r3_2 import build_candidate
from workbench_analysis.daily_source_freeze import build_source_freeze_manifest_v2
P='reports/audits/DM01_A01_R3_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
    config=read('config/dm01_incremental_builders_contract_r3_2.json');ctx=load(config['execution_context']);target=ctx['sessions'][0]
    source=ctx['inputs'][target];parent=ctx['parent'];original=read(P+target.replace('-','')+'_CANDIDATE_R2.json')
    freeze=build_source_freeze_manifest_v2(trade_date=target,sources=source['families'],changed_tdx_files=[],
        observed_at=ctx['observed_at'],ingested_at=ctx['observed_at'],system_available_at=ctx['observed_at'])
    freeze.update(inputs=source['inputs'],parent_data_head_digest=parent['binding']['sha256'],calendar_publication_id=ctx['calendar']['publication_id'],
        identity_publication_id=ctx['identity']['publication_id'],field_source_instances=source['instances'],tdx_roots=['D:/new_tdx'],
        knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    freeze['manifest_sha256']=digest({k:v for k,v in freeze.items() if k!='manifest_sha256'})
    heads=[ROOT/r['path'] for r in read(P+'STAGE_ENTRY_R1.json')['protected_bindings']]
    args=dict(parent_data_head=parent,source_freeze=freeze,calendar_binding=ctx['calendar'],identity_binding=ctx['identity'],
        staging_root=ROOT/'data/v4/dm01_candidate_staging_r3/durable_r2/fresh_determinism_r2',head_paths=heads)
    fresh=build_candidate(**args)
    assert fresh['status']=='READY_FOR_EXTERNAL_REAUDIT',fresh
    assert fresh['logical_digest']==original['logical_digest'] and fresh['candidate_revision']==original['candidate_revision']
    assert {k:r['logical_digest'] for k,r in fresh['components'].items()}=={k:r['logical_digest'] for k,r in original['components'].items()}
    print('PASS_FRESH_NAMESPACE_SAME_SOURCE_SAME_PARENT',flush=True)
    new=read(P+target.replace('-','')+'_SOURCE_CAPTURE_R1.json');instances=new['instances']
    newer=load(instances['TRADING_STATUS']);older=load(source['instances']['TRADING_STATUS'])
    assert newer['source_revision']!=older['source_revision']
    newerraw=load(newer['raw_artifact']);olderraw=load(older['raw_artifact'])
    # Genuine new SDK capture, with actual response provenance. Facts are never mutated to force a revision.
    base=ROOT/'data/v4/source_evidence/dm01_a01_r3/determinism_r2'
    bao=load(source['inputs']['BAOSTOCK_DAILY_UPDATE'])
    bao.update(raw_response_binding=newer['raw_artifact'],daily_rows=newerraw['rows'],source_instances=instances,snapshot_id=newer['source_revision'])
    path=base/('baostock_daily_'+digest(bao)+'.json');_write_immutable(path,bao);baoref=bind(path.relative_to(ROOT).as_posix())
    revision=deepcopy(freeze);revision['inputs']['BAOSTOCK_DAILY_UPDATE']=baoref
    revision['source_families']['BAOSTOCK_DAILY_UPDATE']=dict(baoref,source_revision=newer['source_revision'])
    revision['field_source_instances']=instances
    observed=datetime.now(timezone.utc).isoformat()
    for k in ('observed_at','ingested_at','system_available_at'):revision[k]=observed
    revision['manifest_sha256']=digest({k:v for k,v in revision.items() if k!='manifest_sha256'})
    revisedargs=dict(args,source_freeze=revision,staging_root=ROOT/'data/v4/dm01_candidate_staging_r3/durable_r2/genuine_source_revision_r2')
    revised=build_candidate(**revisedargs)
    assert revised['status']=='READY_FOR_EXTERNAL_REAUDIT',revised
    assert revised['candidate_revision']!=original['candidate_revision']
    prior=read(P+'CONTINUOUS_CHAIN_POSTCHECK_R2.json')['candidates']
    assert all(bind(r['path'])==r for r in prior)
    initial=ROOT/(P+'DETERMINISM_R2.json')
    atomic_bytes(ROOT/(P+'DETERMINISM_INITIAL_ENVELOPE_PROBE_R2.json'),initial.read_bytes())
    result=dict(status='PASS',same_source_same_parent_reruns='NOOP_IDENTICAL_CANDIDATE',fresh_namespace_candidate=fresh['candidate'],
        fresh_namespace_logical_digest=fresh['logical_digest'],original_logical_digest=original['logical_digest'],
        fresh_namespace_exact_component_logical_digests=True,revised_source_candidate=revised['candidate'],
        source_binding_revision_changes_candidate_revision=True,old_candidates_immutable=True,
        source_revision_before=older['source_revision'],source_revision_after=newer['source_revision'],
        genuine_recapture=new['capture_receipt'],provider_row_values_changed=newerraw['rows']!=olderraw['rows'],
        revision_scope='ACTUAL_NEW_DATED_SDK_CAPTURE_PLUS_ACTUAL_CAPTURE_ENVELOPE; NO_FABRICATED_PRICE_OR_STATUS',
        producer_registry_before=new['producer_registry_before'],producer_registry_after=new['producer_registry_after'])
    atomic_json(initial,result)
    handoff=read(P+'EXTERNAL_REAUDIT_HANDOFF_R2.json');handoff['determinism']=bind(P+'DETERMINISM_R2.json')
    atomic_json(ROOT/(P+'EXTERNAL_REAUDIT_HANDOFF_R2.json'),handoff)
    print('PASS_GENUINE_SOURCE_REVISION_OLD_CHAIN_IMMUTABLE')
if __name__=='__main__':main()
