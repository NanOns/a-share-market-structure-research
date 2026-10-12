"""Read-only frozen runtime diagnostic using the current candidate handler.

No product acceptance is implied; protected authority bytes are checked at exit.
All evidence and temporary files must be on G:.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SOURCE), str(SOURCE / 'src')]
sys.dont_write_bytecode = True
os.environ.update(TMP='G:/codex_tmp', TEMP='G:/codex_tmp', TMPDIR='G:/codex_tmp')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--port', type=int, default=28866)
    parser.add_argument('--default-engine', action='store_true', help='Use the same EngineController/production_factory as the normal launcher; isolated workspace only')
    args = parser.parse_args()
    root, evidence = Path(args.root).resolve(), Path(args.evidence).resolve()
    if root.drive.upper() != 'G:' or evidence.drive.upper() != 'G:':
        raise SystemExit('G_STORAGE_REQUIRED')
    evidence.mkdir(parents=True, exist_ok=True)
    protected = {}
    paths = ['config/v4_joint_release_authority_v1.json',
             'data/v4/V4_DATA_ACCEPTED_HEAD.json',
             'data/v4/V4_RESEARCH_SNAPSHOT_HEAD.json',
             'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json']
    for name in paths:
        path = root / name
        if path.exists():
            raw = path.read_bytes()
            (evidence / (path.name + '.before.bin')).write_bytes(raw)
            protected[name] = hashlib.sha256(raw).hexdigest()
    if args.default_engine:
        from workbench_desktop.storage import WorkspaceLease
        from workbench_desktop.engine import EngineController
        import time
        with WorkspaceLease(root):
            controller = EngineController(root, args.port)
            try:
                controller.perform('start')
                metadata = dict(contract='V4_CLOSEOUT_ISOLATED_DEFAULT_ENGINE_V1',pid=os.getpid(),port=controller.port,source_root=str(SOURCE),runtime_root=str(root),normal_factory='EngineController.production_factory -> make_product_handler',launcher_limit='Same actual default engine classes; isolated wrapper does not claim installed launcher cutover',status=controller.status(),protected=protected)
                (evidence / 'SERVER_IDENTITY.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
                while True: time.sleep(.5)
            finally:
                controller.perform('stop')
                after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in protected}
                (evidence / 'PROTECTED_EXIT.json').write_text(json.dumps(dict(before=protected,after=after,unchanged=protected==after),indent=2),encoding='utf-8')
        return
    from workbench_service.v4_server import make_v4_handler
    handler = make_v4_handler(root)
    after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in protected}
    if after != protected:
        raise SystemExit('DIAGNOSTIC_INITIALIZATION_CHANGED_PROTECTED_AUTHORITY')
    metadata = dict(contract='V4_CLOSEOUT_UI_FROZEN_DEFAULT_DIAGNOSTIC_V1',
                    started_at=datetime.now(timezone.utc).isoformat(),
                    pid=os.getpid(), port=args.port, source_root=str(SOURCE), runtime_root=str(root),
                    protected=protected, scope='FROZEN_READ_PATH_ONLY_NOT_CURRENT_PRODUCER_ACCEPTANCE')
    (evidence / 'SERVER_IDENTITY.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in protected}
        (evidence / 'PROTECTED_EXIT.json').write_text(json.dumps(dict(before=protected, after=after, unchanged=protected == after), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
