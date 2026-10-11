"""Restore exact V4 FEP fixture bytes only into the isolated R4 worktree."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ORIGIN=Path('G:/codex work/大A交易').resolve()
OUT=ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b'

def main():
    if ROOT==ORIGIN or not ROOT.is_relative_to(Path('G:/codex work').resolve()):raise ValueError('ISOLATED_G_FIXTURE_DESTINATION_REQUIRED')
    records={}
    def digest(raw):return hashlib.sha256(raw).hexdigest()
    def store(rel,raw,origin,expected=None):
        target=(ROOT/rel).resolve()
        if not target.is_relative_to(ROOT):raise ValueError('FIXTURE_DESTINATION_ESCAPE')
        actual=digest(raw)
        if expected and actual!=expected:raise ValueError('EXACT_FIXTURE_DIGEST_MISMATCH:'+rel)
        target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix(target.suffix+'.r4tmp');tmp.write_bytes(raw);tmp.replace(target)
        records[rel]=dict(path=rel,sha256=actual,bytes=len(raw),origin=origin)
    entry=json.loads((ORIGIN/'reports/fep_e1/ENTRY_BASELINE.json').read_bytes())
    for ref in entry['protected']:
        raw=subprocess.check_output(['git','show',entry['baseline']+':'+ref['path']],cwd=ROOT)
        variants=[(raw,'FROZEN_GIT_BLOB'),(raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'),'FROZEN_GIT_CRLF_WORKTREE_RENDER')]
        source=ORIGIN/ref['path']
        if source.exists():variants.append((source.read_bytes(),'EXACT_ORIGINAL_READ_ONLY_COPY'))
        matched=[(b,label) for b,label in variants if len(b)==ref['bytes'] and digest(b)==ref['sha256']]
        if not matched:raise ValueError('FROZEN_FIXTURE_UNAVAILABLE:'+ref['path'])
        raw,label=matched[0];store(ref['path'],raw,label,ref['sha256'])
    names=['reports/fep_e1/ENTRY_BASELINE.json']
    names+=['reports/fep_e1_r2_final/'+n+'.json' for n in ('OWNER_ROW_PROJECTION','ENGINEERING_OBSERVATION','ENGINEERING_SNAPSHOT','ENGINEERING_MAPPING_REGISTRY')]
    names+=['migrations/'+n for n in ('v4_16_r24_real_shadow_v1.sql','v4_16_settlement_queue_v2.sql','v4_16_real_shadow_integrity_v2.sql')]
    for rel in names:store(rel,(ORIGIN/rel).read_bytes(),'EXACT_ORIGINAL_READ_ONLY_COPY')
    contract=json.loads((ROOT/'config/fep_feature_owner_contract_v1.json').read_bytes())
    refs=[v for v in contract.values() if isinstance(v,dict) and v.get('path') and v.get('sha256')]
    snapshot=json.loads((ROOT/'reports/fep_e1_r2_final/ENGINEERING_SNAPSHOT.json').read_bytes())
    def bindings(value):
        if isinstance(value,dict):
            if value.get('path') and value.get('sha256'):refs.append(value)
            else:
                for item in value.values():bindings(item)
        elif isinstance(value,list):
            for item in value:bindings(item)
    bindings(snapshot['dependency_manifest']);bindings(json.loads((ROOT/'reports/fep_e1_r2_final/ENGINEERING_MAPPING_REGISTRY.json').read_bytes()))
    for ref in refs:
        if ref['path'] in records:
            if records[ref['path']]['sha256']!=ref['sha256']:raise ValueError('CONFLICTING_VERSIONED_FIXTURE:'+ref['path'])
            continue
        store(ref['path'],(ORIGIN/ref['path']).read_bytes(),'EXACT_ORIGINAL_READ_ONLY_COPY',ref['sha256'])
    target=OUT/'R4_FEP_E1_FIXTURE_MANIFEST.json';tmp=target.with_suffix('.tmp')
    tmp.write_text(json.dumps(dict(contract_id='R4_FEP_E1_VERSIONED_REPLAY_FIXTURES_R1',protected_baseline=entry['baseline'],records=list(records.values()),scope='Required exact V4 FEP fixtures only; no legacy database, formula changes or production grants'),ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(target)
    print(json.dumps(dict(fixtures=len(records))))
if __name__=='__main__':main()
