from __future__ import annotations
"""All nine candidates and independent checks precede the single candidate-ready marker."""
import json
from pathlib import Path
from workbench_analysis.daily_data_head import CAPABILITIES
from workbench_analysis.dm01_incremental_component_builders import (
    BUILDERS,BUILD_ORDER,ComponentBuildError,digest,sha,resolve_target_session,_write_immutable,CONTRACT_PATH,ROOT)
from workbench_analysis.dm01_independent_postcheck_r1 import check_cross_components

def build_candidate(*,parent_data_head,source_freeze,calendar_binding,identity_binding,staging_root,head_paths):
    before={str(p):sha(p) for p in head_paths};stage=None;receipts={}
    try:
        from workbench_analysis.daily_source_freeze import ensure_outside_tdx
        for root in (Path('D:/new_tdx'),*[Path(p) for p in source_freeze.get('tdx_roots',[])]):
            ensure_outside_tdx(Path(staging_root),root)
        target=resolve_target_session(parent_data_head['head']['accepted_trade_date'],calendar_binding,source_freeze['observed_at'],source_freeze['trade_date'])
        contract_sha=sha(ROOT/CONTRACT_PATH)
        run_id=digest(dict(target=target,parent=parent_data_head['binding']['sha256'],source=source_freeze['manifest_sha256'],contract=contract_sha))
        stage=Path(staging_root)/run_id
        marker=stage/'PROMOTION_CANDIDATE.json'
        if marker.exists():
            manifest=json.loads(marker.read_text(encoding='utf8'))
            existing=manifest['components'];post=check_cross_components(existing,source_freeze,parent_data_head,calendar_binding,identity_binding)
            if post['status']!='PASS' or manifest['postcheck_digest']!=digest(post) or manifest['candidate_id']!=run_id:
                raise ComponentBuildError('CANDIDATE_DIGEST_MISMATCH')
            if any(sha(Path(p))!=s for p,s in before.items()):raise ComponentBuildError('PROTECTED_HEAD_CHANGED')
            return dict(status='NOOP_IDENTICAL_CANDIDATE',candidate_path=str(marker),candidate_sha256=sha(marker),data_head_moved=False)
        for cap in BUILD_ORDER:
            receipts[cap]=BUILDERS[cap](target,parent_data_head,source_freeze,calendar_binding,identity_binding,stage)
        post=check_cross_components(receipts,source_freeze,parent_data_head,calendar_binding,identity_binding)
        _write_immutable(stage/'independent_cross_postcheck.json',post,source_freeze.get('tdx_roots',[]))
        if post['status']!='PASS':raise ComponentBuildError('CROSS_COMPONENT_POSTCHECK_FAILED:'+str(post['errors']))
        if any(sha(Path(p))!=s for p,s in before.items()):raise ComponentBuildError('PROTECTED_HEAD_CHANGED')
        manifest=dict(contract_id='DM01_ATOMIC_PROMOTION_CANDIDATE_R1',status='CANDIDATE_READY_EXTERNAL_ACCEPTANCE_REQUIRED',
            candidate_id=run_id,target_trade_date=target,parent_data_head_digest=parent_data_head['binding']['sha256'],
            source_freeze_digest=source_freeze['manifest_sha256'],contract_sha256=contract_sha,
            calendar_publication_id=calendar_binding['publication_id'],identity_publication_id=identity_binding['publication_id'],
            components=receipts,postcheck_digest=digest(post),accepted_namespace_visible=False,
            fixture_scope=source_freeze.get('fixture_scope'),market_acceptance_claim=False,
            data_head_promotion_permitted=False,external_acceptance='PENDING',protected_heads=before)
        _write_immutable(marker,manifest,source_freeze.get('tdx_roots',[]))
        return dict(status='DM01_A01_INCREMENTAL_BUILDERS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',
            candidate_path=str(marker),candidate_sha256=sha(marker),components=receipts,postcheck=post,data_head_moved=False)
    except (ValueError,KeyError,OSError,TypeError) as exc:
        result=dict(contract_id='DM01_ATOMIC_FAILURE_R1',status='BLOCKED',reason=str(exc),
            completed_components=list(receipts),accepted_namespace_visible=False,data_head_moved=False,
            protected_heads_unchanged=all(sha(Path(p))==s for p,s in before.items()))
        if stage is not None:
            # Failures remain inspectable, with no marker making partial components consumable.
            from workbench_analysis.daily_increment_builder import _atomic_json
            _atomic_json(stage/'failure.json',result,tdx_root=Path('D:/new_tdx'))
        return result
