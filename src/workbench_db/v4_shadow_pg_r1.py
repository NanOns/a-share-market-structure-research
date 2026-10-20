"""Compatibility API for fixed-v4 immutable Shadow readback exports."""
from contextlib import contextmanager


class ReadTransaction:
    def __init__(self, pg):
        self.pg = pg

    def execute(self, query, params=()):
        return self.pg.execute(query.replace('?', '%s'), params)


def build_readback_r1(root, records, *, environment, evidence_origin):
    """Historical public entrypoint; writes through the current fixed-v4 contract."""
    from .v4_shadow_pg_r3 import build_readback
    return build_readback(root, records, environment=environment, evidence_origin=evidence_origin)


def build_readback(root, records, *, environment, evidence_origin):
    return build_readback_r1(root, records, environment=environment, evidence_origin=evidence_origin)


@contextmanager
def read(descriptor):
    if descriptor.get('contract_id') != 'V4_PG_SHADOW_READBACK_R3':
        raise ValueError('PG_SHADOW_R3_FIXED_V4_BINDING_REQUIRED')
    from .v4_shadow_pg_r3 import read as read_r3
    with read_r3(descriptor) as reader:
        yield reader
