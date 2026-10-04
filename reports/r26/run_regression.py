"""Reproducible exact-scope R26 regression, E/F temporary storage only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]


def atomic(path,value,raw=False):
    target=ROOT/path
    assert path.startswith(('reports/r26/','docs/evidence/r26/'))
    target.parent.mkdir(parents=True,exist_ok=True);stage=target.with_name(target.name+'.r26-staging')
    data=value if raw else (json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+'\n').encode()
    if target.suffix in ('.json','.xml','.txt','.md','.py'):
        data=data.replace(b'\r\n',b'\n')  # repository-wide eol=lf representation
    with stage.open('wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.replace(stage,target)


def scope():
    legacy=[p.as_posix() for p in sorted((ROOT/'tests/upgrade_v3').glob('test_focus_*.py'))]
    legacy=[str(Path(p).relative_to(ROOT)).replace('\\','/') for p in legacy]
    legacy+=['tests/upgrade_v3/'+name for name in ('test_p08_01_research_api.py','test_p08_02_research_ui.py','test_p09_context_mapping.py','test_p12_daily_build_busy_ui.py','test_p12_07_today_research_ui.py','test_p12_14_turnover_ui.py','test_p09_03_ext01_evidence_ui_regression.py','test_v3_unified_entry.py','test_p01_01_lock_scope.py')]
    return legacy


def execute(directory,label,include_r26=True):
    directory=Path(directory).resolve();temp=Path('E:/codex_tmp/test_temp')/('r26-'+label)
    assert directory.drive.upper() in ('E:','F:') and temp.drive.upper() in ('E:','F:')
    env=dict(os.environ,TEMP=str(temp.parent),TMP=str(temp.parent),TMPDIR=str(temp.parent),PYTHONPATH='src'+os.pathsep+'.',PYTHONIOENCODING='utf-8',
             WORKBENCH_API_BACKEND='duckdb',WORKBENCH_PG_DSN='dbname=r26_mock host=127.0.0.1 port=1 connect_timeout=1')
    names=scope()+(['tests/test_v4_17_shadow_ui.py'] if include_r26 else [])
    report='reports/r26/'+label+'-tests.xml';xml=ROOT/report
    command=[sys.executable,'-m','pytest',*names,'-q','--basetemp='+str(temp),'--junitxml='+str(xml.with_name(xml.name+'.pytest-staging'))]
    result=subprocess.run(command,cwd=directory,env=env,capture_output=True)
    staging=xml.with_name(xml.name+'.pytest-staging');raw=staging.read_bytes();atomic(report,raw,True);staging.unlink()
    atomic('reports/r26/'+label+'-output.txt',result.stdout+result.stderr,True)
    tree=ET.fromstring(raw);tests=tree.findall('.//testcase');failures=[dict(node=t.get('classname')+'::'+t.get('name'),message=t.find('failure').get('message')) for t in tests if t.find('failure') is not None]
    summary=dict(directory=str(directory),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip(),exit_code=result.returncode,tests=len(tests),passed=len(tests)-len(failures)-len(tree.findall('.//error'))-len(tree.findall('.//skipped')),failures=failures,errors=len(tree.findall('.//error')),skipped=len(tree.findall('.//skipped')),deselected=0,scope=names,temporary_directory=str(temp),xml=report,
                 postgres_policy='NONSECRET_UNREACHABLE_MOCK_DSN_FOR_EXISTING_MONKEYPATCHED_REPLAY_TESTS; NO_LIVE_PG',
                 captured_xml_sha256=__import__('hashlib').sha256(raw).hexdigest(),
                 captured_output_sha256=__import__('hashlib').sha256(result.stdout+result.stderr).hexdigest(),
                 published_text_representation='UTF8_LF; CAPTURED_SOURCE_DIGESTS_RETAINED',
                 source_worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=directory)))
    atomic('reports/r26/'+label+'-summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('scope','failures')},ensure_ascii=False),flush=True)
    print(json.dumps(failures,ensure_ascii=False),flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',default=str(ROOT));parser.add_argument('--label',required=True);parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
    execute(args.directory,args.label,not args.baseline)
