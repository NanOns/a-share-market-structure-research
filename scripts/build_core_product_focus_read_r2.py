"""Rebuild only the affected Focus read projection from frozen real D2 owners."""
from pathlib import Path
import json,gzip,sys,hashlib,os
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from focus_tracker.core_product_focus_r2 import enriched_project,CONTRACT
from focus_tracker.v4_native_core_adapter import AcceptedPaths
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from scripts.audit_core_algo_ui_r2 import load,sha,write,OUT

def ref(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)

def main():
    hp=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';before=hp.read_bytes();h=json.loads(before);day=h['accepted_trade_date']
    old_ref=h['owners'][day]['forward'];old=load(ROOT/old_ref['path']);days={};sources={}
    for d in h['published_sessions']:
        r=h['owners'][d]['focus'];p=ROOT/r['path'];assert sha(p)==r['sha256'];sources[d]=r
        days[d]=load(p)['rows']
    new=enriched_project(days,AcceptedPaths(ROOT,old['source_bindings']))
    metadata={k:v for k,v in old.items() if k not in ('episodes','events','source_bindings','contract_id')}
    new.update(metadata,contract_id='CORE_PRODUCT_FOCUS_READ_R2',T0=day,source_bindings=old['source_bindings'],
        d2_source_bindings=sources,legacy_forward_source=old_ref,validity_bridge_contract_id=CONTRACT,
        read_scope='CORRECTED_FOCUS_READ_PROJECTION; NOT_VALIDATION_COHORT',external_acceptance='NOT_GRANTED')
    for e in new['episodes']:
        original=next((a for a in old['episodes'] if a['episode_id']==e['episode_id']),None)
        if original:e['research_mainline_context']=original.get('research_mainline_context')
        for key in ('AS_RECORDED','PIT_ELIGIBLE','member_set_asof','knowledge_lineage'):
            if key in old:e[key]=old[key]
    out=ROOT/'data/v4/core_product_focus_read_r2'/sha(hp);out.mkdir(parents=True,exist_ok=True)
    payload=out/'FOCUS.json.gz';tmp=payload.with_suffix('.tmp')
    tmp.write_bytes(gzip.compress(json.dumps(new,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode(),mtime=0));os.replace(tmp,payload)
    manifest=dict(contract_id='CORE_PRODUCT_FOCUS_READ_MANIFEST_R2',T0=day,head=ref(hp),projection=ref(payload),
        source_bindings=sources,legacy_forward=old_ref,implementation=ref(ROOT/'src/focus_tracker/core_product_focus_r2.py'),
        focus_write=False,PIT_ELIGIBLE=False,external_acceptance='NOT_GRANTED')
    mp=out/'MANIFEST.json';atomic_json(ROOT,mp,manifest)
    atomic_json(ROOT,ROOT/'config/core_product_focus_read_authority_r2.json',dict(contract_id='CORE_PRODUCT_FOCUS_READ_AUTHORITY_R2',manifest=ref(mp)))
    new_events={e['idempotency_key']:e for e in new['events']};old_events={e['idempotency_key']:e for e in old['events']}
    receipt=dict(contract_id=CONTRACT,T0=day,source_bindings=sources,manifest=ref(mp),head_unchanged=hp.read_bytes()==before,
        old_episode_count=len(old['episodes']),new_episode_count=len(new['episodes']),old_end_count=sum(bool(e['end_date']) for e in old['episodes']),new_end_count=sum(bool(e['end_date']) for e in new['episodes']),
        source_invalidated_by_day={d:sum(r['validity']=='INVALIDATED' for r in rows) for d,rows in days.items()},
        removed_events=[dict(entity_id=e['entity_id'],trade_date=e['trade_date'],event=e['event']) for k,e in old_events.items() if k not in new_events],
        added_events=[dict(entity_id=e['entity_id'],trade_date=e['trade_date'],event=e['event']) for k,e in new_events.items() if k not in old_events],
        external_acceptance='NOT_GRANTED',scope='Affected Focus lifecycle/path read projection only; immutable source unchanged')
    write(OUT/'FOCUS_VALIDITY_REPAIR_RECEIPT.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('old_episode_count','new_episode_count','old_end_count','new_end_count','source_invalidated_by_day','head_unchanged')}))

if __name__=='__main__':main()
