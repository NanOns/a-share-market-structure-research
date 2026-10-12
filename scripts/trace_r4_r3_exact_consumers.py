"""Actual HTTP Python call traces mapped to all preserved 56 source modules."""
from pathlib import Path
import sys,threading,json,csv,io,hashlib,os,urllib.request,urllib.parse
from collections import Counter
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from workbench_service.exact_candidate_chart_r3 import make_exact_candidate_handler,PATH

def main():
    out=Path(os.environ.get('R4_EXACT_EVIDENCE_DIR',str(ROOT/'docs/audits/r4_r3_semantics_http_20261011'))).resolve();root=Path('G:/codex_tmp/r4_r3_ui_candidate')
    original=json.loads((ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json').read_bytes())['consumers']
    modules={str((ROOT/r['path']).resolve()).casefold():r['path'].replace('\\','/') for r in original}
    calls=Counter()
    def profile(frame,event,arg):
        if event=='call':
            name=frame.f_code.co_filename.casefold()
            if name in modules:calls[(modules[name],frame.f_code.co_name,frame.f_code.co_firstlineno)]+=1
    server=ThreadingHTTPServer(('127.0.0.1',0),make_exact_candidate_handler(root,None,engineering_enable=True))
    threading.setprofile(profile);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        token=hashlib.sha256((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()).hexdigest()
        q=dict(context_token=token,security_id='SEC-3A5B40C6141461B88CA555E0BB852BDF',trade_date='2026-10-09',limit=5)
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_address[1]}{PATH}?'+urllib.parse.urlencode(q),timeout=180) as response:
            assert response.status==200;body=response.read()
    finally:server.shutdown();server.server_close();thread.join();threading.setprofile(None)
    rows=[]
    for item in original:
        relative=item['path'].replace('\\','/');matched=[dict(function=fn,line=line,calls=count) for (path,fn,line),count in calls.items() if path==relative]
        rows.append(dict(path=relative,source_sha256=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),actual_http_call_count=sum(x['calls'] for x in matched),
            classification='REACHABLE_OBSERVED_IN_SCOPED_HTTP' if matched else 'UNRESOLVED_NOT_OBSERVED_IN_THIS_ENTRY',
            functions=json.dumps(matched,separators=(',',':')),full_acceptance='OPEN_OTHER_ENTRIES_AND_OUTPUT_DELTAS',
            scoped_oracle='HTTP_CORE_INDEPENDENT_ORACLE.json' if matched else 'NOT_COVERED'))
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    def atomic(name,text):
        path=out/name;tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(text,encoding='utf8');os.replace(tmp,path)
    atomic('EXACT_FACTOR_56_DYNAMIC_CONSUMERS.csv',buf.getvalue())
    atomic('DYNAMIC_CONSUMER_TRACE.json',json.dumps(dict(contract_id='R4_R3_EXACT_HTTP_56_DYNAMIC_TRACE_R1',
        actual_request=q,http_response_sha256=hashlib.sha256(body).hexdigest(),preserved_module_denominator=len(rows),
        observed_modules=sum(bool(r['actual_http_call_count']) for r in rows),call_frames=[dict(path=p,function=f,line=l,calls=n) for (p,f,l),n in sorted(calls.items())],
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitation='Observed source execution is not per-module semantic acceptance; unobserved modules are not proven legacy/unreachable'),indent=2))
    print(json.dumps(dict(preserved=56,observed=sum(bool(r['actual_http_call_count']) for r in rows))))

if __name__=='__main__':main()
