"""Disposable UI verification server: database and fixtures live on E/F only."""
import argparse
import importlib.util
import os
from pathlib import Path
from http.server import ThreadingHTTPServer
from workbench_db import WorkbenchRepository
from workbench_service.app import make_handler

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,required=True);parser.add_argument('--simulation',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];temp=Path('E:/codex_tmp/test_temp/r26-preview');temp.mkdir(parents=True,exist_ok=True)
    assert temp.resolve().drive.upper() in ('E:','F:')
    os.environ.update(TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp))
    bundle=None
    if args.simulation:
        spec=importlib.util.spec_from_file_location('r26_vector',root/'tests/test_v4_17_shadow_ui.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);bundle=module.fixture()
    db=temp/f'preview-{args.port}.duckdb'
    with WorkbenchRepository(root,db):pass
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(root,db,shadow_simulation_fixture=bundle))
    print('R26_DISPOSABLE_PREVIEW',args.port,'NOT_REAL_EVIDENCE' if bundle else 'NO_REAL_SHADOW_DATA',flush=True)
    server.serve_forever()
