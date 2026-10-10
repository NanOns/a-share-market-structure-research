"""State admission entry point; the legacy isolated bridge is unchanged.

Only a deployed independently accepted resolver may supply a trusted binding.
There is currently no such service, and caller documents cannot install one.
"""
from .trusted_source_review_v1 import resolve

CONTRACT = 'STATE_TRUSTED_REVIEW_CANDIDATE_V1'


def review_candidate(root, *, review_binding=None, source_bindings=None,
                     accepted_head=None, **caller_claims):
    result = resolve(root, capability='STATE_SOURCE_REVIEW',
                     review_binding=review_binding, sources=source_bindings,
                     accepted_head=accepted_head)
    return dict(result, entry_contract_id=CONTRACT,
                formal_cohort_enabled=False, bridge_executed=False,
                caller_claims_authoritative=False)
