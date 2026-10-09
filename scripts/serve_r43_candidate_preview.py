"""Read-only local R4.3 candidate API/preview. Does not alter production routing."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.r43_operational_publication import CandidateReadV2


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8768);args=p.parse_args()
    candidate=json.loads((ROOT/'docs/evidence/r4_3_four_session_closeout_20261009/R43_OPERATIONAL_SUCCESSOR_CANDIDATE.json').read_bytes());api=CandidateReadV2(ROOT,candidate)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                if self.path=='/':raw=(ROOT/'src/workbench_service/static/r43-operational-preview.html').read_bytes();kind='text/html; charset=utf-8'
                elif self.path.startswith('/api/v4/original-0930/'):
                    from workbench_service.research_bff import ResearchBFF
                    code,original=ResearchBFF(ROOT).get('/api/v4/'+self.path.removeprefix('/api/v4/original-0930/'),{})
                    raw=json.dumps(original,ensure_ascii=False).encode();kind='application/json'
                elif self.path=='/api/v4/strict-pit-original':
                    from workbench_service.research_bff import ResearchBFF
                    code,original=ResearchBFF(ROOT).get('/api/v4/context',{})
                    raw=json.dumps(dict(read_scope='ORIGINAL_ACCEPTED_0930_NAMESPACE',member_mode='ORIGINAL_ACCEPTED_0930',original_BFF_status=code,context=original),ensure_ascii=False).encode();kind='application/json'
                else:raw=json.dumps(api.dispatch(self.path),ensure_ascii=False,allow_nan=False).encode();kind='application/json'
                self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
            except (ValueError,KeyError) as exc:
                self.send_response(400);self.end_headers();self.wfile.write(json.dumps(dict(error=str(exc))).encode())
        def log_message(self,*args):pass
    print(json.dumps(dict(status='CANDIDATE_READ_ONLY_PREVIEW',url=f'http://127.0.0.1:{args.port}',context_token=api.token)),flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

if __name__=='__main__':main()
