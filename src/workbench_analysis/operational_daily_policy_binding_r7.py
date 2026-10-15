"""Versioned reader for the accepted exact daily V2 policy envelope.

This binds the newer content-addressed package policy used by the active V4
Head. It retains all existing fail-closed daily and trading restrictions.
"""
import json
import re
from pathlib import Path

from .r43_owner_replay import checked

CONTRACT_ID = "V4_R7_EXACT_DAILY_POLICY_BINDING_R1"
POLICY_PATH = re.compile(r"data/v4/exact_daily_policies_v2/([0-9a-f]{64})/POLICY\.json")


def verify(root, candidate):
    root=Path(root).resolve()
    binding=candidate.get('release_policy') or {}
    match=POLICY_PATH.fullmatch(binding.get('path',''))
    if not match or match.group(1)!=binding.get('sha256'):
        raise ValueError('R7_EXACT_DAILY_POLICY_CONTENT_ADDRESS_REQUIRED')
    path=checked(root,binding)
    policy=json.loads(path.read_bytes())
    if policy.get('contract_id')!='V4_OPERATIONAL_DAILY_EXACT_RELEASE_POLICY_V2':
        raise ValueError('R7_DAILY_POLICY_CONTRACT_MISMATCH')
    if policy.get('status') not in ('PASS_R1_1_RUNTIME_GATES','PASS') or policy.get('publication_ready') is not True:
        raise ValueError('R7_DAILY_POLICY_NOT_PUBLICATION_READY')
    for key in ('historical_PIT_permission','automated_trading_permission','probability_claims'):
        if policy.get(key) is not False:
            raise ValueError('R7_DAILY_POLICY_SCOPE_ESCALATION:'+key)
    if candidate.get('accepted_algorithm_bindings')!=policy.get('accepted_algorithm_bindings'):
        raise ValueError('R7_DAILY_ALGORITHM_BINDING_MISMATCH')
    for ref in policy.get('accepted_algorithm_bindings',[]):
        checked(root,ref)
    for key in ('task_contract','predecessor_policy','predecessor_runtime_policy'):
        ref=policy.get(key)
        if not isinstance(ref,dict):
            raise ValueError('R7_DAILY_POLICY_LINEAGE_MISSING:'+key)
        checked(root,ref)
    for ref in policy.get('component_source_bindings',[]):
        checked(root,ref)
    return dict(contract_id=CONTRACT_ID,status='PASS',policy=binding,
                automated_trading_permission=False,historical_PIT_permission=False,
                algorithm_bindings_checked=len(policy.get('accepted_algorithm_bindings',[])),
                component_bindings_checked=len(policy.get('component_source_bindings',[])))
