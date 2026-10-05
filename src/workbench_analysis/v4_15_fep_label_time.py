"""V4_15_FEP_LABEL_TIME_AUTHORITY_V1: exact additive knowledge-time receipts.

No price evaluation, calendar maturity inference, or accepted-head mutation.
The registry is an explicit owner allocation, never a latest-file search.
"""
import json
from pathlib import Path

from .fep_e1.contracts import digest, exact, instant

CONTRACT = 'V4_15_FEP_LABEL_TIME_AUTHORITY_V1'
IDENTITY = ('enrollment_id', 'horizon', 'outcome_contract_id',
            'outcome_revision_id', 'evaluation_revision', 'evaluation_source_digest')
TIMES = ('source_fact_available_at', 'label_training_mature_at',
         'label_revision_available_at')


def identity(row):
    return {k: row[k] for k in IDENTITY} | {'source_row_digest': digest(row)}


def resolve(root, row, cutoff):
    """Read only exact allocated receipts; missing proof stays denominator-pending."""
    root = Path(root)
    contract = json.loads((root / 'config/v4_15_fep_label_time_authority_v1.json').read_bytes())
    if contract['contract_id'] != CONTRACT:
        raise ValueError('FEP_LABEL_TIME_CONTRACT_MISMATCH')
    instant(cutoff)
    key = identity(row)
    allocations = [e for e in contract['allocations'] if e['identity'] == key]
    if len(allocations) > 1:
        raise ValueError('FEP_LABEL_TIME_AMBIGUOUS_ALLOCATION')
    pending = dict(contract_id=CONTRACT, identity=key, training_allowed=False,
                   quality='PENDING', binding=None,
                   times={t: 'NOT_PROVEN' for t in TIMES})
    if not allocations:
        return pending | {'reason': 'NO_EXACT_OWNER_TIME_RECEIPTS'}
    allocation = allocations[0]
    source_row = exact(root, allocation['upstream_row'])
    if identity(source_row) != key:
        raise ValueError('FEP_LABEL_TIME_UPSTREAM_MISMATCH')
    engineering = row['evidence_class'] == 'ENGINEERING_VECTOR'
    expected_class = 'ENGINEERING_FIXTURE' if engineering else 'REAL_ACCEPTED_EVIDENCE'
    receipts = {}
    for kind in ('source', 'maturity', 'revision'):
        refs = allocation.get(kind, [])
        if not refs:
            return pending | {'reason': 'INCOMPLETE_OWNER_TIME_RECEIPTS'}
        receipts[kind] = []
        for ref in refs:
            receipt = exact(root, ref)
            if (receipt['identity'] != key or receipt['evidence_class'] != expected_class
                    or receipt['status'] != 'ACCEPTED' or receipt['kind'] != kind):
                raise ValueError('FEP_LABEL_TIME_RECEIPT_AUTHORITY_MISMATCH')
            instant(receipt['available_at'])
            receipts[kind].append(receipt)
    # Exact consumed fact inventory, not merely one convenient source timestamp.
    consumed = allocation['consumed_fact_ids']
    actual = [r['fact_id'] for r in receipts['source']]
    if not consumed or len(set(actual)) != len(actual) or sorted(actual) != sorted(consumed):
        raise ValueError('FEP_LABEL_TIME_CONSUMED_FACT_INVENTORY_MISMATCH')
    if len(receipts['maturity']) != 1 or len(receipts['revision']) != 1:
        raise ValueError('FEP_LABEL_TIME_SINGLE_OWNER_RECEIPT_REQUIRED')
    maturity = receipts['maturity'][0]
    if (maturity['full_window_complete'] is not True
            or maturity['required_quality_complete'] is not True
            or maturity['horizon'] != row['horizon'] or row['outcome_status'] != 'OBSERVED'):
        return pending | {'reason': 'WINDOW_OR_QUALITY_NOT_PROVEN'}
    source = max(receipts['source'], key=lambda r: instant(r['available_at']))['available_at']
    times = dict(zip(TIMES, (source, maturity['available_at'], receipts['revision'][0]['available_at'])))
    if instant(times[TIMES[2]]) < instant(source):
        raise ValueError('FEP_REVISION_BEFORE_SOURCE')
    if instant(times[TIMES[1]]) < instant(source):
        raise ValueError('FEP_MATURITY_BEFORE_COMPLETE_SOURCE')
    # Real maturity must be granted separately by the protected V4-15 owner head.
    if not engineering:
        head = exact(root, contract['accepted_owner_head'])
        if row['horizon'] not in head['PROVED_HORIZONS']:
            return pending | {'times': times, 'reason': 'NO_REAL_MATURITY_EVIDENCE'}
        return pending | {'times': times, 'reason': 'REAL_TIME_RECEIPT_ACCEPTANCE_NOT_GRANTED'}
    eligible = all(instant(t) <= instant(cutoff) for t in times.values())
    authority = dict(upstream_digest=digest(row), **times, evidence_class=expected_class,
                     contract_id=CONTRACT, receipt_digest=digest(allocation))
    return pending | dict(times=times, training_allowed=eligible,
                          quality='OBSERVED', binding=authority if eligible else None,
                          reason='ELIGIBLE' if eligible else 'PIT_NOT_YET_VISIBLE')
