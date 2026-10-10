"""Byte-bound full-market State producer adapter; never issues authority.

The verified daily-job context supplies upstream bindings. A self-described
producer is preserved for independent review, not independently admitted here.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .r43_owner_replay import checked
from .v4_14_replay_io import publish, digest
from .validation_cohort_read_contract_r3 import instant, validate_frozen
from .cohort_first_capture_producer_r1 import freeze_source_candidate, extract_candidate

CONTRACT = 'FULL_STATE_SIGNAL_SOURCE_FIRST_OBSERVED_CANDIDATE'


def quarantine_publisher(root, *, publisher_binding, candidate_directory):
    """Read actual publisher output without laundering research into PIT.

    Incomplete observed candidates also remain quarantined. Independent source
    admission and complete event/benchmark facts precede freeze_first_observed.
    """
    import gzip
    directory = Path(candidate_directory)
    if directory.is_absolute() or '..' in directory.parts or directory.parts[:2] != ('docs', 'evidence'):
        raise ValueError('ISOLATED_EVIDENCE_DIRECTORY_REQUIRED')
    raw = checked(root, publisher_binding).read_bytes()
    state = json.loads(gzip.decompress(raw))
    if state['contract_id'] != 'FULL_MARKET_STATE_PRODUCER_OUTPUT_V1':
        raise ValueError('FULL_MARKET_STATE_PUBLISHER_REQUIRED')
    if state.get('production') is not False or state.get('production_write_authorized') is not False:
        raise ValueError('QUARANTINE_PERMISSION_OVERCLAIM')
    rows = state['scenario_outputs']
    if any(r['state'] not in ('TRUE', 'FALSE', 'UNKNOWN') or r['eligible_at_T0'] is not False for r in rows):
        raise ValueError('QUARANTINE_INVALID_QUALIFICATION')
    document = dict(contract_id='STATE_PUBLISHER_QUARANTINE_V1', source=publisher_binding,
        T0=state['T0'], evidence_class=state['evidence_class'], signal_count=len(rows),
        state_counts={k: sum(r['state'] == k for r in rows) for k in ('TRUE', 'FALSE', 'UNKNOWN')},
        status='RESEARCH_CANDIDATE_FROZEN', production=False, source_owner_admitted=False,
        production_write_authorized=False, eligible_at_T0=False, observed_count=None,
        first_available=state['first_available'], frozen_at=state['frozen_at'],
        next_gate='INDEPENDENT_ADMISSION_REQUIRED', adapter_gap=state['adapter_gap'])
    return publish(root, (directory / digest(publisher_binding) / 'quarantine.json').as_posix(), document)


def freeze_first_observed(root, *, state_binding, membership_binding, model_binding,
                          candidate_directory, clock=lambda: datetime.now(timezone.utc)):
    """Generate complete signal rows from original State scenario output.

    Missing or subset sources fail closed. No historical reconstruction, Focus,
    Head CAS or writer grant occurs. Injectable clock is for synthetic tests.
    """
    directory = Path(candidate_directory)
    if directory.is_absolute() or '..' in directory.parts or directory.parts[:2] != ('docs', 'evidence'):
        raise ValueError('ISOLATED_EVIDENCE_DIRECTORY_REQUIRED')
    if not state_binding:
        return dict(status='SOURCE_INCOMPLETE', formal_status='BLOCKED', production_write_authorized=False)
    state, membership, model = [json.loads(checked(root, b).read_bytes())
                                for b in (state_binding, membership_binding, model_binding)]
    now = clock()
    if now.tzinfo is None:
        raise ValueError('AWARE_CAPTURE_CLOCK_REQUIRED')
    day = now.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    if (state.get('contract_id') != 'FULL_MARKET_STATE_PRODUCER_OUTPUT_V1'
            or state.get('scope') != 'ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS'
            or state.get('evidence_class') != 'PIT_OBSERVED' or state.get('T0') != day
            or state.get('membership') != membership_binding or state.get('model') != model_binding
            or membership.get('T0') != day or membership.get('membership_basis') != 'AS_RECORDED'):
        raise ValueError('FULL_MARKET_REALTIME_STATE_SOURCE_REQUIRED')
    for source in (state, membership, model):
        if not instant(source['first_available']) <= instant(source['frozen_at']) <= now:
            raise ValueError('STATE_SOURCE_AVAILABILITY_CUTOFF')
    if now > instant(state['capture_deadline']):
        raise ValueError('STATE_LATE_CAPTURE')
    for source, fields in ((state, ('publication_id', 'revision', 'state_lineage_id', 'frozen_signal_version')),
                           (membership, ('membership_version',)),
                           (model, ('model_contract_id', 'parameters_sha256', 'window_version'))):
        if any(not isinstance(source.get(k), str) or not source[k].strip() for k in fields):
            raise ValueError('STATE_VERSION_IDENTITY_REQUIRED')
    universe = membership['security_ids']
    scenarios = model['scenarios']
    if (not universe or not scenarios or len(set(universe)) != len(universe)
            or len(set(scenarios)) != len(scenarios)):
        raise ValueError('STATE_COMPLETE_UNIVERSE_REQUIRED')
    expected = {(sid, scenario) for sid in universe for scenario in scenarios}
    inputs = state['scenario_outputs']
    pairs = [(r['security_id'], r['scenario']) for r in inputs]
    if len(set(pairs)) != len(pairs) or set(pairs) != expected:
        raise ValueError('STATE_COMPLETE_SCENARIO_SET_REQUIRED')
    rows = []
    source_available = max(instant(s['first_available']) for s in (state, membership, model))
    for item in inputs:
        if item.get('state') not in ('TRUE', 'FALSE', 'UNKNOWN'):
            raise ValueError('STATE_MISSING_OR_INVALID')
        if item['state'] != 'TRUE' and not item.get('exclusion_reasons'):
            raise ValueError('STATE_EXCLUSION_REASON_REQUIRED')
        available = instant(item['first_available'])
        frozen = instant(item['frozen_at'])
        if not source_available <= available <= frozen <= instant(state['frozen_at']):
            raise ValueError('STATE_ROW_AVAILABILITY_CUTOFF')
        row = dict(model_contract_id=model['model_contract_id'], state_lineage_id=state['state_lineage_id'],
            entity_type='STOCK', entity_id=item['security_id'], episode_id=item['episode_id'],
            event_type=item['event_type'], T0=day, publication_id=state['publication_id'],
            frozen_signal_version=state['frozen_signal_version'], parameters_sha256=model['parameters_sha256'],
            window_version=model['window_version'], membership_version=membership['membership_version'],
            scenario=item['scenario'], state=item['state'], eligible_at_T0=item['state'] == 'TRUE',
            ineligibility_reason=None if item['state'] == 'TRUE' else item['exclusion_reasons'],
            asof_first_available=item['first_available'], frozen_at_T0=item['frozen_at'],
            benchmark=item['benchmark'], no_lookahead=True, evidence_class='PIT_OBSERVED',
            cohort_namespace='SHADOW', qualification_source='FULL_MARKET_STATE_PRODUCER_OUTPUT_V1')
        validate_frozen(dict(row, eligible_at_T0=True), cutoff=now.isoformat(), trade_date=day)
        rows.append(row)
    slot = digest([day, state['publication_id'], state['revision']])
    base = (directory / slot).as_posix()
    document = dict(contract_id=CONTRACT, T0=day, state_source=state_binding,
        membership=membership_binding, model=model_binding, cohort_signals=rows,
        production=False, source_owner_admitted=False, production_write_authorized=False,
        observed_count=None, next_gate='INDEPENDENT_SOURCE_OWNER_AND_WRITER_GRANT')
    owner = publish(root, base + '/state_owner.json', document)
    manifest = publish(root, base + '/source_manifest.json', dict(
        contract_id='COHORT_FIRST_CAPTURE_SOURCE_MANIFEST_R1', source_owner=owner, T0=day,
        publication_id=state['publication_id'], revision=state['revision'],
        frozen_signal_version=state['frozen_signal_version'], parameters_sha256=model['parameters_sha256'],
        membership_version=membership['membership_version'], membership_basis='AS_RECORDED',
        evidence_class='PIT_OBSERVED', scope='ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS', signal_count=len(rows),
        first_available=source_available.isoformat(), accepted_at=state['frozen_at'],
        capture_deadline=state['capture_deadline']))
    producer = freeze_source_candidate(root, source_owner_binding=owner, source_manifest_binding=manifest,
        candidate_directory=base + '/producer', clock=clock)
    head = publish(root, base + '/isolated_candidate.json', dict(accepted_trade_date=day,
        owners={day: {'state': owner}}, cohort_signal_producers={day: producer['producer']}, production=False))
    extracted = extract_candidate(root, candidate_binding=head, trade_date=day, cutoff=now.isoformat(),
                                  candidate_directory=base + '/extracted')
    return dict(contract_id=CONTRACT, status='ENGINEERING_CANDIDATE_CAPTURED', formal_status='BLOCKED',
        state_owner=owner, source_manifest=manifest, candidate_binding=head, extraction=extracted,
        source_owner_admitted=False, production_write_authorized=False, observed_count=None,
        next_gate='INDEPENDENT_SOURCE_OWNER_AND_WRITER_GRANT')
