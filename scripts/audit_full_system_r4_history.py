"""Real accepted 5224-stock history -> isolated PG; frozen SQLite oracle."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write,sha
from workbench_db.v4_history_pg_r1 import build,canonical
from workbench_db.v4_native import connection

def main():
    candidate=Path('G:/codex_tmp/full_system_r4_fbd23a6b/history_candidate');candidate.mkdir(parents=True,exist_ok=True)
    authority=json.loads((ROOT/'config/core_product_read_authority_r1.json').read_bytes())
    manifest=json.loads((ROOT/authority['manifest']['path']).read_bytes());source=manifest['source_bindings']['history'];original=manifest['history_index']
    if sha(ROOT/source['path'])!=source['sha256'] or sha(ROOT/original['path'])!=original['sha256']:raise ValueError('ORIGINAL_HISTORY_IDENTITY_INVALID')
    oracle=candidate/'sqlite_oracle.json'
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/r4_sqlite_readonly_oracle.py'),'--source',str(ROOT/original['path']),'--output',str(oracle),'--kind','history'],check=True)
    def rows():
        with gzip.open(ROOT/source['path'],'rt',encoding='utf8') as stream:
            for line in stream:yield json.loads(line)
    start=time.time();binding=build(candidate,rows(),head_token=manifest['head']['sha256'],t0=manifest['T0'],source_digest=source['sha256']);built=time.time()-start
    frozen=json.loads(oracle.read_bytes())['data'];diffs=[];count=bars=0
    with connection(binding['schema'],read_only=True) as pg:
        with pg.cursor(name='r4_history_oracle') as cur:
            cur.execute('SELECT security,payload FROM history WHERE version=%s ORDER BY security',(binding['version'],))
            for sid,series in cur:
                count+=1;bars+=len(series);actual=dict(digest=hashlib.sha256(canonical(series)).hexdigest(),bars=len(series))
                if actual!=frozen.get(sid):diffs.append(sid)
        plan=pg.execute('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT payload FROM history WHERE version=%s AND security=%s',(binding['version'],next(iter(frozen)))).fetchone()[0]
        size=pg.execute("SELECT pg_total_relation_size('history')").fetchone()[0]
    if len(frozen)!=count or diffs:raise ValueError('PG_HISTORY_FULL_ORACLE_MISMATCH')
    write('R4_03_REAL_HISTORY_ORACLE.json',dict(current_status='SCOPED_FULL_PAYLOAD_EQUIVALENCE_PASS',denominator=dict(symbols=count,bars=bars),original_binding=original,source_binding=source,pg_binding=binding,differences=diffs,build_seconds=built,pg_total_relation_bytes=size,explain=plan,evidence_links=[str(oracle)],limitations=['Latest frozen T0 only; five-date HTTP/browser, QFQ version changes and capacity gates not completed'],next_conditions=['Five-date consumer readback and fail-closed UI checks']))
    print(json.dumps(dict(symbols=count,bars=bars,differences=len(diffs),seconds=built,pg_bytes=size)))
if __name__=='__main__':main()
