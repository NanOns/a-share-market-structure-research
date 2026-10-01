"""Publish an immutable candidate marker only after nine independent component checks."""
from datetime import datetime, timezone
from pathlib import Path
import json
from .dm01_incremental_component_builders_r3 import (BUILDERS,BUILD_ORDER,ComponentBuildError,
    ROOT,CONTRACT_PATH,digest,sha,load,_write_immutable,artifact_reference_path,resolve_target_session)
from .dm01_independent_postcheck_r3 import check_cross_components
from .dm01_chain_contract_r3 import validate_parent

def ref(path):
    return dict(path=artifact_reference_path(path),sha256=sha(path),bytes=Path(path).stat().st_size)

def build_candidate(*,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root,head_paths):
    before={artifact_reference_path(p):sha(p) for p in head_paths};stage=None;receipts={}
    try:
        from .daily_source_freeze import ensure_outside_tdx
        for root in (Path('D:/new_tdx'),*[Path(p) for p in source_freeze.get('tdx_roots',[])]):ensure_outside_tdx(Path(staging_root),root)
        contract=load(ref(ROOT/CONTRACT_PATH));validate_parent(parent_data_head,contract)
        target=resolve_target_session(parent_data_head['head']['accepted_trade_date'],calendar_binding,source_freeze['observed_at'],source_freeze['trade_date'])
        contract_sha=sha(ROOT/CONTRACT_PATH)
        run_id=digest(dict(target=target,parent=parent_data_head['binding']['sha256'],source=source_freeze['manifest_sha256'],contract=contract_sha))
        stage=Path(staging_root)/run_id;marker=stage/'PROMOTION_CANDIDATE.json'
        if marker.exists():
            manifest=load(ref(marker));receipts=manifest['components']
            post=check_cross_components(receipts,source_freeze,parent_data_head,calendar_binding,identity_binding)
            if post['status']!='PASS' or digest(post)!=manifest['postcheck_digest'] or manifest['candidate_id']!=run_id:
                raise ComponentBuildError('CANDIDATE_DIGEST_MISMATCH')
            if any(sha(ROOT/p)!=s for p,s in before.items()):raise ComponentBuildError('PROTECTED_HEAD_CHANGED')
            return dict(status='NOOP_IDENTICAL_CANDIDATE',candidate=ref(marker),candidate_revision=run_id,
                logical_digest=manifest['logical_digest'],components=receipts,postcheck=post,data_head_moved=False)
        parentpath=stage/'parent_context.json';_write_immutable(parentpath,parent_data_head,source_freeze.get('tdx_roots',[]))
        for cap in BUILD_ORDER:
            receipts[cap]=BUILDERS[cap](target,parent_data_head,source_freeze,calendar_binding,identity_binding,stage)
        post=check_cross_components(receipts,source_freeze,parent_data_head,calendar_binding,identity_binding)
        postpath=stage/'independent_cross_postcheck.json';_write_immutable(postpath,post,source_freeze.get('tdx_roots',[]))
        if post['status']!='PASS':raise ComponentBuildError('CROSS_COMPONENT_POSTCHECK_FAILED:'+str(post['errors']))
        if any(sha(ROOT/p)!=s for p,s in before.items()):raise ComponentBuildError('PROTECTED_HEAD_CHANGED')
        logical=digest(dict(target=target,parent=parent_data_head['binding']['sha256'],source=source_freeze['manifest_sha256'],
            components={k:r['logical_digest'] for k,r in receipts.items()},contract=contract_sha))
        state=dict(contract_id='DM01_CANDIDATE_KERNEL_STATE_VIEW_R3',accepted_trade_date=target,
            date_accessor='LEGACY_KERNEL_FIELD_NAME_ONLY_CANDIDATE_NOT_ACCEPTED',
            component_permissions={k:dict(status=r['status'],cutoff=target) for k,r in receipts.items()})
        manifest=dict(contract_id='DM01_ATOMIC_CONTINUOUS_CANDIDATE_R3',status='READY_FOR_EXTERNAL_REAUDIT',
            candidate_id=run_id,candidate_revision=run_id,target_trade_date=target,parent_data_head_digest=parent_data_head['binding']['sha256'],
            parent_context_binding=ref(parentpath),accepted_anchor=contract['accepted_data_head'],state_view=state,
            source_freeze_digest=source_freeze['manifest_sha256'],source_instance_digests=source_freeze['field_source_instances'],
            calendar_binding=calendar_binding['binding'],identity_binding=identity_binding['binding'],contract_sha256=contract_sha,
            components=receipts,cross_postcheck_binding=ref(postpath),postcheck_digest=digest(post),logical_digest=logical,
            created_at=datetime.now(timezone.utc).isoformat(),accepted_namespace_visible=False,
            external_acceptance='PENDING',data_head_promotion_permitted=False,production_permission=False,
            shadow_production_permission=False,focus_cutover_permission=False,protected_heads=before,
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False)
        _write_immutable(marker,manifest,source_freeze.get('tdx_roots',[]))
        return dict(status='READY_FOR_EXTERNAL_REAUDIT',candidate=ref(marker),candidate_revision=run_id,
            logical_digest=logical,components=receipts,postcheck=post,data_head_moved=False)
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result=dict(status='BLOCKED',reason=str(exc),completed_components=list(receipts),
            accepted_namespace_visible=False,data_head_moved=False,
            protected_heads_unchanged=all(sha(ROOT/p)==s for p,s in before.items()))
        if stage is not None:
            from .daily_increment_builder import _atomic_json
            _atomic_json(stage/'failure.json',result,tdx_root=Path('D:/new_tdx'))
        return result

def candidate_parent(result, staging_root):
    if result['status'] not in ('READY_FOR_EXTERNAL_REAUDIT','NOOP_IDENTICAL_CANDIDATE'):
        raise ComponentBuildError('FAILED_DAY_CANNOT_PARENT_NEXT_SESSION')
    marker=load(result['candidate'])
    components={k:dict(path=r['artifact_path'],sha256=r['artifact_sha256'],bytes=r['artifact_bytes']) for k,r in marker['components'].items()}
    manifest=dict(parent_data_head_digest=result['candidate']['sha256'],components=components,
        namespace='UNACCEPTED_CANDIDATE_CHAIN',accepted_data_head=marker['accepted_anchor'])
    path=Path(staging_root)/marker['candidate_id']/'candidate_parent_components.json'
    _write_immutable(path,manifest)
    return dict(kind='CANDIDATE_PARENT',binding=result['candidate'],head=marker['state_view'],components=components,
        component_manifest_binding=ref(path),external_acceptance='PENDING')
