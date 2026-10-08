"""Local GET-only QA fault proxy. No production configuration is changed."""
import json,sys,time,urllib.request,urllib.error
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.fp01_evidence import write
CONTROL=ROOT/'runtime/fp13_fault_proxy/control.json'
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        control=json.loads(CONTROL.read_bytes()) if CONTROL.exists() else {}
        mode=control.get('mode','normal');domain=control.get('domain','/api/v4/stocks')
        if mode=='delay' and self.path.startswith(domain):time.sleep(2)
        if mode in ('domain_failure','expired','api_unavailable') and self.path.startswith('/api/v4/') and (mode=='api_unavailable' or self.path.startswith(domain)):
            code=409 if mode=='expired' else 503
            body=json.dumps(dict(code='CONTEXT_CONFLICT:QA_EXPIRED_TOKEN' if code==409 else 'QA_INJECTED_DOMAIN_FAILURE',qa_only=True)).encode();content_type='application/json'
        else:
            try:
                response=urllib.request.urlopen('http://127.0.0.1:28765'+self.path,timeout=30)
            except urllib.error.HTTPError as error:response=error
            code=response.code;body=response.read();content_type=response.headers.get('Content-Type','application/octet-stream');response.close()
        self.send_response(code);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_POST(self):self.send_error(405,'QA_READ_ONLY')
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',28766),Handler).serve_forever()
