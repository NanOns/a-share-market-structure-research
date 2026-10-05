"""FEP_LABEL_ADAPTER_V1: copy exact V4-15 outcomes, never evaluate prices.

Legacy outcomes do not provide the frozen three-time authority required by E1.
Such rows remain denominator evidence and cannot become accepted training labels.
"""
from .contracts import exact, digest, instant

TIMES = ('source_fact_available_at', 'label_training_mature_at', 'label_revision_available_at')
FIELDS = {'ABS_RETURN_N': 'R_N', 'MFE_N': 'MFE_N', 'MAE_N': 'MAE_N', 'PATH_MDD_CLOSE_N': 'PATH_MDD_CLOSE_N'}


def project_with_owner_time(root, row, target, *, authority_head, cutoff):
    """Use the additive exact owner registry; never insert a pending binding."""
    from ..v4_15_fep_label_time import resolve
    authority = resolve(root, row, cutoff)
    if not authority['training_allowed']:
        return dict(training_allowed=False, quality='PENDING',
                    reason=authority['reason'], upstream_key=row['outcome_revision_id'],
                    time_authority=authority)
    return project(row, target, authority_head=authority_head,
                   time_authority=authority['binding'])


def read_source(store, binding, upstream_key, upstream_revision, source_digest):
    if binding not in store.refs('outcomes'):
        raise ValueError('FEP_UPSTREAM_ROW_NOT_REGISTERED')
    row = exact(store.root, binding)
    if (row['outcome_revision_id'], str(row['evaluation_revision']), row['evaluation_source_digest']) != (upstream_key, str(upstream_revision), source_digest):
        raise ValueError('FEP_UPSTREAM_REVISION_DIGEST_MISMATCH')
    return row


def project(row, target, *, authority_head, time_authority=None):
    if row['horizon'] != target['horizon']:
        raise ValueError('FEP_LABEL_HORIZON_MISMATCH')
    family = target['family']
    if family not in FIELDS:
        return dict(training_allowed=False, quality='NOT_IMPLEMENTED', reason='TARGET_ADAPTER_NOT_ENABLED')
    if time_authority is None or not all(t in time_authority for t in TIMES):
        return dict(training_allowed=False, quality=row['outcome_status'], reason='FEP_E1_CONTRACT_CONFLICT_THREE_TIME_AUTHORITY_MISSING', upstream_key=row['outcome_revision_id'])
    if time_authority['upstream_digest'] != digest(row):
        raise ValueError('FEP_TIME_AUTHORITY_ROW_MISMATCH')
    for key in TIMES:
        instant(time_authority[key])
    if instant(time_authority[TIMES[2]]) < instant(time_authority[TIMES[0]]):
        raise ValueError('FEP_REVISION_BEFORE_SOURCE')
    real = row['evidence_class'] != 'ENGINEERING_VECTOR'
    if real and (not authority_head['PROVED_HORIZONS'] or row['horizon'] not in authority_head['PROVED_HORIZONS']):
        return dict(training_allowed=False, quality='PENDING', reason='NO_REAL_MATURITY_EVIDENCE')
    if real:
        # A caller-supplied horizon/time dictionary cannot promote this missing
        # owner interface. Reopening requires a separately accepted contract.
        return dict(training_allowed=False, quality='PENDING', reason='FEP_E1_REAL_ADAPTER_NOT_ENABLED')
    value = row.get(FIELDS[family])
    quality = row.get('path_quality', row['outcome_status']) if family != 'ABS_RETURN_N' else row['outcome_status']
    return dict(numeric_value=value, quality=quality,
                training_allowed=value is not None and quality == 'OBSERVED',
                times={t: time_authority[t] for t in TIMES}, upstream_digest=digest(row),
                evidence_class='REAL_ACCEPTED_EVIDENCE' if real else 'ENGINEERING_FIXTURE')
