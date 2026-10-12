"""Preserve inherited independent audit items under the user-authorized total gate."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('G:/codex work/大A交易')
OUT=ROOT/'docs/audits/v4_full_closeout_20261012'
CARD=Path('D:/Users/lps/Desktop/阶段任务/V4_85E9A881E799BFE58D_AEE6B4AAE6B6_8EE68394E4A788E6A2_B8E6A189E88C80E4BB8A.md')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sources=[SOURCE/'docs/audits/full_system_repair_r3_20261011_239fb9b5/EFFECTIVE_AUDIT_ITEMS_R3.json',
             SOURCE/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/EFFECTIVE_AUDIT_ITEMS_R4.json',
             ROOT/'docs/audits/s1b_20261012/AUDIT_ITEMS.json']
    issues={}
    bindings=[]
    for source in sources:
        if not source.exists():continue
        raw=source.read_bytes();data=json.loads(raw)
        bindings.append(dict(path=str(source),sha256=hashlib.sha256(raw).hexdigest()))
        for item in data.get('issues',[])+data.get('additional_items',[])+data.get('items',[]):
            key=item.get('audit_item_id') or item.get('id')
            if not key:raise ValueError('INHERITED_AUDIT_ITEM_ID_MISSING')
            row=issues.setdefault(key,dict(id=key,history=[]))
            row['history'].append(dict(source=str(source),item=item))
    for key in ('ALL_CONSUMERS','PG_ONLY','FOCUS_FORWARD_SETTLEMENT','EXACT56_FIELDS','LEGAL_FULL_REGRESSION','SIX_UI_WINDOWS','CAPACITY_ROLLBACK','PRODUCTION_ROLE_AND_CUTOVER'):
        issues.setdefault(key,dict(id=key,history=[]))
    rows=[]
    for key,item in sorted(issues.items()):
        item.update(status='IN_PROGRESS_NOT_ACCEPTED',independent_acceptance=True,
                    stage_stop_policy='Continue every independent executable work package; no production promotion until all objective hard gates pass')
        rows.append(dict(id=key,prior_status=' | '.join(str(x['item'].get('status','UNKNOWN')) for x in item['history']),
                         current_status=item['status'],independent_acceptance=True,source_records=len(item['history'])))
    (OUT/'AUDIT_ITEMS_PRESERVED.json').write_text(json.dumps(dict(contract_id='V4_ONE_ROUND_FULL_CLOSEOUT_R1_20261012',
        task_card_sha256=hashlib.sha256(CARD.read_bytes()).hexdigest(),production_cutover_user_authorized=True,
        input_bindings=bindings,items=list(issues.values()),full_acceptance=False),ensure_ascii=False,indent=2),encoding='utf8')
    with (OUT/'REMAINING_ITEMS_WORKING.csv').open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(preserved_independent_items=len(rows),final_delivery=False)))

if __name__=='__main__':main()
