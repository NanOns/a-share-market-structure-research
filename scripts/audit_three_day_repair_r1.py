"""Three-day repair E1: read accepted artifacts, reconcile identities and native prices.

No source writes, network collection, owner substitution or production activation.
"""
import collections
import csv
import hashlib
import io
import json
import struct
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.fp01_evidence import write, ref

OUT = ROOT / 'docs/evidence/three_day_repair_r1_20261008'
DAYS = ('2026-09-28', '2026-09-29', '2026-09-30')


def load(path):
    return json.loads((ROOT / path).read_bytes())


def main():
    if (OUT / 'THREE_DAY_SOURCE_INVENTORY.json').exists():
        raise RuntimeError('FROZEN_EVIDENCE_EXISTS_USE_SUCCESSOR_NAMESPACE')
    source = Path('D:/Users/lps/Desktop/阶段任务/V4_20260928_0930_B8E6A595E6AEB8E797B3E5A893E5B9BDE493A1E4BB8AE5A1_R1_20261008.md')
    write(OUT / 'TASK.md', source.read_bytes())
    protected = {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / 'config').glob('*authority*.json')}
    protected['data/v4/V4_DATA_ACCEPTED_HEAD.json'] = (ROOT / 'data/v4/V4_DATA_ACCEPTED_HEAD.json').read_bytes()
    backup = {p: ref(p) for p in protected}
    for p, raw in protected.items():
        write(OUT / 'baseline' / p, raw)
    head = load('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    chain = load(head['accepted_chain']['path'])
    remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/codex/v4-system-reform'], cwd=ROOT, text=True).strip()
    write(OUT / 'ENTRY.json', dict(contract_id='THREE_DAY_SOURCE_RECONCILIATION_R1',
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        remote=remote, captured_at=datetime.now(timezone.utc).isoformat(), task=ref(OUT / 'TASK.md'),
        phase0=ref('reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json'),
        backup=backup, accepted_chain=ref(head['accepted_chain']['path']),
        stage='A/E1', next_stage='B_ONLY_AFTER_E1_DISPOSITION', acceptance='IN_PROGRESS'))
    inventory, differences, reconciliation, joins = [], [], [], []
    nodes = {n['trade_date']: n for n in chain['nodes']}
    for day in DAYS:
        node = nodes[day]
        datasets = {}
        for family, component in sorted(node['components'].items()):
            path = component['artifact_path']
            actual = ref(path)
            assert actual['sha256'] == component['artifact_sha256'], (day, family, 'HASH_MISMATCH')
            artifact = load(path)
            rows = artifact['rows']
            assert artifact['trade_date'] == day, (day, family, 'ARTIFACT_DATE')
            if not family.startswith('PERIOD_'):
                assert all(r.get('trade_date', day) == day for r in rows), (day, family, 'ROW_DATE')
            datasets[family] = rows
            inventory.append(dict(trade_date=day, family=family, exists=True, covered_rows=len(rows),
                expected_rows=component['row_count'], checksum=actual, source_as_of=component.get('source_as_of'),
                captured_at=component.get('knowledge_time'), first_available_proven=False,
                quality=component['status'], upstream_digest=component.get('input_publication_ids'),
                consumer=component.get('accepted_owner_stage'), owner_contract=artifact['contract_id'],
                timestamp_evidence='NO_TIMESTAMP_IN_COMPONENT' if not component.get('knowledge_time') else 'COMPONENT',
                knowledge_lineage='RECONSTRUCTED_CORRECTED'))
            assert len(rows) == component['row_count']
        indexed = {}
        for family in ('RAW_DAILY', 'ADJUSTED_DAILY', 'IDENTITY_UNIVERSE', 'TRADING_STATUS'):
            rows = datasets[family]
            indexed[family] = {r['security_id']: r for r in rows}
            assert len(indexed[family]) == len(rows), (day, family, 'DUPLICATE_SECURITY')
        raw, adjusted, identity, status = [indexed[f] for f in ('RAW_DAILY','ADJUSTED_DAILY','IDENTITY_UNIVERSE','TRADING_STATUS')]
        errors, affine, tdx_matches, tdx_missing = [], 0, 0, 0
        for sid in sorted(set().union(*[set(v) for v in indexed.values()])):
            i, r, a, s = [v.get(sid) for v in (identity, raw, adjusted, status)]
            symbol = (i or r or a or s).get('source_security_key')
            state = (s or {}).get('status', 'STATUS_UNBOUND')
            joins.append(dict(trade_date=day, security_id=sid, symbol=symbol,
                symbol_effective_date=(i or {}).get('symbol_effective_date'),
                symbol_effective_date_proven='symbol_effective_date' in (i or {}),
                raw_present=r is not None, adjusted_present=a is not None, identity_present=i is not None,
                trading_status=state, identity_source_revision=(r or {}).get('identity_source_revision')))
            reason = None
            if not r:
                reason = 'EXPECTED_NO_BAR_SUSPENDED' if state == 'SUSPENDED' else 'RAW_ABSENT_REQUIRES_SOURCE_SEARCH'
            elif not a or a.get('adjustment_readiness') != 'READY':
                reason = 'UNSUPPORTED_OR_UNPROVED_ADJUSTMENT'
            if reason:
                differences.append(dict(trade_date=day, security_id=sid, symbol=symbol, family='RAW_DAILY' if not r else 'ADJUSTED_DAILY',
                    reason=reason, trading_status=state, source=node['components']['RAW_DAILY']['artifact_path'],
                    next_action='NONE_EXPECTED_SUSPENSION' if state == 'SUSPENDED' and not r else 'RESOLVE_ACCEPTED_ADJUSTMENT_AUTHORITY'))
            if not r:
                continue
            o,h,l,c = [Decimal(str(r[k])) for k in ('open','high','low','close')]
            if not (l <= min(o,c) <= max(o,c) <= h):
                errors.append([sid, 'RAW_OHLC_ORDER'])
            if a and a.get('adjustment_readiness') == 'READY':
                for key in ('open','high','low','close'):
                    expected = Decimal(str(r[key])) * Decimal(a['qfq_mul']) + Decimal(a['qfq_add'])
                    if abs(expected - Decimal(a[key])) > Decimal('0.011'):
                        errors.append([sid, key, 'AFFINE_MISMATCH', str(expected), a[key]])
                    affine += 1
            market, code = symbol.lower().split('.')
            path = Path('D:/new_tdx/vipdoc') / market / 'lday' / (market+code+'.day')
            if not path.exists():
                tdx_missing += 1
                continue
            content = path.read_bytes()
            assert len(content) % 32 == 0, str(path)
            target = int(day.replace('-', ''))
            records = [struct.unpack('<IIIIIfII', content[pos:pos+32]) for pos in range(0,len(content),32) if struct.unpack_from('<I',content,pos)[0] == target]
            if not records:
                tdx_missing += 1
                continue
            assert len(records) == 1
            bar = records[0]
            matches = all(abs(Decimal(bar[idx])/100-Decimal(str(r[key]))) < Decimal('0.00001') for idx,key in enumerate(('open','high','low','close'),1))
            tdx_matches += int(matches)
            if not matches:
                errors.append([sid, 'LOCAL_TDX_VS_ACCEPTED_RAW_DIFFERENCE', str(path)])
        reconciliation.append(dict(trade_date=day, counts={k:len(v) for k,v in indexed.items()},
            trading_status_counts=dict(collections.Counter(r['status'] for r in status.values())),
            affine_comparisons=affine, local_tdx_ohlc_matches=tdx_matches, local_tdx_missing=tdx_missing,
            errors=errors, result='PASS' if not errors else 'FAIL',
            cross_target_qfq_division_used=False, price_basis='PER_TARGET_NATIVE_AFFINE_QFQ',
            membership_not_inferred_from_security_identity=True))
    csvfile = io.StringIO(newline='')
    fields = ['trade_date','security_id','symbol','family','reason','trading_status','source','next_action']
    writer = csv.DictWriter(csvfile, fieldnames=fields); writer.writeheader(); writer.writerows(differences)
    write(OUT / 'THREE_DAY_SOURCE_DIFF.csv', csvfile.getvalue().encode('utf-8-sig'))
    write(OUT / 'THREE_DAY_SECURITY_OUTER_JOIN.json', joins)
    write(OUT / 'THREE_DAY_SOURCE_INVENTORY.json', dict(contract_id='THREE_DAY_SOURCE_RECONCILIATION_R1', datasets=inventory))
    write(OUT / 'IDENTITY_AND_QFQ_RECONCILIATION.json', reconciliation)
    assert all((ROOT / p).read_bytes() == raw for p,raw in protected.items())
    write(OUT / 'E1_RECEIPT.json', dict(result='SOURCE_COMPONENTS_RECONCILED' if all(not r['errors'] for r in reconciliation) else 'BLOCKED',
        per_day=reconciliation, difference_count=len(differences), production_authorities_unchanged=True,
        full_e1_acceptance=False, remaining=['membership/source windows/full physical source inventory', 'symbol effective-date authority'],
        next_stage='COMPLETE_E1_SOURCE_DISCOVERY_BEFORE_OWNER_REPLAY'))
    print(json.dumps(reconciliation))


if __name__ == '__main__':
    main()
