"""Isolated read-only product QA on real accepted Head; no daily worker."""
from pathlib import Path
from http.server import ThreadingHTTPServer
import sys,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_service.core_product_server_r1 import make_product_handler

class ReadOnlyJobs:
    def status(self):return dict(state='READ_ONLY_QA',last_processed_trade_date='2026-10-09')
    def settings(self,*args):
        if args:raise ValueError('QA_WRITES_DISABLED')
        return dict(auto_enabled=False)
    def enqueue(self,*args,**kwargs):raise ValueError('QA_WRITES_DISABLED')
    def retry(self,*args):raise ValueError('QA_WRITES_DISABLED')
    def cancel(self,*args):raise ValueError('QA_WRITES_DISABLED')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=28767);a=p.parse_args()
    print('REAL_ACCEPTED_HEAD_READ_ONLY_QA',a.port,flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),make_product_handler(ROOT,ReadOnlyJobs())).serve_forever()
