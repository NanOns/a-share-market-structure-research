"""Bounded official lifecycle capture plus exact current-day TDX byte freezing."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import unicodedata
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup, UnicodeDammit
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json,sha
from build_v4_08_membership_prerequisite import read_frozen_file

def now():return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def normalized(text):return ''.join(unicodedata.normalize('NFKC',text).split())

def capture():
    manifest_path=ROOT/'reports/v4_08/audit_inputs/V4_08_R3_LIFECYCLE_CAPTURE_MANIFEST.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('runtime_authorized') is not False or manifest.get('scope')!='R3_IDENTITY_AUDIT_ONLY':
        raise ValueError('LIFECYCLE_CAPTURE_MANIFEST_NOT_AUDIT_ONLY')
    frozen_path=manifest.get('source_contract_path','')
    if not frozen_path.startswith('reports/v4_08/audit_inputs/'):
        raise ValueError('LIFECYCLE_SOURCE_CONTRACT_NOT_AUDIT_ONLY')
    frozen_bytes=(ROOT/frozen_path).read_bytes()
    if sha(frozen_bytes)!=manifest.get('source_contract_sha256') or json.loads(frozen_bytes)!=manifest.get('source_contract'):
        raise ValueError('LIFECYCLE_SOURCE_CONTRACT_BYTES_MISMATCH')
    config=manifest['source_contract']
    capture_id=datetime.now(timezone.utc).strftime('capture_%Y%m%dT%H%M%SZ')
    directory=ROOT/config['raw_evidence_root']/capture_id
    directory.mkdir(parents=True,exist_ok=False)
    def get(source):
        item=dict(source);item['request_started_at']=now()
        try:
            if urlparse(source['url']).hostname not in config['allowed_hosts']:raise ValueError('host not approved')
            with requests.get(source['url'],headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.sse.com.cn/' if 'sse.com' in source['url'] else 'https://www.szse.cn/'},timeout=config['timeout_seconds'],stream=True,allow_redirects=False) as response:
                item['http_status']=response.status_code
                parts=[];size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>config['maximum_response_bytes']:raise ValueError('response exceeds source budget')
                    parts.append(chunk)
                data=b''.join(parts);item['observed_at']=now()
                suffix='.pdf' if data.startswith(b'%PDF') else '.xlsx' if data.startswith(b'PK') else '.html'
                path=directory/(source['id']+suffix);atomic_bytes(path,data)
                item.update(path=path.relative_to(ROOT).as_posix(),sha256=sha(data),byte_count=len(data))
                if response.status_code!=200:raise ValueError('HTTP_'+str(response.status_code))
                if suffix=='.pdf':
                    # Bundled runtime supports immutable PDF text extraction; no dependency installation.
                    python=Path(r'C:\Users\lps\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
                    proc=subprocess.run([str(python),'-c','import sys,pypdf;print("\\n".join(p.extract_text() or "" for p in pypdf.PdfReader(sys.argv[1]).pages))',str(path)],text=True,capture_output=True,encoding='utf-8',errors='replace',timeout=45,env={**__import__('os').environ,'PYTHONIOENCODING':'utf-8'})
                    if proc.returncode:raise ValueError('PDF_TEXT_EXTRACTION_FAILED')
                    text=proc.stdout
                elif suffix=='.xlsx':
                    from openpyxl import load_workbook
                    book=load_workbook(io.BytesIO(data),read_only=True,data_only=True)
                    text='\n'.join('\t'.join('' if x is None else str(x) for x in row) for sheet in book for row in sheet.iter_rows(values_only=True))
                    book.close()
                else:
                    text=BeautifulSoup(UnicodeDammit(data).unicode_markup or '', 'html.parser').get_text(' ',strip=True)
                extracted=directory/(source['id']+'.txt');atomic_bytes(extracted,text.encode('utf-8'))
                item.update(extracted_text_path=extracted.relative_to(ROOT).as_posix(),extracted_text_sha256=sha(extracted.read_bytes()))
                norm=normalized(text);item['expected_phrase_checks']={phrase:normalized(phrase) in norm for phrase in source['expected']}
                item['status']='PASS_CAPTURE' if all(item['expected_phrase_checks'].values()) else 'CAPTURED_EXPECTED_PHRASE_MISSING'
        except Exception as error:
            item['status']='BLOCKED_CAPTURE';item['error']=str(error)[:200]
        return item
    if len(config['sources'])>config['maximum_requests']:raise ValueError('request budget exceeded')
    with ThreadPoolExecutor(max_workers=4) as pool:sources=list(pool.map(get,config['sources']))
    total=sum(x.get('byte_count',0) for x in sources)
    if total>config['maximum_total_response_bytes']:raise ValueError('total capture budget exceeded')
    atomic_json(ROOT/'reports/v4_08/V4_08_R3_OFFICIAL_LIFECYCLE_SOURCE_CAPTURE.json',{'contract_id':config['source_contract_id'],'capture_id':capture_id,'sources':sources,'request_count':len(sources),'total_bytes':total,'complete_observed_at':max(x.get('observed_at',x['request_started_at']) for x in sources),'status':'CAPTURE_COMPLETED_WITH_PER_SOURCE_GATES'})
    frozen={};files=[]
    for relative in ['T0002/hq_cache/tdxhy.cfg','T0002/hq_cache/tdxzs.cfg','T0002/hq_cache/infoharbor_block.dat']:
        data,evidence=read_frozen_file(Path('D:/new_tdx')/relative)
        path=directory/'tdx'/relative
        atomic_bytes(path,data);frozen[relative]=sha(data)
        files.append({'source_relative_path':relative,'frozen_path':path.relative_to(ROOT).as_posix(),'sha256':sha(data),'byte_count':len(data),'observed_at':evidence['observed_at']})
    complete=max(x['observed_at'] for x in files)
    atomic_json(ROOT/'reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json',{'contract_id':'V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE_V1','capture_id':capture_id,'status':'PASS_EXACT_DAY_BYTES_FROZEN','target_trade_date':'2026-09-30','complete_observed_at':complete,'system_available_at':now(),'source_bytes_digest':sha(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()),'source_file_digests':frozen,'files':files,'provider_available_at_basis':'PROJECT_FIRST_OBSERVED_PROVIDER_BYTES','provider_available_at':complete,'membership_asof_basis':'PROJECT_FIRST_OBSERVED_SOURCE_STATE','membership_asof_date':'2026-09-30','filesystem_mtime_used_as_availability':False,'tdx_root_write_count':0,'daily_capture_reused_from_previous_day':False,'external_policy_disposition':'V4_08_R2_INDEPENDENT_EXTERNAL_AUDIT_20260930 sections 8/9'})
    print(json.dumps({'source_results':{x['id']:x['status'] for x in sources},'tdx_complete_observed_at':complete},ensure_ascii=False))

def reextract():
    path=ROOT/'reports/v4_08/V4_08_R3_OFFICIAL_LIFECYCLE_SOURCE_CAPTURE.json'
    report=json.loads(path.read_text(encoding='utf-8'))
    for item in report['sources']:
        if item.get('http_status')!=200 or not item.get('path') or item['path'].lower().endswith('.pdf'):continue
        data=(ROOT/item['path']).read_bytes()
        if sha(data)!=item['sha256']:raise ValueError('immutable raw source hash changed')
        text=BeautifulSoup(UnicodeDammit(data).unicode_markup or '', 'html.parser').get_text(' ',strip=True)
        dest=(ROOT/item['path']).with_suffix('.txt');atomic_bytes(dest,text.encode('utf-8'))
        item.update(extracted_text_path=dest.relative_to(ROOT).as_posix(),extracted_text_sha256=sha(dest.read_bytes()))
        item['expected_phrase_checks']={x:normalized(x) in normalized(text) for x in item['expected']}
        item['status']='PASS_CAPTURE' if all(item['expected_phrase_checks'].values()) else 'CAPTURED_EXPECTED_PHRASE_MISSING'
        item.pop('error',None)
    report['extraction_corrected_from_exact_frozen_bytes']=True
    atomic_json(path,report)
    print(json.dumps({x['id']:x['status'] for x in report['sources']}))

if __name__=='__main__':
    reextract() if '--reextract' in sys.argv else capture()
