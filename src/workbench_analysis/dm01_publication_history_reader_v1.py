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
    def __truediv__(self,path):
        from .historical_stage_governance_r17 import STAGE,resolve,registry
        if str(path).replace('\\','/')==STAGE:
            return resolve(self.root,dict(path=STAGE,sha256='f7607601de402f2b2bdada84dffdefbacad7f9f66e252c57dfdf045060e90e99'))
        if str(path).replace('\\','/')=='tests/v4_09/test_stock_prewatch.py':
            ref=next(r['original_namespace'] for r in registry(self.root)['source_archives'] if r['original_namespace']['path']==str(path))
            return resolve(self.root,ref,source=True)
        return super().__truediv__(path)

@contextmanager
def _frozen_readers():
    from scripts import promote_v4_09_accepted_head as v9
    from scripts import validate_v4_10_promotion_r1 as v10
    root=Path(v10.ROOT)
    from .historical_stage_governance_r17 import current_state
    current_state(root)
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
    from .historical_stage_governance_r17 import current_state
    return dict(result,current_accepted_state=current_state(root),validation_scope='ACCEPTED_PUBLICATION_HISTORY_ONLY',
        historical_data_head_resolution='EXPLICIT_EXACT_HISTORICAL_ORIGINAL_BYTE_ARCHIVE',
        current_data_head=binding(root,HEAD_PATH),current_data_head_date=current['accepted_trade_date'],
        business_reacceptance_performed=False,production_authorization=False)

def validate_v4_10_history(candidate=None):
    from .dm01_publication_history_reader_v3 import validate_v4_10_history as upgraded
    return upgraded(candidate,project_root=Path(__file__).resolve().parents[2])

def validate_v4_09_history():
    from .dm01_publication_history_reader_v3 import validate_v4_09_history as upgraded
    return upgraded(project_root=Path(__file__).resolve().parents[2])

def validate_v4_09_history_head(candidate,global_head,receipt):
    from .dm01_publication_history_reader_v3 import validate_v4_09_history_head as upgraded
    return upgraded(candidate,global_head,receipt,project_root=Path(__file__).resolve().parents[2])
