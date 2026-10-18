"""FEP persistence is disabled until its fixed v4 table contract is delivered."""


STORAGE_NOT_READY = 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'


def apply(pg, root, *, bootstrap=False):
    raise RuntimeError(STORAGE_NOT_READY)


def validate_inventory(pg):
    return dict(status='STORAGE_NOT_READY', reason=STORAGE_NOT_READY,
                tables=[], guarded=[], mutable=[])
