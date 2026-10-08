"""Independent package oracle and bounded local source discovery for E1."""
import collections
import gzip
import json
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.fp01_evidence import write, ref
from scripts.audit_three_day_repair_r1 import OUT, DAYS, load


def main():
    if (OUT / 'PACKAGE_ORACLE.json').exists():
        raise RuntimeError('FROZEN_ORACLE_EXISTS')
    head = load('data/v4/V4_DATA_ACCEPTED_HEAD.json')
    chain = load(head['accepted_chain']['path'])
    packages = list((ROOT / 'data/v4').rglob('hsjday.zip'))
    package_refs = [ref(p) for p in packages]
    expected = {}
    for n in chain['nodes']:
        if n['trade_date'] in DAYS:
            expected[n['trade_date']] = load(n['components']['RAW_DAILY']['artifact_path'])['rows']
    lookup = {b['sha256']: ROOT / b['path'] for b in package_refs}
    by_package = collections.defaultdict(list)
    for day, rows in expected.items():
        for row in rows:
            by_package[row['source_snapshot_id'].removeprefix('sha256-')].append((day,row))
    results = []
    for sha, rows in by_package.items():
        path = lookup.get(sha)
        if path is None:
            results.append(dict(sha256=sha, result='NOT_VERIFIABLE', reason='SOURCE_PACKAGE_NOT_FOUND'))
            continue
        with zipfile.ZipFile(path) as z:
            names = {name.replace('\\','/').split('/')[-1].lower(): name for name in z.namelist() if name.endswith('.day')}
            cached = {}
            counts, errors = collections.Counter(), []
            for day, row in rows:
                market, code = row['source_security_key'].lower().split('.')
                key = market+code+'.day'
                if key not in cached:
                    raw = z.read(names[key])
                    assert len(raw) % 32 == 0
                    targets = {int(d.replace('-','')) for d in DAYS}
                    cached[key] = {record[0]:record for record in struct.iter_unpack('<IIIIIfII',raw) if record[0] in targets}
                b = cached[key].get(int(day.replace('-','')))
                if b is None:
                    errors.append([day,row['security_id'],'MISSING_PACKAGE_BAR']); continue
                for idx,field in enumerate(('open','high','low','close'),1):
                    if abs(b[idx]/100-row[field]) > 1e-8:
                        errors.append([day,row['security_id'],field,b[idx]/100,row[field]])
                    counts[day+':OHLC'] += 1
                for idx,field in ((5,'amount'),(6,'volume')):
                    if b[idx] != row[field]:
                        errors.append([day,row['security_id'],field,b[idx],row[field]])
                    counts[day+':'+field] += 1
            results.append(dict(package=ref(path), result='PASS' if not errors else 'FAIL', comparisons=dict(counts), errors=errors))
    write(OUT / 'PACKAGE_ORACLE.json',dict(packages=package_refs,results=results,independent_method='TDX_BINARY_STRUCT_32_BYTES_NO_ETL_KERNEL_CALL'))
    discovered = []
    for p in sorted((ROOT / 'data').rglob('*')):
        if not p.is_file(): continue
        name = p.name.lower()
        if any(token in name for token in ('membership','gbbq','baostock','execution_context','identity')):
            discovered.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size))
    membership = []
    for item in discovered:
        p = ROOT / item['path']
        if 'membership' not in p.name.lower():continue
        if p.suffix == '.parquet':
            import pyarrow.parquet as pq
            t = pq.read_table(p)
            dates = {col:sorted(set(map(str,t[col].to_pylist()))) for col in t.column_names if 'date' in col}
            membership.append(dict(**ref(p),rows=t.num_rows,dates=dates,
                target_date_rows={d:sum(str(v)==d for v in t['date'].to_pylist()) for d in DAYS} if 'date' in t.column_names else {},
                pit_values=sorted(set(t['pit_membership'].to_pylist())) if 'pit_membership' in t.column_names else None))
        elif p.suffix == '.gz' and 'v4_08' in str(p):
            rows=[json.loads(l) for l in gzip.open(p,'rt',encoding='utf8')]
            membership.append(dict(**ref(p),rows=len(rows),date_fields={key:dict(collections.Counter(str(r.get(key)) for r in rows))
                for key in ('trade_date','membership_effective_date','source_as_of','captured_at')},sample=rows[:1]))
    write(OUT / 'LOCAL_SOURCE_DISCOVERY.json',dict(search_roots=['data','D:/new_tdx'],
        scope='REPOSITORY_DATA_RECURSIVE_AND_CONFIGURED_TDX_TARGET_FILES; NOT_ENTIRE_DISK',files=discovered,membership=membership,
        no_network_collection=True, absence_claim_limited_to_searched_roots=True))
    print(json.dumps(dict(package_results=[dict(result=r['result'],comparisons=r.get('comparisons')) for r in results],membership_candidates=len(membership))))


if __name__ == '__main__':main()
