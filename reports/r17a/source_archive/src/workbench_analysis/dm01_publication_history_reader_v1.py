"""Read-only replay of frozen business publication validators after Data promotion.

The accepted validator bytes remain immutable. Only their filesystem view of the
audited 9/24 movable namespace resolves to its explicit exact-byte archive. This
adapter never invokes promotion and grants no current business-stage acceptance.
"""
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from .dm01_accepted_chain_v1 import (
    HistoricalProjectView,validate_head_v2,load,binding,HEAD_PATH,HEAD_CONTRACT)

_LOCK=RLock()

class PublicationHistoryView(HistoricalProjectView):
    def __fspath__(self):return str(self.root)

@contextmanager
def _frozen_readers():
    from scripts import promote_v4_09_accepted_head as v9
    from scripts import validate_v4_10_promotion_r1 as v10
    root=Path(v10.ROOT)
    current=load(root,binding(root,HEAD_PATH))
    if current.get('contract_id')==HEAD_CONTRACT:validate_head_v2(root,current)
    with _LOCK:
        before=[(module,module.ROOT) for module in (v9,v10)]
        try:
            for module,original in before:module.ROOT=PublicationHistoryView(original)
            yield root,v9,v10,current
        finally:
            for module,original in before:module.ROOT=original

def _scope(result,root,current):
    return dict(result,validation_scope='ACCEPTED_PUBLICATION_HISTORY_ONLY',
        historical_data_head_resolution='EXPLICIT_EXACT_20260924_ORIGINAL_BYTE_ARCHIVE',
        current_data_head=binding(root,HEAD_PATH),current_data_head_date=current['accepted_trade_date'],
        business_reacceptance_performed=False,production_authorization=False)

def validate_v4_10_history(candidate=None):
    with _frozen_readers() as (root,v9,v10,current):
        return _scope(v10.validate(candidate),root,current)

def validate_v4_09_history():
    with _frozen_readers() as (root,v9,v10,current):
        return _scope(v9.validate(),root,current)

def validate_v4_09_history_head(candidate,global_head,receipt):
    with _frozen_readers() as (root,v9,v10,current):
        return _scope(v9.validate_head(candidate,global_head,receipt),root,current)
