"""Five independently frozen dated inputs, native PG whole-payload readback."""
import gzip,hashlib,json,os,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write,sha
from workbench_analysis.r43_owner_replay import checked
from workbench_db.v4_history_pg_r1 import build,read,canonical
from workbench_db.v4_native import connection

def main():
    from tests import v4_native_isolation_plugin_r4 as guard
    source=Path('G:/codex work/大A交易').resolve()
    head_path=source/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head_bytes=head_path.read_bytes();head=json.loads(head_bytes)
    replay=checked(source,head['day_receipt']).parent/'owner_v3/CORE_REPLAY.json'
    owners=json.loads(replay.read_bytes())['owners']
    candidate=Path('G:/codex_tmp/full_system_r4_fbd23a6b/five_history_candidate')
    candidate.mkdir(parents=True,exist_ok=True)
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    os.environ['R4_CONNECTION_LEDGER']=str(ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_03_FIVE_HISTORY_CONNECTIONS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config)
    results=[]
    try:
        for owner in owners:
            day=owner['trade_date'];guard.ACTIVE='FIVE_DATE_WHOLE_HISTORY:'+day
            path=checked(source,owner['history']);expected={};samples={}
            def rows():
                with gzip.open(path,'rt',encoding='utf8') as stream:
                    for line in stream:
                        row=json.loads(line);sid=row['security_id'];series=row['bars']
                        expected[sid]=(hashlib.sha256(canonical(series)).hexdigest(),len(series))
                        if len(samples)<3:samples[sid]=series
                        yield row
            start=time.monotonic()
            binding=build(candidate,rows(),head_token=hashlib.sha256(head_bytes).hexdigest(),t0=day,source_digest=owner['history']['sha256'])
            diffs=[];count=bars=0;latest=None
            with connection(binding['schema'],read_only=True) as pg:
                with pg.cursor(name='whole_dated_readback') as cur:
                    cur.execute('SELECT security,payload FROM history WHERE version=%s ORDER BY security',(binding['version'],))
                    for sid,series in cur:
                        count+=1;bars+=len(series)
                        if (hashlib.sha256(canonical(series)).hexdigest(),len(series))!=expected.get(sid):diffs.append(sid)
                        if series:latest=max(latest or '',series[-1]['trade_date'])
            if diffs or count!=len(expected) or latest>day:raise ValueError('FIVE_DATE_HISTORY_FULL_PAYLOAD_MISMATCH')
            for sid,series in samples.items():
                if read(candidate,binding,day,sid)!=series:raise ValueError('ACTUAL_HISTORY_READER_MISMATCH')
            try:read(candidate,binding,'1900-01-01',next(iter(samples)))
            except ValueError as exc:
                if 'CONTEXT' not in str(exc):raise
            else:raise ValueError('CROSS_DATE_READ_NOT_REJECTED')
            results.append(dict(T0=day,source_binding=owner['history'],pg_binding=binding,symbols=count,bars=bars,latest_bar=latest,differences=diffs,actual_reader_symbols=list(samples),cross_date='REJECTED',seconds=time.monotonic()-start))
            print(json.dumps(dict(T0=day,symbols=count,bars=bars,differences=len(diffs))),flush=True)
        if head_path.read_bytes()!=head_bytes:raise ValueError('SOURCE_HEAD_CHANGED')
        write('R4_03_FIVE_DATE_HISTORY_RESULT.json',dict(contract_id='R4_FIVE_DATE_HISTORY_SOURCE_ORACLE_R1',current_status='SCOPED_FIVE_DATE_FULL_PAYLOAD_PASS',denominator=len(results),results=results,source_replay=dict(path=str(replay),sha256=sha(replay)),negative_vectors=['Cross-date binding rejected for each date'],evidence_links=['R4_03_FIVE_HISTORY_CONNECTIONS.jsonl'],limitations=['No HTTP/browser or production authority loading claim','Per-date frozen source equivalence does not grant precise v0.3 owner/PIT admission'],next_conditions=['Actual HTTP/browser native read authority and capacity gate']))
    finally:
        guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)

if __name__=='__main__':main()
