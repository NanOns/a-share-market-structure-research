"""Recover exact missing inputs named by raw failures, without mutating originals."""
import csv
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import sys
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.hydrate_r4_r3_scope_fixtures import ROOT,SOURCE,OUT,sha

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ledger',type=Path,default=OUT/'V4_BASELINE_FULL_GUARDED_20261011T103651_INDEPENDENT_NODES.csv')
    parser.add_argument('--transitive-json',action='store_true')
    args=parser.parse_args();ledger=args.ledger.resolve()
    if not ledger.is_relative_to(OUT.resolve()):raise ValueError('RAW_FAILURE_LEDGER_SCOPE_REQUIRED')
    requested={}
    for row in csv.DictReader(ledger.open(encoding='utf8')):
        if row['category']!='FROZEN_FIXTURE_ABSENT':continue
        text=row['raw_message'].replace('\\\\','/').replace('\\','/')
        for match in re.finditer(re.escape(str(ROOT).replace('\\','/'))+r'/([^\n\r\'\"]+)',text):
            rel=match.group(1)
            # Tracebacks contain code lines too; only concrete existing source
            # files under the read-only original workspace are copy candidates.
            source=(SOURCE/rel).resolve()
            if source.is_file() and source.is_relative_to(SOURCE.resolve()):requested.setdefault(rel,[]).append(row['nodeid'])
    if args.transitive_json:
        pending=list(requested);visited=set()
        def references(value):
            if isinstance(value,dict):
                if isinstance(value.get('path'),str):yield value['path']
                for child in value.values():yield from references(child)
            elif isinstance(value,list):
                for child in value:yield from references(child)
        while pending:
            rel=pending.pop()
            if rel in visited:continue
            visited.add(rel);source=(SOURCE/rel).resolve()
            if source.suffix!='.json':continue
            try:value=json.loads(source.read_bytes())
            except (ValueError,UnicodeDecodeError):continue
            for name in references(value):
                child=(SOURCE/name).resolve()
                if child.is_file() and child.is_relative_to(SOURCE.resolve()):
                    child_rel=child.relative_to(SOURCE).as_posix()
                    if child_rel not in requested:
                        requested[child_rel]=requested[rel];pending.append(child_rel)
    records=[]
    for rel,nodes in sorted(requested.items()):
        source=(SOURCE/rel).resolve();target=(ROOT/rel).resolve()
        if not target.is_relative_to(ROOT):raise ValueError('FAILED_FIXTURE_TARGET_ESCAPE')
        before=sha(source)
        if target.exists():status='PRESENT_IDENTICAL' if sha(target)==before else 'PRESENT_DIFFERENT_PRESERVED'
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.open('rb') as origin,target.open('xb') as dest:
                while block:=origin.read(65536):dest.write(block)
            if sha(target)!=before:raise ValueError('COPY_DIGEST_MISMATCH')
            status='COPIED_MISSING_FROM_FAILURE'
        after=sha(source)
        if before!=after:raise ValueError('SOURCE_CHANGED_DURING_READ')
        records.append(dict(path=rel,nodes=sorted(set(nodes)),bytes=source.stat().st_size,
                            source_sha256_before=before,source_sha256_after=after,target_sha256=sha(target),status=status))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    (OUT/('FAILURE_INPUT_COPY_'+stamp+'.json')).write_text(json.dumps(dict(
        contract_id='R4_R3_FAILED_INPUT_RECOVERY_R1',input_ledger=str(ledger.relative_to(ROOT)),records=records,
        source_ledger_sha256=sha(ledger),production_or_source_mutations=0),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(requested=len(requested),copied=sum(r['status']=='COPIED_MISSING_FROM_FAILURE' for r in records))))

if __name__=='__main__':main()
