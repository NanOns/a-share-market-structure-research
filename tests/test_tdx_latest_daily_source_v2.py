import struct,zipfile
from pathlib import Path
import pytest
from workbench_analysis.tdx_latest_daily_source_v2 import extract_target_session_bars
from workbench_analysis.tdx_official_daily_source import sha256_file


def package(tmp_path):
    p=tmp_path/'package.zip'
    with zipfile.ZipFile(p,'w') as z:
        for market in ['sh','sz']:
            z.writestr(market+'/lday/'+market+('600000' if market=='sh' else '000001')+'.day',b''.join(
                struct.pack('<IIIIIfII',d,100,130,90,120,1000.,10,0)
                for d in [20260930,20261008,20261009]))
    return dict(provider_package_date='2026-10-09',observed_at='2026-10-09T10:40:00+00:00',
                download=dict(path=str(p),bytes=p.stat().st_size,sha256=sha256_file(p)))


def test_latest_contains_actual_older_session(tmp_path):
    p=package(tmp_path)
    a=extract_target_session_bars(p,'2026-10-08',snapshot_root=tmp_path/'frozen')
    b=extract_target_session_bars(p,'2026-10-08',snapshot_root=tmp_path/'frozen')
    assert a['row_count']==2 and a['reconstruction_from_later_snapshot']
    assert a['artifact']==b['artifact']
    assert a['source_available_at']==p['observed_at']
    assert a['PIT_ELIGIBLE'] is False


def test_absent_date_not_inferred_from_package_date(tmp_path):
    a=extract_target_session_bars(package(tmp_path),'2026-10-07',snapshot_root=tmp_path/'frozen')
    assert a['status']=='WAIT_TDX_TARGET_BARS' and not a['target_bars']


def test_tamper_fails(tmp_path):
    p=package(tmp_path);Path(p['download']['path']).write_bytes(b'html')
    with pytest.raises(ValueError,match='BINDING'):
        extract_target_session_bars(p,'2026-10-08',snapshot_root=tmp_path/'frozen')
