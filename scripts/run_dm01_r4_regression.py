"""Reproducible explicit union of accepted DM01 and R31R2 scopes plus R4 vectors."""
import argparse,json,os,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--basetemp',required=True,type=Path);args=parser.parse_args()
    if args.basetemp.resolve().drive.upper() not in ('E:','F:'):raise ValueError('E_F_TEST_STORAGE_REQUIRED')
    args.output.mkdir(parents=True,exist_ok=True)
    scope=json.loads((ROOT/'reports/dm01_r4/REGRESSION_SCOPE.json').read_bytes())['scope']
    xml=args.output/'regression.xml';log=args.output/'regression.log'
    command=[sys.executable,'-B','-m','pytest',*scope,'-q','--basetemp='+str(args.basetemp),'--junitxml='+str(xml)]
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT),PYTHONDONTWRITEBYTECODE='1')
    with log.open('w',encoding='utf8') as stream:result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    suite=ET.parse(xml).getroot().find('testsuite');cases=suite.findall('testcase')
    failures=[t.get('classname')+'::'+t.get('name') for t in cases if t.find('failure') is not None or t.find('error') is not None]
    value=dict(scope=scope,command=command,tested_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        exit_code=result.returncode,total=int(suite.get('tests')),errors=int(suite.get('errors')),failed=int(suite.get('failures')),
        skipped=int(suite.get('skipped')),passed=len(cases)-len(failures)-int(suite.get('skipped')),failures=failures,
        log=str(log.resolve()),junitxml=str(xml.resolve()),test_storage=str(args.basetemp.resolve()))
    p=args.output/'summary.json';q=p.with_suffix('.tmp');q.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');os.replace(q,p)
    print(json.dumps({k:v for k,v in value.items() if k not in ('scope','command')}))
    return result.returncode
if __name__=='__main__':raise SystemExit(main())
