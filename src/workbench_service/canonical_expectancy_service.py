"""Explicit read-only canonical API; immutable context and current scoped permission.

The historical implementation read from a separate ``fep`` schema. Until a
versioned fixed-table migration under ``market_research.v4`` is available, this
API must not query that retired namespace.
"""

STORAGE_NOT_READY = 'V4_SINGLE_SCHEMA_FEP_STORAGE_MIGRATION_REQUIRED'

class CanonicalExpectancyReadAPI:
    def __init__(self, pg):self.pg=pg
    def bootstrap(self, slot):
        return dict(status='STORAGE_NOT_READY', reason=STORAGE_NOT_READY,
                    missing_inputs=['V4_FIXED_FEP_TABLE_MIGRATION'], production=False)
    def projection(self, slot, token, *, diagnostic=False, mode='HISTORICAL_AS_OF'):
        return dict(status='STORAGE_NOT_READY', reason=STORAGE_NOT_READY,
                    missing_inputs=['V4_FIXED_FEP_TABLE_MIGRATION'], diagnostic=False,
                    MODEL_DISPLAY='UNGRANTED', PRIORITY_USE='UNGRANTED', production=False)
    def priority(self):return dict(status='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE',v2_active=False,REAL_PRIORITY_SHADOW='NOT_GRANTED')
