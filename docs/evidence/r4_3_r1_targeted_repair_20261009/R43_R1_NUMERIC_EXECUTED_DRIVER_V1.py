"""R4.3 R1 engineering re-review of frozen bytes; never external signoff.

All writes target a new evidence directory. Frozen oracle sources execute with
their output functions redirected, not their input directories rewritten.
"""
from pathlib import Path
from collections import Counter, defaultdict
from statistics import median
import gzip, hashlib, json, os, re, sys, time, traceback

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'docs/evidence/r4_3_four_session_closeout_20261009'
NEW = ROOT / 'docs/evidence/r4_3_r1_targeted_repair_20261009'
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

def load(p): return json.loads(p.read_bytes())
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def rows(p):
    with gzip.open(p, 'rt', encoding='utf8') as f:
        return [json.loads(l) for l in f if l.strip()]
def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp.numeric-r1')
    tmp.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    os.replace(tmp, p)
def ref(p):
    try: name=p.relative_to(ROOT).as_posix()
    except ValueError: name=str(p)
    return dict(path=name, bytes=p.stat().st_size, sha256=sha(p))

def run_frozen_oracle(name):
    path = ROOT / 'scripts' / name
    source = path.read_text(encoding='utf8')
    # Only terminal output destinations change; calculations and input paths
    # retain the frozen source and original actual-byte inputs.
    source = source.replace("target=OUT/'05_INDEPENDENT_PROFILE_BRANCH_AND_METADATA_ORACLE.json'", "target=NEWOUT/'05_INDEPENDENT_PROFILE_BRANCH_AND_METADATA_ORACLE.json'")
    source = source.replace("p=OUT/'05_INDEPENDENT_DAILY_PRICE_LIMIT_ORACLE.json'", "p=NEWOUT/'05_INDEPENDENT_DAILY_PRICE_LIMIT_ORACLE.json'")
    ns = dict(__name__='r43_r1_scoped_oracle', __file__=str(path), NEWOUT=NEW)
    started = time.time()
    receipt = dict(command='E:/python/python.exe scripts/audit_r43_r1_scoped_numeric.py', invoked_oracle=name, execution_mode='Compiled frozen script body in isolated namespace; only output destinations redirected', original_source=ref(path), executed_source_sha256=hashlib.sha256(source.encode()).hexdigest(), output_redirect_only=True)
    try:
        exec(compile(source, str(path), 'exec'), ns)
        if name == 'audit_r43_core_numeric_independent.py':
            ns['write'] = lambda n, v: write(NEW / n, v)
        elif name in ('audit_r43_cross_section.py', 'reconcile_r4_3_universe.py'):
            ns['write'] = lambda p, v: write(NEW / p.relative_to(OLD), v)
            if '_atomic_write' in ns:
                def redirected_atomic(p, content, **kwargs):
                    q = NEW / p.relative_to(OLD); q.parent.mkdir(parents=True, exist_ok=True)
                    tmp=q.with_suffix(q.suffix+'.tmp.numeric-r1');tmp.write_bytes(content);os.replace(tmp,q)
                ns['_atomic_write'] = redirected_atomic
        # Profile samples are the newly rerun numeric oracle, not old PASS text.
        if name == 'audit_r43_profile_independent.py':
            original_load=ns['load']
            ns['load']=lambda p: original_load(NEW / p.name if p.name == '05_FOUR_SESSION_RAW_QFQ_CORE_PROFILE_NUMERIC_ORACLE.json' else p)
        ns['main']()
        receipt.update(exit_code=0, traceback=None)
    except Exception:
        receipt.update(exit_code=1, traceback=traceback.format_exc())
    receipt['elapsed_seconds']=round(time.time()-started,3)
    write(NEW / ('R1_EXECUTION_' + path.stem + '.json'), receipt)
    if receipt['exit_code']: raise RuntimeError(receipt['traceback'])
    print(name, 'exit_code=0', flush=True)
    return receipt

def verify_actual_bytes():
    errors=[]; verified={}; code_revisions=[]
    def bound(r):
        if not isinstance(r,dict):return
        if isinstance(r.get('path'),str) and len(str(r.get('sha256',''))) == 64:
            p=ROOT/r['path']
            if not p.is_file():errors.append(dict(path=r['path'],error='MISSING_ACTUAL_BYTES'));return
            if p not in verified:
                with p.open('rb') as f: prefix=f.read(128)
                if prefix.startswith(b'version https://git-lfs.github.com/spec/v1'):errors.append(dict(path=r['path'],error='LFS_POINTER_INSTEAD_OF_BYTES'))
                verified[p]=ref(p)
            actual=verified[p]
            if actual['sha256']!=r['sha256'] or 'bytes' in r and actual['bytes']!=r['bytes']:
                record=dict(path=r['path'],expected=r,actual=actual)
                if r['path'].startswith(('src/','scripts/')):code_revisions.append(record)
                else:errors.append(record)
        for v in r.values():walk(v)
    def walk(v):
        if isinstance(v,dict):bound(v)
        elif isinstance(v,list):
            for x in v:walk(x)
    manifest=load(OLD/'ACTUAL_ARTIFACT_BYTES_MANIFEST.json')
    walk(manifest)
    for name in ('00_ENTRY_DRIVE_HEAD_AND_PROTECTED_DIGESTS.json','01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json','MEMBER_SNAPSHOT_S.json','04_GBBQ_IDENTITY_LIFECYCLE_SPECIAL_SOURCE_TRACE.json','owner_v3/CORE_REPLAY.json','owner_v3/PROFILE_STRUCTURE_REPLAY.json','owner_v3/DAILY_PRICE_LIMIT_REPLAY.json','06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json'):
        p=OLD/name
        if not p.exists():continue
        # Owner sources include native ZIP/GBBQ/rosters outside this directory.
        try:walk(load(p))
        except json.JSONDecodeError:errors.append(dict(path=str(p),error='BAD_JSON'))
    result=dict(contract='R43_R1_REAL_LFS_BYTES_SHA_REVIEW_V1',files=list(verified.values()),total_bytes=sum(x['bytes'] for x in verified.values()),errors=errors,current_code_revisions_vs_frozen_execution_bindings=code_revisions,acceptance='PASS' if not errors else 'FAIL',drive_archive_recovery='NOT_PERFORMED; local archive chunk bytes verified if present, hydrated local actual owner bytes used, no remote archive-read claim')
    write(NEW/'R43_R1_ACTUAL_BYTES_FULL_SHA.json',result)
    assert not errors, errors[:5]
    return result

def membership_sector_oracle():
    snapshot=load(OLD/'MEMBER_SNAPSHOT_S.json'); members=rows(ROOT/snapshot['memberships']['path'])
    member_digest=hashlib.sha256(json.dumps(members,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert member_digest==snapshot['member_digest']
    original_keys=sorted(set().union(*(r.keys() for r in members)))
    assert len(original_keys)==10 and 'industry_level' not in original_keys and 'primary_industry_rank_eligible' not in original_keys
    # A second parser directly consumes all three frozen source files. It does
    # not import build_snapshot, normalization, or production TDX readers.
    source_paths={Path(r['path']).name:ROOT/r['path'] for r in snapshot['sources']}
    names={}
    for line in source_paths['tdxzs.cfg'].read_bytes().decode('gb18030',errors='replace').splitlines():
        f=line.strip().split('|')
        if len(f)>=6 and f[5]:names[f[5]]=f[0]
    market={'0':'SZ','1':'SH','2':'BJ'};parsed=[]
    for line in source_paths['tdxhy.cfg'].read_bytes().decode('gb18030',errors='replace').splitlines():
        f=line.strip().split('|')
        if len(f)<3 or f[0] not in market or not re.fullmatch(r'\d{6}',f[1]) or not f[2]:continue
        code=f[2];security=market[f[0]]+'.'+f[1]
        parsed.append(('INDUSTRY',code,names.get(code,code),security,'tdxhy.cfg'))
        parent_code=code[:5] if len(code)>5 else ''
        if parent_code and parent_code in names:parsed.append(('INDUSTRY',parent_code,names[parent_code],security,'tdxhy.cfg:DERIVED_PARENT'))
    current=None
    for line in source_paths['infoharbor_block.dat'].read_bytes().decode('gb18030',errors='replace').splitlines():
        if line.startswith('#'):
            header=line[1:].split(',');label=header[0]
            if '_' not in label:current=None;continue
            prefix,name=label.split('_',1)
            current=(header[2].strip() if len(header)>2 and header[2].strip() else name,name) if prefix=='GN' else None
        elif current:
            for m,code in re.findall(r'([012])#(\d{6})',line):parsed.append(('THEME',current[0],current[1],market[m]+'.'+code,'infoharbor_block.dat'))
    identities={r['source_security_key'].upper():r for r in load(ROOT/snapshot['identity_source']['path'])['rows'] if r.get('identity_status')=='IDENTITY_BOUND'}
    independent=[];seen=set()
    for typ,code,name,security,source in parsed:
        k=(typ,code,security)
        if k in seen:continue
        seen.add(k);ident=identities.get(security)
        independent.append(dict(sector_id=typ+':'+code,sector_type=typ,sector_code=code,sector_name=name,source_security_key=security,source=source,security_id=ident['security_id'] if ident else None,identity_status='MAPPED' if ident else 'UNMAPPED_QUARANTINED',list_date=ident.get('list_date') if ident else None,delist_date=ident.get('delist_date') if ident else None))
    independent.sort(key=lambda r:(r['sector_type'],r['sector_id'],r['source_security_key']))
    independent_digest=hashlib.sha256(json.dumps(independent,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert independent==members and independent_digest==member_digest
    write(NEW/'R43_R1_INDEPENDENT_NATIVE_SOURCE_MEMBER_DIGEST.json',dict(source_files=[ref(p) for p in source_paths.values()],full_rows=len(independent),digest=independent_digest,first_unequal_record=None,production_parser_imported=False,acceptance='PASS',command='E:/python/python.exe scripts/audit_r43_r1_scoped_numeric.py'))
    ledger=load(OLD/'01_LATEST_TDX_INDUSTRY_CONCEPT_CAPTURE_LEDGER.json')
    old_members=rows(ROOT/ledger['accepted_0930']['path'])
    assert len(old_members)==50162 and len({r['sector_id'] for r in old_members})==378
    assert sha(ROOT/ledger['accepted_0930']['path'])==ledger['accepted_0930']['sha256']
    key=lambda r:(r['sector_id'],r['source_security_key'])
    assert len(members)==55136 and len(set(map(key,members)))==55136
    assert sum(bool(r['security_id']) for r in members)==52912
    groups=defaultdict(list)
    for r in members:groups[r['sector_id']].append(r)
    parent=[k for k,v in groups.items() if all('DERIVED_PARENT' in x['source'] for x in v)]
    leaf=[k for k in groups if k.startswith('INDUSTRY:') and k not in parent]
    theme=[k for k in groups if k.startswith('THEME:')]
    actual_population=dict(source_nonparent_industry=len(leaf),source_derived_parent=len(parent),concept=len(theme),unclassified_placeholder=1,eligible_named_leaf=len(leaf)-1)
    # This is a real frozen-evidence reporting contradiction. Never relabel
    # the T00 unmapped placeholder as a fictional twenty-third parent.
    write(NEW/'R43_R1_PARENT_COUNT_REPORTING_CONTRADICTION.json',dict(actual_population=actual_population,old_claim=dict(leaf=110,parent=23,concept=268),frozen_claim=ref(OLD/'W4_SOURCE_SECTOR_COVERAGE_EXPLANATION.json'),acceptance='OLD_23_PARENT_COUNT_FAIL; ACTUAL_22_PARENT_COVERAGE_VERIFIED',cross_cutting_audit_item='R43-R1-CROSS-TAXONOMY-DENOMINATOR',scope='Count labels only; no membership or numeric owner changes',source_relation_digest=member_digest,independent_source_parent_ids=sorted(parent)))
    assert (len(leaf),len(parent),len(theme))==(111,22,268)
    sample=[dict(sector_id=k,relation_count=len(groups[k]),first_member=groups[k][0]) for k in sorted(groups)]
    sector_replay=load(OLD/'06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json')
    core_replay=load(OLD/'owner_v3/CORE_REPLAY.json')['owners'];daily=[];samples=[];errors=[];metadata_rows=0
    required=dict(knowledge_lineage='RECONSTRUCTED_LATEST_MEMBERSHIP',AS_RECORDED=False,PIT_ELIGIBLE=False,survivorship_bias_risk=True)
    for owner in core_replay:
        day=owner['trade_date'];core={r['security_id']:r for r in rows(ROOT/owner['core']['path'])};adjusted={r['security_id']:r for r in rows(ROOT/owner['adjusted']['path'])};native=rows(OLD/'sector_v3'/day/'native.jsonl.gz');nativeby={r['sector_id']:r for r in native};relative={r['security_id']:r for r in rows(OLD/'sector_v3'/day/'relative_sector_loo.jsonl.gz')}
        eligible={k:{r['security_id'] for r in v if r['security_id'] in core and r['list_date'] and r['list_date']<=day and (not r['delist_date'] or r['delist_date']>day)} for k,v in groups.items()}
        assert len(native)==400 and not eligible['INDUSTRY:T00'] and 'INDUSTRY:T00' not in nativeby
        checks=0
        for n in native:
            ids=eligible[n['sector_id']];assert set(n['member_ids'])==ids
            for horizon in (1,5,20,60):
                values=[core[s]['fields'].get('ret'+str(horizon),{}).get('value') for s in ids if core[s]['fields'].get('ret'+str(horizon),{}).get('value') is not None]
                want=median(values) if values else None;actual=n['fields']['sector_rs'+str(horizon)]['value']
                if want!=actual:errors.append(dict(day=day,sector=n['sector_id'],field='sector_rs'+str(horizon),expected=want,actual=actual))
                checks+=1
            for field,predicate,values in [('breadth_ret1',lambda x:x>0,[core[s]['fields']['ret1']['value'] for s in ids]),('ma20_width',lambda x:x>0,[adjusted.get(s,{}).get('close')-core[s]['fields']['ma20']['value'] if adjusted.get(s,{}).get('close') is not None and core[s]['fields']['ma20']['value'] is not None else None for s in ids])]:
                values=[v for v in values if v is not None];want=sum(predicate(v) for v in values)/len(values) if values else None
                if want!=n['fields'][field]['value']:errors.append(dict(day=day,sector=n['sector_id'],field=field,expected=want,actual=n['fields'][field]['value']))
                checks+=1
        for oracle in sector_replay['oracle']:
            if oracle['trade_date']!=day:continue
            ids=eligible[oracle['sector_id']]-{oracle['security_id']};values={}
            assert len(ids)==oracle['others']
            for horizon in (1,5):
                vv=[core[s]['fields']['ret'+str(horizon)]['value'] for s in ids if core[s]['fields']['ret'+str(horizon)]['value'] is not None]
                want=median(vv) if vv else None;actual=oracle['values']['sector_rs'+str(horizon)]['value'];values['ret'+str(horizon)]=want
                if want!=actual:errors.append(dict(day=day,sector=oracle['sector_id'],target=oracle['security_id'],expected=want,actual=actual))
                rel=next(r for r in relative[oracle['security_id']]['memberships'] if r['sector_id']==oracle['sector_id'])
                stock=core[oracle['security_id']]['fields']['ret'+str(horizon)]['value'];expected_relative=stock-want if stock is not None and want is not None else None
                got=rel['relative_substitutions']['rel_market_'+str(horizon)]
                if got!=expected_relative:errors.append(dict(day=day,sector=oracle['sector_id'],target=oracle['security_id'],field='relative_substitution',expected=expected_relative,actual=got))
            samples.append(dict(trade_date=day,security_id=oracle['security_id'],sector_id=oracle['sector_id'],actual_others=len(ids),independent_medians=values))
        for name in ('native.jsonl.gz','relative_sector_loo.jsonl.gz','rotation.jsonl.gz','profiles_with_tdx_relative.jsonl.gz'):
            for r in rows(OLD/'sector_v3'/day/name):
                for k,v in required.items():
                    if r.get(k)!=v:errors.append(dict(day=day,artifact=name,field=k,error='LINEAGE_MISMATCH'))
                assert r.get('membership_snapshot_id')==snapshot['membership_snapshot_id'];metadata_rows+=1
        daily.append(dict(trade_date=day,all_source_sectors=len(groups),computed_sectors=len(native),independent_numeric_checks=checks,excluded_zero_eligible_source_sector='INDUSTRY:T00',leaf_rank_population=110,parent_population=22,theme_population=268,rotation_state_counts=dict(Counter(r['operational_state'] if 'operational_state' in r else r.get('state') for r in rows(OLD/'sector_v3'/day/'rotation.jsonl.gz')))))
    assert len(samples)==40
    result=dict(contract='R43_R1_SECTOR_MULTI_MEMBERSHIP_INDEPENDENT_MEDIAN_V1',relations=55136,mapped=52912,unmapped=2224,full_relation_digest=member_digest,frozen_row_key_union=original_keys,original_0930=dict(relations=len(old_members),sectors=378,binding=ledger['accepted_0930']),source_sector_counts=actual_population,coverage_all_401_groups=sample,dates=daily,loo_samples=samples,metadata_rows_checked=metadata_rows,errors=errors,acceptance='PASS' if not errors else 'FAIL',rotation_scope='Actual rows/hash/lineage checked; no claim of independently rederived rotation state machine or historical first availability')
    write(NEW/'R43_R1_MEMBERSHIP_ALL_SECTORS_LOO_NUMERIC.json',result)
    assert not errors,errors[:5]
    return result

def main():
    write(NEW/'R43_R1_NUMERIC_STAGE_ENTRY.json',dict(stage='P0-C',task_card='V4_R4_3_定点修复与安全切换任务卡_R1_20261009.md',contract='R43_R1_SCOPED_ENGINEERING_REVIEW_V1',scope='Hydrated frozen actual bytes; independently formulated numeric checks; original frozen evidence remains read-only',next_stage='FINAL_CANDIDATE_EXTERNAL_SCOPED_ADMISSION',acceptance='IN_PROGRESS',external_reviewer=False))
    byte_review=verify_actual_bytes()
    receipts=[]
    for name in ['reconcile_r4_3_universe.py','audit_r43_core_numeric_independent.py','audit_r43_cross_section.py','audit_r43_profile_independent.py','audit_r43_daily_limits_independent.py']:
        receipts.append(run_frozen_oracle(name))
    sectors=membership_sector_oracle()
    protected=[dict(path=x['path'],expected_sha256=x['sha256'],actual_sha256=sha(ROOT/x['path'])) for x in byte_review['files'] if x['path'].startswith('docs/evidence/r4_3_four_session_closeout_20261009/')]
    assert all(r['expected_sha256']==r['actual_sha256'] for r in protected)
    write(NEW/'R43_R1_SCOPED_NUMERIC_REVIEW_RECEIPT.json',dict(engineering_acceptance='PASS',external_acceptance='NOT_VERIFIABLE_NO_INDEPENDENT_EXTERNAL_REVIEWER_SIGNOFF',production_admission='NOT_GRANTED',commands=receipts,original_evidence_unchanged=protected,source_sha256=sha(Path(__file__)),numeric_checks_scope='Actual native RAW/full RPS; 128 MA/ATR/QFQ samples and 512 Profile branches; 400 sectors/date and 40 LOO samples',excluded=['Strict historical PIT','Independent external signing authority','Intraday events','Full forward statistic maturity','Independent rotation recurrence implementation']))
    report='''# R4.3 R1 限定来源/数值工程复核 V2

结论：限定工程数值复核 PASS；独立外部签收 NOT_VERIFIABLE；生产准入 NOT_GRANTED。本报告由执行修复任务的工程代理生成，不是独立外部审查者签收，绝不签发 EXTERNALLY_ACCEPTED_R43_OPERATIONAL。

可复现命令：`E:/python/python.exe scripts/audit_r43_r1_scoped_numeric.py`。全部输出进入新的 R1 证据目录，原冻结证据不覆盖。运行源码、派生执行源码 SHA、各命令退出码及实际文件 SHA 位于 R43_R1_SCOPED_NUMERIC_REVIEW_RECEIPT.json、R1_EXECUTION_*.json 和 R43_R1_ACTUAL_BYTES_FULL_SHA.json。

实际读取 hydrated Git LFS 数据字节，拒绝 pointer；完整 SHA 覆盖成员、Owner、原冻结 native ZIP/GBBQ、相关绑定和冻结证据。未读取或重组 Drive 17 段备份，本报告不冒称 Drive 外部复算。保留原 9/30 快照保护绑定。

独立读原 S 的所有55,136行确认其字段全集只有10列，确实不含 industry_level/primary_industry_rank_eligible。行业层级由 source 中 DERIVED_PARENT 推导；当前 capture 新增12列与 legacy 冻结S schema不同，不能据此伪造原 legacy verifier失败。该函数矛盾的真实失败/修复以 P0-A 新收据为准。原关系完整digest和原 9/30 50,162关系/378板块实际SHA均保持。

重新执行原独立数值 oracle（输入保持冻结，输出定向新目录）：四日 native RAW 与停牌全量对照、T-1/T-3、128 个跨事件/短上市/停牌/普通真实样本的当前与前驱 MA/ATR/QFQ、全量 RPS 排序与可用精确端点、512 Profile 分支、dated daily limit Decimal 校验。详见新 03/05 系列结果。

新独立算法直接解析三份native冻结源并还原所有55,136个10列字典，完整digest与原S完全一致；不导入生产parser/normalization。核对55,136=52,912+2,224关系、多对多key唯一性，覆盖全部401源组。实际数据为110合法叶级、22 derived父级、268概念，另1个T00未分类placeholder；旧收据与任务卡的“23父级”真实 FAIL，不把 T00 改名成不存在的第23父。独立审计项 R43-R1-CROSS-TAXONOMY-DENOMINATOR 的事实已单独记录。每日期 400 板块成员集合与 ret1/5/20/60 中位数、breadth 与 MA20 width 直接重算；40 个 LOO 样本重新排除目标股票取独立中位数并核对实际相对替代值。T00 只有源关系且无合法成员，不造价格。父级分群保留；未映射按关系分母、北交所 optional degraded 不擅改。

运营回算 lineage、AS_RECORDED=false、PIT_ELIGIBLE=false、survivorship_bias_risk=true 在实际 native、relative、Rotation、enriched Profile 行逐一校验。Rotation 仅复核实际字节/lineage，未以新的独立实现重推完整状态机；未声称严格历史 PIT、盘中事件或成熟 Forward 统计。

下一门：最终实际候选 digest 的独立外部来源/数值/兼容范围签收。旧版本工程 PASS 或旧外审不替代新候选签收；本工程复核不能满足该身份门，不能据此执行生产 CAS 或启动 FP-01～FP-14。
'''
    p=NEW/'R43_SCOPED_EXTERNAL_SOURCE_NUMERIC_REVIEW_V2.md';tmp=p.with_suffix('.tmp.numeric-r1');tmp.write_text(report,encoding='utf8');os.replace(tmp,p)
    print('SCOPED_ENGINEERING_REVIEW_PASS; EXTERNAL_SIGNOFF_NOT_VERIFIABLE',flush=True)

if __name__=='__main__':main()
