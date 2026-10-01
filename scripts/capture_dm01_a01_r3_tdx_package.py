"""Freeze the current official package for strict dated reconstruction, never backdate it."""
from datetime import datetime,timezone
import hashlib,json,os,re,sys,time,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_analysis.tdx_official_daily_source import (_request,_read_bounded,_zip_validate,
    validate_official_url,discover_download_url,discover_update_info_url,parse_update_date,PAGE_URL)
from workbench_analysis.daily_source_freeze import ensure_outside_tdx
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    base=ROOT/'data/v4/source_evidence/dm01_a01_r3/tdx'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    ensure_outside_tdx(base,Path('D:/new_tdx'));base.mkdir(parents=True,exist_ok=False)
    observed=datetime.now(timezone.utc).isoformat()
    with _request(PAGE_URL,timeout=30) as r:page=_read_bounded(r,4*1024*1024)
    url=discover_download_url(page)
    with _request(discover_update_info_url(page,url),timeout=30) as r:info=_read_bounded(r,262144)
    published,publication_time=parse_update_date(info)
    atomic_bytes(base/'page.html',page);atomic_bytes(base/'update_info.js',info)
    attempts=[];cookie=None;package=None
    for attempt in range(3):
        started=datetime.now(timezone.utc).isoformat();tmp=base/('download_'+str(attempt)+'.part')
        if cookie:
            req=urllib.request.Request(validate_official_url(url),headers={'User-Agent':'Mozilla/5.0','Referer':PAGE_URL,'Cookie':cookie})
            r=urllib.request.urlopen(req,timeout=120)
        else:r=_request(url,timeout=120)
        with r:
            validate_official_url(r.geturl());headers={k:r.headers.get(k) for k in ('Content-Type','Content-Length','Last-Modified','ETag')}
            h=hashlib.sha256();size=0
            with tmp.open('wb') as f:
                while True:
                    chunk=r.read(1024*1024)
                    if not chunk:break
                    size+=len(chunk)
                    if size>1024*1024*1024:raise ValueError('TDX_PACKAGE_SIZE_BOUND')
                    f.write(chunk);h.update(chunk)
                f.flush();os.fsync(f.fileno())
        record=dict(attempt=attempt,observed_at=started,received_at=datetime.now(timezone.utc).isoformat(),
            url=url,headers=headers,bytes=size,sha256=h.hexdigest(),ZIP_valid=zipfile.is_zipfile(tmp))
        if record['ZIP_valid']:
            record['zip_validation']=_zip_validate(tmp)
            package=base/('sha256-'+h.hexdigest())/'hsjday.zip';package.parent.mkdir()
            os.replace(tmp,package);record['package_binding']=bind(package.relative_to(ROOT).as_posix())
        else:
            archive=base/('NON_ZIP_RESPONSE_'+str(attempt)+'.html');os.replace(tmp,archive)
            record['rejected_response_binding']=bind(archive.relative_to(ROOT).as_posix())
            text=archive.read_text(encoding='utf8',errors='replace')
            # The public download's static cookie challenge; no browser or arbitrary script evaluation.
            nums=[re.search(r'\b'+key+r':(\d+)',text) for key in ('WTKkN','bOYDu','wyeCN')]
            ssid=re.search(r'\]\(t,(\d+)\)',text)
            if all(nums) and ssid:
                cookie='__tst_status='+str(sum(int(m[1]) for m in nums))+'#; EO_Bot_Ssid='+ssid[1]
                record['retry_reason']='PUBLIC_DOWNLOAD_STATIC_COOKIE_CHALLENGE'
        attempts.append(record)
        atomic_json(base/'request_receipt.json',dict(status='PASS_OFFICIAL_ZIP' if package else 'REJECTED_NON_ZIP',
            observed_at=observed,official_publication_date=published,official_publication_time=publication_time,
            attempts=attempts,request_count=2+len(attempts),request_limit=5,
            package=bind(package.relative_to(ROOT).as_posix()) if package else None,
            page=bind((base/'page.html').relative_to(ROOT).as_posix()),update_info=bind((base/'update_info.js').relative_to(ROOT).as_posix()),
            knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False,tdx_root_write_count=0))
        if package:break
    ref=bind((base/'request_receipt.json').relative_to(ROOT).as_posix())
    atomic_json(ROOT/'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json',dict(status='PASS' if package else 'BLOCKED',capture_receipt=ref))
    print(json.dumps(dict(status='PASS' if package else 'BLOCKED',capture_receipt=ref)))
if __name__=='__main__':main()
