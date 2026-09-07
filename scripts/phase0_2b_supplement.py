"""Bounded supplemental evidence; carries all earlier request budgets forward."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from validation.phase0_2b import FrozenRun, EvidenceClient, read_frozen

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/phase0_2b'

if __name__ == '__main__':
    if '--network-authorized' not in sys.argv:
        raise SystemExit('Explicit network authorization required')
    prior = []
    for path in sorted(BASE.glob('run_*')):
        if not (path / 'FROZEN.json').exists():
            raise SystemExit('Unfrozen earlier run requires review before any new requests')
        if (path / 'FROZEN.json').exists() and (path / 'network_audit.json').exists():
            prior.extend(read_frozen(path, 'network_audit.json'))
    run = FrozenRun(BASE, Path('D:/new_tdx'))
    client = EvidenceClient(run, prior)
    for code in ('600519', '000651'):
        params = {'reportName': 'RPT_SHAREBONUS_DET', 'columns': 'ALL',
                  'filter': f'(SECURITY_CODE="{code}")', 'pageNumber': '1', 'pageSize': '100',
                  'sortColumns': 'EX_DIVIDEND_DATE', 'sortTypes': '-1', 'source': 'WEB', 'client': 'WEB'}
        payload = client.get('EASTMONEY', 'https://datacenter-web.eastmoney.com/api/data/v1/get', params)
        run.put(f'corporate_{code}.json', payload)
        print(code, bool(payload), dict(client.budget.count), flush=True)
    run.put('network_audit.json', client.audit)
    run.freeze()
