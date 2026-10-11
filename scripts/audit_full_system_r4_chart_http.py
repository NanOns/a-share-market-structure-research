"""Actual product HTTP with explicit isolated history authority and native guard."""
import json,os,sys,threading,subprocess,time
from pathlib import Path
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.parse import urlencode,quote
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write,sha

def main():
    from tests import v4_native_isolation_plugin_r4 as guard
    from workbench_service.core_product_server_r1 import make_product_handler
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    from workbench_analysis.operational_successor_v1 import accepted_api
    source=Path('G:/codex work/大A交易').resolve();api=accepted_api(source)
    previous=json.loads((ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_03_FIVE_DATE_HISTORY_RESULT.json').read_bytes())
    candidate=Path('G:/codex_tmp/full_system_r4_fbd23a6b/chart_http_candidate');candidate.mkdir(parents=True,exist_ok=True)
    context=candidate/'ISOLATED_HISTORY_AUTHORITY.json'
    value=dict(contract_id='R4_ISOLATED_DATED_HISTORY_READ_R1',production_accepted=False,source_root=str(source),head_token=api.token,index_root='G:/codex_tmp/full_system_r4_fbd23a6b/five_history_candidate',dates={r['T0']:dict(history_index=r['pg_binding'],source_binding=r['source_binding']) for r in previous['results']})
    context.write_text(json.dumps(value),encoding='utf8')
    sid=previous['results'][-1]['actual_reader_symbols'][0]
    queries=[dict(trade_date=r['T0'],period=period,price_basis=basis,limit=120) for r in previous['results'] for period in ('D','W','M') for basis in ('RAW','QFQ')]
    oracle_request=candidate/'ORACLE_REQUEST.json';oracle_output=candidate/'ORACLE_OUTPUT.json'
    oracle_request.write_text(json.dumps(dict(security_id=sid,queries=[q for q in queries if q['trade_date']==api.candidate['accepted_trade_date']])),encoding='utf8')
    subprocess.run([sys.executable,'-B',str(ROOT/'scripts/r4_frozen_chart_oracle.py'),str(oracle_request),str(oracle_output)],check=True)
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    os.environ['R4_CONNECTION_LEDGER']=str(ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_03_CHART_HTTP_CONNECTIONS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='ACTUAL_PRODUCT_CHART_HTTP'
    jobs=DailyJobs(candidate);server=ThreadingHTTPServer(('127.0.0.1',0),make_product_handler(source,jobs,isolated_history_authority=context))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();results=[]
    def get(q):
        url=f'http://127.0.0.1:{server.server_port}/api/v4/stocks/'+quote(sid,safe='')+'/chart?'+urlencode(q)
        try:
            with urlopen(url,timeout=60) as response:return response.status,json.loads(response.read())
        except HTTPError as exc:return exc.code,json.loads(exc.read())
    try:
        for q in queries:
            start=time.monotonic();code,data=get(dict(q,context_token=api.token))
            domain='period_raw' if q['price_basis']=='RAW' else 'period_adjusted'
            expected_missing=q['period']!='D' and domain not in api.candidate['owners'][q['trade_date']]
            if expected_missing:
                if code!=200 or data.get('status')!='SOURCE_INCOMPLETE' or data.get('gap',{}).get('reason')!='DATED_'+domain.upper()+'_OWNER_NOT_BOUND':raise ValueError('MISSING_PERIOD_OWNER_NOT_EXPLICIT:'+str((code,data)))
            elif code!=200 or data.get('as_of')!=q['trade_date'] or data.get('series_index',{}).get('engine')!='postgresql' or any(x['trade_date']>q['trade_date'] for x in data['items']):raise ValueError('ACTUAL_CHART_HTTP_FAILED:'+str((code,data)))
            if data.get('production_accepted') is not False:raise ValueError('ISOLATED_READ_MISLABELED_PRODUCTION')
            results.append(dict(query=q,code=code,items=data['items'],total=data['total'],expected_missing=expected_missing,status=data.get('status'),seconds=time.monotonic()-start))
        oracle=json.loads(oracle_output.read_bytes());latest=[x for x in results if x['query']['trade_date']==api.candidate['accepted_trade_date']]
        if any(any(x[k]!=y[k] for k in ('query','code','items','total')) for x,y in zip(latest,oracle)) or len(latest)!=len(oracle):raise ValueError('FROZEN_SQLITE_CHART_ORACLE_MISMATCH')
        bad_code,bad=get(dict(queries[0],context_token='invalid'))
        if bad_code!=409:raise ValueError('CONTEXT_TOKEN_NEGATIVE_NOT_REJECTED')
        value['dates'][queries[0]['trade_date']]['history_index']['engine']='sqlite3';context.write_text(json.dumps(value),encoding='utf8')
        tamper_code,tamper=get(dict(queries[0],context_token=api.token))
        if tamper_code!=400 or 'BINDING' not in tamper.get('reason',''):raise ValueError('NON_PG_AUTHORITY_NOT_REJECTED')
        write('R4_03_CHART_HTTP_RESULT.json',dict(contract_id='R4_ISOLATED_PRODUCT_CHART_HTTP_R1',current_status='SCOPED_HTTP_CHART_PASS',denominator=len(results),security_id=sid,results=results,latest_frozen_oracle=dict(path=str(oracle_output),sha256=sha(oracle_output),cases=len(oracle),differences=0),negative_vectors=[dict(code=bad_code,reason=bad.get('reason')),dict(code=tamper_code,reason=tamper.get('reason'))],evidence_links=['R4_03_CHART_HTTP_CONNECTIONS.jsonl'],limitations=['Explicit isolated authority only; default production authority not switched','One real security across five dates, six basis/period combinations; browser DOM and capacity not yet checked'],next_conditions=['Browser DOM readback, wider representative securities and capacity']))
        print(json.dumps(dict(cases=len(results),latest_oracle_cases=len(oracle),differences=0,negative_codes=[bad_code,tamper_code])))
    finally:
        value['dates'][queries[0]['trade_date']]['history_index']['engine']='postgresql';context.write_text(json.dumps(value),encoding='utf8')
        server.shutdown();server.server_close();jobs.close();guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)

if __name__=='__main__':main()
