"""Read-only canonical authority availability gate; never synthesize identities.

This gate diagnoses necessary upstream authority. It does not accept predictions,
create publications, or substitute a date-matched/current publication for an
explicit historical identity manifest.
"""
from collections import Counter
from psycopg import sql

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
        record['accepted_publications_on_date_diagnostic_only'] = pg.execute(
            "select count(*) from v4.publications where trade_date=%s and status='ACCEPTED'",
            (row['trade_date'],)).fetchone()[0]
        mapping = exact_authorities.get(row['observation_id'])
        if mapping is None:
            record['reasons'].append('MISSING_EXACT_HISTORICAL_AUTHORITY_MANIFEST')
        else:
            # Digests from the previous prototype are not publication identities.
            if mapping.get('publication_id') in (row['original_e2_row_digest'], row['observation_id']):
                record['reasons'].append('DIGEST_IS_NOT_CANONICAL_PUBLICATION_AUTHORITY')
            if mapping.get('source_evidence_digest') != row['original_e2_row_digest']:
                record['reasons'].append('SOURCE_EVIDENCE_BINDING_MISMATCH')
            deps = mapping.get('dependency_manifest', {})
            if any(not deps.get(k) or deps[k] in ('CURRENT', 'LATEST', 'TODAY', 'UNKNOWN') for k in DEPENDENCIES):
                record['reasons'].append('HISTORICAL_DEPENDENCIES_MISSING_OR_INFERRED')
            if deps.get('publication') != mapping.get('publication_id'):
                record['reasons'].append('MANIFEST_PUBLICATION_MISMATCH')
            chain = pg.execute("""select p.status,p.trade_date::text,p.model_namespace_id,
                p.accepted_at,r.feature_cutoff,o.slot_deadline,s.namespace_id,o.entity_id,
                o.trade_date::text,r.dependency_manifest,r.evidence_origin,r.execution_mode,
                x.feature_contract_id,x.feature_digest,x.quality_digest
                from fep.observations o join fep.scopes s using(scope_id)
                join fep.observation_revisions r using(observation_id)
                join v4.publications p using(publication_id)
                join fep.snapshots x on x.observation_id=o.observation_id and x.observation_revision=r.revision
                where o.observation_id=%s and r.revision=%s and x.snapshot_id=%s and p.publication_id=%s""",
                (mapping.get('observation_id'), mapping.get('observation_revision'),
                 mapping.get('snapshot_id'), mapping.get('publication_id'))).fetchone()
            if chain is None:
                record['reasons'].append('EXACT_CANONICAL_CHAIN_NOT_FOUND')
            else:
                status, day, ns, accepted, cutoff, deadline, scope_ns, entity, obs_day, manifest, origin, mode, feature, fd, qd = chain
                if (status != 'ACCEPTED' or day != row['trade_date'] or obs_day != day or ns != scope_ns
                        or entity != row['entity_id'] or accepted > cutoff or cutoff > deadline):
                    record['reasons'].append('CANONICAL_PUBLICATION_OBSERVATION_MISMATCH')
                if manifest != deps or feature != deps.get('feature_contract') or fd != mapping.get('feature_digest') or qd != mapping.get('quality_digest'):
                    record['reasons'].append('CANONICAL_SNAPSHOT_DEPENDENCY_BINDING_MISMATCH')
                if origin not in ('RECONSTRUCTED_ASOF', 'RECONSTRUCTED_CORRECTED') or mode != 'REPLAY':
                    record['reasons'].append('HISTORICAL_EVIDENCE_ORIGIN_UPGRADE_FORBIDDEN')
        record['status'] = CONFLICT if record['reasons'] else 'AUTHORITY_PRESENT_REQUIRES_CANONICAL_VALIDATION'
        result.append(record)
    counts = Counter(x['status'] for x in result)
    return dict(contract_version=VERSION, status=CONFLICT if counts[CONFLICT] else 'REQUIRES_FURTHER_VALIDATION',
                logical_observations=len(rows), affected_observations=counts[CONFLICT], exact_authority_bindings_supplied=len(exact_authorities),
                population=result, no_fallback=True, no_inferred_identity=True, no_database_writes=True,
                canonical_integration_accepted=False)


def inventory(pg):
    tables = pg.execute("select tablename from pg_tables where schemaname='fep' order by tablename").fetchall()
    return {name: pg.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(name))).fetchone()[0]
            for name, in tables}
