"""Frozen original BFF chart oracle, isolated process, old index read-only."""
import json,sys
from pathlib import Path
root=Path('G:/codex work/大A交易').resolve();sys.path[:0]=[str(root),str(root/'src')]
from workbench_analysis.operational_successor_v1 import accepted_api
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
api=accepted_api(root);bff=CoreProductBFFR1(api,None)
request=json.loads(Path(sys.argv[1]).read_bytes());results=[]
for q in request['queries']:
    code,value=bff.get('/api/v4/stocks/'+request['security_id']+'/chart',dict(q,context_token=api.token))
    results.append(dict(query=q,code=code,items=value.get('items'),total=value.get('total')))
Path(sys.argv[2]).write_text(json.dumps(results,ensure_ascii=False),encoding='utf8')
