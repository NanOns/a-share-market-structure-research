"""Actual scanner publisher in an isolated namespace; publication confers no rights.

Uses byte-bound target facts and the frozen legacy scanner, not cached branch
statuses. Historical facts remain reconstructed. Observation receipts must be
supplied independently; this module never invents first-availability or events.
"""
import json
import gzip
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from .r43_owner_replay import checked, gzrows, ref
from .v4_14_replay_io import digest, publish
from .r43_focus_replay import confirmation
from .validation_cohort_read_contract_r3 import instant

CONTRACT = 'FULL_MARKET_STATE_PRODUCER_OUTPUT_V1'


def build(root, *, candidate_binding, trade_date, revision,
          observation_binding=None, clock=lambda: datetime.now(timezone.utc)):
    from v4.confirmation import package
    head = json.loads(checked(root, candidate_binding).read_bytes())
    if head['accepted_trade_date'] != trade_date:
        raise ValueError('STATE_TARGET_DATE_MISMATCH')
    owner = head['owners'][trade_date]
    checked(root, owner['core'])
    checked(root, head['membership_snapshot'])
    life = json.loads(checked(root, owner['lifecycle']).read_bytes())
    universe = life['active_security_ids']
    if not universe or len(set(universe)) != len(universe):
        raise ValueError('STATE_UNIVERSE_INVALID')
    inputs = gzrows(checked(root, owner['prewatch']))
    by_id = {}
    for row in inputs:
        sid = row['security_id']
        if sid in by_id or sid not in universe or row['trade_date'] != trade_date:
            raise ValueError('STATE_INPUT_CONTAMINATION')
        by_id[sid] = row
    contract, manifest, parameters, machine, _ = package()
    dependencies = {k: contract[k] for k in ('parameters', 'machine_ast', 'legacy_manifest')}
    dependencies['legacy_source'] = manifest['legacy_source']
    dependencies['publisher'] = ref(root, Path(root)/'src/workbench_analysis/full_market_state_publisher_v1.py')
    dependencies['wrapper'] = ref(root, Path(root)/'src/workbench_analysis/r43_focus_replay.py')
    for binding in dependencies.values():
        checked(root, binding)
    from .producer_dependency_archive_v1 import freeze_dependencies
    dependency_archive = freeze_dependencies(root, list(dependencies.values()))
    now = clock()
    if now.tzinfo is None:
        raise ValueError('AWARE_CAPTURE_CLOCK_REQUIRED')
    frozen = now.isoformat()
    observation = None
    if observation_binding:
        observation = json.loads(checked(root, observation_binding).read_bytes())
        if trade_date != now.astimezone(timezone(timedelta(hours=8))).date().isoformat():
            raise ValueError('HISTORICAL_OR_FUTURE_OBSERVATION_FORBIDDEN')
        # A declaration on reconstructed rows is insufficient, even with a receipt.
        if any(r.get('AS_RECORDED') is not True or r.get('PIT_ELIGIBLE') is not True for r in inputs):
            raise ValueError('RECONSTRUCTED_FACTS_CANNOT_BECOME_OBSERVED')
        expected = dict(facts=owner['prewatch'], lifecycle=owner['lifecycle'], membership=head['membership_snapshot'])
        if observation.get('T0') != trade_date or observation.get('sources') != expected:
            raise ValueError('OBSERVATION_SOURCE_BINDING_MISMATCH')
        for receipt in observation['receipts']:
            if not instant(receipt['requested_at']) <= instant(receipt['received_at']) <= instant(receipt['first_available']) <= instant(observation['cutoff']) <= now:
                raise ValueError('INDEPENDENT_SOURCE_CLOCK_INVALID')
        if not observation['receipts'] or set(r['source'] for r in observation['receipts']) != set(expected):
            raise ValueError('INDEPENDENT_SOURCE_RECEIPTS_REQUIRED')
    available = max((instant(r['first_available']) for r in observation['receipts']), default=None) if observation else None
    model = publish(root, 'docs/evidence/state_publisher_models_v1/' + digest(dependencies) + '/model.json',
        dict(model_contract_id=contract['contract_id'], parameters_sha256=dependencies['parameters']['sha256'],
             window_version='TARGET_FACT_R4_27_SESSION_WITH_BOUND_UPSTREAM_WINDOWS',
             scenarios=machine['scenario_priority'], dependencies=dependencies))
    outputs = []
    for sid in sorted(universe):
        row = by_id.get(sid)
        values = (row or {}).get('target_values')
        if values and (values.get('security_id') != sid or values.get('trade_date') != trade_date):
            raise ValueError('STATE_FACT_IDENTITY_MISMATCH')
        from .strict_source_candidate_v2 import validate_cutoff
        if row:
            validate_cutoff(row, trade_date)
        result = confirmation(values) if values else None
        branches = {b['scenario']: b for b in result['scenario_evidence']} if result else {}
        for scenario in machine['scenario_priority']:
            branch = branches.get(scenario, dict(status='UNKNOWN', unknown_reasons=['STATE_FACTS_MISSING'], checks={}))
            reasons = branch['unknown_reasons'] or [k + ':FALSE' for k, v in branch['checks'].items() if v is False]
            outputs.append(dict(security_id=sid, scenario=scenario, state=branch['status'],
                qualification={'TRUE': 'eligible', 'FALSE': 'ineligible', 'UNKNOWN': 'unknown'}[branch['status']],
                eligible_at_T0=False, exclusion_reasons=reasons, checks=branch['checks'],
                first_available=available.isoformat() if available else None, frozen_at=frozen,
                actual_cutoff=observation['cutoff'] if observation else None,
                episode_id=None, event_type=None, benchmark=None,
                unavailable={'episode_id': 'NO_PRIOR_EPISODE', 'event_type': 'SOURCE_PRODUCER_NOT_IMPLEMENTED',
                             'benchmark': 'SOURCE_PRODUCER_NOT_IMPLEMENTED'},
                membership_version=head['membership_snapshot']['sha256'], model_sha256=model['sha256'],
                parameters_sha256=dependencies['parameters']['sha256'],
                source_owners={k: owner[k]['sha256'] for k in ('prewatch', 'lifecycle', 'core')},
                source_window=(row or {}).get('normal_evidence')))
    document = dict(contract_id=CONTRACT, T0=trade_date, revision=revision,
        publication_id='STATE_PUBLISHER:' + digest([candidate_binding, model, observation_binding, revision]),
        scope='ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS', scenario_outputs=outputs,
        membership=head['membership_snapshot'], model=model, candidate_head=candidate_binding,
        source_owners={k: owner[k] for k in ('prewatch', 'lifecycle', 'core')},
        frozen_computation_dependencies=dependency_archive,
        observation=observation_binding, first_available=available.isoformat() if available else None,
        frozen_at=frozen, evidence_class='OBSERVED_SOURCE_CANDIDATE' if observation else 'RECONSTRUCTED_RESEARCH_ONLY',
        production=False, source_owner_admitted=False, production_write_authorized=False,
        observed_count=None, adapter_ready=False,
        adapter_gap='INDEPENDENT_ADMISSION_REQUIRED; EPISODE_EVENT_BENCHMARK_REQUIRED',
        next_gate='INDEPENDENT_STATE_SOURCE_OWNER_ADMISSION')
    slot = digest([candidate_binding, model, observation_binding, revision])
    path = 'docs/evidence/state_publisher_outputs_v1/' + slot + '/output.json.gz'
    # Retry preserves the original actual clock and exact bytes.
    if (Path(root) / path).exists():
        old = json.loads(gzip.decompress((Path(root) / path).read_bytes()))
        document['frozen_at'] = old['frozen_at']
        for row in document['scenario_outputs']:
            row['frozen_at'] = old['frozen_at']
    from .v4_14_replay_io import canonical, path_in
    _, target = path_in(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = gzip.compress(canonical(document) + b'\n', mtime=0)
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix='.state-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.read_bytes() != raw:
                raise ValueError('STATE_CHANGED_BYTE_OVERWRITE_FORBIDDEN')
    finally:
        os.unlink(temporary)
    return ref(root, target)
