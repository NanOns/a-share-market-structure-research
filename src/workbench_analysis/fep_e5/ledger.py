"""Retired payload-ledger adapter; canonical FEP persistence lives in v4 tables.

The former implementation depended on a module-owned ``fep_e5_engineering``
schema with an incompatible payload layout. It must not read, install, or write
that storage. Use the typed canonical repository and fixed v4 contracts instead.
"""

ERROR = 'V4_FEP_CANONICAL_LEDGER_REQUIRED'


class Ledger:
    """Compatibility shell that fails before touching PostgreSQL."""

    def __init__(self, pg, *, historical_fixture=False):
        self.pg = pg
        self.historical_fixture = historical_fixture

    @staticmethod
    def identity_columns(payload):
        return dict(scope=payload['scope_id'], observation_scope=payload['observation_scope'],
                    target=payload['target_id'], horizon=payload['horizon'],
                    feature=payload['feature_contract_id'], namespace=payload['namespace'])

    def _retired(self, *args, **kwargs):
        raise RuntimeError(ERROR)

    fixture_guard = _retired
    install = _retired
    get = _retired
    rows = _retired
    put = _retired
    register_model = _retired
    plan = _retired
    bind = _retired
    grant = _retired
    cas = _retired
    allowed = _retired
    rollback = _retired
    inventory = _retired
