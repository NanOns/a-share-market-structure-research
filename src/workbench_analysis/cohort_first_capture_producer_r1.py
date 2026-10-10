"""Complete first-capture extraction into immutable engineering candidates.

Consumes a daily Head-bound producer, never Focus/corrected historical events.
Does not issue a grant, mutate an accepted Head or enroll a production sample.
"""
import json
import hashlib
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .r43_owner_replay import checked
from .v4_14_replay_io import publish, digest, canonical, path_in
from .validation_cohort_read_contract_r3 import CONTRACT, enrollment_identity, instant, validate_frozen

CONTRACT_ID = 'COHORT_FIRST_CAPTURE_PRODUCER_R1'


def freeze_source_candidate(root, *, source_owner_binding, source_manifest_binding,
                            candidate_directory, clock=lambda: datetime.now(timezone.utc)):
    """Freeze a new real-time source candidate from an independent full Owner.

    The manifest and Owner are byte-bound candidate inputs with asserted lineage;
    these checks do not establish independent admission or formal authority.
    No Head or grant is created and every result remains isolated.
    clock is injectable only for isolated regression; production uses UTC now.
    """
    directory = Path(candidate_directory)
    if directory.is_absolute() or '..' in directory.parts or directory.parts[:2] != ('docs', 'evidence'):
        raise ValueError('ISOLATED_EVIDENCE_DIRECTORY_REQUIRED')
    owner = json.loads(checked(root, source_owner_binding).read_bytes())
    manifest = json.loads(checked(root, source_manifest_binding).read_bytes())
    now = clock()
    if now.tzinfo is None:
        raise ValueError('AWARE_CAPTURE_CLOCK_REQUIRED')
    day = now.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    if (manifest.get('contract_id') != 'COHORT_FIRST_CAPTURE_SOURCE_MANIFEST_R1'
            or manifest.get('source_owner') != source_owner_binding
            or manifest.get('T0') != day or manifest.get('evidence_class') != 'PIT_OBSERVED'
            or manifest.get('membership_basis') != 'AS_RECORDED'
            or manifest.get('scope') != 'ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS'
            or not all(isinstance(manifest.get(k), str) and manifest[k].strip()
                       for k in ('revision', 'membership_version', 'publication_id',
                                 'frozen_signal_version', 'parameters_sha256'))):
        raise ValueError('CAPTURE_REALTIME_FULL_SOURCE_MANIFEST_REQUIRED')
    if not re.fullmatch('[0-9a-f]{64}', manifest['parameters_sha256']):
        raise ValueError('CAPTURE_PARAMETERS_SHA256_REQUIRED')
    if not instant(manifest['first_available']) <= instant(manifest['accepted_at']) <= now <= instant(manifest['capture_deadline']):
        raise ValueError('CAPTURE_REALTIME_OBSERVATION_SLOT_REQUIRED')
    rows = owner['cohort_signals']
    seen = set()
    for row in rows:
        key = enrollment_identity(row)
        if key in seen:
            raise ValueError('CAPTURE_DUPLICATE_IDENTITY')
        seen.add(key)
        if (row.get('T0') != day or type(row.get('eligible_at_T0')) is not bool
                or any(row.get(k) != manifest.get(k) for k in ('publication_id', 'frozen_signal_version', 'parameters_sha256'))):
            raise ValueError('CAPTURE_FROZEN_VERSION_OR_ELIGIBILITY_REQUIRED')
        validate_frozen(dict(row, eligible_at_T0=True), cutoff=now.isoformat(), trade_date=day)
        if not row['eligible_at_T0'] and not row.get('ineligibility_reason'):
            raise ValueError('CAPTURE_INELIGIBILITY_REASON_REQUIRED')
        if not instant(manifest['first_available']) <= instant(row['asof_first_available']) <= instant(row['frozen_at_T0']):
            raise ValueError('CAPTURE_ROW_PRECEDES_SOURCE_AVAILABILITY')
    if type(manifest.get('signal_count')) is not int or manifest['signal_count'] != len(rows):
        raise ValueError('CAPTURE_COMPLETE_OWNER_SIGNAL_SET_REQUIRED')
    # Freeze producer's own capture time without rewriting any original row.
    identity = digest([day, manifest['publication_id'], manifest['revision']])
    ledger_path = (directory / identity / 'signals.json').as_posix()
    producer_path = (directory / identity / 'producer.json').as_posix()
    ledger = dict(signals=rows)
    raw = canonical(ledger) + b'\n'
    signals = dict(path=ledger_path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    producer = dict(manifest, contract_id='COHORT_COMPLETE_SIGNAL_PRODUCER_R1',
                    qualification_source='ACCEPTED_STATE_OWNER', signals=signals,
                    captured_at=now.isoformat(), accepted_at=now.isoformat(),
                    source_manifest=source_manifest_binding)
    # Never rewrite a first-capture time on retries: a matching existing source
    # returns its original producer, while changed same-slot source is denied.
    _, existing = path_in(root, producer_path)
    if existing.exists():
        previous = json.loads(existing.read_bytes())
        if previous.get('source_manifest') != source_manifest_binding or previous.get('source_owner') != source_owner_binding:
            raise ValueError('FROZEN_SOURCE_REWRITE_FORBIDDEN')
        checked(root, previous['signals'])
        from .v4_14_replay_io import ref
        return dict(status='ISOLATED_SOURCE_FIRST_CAPTURE_FROZEN', producer=ref(root, producer_path), production_write_authorized=False)
    _, ledger_file = path_in(root, ledger_path)
    if ledger_file.exists() and ledger_file.read_bytes() != raw:
        raise ValueError('FROZEN_SOURCE_REWRITE_FORBIDDEN')
    publish(root, ledger_path, ledger)
    producer_ref = publish(root, producer_path, producer)
    return dict(status='ISOLATED_SOURCE_FIRST_CAPTURE_FROZEN', producer=producer_ref,
                production_write_authorized=False)


def extract_candidate(root, *, candidate_binding, trade_date, cutoff, candidate_directory):
    directory = Path(candidate_directory)
    if directory.is_absolute() or '..' in directory.parts or directory.parts[:2] != ('docs', 'evidence'):
        raise ValueError('ISOLATED_EVIDENCE_DIRECTORY_REQUIRED')
    head = json.loads(checked(root, candidate_binding).read_bytes())
    if head.get('accepted_trade_date') != trade_date:
        raise ValueError('CAPTURE_DAILY_CANDIDATE_DATE_MISMATCH')
    producer_ref = head.get('cohort_signal_producers', {}).get(trade_date)
    if not producer_ref:
        return dict(contract_id=CONTRACT_ID, status='SOURCE_INCOMPLETE', observed_count=None,
                    production_write_authorized=False, missing_inputs=['COMPLETE_FIRST_CAPTURE_SIGNAL_PRODUCER'])
    producer = json.loads(checked(root, producer_ref).read_bytes())
    if (producer.get('contract_id') != 'COHORT_COMPLETE_SIGNAL_PRODUCER_R1'
            or producer.get('T0') != trade_date or producer.get('membership_basis') != 'AS_RECORDED'
            or producer.get('evidence_class') != 'PIT_OBSERVED'
            or producer.get('scope') != 'ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS'
            or producer.get('qualification_source') != 'ACCEPTED_STATE_OWNER'
            or not all(producer.get(k) for k in ('revision', 'membership_version', 'publication_id',
                                                 'frozen_signal_version', 'parameters_sha256'))):
        raise ValueError('CAPTURE_FULL_PRODUCER_CONTRACT_REQUIRED')
    if not isinstance(producer['parameters_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', producer['parameters_sha256']):
        raise ValueError('CAPTURE_PARAMETERS_SHA256_REQUIRED')
    times = [instant(producer[k]) for k in ('first_available', 'captured_at', 'accepted_at')]
    if not times[0] <= times[1] <= times[2] <= instant(cutoff):
        raise ValueError('CAPTURE_TIMESTAMP_ORDER_REQUIRED')
    source_owner_ref = producer['source_owner']
    if source_owner_ref != head.get('owners', {}).get(trade_date, {}).get('state'):
        raise ValueError('CAPTURE_ACCEPTED_STATE_OWNER_REQUIRED')
    source_owner = json.loads(checked(root, source_owner_ref).read_bytes())
    ledger = json.loads(checked(root, producer['signals']).read_bytes())
    rows = ledger['signals']
    # Exact equality proves this is the entire producer output, not a UI subset.
    if source_owner.get('cohort_signals') != rows or type(producer.get('signal_count')) is not int or producer['signal_count'] != len(rows):
        raise ValueError('CAPTURE_COMPLETE_OWNER_SIGNAL_SET_REQUIRED')
    identities = set()
    eligible = []
    for row in rows:
        identity = enrollment_identity(row)
        if identity in identities:
            raise ValueError('CAPTURE_DUPLICATE_IDENTITY')
        identities.add(identity)
        if (row.get('T0') != trade_date or type(row.get('eligible_at_T0')) is not bool
                or any(row.get(k) != producer[k] for k in ('publication_id', 'frozen_signal_version', 'parameters_sha256'))):
            raise ValueError('CAPTURE_FROZEN_VERSION_OR_ELIGIBILITY_REQUIRED')
        validate_frozen(dict(row, eligible_at_T0=True), cutoff=cutoff, trade_date=trade_date)
        if instant(row['asof_first_available']) < times[0]:
            raise ValueError('CAPTURE_ROW_PRECEDES_SOURCE_AVAILABILITY')
        if not row['eligible_at_T0'] and not row.get('ineligibility_reason'):
            raise ValueError('CAPTURE_INELIGIBILITY_REASON_REQUIRED')
        if row['eligible_at_T0']:
            eligible.append(row)
    # A stable slot path prevents a changed same-revision batch from overwriting
    # the first frozen candidate. Changed identities require a new revision.
    slot = digest([trade_date, producer['publication_id'], producer['revision']])
    path = (directory / (slot + '.json')).as_posix()
    owner = dict(contract_id=CONTRACT, trade_date=trade_date,
                 revision=producer['revision'], enrollments=eligible)
    receipt = dict(producer, contract_id='COHORT_COMPLETE_SIGNAL_CAPTURE_R1')
    def planned_ref(path, value):
        raw = canonical(value) + b'\n'
        return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    owner_path = (directory / slot / 'owner.json').as_posix()
    receipt_path = (directory / slot / 'capture_receipt.json').as_posix()
    owner_ref = planned_ref(owner_path, owner)
    receipt_ref = planned_ref(receipt_path, receipt)
    bundle = dict(contract_id=CONTRACT_ID, candidate_head=candidate_binding,
                  source_producer=producer_ref, source_owner=source_owner_ref,
                  owner=owner, owner_binding=owner_ref, capture_receipt_binding=receipt_ref,
                  complete_signal_ledger=rows,
                  capture_receipt=receipt,
                  production=False, production_write_authorized=False,
                  observed_count=None, matured_count=None, settled_count=None,
                  next_gate='INDEPENDENT_OWNER_ADMISSION_AND_SEPARATE_WRITE_GRANT')
    # Reject known collisions before creating any fragment. The final manifest
    # is published last and is the only visibility marker for a complete bundle.
    for target, document in ((owner_path, owner), (receipt_path, receipt), (path, bundle)):
        _, target_path = path_in(root, target)
        if target_path.exists() and target_path.read_bytes() != canonical(document) + b'\n':
            raise ValueError('REPLAY_CHANGED_BYTE_OVERWRITE_FORBIDDEN')
    publish(root, owner_path, owner)
    publish(root, receipt_path, receipt)
    binding = publish(root, path, bundle)
    return dict(contract_id=CONTRACT_ID, status='ISOLATED_FIRST_CAPTURE_EXTRACTED',
                candidate=binding, eligible_count=len(eligible), ineligible_count=len(rows)-len(eligible),
                owner_binding=owner_ref, capture_receipt_binding=receipt_ref,
                observed_count=None, production_write_authorized=False,
                next_gate=bundle['next_gate'])
