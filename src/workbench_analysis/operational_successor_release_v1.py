"""One-session CAS, readback and crash-recoverable exact predecessor rollback."""
from pathlib import Path
from datetime import datetime,timezone
import json
from .operational_daily_storage_v1 import atomic_json,exclusive_lock
from .r43_owner_replay import checked,ref
from .tdx_official_daily_source import sha256_file,_atomic_write
from .operational_successor_v1 import validate,digest


def _tdx_root(root):
    from common.paths import resolve_tdx_root
    return resolve_tdx_root(Path(root).resolve())


def verify_policy(root,candidate,*,verify_loaded=True):
    root=Path(root)
    binding=candidate['release_policy'];policy=json.loads(checked(root,binding).read_bytes())
    from .operational_daily_exact_policy_v2 import CONTRACT,KERNEL,verify
    if policy.get('contract_id')==CONTRACT:
        policy,_=verify(root,binding,verify_loaded=verify_loaded)
        if candidate.get('accepted_algorithm_bindings')!=policy['accepted_algorithm_bindings']:
            raise ValueError('DAILY_ALGORITHM_BINDING_MISMATCH')
        generation=json.loads(checked(root,candidate['exact_daily_generation_scope']).read_bytes())
        if candidate.get('exact_daily_adjustment_contract')!=KERNEL:
            raise ValueError('DAILY_EXACT_GENERATION_BINDING_REQUIRED')
        from .operational_sealed_preparation_v1 import KEY,verify as verify_preparation
        from .operational_runtime_acceptance_r1_1 import KEY as R11,verify as verify_runtime_preparation
        if R11 in candidate:
            verify_runtime_preparation(root,candidate,policy)
        elif KEY in candidate:
            verify_preparation(root,candidate,policy)
        elif generation.get('adjustment_contract')!=dict(contract=KERNEL,policy=binding):
            raise ValueError('DAILY_EXACT_GENERATION_BINDING_REQUIRED')
        return
    if checked(root,binding)!=root/'config/read_only_operational_daily_release_policy_v1_1.json':
        raise ValueError('EXACT_DAILY_POLICY_REQUIRED')
    if policy.get('publication_ready') is not True:
        raise ValueError('DAILY_ALGORITHM_ADMISSION_NOT_READY')
    if policy.get('historical_PIT_permission') or policy.get('automated_trading_permission') or policy.get('algorithm_upgrade_permission'):
        raise ValueError('DAILY_POLICY_SCOPE_ESCALATION')
    checked(root,policy['task_contract'])
    for binding in policy['accepted_algorithm_bindings']:checked(root,binding)
    if candidate.get('accepted_algorithm_bindings')!=policy['accepted_algorithm_bindings']:
        raise ValueError('DAILY_ALGORITHM_BINDING_MISMATCH')


def promote(root,candidate,expected_sha,readback):
    root=Path(root);head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    transaction=root/'runtime/dynamic_daily/publication_transaction.json'
    with exclusive_lock(root,root/'runtime/dynamic_daily/publisher.lock'):
        verify_policy(root,candidate)
        if candidate.get('exact_daily_adjustment_contract'):
            from workbench_db.v4_successor_pg_authority_preparation_v1 import prepare_remaining
            prepare_remaining(root,candidate)
        validate(root,candidate)
        if sha256_file(head)!=expected_sha or candidate['predecessor']['sha256']!=expected_sha:
            raise ValueError('STALE_OPERATIONAL_HEAD_CAS')
        current_joint=root/'config/v4_current_native_joint_authority_v3.json'
        joint_before=current_joint.read_bytes() if current_joint.exists() else None
        joint_binding=None
        if candidate.get('exact_daily_adjustment_contract'):
            from workbench_service.native_current_snapshot_v3 import prepare_joint
            joint_binding=prepare_joint(root,candidate)
        joint_previous=None
        if joint_before is not None:
            joint_archive=head.parent/'current_joint_predecessors'/(digest(json.loads(joint_before))+'.json')
            _atomic_write(joint_archive,joint_before,tdx_root=_tdx_root(root))
            joint_previous=ref(root,joint_archive)
        before=head.read_bytes();archive=head.parent/'predecessors'/(expected_sha+'.json')
        _atomic_write(archive,before,tdx_root=_tdx_root(root))
        coordination=dict(current_joint=joint_binding,current_joint_predecessor=joint_previous)
        published = _commit_pointers(root,head,current_joint,transaction,candidate,before,archive,coordination,joint_before,
            checked(root,joint_binding).read_bytes() if joint_binding is not None else None,readback)
    head_accepted_at = datetime.now(timezone.utc).isoformat()
    try:
        from .forward_r7_pipeline import capture_after_accepted_head
        forward_capture = capture_after_accepted_head(root,candidate,head_accepted_at=head_accepted_at)
    except Exception as exc:
        forward_capture = dict(status='RETRY_REQUIRED',trade_date=candidate.get('accepted_trade_date'),
                               head_accepted_at=head_accepted_at,error_code=type(exc).__name__,retryable=True)
    return dict(published,head_accepted_at=head_accepted_at,forward_r7_capture=forward_capture)


def _commit_pointers(pointer_root,head,current_joint,transaction,candidate,before,archive,coordination,joint_before,joint_bytes,readback):
    """Shared exact pointer CAS/readback rollback; caller holds publisher lock."""
    root=Path(pointer_root)
    atomic_json(root,transaction,dict(state='PREPARED',predecessor=ref(root,archive),candidate_token=digest(candidate),**coordination))
    atomic_json(root,head,candidate)
    if joint_bytes is not None:
        _atomic_write(current_joint,joint_bytes,tdx_root=_tdx_root(root))
    current=sha256_file(head)
    atomic_json(root,transaction,dict(state='CAS_COMPLETE_READBACK_PENDING',predecessor=ref(root,archive),head_sha256=current,candidate_token=digest(candidate),**coordination))
    try:
        receipt=readback(candidate)
        if receipt.get('context_token')!=digest(candidate) or receipt.get('accepted_trade_date')!=candidate['accepted_trade_date'] or receipt.get('status')!='PASS':
            raise ValueError('HTTP_SAME_TOKEN_READBACK_FAILED')
    except Exception:
        if sha256_file(head)!=current:raise ValueError('ROLLBACK_HEAD_MOVED_FAIL_CLOSED')
        _atomic_write(head,before,tdx_root=_tdx_root(root))
        if joint_bytes is not None:
            if joint_before is None:current_joint.unlink()
            else:_atomic_write(current_joint,joint_before,tdx_root=_tdx_root(root))
        atomic_json(root,transaction,dict(state='ROLLED_BACK',predecessor=ref(root,archive),failed_token=digest(candidate),**coordination))
        raise
    atomic_json(root,transaction,dict(state='COMMITTED',predecessor=ref(root,archive),head_sha256=current,readback=receipt,**coordination))
    return dict(status='PUBLISHED',accepted_trade_date=candidate['accepted_trade_date'],context_token=digest(candidate),head_sha256=current)


def recover(root):
    root=Path(root);transaction=root/'runtime/dynamic_daily/publication_transaction.json'
    if not transaction.is_file():return
    with exclusive_lock(root,root/'runtime/dynamic_daily/publisher.lock'):
        record=json.loads(transaction.read_bytes())
        if record['state'] not in ('PREPARED','CAS_COMPLETE_READBACK_PENDING'):return
        def restore_joint():
            if not record.get('current_joint'):return
            path=root/'config/v4_current_native_joint_authority_v3.json'
            previous=record.get('current_joint_predecessor')
            if path.exists() and previous and path.read_bytes()==checked(root,previous).read_bytes():return
            if path.exists() and json.loads(path.read_bytes()).get('business_token')!=record['candidate_token']:
                raise ValueError('RECOVERY_CURRENT_JOINT_MOVED_FAIL_CLOSED')
            if previous:_atomic_write(path,checked(root,previous).read_bytes(),tdx_root=_tdx_root(root))
            elif path.exists():path.unlink()
        head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
        current=json.loads(head.read_bytes())
        if digest(current)!=record['candidate_token']:
            if sha256_file(head)==record['predecessor']['sha256']:
                restore_joint()
                atomic_json(root,transaction,dict(record,state='RECOVERED_PRE_CAS'))
                return
            raise ValueError('RECOVERY_HEAD_MOVED_FAIL_CLOSED')
        restore_joint()
        _atomic_write(head,checked(root,record['predecessor']).read_bytes(),tdx_root=_tdx_root(root))
        atomic_json(root,transaction,dict(record,state='RECOVERED_EXACT_PREDECESSOR'))


def engineering_shadow_promote(root,candidate,expected_sha,readback,*,shadow_root,evidence_binding):
    """Engineering G4 only: formal source/PG reads, G-local shadow pointers."""
    import os
    shadow=Path(shadow_root).resolve();root=Path(root).resolve()
    if (os.environ.get('R4_NATIVE_ISOLATION')!='1' or shadow.drive.upper()!='G:'
            or not any(part.lower()=='codex_tmp' for part in shadow.parts) or shadow==root):
        raise ValueError('ENGINEERING_SHADOW_SCOPE_REQUIRED')
    validate(root,candidate)
    from .operational_daily_exact_policy_v2 import verify
    policy,_=verify(root,candidate['release_policy'],candidate_only=True)
    if candidate.get('accepted_algorithm_bindings')!=policy['accepted_algorithm_bindings']:raise ValueError('DAILY_ALGORITHM_BINDING_MISMATCH')
    evidence=json.loads(checked(root,evidence_binding).read_bytes())
    if evidence.get('contract_id')!='V4_R1_1_DUAL_REFERENCE_SEMANTIC_AND_IDENTITY_PARITY' or evidence.get('target_trade_date')!=candidate['accepted_trade_date']:
        raise ValueError('ENGINEERING_G123_CONTEXT_REQUIRED')
    if evidence.get('scope')!='FULL_ALL_DOMAIN' or evidence.get('sample_count')==30:
        raise ValueError('ENGINEERING_FULL_DOMAIN_EVIDENCE_REQUIRED')
    counts=evidence.get('counts',{})
    if counts.get('stocks')!=5225 or counts.get('sectors')!=400:raise ValueError('ENGINEERING_FULL_DENOMINATOR_REQUIRED')
    if evidence.get('accepted_algorithm_bindings')!=policy['accepted_algorithm_bindings']:raise ValueError('ENGINEERING_G123_SOURCE_MISMATCH')
    actual=json.loads(checked(root,evidence['candidate_binding']).read_bytes())
    if actual!=candidate or any(evidence.get(g,{}).get('status')!='PASS' for g in ('G1','G2','G3')):
        raise ValueError('ENGINEERING_G123_PASS_REQUIRED')
    head=shadow/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    transaction=shadow/'runtime/dynamic_daily/publication_transaction.json'
    with exclusive_lock(shadow,shadow/'runtime/dynamic_daily/publisher.lock'):
        if sha256_file(head)!=expected_sha or candidate['predecessor']['sha256']!=expected_sha:raise ValueError('STALE_OPERATIONAL_HEAD_CAS')
        before=head.read_bytes();archive=shadow/'data/v4/predecessors'/(expected_sha+'.json')
        _atomic_write(archive,before,tdx_root=_tdx_root(root))
        result=_commit_pointers(shadow,head,shadow/'config/v4_current_native_joint_authority_v3.json',transaction,candidate,before,archive,{},None,None,readback)
    return dict(result,status='ENGINEERING_SHADOW_PUBLISHED',production_accepted=False,formal_head_changed=False)
