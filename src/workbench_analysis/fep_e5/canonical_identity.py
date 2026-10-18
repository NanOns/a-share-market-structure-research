"""Read-only canonical authority availability gate; never synthesize identities.

This gate diagnoses necessary upstream authority. It does not accept predictions,
create publications, or substitute a date-matched/current publication for an
explicit historical identity manifest.
"""
from collections import Counter

VERSION = 'FEP_E5_CANONICAL_IDENTITY_AVAILABILITY_V1'
CONFLICT = 'CONTRACT_CONFLICT_CANONICAL_PUBLICATION_BINDING'
DEPENDENCIES = ('publication', 'accepted_head', 'algorithm_contract', 'parameter_contract',
                'calendar', 'universe', 'adjustment_basis', 'feature_contract', 'membership',
                'state_event_revision', 'enrichment_revision')


def readback_population(pg, rows, exact_authorities):
    """Return every source identity, even when all authority mappings are absent.

    Caller supplies immutable accepted authority bindings. Candidate counts by
    date are diagnostics only and never provide a mapping or fallback.
    """
    ids = [r['observation_id'] for r in rows]
    if len(ids) != len(set(ids)) or set(exact_authorities) - set(ids):
        raise ValueError('CANONICAL_POPULATION_IDENTITY_CONFLICT')
    result = []
    for row in rows:
        record = dict(source_observation_id=row['observation_id'], entity_id=row['entity_id'],
                      trade_date=row['trade_date'], source_evidence_digest=row['original_e2_row_digest'],
                      canonical_identity=None, reasons=[], prediction_evidence='HISTORICAL_SIMULATION',
                      FIRST_OBSERVED=False, REAL_OOS=False)
        record['accepted_publications_on_date_diagnostic_only'] = None
        record['reasons'].append('V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED')
        record['status'] = CONFLICT
        result.append(record)
    counts = Counter(x['status'] for x in result)
    return dict(contract_version=VERSION, status=CONFLICT if counts[CONFLICT] else 'REQUIRES_FURTHER_VALIDATION',
                logical_observations=len(rows), affected_observations=counts[CONFLICT], exact_authority_bindings_supplied=len(exact_authorities),
                population=result, no_fallback=True, no_inferred_identity=True, no_database_writes=True,
                canonical_integration_accepted=False)


def inventory(pg):
    """Return no legacy FEP inventory until fixed v4 tables are provisioned."""
    return {}
