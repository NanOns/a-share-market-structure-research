"""Future first-capture preflight only; never issues production authority."""
import json
from .r43_owner_replay import checked
from .validation_cohort_read_contract_r3 import enrollment_identity, instant, validate_frozen

CONTRACT = 'COHORT_FIRST_CAPTURE_READINESS_R1'


def inspect_daily_candidate(root, *, candidate_binding, trade_date, cutoff):
    """Observe DD's sealed candidate without enrollment, grant issuance or CAS.

    This boundary deliberately requires the real producer's Head-bound artifacts.
    Ordinary derived events and a source-ready receipt cannot replace them.
    A candidate is not yet an accepted Head and can only pass isolated preflight.
    """
    candidate = json.loads(checked(root, candidate_binding).read_bytes())
    if candidate.get('accepted_trade_date') != trade_date:
        raise ValueError('CAPTURE_DAILY_CANDIDATE_DATE_MISMATCH')
    owner = candidate.get('owners', {}).get(trade_date, {}).get('validation_cohort')
    receipt = candidate.get('cohort_capture_receipts', {}).get(trade_date)
    grant = candidate.get('cohort_write_grants', {}).get(trade_date)
    missing = [name for name, binding in (
        ('INDEPENDENT_VALIDATION_COHORT_OWNER', owner),
        ('COMPLETE_AS_RECORDED_SIGNAL_PRODUCER_RECEIPT', receipt),
        ('SEPARATE_FIRST_CAPTURE_WRITE_GRANT', grant)) if not binding]
    result = dict(contract_id='DD_R22_COHORT_CAPTURE_BOUNDARY_R1',
                  candidate_binding=candidate_binding, trade_date=trade_date,
                  production_write_authorized=False, observed_count=None,
                  matured_count=None, settled_count=None,
                  blocks_local_daily_publication=False)
    if missing:
        return dict(result, status='SOURCE_INCOMPLETE', missing_inputs=missing,
                    preflight_invoked=False, reason='REAL_FULL_SIGNAL_PRODUCER_AND_ADMISSION_REQUIRED')
    try:
        owner_document = json.loads(checked(root, owner).read_bytes())
        preflight = prepare_capture(root, accepted_head=candidate_binding,
                                    owner_binding=owner, trade_date=trade_date,
                                    revision=owner_document['revision'], cutoff=cutoff)
    except (ValueError, KeyError, TypeError) as exc:
        return dict(result, status='CAPTURE_PREFLIGHT_REJECTED',
                    preflight_invoked=True, reason=str(exc))
    return dict(result, status='ISOLATED_CAPTURE_CANDIDATE_READY',
                preflight_invoked=True, preflight=preflight,
                next_gate='INDEPENDENT_OWNER_ADMISSION_AND_DD_R22_CAS')


def prepare_capture(root, *, accepted_head, owner_binding, trade_date, revision, cutoff):
    """Validate independently bound full signal ledger and a separate writer grant.

    accepted_head must come from the verified daily-job context, never HTTP input.
    A successful preflight is an isolated candidate, not permission to mutate Head.
    """
    head = json.loads(checked(root, accepted_head).read_bytes())
    if head.get('owners', {}).get(trade_date, {}).get('validation_cohort') != owner_binding:
        raise ValueError('CAPTURE_OWNER_BINDING_REQUIRED')
    receipt_ref = head.get('cohort_capture_receipts', {}).get(trade_date)
    grant_ref = head.get('cohort_write_grants', {}).get(trade_date)
    if not receipt_ref or not grant_ref:
        raise ValueError('CAPTURE_RECEIPT_AND_WRITE_GRANT_REQUIRED')
    receipt = json.loads(checked(root, receipt_ref).read_bytes())
    grant = json.loads(checked(root, grant_ref).read_bytes())
    if (grant.get('contract_id') != 'COHORT_FIRST_CAPTURE_WRITE_GRANT_R1'
            or grant.get('capability') != 'PREPARE_FIRST_CAPTURE'
            or grant.get('authorized') is not True or grant.get('revoked') is not False
            or grant.get('owner') != owner_binding or grant.get('trade_date') != trade_date
            or grant.get('revision') != revision or grant.get('source_receipt') != receipt_ref):
        raise ValueError('CAPTURE_WRITE_GRANT_IDENTITY_REQUIRED')
    if not instant(grant['valid_from']) <= instant(cutoff) < instant(grant['valid_until']):
        raise ValueError('CAPTURE_WRITE_GRANT_EXPIRED')
    if (receipt.get('contract_id') != 'COHORT_COMPLETE_SIGNAL_CAPTURE_R1'
            or receipt.get('T0') != trade_date or receipt.get('revision') != revision
            or receipt.get('membership_basis') != 'AS_RECORDED'
            or not receipt.get('membership_version')
            or receipt.get('scope') != 'ALL_ELIGIBLE_AND_INELIGIBLE_SIGNALS'):
        raise ValueError('CAPTURE_COMPLETE_AS_RECORDED_RECEIPT_REQUIRED')
    for field in ('first_available', 'captured_at', 'accepted_at'):
        if instant(receipt[field]) > instant(cutoff):
            raise ValueError('CAPTURE_FUTURE_AVAILABILITY')
    if not instant(receipt['first_available']) <= instant(receipt['captured_at']) <= instant(receipt['accepted_at']):
        raise ValueError('CAPTURE_TIMESTAMP_ORDER_REQUIRED')
    ledger = json.loads(checked(root, receipt['signals']).read_bytes())
    rows = ledger['signals']
    if type(receipt.get('signal_count')) is not int or receipt['signal_count'] != len(rows):
        raise ValueError('CAPTURE_FULL_LEDGER_COUNT_REQUIRED')
    identities = set()
    eligible = []
    for row in rows:
        identity = enrollment_identity(row)
        if identity in identities:
            raise ValueError('CAPTURE_DUPLICATE_IDENTITY')
        identities.add(identity)
        if (row.get('T0') != trade_date or row.get('publication_id') != receipt.get('publication_id')
                or row.get('frozen_signal_version') != receipt.get('frozen_signal_version')
                or row.get('parameters_sha256') != receipt.get('parameters_sha256')
                or not receipt.get('parameters_sha256')
                or row.get('eligible_at_T0') not in (True, False)
                or type(row.get('eligible_at_T0')) is not bool):
            raise ValueError('CAPTURE_FROZEN_VERSION_OR_ELIGIBILITY_REQUIRED')
        # Validate ineligible rows' frozen provenance too, without enrolling them.
        validate_frozen(dict(row, eligible_at_T0=True), cutoff=cutoff, trade_date=trade_date)
        if instant(row['asof_first_available']) < instant(receipt['first_available']):
            raise ValueError('CAPTURE_ROW_PRECEDES_SOURCE_AVAILABILITY')
        if not row['eligible_at_T0'] and not row.get('ineligibility_reason'):
            raise ValueError('CAPTURE_INELIGIBILITY_REASON_REQUIRED')
        if row['eligible_at_T0']:
            eligible.append(row)
    owner = json.loads(checked(root, owner_binding).read_bytes())
    if (owner.get('revision') != revision or owner.get('trade_date') != trade_date
            or owner.get('enrollments') != eligible):
        raise ValueError('CAPTURE_OWNER_FULL_ELIGIBLE_SET_REQUIRED')
    return dict(contract_id=CONTRACT, status='ISOLATED_CAPTURE_CANDIDATE_READY',
                source_receipt=receipt_ref, write_grant=grant_ref, revision=revision,
                eligible_count=len(eligible), ineligible_count=len(rows)-len(eligible),
                production_write_authorized=False, observed_count=None,
                matured_count=None, settled_count=None,
                next_gate='INDEPENDENT_OWNER_ADMISSION_AND_DD_R22_CAS')
