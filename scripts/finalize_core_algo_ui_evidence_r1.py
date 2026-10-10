"""Build explicit audit inventory from hash-bound local artifacts, without acceptance grants."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,gzip,subprocess,os,zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/core_algo_ui_r1_20261010'
def load(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:
        return [json.loads(x) for x in f if x.strip()] if '.jsonl' in p.name else json.load(f)
def ref(p):
    return dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,d):
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(tmp,p)
def main():
    code_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    h=load(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=h['accepted_trade_date'];head=ref(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    assert head['sha256']=='55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e'
    bindings=h['owners'][day];context=load(OUT/'API_UI_NUMERIC_SAMPLES.json')['home']['context']
    bff=ref(ROOT/'src/workbench_service/core_product_bff_r1.py');ui=[ref(p) for p in sorted((ROOT/'src/workbench_service/static/core-product-r1').glob('*.js'))]
    rows=[]
    modules={3:('core','src/v4/factors/core.py'),4:('profile','src/v4/profile_core.py'),5:('market','src/workbench_analysis/r43_market_replay.py'),6:(None,None),7:('seed','src/v4/base_seed.py'),8:('sector','src/sector/rotation_r5.py'),9:('prewatch','src/v4/stock_prewatch.py'),10:('lifecycle','src/v4/research_state.py'),11:('focus','src/workbench_analysis/r43_focus_replay.py'),12:('events','src/workbench_analysis/v4_12_structure_engine.py'),13:('relative_sector','src/workbench_analysis/v4_13_loo_runtime.py'),14:(None,'src/workbench_analysis/v4_14_full_dag.py'),15:('forward','src/workbench_analysis/r43_focus_replay.py')}
    for n in range(3,23):
        kind,producer=modules.get(n,(None,None));owner=bindings.get(kind)
        configs=[ref(p) for p in sorted((ROOT/'config').glob('v4_'+str(n).zfill(2)+'*.json')) if 'fixture' not in p.name and 'vector' not in p.name]
        contracts=[]
        for r in configs:
            d=load(ROOT/r['path']);contracts.append(dict(**r,contract_id=d.get('contract_id'),version=d.get('version',d.get('contract_version')),status=d.get('status')))
        sample=None
        if owner:
            d=load(ROOT/owner['path']);sample=d[0] if isinstance(d,list) else (d.get('rows') or [d])[0]
        fields=(sample or {}).get('fields',{});units=sorted({str(c.get('unit')) for c in fields.values() if isinstance(c,dict) and c.get('unit')})
        sample_metadata={k:{a:v for a,v in c.items() if a in ('value','unit','quality','contract_id','parameter_set_id','window_start_trade_date','window_end_trade_date','actual_count','calendar_span','suspended_count','input_digest','output_digest')} for k,c in list(fields.items())[:10] if isinstance(c,dict)}
        actual_producer=ref(ROOT/producer) if producer and (ROOT/producer).exists() else None
        rows.append(dict(module=f'V4-{n:02}',producer_file=actual_producer,producer_file_not_resolved=producer if producer and actual_producer is None else None,contract_files=contracts,owner=owner,owner_contract_id=(sample or {}).get('contract_id'),T0=day if owner else None,member_set_asof=context['member_set_asof'] if owner else None,knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP' if owner else 'NO_NEW_DATED_PUBLICATION_VERIFIED',PIT_ELIGIBLE=False,units=units or ['PER_FIELD_REGISTRY_OR_NATIVE_SOURCE_METADATA'],window_scope='FIELD_EXPLICIT_ACTUAL_BARS_OR_MARKET_SESSIONS; NONCOMPUTED_ITEMS_NOT_VERIFIABLE',bff=bff if owner else None,ui=ui if owner else [],input_source_sha=owner.get('sha256') if owner else None,evidence=['oracle/OUTPUT.json','API_FIELD_CONTRACT_AUDIT.json'] if owner else ['CONTRACT_SYNC_RECEIPT.json'],numeric_verdict='PASS_SCOPED' if n in (3,5,8,10,11,15) else 'NOT_VERIFIABLE_THIS_ROUND',product_verdict='SCOPED_READ_ONLY' if owner else 'NOT_VERIFIABLE',external_verdict='NOT_GRANTED',open_reason='Full recursive reducer/detector, all boundary samples and historical first-availability are not certified by scoped arithmetic.' if owner else 'Contract/engineering artifacts exist; this round does not activate or infer a permitted real source from them.'))
        rows[-1]['sample_field_metadata']=sample_metadata
        if n==16:
            policy=load(ROOT/'config/v4_16_current_runtime_entrypoints_v1.json')
            rows[-1]['operational_policy']={k:policy[k] for k in ('runtime_authorized','first_real_shadow_authorized','entry_policy','external_acceptance')}
        if n==17:rows[-1]['operational_policy']=load(ROOT/'config/v4_17_shadow_ui_source_v1.json')
    for name in ('FEP-E1','FEP-E2','FEP-E3','FEP-E4','FEP-E5'):
        rows.append(dict(module=name,contract_files=[ref(p) for p in sorted((ROOT/'config').glob('fep*.json')) if name[-2:].lower() in p.name],producer_files=[ref(p) for p in sorted((ROOT/'src/workbench_analysis'/name.lower().replace('-','_')).glob('*.py'))],owner=None,bff_route='/api/v4/forward/fep',T0=None,PIT_ELIGIBLE=False,numeric_verdict='SOURCE_NOT_PRESENT',product_verdict='NOT_VERIFIABLE',external_verdict='NOT_GRANTED',open_reason='No legally admitted T0 operational model read owner; no predictions or probabilities generated.'))
    six=[]
    for name,kinds in [('home',['focus','rotation','market']),('sectors',['sector','rotation']),('stocks',['core','profile','period_raw','period_adjusted']),('focus',['forward','focus']),('market',['market','raw','core']),('diagnostics',['diagnostic'])]:
        six.append(dict(entry=name,owner_bindings={k:bindings[k] for k in kinds},bff=bff,ui_files=ui,context_token=head['sha256'],T0=day,member_set_asof=context['member_set_asof'],PIT_ELIGIBLE=False,API_evidence='API_FIELD_CONTRACT_AUDIT.json',IAB_evidence='CORE_ALGO_UI_IAB_QA_INDEX.json',product_verdict='PASS_SCOPED_READ_VIEW; FULL_CONTRACT_OPEN',algorithm_verdict='SEE_MODULE_SCOPES',external_verdict='NOT_GRANTED'))
    fp_names=['生产语义','数据总线','BFF字段','六入口框架','今日总览','板块研究','个股画像图表','Focus生命周期','市场与事件','Forward结算','诊断与旧模块','PIT回放比较','浏览器验收','生产发布运营']
    gaps={1:'原用户事件权限链保持，独立外部签收未获授予',2:'10/12真实新日闭环 WAIT_REAL_DAY；当期读域不暂停',3:'alias/out-of-universe historical identity and absent producers',4:'完整合同按每域缺口保持OPEN',5:'Focus变化不等同于全部PREWATCH/结构变化；观察池独立来源未接入',6:'完整Rotation reducer、10/20日扩散、cluster、27未映射证券身份逐项解释',7:'历史别名/退市、新股边界、高级竞争假设完整Owner',8:'失效重入边界真实样本缺失；自动写入未激活',9:'分钟首封/炸板/新闻实际source缺失；全市场趋势与宽度完整独立重建待验',10:'VALIDATION_COHORT_OWNER_NOT_PRESENT; maturity/settlement/statistics/FEP gated',11:'旧模块迁移/独立Shadow不存在当期验收Source；UI健康计数仅None字段代理',12:'首次可用时点缺证据；corrected compare单独可用',13:'双宽六域和fault recovery已测；OS真实离线/新日期串读/全部罕见UI边界未现场验证',14:'生产原端口未重启；FP14旧BLOCKED与外部发布门未改'}
    fps=[dict(card=f'FP{n:02}',name=fp_names[n-1],status='WAIT_REAL_DAY' if n==2 else 'NOT_VERIFIABLE' if n in (1,10,14) else 'PASS_SCOPED',full_contract_status='OPEN',precise_open=gaps[n],external_acceptance='NOT_GRANTED') for n in range(1,15)]
    write(OUT/'CORE_ALGO_UI_LINEAGE_MATRIX.json',dict(contract='CORE_ALGO_UI_LINEAGE_MATRIX_R1',code_result_sha=code_sha,BASE_SHA='64a0e31390765027f96b6a537bbf7f044abf6c83',source_head=head,context=context,six_entries=six,FP01_FP14=fps,modules=rows,status='SCOPED_ENGINEERING_REPAIR_COMPLETE; FULL_PRODUCT_ACCEPTANCE_OPEN'))
    records=load(OUT/'iab/BROWSER_DOM_RECORDS.json');images=[]
    for p in sorted((OUT/'iab').glob('*.jpg')):
        stat=p.stat();images.append(dict(**ref(p),scenario=p.stem,viewport='1920x1080' if '1920' in p.stem else '1366x768',screenshot_time_utc=datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat(),T0=day,head_sha=head['sha256'],code_sha=code_sha,browser='Codex IAB',service='28768 explicit fault injection' if 'fault' in p.stem else '28767 isolated real accepted owners; not production port28765'))
    dom_correspondence=[]
    for domain,needle,source in [('home','5224','API_UI_NUMERIC_SAMPLES.json:home.counts.stocks'),('sector','322','sector current mapped unique members'),('stock_month','13.59','actual native history QFQ final bar'),('focus','已发布 10 条','Focus outcomes for 三一重能'),('market','19003.65','native RAW amount CNY/1e8'),('diagnostics','5210','diagnostic raw row_count')]:
        matching=[r for r in records if r.get('module')==domain and r.get('phase')=='final_loaded']
        dom_correspondence.append(dict(domain=domain,source=source,needle=needle,checks=[dict(viewport=r['viewport'],matched=needle in r.get('text',''),overflow=r.get('overflow'),timestamp=r['timestamp']) for r in matching]))
    write(OUT/'CORE_ALGO_UI_IAB_QA_INDEX.json',dict(browser='Codex IAB',source_head=head,code_result_sha=code_sha,T0=day,images=images,dom_correspondence=dom_correspondence,records_file=ref(OUT/'iab/BROWSER_DOM_RECORDS.json'),injection_scope='QA loopback transport only; business data are actual accepted owner results; no fixture business verdict',production_port_restarted=False,production_final_browser_acceptance='WAIT_USER_NORMAL_RESTART',unverified=['OS_actual_offline','actual_date_switch_1012','complete_alias_and_delisted_UI','full_detector_and_rotation_reducer','FP13_FP14_full_external_joint_acceptance']))
    pack=load(ROOT/'config/core_product_read_authority_r1.json');write(OUT/'LOCAL_MATERIALIZATION_RECEIPT.json',dict(authority=ref(ROOT/'config/core_product_read_authority_r1.json'),manifest=load(ROOT/pack['manifest']['path']),note='history sqlite stays ignored on G; reproduce with build_core_product_read_pack_r1.py from accepted local sources; not a new factor owner'))
    print(json.dumps(dict(matrix_rows=len(rows),FP_cards=len(fps),screenshots=len(images),dom=dom_correspondence),ensure_ascii=False))
if __name__=='__main__':main()
