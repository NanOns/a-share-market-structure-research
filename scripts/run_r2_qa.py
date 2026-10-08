"""R2 real-source inventory and independent values; browser acceptance stays separate."""
import gzip,json,sys,subprocess,sqlite3
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.domain_views import objects
from workbench_service.current_v4_context import SourceInvalid
OUT=ROOT/'docs/evidence/r2_repair_20261008'

def audit():
    r=ProductionV4ResearchReader(ROOT);day=r.context['trade_date'];verified=[]
    for name,b in r.manifest['sources'].items():
        actual=ref(b['path'])
        if actual['sha256']!=b['sha256']:raise SourceInvalid('R2_SOURCE_MISMATCH:'+name)
        verified.append(dict(name=name,**actual))
    groups={};samples={};ids={};allrows={}
    for domain,n in [('stocks',10),('sectors',5),('market',1)]:
        rows=objects(r,domain);allrows[domain]=rows;ids[domain]={x['entity_id'] for x in rows};samples[domain]=rows[:n]
        assert len(ids[domain])==r.manifest['counts'][domain]
        for row in rows:
            assert row['trade_date']==day
            for field,c in row['fields'].items():
                key=(domain,field,c.get('source_digest'),str(c.get('source_as_of')))
                g=groups.setdefault(key,dict(domain=domain,field=field,owner=c.get('source_contract_id') or c.get('producer_contract_id') or 'OWNER_CONTRACT_NOT_DECLARED',source_digest=c.get('source_digest'),source_as_of=c.get('source_as_of'),price_basis=c.get('adjustment_basis') or 'OWNER_CELL_BASIS_NOT_DECLARED',dependency=c.get('source_field'),count=0,quality_counts=Counter(),reasons=Counter()))
                g['count']+=1;g['quality_counts'][c.get('quality','MISSING')]+=1
                if c.get('reason'):g['reasons'][str(c['reason'])]+=1
    extras=[];factors={};profiles={}
    for name,destination in [('stock_factors',factors),('stock_profiles',profiles),('advanced',None)]:
        with gzip.open(ROOT/r.manifest['sources'][name]['path'],'rt',encoding='utf8') as f:
            for line in f:
                x=json.loads(line);sid=x['security_id']
                if destination is not None:
                    assert x['trade_date']==day
                    if sid in {y['entity_id'] for y in samples['stocks']}:destination[sid]=x
                elif sid not in ids['stocks']:extras.append(dict(security_id=sid,trade_date=x['trade_date'],cutoff=x.get('cutoff'),disposition='OUTSIDE_CURRENT_RAW_POOL_NOT_IMPLICITLY_ADMITTED',identity_reason='REQUIRES_DATED_IDENTITY_OWNER_RECONCILIATION'))
    oracle=[]
    for row in samples['stocks']:
        sid=row['entity_id']
        for field in ('ma5','ma20','ret1','amount_ratio20','rps20'):
            owner=factors[sid]['fields'][field];cell=row['fields'][field]
            assert cell['value']==owner['value']
            assert owner.get('window_end_trade_date',factors[sid]['trade_date'])==day
            oracle.append(dict(entity_id=sid,field=field,api=cell['value'],owner=owner['value'],source=ref(r.manifest['sources']['stock_factors']['path'])))
    independent=[]
    with sqlite3.connect((ROOT/r.manifest['domain_features']['stocks']['series']['path']).as_uri()+'?mode=ro',uri=True) as db:
        for row in samples['stocks']:
            bars=[json.loads(x[0]) for x in db.execute('SELECT payload FROM bars WHERE security=? AND day<=? ORDER BY day',(row['entity_id'],day))]
            for n in (5,20):
                window=bars[-n:]
                if len(window)!=n or any(x['qfq_ohlc'] is None for x in window):continue
                expected=sum(float(x['qfq_ohlc'][3]) for x in window)/n;actual=row['fields']['ma'+str(n)]['value']
                if actual is None:continue
                assert abs(actual-expected)<1e-10
                independent.append(dict(entity_id=row['entity_id'],field='ma'+str(n),owner=actual,independent=expected,formula='SUM_NATIVE_QFQ_CLOSE/N',source=r.manifest['sources']['stock_series']))
    sector_source={}
    with gzip.open(ROOT/r.manifest['sources']['sector_operational']['path'],'rt',encoding='utf8') as f:
        for line in f:
            x=json.loads(line);sector_source[x['sector_id']]=x
    for row in samples['sectors']:
        for field in ('sector_rs5','breadth_ret1','participation_proxy'):
            expected=sector_source[row['entity_id']]['fields'][field]['value'];actual=row['fields'][field]['value'];assert actual==expected
            oracle.append(dict(entity_id=row['entity_id'],field=field,api=actual,owner=expected))
    market=json.loads((ROOT/r.manifest['sources']['market_operational']['path']).read_bytes())
    for extra in extras:
        extra['dated_identity_and_status']=[]
    for date in ('2026-09-28','2026-09-29','2026-09-30'):
        maps={}
        for kind in ('IDENTITY_UNIVERSE','TRADING_STATUS'):
            binding=market['sources'][date+':'+kind]
            if ref(binding['path'])['sha256']!=binding['sha256']:raise SourceInvalid('EXTRA_IDENTITY_SOURCE_MISMATCH')
            maps[kind]={x['security_id']:x for x in json.loads((ROOT/binding['path']).read_bytes())['rows']}
        for extra in extras:
            sid=extra['security_id'];extra['dated_identity_and_status'].append(dict(trade_date=date,identity=maps['IDENTITY_UNIVERSE'].get(sid),trading_status=maps['TRADING_STATUS'].get(sid)))
            status=maps['TRADING_STATUS'].get(sid,{})
            if date==day and status.get('status')=='SUSPENDED' and status.get('actual_bar_present') is False:
                extra['identity_reason']='BOUND_IDENTITY_SUSPENDED_NO_RAW_BAR';extra['first_available_proven']=False
    for field in ('trend_axis','breadth_axis','participation_axis','stress_level'):
        actual=allrows['market'][0]['fields'][field]['value'];expected=market['row'][field];assert actual==expected
        oracle.append(dict(entity_id='A_SHARE_RESEARCH_MARKET',field=field,api=actual,owner=expected,raw=market['raw']))
    write(OUT/'R2_OWNER_DATE_MATRIX.json',dict(contract_id='R2_OWNER_DATE_DIGEST_MATRIX_V1',trade_date=day,counts=r.manifest['counts'],fields=list(groups.values()),sources=verified,advanced_extra_identities=extras,current_core='FP06_SUCCESSOR_CURRENT_0930_VERIFIED_NOT_LEGACY_0928',LOO='NOT_BOUND_TO_CURRENT_PRODUCTION',FEP='NOT_BOUND_TO_CURRENT_PRODUCTION',knowledge_lineage='RECONSTRUCTED_CORRECTED_NOT_STRICT_PIT',acceptance='DEGRADED_PASS',remaining_debt=['11_IDENTITY_OWNER_RECONCILIATION','STRICT_FIRST_AVAILABLE','FEP_CURRENT_INFERENCE','LOO_CURRENT_BINDING']))
    write(OUT/'R2_REAL_VALUE_ORACLE.json',dict(checks=oracle,independent_arithmetic=independent,samples=samples,pass_count=len(oracle),scope='69_OWNER_VALUE_EQUALITIES_PLUS_NATIVE_QFQ_MA_INDEPENDENT_ARITHMETIC'))
    inventory=json.loads((ROOT/'docs/evidence/fp13_20261008/FEATURE_PRODUCER_API_UI_TEST_MATRIX.json').read_bytes())['rows'];coverage=[]
    for x in inventory:
        domain=x['api'].split('/')[3];field=x['feature'];matched=[c for k,c in groups.items() if k[0]==domain and k[1]==field]
        ready=bool(matched) and any(any(c['quality_counts'].get(q,0)>0 for q in ('KNOWN','ACCEPTED','OBSERVED')) for c in matched)
        coverage.append(dict(x,production_required=True,owner_source_ready=ready,ui_rendered=False,numeric_oracle=any(o['field']==field for o in oracle),browser_pass=False,debt_reason=None if ready else x.get('reason') or 'OWNER_FIELD_NOT_PUBLISHED_OR_QUALITY_UNKNOWN',owner=x['producer'],due='NEXT_REAL_OWNER_ADMISSION' if not ready else 'R2_IAB_FIELD_VERIFICATION',product_pass=False))
    write(OUT/'R2_PRODUCT_FIELD_COVERAGE.json',dict(contract_id='R2_FIELD_COVERAGE_V2',rows=coverage,full_product_pass=False,inventory_count=len(coverage),source_ready_count=sum(x['owner_source_ready'] for x in coverage)))
    print(json.dumps(dict(source_refs=len(verified),oracle=len(oracle),extras=len(extras),field_groups=len(groups),counts=r.manifest['counts'])))

if __name__=='__main__':audit()
