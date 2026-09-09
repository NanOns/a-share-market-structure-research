from __future__ import annotations
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from urllib.request import urlopen

def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)
def alive(pid):
 try:os.kill(pid,0);return True
 except OSError:return False
def main():
 p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--root',required=True);p.add_argument('--host',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--status',required=True);a=p.parse_args();root=Path(a.root);status=Path(a.status)
 write(status,{'state':'等待旧服务退出'})
 for _ in range(100):
  if not alive(a.pid):break
  time.sleep(.1)
 command=[sys.executable,str(root/'run_workbench_service.py'),'--host',a.host,'--port',str(a.port)];flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
 child=subprocess.Popen(command,cwd=root,creationflags=flags);write(status,{'state':'启动新服务','pid':child.pid})
 deadline=time.monotonic()+15;url=f'http://{a.host}:{a.port}/api/operations/status'
 while time.monotonic()<deadline:
  try:
   with urlopen(url,timeout=1) as response:
    if response.status==200:write(status,{'state':'READY','pid':child.pid});return 0
  except Exception:time.sleep(.25)
 child.terminate()
 try:child.wait(timeout=5)
 except Exception:pass
 previous=root/'runtime/operations_config.previous.json';current=root/'runtime/operations_config.json'
 if previous.is_file():os.replace(previous,current)
 rollback=subprocess.Popen(command,cwd=root,creationflags=flags);write(status,{'state':'回退旧配置','pid':rollback.pid})
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  try:
   with urlopen(url,timeout=1) as response:
    if response.status==200:write(status,{'state':'ROLLED_BACK','pid':rollback.pid});return 0
  except Exception:time.sleep(.25)
 write(status,{'state':'FAILED','pid':rollback.pid,'message':'新旧配置均未通过健康检查'});return 1
if __name__=='__main__':raise SystemExit(main())
