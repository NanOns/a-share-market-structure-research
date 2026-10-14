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
    parser.add_argument('--root',type=Path,default=ROOT,
                        help='Read-only product data root; source code and static assets remain this checkout')
    parser.add_argument('--chart-history-index-root',type=Path,default=None,
                        help='Optional read-only root whose workspace identity matches the bound PG history schema')
    parser.add_argument('--market-fact-index-root',type=Path,default=None,
                        help='Optional read-only root whose workspace identity matches the bound PG market-facts schema')
    parser.add_argument('--operational-owner-index-root',type=Path,default=None,
                        help='Optional read-only root whose workspace identity matches the bound operational-owner schema')
    args=parser.parse_args()
    if args.port==28765:raise ValueError('PROTECTED_PRODUCTION_PORT')
    base=make_product_handler(args.root.resolve(),ReadOnlyJobs(),static_root=ROOT/'src/workbench_service/static',
                              chart_history_index_root=args.chart_history_index_root.resolve() if args.chart_history_index_root else None,
                              market_fact_index_root=args.market_fact_index_root.resolve() if args.market_fact_index_root else None,
                              operational_owner_index_root=args.operational_owner_index_root.resolve() if args.operational_owner_index_root else None)
    class Handler(base):
        def do_POST(self):self.send(405,dict(reason='READ_ONLY_PREVIEW'))
        def do_PUT(self):self.send(405,dict(reason='READ_ONLY_PREVIEW'))
        def do_DELETE(self):self.send(405,dict(reason='READ_ONLY_PREVIEW'))
    with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:
        print(f'READ_ONLY_CANDIDATE_PREVIEW http://127.0.0.1:{args.port}/v4/research/focus',flush=True)
        server.serve_forever()


if __name__=='__main__':main()
