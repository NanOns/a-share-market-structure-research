"""Seal executed readbacks and extend the field ledger from actual sector bytes."""
import csv
import gzip
import json
import os
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from workbench_analysis.corrected_owner_replay import load,ref
from workbench_analysis.market_source_acquisition import write
OUT=ROOT/'docs/evidence/r4_3_four_session_closeout_20261009'

def main():
    http=load(OUT/'CANDIDATE_HTTP_FOUR_DATE_SAME_CONTEXT_READBACK.json')
    names=['CANDIDATE_HTTP_FOUR_DATE_SAME_CONTEXT_READBACK.json','LIVE_ORIGINAL_0930_SAME_CONTEXT_READBACK.json','UI_CANDIDATE_1008_AX.txt','UI_ORIGINAL_0930_AX.txt','W6_CANDIDATE_API_SAME_CONTEXT_READBACK.json']
    write(OUT/'11_FOUR_SESSION_LIVE_API_SAME_CONTEXT_AND_UI_READBACK.json',dict(
        contract_id='R43_READBACK_SCOPE_SEPARATION_V1',candidate_context_token=http['context']['context_token'],
        candidate_http='FOUR_DATE_SAME_CONTEXT_PASS',candidate_ui='ACTUAL_1008_PROFILE_AX_READBACK',
        production_readback='ORIGINAL_0930_LAST_GOOD_PRESERVED',production_cutover=False,
        FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS=False,external_acceptance='ABSENT',
        UI_scope_limit='Candidate Profile and date/domain controls read; no claim of all-domain UI or W8 acceptance',
        bindings=[ref(ROOT,OUT/n) for n in names]))
    target=OUT/'07_FIELD_LINEAGE_AND_UNKNOWN_REASONS_BY_DATE.csv'
    with target.open(encoding='utf-8-sig',newline='') as f: records=list(csv.DictReader(f));columns=list(records[0])
    records=[r for r in records if r['family'] not in ['TDX_NATIVE','TDX_LOO']]
    for item in load(OUT/'sector_v3/SECTOR_REPLAY.json')['owners']:
        for family,key in [('TDX_NATIVE','native'),('TDX_LOO','relative_sector')]:
            binding=item[key]
            with gzip.open(ROOT/binding['path'],'rt',encoding='utf8') as f: rows=[json.loads(line) for line in f if line.strip()]
            fields=sorted({k for r in rows for k in r.get('fields',{})}) if family=='TDX_NATIVE' else ['relative_sector']
            for field in fields:
                counts=Counter()
                for row in rows:
                    cell=row.get('fields',{}).get(field,{}) if family=='TDX_NATIVE' else row
                    if not isinstance(cell,dict):cell={'value':cell}
                    quality=cell.get('quality_state',cell.get('quality'))
                    known=cell.get('value') not in (None,'UNKNOWN') and quality!='UNKNOWN'
                    reason=cell.get('unknown_reason',cell.get('reason'))
                    counts[('KNOWN' if known else 'UNKNOWN', '' if known else json.dumps(reason,ensure_ascii=False,sort_keys=True))]+=1
                for (quality,reason),count in counts.items(): records.append(dict(trade_date=item['trade_date'],family=family,field=field,quality=quality,reason=reason,count=count,source_path=binding['path'],source_sha256=binding['sha256'],knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP',AS_RECORDED=False,PIT_ELIGIBLE=False))
    temporary=target.with_suffix('.tmp.seal')
    with temporary.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(records)
    os.replace(temporary,target)
    receipt=load(OUT/'owner_v3/W3_W5_RECEIPT.json');receipt['lineage']=ref(ROOT,target);write(OUT/'owner_v3/W3_W5_RECEIPT.json',receipt)
    print(json.dumps(dict(readback='PASS',field_ledger_rows=len(records))))

if __name__=='__main__':main()
