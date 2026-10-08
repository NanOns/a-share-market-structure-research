"""Append-only R4.1 correction: exercise the normal source entry and inspect bars."""
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.market_source_acquisition import read_day_bytes, is_stock_code, write, now
from workbench_analysis.tdx_official_daily_source import capture_tdx_official_daily_package


def main():
    out = ROOT / 'docs/evidence/source_acquisition_r4_20261009/tdx_download_correction'
    dates = ['2026-09-28', '2026-09-29', '2026-09-30', '2026-10-08']
    write(out / 'STAGE_ENTRY.json', dict(contract='TDX_EXISTING_R3_DOWNLOADER_ADAPTER_V1',
          upgrade_document='R4.1', phase0='DEGRADED_PASS', observed_at=now(),
          scope='Correct the erroneous unavailable conclusion and verify four-session official RAW coverage',
          next_stage='SOURCE_COORDINATE_AND_OWNER_ADMISSION'))
    receipt = capture_tdx_official_daily_package(target_date=dates[-1],
          snapshot_root=ROOT / 'data/v4/source_snapshots')
    rows = []
    counts = {day: Counter() for day in dates}
    with zipfile.ZipFile(receipt['download']['path']) as archive:
        for name in archive.namelist():
            parts = name.lower().replace('\\', '/').split('/')
            leaf = parts[-1]
            if not leaf.endswith('.day'):
                continue
            market = next((p for p in parts if p in ('sh', 'sz', 'bj')), None)
            code = f'{market}.{leaf[-10:-4]}'
            if not market or not is_stock_code(code):
                continue
            bars, last = read_day_bytes(archive.read(name), dates)
            for day, bar in bars.items():
                counts[day][market] += 1
                rows.append(dict(trade_date=day, source_security_key=code,
                                 archive_entry=name, last_record_date=last, **bar))
    write(out / 'OFFICIAL_FOUR_SESSION_RAW_BARS.json', dict(contract='TDX_OFFICIAL_RAW_FOUR_SESSION_OBSERVATION_V1',
          package_sha256=receipt['download']['sha256'], knowledge_lineage='RECONSTRUCTED_CORRECTED',
          AS_RECORDED=False, production_admission=False, rows=rows))
    write(out / 'CORRECTION_RECEIPT.json', dict(status='PASS_DOWNLOAD_AND_FOUR_SESSION_RAW_READ',
          observed_at=now(), supersedes='R4-A01 claim that official TDX package acquisition is blocked',
          cause='Daily source entry omitted existing R3 static-cookie challenge downloader',
          source_receipt=receipt, counts={d: dict(counts[d], total=sum(counts[d].values())) for d in dates},
          tdx_root_write_count=0, production_heads_changed=False,
          acceptance='DOWNLOAD_AND_RAW_COVERAGE_ONLY', next_stage='SOURCE_COORDINATE_AND_OWNER_ADMISSION'))
    print(json.dumps({d: dict(counts[d], total=sum(counts[d].values())) for d in dates}))


if __name__ == '__main__':
    main()
