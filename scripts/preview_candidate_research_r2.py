"""Temporary loopback preview; no AUTO worker, jobs, CAS or Windows service."""
import sys
import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_service.core_product_server_r1 import make_product_handler


class ReadOnlyJobs:
    def status(self):
        return dict(auto_enabled=False,worker_error=None,active_job=None,preview_only=True)
    def __getattr__(self,name):
        raise ValueError('CANDIDATE_PREVIEW_MUTATION_FORBIDDEN')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=28766)
    args=parser.parse_args()
    if args.port==28765:raise ValueError('PROTECTED_PRODUCTION_PORT')
    base=make_product_handler(ROOT,ReadOnlyJobs())
    class Handler(base):
        def do_POST(self):self.send(405,dict(reason='READ_ONLY_PREVIEW'))
        def do_PUT(self):self.send(405,dict(reason='READ_ONLY_PREVIEW'))
        def do_DELETE(self):self.send(405,dict(reason='READ_ONLY_PREVIEW'))
    with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
        print(f'READ_ONLY_CANDIDATE_PREVIEW http://127.0.0.1:{args.port}/v4/research/focus',flush=True)
        server.serve_forever()


if __name__=='__main__':main()
