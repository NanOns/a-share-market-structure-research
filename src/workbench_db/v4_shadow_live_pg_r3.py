"""Retired path-derived Shadow writer compatibility guard.

The active V4 Shadow readback writer is ``v4_shadow_pg_r3`` and stores its
versioned records in the fixed ``v4`` schema. This module remains only for
contracts that still import the old native-engine marker/helper.
"""
from pathlib import Path
import hashlib
import os

CONTRACT = 'R4_R3_NATIVE_SHADOW_LIVE_STORAGE_V1'
MIGRATION = 'migrations/v4_shadow_live_pg_r3.sql'
ROOT = Path(__file__).resolve().parents[2]


def canonical(value):
    import json
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class NativeShadowDatabase:
    engine = 'postgresql'
    artifact_prefix = 'pg-shadow:'

    def __init__(self, controller, path):
        # Preserve the import surface but never open a connection or create a
        # second, path-derived Shadow namespace.
        raise RuntimeError('V4_SINGLE_SCHEMA_SHADOW_STORAGE_MIGRATION_REQUIRED')


def native_mode():
    return 'V4_NATIVE_PG_DSN' in os.environ or os.environ.get('R4_NATIVE_ISOLATION') == '1'


def qualify_simulation_dependencies(root, deps, ref):
    """Only explicit simulation fixtures may qualify current native source bytes."""
    require(native_mode() and os.environ.get('R4_NATIVE_ISOLATION') == '1',
            'EXPLICIT_NATIVE_SHADOW_SIMULATION_REQUIRED')
    require(Path(root).resolve() == ROOT, 'EXACT_ISOLATED_SHADOW_SIMULATION_ROOT_REQUIRED')
    old_storage, old_migration = deps['storage'], deps['migration']
    deps['storage'] = ref('config/v4_shadow_live_pg_storage_r3.json')
    deps['migration'] = ref(MIGRATION)
    deps['bindings'] = [deps['storage'] if row == old_storage else
                        deps['migration'] if row == old_migration else ref(row['path'])
                        for row in deps['bindings']]
    deps['bindings'].append(ref('src/workbench_db/v4_shadow_live_pg_r3.py'))
    deps['native_engineering_storage_qualification'] = dict(
        contract=CONTRACT, external_acceptance='NOT_GRANTED',
        production=False, real_maturity=False)
