"""Supported direct launcher for frozen DM01 modules; no cwd/user-site imports."""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
MODULES=('scripts.run_v4_dm01_daily_increment','scripts.build_dm01_r4_tdx_delta',
         'scripts.freeze_v4_dm01_daily_sources','scripts.verify_dm01_r4_runtime','scripts.verify_dm01_r4r1_runtime')

def bootstrap():
    import site
    user=Path(site.getusersitepackages()).resolve()
    sys.path[:]=[p for p in sys.path if not (p and (Path(p).resolve()==user or Path(p).resolve().is_relative_to(user)))]
    for path in (ROOT,ROOT/'src'):
        text=str(path)
        while text in sys.path: sys.path.remove(text)
        sys.path.insert(0,text)
    os.chdir(ROOT)  # Frozen engineering recipes contain repository-relative reads.
    return ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module',choices=MODULES,default=MODULES[0])
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--target-date')
    parser.add_argument('--fixture-root',type=Path)
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    bootstrap()
    if args.fixture_root:
        from tests.runtime_isolation import create, guard
        root=create(args.fixture_root);guard(root,root/'fixture.duckdb','DISPOSABLE_RECOVERY')
        if args.module not in MODULES[-2:]: parser.error('fixture execution supports R4/R4R1 engineering builders only')
        if args.module.endswith('r4r1_runtime'):
            from tests.v4_dm01_r4r1.test_lineage import env
        else:
            from tests.v4_dm01_r4.test_runtime import env
        from workbench_analysis import dm01_runtime_r4 as r
        e=env.__wrapped__(root)
        result=r.build_candidate(parent=e['parent'],freeze=e['freeze'],cal=e['calendar'],identity=e['identity'],root=root)
        print(json.dumps(dict(status='ENGINEERING_FIXTURE_EXECUTED',result=result,real_forward_evidence=False,source_requests=0,tdx_root_write_count=0)))
        return 0
    if args.preflight:
        from datetime import datetime,timezone
        from workbench_analysis import dm01_runtime_r4 as r
        try:
            gate=r.session_gate(args.target_date,datetime.now(timezone.utc).isoformat(),ROOT)
            result=dict(gate,preflight=True,source_requests=0,data_mutation=False,tdx_root_write_count=0)
        except (ValueError,OSError,KeyError,TypeError) as error:
            result=dict(status='BLOCKED',reason=str(error),preflight=True,source_requests=0,data_mutation=False,tdx_root_write_count=0)
        print(json.dumps(result));return 2 if result['status']=='BLOCKED' else 0
    arguments=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
    # Frozen verification recipes write historical evidence paths; only isolated
    # fixture mode above is admitted here. Their source bytes stay immutable.
    if args.module in MODULES[-2:]: parser.error('verification recipes require --fixture-root or --preflight')
    sys.argv=[str(ROOT/(args.module.replace('.','/')+'.py'))]+arguments
    runpy.run_module(args.module,run_name='__main__')
    return 0

if __name__=='__main__': raise SystemExit(main())
