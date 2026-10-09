"""Isolated controlled-clock source cache tests; no real provider calls."""
from datetime import datetime
import pytest
import workbench_analysis.operational_daily_executor_v1 as module


@pytest.mark.parametrize('downloaded,expected',['2026-10-09T17:45:00+08:00,2'.split(','),
                                              '2026-10-09T18:36:00+08:00,1'.split(',')])
def test_missing_target_refreshes_pre_gate_capture_once(tmp_path,monkeypatch,downloaded,expected):
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.fromisoformat('2026-10-09T18:40:00+08:00').astimezone(tz)
    calls=[]
    def capture(**kwargs):
        calls.append(kwargs.get('force_refresh',False))
        return dict(download={'path':'fixture'},provider_package_date='2026-10-09',
                    downloaded_at=downloaded,observed_at=downloaded)
    monkeypatch.setattr(module,'datetime',Clock)
    monkeypatch.setattr(module,'capture_latest_tdx_package',capture)
    monkeypatch.setattr(module,'extract_target_session_bars',lambda *a,**k:dict(status='WAIT_TDX_TARGET_BARS'))
    def runtime(*a,**k):raise RuntimeError('STOP_BEFORE_ANY_SDK_CALL')
    monkeypatch.setattr(module,'load_runtime_acceptance_manifest',runtime)
    with pytest.raises(RuntimeError,match='STOP_BEFORE_ANY_SDK_CALL'):
        module.execute_sources(tmp_path,'2026-10-09','CATCH_UP',capture_only=True)
    assert len(calls)==int(expected)
    assert calls==([False,True] if int(expected)==2 else [False])
