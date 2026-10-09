import struct,zipfile
from pathlib import Path
import pytest
from workbench_analysis.tdx_latest_daily_source_v2 import extract_target_session_bars
from workbench_analysis.tdx_local_daily_fallback_v1 import fallback
from workbench_analysis.tdx_official_daily_source import sha256_file


def fixture(tmp_path):
    native=tmp_path/'readonly/vipdoc/sh/lday/sh600000.day';native.parent.mkdir(parents=True)
    record=lambda d:struct.pack('<IIIIIfII',d,100,130,90,120,1000.,10,0)
    native.write_bytes(record(20261008)+record(20261009))
    package=tmp_path/'official.zip'
    with zipfile.ZipFile(package,'w') as archive:
        archive.writestr('sh/lday/sh600000.day',record(20261009))
        archive.writestr('sz/lday/sz000001.day',record(20261009))
    latest=dict(provider_package_date='2026-10-09',observed_at='2026-10-09T10:40:00+00:00',
                download=dict(path=str(package),bytes=package.stat().st_size,sha256=sha256_file(package)))
    out=tmp_path/'artifacts';extracted=extract_target_session_bars(latest,'2026-10-08',snapshot_root=out,tdx_root=tmp_path/'readonly')
    row=dict(date='2026-10-08',code='sh.600000',tradestatus='1',open='1',high='1.3',low='.9',close='1.2',volume='10',amount='1000')
    return latest,extracted,row,out,native


def test_real_bytes_fallback_preserves_both_readonly_inputs(tmp_path):
    latest,extracted,row,out,native=fixture(tmp_path)
    before=(native.read_bytes(),Path(latest['download']['path']).read_bytes())
    effective,result,receipt=fallback(latest,extracted,'2026-10-08',[row],snapshot_root=out,tdx_root=tmp_path/'readonly')
    assert result['row_count']==1 and result['target_bars'][0]['close']==1.2
    assert effective['download']['sha256']!=latest['download']['sha256'] and receipt
    assert (native.read_bytes(),Path(latest['download']['path']).read_bytes())==before
    again=fallback(latest,extracted,'2026-10-08',[row],snapshot_root=out,tdx_root=tmp_path/'readonly')
    assert result['artifact']==again[1]['artifact']


def test_provider_mismatch_blocks_fallback(tmp_path):
    latest,extracted,row,out,native=fixture(tmp_path);row['close']='1.21'
    with pytest.raises(ValueError,match='OHLCV_MISMATCH'):
        fallback(latest,extracted,'2026-10-08',[row],snapshot_root=out,tdx_root=tmp_path/'readonly')
