"""Versioned byte-bound bridge candidate. Never grants source or writer authority.

The admission binding comes from a verified independent context, never from the
Publisher. Missing sources preserve the original research publication unchanged.
"""
import gzip
import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from .r43_owner_replay import checked
from .v4_14_replay_io import publish, digest
from .validation_cohort_read_contract_r3 import instant
from .full_state_first_observed_v1 import quarantine_publisher, freeze_first_observed

CONTRACT = 'STATE_PUBLISHER_FIRST_OBSERVED_BRIDGE_V1'


def bridge(root, *, publisher_binding, membership_binding=None, model_binding=None,
           events_binding=None, benchmark_binding=None, admission_binding=None,
           candidate_directory, clock=lambda: datetime.now(timezone.utc)):
    quarantine = quarantine_publisher(root, publisher_binding=publisher_binding,
                                      candidate_directory=candidate_directory + '/quarantine')
    source = json.loads(gzip.decompress(checked(root, publisher_binding).read_bytes()))
    bindings = dict(publisher=publisher_binding, membership=membership_binding,
                    model=model_binding, events=events_binding, benchmark=benchmark_binding)
    gaps = [{'field': k, 'reason': 'SOURCE_PRODUCER_NOT_IMPLEMENTED_OR_NOT_SUPPLIED'}
            for k, value in bindings.items() if not value]
    if not admission_binding:
        gaps.append(dict(field='independent_admission', reason='INDEPENDENT_SOURCE_REVIEW_REQUIRED'))
    if source['evidence_class'] != 'OBSERVED_SOURCE_CANDIDATE':
        gaps.append(dict(field='evidence_class', reason='HISTORICAL_RECONSTRUCTION_NO_UPGRADE'))
    if gaps:
        return dict(contract_id=CONTRACT, status='SOURCE_GAPS', source=publisher_binding,
                    quarantine=quarantine, gaps=gaps, production_write_authorized=False,
                    source_owner_admitted=False, observed_count=None)
    now = clock()
    day = now.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    admission = json.loads(checked(root, admission_binding).read_bytes())
    if (admission.get('contract_id') != 'STATE_SOURCE_INDEPENDENT_REVIEW_V1'
            or admission.get('sources') != bindings or admission.get('T0') != day
            or admission.get('decision') != 'SOURCE_FIELDS_REVIEWED'
            or admission.get('reviewer_role') != 'INDEPENDENT_SOURCE_REVIEWER'
            or source['T0'] != day):
        raise ValueError('INDEPENDENT_EXACT_SOURCE_REVIEW_REQUIRED')
    membership, model, events, benchmarks = [json.loads(checked(root, b).read_bytes())
        for b in (membership_binding, model_binding, events_binding, benchmark_binding)]
    original_model = json.loads(checked(root, source['model']).read_bytes())
    clock_gaps = [dict(field=name + '.' + key, reason='SOURCE_CLOCK_NOT_SUPPLIED')
        for name, doc in zip(('publisher', 'membership', 'model', 'events', 'benchmark', 'review'),
                             (source, membership, model, events, benchmarks, admission))
        for key in ('first_available', 'frozen_at') if not doc.get(key)]
    if clock_gaps:
        return dict(contract_id=CONTRACT, status='SOURCE_GAPS', source=publisher_binding,
                    quarantine=quarantine, gaps=clock_gaps, production_write_authorized=False,
                    source_owner_admitted=False, observed_count=None)
    if (membership.get('membership_basis') != 'AS_RECORDED'
            or membership.get('AS_RECORDED') is not True or membership.get('PIT_ELIGIBLE') is not True
            or membership.get('publisher_membership') != source['membership']
            or model.get('publisher_model') != source['model']):
        raise ValueError('REAL_SOURCE_MEMBERSHIP_MODEL_BINDING_REQUIRED')
    if any(model.get(k) != original_model.get(k) for k in
           ('model_contract_id', 'parameters_sha256', 'window_version', 'scenarios')):
        raise ValueError('BRIDGE_FROZEN_COMPUTATION_MODEL_MISMATCH')
    for doc in (source, membership, model, events, benchmarks, admission):
        if doc.get('T0') != day or not instant(doc['first_available']) <= instant(doc['frozen_at']) <= now:
            raise ValueError('BRIDGE_SOURCE_CLOCK_REQUIRED')
    event_rows = events['rows']; benchmark_rows = benchmarks['rows']
    def indexed(rows):
        result = {(r['security_id'], r['scenario']): r for r in rows}
        if len(result) != len(rows):
            raise ValueError('BRIDGE_DUPLICATE_ROW')
        return result
    event_map, benchmark_map = indexed(event_rows), indexed(benchmark_rows)
    pairs = {(r['security_id'], r['scenario']) for r in source['scenario_outputs']}
    if pairs != set(event_map) or pairs != set(benchmark_map):
        raise ValueError('BRIDGE_COMPLETE_EVENT_BENCHMARK_REQUIRED')
    candidate = deepcopy(source)
    candidate.update(membership=membership_binding, model=model_binding,
        evidence_class='PIT_OBSERVED', state_lineage_id=admission['state_lineage_id'],
        frozen_signal_version=admission['frozen_signal_version'], capture_deadline=admission['capture_deadline'],
        first_available=max(instant(d['first_available']) for d in
            (source, membership, model, events, benchmarks, admission)).isoformat(),
        frozen_at=now.isoformat(), independent_review=admission_binding)
    for row in candidate['scenario_outputs']:
        key = row['security_id'], row['scenario']
        event, benchmark = event_map[key], benchmark_map[key]
        if any(not isinstance(event.get(k), str) or not event[k].strip()
               or event[k] == 'NOT_APPLICABLE' for k in ('episode_id', 'event_type')):
            raise ValueError('BRIDGE_REAL_EVENT_REQUIRED')
        row.update(episode_id=event['episode_id'], event_type=event['event_type'],
                   benchmark=benchmark['benchmark'], first_available=candidate['first_available'],
                   frozen_at=candidate['frozen_at'])
    slot = digest([publisher_binding, admission_binding])
    state = publish(root, candidate_directory + '/' + slot + '/state.json', candidate)
    result = freeze_first_observed(root, state_binding=state, membership_binding=membership_binding,
        model_binding=model_binding, candidate_directory=candidate_directory + '/' + slot + '/first', clock=clock)
    return dict(contract_id=CONTRACT, status='ENG_PRODUCER_READY', source=publisher_binding,
        quarantine=quarantine, candidate=state, first_observed=result,
        production_write_authorized=False, source_owner_admitted=False, observed_count=None)
