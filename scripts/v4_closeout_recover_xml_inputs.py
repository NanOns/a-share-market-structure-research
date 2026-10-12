"""Recover only absent exact archived inputs; never replace current authority."""
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[Path('G:/codex work/r4-pg-only-20261011'),Path('G:/codex work/大A交易')]
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/denominator')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    global ROOT
    if len(sys.argv)>3:
        ROOT=Path(sys.argv[3]).resolve()
        if not ROOT.is_relative_to(Path('G:/codex_tmp').resolve()):
            raise ValueError('HISTORICAL_RECOVERY_G_ISOLATED_ROOT_REQUIRED')
    xml=Path(sys.argv[1]).resolve();label=sys.argv[2]
    if not label.isalnum():raise ValueError('RUN_LABEL_REQUIRED')
    wanted=set()
    prefix=str(ROOT).replace('\\','/')+'/'
    for node in ET.parse(xml).findall('.//testcase'):
        for tag in ('failure','error'):
            fault=node.find(tag)
            if fault is None:continue
            text=((fault.text or '')+'\n'+fault.get('message','')).replace('\\\\','/').replace('\\','/')
            for match in re.finditer(re.escape(prefix)+r"([^'\"\r\n]+)",text):
                name=match.group(1)
                if any((source/name).is_file() for source in SOURCES):wanted.add(name)
    queue=list(wanted);seen=set();records=[]
    def refs(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and value.get('sha256'):yield value
            for child in value.values():yield from refs(child)
        elif isinstance(value,list):
            for child in value:yield from refs(child)
    while queue:
        name=queue.pop()
        if name in seen:continue
        seen.add(name);target=(ROOT/name).resolve()
        if not target.is_relative_to(ROOT):raise ValueError('INPUT_RECOVERY_PATH_ESCAPE')
        source=next((base/name for base in SOURCES if (base/name).is_file()),None)
        if source is None:continue
        before=sha(source)
        if target.exists():status='EXISTING_PRESERVED'
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_suffix(target.suffix+'.closeout-copy-'+label+'.tmp')
            with source.open('rb') as origin,temporary.open('xb') as dest:
                while block:=origin.read(1024*1024):dest.write(block)
            assert sha(temporary)==before
            import os
            try:os.link(temporary,target)
            except FileExistsError:pass
            temporary.unlink();status='COPIED_MISSING_ONLY'
        assert sha(source)==before
        records.append(dict(path=name,source=str(source),sha256=before,status=status))
        if source.suffix=='.json':
            # Existing frozen fixtures can differ from the current source
            # document. Follow their own pinned dependencies, never replace
            # their historical graph with the latest source graph.
            try:document=json.loads(target.read_bytes())
            except (ValueError,UnicodeError):continue
            for ref in refs(document):
                child=ref['path']
                if Path(child).is_absolute():continue
                valid=next((base/child for base in SOURCES if (base/child).is_file() and sha(base/child)==ref['sha256']),None)
                if valid is not None:queue.append(child)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/('XML_INPUT_RECOVERY_'+label+'.json')).write_text(json.dumps(dict(input_xml=str(xml),records=records,source_writes=0),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(named_inputs=len(wanted),visited=len(seen),copied=sum(r['status']=='COPIED_MISSING_ONLY' for r in records))))
if __name__=='__main__':main()
