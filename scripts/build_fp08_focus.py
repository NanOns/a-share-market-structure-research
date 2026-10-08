"""Real two-session Focus reconstruction in a separately gated successor namespace."""
import gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.fp_domain_evidence import enter,check_protected
from scripts.build_fp05_market import verified
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.current_v4_context import canonical,digest
from focus_tracker.v4_successor import project
from focus_tracker.read_api import FocusTrackerReadAPI

def main():
    out=enter(8);reader=ProductionV4ResearchReader(ROOT);current=reader.manifest['sources']['states'];payload=json.load(gzip.open(verified(current),'rt',encoding='utf8'));prior=payload['prior_binding'];old=json.load(gzip.open(verified(prior),'rt',encoding='utf8'))
    days={old['rows'][0]['trade_date']:old['rows'],payload['rows'][0]['trade_date']:payload['rows']};result=project(days);assert result==project(days);keys=[r['idempotency_key'] for r in result['events']];assert len(keys)==len(set(keys))
    assert max(days)==reader.context['trade_date'];sources=dict(current=current,prior=prior,producer_set=payload['producer_set'],kernel=ref('src/focus_tracker/v4_successor.py'),legacy_kernel=ref('src/focus_tracker/lifecycle.py'))
    verified(payload['producer_set']);code,legacy=FocusTrackerReadAPI(env_file=ROOT/'config/.env').handle('/api/v3/focus-tracker/summary',{})
    write(out/'LEGACY_HISTORY_READBACK.json',dict(http=code,result=legacy,legacy_mutations=0))
    result.update(contract_id='FP08_FOCUS_SUCCESSOR_PUBLICATION_V1',sources=sources,trade_date=max(days),earliest_valid_date=min(days),legacy_history=dict(status=legacy.get('status'),http=code,preserved=True),permissions=dict(read=True,automatic_event_write=False,manual_pin=False),write_block_reason='PATH_OBSERVATION_ADAPTER_AND_LEGACY_MIGRATION_NOT_ADMITTED',namespace='V4_FOCUS_RECONSTRUCTED_SUCCESSOR_V1',AS_RECORDED=False)
    folder=ROOT/'data/v4/fp08_focus'/digest(canonical(result));path=folder/'focus.json';write(path,result)
    pointer=ROOT/'config/v4_focus_operational_authority_v1.json';before=json.loads(pointer.read_bytes()) if pointer.exists() else None
    authority=dict(contract_id='FP08_FOCUS_READ_AUTHORITY_V1',trade_date=max(days),input_data_head=json.loads((ROOT/'config/v4_stock_operational_authority_v1.json').read_bytes())['input_data_head'],publication=ref(path),previous=before if before and before.get('publication')!=ref(path) else (before or {}).get('previous'))
    write(pointer,authority);write(out/'MATERIALIZATION_READBACK.json',dict(episodes=len(result['episodes']),events=len(result['events']),idempotent=True,source_days=sorted(days),automatic_write=False,legacy_rows_preserved=True,protected=check_protected(out)))
    print(json.dumps(dict(episodes=len(result['episodes']),events=len(result['events']),automatic_write=False)))
if __name__=='__main__':main()
