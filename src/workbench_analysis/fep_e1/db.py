"""Fixed v4 FEP storage inventory; migration is owned by the central runner."""

STORAGE_NOT_READY = 'V4_FEP_FIXED_SCHEMA_MIGRATION_REQUIRED'
MIGRATION_VERSION = 'V4_FEP_FIXED_SCHEMA_STORAGE_R1'

TABLES = (
    'acceptance_receipts', 'activations', 'contracts', 'dataset_eligibility_ledger',
    'dataset_fold_cutoffs', 'dataset_fold_label_selection', 'dataset_rows', 'datasets',
    'deployment_change_receipts', 'deployment_heads', 'feature_values', 'field_registry',
    'field_scope', 'label_revisions', 'label_source_bindings', 'model_set_members',
    'model_sets', 'models', 'observation_revisions', 'observations', 'permission_keys',
    'prediction_runs', 'prediction_slots', 'predictions', 'priority_projection',
    'priority_projection_grants', 'reconstruction_authorities', 'reports', 'scopes',
    'signal_contract_registry', 'slot_model_bindings', 'slot_receipts', 'snapshots',
    'targets', 'training_runs',
)


def apply(pg, root, *, bootstrap=False):
    """Verify installation only; never execute legacy migrations or create a schema."""
    row = pg.execute(
        'SELECT checksum_sha256 FROM v4.schema_migrations WHERE version=%s',
        (MIGRATION_VERSION,),
    ).fetchone()
    if not row:
        raise RuntimeError(STORAGE_NOT_READY)
    return [dict(version=MIGRATION_VERSION, sha256=row[0].strip(), status='ALREADY_APPLIED')]


def validate_inventory(pg):
    present = {r[0] for r in pg.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='v4' AND tablename=ANY(%s)",
        (list(TABLES),),
    ).fetchall()}
    missing = set(TABLES) - present
    if missing:
        raise ValueError('FEP_FIXED_V4_TABLES_MISSING:' + ','.join(sorted(missing)))

    immutable = set(TABLES) - {'deployment_heads'}
    guards = {table for table, has_guard in pg.execute(
        """SELECT c.relname, bool_or((t.tgtype & 24)=24 AND t.tgenabled='O')
           FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
           JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='v4' AND c.relname=ANY(%s) AND c.relname<>'deployment_heads' AND NOT t.tgisinternal
           GROUP BY c.relname""",
        (list(TABLES),),
    ).fetchall() if has_guard}
    if guards != immutable:
        raise ValueError('FEP_FIXED_V4_APPEND_ONLY_GUARD_INVENTORY')
    controlled_head = pg.execute(
        """SELECT EXISTS(
             SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
             JOIN pg_namespace n ON n.oid=c.relnamespace
             WHERE n.nspname='v4' AND c.relname='deployment_heads'
               AND t.tgname='controlled_head' AND t.tgenabled='O' AND NOT t.tgisinternal)"""
    ).fetchone()[0]
    if not controlled_head:
        raise ValueError('FEP_FIXED_V4_HEAD_CAS_GUARD_MISSING')
    return dict(schema='v4', tables=sorted(present), guarded=sorted(guards), mutable=['deployment_heads'])
