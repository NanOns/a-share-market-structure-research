"""Simulation-only candidate consumer; activation requires independent acceptance.

Queue V2 identity and fencing stay frozen. Evaluation contract is Forward 1.2.
No existing accepted dependency binding selects this worker.
"""
from types import FunctionType
from scripts.v4_16_settlement_worker_v2 import DurableSettlementWorker as HistoricalWorker
from workbench_analysis.v4_15_forward_r2 import SettlementRuntime

_old = HistoricalWorker.deliver
_candidate_deliver = FunctionType(_old.__code__, dict(_old.__globals__, SettlementRuntime=SettlementRuntime),
                                _old.__name__, _old.__defaults__, _old.__closure__)

class DurableSettlementWorker(HistoricalWorker):
    def deliver(self, *args, **kwargs):
        if not self.db.controller.simulation:
            raise ValueError('FORWARD_R2_INDEPENDENT_ACCEPTANCE_REQUIRED')
        return _candidate_deliver(self, *args, **kwargs)
