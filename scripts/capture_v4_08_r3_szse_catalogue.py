"""Complete the official target-day A-stock catalogue with bounded pagination."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import threading
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json,sha

def main():
    contract=json.loads((ROOT/'config/v4_08_r3_lifecycle_source_contract_v1.json').read_text(encoding='utf-8'))
    capture=json.loads((ROOT/'reports/v4_08/V4_08_R3_OFFICIAL_LIFECYCLE_SOURCE_CAPTURE.json').read_text(encoding='utf-8'))
    first=next(x for x in capture['sources'] if x['id']=='SZSE_stock_list')
    raw=(ROOT/first['path']).read_bytes();metadata=json.loads(raw)[0]['metadata']
    pages=metadata['pagecount'];total=metadata['recordcount']
    if pages>contract['maximum_catalogue_pages']:raise ValueError('catalogue pagination exceeds source budget')
    target=metadata['subname'].strip()
    if target!=contract['target_date']:raise ValueError('official catalogue is not dated at target')
    directory=(ROOT/first['path']).parent/'szse_catalogue';directory.mkdir(exist_ok=True)
    lock=threading.Lock();byte_total=len(raw)
    def page(number):
        nonlocal byte_total
        url='https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1110&TABKEY=tab1&tab1PAGENO='+str(number)
        if number==1:data=raw;observed=first['observed_at']
        else:
            with requests.get(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.szse.cn/'},timeout=contract['timeout_seconds'],stream=True,allow_redirects=False) as response:
                response.raise_for_status();parts=[];size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>contract['maximum_response_bytes']:raise ValueError('page byte budget exceeded')
                    parts.append(chunk)
                data=b''.join(parts)
                observed=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            with lock:
                byte_total+=len(data)
                if byte_total>contract['maximum_total_response_bytes']:raise ValueError('catalogue total byte budget exceeded')
        document=json.loads(data)[0];m=document['metadata']
        if m['pageno']!=number or m['recordcount']!=total or m['subname'].strip()!=target:raise ValueError('official pagination identity changed during capture')
        path=directory/f'page_{number:03}.json';atomic_bytes(path,data)
        return {'page_no':number,'url':url,'path':path.relative_to(ROOT).as_posix(),'sha256':sha(data),'byte_count':len(data),'observed_at':observed,'row_count':len(document['data'])},document['data']
    with ThreadPoolExecutor(max_workers=contract['maximum_parallel_requests']) as pool:results=list(pool.map(page,range(1,pages+1)))
    records=[row for _,rows in results for row in rows]
    codes=[row['agdm'] for row in records]
    if len(codes)!=total or len(set(codes))!=total:raise ValueError('official catalogue is incomplete or duplicate across pages')
    report={'contract_id':'V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE_V1','status':'PASS_COMPLETE_TARGET_DAY_SZSE_CATALOGUE','target_trade_date':target,'complete_observed_at':max(x['observed_at'] for x,_ in results),'official_record_count':total,'page_count':pages,'network_request_count':pages-1,'maximum_allowed_pages':contract['maximum_catalogue_pages'],'pages':[x for x,_ in results],'records':records,'source_contract_sha256':sha((ROOT/'config/v4_08_r3_lifecycle_source_contract_v1.json').read_bytes())}
    atomic_json(ROOT/'reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json',report)
    print(json.dumps({'status':report['status'],'record_count':total,'page_count':pages,'complete_observed_at':report['complete_observed_at']}))

if __name__=='__main__':main()
