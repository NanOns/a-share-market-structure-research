"""Add independently proven field admissions without blanket readiness."""
import copy,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.current_v4_context import canonical,digest
OUT=ROOT/'docs/evidence/r2_presentation_continuation_20261008'

def main():
    old=json.loads((ROOT/'docs/evidence/r2_field_continuation_20261008/FIELD_INVENTORY_V3.json').read_bytes())
    previous=json.loads((ROOT/'docs/evidence/r2_field_continuation_20261008/CANDIDATE.json').read_bytes())
    old_reader=ProductionV4ResearchReader(ROOT,snapshot_authority=previous['snapshot']);reader=ProductionV4ResearchReader(ROOT)
    def rows(r,domain):
        with sqlite3.connect(r.path.as_uri()+'?mode=ro',uri=True) as db:
            return {json.loads(p)['entity_id']:json.loads(p)['fields'] for p, in db.execute('SELECT payload FROM objects WHERE domain=?',(domain,))}
    stocks=rows(reader,'stocks');sectors=rows(reader,'sectors');old_stocks=rows(old_reader,'stocks');old_sectors=rows(old_reader,'sectors')
    unchanged=[]
    for item in old['rows']:
        if not item['product_pass']:continue
        if item['feature']=='focus_timeline':
            assert old_reader.manifest['domain_features']['focus']['events']==reader.manifest['domain_features']['focus']['events']
        else:
            current,prior=(sectors,old_sectors) if item['section']=='62C/64' else (stocks,old_stocks)
            for sid in current:
                for field in item['source_fields']:assert current[sid][field]==prior[sid][field],(sid,field,'PREVIOUS_FIELD_ADMISSION_CHANGED')
        unchanged.append(dict(section=item['section'],feature=item['feature']))
    state=json.loads((OUT/'PROFILE_STATE_ORACLE.json').read_bytes());browser=json.loads((OUT/'BROWSER_STATE_ORACLE.json').read_bytes())
    assert state['result']==browser['result']=='PASS' and browser['actual_field_checks']==70
    field_map={'ma_structure':'ma_structure_state'}
    result=copy.deepcopy(old)
    for item in result['rows']:
        field=field_map.get(item['feature'],item['feature'])
        if item['section']=='62D/65' and field in state['fields']:
            item.update(ui_rendered=True,numeric_oracle=True,browser_pass=True,product_pass=True,debt_reason=None,
                admission_scope='ACCEPTED_CURRENT_OWNER_STATE_THRESHOLDS_AND_TYPED_UNKNOWN',
                oracle_scope=state['scope'],evidence=[ref(OUT/'PROFILE_STATE_ORACLE.json'),ref(OUT/'BROWSER_STATE_ORACLE.json'),ref(OUT/'BROWSER_ORACLE.json')])
        if item['section']=='62D/65' and item['feature'] in ('why_now','waiting_for'):
            source='transition_reasons' if item['feature']=='why_now' else 'unknown_predicates'
            item.update(source_fields=[source],source_present_rows=len(stocks),owner_source_ready=True,
                ui_rendered=True,known_rows=sum(v[source]['quality']=='KNOWN' for v in stocks.values()),
                source_mapping='OWNER_TRANSITION_REASONS' if source=='transition_reasons' else 'MISSING_PREDICATE_EVIDENCE_ONLY',
                debt_reason='NO_EXPLICIT_OWNER_FIELD_PUBLISHED_FALLBACK_IS_VISIBLY_DISTINGUISHED')
            # Explicit waiting conditions remain an independent requirement.
            item['product_pass']=False
        if item['section']=='62F' and item['feature']=='anchor':
            item.update(ui_rendered=True,browser_pass=True,structural_oracle=True,numeric_oracle=False,numeric_oracle_applicable=False,
                product_pass=True,debt_reason=None,admission_scope='TYPED_FOCUS_EVENT_ANCHORS_ONLY_NOT_STRUCTURE_ANCHOR',
                evidence=[ref(OUT/'REAL_SOURCE_ORACLE.json'),ref(OUT/'BROWSER_ORACLE.json')])
    result.update(contract_id='R2_FIELD_ADMISSION_V4',context_token=reader.token,ui_build_id=json.loads((OUT/'BROWSER_ORACLE.json').read_bytes())['ui_build_id'],
        inherited_admission_source=ref('docs/evidence/r2_field_continuation_20261008/FIELD_INVENTORY_V3.json'),
        inherited_values_reverified=unchanged,next_stage='UNADMITTED_FIELDS_REQUIRE_SEPARATE_SOURCE_UI_OR_ORACLE_WORK',full_product_pass=False)
    result['counts']={key:sum(row.get(key) is True for row in result['rows']) for key in ('owner_source_ready','ui_rendered','numeric_oracle','browser_pass','product_pass')}
    assert len(result['rows'])==110 and result['counts']['product_pass']==15
    write(OUT/'FIELD_INVENTORY_V4.json',result);print(json.dumps(result['counts']))

if __name__=='__main__':main()
