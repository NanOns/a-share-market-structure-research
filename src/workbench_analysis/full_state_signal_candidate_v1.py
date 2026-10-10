"""Full universe extraction of the existing scanner's T0 State outputs.

Never imports Focus or prior selected events. Research eligibility is descriptive
and is separate from formal enrollment eligibility, which remains false.
"""
from .v4_14_replay_io import digest, publish

CONTRACT = 'FULL_STATE_SIGNAL_SOURCE_CANDIDATE_V1'


def produce(rows, *, universe, trade_date, source_binding, membership_binding,
            model_binding, config_binding, captured_at):
    by_id = {}
    for row in rows:
        sid = row['security_id']
        if sid in by_id or row['trade_date'] != trade_date:
            raise ValueError('STATE_DUPLICATE_OR_DATE_MISMATCH')
        by_id[sid] = row
    if len(set(universe)) != len(universe) or set(by_id) - set(universe):
        raise ValueError('STATE_UNIVERSE_RECONCILIATION_REQUIRED')
    signals = []
    for sid in sorted(universe):
        row = by_id.get(sid)
        branches = (row or {}).get('confirmation', {}).get('scenario_evidence', [])
        # Include every algorithm scenario, whether qualifying or excluded.
        if not branches:
            branches = [dict(scenario='STATE_SOURCE', status='UNKNOWN', unknown_reasons=['STATE_OUTPUT_MISSING'])]
        if len({b['scenario'] for b in branches}) != len(branches):
            raise ValueError('DUPLICATE_STATE_SCENARIO')
        for branch in branches:
            state = branch['status']
            if state not in ('TRUE', 'FALSE', 'UNKNOWN'):
                raise ValueError('STATE_THREE_VALUE_REQUIRED')
            eligible = state == 'TRUE'
            signals.append(dict(signal_id=digest([trade_date, sid, branch['scenario']]),
                security_id=sid, T0=trade_date, scenario=branch['scenario'], state=state,
                research_eligible=eligible, eligible_at_T0=False,
                research_exclusion_reason=None if eligible else branch.get('unknown_reasons') or ['SCANNER_PREDICATE_FALSE'],
                ineligibility_reason='CANDIDATE_NOT_INDEPENDENTLY_ADMITTED',
                checks=branch.get('checks', {}), source_window=(row or {}).get('normal_evidence'),
                first_available=None, frozen_at_candidate=captured_at))
    return dict(contract_id=CONTRACT, T0=trade_date, scope='FULL_OBSERVATION_UNIVERSE_ALL_SCENARIOS',
        evidence_class='RECONSTRUCTED_RESEARCH_ONLY', production=False, PIT_ELIGIBLE=False,
        source=source_binding, membership=membership_binding, model=model_binding, config=config_binding,
        signal_count=len(signals), universe_count=len(universe), missing_state_count=len(set(universe)-set(by_id)),
        research_eligible_count=sum(r['research_eligible'] for r in signals), signals=signals,
        observed_count=None, matured_count=None, next_gate='INDEPENDENT_STATE_SOURCE_ADMISSION')


def freeze(root, document, *, publication_id, revision):
    # Revision slot never overwrites; content alterations require a new revision.
    slot = digest([document['T0'], publication_id, revision])
    return publish(root, f'data/v4/state_signal_candidates/{slot}/signals.json',
                   dict(document, publication_id=publication_id, revision=revision))
