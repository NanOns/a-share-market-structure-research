"""Stable UTF-8/BOM CSV from one immutable, validated reader."""
import csv,io

def stock_csv(reader,query):
    params=dict(query);params.pop('offset',None);params['limit']=200
    stream=io.StringIO(newline='');writer=csv.writer(stream)
    writer.writerow(['身份','名称','代码','截至日','收盘价','研究情景','资格判断','主行业'])
    offset=0;seen=set()
    while True:
        page=reader.query('stocks',dict(params,offset=offset),summary=True)
        for r in page['items']:
            if r['entity_id'] in seen:raise ValueError('CSV_DUPLICATE_IDENTITY')
            seen.add(r['entity_id']);fields=r['fields']
            writer.writerow([r['entity_id'],r['display_name'],r['symbol'],r['trade_date'],*[fields.get(k,{}).get('value') for k in ('close','scenario','final_eligibility','primary_industry')]])
        offset+=len(page['items'])
        if not page['has_next']:break
        if not page['items']:raise ValueError('CSV_MISSING_PAGE')
    if len(seen)!=page['total']:raise ValueError('CSV_COUNT_MISMATCH')
    return ('\ufeff'+stream.getvalue()).encode('utf8'),len(seen)
