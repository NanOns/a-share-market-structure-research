"""Per-field research source generation and inherited episode facts; no grant."""
from workbench_analysis.r43_owner_replay import checked
from .d2_admission_candidate_r4 import instant
import json

CONTRACT = 'SECTOR_D2_RESEARCH_SOURCE_MATRIX_V1'


def build(root, *, candidate_binding, prior_binding=None, cutoff):
    source = json.loads(checked(root, candidate_binding).read_bytes())
    prior = json.loads(checked(root, prior_binding).read_bytes()) if prior_binding else None
    result = []
    for row in source['rows']:
        fields = {k: dict(value=row.get(k, 'UNKNOWN'), status='RECONSTRUCTED_RESEARCH_ONLY',
                         source=candidate_binding) for k in ('CONFIRMED', 'WARM')}
        episode = next((p for p in (prior or {}).get('rows', []) if p['entity_id'] == row['sector_id']), None)
        if episode and (not episode.get('episode_id') or episode.get('AS_RECORDED') is not True or
                        instant(episode['first_available']) > instant(cutoff)):
            raise ValueError('LEGITIMATE_PRIOR_EPISODE_REQUIRED')
        if not episode:
            for name in ('frozen_invalidation', 'episode_invalidation_contract_id', 'followup_complete', 'scenario'):
                fields[name] = dict(value=None, status='NO_PRIOR_EPISODE', source=None)
        else:
            if episode['trade_date'] >= source['T0']:
                raise ValueError('PRIOR_EPISODE_DATE_INVALID')
            fields['episode_invalidation_contract_id'] = dict(value=episode.get('invalidation_contract_id'),
                status='INHERITED_CANDIDATE' if episode.get('invalidation_contract_id') else 'UNKNOWN', source=prior_binding)
            fields['scenario'] = dict(value=episode.get('scenario'), status='INHERITED_CANDIDATE' if episode.get('scenario') else 'UNKNOWN', source=prior_binding)
            fields['frozen_invalidation'] = dict(value=None, status='UNKNOWN', source=prior_binding,
                                                 reason='CREATION_CONDITION_EVALUATION_RECEIPT_REQUIRED')
            due = episode.get('due_at')
            fields['followup_complete'] = dict(value=None, status='PENDING' if due and instant(cutoff) < instant(due) else 'UNKNOWN',
                source=prior_binding, reason='SETTLEMENT_OWNER_REQUIRED_AT_DUE')
        result.append(dict(entity_id=row['sector_id'], fields=fields))
    return dict(contract_id=CONTRACT, T0=source['T0'], rows=result, source=candidate_binding,
                prior_source=prior_binding, production=False, formal_D2='NOT_GRANTED',
                independent_admission_scope=['RESEARCH_CONFIRMED_WARM_EXACT_INPUTS', 'LEGACY_MISSING_STATE_ORACLE'],
                excluded_admission_scope=['A05_CROSS_DATE', 'FORMAL_D2', 'NATIVE_PROXY_AUTHORITY'])
