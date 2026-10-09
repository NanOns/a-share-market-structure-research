"""Actual frozen-source reparse plus a separate plain-text independent decoder."""
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.tdx_member_retro_r43 import EVIDENCE,parse_frozen_rows,normalized_frozen_rows,reparse_verification
from workbench_analysis.corrected_owner_replay import load,ref,checked,gzrows,gzwrite
from workbench_analysis.market_source_acquisition import write
OUT=ROOT/'docs/evidence/r4_3_r1_targeted_repair_20261009'

def checksum(rows):return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def independent_decode(snapshot):
    text={Path(b['path']).name:checked(ROOT,b).read_bytes().decode('gb18030',errors='replace') for b in snapshot['sources']}
    names={f[5]:f[0] for line in text['tdxzs.cfg'].splitlines() if len(f:=line.strip().split('|'))>=6 and f[5]}
    mapping={r['source_security_key'].upper():r for r in load(checked(ROOT,snapshot['identity_source']))['rows'] if r.get('identity_status')=='IDENTITY_BOUND'}
    edges=[];markets={'0':'SZ','1':'SH','2':'BJ'}
    for line in text['tdxhy.cfg'].splitlines():
        f=line.strip().split('|')
        if len(f)<3 or f[0] not in markets or not re.fullmatch('[0-9]{6}',f[1]) or not f[2]:continue
        code=f[2];key=markets[f[0]]+'.'+f[1]
        edges.append(('INDUSTRY',code,names.get(code,code),key,'tdxhy.cfg'))
    for kind,code,name,key,source in list(edges):
        parent=code[:5] if len(code)>5 else ''
        if parent and parent in names:edges.append((kind,parent,names[parent],key,'tdxhy.cfg:DERIVED_PARENT'))
    current=None
    for line in text['infoharbor_block.dat'].splitlines():
        if line.startswith('#'):
            parts=line[1:].split(',');label=parts[0]
            current=None
            if '_' in label and label.split('_',1)[0]=='GN':
                name=label.split('_',1)[1];code=parts[2].strip() if len(parts)>2 and parts[2].strip() else name
                current=(code,name)
            continue
        if current:
            for market,number in re.findall('([012])#([0-9]{6})',line):edges.append(('THEME',current[0],current[1],markets[market]+'.'+number,'infoharbor_block.dat'))
    seen=set();rows=[]
    for kind,code,name,key,source in edges:
        if (kind,code,key) in seen:continue
        seen.add((kind,code,key));ident=mapping.get(key);parent=source.endswith(':DERIVED_PARENT')
        rows.append(dict(sector_id=kind+':'+code,sector_type=kind,sector_code=code,sector_name=name,source_security_key=key,source=source,industry_level='PARENT_DERIVED' if parent else 'LEAF' if kind=='INDUSTRY' else 'CONCEPT',primary_industry_rank_eligible=not parent,security_id=ident['security_id'] if ident else None,identity_status='MAPPED' if ident else 'UNMAPPED_QUARANTINED',list_date=ident.get('list_date') if ident else None,delist_date=ident.get('delist_date') if ident else None))
    return sorted(rows,key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))

def main():
    snapshot=load(ROOT/EVIDENCE/'MEMBER_SNAPSHOT_S.json');original=gzrows(checked(ROOT,snapshot['memberships']))
    command=[sys.executable,'-c',"import sys,json;from pathlib import Path;sys.path.insert(0,str(Path.cwd()/'src'));from workbench_analysis.tdx_member_retro_r43 import reparse_verification;r=reparse_verification(Path.cwd());print(json.dumps({'acceptance':r['acceptance'],'relation_count':r['relation_count'],'member_digest':r['member_digest'],'normalized_row_digest':r['normalized_row_digest']}))"]
    run=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,encoding='utf8',env=os.environ|{'PYTHONIOENCODING':'utf8','PYTHONUTF8':'1'})
    assert run.returncode==0,run.stderr
    actual=parse_frozen_rows(ROOT,snapshot);second=parse_frozen_rows(ROOT,snapshot);independent=independent_decode(snapshot)
    assert actual==second==independent==normalized_frozen_rows(original)
    assert checksum(original)==snapshot['member_digest']
    tests=[];sandbox=Path('E:/codex_tmp/r43_r1_source_negative');sandbox.mkdir(parents=True,exist_ok=True)
    for b in [snapshot['memberships'],snapshot['identity_source']]+snapshot['sources']:
        p=sandbox/b['path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(checked(ROOT,b),p)
    for b in snapshot['sources']:
        p=sandbox/EVIDENCE/'latest_member_parse/T0002/hq_cache'/Path(b['path']).name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(checked(ROOT,b),p)
    # One actual frozen byte flipped, then restored; only isolated E: is touched.
    b=snapshot['sources'][0];p=sandbox/b['path'];raw=p.read_bytes();p.write_bytes(bytes([raw[0]^1])+raw[1:])
    try:parse_frozen_rows(sandbox,snapshot);raise AssertionError('SOURCE_BIT_CHANGE_ACCEPTED')
    except ValueError as exc:tests.append(dict(case='one_source_bit_changed',status='REJECTED',reason=str(exc)))
    p.write_bytes(raw)
    # Change a real canonical mapping while retaining the original input binding.
    b=snapshot['identity_source'];p=sandbox/b['path'];raw=p.read_bytes();identity=json.loads(raw);mapped=next(r for r in identity['rows'] if r.get('identity_status')=='IDENTITY_BOUND');mapped['security_id']='MUTATED_CANONICAL_MAPPING';p.write_text(json.dumps(identity),encoding='utf8')
    try:parse_frozen_rows(sandbox,snapshot);raise AssertionError('MEMBER_MAPPING_CHANGE_ACCEPTED')
    except ValueError as exc:tests.append(dict(case='one_member_mapping_changed',status='REJECTED',reason=str(exc)))
    p.write_bytes(raw)
    copy=sandbox/EVIDENCE/'latest_member_parse/T0002/hq_cache'/Path(snapshot['sources'][1]['path']).name;raw=copy.read_bytes();copy.write_bytes(bytes([raw[0]^1])+raw[1:])
    try:parse_frozen_rows(sandbox,snapshot);raise AssertionError('PARSE_COPY_CHANGE_ACCEPTED')
    except ValueError as exc:tests.append(dict(case='one_parse_copy_bit_changed',status='REJECTED',reason=str(exc)))
    samples=[]
    for kind in ['LEAF','PARENT_DERIVED','CONCEPT']:
        samples.extend(r for r in actual if r['industry_level']==kind and r['security_id'])
        samples=samples[:len(samples)-max(0,sum(r['industry_level']==kind for r in samples)-8)]
    groups=Counter(level for level,sector in {(r['industry_level'],r['sector_id']) for r in actual})
    coverage={kind:sorted({r['sector_id'] for r in actual if r['industry_level']==kind}) for kind in groups}
    receipt=load(OUT/'SOURCE_CAPTURE_REPARSE_VERIFICATION_V2.json');receipt.update(command=command,exit_code=run.returncode,stdout=run.stdout,stderr=run.stderr,independent_decoder=ref(ROOT,Path(__file__)),independent_normalized_digest=checksum(independent),independent_full_row_mismatches=0,repeat_digest=checksum(second),negative_cases=tests,coverage=coverage,samples=samples,source_sector_count=401,mapped_count=sum(r['security_id'] is not None for r in actual),unmapped_count=sum(r['security_id'] is None for r in actual),coverage_correction='111 non-parent source industries = 110 eligible leaf + unmapped T00; 22 derived parent; 268 concept. Old 110/23 statement is inaccurate.',snapshot_and_all_owner_bytes_changed=False)
    write(OUT/'SOURCE_CAPTURE_REPARSE_VERIFICATION_V2.json',receipt)
    failure=load(OUT/'R43_SOURCE_REPARSE_FAILURE_REPRODUCTION.json')
    write(OUT/'R43_SOURCE_REPARSE_CONTRADICTION_AND_FIX_V2.json',dict(contract_id='R43_P0_A_REAL_SOURCE_REPAIR_V2',failure=ref(ROOT,OUT/'R43_SOURCE_REPARSE_FAILURE_REPRODUCTION.json'),legacy_original_actual_exit_code=failure['legacy_verifier']['exit_code'],fresh_capture_before_fix_actual_exit_code=failure['exit_code'],after_fix=ref(ROOT,OUT/'SOURCE_CAPTURE_REPARSE_VERIFICATION_V2.json'),executed_code=ref(ROOT,ROOT/'src/workbench_analysis/tdx_member_retro_r43.py'),scope='Shared complete pure normalization, explicit additive view of frozen legacy10 S; original hash and all business classifications retained',snapshot_identity_preserved=snapshot['membership_snapshot_id'],snapshot_digest_preserved=snapshot['member_digest'],normalized_view_digest=checksum(actual),owner_rebuild_required=False,independent_external_signed=False,acceptance='SOURCE_REPARSE_ENGINEERING_PASS_EXTERNAL_REVIEW_PENDING'))
    print(json.dumps(dict(status='PASS',relation_count=len(actual),original_digest=checksum(original),normalized_digest=checksum(actual),coverage=groups,negative_cases=len(tests),samples=len(samples))))

if __name__=='__main__':main()
