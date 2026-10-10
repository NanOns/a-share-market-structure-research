"""Stdlib-only verify of the R4 extracted review package; all output on G:."""
from pathlib import Path
import hashlib, json, os, subprocess, sys

def main():
    for key in ('TMP','TEMP','TMPDIR'):os.environ[key]='G:/codex_tmp'
    root=Path(sys.argv[1]).resolve()
    if root.drive.upper()!='G:':raise ValueError('G_ONLY_REVIEW_WORKSPACE_REQUIRED')
    d=root/'docs/evidence/v4_current_snapshot_r4_20261010'
    manifest=json.loads((d/'08_EVIDENCE_MANIFEST_SHA256.json').read_bytes())
    bindings=manifest['files']+manifest['sources'];errors=[]
    for binding in bindings:
        p=(root/binding['path']).resolve()
        if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=binding['sha256']:
            errors.append(binding['path'])
    if errors:raise ValueError('PACKAGE_BYTES_MISMATCH:'+repr(errors))
    outputs=Path('G:/codex_tmp/test_temp/r4_offline_outputs');outputs.mkdir(parents=True,exist_ok=True)
    mini=d/'06_EXTERNAL_RECHECK_MINIPACK';b=d/'02_B_SECTOR'
    runs=[]
    for script,source,result in [(mini/'LOO_SAMPLE_ORACLE.py',mini/'LOO_SAMPLE_INPUT.json.gz',outputs/'loo.json'),
                                 (mini/'PULSE_ORACLE.py',mini/'PULSE_INPUT.json',outputs/'pulse.json'),
                                 (b/'B_SECTOR_ORACLE.py',b/'B_SECTOR_READINESS_CANDIDATE_INPUT.json',outputs/'sector.json')]:
        p=subprocess.run([sys.executable,'-B',str(script),str(source),str(result)],capture_output=True,text=True,encoding='utf8')
        runs.append(dict(script=script.relative_to(root).as_posix(),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode:raise ValueError('OFFLINE_ORACLE_FAILED:'+str(script))
    actual=json.loads((b/'B_SECTOR_READINESS_CANDIDATE_OUTPUT.json').read_bytes())['rows']
    expected=json.loads((outputs/'sector.json').read_bytes())['rows']
    sector_errors=[(a['entity_id'],k) for a,e in zip(actual,expected) for k,v in e.items() if a.get(k)!=v]
    if len(actual)!=len(expected) or sector_errors:raise ValueError('OFFLINE_SECTOR_DIFF:'+repr(sector_errors))
    receipt=dict(byte_checks=len(bindings),byte_errors=0,oracles=runs,sector_rows=len(actual),sector_comparisons=sum(len(e) for e in expected),sector_errors=0,
                 scope='Stdlib on clean extracted package; no business imports or TDX access; not external auditor acceptance')
    (outputs/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
