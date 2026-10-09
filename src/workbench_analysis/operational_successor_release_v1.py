"""One-session CAS, readback and crash-recoverable exact predecessor rollback."""
from pathlib import Path
import json
from .operational_daily_storage_v1 import atomic_json,exclusive_lock
from .r43_owner_replay import checked,ref
from .tdx_official_daily_source import sha256_file,_atomic_write
from .operational_successor_v1 import validate,digest


def verify_policy(root,candidate):
    root=Path(root)
    binding=candidate['release_policy'];policy=json.loads(checked(root,binding).read_bytes())
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
        validate(root,candidate);verify_policy(root,candidate)
        if sha256_file(head)!=expected_sha or candidate['predecessor']['sha256']!=expected_sha:
            raise ValueError('STALE_OPERATIONAL_HEAD_CAS')
        before=head.read_bytes();archive=head.parent/'predecessors'/(expected_sha+'.json')
        _atomic_write(archive,before,tdx_root=Path('D:/new_tdx'))
        atomic_json(root,transaction,dict(state='PREPARED',predecessor=ref(root,archive),candidate_token=digest(candidate)))
        atomic_json(root,head,candidate)
        current=sha256_file(head)
        atomic_json(root,transaction,dict(state='CAS_COMPLETE_READBACK_PENDING',predecessor=ref(root,archive),head_sha256=current,candidate_token=digest(candidate)))
        try:
            receipt=readback(candidate)
            if receipt.get('context_token')!=digest(candidate) or receipt.get('accepted_trade_date')!=candidate['accepted_trade_date'] or receipt.get('status')!='PASS':
                raise ValueError('HTTP_SAME_TOKEN_READBACK_FAILED')
        except Exception:
            if sha256_file(head)!=current:raise ValueError('ROLLBACK_HEAD_MOVED_FAIL_CLOSED')
            _atomic_write(head,before,tdx_root=Path('D:/new_tdx'))
            atomic_json(root,transaction,dict(state='ROLLED_BACK',predecessor=ref(root,archive),failed_token=digest(candidate)))
            raise
        atomic_json(root,transaction,dict(state='COMMITTED',predecessor=ref(root,archive),head_sha256=current,readback=receipt))
        return dict(status='PUBLISHED',accepted_trade_date=candidate['accepted_trade_date'],context_token=digest(candidate),head_sha256=current)


def recover(root):
    root=Path(root);transaction=root/'runtime/dynamic_daily/publication_transaction.json'
    if not transaction.is_file():return
    with exclusive_lock(root,root/'runtime/dynamic_daily/publisher.lock'):
        record=json.loads(transaction.read_bytes())
        if record['state'] not in ('PREPARED','CAS_COMPLETE_READBACK_PENDING'):return
        head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
        current=json.loads(head.read_bytes())
        if digest(current)!=record['candidate_token']:
            if sha256_file(head)==record['predecessor']['sha256']:
                atomic_json(root,transaction,dict(record,state='RECOVERED_PRE_CAS'))
                return
            raise ValueError('RECOVERY_HEAD_MOVED_FAIL_CLOSED')
        _atomic_write(head,checked(root,record['predecessor']).read_bytes(),tdx_root=Path('D:/new_tdx'))
        atomic_json(root,transaction,dict(record,state='RECOVERED_EXACT_PREDECESSOR'))
