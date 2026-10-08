"""Independent real prior-window ratio oracle; no kernel calls."""
import collections,copy,json,math,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import checked_path
OUT=ROOT/'docs/evidence/r2_raw_turnover_continuation_20261008'

def main():
    reader=ProductionV4ResearchReader(ROOT);authority=reader.manifest['domain_features']['stocks'];counts=collections.Counter();unknown=collections.Counter()
    prior=json.loads((ROOT/'docs/evidence/r2_presentation_continuation_20261008/FIELD_INVENTORY_V4.json').read_bytes())
    predecessor=json.loads((OUT/'PREDECESSOR.json').read_bytes())['authority'];old=ProductionV4ResearchReader(ROOT,snapshot_authority=predecessor['snapshot'])
    with sqlite3.connect(old.path.as_uri()+'?mode=ro',uri=True) as previous:
        old_stocks={json.loads(p)['entity_id']:json.loads(p)['fields'] for p, in previous.execute('SELECT payload FROM objects WHERE domain=?',('stocks',))}
    with sqlite3.connect(reader.path.as_uri()+'?mode=ro',uri=True) as db,sqlite3.connect(checked_path(ROOT,authority['series']).as_uri()+'?mode=ro',uri=True) as series:
        for payload, in db.execute('SELECT payload FROM objects WHERE domain=?',('stocks',)):
            item=json.loads(payload);sid=item['entity_id'];fields=item['fields'];previous=old_stocks[sid]
            assert {k:v for k,v in fields.items() if k not in ('amount','volume')}==previous,(sid,'EXISTING_STOCK_FIELDS_CHANGED')
            bars=[json.loads(p) for p, in series.execute('SELECT payload FROM bars WHERE security=? AND day<=? ORDER BY day DESC LIMIT 21',(sid,reader.context['trade_date']))]
            for n in (5,20):
                for field in ('amount','volume'):
                    key=field+'_ratio'+str(n);cell=fields[key]
                    if cell['value'] is None or cell['quality']=='UNKNOWN':unknown[key]+=1;assert cell['reason'];continue
                    assert len(bars)>=n+1 and bars[0]['trade_date']==reader.context['trade_date']
                    denominator=sum(b[field] for b in bars[1:n+1])/n
                    assert denominator>0
                    expected=bars[0][field]/denominator
                    assert math.isclose(cell['value'],expected,rel_tol=1e-12,abs_tol=1e-12),(sid,key,expected,cell['value'])
                    counts[key]+=1
    write(OUT/'RATIO_ORACLE.json',dict(result='PASS',formula='current_actual_value / arithmetic_mean_of_previous_N_completed_session_values_excluding_current',
        series=authority['series'],known_comparisons=dict(counts),unknown_preserved=dict(unknown),existing_stock_fields_unchanged=True,independent_from_native_kernel=True))
    result=copy.deepcopy(prior)
    for item in result['rows']:
        if item['section']=='62D/65' and item['feature']=='amount':
            item.update(owner_source_ready=True,ui_rendered=True,numeric_oracle=True,browser_pass=True,product_pass=True,debt_reason=None,
                known_rows=counts['amount_ratio20'],unknown_rows=unknown['amount_ratio20'],source_present_rows=5213,
                source_fields=['amount','amount_ratio5','amount_ratio20'],admission_scope='CURRENT_RAW_AMOUNT_CNY_AND_ACCEPTED_PRIOR_WINDOW_RATIOS',
                reason_counts={'ACCEPTED_OWNER_RATIO_UNAVAILABLE':unknown['amount_ratio20']},
                evidence=[ref(OUT/'REAL_SOURCE_ORACLE.json'),ref(OUT/'RATIO_ORACLE.json'),ref(OUT/'BROWSER_ORACLE.json')])
    result.update(contract_id='R2_FIELD_ADMISSION_V5',context_token=reader.token,ui_build_id=json.loads((OUT/'BROWSER_ORACLE.json').read_bytes())['ui_build_id'],
        inherited_admission_source=ref('docs/evidence/r2_presentation_continuation_20261008/FIELD_INVENTORY_V4.json'),
        inherited_stock_field_values_reverified=True,full_product_pass=False)
    result['counts']={key:sum(r.get(key) is True for r in result['rows']) for key in ('owner_source_ready','ui_rendered','numeric_oracle','browser_pass','product_pass')}
    assert len(result['rows'])==110 and result['counts']['product_pass']==16
    write(OUT/'FIELD_INVENTORY_V5.json',result);print(json.dumps(dict(counts=result['counts'],ratio_comparisons=sum(counts.values()))))

if __name__=='__main__':main()
