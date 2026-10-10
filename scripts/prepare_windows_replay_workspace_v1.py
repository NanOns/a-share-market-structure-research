"""Copy exact bounded reference closure into G-only isolated replay workspace."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from collections import deque

ROOT = Path(__file__).resolve().parents[1]


def prepare(destination):
    target = Path(destination).resolve()
    prefix = Path('G:/codex_tmp/test_temp').resolve()
    if target == prefix or not target.is_relative_to(prefix) or target.exists():
        raise ValueError('NEW_ISOLATED_G_WORKSPACE_REQUIRED')
    target.mkdir(parents=True)
    pending, copied, missing = deque(), set(), set()
    def enqueue(value):
        if not isinstance(value,str) or not value or len(value)>1000:
            return
        if not value.replace('\\','/').startswith(('src/','scripts/','config/','data/','docs/','reports/','G:/codex work/')):
            return
        path = Path(value)
        if not path.is_absolute():
            path = ROOT/path
        try:
            path = path.resolve()
            relative = path.relative_to(ROOT)
        except (OSError,ValueError):
            return
        if path.is_file() and '.git' not in relative.parts:
            pending.append(path)
    def scan(value):
        if isinstance(value,dict):
            for v in value.values():scan(v)
        elif isinstance(value,list):
            for v in value:scan(v)
        elif isinstance(value,str):
            enqueue(value)
    prefixes = ['src','scripts','config','reports/v4_phase0','reports/v4_baostock',
        'docs/evidence/source_acquisition_r4_20261009','docs/evidence/r4_3_four_session_closeout_20261009']
    for name in prefixes:
        for source in (ROOT/name).rglob('*'):
            if source.is_file() and '__pycache__' not in source.parts:pending.append(source)
    for source in (ROOT/'data/v4').glob('*.json'):pending.append(source)
    # Product layer contracts have fixed dated inputs outside head closure.
    for source in (ROOT/'docs/evidence').glob('*/STAGE_CONTRACT*.json'):pending.append(source)
    head=json.loads((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    receipt=json.loads((ROOT/head['day_receipt']['path']).read_bytes())
    freeze=json.loads((ROOT/receipt['source_freeze']['path']).read_bytes())
    predecessor=ROOT/head['predecessor']['path']
    pending.append(predecessor)
    scan(freeze)
    while pending:
        source=pending.popleft()
        relative=source.relative_to(ROOT)
        if relative.as_posix() in copied:continue
        destination=target/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
        copied.add(relative.as_posix())
        if source.suffix=='.json':
            try:scan(json.loads(source.read_bytes()))
            except (ValueError,UnicodeError):pass
        if len(copied)%500==0:print('Copied',len(copied),flush=True)
    # Writable heads are independent byte copies. All original artifacts remain
    # byte-identical; no hard links or output redirection into production.
    (target/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').write_bytes(predecessor.read_bytes())
    git = shutil.which('git')
    subprocess.run([git,'init',str(target)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    alternate=target/'.git/objects/info/alternates'
    alternate.write_text((ROOT/'.git/objects').as_posix()+'\n',encoding='utf-8')
    commit=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    subprocess.run([git,'update-ref','refs/heads/replay',commit],cwd=target,check=True)
    (target/'.git/HEAD').write_text('ref: refs/heads/replay\n',encoding='ascii')
    request=dict(contract_id='V4_ISOLATED_PACKAGE_QA_V1', evidence_kind='ARCHIVED_SOURCE_REPLAY',
        source_workspace=str(ROOT), production_head_sha256=hashlib.sha256((ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()).hexdigest(),
        source_freeze=receipt['source_freeze'], predecessor=head['predecessor'], target_session=freeze['target_session'],
        original_observed_at=freeze['observed_at'], copied_files=len(copied),
        first_capture_claim=False, external_acceptance='NOT_GRANTED')
    (target/'ISOLATED_PACKAGE_QA.json').write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(request,ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('workspace')
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    prepare(parser.parse_args().workspace)
