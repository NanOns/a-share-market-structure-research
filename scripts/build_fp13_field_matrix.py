"""Field-by-field completeness inventory, not an assertion of product PASS."""
import gzip,json,sys,sqlite3,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.current_v4_context import digest

def main():
    r=ProductionV4ResearchReader(ROOT);out=ROOT/'docs/evidence/fp13_20261008'
    def get(path):
        with urllib.request.urlopen('http://127.0.0.1:28765/api/v4/'+path) as response:return json.load(response)
    sources=r.manifest['sources'];raw_ref=sources['RAW_DAILY'];raw_bytes=(ROOT/raw_ref['path']).read_bytes();assert digest(raw_bytes)==raw_ref['sha256'];raw=json.loads(raw_bytes)['rows'];by={x['security_id']:x for x in raw}
    stock=r.query('stocks',{'q':'600000'})['items'][0];sid=stock['entity_id'];profile=get('stocks/'+sid+'/profile')
    checks=[]
    for name in ('close','open','high','low','amount','volume'):
        if name in stock['fields'] and name in by[sid]:
            actual=stock['fields'][name]['value'];expected=by[sid][name];assert actual==expected
            checks.append(dict(module='stock_raw',field=name,api=actual,source=expected,binding=raw_ref))
    market=get('market/breadth')['data'];amount=sum(x['amount'] for x in raw if isinstance(x.get('amount'),(int,float)))
    assert abs(amount-market['amount_cny'])<.01
    checks.append(dict(module='market_breadth',field='amount_cny',api=market['amount_cny'],source_sum=amount,binding=raw_ref))
    sector=r.query('sectors',{'limit':1})['items'][0]
    native_ref=sources['sector_operational'];assert digest((ROOT/native_ref['path']).read_bytes())==native_ref['sha256']
    with gzip.open(ROOT/native_ref['path'],'rt',encoding='utf8') as stream:native=next(json.loads(line) for line in stream if json.loads(line)['sector_id']==sector['entity_id'])
    for key in ('sector_rs20','sector_rs5','breadth_ret1','participation_proxy'):
        actual=sector['fields'][key]['value'];expected=native['fields'][key]['value'];assert actual==expected
        checks.append(dict(module='sector',field=key,api=actual,owner=expected,binding=native_ref))
    for module,key in (('focus','focus_operational'),('forward','forward_operational')):
        binding=sources[key];body=(ROOT/binding['path']).read_bytes();assert digest(body)==binding['sha256'];source=json.loads(body)
        expected=len(source['episodes' if module=='focus' else 'enrollments']);actual=r.query(module)['total'];assert actual==expected
        checks.append(dict(module=module,field='count',api=actual,source=expected,binding=binding))
    home=get('home');mb=sources['market_operational'];mbytes=(ROOT/mb['path']).read_bytes();assert digest(mbytes)==mb['sha256'];m=json.loads(mbytes)
    for key in ('trend_axis','breadth_axis','participation_axis','stress_level'):
        assert home['market']['row'][key]==m['row'][key]
        checks.append(dict(module='home',field=key,api=home['market']['row'][key],owner=m['row'][key],binding=mb))
    with sqlite3.connect(r.path.as_uri()+'?mode=ro',uri=True) as db:
        long=db.execute("SELECT payload FROM objects WHERE domain='stocks' ORDER BY length(name) DESC LIMIT 1").fetchone()
    write(out/'REAL_INDEPENDENT_ORACLE.json',dict(checks=checks,prior_oracles=[ref(ROOT/f'docs/evidence/{stage}_20261008/{name}') for stage,name in [('fp05','SOURCE_AND_VALUE_READBACK.json'),('fp07','REAL_VALUE_READBACK.json'),('fp09','RULE_SAMPLE_READBACK.json'),('fp12','REAL_VALUE_ORACLE.json')]],long_name_stock=json.loads(long[0])))
    labels=(ROOT/'src/workbench_service/static/research/labels.js').read_text(encoding='utf8');matrix=[]
    groups=[
      ('62C/64','sectors','scripts/build_fp06_sector.py','tests/test_fp06_sector.py','sector_type maturity health output_state why_now sector_rs20 sector_rs5 breadth_delta3 seed_width participation_proxy exhaustion quality emergence confirmation amount rank_velocity ma20_width entered exited retention overlap unique_member_share'),
      ('62D/65','stocks','scripts/build_fp07_stock.py','tests/test_fp07_stock.py','trend_state weekly_trend_state monthly_trend_state position_state ma_structure relative_state compression_state amount_state turnover_state basic_breakout_state basic_pullback_state basic_recovery_state support_state risk market_regime primary_industry supporting_concepts maturity health validity tracking scenario quality why_now waiting_for invalid_if price ma atr_normalized_position rps5 rps20 relative compression amount turnover sector_facts hypothesis supporting_evidence counterevidence next_discriminator anchors structure_events factor_timeline focus_timeline'),
      ('62F','focus','scripts/build_fp08_focus.py','tests/test_fp08_focus.py','event episode_id parent_episode_id health validity membership path_state outcome_status waiting_for anchor observation'),
      ('62G','market','scripts/build_fp09_market_center.py','tests/upgrade_m8/test_limit_rules.py','indices breadth limits ladders broken_limit facts_events'),
      ('62H/68','diagnostics','src/workbench_service/diagnostic_views.py','tests/test_fp11_diagnostics.py','health sources contracts jobs legacy shadow rps20_matrix technical_scanner loo'),
      ('66/67','replay_compare','src/workbench_service/replay_views.py','tests/test_fp12_replay.py','strict_pit corrected_history stock_previous stock_market frozen_sector current_loo sector_market sector_three sector_lifecycle followup date_token'),
    ]
    for section,domain,producer,test,keys in groups:
        if domain=='stocks':fields={**profile.get('F',{}),**profile.get('R',{}),**stock['fields']}
        elif domain in ('sectors','focus'):fields=r.query(domain,{'limit':1})['items'][0]['fields']
        else:fields={}
        for key in keys.split():
            cell=fields.get(key);state='SOURCE_OR_ADAPTER_DEBT' if not cell or cell.get('value') is None else 'REAL_FIELD_PRESENT'
            visible=(key+':') in labels if domain in ('stocks','sectors') else None
            matrix.append(dict(section=section,feature=key,producer=producer,api=('/api/v4/replay ; /api/v4/compare' if domain=='replay_compare' else '/api/v4/'+domain),ui=('/v4/research/replay ; /v4/research/compare' if domain=='replay_compare' else '/v4/research/'+domain),test=test,source=cell.get('source_digest') if cell else None,value=cell.get('value') if cell else None,quality=cell.get('quality') if cell else None,reason=cell.get('reason') if cell else 'Requires explicit route/adapter/source proof; no empty-placeholder credit',field_state=state,has_chinese_label=visible,ui_acceptance='REQUIRES_BROWSER_FIELD_PROOF',product_pass=False))
    for key in ('navigation','four_axes','rotation_changes','sector_changes','stock_changes','risk_changes','member_preview'):
        matrix.append(dict(section='62A/62B/63',feature=key,producer='src/workbench_service/domain_views.py',api='/api/v4/home',ui='/v4/research/home',test='tests/test_fp05_home.py',ui_acceptance='See home DOM/screenshots; missing rotation/member history is source debt',product_pass=False))
    write(out/'FEATURE_PRODUCER_API_UI_TEST_MATRIX.json',dict(contract='FP13_FIELD_MATRIX_V1',coverage_claim='INVENTORY_ONLY_NOT_100_PERCENT_ACCEPTANCE',rows=matrix,source_debt='docs/audits/FP13_FULL_PRODUCT_OPEN_ITEMS_20261008.md'))
    print('Independent oracle and',len(matrix),'mandatory field/path inventory rows written')
if __name__=='__main__':main()
