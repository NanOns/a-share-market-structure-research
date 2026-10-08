"""R2 isolated GET-only fault successor; never a production source."""
import json,sys
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import fp13_fault_proxy as predecessor
predecessor.CONTROL=ROOT/'runtime/r2_fault_proxy/control.json'

class Handler(predecessor.Handler):
    def do_GET(self):
        path=predecessor.CONTROL
        control=json.loads(path.read_bytes()) if path.exists() else {}
        if control.get('mode')=='forbidden' and self.path.startswith(control.get('domain','/api/v4/stocks')):
            raw=b'{"code":"QA_ONLY_FORBIDDEN","qa_only":true}'
            self.send_response(403);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return
        super().do_GET()

if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',28767),Handler).serve_forever()
