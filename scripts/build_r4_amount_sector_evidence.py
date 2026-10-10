"""Read-only source audit and isolated R4 A/B evidence, G-only temporary storage."""
from immediate_r3_common import *
import csv, io, sys, zipfile
from collections import Counter
from statistics import median, fmean
sys.path.insert(0,str(ROOT/'src'))
from sector.d2_admission_candidate_r4 import extract, FIELDS

D=ROOT/'docs/evidence/v4_current_snapshot_r4_20261010'
A=D/'01_A_AMOUNT';B=D/'02_B_SECTOR'
R3=OUT/'11_DEEPENING'
DIMENSIONS=['FORMULA_LOGIC','DATED_INPUT','FORMAL_OWNER','API_UI_BINDING','HISTORICAL_AS_RECORDED_PIT','FUTURE_MATURED_OUTCOME']

def dimensions(known=False):
    return dict(zip(DIMENSIONS,['PASS_SCOPED','PASS_SCOPED' if known else 'SOURCE_NOT_PRESENT',
        'PASS_SCOPED' if known else 'NOT_AUTHORIZED','NOT_TESTED',
        'UNKNOWN','NOT_TESTED']))

def main():
    A.mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
    # Consult and bind full applicable contracts, not just headings.
    contracts=[p for p in (ROOT/'docs/evidence').glob('*REV2*20260925.md')]+[p for p in (ROOT/'docs/evidence').glob('*REV4*FEP*')]
    contracts += [D/'V4_R4_CURRENT_SNAPSHOT_REPAIR_AND_ADMISSION_TASKS_20261010.md',D/'V4_R3_INDEPENDENT_EXTERNAL_AUDIT_R1_20261010.md',ROOT/'AGENTS.md']
    for p in contracts:p.read_text(encoding='utf8')
    for p in [OUT/'08_REMAINING_LEDGER.json',ROOT/'config/v4_08_b2_machine_ast_r5.json',ROOT/'config/v4_10_input_provenance_r1_2.json']:
        load(p);contracts.append(p)
    head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');day=head['accepted_trade_date'];owners=head['owners'][day]
    old=load(R3/'PIT_ORIGINAL_INGEST_AND_MISSING_DAYS.json')['formal_Amount_A_h21']
    calendar=load(old['calendar']);sessions=calendar['session_dates'];ix=sessions.index(old['target']);window=sessions[ix-20:ix+1]
    assert window==old['required_sessions'] and len(window)==21
    # Enumerate all actual project receipt/archive candidates. Never infer availability from mtime.
    inventories=[];found=[]
    roots=[ROOT/'data/v4',ROOT/'docs/evidence',Path('G:/codex_tmp'),Path('D:/Users/lps/Desktop/阶段任务'),Path('D:/Titan线下采集'),Path('D:/TitanTest'),Path('D:/new_tdx/T0002/hq_cache')]
    for root in roots:
        files=[];errors=[]
        if root.exists():
            for base,dirs,names in os.walk(root,onerror=lambda e:errors.append(str(e))):
                for name in names:
                    low=name.lower()
                    if 'a04_go_forward_r3' in base or any(s in low for s in ['member','membership','capture','receipt','freeze','tdxhy','tdxzs','block.dat','backup','archive']) or low.endswith('.zip'):
                        files.append(Path(base)/name)
        entries=[]
        for p in files:
            entry=dict(path=str(p),bytes=p.stat().st_size)
            if p.stat().st_size < 20_000_000:
                entry.update(sha256=sha(p));
                if p.suffix=='.json':
                    try:
                        obj=json.loads(p.read_text(encoding='utf8'))
                        if isinstance(obj,dict):
                            for key in ['target_trade_date','trade_date','observed_at','first_available_at','captured_at','membership_basis','contract_id','publication_id']:
                                if key in obj:entry[key]=obj[key]
                            if obj.get('membership_basis')=='PIT_OBSERVED_ACCEPTED' and obj.get('contract_id')=='AMOUNT_A_FORMAL_AUTHORITY_GO_FORWARD_V1':found.append((p,obj))
                    except (ValueError,UnicodeError):pass
            else:entry['byte_hash_status']='LARGE_ARCHIVE_NOT_REHASHED_REUSE_BOUND_RECEIPT'
            if p.suffix.lower()=='.zip':
                try:
                    with zipfile.ZipFile(p) as archive:
                        members=archive.infolist();entry['archive_member_count']=len(members)
                        entry['archive_members']=[dict(name=x.filename,size=x.file_size,crc=x.CRC) for x in members]
                        inspected=[]
                        for x in members:
                            if x.file_size<5_000_000 and not x.is_dir() and any(s in x.filename.lower() for s in ['member','membership','capture','receipt','freeze','tdxhy','tdxzs','block.dat']):
                                raw_bytes=archive.read(x);record=dict(name=x.filename,sha256=hashlib.sha256(raw_bytes).hexdigest(),crc_verified=True)
                                try:
                                    obj=json.loads(raw_bytes)
                                    if isinstance(obj,dict):
                                        record['capture_fields']={k:obj[k] for k in ['trade_date','target_trade_date','observed_at','first_available_at','captured_at','membership_basis','contract_id'] if k in obj}
                                except (ValueError,UnicodeError):pass
                                inspected.append(record)
                        entry['small_source_members_inspected']=inspected
                        entry['historical_original_admission']='NO_ADDITIONAL_ACCEPTED_H21_OBSERVATION_DISCOVERED; ARCHIVE_RECEIPT_NOT_ASOF_AUTHORITY'
                except (OSError,zipfile.BadZipFile,RuntimeError) as exc:entry['archive_error']=str(exc)
            entries.append(entry)
        inventories.append(dict(root=str(root),exists=root.exists(),candidate_count=len(entries),errors=errors,entries=entries))
    observed={obj['target_trade_date']:(p,obj) for p,obj in found}
    from workbench_analysis.amount_a_go_forward_r3 import read_verified_observations
    verified=read_verified_observations(ROOT,[binding(p) for p,obj in found])
    assert len(verified)==len(observed)
    missing=[s for s in window if s not in observed]
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=['trade_date','source_path','raw_bytes_sha','first_capture_timestamp','collector_run_id','membership_version','canonical_trade_date','availability_verified','accepted_authority','classification']);writer.writeheader()
    for s in missing:writer.writerow(dict(trade_date=s,source_path='',raw_bytes_sha='',first_capture_timestamp='',collector_run_id='',membership_version='',canonical_trade_date=s,availability_verified=False,accepted_authority='',classification='NO_ORIGINAL_BYTES'))
    markdown(A/'A_H21_MISSING_20_SESSION_PROVENANCE.csv',buffer.getvalue())
    full=A/'A_H21_SEARCH_FULL_INVENTORY.json.gz';temp=full.with_suffix('.tmp')
    temp.write_bytes(gzip.compress(json.dumps(inventories,ensure_ascii=False,sort_keys=True).encode(),mtime=0));os.replace(temp,full)
    summaries=[dict(root=x['root'],exists=x['exists'],candidate_count=x['candidate_count'],errors=x['errors'],archive_count=sum('archive_member_count' in e for e in x['entries']),small_archive_members_inspected=sum(len(e.get('small_source_members_inspected',[])) for e in x['entries'])) for x in inventories]
    write(A/'A_H21_SOURCE_SEARCH_MANIFEST.json',dict(contract_bindings=[binding(p) for p in contracts],calendar=old['calendar'],recomputed_window=window,verified_missing_sessions=missing,
        available_observations=[binding(p) for p,obj in found],locations=summaries,full_inventory=binding(full),
        git_history_search=dict(command='git log --all --name-only --format= -- data/v4/a04_go_forward_r3 docs/evidence',output=subprocess.check_output(['git','log','--all','--name-only','--format=','--','data/v4/a04_go_forward_r3'],text=True,cwd=ROOT)),
        Drive_status='REMOTE_ORIGINAL_RECEIPT_SEARCH_NOT_EXECUTED_BY_A_AGENT; LOCAL_DELIVERY_RECEIPTS_ENUMERATED',
        Drive_root_search_receipt=binding(D/'00_R3_REUSE/DRIVE_SOURCE_SEARCH_SCOPE.json') if (D/'00_R3_REUSE/DRIVE_SOURCE_SEARCH_SCOPE.json').exists() else None,
        terminal_state='H21_STRICT_HISTORY_NOT_VERIFIABLE',no_mtime_availability_inference=True,search_scope='NAMED_EXISTING_LOCAL_ARCHIVES_NOT_ALL_DISKS',formal_consumer_enabled=False))
    markdown(A/'A_H21_STRICT_VS_CORRECTED_BOUNDARY.md','# H21 严格与 corrected 边界\n\n原目标仍为 2026-09-30。绑定正式 calendar 重算21会话，实际 accepted observation 仅9/30，前20会话无原件。H21_STRICT_HISTORY_NOT_VERIFIABLE；FORMAL_H21_BLOCKED_HISTORICAL_EVIDENCE。搜索范围及逐文件SHA见 manifest；未声称遍历整机未知存储或远程原件。\n\nSTRICT_H21_PIT 必须有每个会话实际同日首获、正式成员与RAW金额/停牌收据。CORRECTED_LATEST_MEMBERSHIP_RESEARCH 只沿既有运营研究读域，PIT_ELIGIBLE=false / SURVIVORSHIP_BIAS_PRESENT，不写正式Amount Owner。10/09最新成员不能回填九月。未来capture复用 amount_a_go_forward_r3.accepted_observation_payload 与 immutable append，需正式accepted Head和成员授权；本轮不执行写入。未来数据不能证明旧日首获。\n')
    bindings=load(R3/'AMOUNT_FIELD_FAMILY_API_BINDINGS.json')
    raw=load(owners['raw']);core=load(owners['core']);native=load(owners['sector']);market=load(owners['market']);ci={r['security_id']:r for r in core}
    diffs=[]
    total=sum(r['amount'] for r in raw);expected=bindings['market']['data']['amount_cny']
    diffs.append(dict(field='market.amount_cny',expected=expected,actual=total,delta=total-expected,input_sha=owners['raw']['sha256'],reason='UNIQUE_RAW_SECURITY_SUM_CNY',sample_date=day))
    assert len(raw)==len({r['security_id'] for r in raw})
    for row in native:
        vals=[ci[m]['fields']['amount_ratio20']['value'] for m in set(row['member_ids']) if m in ci and ci[m]['fields']['amount_ratio20']['value'] is not None]
        actual=median(vals) if vals else None;expected=row['fields']['participation_proxy']['value']
        diffs.append(dict(field='sector.participation_proxy',entity_id=row['sector_id'],expected=expected,actual=actual,delta=None if actual is None or expected is None else actual-expected,input_sha=owners['core']['sha256'],output_sha=owners['sector']['sha256'],sample_date=day,reason='MEDIAN_KNOWN_STOCK_AMOUNT_RATIO20_UNIQUE_MEMBERS'))
    sample=bindings['stock'];r=next(r for r in raw if r['security_id']==sample['raw']['security_id'])
    diffs.append(dict(field='stock.amount',expected=sample['amount']['value'],actual=r['amount'],delta=r['amount']-sample['amount']['value'],input_sha=owners['raw']['sha256'],sample_date=day))
    ratios=ci[r['security_id']]['fields']['amount_ratio20']['value'];diffs.append(dict(field='stock.amount_ratio20',expected=sample['ratio20']['value'],actual=ratios,delta=ratios-sample['ratio20']['value'],input_sha=owners['core']['sha256'],reason='SOURCE_TO_PRIOR_API_BINDING_SPOT_CHECK_NOT_NEW_RUNTIME_QA',sample_date=day))
    history_ref=bindings['market']['source']['history'];history_path=checked(history_ref)
    selected=set(sorted(ci)[::max(1,len(ci)//8)][:8]);selected.add(r['security_id'])
    with gzip.open(history_path,'rt',encoding='utf8') as stream:
        for line in stream:
            item=json.loads(line);sid=item['security_id']
            if sid not in selected:continue
            bars=[b for b in item['bars'] if b['trade_date']<=day]
            if len(bars)<21 or bars[-1]['trade_date']!=day:continue
            actual=bars[-1]['amount']/fmean(b['amount'] for b in bars[-21:-1])
            expected=ci[sid]['fields']['amount_ratio20']['value']
            diffs.append(dict(field='stock.amount_ratio20_independent_window',entity_id=sid,expected=expected,actual=actual,delta=None if expected is None else actual-expected,input_sha=history_ref['sha256'],source_availability_at=None,reason='EXACT_21_ACTUAL_NATIVE_BARS_PRIOR20_FMEAN',sample_date=day,window=[b['trade_date'] for b in bars[-21:]]))
    families=[dict(field='stock.amount / amount_ratio20 / amr20_mean_prior',formula='RAW amount CNY; ratio20 CURRENT/prior20 actual mean; amr20_mean_prior independent RAW producer',window='CURRENT / EXACT_PRIOR20',unit='CNY_YUAN / dimensionless',adjustment='RAW amount unchanged by QFQ',consumer='core_product_bff_r1 stock profile; confirmation/raw producer',sources=[owners['raw'],owners['core']],states=dimensions(True)),
        dict(field='sector.participation_proxy',formula='median known member stock amount_ratio20; unique dated members',window='stock prior20 ratios at T0',unit='dimensionless',adjustment='RAW amount ratios',consumer='BFF sector table/detail',sources=[owners['sector'],owners['core']],states=dimensions(True)),
        dict(field='sector.Amount A',formula='H21 common valid members: sum RAW T / mean prior20 daily sums',window=window,unit='dimensionless; sums CNY_YUAN',adjustment='RAW only; confirmed suspended zero else UNKNOWN',consumer='formal disabled; never substitute stock ratio or proxy',sources=[binding('src/workbench_analysis/amount_a_go_forward_r3.py')],states=dimensions(False)),
        dict(field='market.total_amount',formula='sum unique actual T0 RAW amount; no flattened sectors',window='T0',unit='CNY_YUAN API; CNY_YI display /1e8',adjustment='RAW only',consumer='market breadth BFF/UI',sources=[owners['raw'],owners['market']],states=dimensions(True))]
    for family in families:family.update(T0=day,first_available=None,member_version=head['membership_mode'],null_policy='UNKNOWN_NOT_ZERO',supplier_economic_equivalence='ECONOMIC_EQUIVALENCE_UNPROVEN',next_action='Independent source/runtime acceptance; strict H21 remains disabled')
    stock_family=families.pop(0)
    families[:0]=[dict(stock_family,field='stock.amount',formula='TDX Native RAW amount CNY_YUAN',window='T0'),dict(stock_family,field='stock.amount_ratio20',formula='current native amount / fmean prior20 actual native amounts; 21-bar window',window='EXACT_PRIOR20_ACTUAL'),dict(stock_family,field='stock.amr20_mean_prior',formula='independent RAW producer current / prior20 RAW mean',states=dimensions(False),sources=[binding('src/v4/target_fact_producers_r4.py'),binding('src/workbench_analysis/today_research_factors_v3_3.py')],current_source_verification='NOT_TESTED; no expansion from stock ratio spot to AMR owner')]
    write(A/'A_AMOUNT_CONSUMER_LINEAGE.json',dict(families=families,prior_api_bindings=bindings,formal_consumer_enabled=False,source_authority='TDX_NATIVE_RAW_AMOUNT',representation_reused='14292 DIRECT_BINARY32 / 995 DECIMAL_EQUAL / 345 HALF_UP_BINARY32; NOT ECONOMIC EQUIVALENCE'))
    failures=[r for r in diffs if r.get('delta') is not None and abs(r['delta'])>1e-10]
    write(A/'A_AMOUNT_INDEPENDENT_DIFF.json',dict(rows=diffs,comparison_count=len(diffs),failure_count=len(failures),tolerance=1e-10,scope='CURRENT_RAW_AMOUNT_SUM_AND_NATIVE_MEDIAN; STOCK_SOURCE_MAPPING_AND_9_PRIOR20_WINDOW_SPOTS',not_claimed=['full stock universe ratio-window recalculation','new live API/DOM','supplier economic equivalence','AMR20 formal owner passed'],source_bindings=[owners['raw'],owners['core'],owners['sector'],owners['market'],history_ref]))
    markdown(A/'A_FIX_AND_VERDICT.md','# Amount 定点结论\n\n缺成员会话时旧代码把 comparable_member_count/coverage 显示为0；已修为null并记录 observed_session_count。原缺20会话是历史事实边界，并非继续测试即可恢复。当前RAW市场总额、400板块参与代理及股票源映射独立核对见diff；没有错误消费者替换证据，保留原TDX Native主权威。\n\nAMOUNT_ENGINEERING_AND_PROVENANCE_AUDIT_PASS_SCOPED；FORMAL_H21_BLOCKED_HISTORICAL_EVIDENCE。经济口径继续 ECONOMIC_EQUIVALENCE_UNPROVEN，跨模块 AUD_AMOUNT_A_06 独立保持OPEN。新增源原件或正式首获链出现前门保持关闭；远程原件未查范围如实列明。\n')
    extracted_native=[dict(entity_type='SECTOR',sector_id=row['sector_id'],trade_date=row['trade_date'],
        member_ids=row['member_ids'],member_set_asof=row['member_set_asof'],fields={'dq5':{k:row['fields']['dq5'].get(k) for k in ('value','quality','reason_code','producer','parameter_set_id','window_identity')}}) for row in native]
    candidates=[extract(row,source_binding=owners['sector'],cutoff=day+'T23:59:59+08:00') for row in extracted_native]
    assert len(candidates)==400 and len({x['entity_id'] for x in candidates})==400
    write(B/'B_SECTOR_READINESS_CANDIDATE_INPUT.json',dict(source_binding=owners['sector'],extraction='EXACT_MINIMAL_NATIVE_FIELDS; DQ5_METADATA_SUBSET_NOT_NEW_OWNER',rows=extracted_native))
    write(B/'B_SECTOR_READINESS_CANDIDATE_OUTPUT.json',dict(rows=candidates))
    write(B/'B_SECTOR_READINESS_CANDIDATE_RECEIPT.json',dict(status='ENGINEERING_CANDIDATE_PASS_SCOPED',input_sha=owners['sector']['sha256'],code=binding('src/sector/d2_admission_candidate_r4.py'),input_count=len(native),output_count=len(candidates),unique_count=400,type_counts=dict(Counter(r['sector_type'] for r in native)),dq5_known_count=sum(r['fields']['dq5']['value'] is not None for r in native),missing_field_counts={f:sum(f in r['missing_fields'] for r in candidates) for f in FIELDS},formal_owner='SECTOR_D2_OWNER_OPEN',accepted=False,reducer_invoked=False,reason='REQUIRED_PRODUCER_INPUTS_ABSENT; DO_NOT_INVOKE_FORMAL_REDUCER_WITH_INVENTED_FACTS'))
    gaps=load(OUT/'09_CONTINUATION/SECTOR_D2_EXACT_CONTRACT_GAPS.json')['missing_fields']
    write(B/'B_SECTOR_PRODUCER_INPUT_MATRIX.json',dict(fields=[dict(field=f,current_contract=gaps[f],exact_input_owner=None,extraction='SOURCE_BOUND_TRI_RECEIPT_AT_T' if f not in ('frozen_invalidation','episode_invalidation_contract_id') else 'CREATION_FROZEN_CONTRACT_PLUS_EXACT_T_MINUS_1_EPISODE',candidate_owner='ISOLATED_ONLY',states=dimensions(),T0=day,first_available=None,window_identity='T/T-1/H21 explicit per receipt',member_version=head['membership_mode'],real_consumer='sector detail/table UNKNOWN presentation',next_action='Independent contract/owner admission') for f in FIELDS],dq5_source=owners['sector'],existing_reducer=binding('src/v4/research_state.py')))
    properties=dict(contract_id={'const':'SECTOR_D2_EXTRACTION_CANDIDATE_R4_R1'},entity_type={'const':'SECTOR'},entity_id={'type':'string','minLength':1},trade_date={'type':'string','format':'date'},member_ids={'type':'array','items':{'type':'string'},'uniqueItems':True},member_set_asof={'type':['string','null']},source_binding={'type':'object','required':['path','sha256']},upstream={'type':'object','required':list(FIELDS)},formal_consumer_enabled={'const':False},accepted={'const':False})
    write(B/'B_SECTOR_ENTRY_SCHEMA.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','title':'SECTOR isolated entry R4 R1','type':'object','required':list(properties),'properties':properties})
    markdown(B/'B_SECTOR_EXTRACTION_CONTRACT_R1.md','# SECTOR D2 extraction 候选 R4 R1\n\nStatus: PROPOSAL_NOT_ACCEPTED。对象固定 SECTOR；保留原 research_state.reduce_state 和正式参数，不将STOCK入口改名。来源哈希、T0 cutoff、唯一成员分母、member_set_asof、质量、first_available、window_identity、producer_parameter_set全部必须有源；schema migration仅新增隔离候选，旧Owner和Head不迁移。\n\nCONFIRMED复用版本化 legacy B2 AST，仅其diagnostic可研究；正式valid-member/normal-rank/coverage receipts缺源则UNKNOWN。WARM复用warm AST的SETUP/RECOVERY和q20/dq5_3，Amount A分支要求strict H21。Native dq5与legacy dq5_3不能互换。frozen_invalidation只来自入组时真实contract ID/version/hash冻结的Episode和精确T-1，禁止默认常量。observe_episode按session_index单调、同会话同事件幂等，冲突拒绝、失效当日不可重入。followup_complete要求due_plan、真实到期且settled Owner，右删失不完成。scenario仅正式V4-11/V4-12源；Rotation/B0不作替代。\n\n当前400板块全部有独立SECTOR入口，dq5可单独读取；六字段无Owner，D2 readiness精确缺源。完整入力且合同正式独立接纳后才能接原D2 reducer；本轮候选不发行。正负例、真实源数量守恒见oracle与receipt。\n')
    markdown(B/'B_SECTOR_ADMISSION_BLOCKERS.md','# Sector 正式门\n\nSECTOR_D2_OWNER_OPEN；六Producer和Episode/due/scenario原件未获准。候选工程可范围通过，正式Owner不可自签。当前dq5/成员/参与代理保持可读，不因Amount H21阻断不依赖金额的板块事实。任何新source都须sha验证、T0首获、正式合同与独立授权；不改Accepted Head，不激活D2。\n')
    print(json.dumps(dict(A_missing=len(missing),amount_comparisons=len(diffs),amount_failures=len(failures),B_count=len(candidates)),ensure_ascii=False))

if __name__=='__main__':main()
