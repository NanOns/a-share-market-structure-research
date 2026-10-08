"""R4.1 real acquisition and immutable entry freeze; no owner promotion."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.market_source_acquisition import acquire, digest, now, official_sessions, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/source_acquisition_r4_20261009')
    args = parser.parse_args()
    folder = args.output
    entry = folder / '00_R4_ENTRY_HEAD_AND_EXISTING_SOURCE_CONTRACT.json'
    dates = ['2026-09-28', '2026-09-29', '2026-09-30', '2026-10-08']
    if not entry.exists():
        paths = ['config/v4_joint_release_authority_v1.json', 'data/v4/V4_DATA_ACCEPTED_HEAD.json',
                 'config/v4_daily_source_freeze_v2.json', 'config/baostock_supplemental_contract_v1.json']
        write(entry, dict(stage_contract='R4.1', requested_at=now(), dates=dates,
            head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
            preserved={p: digest((ROOT/p).read_bytes()) for p in paths},
            phase0='DEGRADED_PASS', acceptance='ENTRY_FROZEN', next_stage='LIVE_SOURCE_CAPTURE',
            official_sessions=[d for d in official_sessions(ROOT) if '2026-09-24' <= d <= '2026-10-08']))
    http = folder / 'HTTP_REQUESTS.json'
    requests = json.loads(http.read_bytes()) if http.exists() else []
    def audit(event, params):
        if event == 'urllib.Request':
            requests.append(dict(url=params[0], method=params[3], requested_at=now()))
            write(http, requests)
    sys.addaudithook(audit)
    with (ROOT / 'docs/evidence/three_day_repair_r1_20261008/THREE_DAY_SOURCE_DIFF.csv').open(encoding='utf-8-sig') as f:
        codes = sorted({r['symbol'].lower() for r in csv.DictReader(f) if r['reason']=='UNSUPPORTED_OR_UNPROVED_ADJUSTMENT'})
    result = acquire(ROOT, dates, folder / 'capture', codes)
    write(folder / '01_TDX_LOCAL_OFFICIAL_BAOSTOCK_REAL_REQUEST_LEDGER.json', dict(
        status=result['status'], acquisition='capture/acquisition.json', http_request_count=len(requests),
        http_requests=requests, session_attempts=result['session_attempts'], query_receipts=result['queries']))
    ledger=json.loads((ROOT/'reports/v4_baostock/request_ledger.json').read_bytes())
    write(folder/'BAOSTOCK_SHARED_BUDGET_READBACK.json',ledger)
    print(json.dumps(dict(status=result['status'], http_requests=len(requests), queries=len(result['queries']),
                          local_files=len(result['local']))))
    return 0 if result['status']=='CAPTURE_OBSERVATIONS_READY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
