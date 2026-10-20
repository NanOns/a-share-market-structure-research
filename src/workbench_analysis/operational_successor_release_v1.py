"""One-session CAS, readback and crash-recoverable exact predecessor rollback."""
from pathlib import Path
from datetime import datetime,timezone
import json
from .operational_daily_storage_v1 import atomic_json,exclusive_lock
from .r43_owner_replay import checked_pg as checked,ref
from .tdx_official_daily_source import sha256_file,_atomic_write
from .operational_successor_v1 import validate,digest


def _tdx_root(root):
    from common.paths import resolve_tdx_root
    return resolve_tdx_root(Path(root).resolve())


def verify_policy(root,candidate,*,verify_loaded=True):
    import os
    root=Path(root);binding=candidate['release_policy']
    namespace=(candidate.get('contract_namespace') or candidate.get('model_namespace_id')
               or os.environ.get('V4_PG_MODEL_NAMESPACE_ID','')).strip()
    expected_contract=('V4_OPERATIONAL_DAILY_EXACT_RELEASE_POLICY_V2'
        if candidate.get('exact_daily_adjustment_contract') else 'READ_ONLY_OPERATIONAL_DAILY_RELEASE_POLICY_V1_1')
    from workbench_db.v4_publication_reader import readonly_connection, PgPublicationReader
    from .contract_registry_pg_v1 import load_current_approved_contract_by_digest
    with readonly_connection() as pg:
        identity=PgPublicationReader._read_database_identity(pg)
        if not namespace:
            namespaces=pg.execute("SELECT namespace FROM v4.contract_versions WHERE contract_id=%s AND raw_sha256=%s",
                (expected_contract,binding['sha256'])).fetchall()
            if len(namespaces)!=1:raise ValueError('PG_DAILY_CONTRACT_NAMESPACE_NOT_UNIQUE')
            namespace=str(namespaces[0][0])
        registered=load_current_approved_contract_by_digest(pg,expected_contract,binding['sha256'],namespace,
            expected_database_identity=identity)
    if len(registered.raw_content)!=binding.get('bytes'):
        raise ValueError('PG_DAILY_CONTRACT_SOURCE_SIZE_MISMATCH')
    if registered.raw_sha256!=binding.get('sha256'):
        raise ValueError('PG_DAILY_CONTRACT_SOURCE_DIGEST_MISMATCH')
    policy=registered.parsed_json
    if not isinstance(policy,dict):raise ValueError('PG_DAILY_CONTRACT_JSON_REQUIRED')
    from .operational_daily_exact_policy_v2 import CONTRACT,KERNEL,verify
    if policy.get('contract_id')==CONTRACT:
        policy,_=verify(root,binding,verify_loaded=verify_loaded,registered_policy=dict(
            contract_id=registered.contract_id,raw_sha256=registered.raw_sha256,parsed_json=registered.parsed_json))
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
    if registered.contract_id!='READ_ONLY_OPERATIONAL_DAILY_RELEASE_POLICY_V1_1':
        raise ValueError('PG_APPROVED_DAILY_POLICY_REQUIRED')
    if policy.get('publication_ready') is not True:
        raise ValueError('DAILY_ALGORITHM_ADMISSION_NOT_READY')
    if policy.get('historical_PIT_permission') or policy.get('automated_trading_permission') or policy.get('algorithm_upgrade_permission'):
        raise ValueError('DAILY_POLICY_SCOPE_ESCALATION')
    checked(root,policy['task_contract'])
    for binding in policy['accepted_algorithm_bindings']:checked(root,binding)
    if candidate.get('accepted_algorithm_bindings')!=policy['accepted_algorithm_bindings']:
        raise ValueError('DAILY_ALGORITHM_BINDING_MISMATCH')


def promote(root,candidate,expected_sha,readback):
    root=Path(root)
    verify_policy(root,candidate)
    if candidate.get('exact_daily_adjustment_contract'):
        from workbench_db.v4_successor_pg_authority_preparation_v1 import prepare_remaining
        prepare_remaining(root,candidate)
    validate(root,candidate)
    if candidate.get('predecessor',{}).get('sha256')!=expected_sha:
        raise ValueError('STALE_OPERATIONAL_HEAD_CAS')
    from workbench_db.v4_operational_live_head_pg_r1 import compare_and_swap
    with exclusive_lock(root,root/'runtime/dynamic_daily/publisher.lock'):
        committed=compare_and_swap(root,candidate,expected_sha)
    current=committed['head_sha256']
    try:
        receipt=readback(candidate)
        if (receipt.get('context_token')!=digest(candidate)
                or receipt.get('accepted_trade_date')!=candidate['accepted_trade_date']
                or receipt.get('status')!='PASS'):
            raise ValueError('HTTP_SAME_TOKEN_READBACK_FAILED')
    except Exception:
        # Restore only if the candidate remains current; never overwrite a
        # newer accepted Head after a concurrent publication.
        try:
            compare_and_swap(root,committed['predecessor'],current)
        except Exception as rollback_error:
            raise ValueError('PG_HEAD_READBACK_FAILED_ROLLBACK_CONFLICT') from rollback_error
        raise
    published=dict(status='PUBLISHED',accepted_trade_date=candidate['accepted_trade_date'],
                   context_token=digest(candidate),head_sha256=current,
                   generation=committed['generation'])
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
    # PostgreSQL commits the Head row atomically. An uncommitted CAS is rolled
    # back by PostgreSQL itself; a committed Head is verified on each read.
    return dict(status='PG_ATOMIC_HEAD_NO_FILE_RECOVERY', file_fallback=False)


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
