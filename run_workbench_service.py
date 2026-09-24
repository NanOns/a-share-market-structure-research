from pathlib import Path
import argparse,json,os,re,sys
ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT/'src'))
from workbench_service.app import serve
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=28765); p.add_argument('--database'); a=p.parse_args()
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
