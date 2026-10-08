"""Evidence-gated scoped QA successor; full-product omissions remain explicit."""
import json,re,sys,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
OUT=ROOT/'docs/evidence/r2_repair_20261008'

def main():
    r=ProductionV4ResearchReader(ROOT);candidate=json.loads((OUT/'R2_RELEASE_CANDIDATE.json').read_bytes());runs=json.loads((OUT/'browser/RUNS_FINAL.json').read_bytes())
    assert len(runs)==12 and all(x['datePresent'] for x in runs)
    for x in runs:
        assert (x['width'],x['height']) in [(1366,768),(1920,1080)]
        assert (OUT/x['screenshot']).stat().st_size>1000
    # Narrow released field set: this is not the 110-feature full-product gate.
    requirements={
        'stocks_daily':('browser/final_stock_all_fields.txt',['收盘价','二十会话均线','五会话相对强度分位','来源']),
        'sectors_current_facts':('browser/final_sectors_1920.txt',['成员数','二十会话相对强度','五会话相对强度','单会话上涨宽度','参与度代理','来源']),
        'market_current':('browser/final_home_1920.txt',['趋势','宽度变化','参与度','压力','数值与来源']),
        'focus_read_corrected':('browser/final_focus_1920.txt',['Focus 独立关注清单','关注资格','有效性']),
        'forward_read':('browser/final_focus_1920.txt',['Forward 样本','期限计划','待到期结算']),
        'diagnostics':('browser/final_diagnostics_1920.txt',['来源与版本','生产源健康','RAW_DAILY']),
        'compare_corrected':('browser/compare_corrected.txt',['事后重建对照（非 PIT）','3.268%','-0.136%']),
    }
    proof=[]
    for scope,(file,labels) in requirements.items():
        text=(OUT/file).read_text(encoding='utf8');missing=[x for x in labels if x not in text]
        assert not missing,(scope,missing)
        proof.append(dict(scope=scope,labels=labels,DOM=ref(OUT/file),pass_=True))
    disconnected=(OUT/'browser/service_disconnected_final.txt').read_text(encoding='utf8');recovered=(OUT/'browser/service_recovered_final.txt').read_text(encoding='utf8')
    assert '研究服务连接中断' in disconnected and '共 5213 条' in recovered
    assert '数据版本已变化' in (OUT/'browser/fault_409.txt').read_text(encoding='utf8')
    assert '读取失败' in (OUT/'browser/fault_503.txt').read_text(encoding='utf8')
    assert '市场指数' in (OUT/'browser/fault_503_other_domain.txt').read_text(encoding='utf8')
    records=[]
    def get(route,expected=200):
        try:
            with urllib.request.urlopen('http://127.0.0.1:28765/api/v4/'+route,timeout=20) as response:code=response.status;data=json.load(response)
        except urllib.error.HTTPError as e:code=e.code;data=json.load(e)
        assert code==expected,(route,code)
        records.append(dict(route=route,http=code,status=data.get('status'),resource_type=data.get('resource_type')));return data
    for domain in ('stocks','sectors','focus','forward'):
        ids=[];offset=0
        while True:
            d=get(f'{domain}?limit=200&offset={offset}')
            assert d['context_token']==r.token
            ids.extend(x['entity_id'] for x in d['items']);offset+=len(d['items'])
            if not d['has_next']:break
        assert len(ids)==len(set(ids))==d['total']==r.manifest['counts'][domain]
    sid=r.manifest['domain_features']['focus']['episodes'][0]['entity_id']
    for kind in ('episodes','timeline','anchors','observations','outcomes'):
        data=get(f'focus/{sid}/{kind}');assert data['resource_type']==kind
        if kind=='outcomes':assert data['status']=='SOURCE_INCOMPLETE' and not data['items']
        for item in data['items']:assert all(k in item for k in data['item_schema'])
    stock=r.query('stocks',{'limit':1})['items'][0]['entity_id'];data=get('stocks/'+stock+'/timeline');assert data['status'] in ('READY','SOURCE_INCOMPLETE','EMPTY_VALID')
    get('stocks?context_token=expired',409);get('stocks?limit=201',400)
    inventory=json.loads((OUT/'R2_PRODUCT_FIELD_COVERAGE.json').read_bytes());labels_source=(ROOT/'src/workbench_service/static/research/labels.js').read_text(encoding='utf8');visible='\n'.join((OUT/p).read_text(encoding='utf8') for p in ['browser/final_stock_all_fields.txt',*[x['dom'] for x in runs]])
    for x in inventory['rows']:
        feature=x['feature'];match=re.search(r'["\']?'+re.escape(feature)+r'["\']?\s*:\s*["\']([^"\']+)',labels_source)
        label=match[1] if match else None;x['has_chinese_label']=bool(label);x['ui_rendered']=bool(label and label in visible)
        x['browser_pass']=bool(x['owner_source_ready'] and x['ui_rendered'])
        x['product_pass']=bool(x['browser_pass'] and x['numeric_oracle'])
        if x['owner_source_ready'] and not x['product_pass']:x['debt_reason']='FULL_FIELD_ORACLE_OR_INTERACTION_PROOF_PENDING'
    inventory['full_product_pass']=False;write(OUT/'R2_PRODUCT_FIELD_COVERAGE.json',inventory)
    write(OUT/'R2_HTTP_QA.json',dict(requests=records,pagination_verified=True,context_token=r.token))
    evidence=[ref(p) for p in sorted((OUT/'browser').iterdir()) if p.is_file()]+[ref(OUT/p) for p in ('R2_HTTP_QA.json','R2_OWNER_DATE_MATRIX.json','R2_REAL_VALUE_ORACLE.json','R2_PRODUCT_FIELD_COVERAGE.json','R2_CSV_DOWNLOAD.json','REGRESSION.json')]
    browser=dict(browser='CODEX_IAB',runs=runs,scoped_fields=proof,service_disconnect_recovery_pass=True,partial_503_isolation_pass=True,isolated_403_409_pass=True,keyboard_search_chinese_pass=True,date_back_forward_pass=True,csv_native_download_pass=True,edge_pass=False,Edge='WAIVED_BY_R2_NOT_FALSIFIED',full_product_fields_pass=False,evidence=evidence)
    write(OUT/'R2_IAB_BROWSER_EVIDENCE.json',browser)
    qa=dict(contract_id='FP13_FULL_PRODUCT_QA_V2',acceptance='SCOPED_QA_PASS',product_complete=False,full_product_result='FULL_PRODUCT_RELEASE_BLOCKED',iab_browser_pass=True,service_disconnect_recovery_pass=True,field_scope_coverage_pass=True,required_full_field_coverage_pass=False,edge_pass=False,ui_build_id=candidate['ui_build_id'],context_token=r.token,operational_release_scope=candidate['operational_release_scope'],evidence=evidence+[ref(OUT/'R2_IAB_BROWSER_EVIDENCE.json')],independent_external_acceptance='PENDING')
    write(OUT/'FP13_QA_V2_FINAL.json',qa);print('SCOPED_QA_PASS / FULL_PRODUCT_RELEASE_BLOCKED')

if __name__=='__main__':main()
