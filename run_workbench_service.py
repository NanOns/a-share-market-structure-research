from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT/'src'))
from workbench_service.app import serve
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=28765); p.add_argument('--database'); a=p.parse_args()
 database=a.database
 if not database:
  local=ROOT/'runtime/operations_config.json'
  if local.is_file(): database=json.loads(local.read_text('utf-8')).get('config',{}).get('database_path')
 serve(ROOT,a.host,a.port,database)
