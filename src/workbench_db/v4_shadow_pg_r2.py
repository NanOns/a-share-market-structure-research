"""Compatibility API for fixed-v4 immutable Shadow readback exports."""
from contextlib import contextmanager

from .v4_snapshot_pg_r2 import digest


def build_readback(root, records, *, environment, evidence_origin):
    from .v4_shadow_pg_r3 import build_readback as build_r3
    return build_r3(root, records, environment=environment, evidence_origin=evidence_origin)


@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') != 'V4_PG_SHADOW_READBACK_R3':
        raise ValueError('PG_SHADOW_R3_FIXED_V4_BINDING_REQUIRED')
    from .v4_shadow_pg_r3 import read as read_r3
    with read_r3(descriptor) as reader:
        yield reader
