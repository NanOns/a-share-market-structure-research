"""Historical FEP reconstruction helpers with PostgreSQL access disabled.

The old implementation persisted to a standalone ``fep`` schema. Database
operations remain unavailable until the fixed, versioned ``v4`` table
migration and its source contract are supplied.
"""

from datetime import datetime, timezone

from workbench_analysis.fep_e1.contracts import digest

VERSION = 'FEP_E5_CANONICAL_RECONSTRUCTION_V1'
SCOPE = 'FEP_STOCK_ENTRY_CORE'
FEATURE = 'FEP_E2_HISTORICAL_CORE_FEATURE_V1'
TARGET = 'ABS_RETURN_N:T1'
NS = 'FEP_E5_RECONSTRUCTION_ONLY_V1'
AUTH_CONTRACT = 'FEP_E5_HISTORICAL_RECONSTRUCTION_AUTHORITY_V1'
STORAGE_NOT_READY = 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'
OUTPUT_FIELDS = ('axes','state','OOD_state','quality_state','support_state','backoff_level','backoff_trace',
    'global_OOD_OK','raw_quantiles','coherent_quantiles','coherence_state','threshold_state','baseline_estimand',
    'calibration_state','projection_state','prediction_evidence','evidence_origin','synthetic_only','FIRST_OBSERVED',
    'REAL_OOS','PROMOTION_EVIDENCE','historical_model_applied_after_observation')


def _require_fixed_v4_fep_storage():
    raise RuntimeError(STORAGE_NOT_READY)


def now():
    return datetime.now(timezone.utc).isoformat()


def apply(pg, root, paths):
    _require_fixed_v4_fep_storage()


def contract(pg, name, body, *, family=None):
    _require_fixed_v4_fep_storage()


def authority_entries(rows, frozen_manifest):
    """Pure historical manifest normalization; it never reads or writes PG."""
    entries=[]
    for row in rows:
        values=row['model_features']; envelopes=row['feature_snapshot']['core_envelopes']
        fields={k:dict(value=v,quality=envelopes[k]['quality_state'],source_digest=envelopes[k]['input_digest'],
                       reason=envelopes[k].get('unknown_reason')) for k,v in values.items()}
        fd=digest(values);qd=digest({k:dict(quality=v['quality'],source_digest=v['source_digest']) for k,v in fields.items()})
        snap='FEP_CANONICAL_SNAPSHOT:'+digest([row['observation_id'],FEATURE,fd,qd])
        manifest=dict(frozen_manifest,source_observation_id=row['observation_id'],entity_id=row['entity_id'],
            source_row_digest=row['original_e2_row_digest'],feature_contract=FEATURE,feature_digest=fd,quality_digest=qd,
            feature_entries=fields,snapshot_id=snap,prediction_input_digest=digest([snap,fd,qd]),
            max_feature_source_trade_date=row['feature_snapshot']['max_feature_source_trade_date'])
        if manifest['max_feature_source_trade_date']>row['trade_date']:
            raise ValueError('FUTURE_FEATURE_FORBIDDEN')
        entries.append(dict(authority_id='FEP_RECONSTRUCTION_AUTHORITY:'+digest(manifest),scope_id=SCOPE,namespace_id=NS,
            trade_date=row['trade_date'],evidence_origin='RECONSTRUCTED_CORRECTED',feature_contract_id=FEATURE,
            source_manifest=manifest,source_manifest_digest=digest(manifest),accepted_head_identity=frozen_manifest['accepted_head']))
    return entries


def seed_identity(pg, rows, entries, model_catalog):
    _require_fixed_v4_fep_storage()


def head(pg):
    _require_fixed_v4_fep_storage()


def cas(pg, grant, action, request, *, expected=None, prior=None):
    _require_fixed_v4_fep_storage()


def plan(pg, prior_record, mapping, model, cutoff, activation):
    _require_fixed_v4_fep_storage()


def accept(pg, prior_record, mapping, model, cutoff, activation, *, fail_before_receipt=False):
    _require_fixed_v4_fep_storage()


def inventory(pg):
    return {}
