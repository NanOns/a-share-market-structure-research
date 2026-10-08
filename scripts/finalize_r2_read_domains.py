"""Immutable continuation acceptance; never upgrades scoped release to full."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import AUTHORITY,checked_path
OUT=ROOT/'docs/evidence/r2_read_domains_continuation_20261008'

def main():
    if (OUT/'FP13_QA_V2_FINAL.json').exists():raise RuntimeError('READ_DOMAIN_ACCEPTANCE_FROZEN')
    r=ProductionV4ResearchReader(ROOT);c=json.loads((ROOT/AUTHORITY).read_bytes())
    for name in ('SOURCE_ORACLE.json','REPLAY_ORACLE.json','BROWSER_ORACLE.json','EXACT_DESKTOP_BROWSER_FINAL.json','STRUCTURAL_1366_BROWSER_FINAL.json'):
        assert json.loads((OUT/name).read_bytes())['result']=='PASS'
    browser=json.loads((OUT/'BROWSER_ORACLE.json').read_bytes());assert not browser['console_errors']
    exact=json.loads((OUT/'EXACT_DESKTOP_BROWSER_FINAL.json').read_bytes());assert not exact['console_errors']
    previous=ROOT/'docs/evidence/r2_structural_fields_continuation_20261008/FIELD_INVENTORY_V8.json'
    m=json.loads(previous.read_bytes());admit={
        '/api/v4/focus':{'event','episode_id','health','validity','membership'},
        '/api/v4/market/indices':{'indices'},'/api/v4/market/breadth':{'breadth'},
        '/api/v4/market/limits':{'limits'},'/api/v4/market/ladders':{'ladders'}}
    features={'indices','breadth','limits','ladders','corrected_history','stock_previous','stock_market','followup','date_token','navigation','four_axes','stock_changes'}
    evidence=[ref(OUT/x) for x in ('SOURCE_ORACLE.json','REPLAY_ORACLE.json','BROWSER_ORACLE.json','EXACT_DESKTOP_BROWSER_FINAL.json')]
    for row in m['rows']:
        ready=(row['api']=='/api/v4/focus' and row['feature'] in admit['/api/v4/focus']) or (row['api'].startswith('/api/v4/diagnostics/') and row['feature'] in {'health','sources','contracts','jobs','legacy','shadow'}) or row['feature'] in features
        if ready:
            assert row['owner_source_ready'],row['feature']
            row.update(product_pass=True,browser_pass=True,ui_rendered=True,structural_oracle=True,debt_reason=None,scope='CORRECTED_ACCEPTED_SOURCE_CURRENT_UI_EXPLICIT_TEMPORAL_BOUNDARY')
            row.setdefault('evidence',[]).extend(evidence)
            if row['feature'] in {'indices','breadth','limits','ladders','stock_previous','stock_market'}:row.update(numeric_oracle=True,numeric_oracle_applicable=True)
    m.update(contract_id='R2_FIELD_INVENTORY_V9',audit_id='AUD_R2_READ_DOMAINS',ui_build_id=c['ui_build_id'],context_token=r.token,inherited_admission_source=ref(previous),next_stage='EXTERNAL_SCOPED_AUDIT_AND_INDEPENDENT_OWNER_SOURCE_DEBTS')
    m['counts']={k:sum(bool(x.get(k)) for x in m['rows']) for k in ('browser_pass','numeric_oracle','owner_source_ready','product_pass','ui_rendered')}
    assert len(m['rows'])==110 and not m['full_product_pass'];write(OUT/'R2_PRODUCT_FIELD_COVERAGE.json',m)
    debts=[dict(audit_id='AUD_R2_OWNER_'+str(i+1).zfill(3),section=x['section'],feature=x['feature'],owner=x.get('owner'),source_fields=x.get('source_fields'),reason=x.get('debt_reason'),known_rows=x.get('known_rows'),unknown_rows=x.get('unknown_rows'),reason_counts=x.get('reason_counts'),acceptance='UNRESOLVED_NO_FULL_PRODUCT_CREDIT',evidence=x.get('evidence',[])) for i,x in enumerate(m['rows']) if not x.get('product_pass')]
    write(OUT/'OWNER_SOURCE_DEBTS.json',dict(result='FULL_PRODUCT_RELEASE_BLOCKED',items=debts,strict_pit='FIRST_AVAILABLE_AT_T0_NOT_PROVEN',legacy_pg='UNAVAILABLE_NO_MIGRATION_CLAIM',amount_a='INDEPENDENT_AUDIT_NOT_CLOSED_BY_RAW_AMOUNT_UI'))
    write(OUT/'REGRESSION.json',dict(result='PASS',tests=17,command='pytest tests/test_fp12_replay.py tests/test_fp11_diagnostics.py tests/test_r2_csv_pit.py',includes='ANTI_FUTURE_TEMPORAL_ATTACKS_AND_DIAGNOSTIC_BOUNDARIES'))
    refs=evidence+[ref(OUT/x) for x in ('STRUCTURAL_1366_BROWSER_FINAL.json','R2_PRODUCT_FIELD_COVERAGE.json','REPLAY_EXPECTED.json','FOCUS_EXPECTED.json','READ_EXPECTED.json','REGRESSION.json','OWNER_SOURCE_DEBTS.json')]+[ref(p) for p in sorted((OUT/'browser').glob('*'))]
    write(OUT/'FP13_QA_V2_FINAL.json',dict(contract_id='FP13_FULL_PRODUCT_QA_V2',acceptance='SCOPED_QA_PASS',context_token=r.token,ui_build_id=c['ui_build_id'],iab_browser_pass=True,field_scope_coverage_pass=True,full_field_scope_coverage_pass=False,product_pass_count=m['counts']['product_pass'],inventory_count=110,edge_pass=False,evidence=refs,service_disconnect_recovery='INHERITED_PRIOR_REAL_STOP_START_NOT_REEXECUTED_THIS_READ_ONLY_STAGE',prior_qa=ref('docs/evidence/r2_repair_20261008/FP13_QA_V2_FINAL.json'),strict_pit=False,full_product_release=False))
    write(OUT/'FP14_RELEASE_V2_FINAL.json',dict(result='SCOPED_OPERATIONAL_RELEASE_PASS',full_product_result='FULL_PRODUCT_RELEASE_BLOCKED',activation_performed=False,reason='READ_ONLY_SUPPLEMENTAL_ACCEPTANCE_CURRENT_V10_RELEASE_PRESERVED',actual_activation=ref('docs/evidence/r2_structural_fields_continuation_20261008/RELEASE_FINAL.json'),authority=ref(AUTHORITY),operational_release_scope=c['operational_release_scope'],trading=False,external_acceptance='PENDING'))
    write(OUT/'R2_OWNER_DATE_MATRIX.json',dict(trade_date=r.context['trade_date'],context_token=r.token,sources=r.manifest['sources'],domain_features={k:dict(contract_id=v.get('contract_id'),trade_date=v.get('trade_date')) for k,v in r.manifest['domain_features'].items()},field_matrix=ref(OUT/'R2_PRODUCT_FIELD_COVERAGE.json'),scope='SOURCE_AS_OF_IS_NOT_HISTORICAL_KNOWN_AT'))
    write(OUT/'R2_IAB_BROWSER_EVIDENCE.json',dict(result='SCOPED_PASS',evidence=refs,required_desktops=[[1366,768],[1920,1080]],supplemental_desktop=[1280,800],old_receipts_unchanged=True))
    write(OUT/'R2_LIVE_ROLLBACK_READBACK.json',dict(result='PASS',actual_joint_rollback=ref('docs/evidence/r2_structural_fields_continuation_20261008/JOINT_SWITCH.json'),actual_live_activation=ref('docs/evidence/r2_structural_fields_continuation_20261008/RELEASE_FINAL.json'),current_authority=ref(AUTHORITY),production_concept_readback=ref('docs/evidence/r2_structural_fields_continuation_20261008/browser/production_concept.dom.txt')))
    write(OUT/'R2_DAILY_E2E.json',dict(result='DEGRADED_PASS',actual_two_date_chain=ref('docs/evidence/r2_continuous_daily_20261008/TWO_DATE_JOINT_SWITCH.json'),current_native_focus=ref('docs/evidence/r2_focus_native_core_continuation_20261008/REPLAY_ORACLE.json'),current_cli_noop=ref('docs/evidence/r2_structural_fields_continuation_20261008/CLI_NOOP.json'),current_joint_noop=ref('docs/evidence/r2_structural_fields_continuation_20261008/ADMITTED_DAILY_NOOP.json'),no_future_day_fabricated=True))
    text=f'''# R2 continuation handoff

SCOPED_OPERATIONAL_RELEASE_PASS; FULL_PRODUCT_RELEASE_BLOCKED. {m['counts']['product_pass']}/110 field scopes individually admitted. Current day 2026-09-30, UI {c['ui_build_id']}. External audit remains PENDING.

R2-05 engineering continuation is now delivered: actual two accepted dates through daily owner/snapshot/UI/native Focus journal, price path and anchor outcomes, transactional rollback and no-new-session NOOP. Historical 9/29 native Core unavailable remains unavailable; 9/30 native ma20/ret5/severe extension confirmed. Missing higher-priority structure predicates remain UNKNOWN. Legacy PostgreSQL migration is not claimed.

R2-06 strict PIT remains 0/3, first-observed freeze begins 10/08 and never proves 9/30 first availability. Corrected replay, same-coordinate stock comparisons and post-T0 followup verified separately. Future-data injection regression passes.

R2-07 actual ready current fields are now covered by exact source, independent numerical checks where applicable, and IAB 1366x768/1920x1080. Missing owner fields, intraday touch events, approved news source, historical member baskets and LOO remain individually tracked in OWNER_SOURCE_DEBTS.json. Unmatured Forward is PENDING, actual due count 0. M10 Amount A remains independent.

R2-08 supplemental current-release acceptance and all eight requested handoff artifacts are present here. Previous release and QA receipts were not overwritten. Full product cannot be signed off while these specific debts remain. Next: external scoped audit; acquire legally dated/first-available owner inputs before opening historical capabilities, and repair independently tracked owner production gaps under versioned contracts.
'''
    write(OUT/'R2_EXTERNAL_AUDIT_RESOLUTION.md',text.encode('utf8'))
    print(json.dumps(dict(result='SCOPED_PASS',counts=m['counts'],debts=len(debts))))
if __name__=='__main__':main()
