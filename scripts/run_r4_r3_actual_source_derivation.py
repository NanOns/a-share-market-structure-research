"""Actual archived source freeze -> normal executor derivation, without promotion."""
import hashlib,json,os,sys,traceback
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
run_id=sys.argv[1] if len(sys.argv)>1 else 'SOURCE_DERIVATION_R1'
exact_candidate='--exact-candidate' in sys.argv[2:]
if not run_id.startswith('SOURCE_DERIVATION_R') or not run_id.replace('_','').isalnum():raise ValueError('VERSIONED_EVIDENCE_RUN_ID_REQUIRED')
OUT=ROOT/'docs/audits/r4_r3_consumers_20261011'/run_id;OUT.mkdir(exist_ok=False)
workspace=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
from scripts.r4_readonly_source_guard import install
install(['G:/codex work/大A交易','D:/new_tdx'])
fork=json.loads((workspace/'ENGINEERING_FORK_RECEIPT.json').read_bytes())
linked=set(fork['linked_readonly_files'])
def protect(event,args):
    paths=[];write=False
    if event=='open':
        write=any(c in (args[1] or '') for c in 'wax+') or bool(args[2]&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC));paths=args[:1]
    elif event in ('os.remove','os.rename','os.rmdir'):write=True;paths=args[:2] if event=='os.rename' else args[:1]
    if write and any(isinstance(p,(str,bytes,os.PathLike)) and str(Path(os.fsdecode(p)).resolve()) in linked for p in paths):raise PermissionError('FROZEN_LINKED_INPUT_WRITE_FORBIDDEN')
sys.addaudithook(protect)
os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
os.environ['R4_CONNECTION_LEDGER']=str(OUT/'ACTUAL_CONNECTIONS.jsonl')
os.environ['R4_ENGINEERING_HISTORICAL_GIT_ROOT']=str(ROOT)
from tests import v4_native_isolation_plugin_r4 as guard
config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='NORMAL_EXECUTOR_ARCHIVED_REAL_FREEZE_DERIVATION'
from scripts.r4_r3_consumer_trace import ConsumerTrace
trace=ConsumerTrace(OUT/'ACTUAL_56_TRACE.json','operational_daily_executor_v1.derive_ready_sources actual archived real 2026-10-09 source freeze')
trace.start()
protected=['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_joint_release_authority_v1.json']
before={p:hashlib.sha256((workspace/p).read_bytes()).hexdigest() for p in protected}
freeze=next((workspace/'data/v4/dynamic_daily_sources/daily_freezes/2026-10-09').glob('*.json'))
binding=dict(path=freeze.relative_to(workspace).as_posix(),sha256=hashlib.sha256(freeze.read_bytes()).hexdigest())
if run_id not in ('SOURCE_DERIVATION_R1','SOURCE_DERIVATION_R2'):
    # A new engineering derivative relocates the package address only. The
    # captured source and its original absolute address remain immutable.
    document=json.loads(freeze.read_bytes())
    package=document.get('effective_package')
    if package:
        original=Path(package['download']['path']).resolve()
        relative=original.relative_to(Path('G:/codex work/大A交易').resolve())
        relocated=workspace/relative
        expected=package['download']['sha256']
        def digest(path):
            value=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
            return value.hexdigest()
        if digest(original)!=expected or digest(relocated)!=expected:
            raise ValueError('ENGINEERING_PACKAGE_RELOCATION_HASH_MISMATCH')
        document['engineering_source_origin']=dict(binding=binding,original_package_path=str(original),
            relocated_package_path=str(relocated),package_sha256=expected,production_permission=False,PIT_ELIGIBLE=False)
        package['download']['path']=str(relocated.resolve())
        if exact_candidate:
            executed_paths=['src/workbench_analysis/exact_operational_core_candidate_r3.py','src/adjustment/tdx_adjustment_v0_3.py','src/workbench_analysis/operational_owner_adapter_v1.py','src/workbench_analysis/r43_owner_replay.py']
            document['engineering_exact_adjustment_candidate']=dict(contract='V4_OPERATIONAL_CORE_EXACT_AFFINE_CANDIDATE_R3',
                executed_sources={p:digest(ROOT/p) for p in executed_paths},production_permission=False,PIT_ELIGIBLE=False)
        derivative=OUT/'ENGINEERING_SOURCE_FREEZE.json'
        derivative.write_text(json.dumps(document,indent=2)+'\n',encoding='utf8')
        # Store a separate new input under the isolated root for normal binding checks.
        local=workspace/'data/v4/dynamic_daily_sources/engineering_replays'/run_id/'SOURCE_FREEZE.json'
        local.parent.mkdir(parents=True,exist_ok=False)
        local.write_bytes(derivative.read_bytes())
        binding=dict(path=local.relative_to(workspace).as_posix(),sha256=digest(local))
try:
    from workbench_analysis.operational_daily_executor_v1 import derive_ready_sources
    result=derive_ready_sources(workspace,'2026-10-09',dict(source_freeze=binding),engineering_replay_current=run_id!='SOURCE_DERIVATION_R1' and run_id!='SOURCE_DERIVATION_R2',progress=lambda *args:print(json.dumps(args,default=str),flush=True))
except BaseException as exc:result=dict(status='ENGINEERING_FAILED',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
finally:
    trace.close();guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)
after={p:hashlib.sha256((workspace/p).read_bytes()).hexdigest() for p in protected}
if before!=after:raise ValueError('UNAUTHORIZED_AUTHORITY_CHANGED')
(OUT/'RESULT.json').write_text(json.dumps(dict(result=result,source_freeze=binding,protected_before=before,protected_after=after,production_changed=False,source_time='Archived actual source bytes; no fabricated contemporaneous capture or PIT approval'),indent=2,default=str)+'\n',encoding='utf8')
print(json.dumps(dict(status=result.get('status'),error=result.get('error'))),flush=True)
