"""Loopback-only transport fault injection, forwarding actual accepted-owner API."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError
from pathlib import Path
import json,time,socket
CONTROL=Path('G:/codex_tmp/core_product_fault_r2.json')
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        mode=json.loads(CONTROL.read_text()) if CONTROL.exists() else {}
        route=self.path.split('?')[0]
        if route==mode.get('route') or mode.get('route')=='/api/v4/*' and route.startswith('/api/v4/'):
            if mode.get('disconnect'):
                self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            if mode.get('delay'):time.sleep(min(float(mode['delay']),5))
            if mode.get('status'):
                payload=json.dumps({'code':'QA_TRANSPORT_FAULT_INJECTION','reason':'EXPLICIT_TEST_ONLY_REAL_OWNER_UNCHANGED'}).encode()
                self.send_response(mode['status']);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(payload);return
        try:
            response=urlopen('http://127.0.0.1:28767'+self.path,timeout=90)
        except HTTPError as exc:response=exc
        payload=response.read();self.send_response(response.status)
        self.send_header('Content-Type',response.headers.get('Content-Type','application/octet-stream'))
        self.end_headers();self.wfile.write(payload)
    def log_message(self,*args):pass
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',28768),Handler).serve_forever()
