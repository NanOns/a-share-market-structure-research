"""Six targeted ex-date probes, preserving prior provider budgets."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from validation.phase0_2b import FrozenRun, EvidenceClient, read_frozen
from phase0_2b_runner import fetch_bar

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
    rows = []
    for sid, date in [('SH.600519', 20250626), ('SH.600519', 20251219), ('SH.600519', 20260626),
                      ('SZ.000651', 20150703), ('SZ.000651', 20260826), ('SZ.000651', 20260827)]:
        for provider in ('EASTMONEY', 'TENCENT'):
            pair = {str(m): fetch_bar(client, provider, sid, date, m) for m in (0, 1)}
            rows.append({'security_id': sid, 'date': date, 'external_source': provider, **pair})
        print(sid, date, dict(client.budget.count), flush=True)
    run.put('probes.json', rows)
    run.put('network_audit.json', client.audit)
    run.freeze()
