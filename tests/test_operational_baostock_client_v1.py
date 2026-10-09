import json
from types import SimpleNamespace
import pytest
from workbench_analysis.baostock_supplemental import RequestBudget,BaoStockError
from workbench_analysis import operational_baostock_client_v1 as runtime


class SDK:
    def login(self):return SimpleNamespace(error_code='0',error_msg='')
    def logout(self):return SimpleNamespace(error_code='0',error_msg='')


def test_owned_dead_process_marker_recovers_with_budget_preserved(tmp_path,monkeypatch):
    ledger=tmp_path/'reports/v4_baostock/request_ledger.json';ledger.parent.mkdir(parents=True)
    marker=ledger.with_suffix('.json.session.lock')
    marker.write_text(json.dumps(dict(contract_id='DAILY_SDK_SESSION_LOCK_V1',pid=123)))
    monkeypatch.setattr(runtime,'alive',lambda pid:False)
    budget=RequestBudget(ledger)
    with runtime.BaoStockClient(budget,sdk=SDK(),auth_mode='PUBLIC_ANONYMOUS',allow_unaccepted_runtime_smoke=True):
        assert json.loads(marker.read_bytes())['pid']>0
    assert not marker.exists()
    assert json.loads(ledger.read_bytes())['by_shanghai_date'][budget.day]['count']==2


def test_unowned_legacy_marker_is_not_deleted(tmp_path):
    ledger=tmp_path/'reports/v4_baostock/request_ledger.json';ledger.parent.mkdir(parents=True)
    marker=ledger.with_suffix('.json.session.lock');marker.write_bytes(b'')
    with pytest.raises(BaoStockError,match='UNOWNED_LEGACY'):
        with runtime.BaoStockClient(RequestBudget(ledger),sdk=SDK(),auth_mode='PUBLIC_ANONYMOUS',allow_unaccepted_runtime_smoke=True):pass
    assert marker.is_file() and marker.read_bytes()==b''
