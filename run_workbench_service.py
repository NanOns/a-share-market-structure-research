from pathlib import Path
import argparse,json,os,re,sys,time
os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp')
sys.dont_write_bytecode=True
SOURCE_ROOT=Path(__file__).resolve().parent
ROOT=SOURCE_ROOT; sys.path[:0]=[str(SOURCE_ROOT),str(SOURCE_ROOT/'src')]
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=28765); p.add_argument('--database'); modes=p.add_mutually_exclusive_group(); modes.add_argument('--v4-shadow-only',action='store_true',help='Serve the read-only V4 preview without legacy workbench dependencies'); modes.add_argument('--v4-default','--v4-production',dest='v4_default',action='store_true'); modes.add_argument('--legacy-v3',action='store_true'); p.add_argument('--workspace-root',type=Path,help='Explicit G-local data/config workspace; source imports remain bound to this release'); p.add_argument('--native-pg-roles',type=Path,help='Explicit Windows user DPAPI role credentials inside the chosen workspace'); a=p.parse_args()
 if a.workspace_root is not None:
  ROOT=a.workspace_root.resolve()
  if ROOT.drive.upper()!='G:' or not ROOT.is_dir():raise SystemExit('G_LOCAL_WORKSPACE_REQUIRED')
 if a.native_pg_roles is not None:
  role_file=a.native_pg_roles.resolve()
  if not role_file.is_relative_to(ROOT/'config'):raise SystemExit('PG_ROLE_FILE_OUTSIDE_WORKSPACE_CONFIG')
  from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
  os.environ['V4_NATIVE_PG_DSN']=load_credentials(role_file)[ROLES[1]]
 if a.v4_shadow_only:
  from workbench_service.shadow_server import serve_shadow
  serve_shadow(ROOT,a.host,a.port)
  raise SystemExit(0)
 authority_path=ROOT/'config/v4_production_runtime_authority_v1.json'
 if not a.legacy_v3:
  if not authority_path.is_file():raise SystemExit('V4_RUNTIME_AUTHORITY_MISSING: fail closed')
  authority=json.loads(authority_path.read_bytes())
  if authority.get('activation_status')!='ACTIVE' and not a.v4_default:raise SystemExit('V4_CUTOVER_GATE_NOT_ACTIVE: use explicit candidate entry')
  if a.host not in ('127.0.0.1','localhost'):raise SystemExit('V4_LOOPBACK_HOST_REQUIRED')
  from workbench_desktop.storage import WorkspaceLease
  from workbench_desktop.engine import EngineController
  with WorkspaceLease(ROOT):
   controller=EngineController(ROOT,a.port)
   try:
    controller.perform('start')
    while True:time.sleep(.5)
   except KeyboardInterrupt:
    pass
   finally:
    controller.perform('stop')
  raise SystemExit(0)
 from workbench_service.app import serve
 local_env=ROOT/'config/.env'
 if local_env.is_file():
  for line in local_env.read_text('utf-8').splitlines():
   key,sep,value=line.partition('=')
   if sep and key.strip()=='WORKBENCH_PG_DSN' and not os.environ.get('WORKBENCH_PG_DSN'):
    os.environ['WORKBENCH_PG_DSN']=value.strip().strip('"').strip("'")
 config_text=(ROOT/'config/workbench.yaml').read_text('utf-8')
 engine_match=re.search(r'^\s{4}engine:\s*["\']?(postgresql|duckdb)',config_text,re.MULTILINE)
 if not engine_match: raise SystemExit('WORKBENCH_DATABASE_ENGINE_NOT_CONFIGURED')
 engine=engine_match.group(1)
 if engine=='postgresql':
  if not os.environ.get('WORKBENCH_PG_DSN'):
   raise SystemExit('WORKBENCH_PG_DSN_REQUIRED: configured PostgreSQL cannot fall back to DuckDB')
  os.environ['WORKBENCH_API_BACKEND']='postgresql'
 else:
  os.environ['WORKBENCH_API_BACKEND']='duckdb'
 database=a.database
 if not database:
  local=ROOT/'runtime/operations_config.json'
  if local.is_file(): database=json.loads(local.read_text('utf-8')).get('config',{}).get('database_path')
 serve(ROOT,a.host,a.port,database)
