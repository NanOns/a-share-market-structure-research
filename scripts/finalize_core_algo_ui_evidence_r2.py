"""Normalize every audit row to the requested contract without broadening verdicts."""
from pathlib import Path
import json,gzip,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/core_algo_ui_r2_20261010'

def load(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:
        return json.loads(next(f)) if '.jsonl' in p.name else json.load(f)

def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def write(p,v):
    import os
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p)

KEYS=('feature_id','contract_section','producer_code','factor_or_algorithm_version','exact_input_owners','T0','member_set_asof','PIT_scope','output_owner_and_field','data_quality','field_unit','field_window','test_oracle','BFF_route','UI_route/component','browser_result','current_verdict','fix_owner')
AXES=('ALGO_FORMULA_VALID','DATA_CURRENT_VALID','API_BINDING_VALID','UI_RENDER_VALID','GO_FORWARD_VALIDATION','STRICT_PIT_VALID')

def main():
    h=load(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=h['accepted_trade_date'];owners=h['owners'][day]
    old=load(ROOT/'docs/evidence/core_algo_ui_r1_20261010/CORE_ALGO_UI_LINEAGE_MATRIX.json');oracle=load(OUT/'oracle/OUTPUT.json')
    current=load(OUT/'API_FIELD_CONTRACT_AUDIT.json');routes={r['route']:r for r in current['routes']};records=load(OUT/'iab/BROWSER_DOM_RECORDS.json') if (OUT/'iab/BROWSER_DOM_RECORDS.json').exists() else []
    base=load(OUT/'STAGE_LEDGER.json')['BASE_SHA'];rows=[];membership=current['context']['member_set_asof']
    registries={}
    for filename in ('v4_03_field_registry_v1.json','v4_04_field_registry_v2.json','v4_08_sector_field_registry_r5.json'):
        for field in load(ROOT/'config'/filename)['fields']:registries[field['field_id']]=field
    def add(fid,section,producer,version,inputs,output,quality,unit,window,api,ui,proof=None,formula='NOT_VERIFIABLE',data='SOURCE_NOT_PRESENT',browser='NOT_VERIFIABLE',fix='PRODUCER'):
        route=routes.get(api,{})
        verdict=dict(zip(AXES,[formula,data,'PASS_SCOPED' if route.get('verdict')=='PASS_SCOPED' else 'SOURCE_NOT_PRESENT' if route.get('verdict')=='SOURCE_NOT_PRESENT' else 'NOT_VERIFIABLE',browser,'ONGOING_REAL_OBSERVATIONS_NOT_STATISTICAL_ACCEPTANCE','NOT_PROVEN_RECONSTRUCTED']))
        rows.append(dict(zip(KEYS,[fid,section,producer,version,inputs,day if output else None,membership if output else None,'LATEST_MEMBERSHIP_CORRECTED; PIT_ELIGIBLE=false',output,quality,unit,window,proof,api,ui,dict(verdict=browser,evidence='iab/BROWSER_DOM_RECORDS.json',scope='Only recorded observations; no inherited field-level PASS'),verdict,fix])))
    mapping={'core':('V4-03','src/v4/factors/core.py','stocks','fields'),'profile':('V4-04','src/v4/profile_core.py','stocks','derived_fields'),
             'sector':('V4-08','src/sector/native_r5.py','sectors','fields'),'prewatch':('V4-09','src/v4/stock_prewatch.py','stocks','fields'),
             'relative_sector':('V4-13','src/workbench_analysis/v4_13_loo_runtime.py','stocks','fields')}
    tested={c['field'].split('.')[-1] for c in oracle['results'] if c['domain']=='STOCK' and c['passed']}
    sector_tested={c['field'] for c in oracle['results'] if c['domain']=='SECTOR' and c['passed']}
    rps_tested={c['field'].split('.')[-1] for c in oracle['results'] if c['domain']=='RPS' and c['passed']}
    for key,(module,path,domain,field_container) in mapping.items():
        owner=owners[key];p=ROOT/owner['path'];assert ref(p)['sha256']==owner['sha256'];sample=load(p)
        if isinstance(sample,list):sample=sample[0]
        fields=sample.get(field_container,{})
        if key=='profile':fields=dict(fields,**sample.get('states',{}))
        if not fields:fields={'record':sample}
        for field,cell in fields.items():
            if not isinstance(cell,dict):cell=dict(value=cell)
            inputs=cell.get('source_publications') or cell.get('source_refs')
            if not inputs:inputs=load(OUT/'oracle/INPUT.json')['source_bindings']
            formula='PASS_CURRENT_FULL_POOL_RANK' if key=='core' and field in rps_tested else 'PASS_SCOPED_REAL_STOCK_SAMPLE' if key=='core' and field in tested else 'PASS_SCOPED_4_SECTORS' if key=='sector' and field in sector_tested else 'NOT_VERIFIABLE_THIS_ROUND'
            add(module+'.'+field,'TASK ALG01/02; REV2 §§62A–69/81.2',ref(ROOT/path),cell.get('contract_id') or cell.get('model_contract_id') or cell.get('producer') or sample.get('contract_id'),inputs,
                dict(owner=owner,field=field_container+'.'+field,sample_identity=sample.get('security_id',sample.get('sector_id'))),
                cell.get('quality',cell.get('quality_state','SEE_EXACT_OWNER')),cell.get('unit',registries.get(field,{}).get('unit','UNIT_NOT_DECLARED_BY_OWNER_OR_REGISTRY')),
                dict({k:cell[k] for k in ('window_start_trade_date','window_end_trade_date','actual_count','calendar_span','suspended_count','n','k','time_role') if k in cell},registered_window={k:v for k,v in registries.get(field,{}).items() if 'window' in k or k in ('as_of','time_role')}),
                '/api/v4/'+domain,'/v4/research/'+domain+' : DataTable/EvidenceDrawer',proof='oracle/OUTPUT.json' if formula.startswith('PASS') else None,formula=formula,data='HASH_BOUND_T0_SAMPLE',fix='INDEPENDENT_ALGORITHM_AUDIT')
    for axis in ('trend_axis','breadth_axis','participation_axis','stress_level','stress_change','regime'):
        add('V4-05.market.'+axis,'TASK ALG02.D; REV2 §62B.1',ref(ROOT/'src/workbench_analysis/r43_market_replay.py'),'MARKET_REGIME_V1 / DAILY_REBALANCED_RESEARCH_INDEX_FP05_V2',
            load(OUT/'oracle/INPUT.json')['market_path']['sources'],dict(owner=owners['market'],field='regime' if axis=='regime' else 'trend.trend_axis' if axis=='trend_axis' else 'axes.'+axis),'RECONSTRUCTED_OBSERVED','state','T0 with explicit prior3/lag5/20-session windows','/api/v4/market','/v4/research/market : four axes',proof='oracle/OUTPUT.json',formula='PASS_SCOPED_T0_RAW_PATH_AND_FIVE_POINT_REGIME',data='HASH_BOUND_T0',fix='INDEPENDENT_MARKET_AUDIT')
    for module in old['modules']:
        fid=module['module']
        if fid in {m[0] for m in mapping.values()} or fid=='V4-05':continue
        owner=module.get('owner');path=module.get('producer_file') or module.get('producer_files')
        if fid=='V4-10':owner=owners['focus']
        if fid=='V4-15':owner=None
        if owner and owner.get('path'):owner=owners.get(next((k for k,v in owners.items() if v.get('path')==owner['path']),''),owner)
        add(fid,'TASK ALG01; existing accepted stage contract (scope retained)',path,module.get('owner_contract_id') or module.get('contract_files'),
            {'dated_bindings':owners if owner else {},'contract_bindings':module.get('contract_files',[])},dict(owner=owner,field='module scope') if owner else None,
            'FIELD_LOCAL' if owner else 'SOURCE_NOT_PRESENT','PER_EXACT_FIELD_REGISTRY','PER_EXACT_OWNER',module.get('bff_route'),None,
            proof='oracle/OUTPUT.json' if fid in ('V4-11','V4-15') else None,formula='PASS_SCOPED_D0_THRESHOLD_RULES' if fid=='V4-11' else 'PASS_SCOPED_FOCUS_PATH_ONLY_NOT_COHORT' if fid=='V4-15' else 'NOT_VERIFIABLE',data='HASH_BOUND_T0' if owner else 'SOURCE_NOT_PRESENT')
        if fid=='V4-15':rows[-1]['current_verdict']['ALGO_FORMULA_VALID']='NOT_VERIFIABLE_VALIDATION_COHORT_SOURCE_NOT_PRESENT';rows[-1]['test_oracle']=None
    focus_manifest=load(ROOT/load(ROOT/'config/core_product_focus_read_authority_r2.json')['manifest']['path'])
    add('Focus.lifecycle_and_price_path','TASK ALG02.E / UI04 FP08',ref(ROOT/'src/focus_tracker/core_product_focus_r2.py'),'D2_FOCUS_VALIDITY_BRIDGE_R2',focus_manifest['source_bindings'],dict(owner=focus_manifest['projection'],field='episodes / observations / anchors / outcomes'),'FIELD_LOCAL','return_fraction','Anchor close through actual target-session path','/api/v4/focus','/v4/research/focus',proof=['oracle/OUTPUT.json','FOCUS_VALIDITY_REPAIR_RECEIPT.json'],formula='PASS_SCOPED_THREE_REAL_EPISODES_AND_EXPLICIT_BOUNDARY_TESTS',data='HASH_BOUND_T0_READ_PROJECTION')
    for entry in old['six_entries']:
        name=entry['entry'];api='/api/v4/'+('sources' if name=='diagnostics' else name);seen=[r for r in records if r.get('module')==name or r.get('scenario')==name]
        bindings=dict(entry['owner_bindings'])
        if 'forward' in bindings:bindings['forward']=focus_manifest['projection']
        add('UI.'+name,'TASK UI04/QA05; REV2 §§62A–69',ref(ROOT/'src/workbench_service/core_product_bff_r1.py'),'CORE_PRODUCT_BFF_R1 + CORE_PRODUCT_FOCUS_READ_R2',bindings,dict(owner_bindings=bindings,field='entry components'),'FIELD_LOCAL','PER_FIELD','DATED_T0',api,'/v4/research/'+name,proof='API_FIELD_CONTRACT_AUDIT.json',data='HASH_BOUND_T0',browser='PASS_SCOPED_RECORDED_DOM' if seen else 'NOT_VERIFIABLE',fix='UI_AND_API_AUDIT')
    for fp in old['FP01_FP14']:
        add(fp['card'],'TASK packages ALG/BFF/UI/QA; FP01–FP14 latest ingress',None,'FP_TASK_CONTRACT_R1',{},None,'FEATURE_SPECIFIC','FEATURE_SPECIFIC','FEATURE_SPECIFIC',None,None,proof='UI_FEATURE_ACCEPTANCE_MATRIX.md',formula='SEE_FIELD_ROWS',fix='REMAINING_WORK_LEDGER')
        rows[-1]['current_verdict']['GO_FORWARD_VALIDATION']='WAIT_REAL_DAY' if fp['card']=='FP02' else 'SEE_REMAINING_WORK_LEDGER'
    for row in rows:assert set(KEYS)<=row.keys() and set(AXES)==set(row['current_verdict'])
    write(OUT/'CORE_ALGO_UI_LINEAGE_MATRIX.json',dict(contract='CORE_ALGO_UI_LINEAGE_MATRIX_R2',BASE_SHA=base,code_sha_at_generation=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),T0=day,source_head=ref(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),rows=rows,required_fields=list(KEYS),verdict_axes=list(AXES),status='FIELD_SCOPED_EVIDENCE; FULL_PRODUCT_EXTERNAL_ACCEPTANCE_NOT_GRANTED'))
    print(json.dumps(dict(rows=len(rows),required_fields=len(KEYS),verdict_axes=len(AXES))))

if __name__=='__main__':main()
