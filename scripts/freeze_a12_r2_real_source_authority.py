"""Source archaeology, real dated matrices, and a unique unaccepted Path B proposal."""
import json,sys,gzip
from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.build_a12_status_st_authority_r1 import PATHS
from workbench_analysis.status_st_authority_candidate_r2 import candidate_fact

OUT='reports/audits/A12_R2_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def save(name,obj):atomic_json(ROOT/(OUT+name+'_R1.json'),obj)
def main():
    if (ROOT/(OUT+'MASTER_SOURCE_AUTHORITY_AMENDMENT_CANDIDATE_R1.json')).exists():raise ValueError('IMMUTABLE_OWNER_CANDIDATE_ALREADY_FROZEN')
    entry=read(OUT+'STAGE_ENTRY_R1.json');assert all(bind(b['path'])['sha256']==b['sha256'] for b in entry['protected_bindings'])
    source='data/v4/source_evidence/a12_r2/'
    inventory=[]
    def inv(family,paths,dated,queryable,mutable,role,can,cannot,revision,knowledge):
        inventory.append(dict(source_family=family,sources=[bind(p) for p in paths],dated=dated,historical_queryable=queryable,mutable_current=mutable,source_class=role,can_prove=can,cannot_prove=cannot,revision_semantics=revision,knowledge_time_semantics=knowledge))
    inv('ACCEPTED_TDX_DAILY',[PATHS['daily']],True,False,False,'LOCAL','Actual bar presence / raw OHLC','Missing bar does not prove suspension or ST','Accepted frozen snapshot hash','Captured snapshot; no historical first availability inference')
    inv('DATED_IDENTITY_ALIAS',['data/v4/V4_01_ACCEPTED_HEAD.json','data/v4/bootstrap/dated_security_alias_r7.jsonl','data/v4/source_evidence/v4_02_r3/szse_2025_028_code_change_302132.pdf'],True,False,False,'LOCAL_AND_OFFICIAL','Stable security ID and effective code interval','ST or trading state','Dated alias R7 immutable bytes','Official event effective date distinct from capture 2026-09-25')
    inv('OFFICIAL_SPECIAL_PHASE_NOTICES',['data/v4/bootstrap/special_price_phase_events_r4.jsonl']+[p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4/source_evidence/v4_02_r4').glob('*.pdf')],True,False,False,'OFFICIAL','Bounded delisting dates / resumes / explicit risk-warning dates','Whole-market status/ST coverage; generic delisting risk board is not isST=1','Captured official notice revision hashes','Effective dates from body; observed 2026-09-27 not at-target available')
    inv('OFFICIAL_ST_BOUNDARIES',[source+p for p in ['600518_st_removal_mirror.pdf','600387_risk_transition.pdf','000972_risk_transition.pdf']],True,False,False,'OFFICIAL','Exact ST removal, ST to *ST, normal to risk-warning dates','Other issuers or dates outside notice scope','PDF hash with bounded capture receipts','Captured 2026-10-01; reconstructed only')
    inv('BAOSTOCK_HISTORICAL_DAILY_UPDATES',[PATHS['st'],'reports/v4_02/V4_02_DATED_ST_STATUS_V1_R6_2_20260926.json','scripts/build_v4_02_isst_worker.py',source+'DailyUpdates.md',source+'stockKData.md'],True,True,False,'PROVIDER','Dated binary ST flag; normal and suspended daily field semantics','AS_RECORDED / legal full risk taxonomy / local TDX authority','Per-date normalized full-market tuple digest frozen on 2026-09-26; query can revise','Received 2026-09-26, query date is effective trade date not knowledge time')
    inv('BAOSTOCK_CAPTURED_GAP_FACTS',[PATHS['status'],'reports/v4_02/V4_02_DATED_TRADING_STATUS_R6_2_20260926.json','scripts/build_v4_02_dated_trading_status.py'],True,True,False,'PROVIDER','0 suspension / 1 should trade on queried gap dates; 4 actual conflicts','Unqueried provider flags; raw payload not retained','982 bounded date-range queries; normalized tuples retained in status file','Observed 2026-09-26T12:09:31Z; reconstruction only')
    tnfs=[p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4/source_evidence/a11_authority_r1/tnf').rglob('*') if p.is_file()]
    inv('TDX_CURRENT_TNF',tnfs,False,False,True,'LOCAL','Captured current names/types','Dated historical ST or suspension','Frozen current snapshot; future mutable refresh separate','Current capture time only')
    capture='reports/dm01/a01_r2/20261001T033251758661Z/'
    inv('DM01_EXISTING_DELAYED_TARGET_AND_SMOKE',[capture+'TARGET_DATE_CAPTURE_query_daily_history_k_AStock_response.json',capture+'CAPABILITY_SMOKE_query_daily_history_k_AStock_response.json','reports/audits/A01_R2_NORMALIZED_RUNTIME_AND_TARGET_CAPTURE_R2.json'],True,True,False,'PROVIDER','Observed dated status/ST on 9/28 and 9/30; actual local missing should-trade case','At-target recorded owner acceptance; not part of 9/24 historical rebuild','Raw responses immutable; purpose-scoped V2_1 receipt','Captured 10/1 actual timestamps; do not backdate to 9/28')
    inv('BOUNDED_REVISION_PROBE',[source+'PROVIDER_SEMANTICS_REVISION_CONTRACT_R1.json',source+'PROVIDER_SEMANTICS_REVISION_CAPTURE_R1.json',source+'PROVIDER_DOCUMENTATION_CAPTURE_R1.json'],True,True,False,'PROVIDER','Independent real official-boundary comparisons and alias anomaly','Universal no-revision guarantee','Freeze observed response; sampled equality does not prove unrevisability','Actual observed/received timestamps on 10/1')
    ipo=[]
    for p in (ROOT/'data/v4/source_evidence/v4_08_r3').rglob('*suspension*'):
        if p.is_file():ipo.append(bind(p.relative_to(ROOT).as_posix()))
    inv('IPO_DEFERMENT_FILES',[b['path'] for b in ipo],True,False,False,'OFFICIAL','Only IPO/listing deferment where body says so','Listed-security market suspension','Filename not authority; verify body code/effective dates','Observed/captured time separate from original notice')
    save('SOURCE_ARCHAEOLOGY',dict(contract_id='A12_R2_REAL_SOURCE_ARCHAEOLOGY_V1',sources=inventory,path_a_whole_history_coverage=False,path_a_rejection='Existing dated official notices are sparse and current TNF cannot fill historical intervals',reused_source_capture=True,default_network_refresh=False))
    save('SOURCE_NOTICE_SEMANTIC_AUDIT',dict(audit_id='OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS',status='OPEN',scope='v4_08_r3 suspension-labelled IPO postponement evidence and all later consumers',evidence=ipo,confirmed_examples={'SZ.300728':'2017-11-14 IPO issuance postponement, not a listed-stock halt','SH.688688':'2020-11-03 listing postponed, not trading halt','SH.603302':'2017-12-13 IPO postponed'},acceptance_independent_of_a12=True,a12_disposition='EXCLUDED_FROM_DATED_MARKET_SUSPENSION_MATRIX',external_acceptance=None,next_stage='Independent retrospective evidence-semantic audit; do not mutate accepted heads'))
    c=duckdb.connect(str(ROOT/'tmp/a12_r2/source_cache.duckdb'))
    if not c.execute("select count(*) from information_schema.tables where table_name='universe'").fetchone()[0]:
        c.execute('create table universe as select * from read_json_auto(?)',[str(ROOT/PATHS['universe'])])
    c.execute('create or replace temp view u as select * from universe')
    probe=read(source+'PROVIDER_SEMANTICS_REVISION_CAPTURE_R1.json');comparisons=[]
    for w in probe['results']:
        assert 'error' not in w and w['metadata']['error_code']=='0'
        for r in w['rows']:
            row=c.execute('select s.security_id,s.source_security_key,s.trade_date,s.status,s.provider_tradestatus,i.is_st,u.source_bar_present,u.board_scope from status s join st i using(security_id,source_security_key,trade_date) join u using(security_id,source_security_key,trade_date) where s.source_security_key=? and s.trade_date=?',[r['code'].upper(),r['date']]).fetchone()
            if row:
                comparisons.append(dict(code=r['code'],date=r['date'],cached_st=row[5],probe_st=r['isST'],st_equal=row[5]==r['isST'],cached_provider_status=row[4],probe_status=r['tradestatus'],provider_status_equal=None if row[4] is None else row[4]==r['tradestatus'],local_actual=row[6],cached_status=row[3]))
            else:comparisons.append(dict(code=r['code'],date=r['date'],required_alias_membership=False,probe=r,disposition='OUTSIDE_EFFECTIVE_ALIAS_OR_SCOPE; NEVER_IMPORT_BY_PROVIDER_CURRENT_CODE'))
    assert all(r.get('st_equal',True) for r in comparisons)
    assert all(r.get('provider_status_equal') in (None,True) for r in comparisons)
    save('PROVIDER_SEMANTICS_AND_REVISION',dict(contract_id='A12_R2_PROVIDER_SEMANTICS_V1',documentation=bind(source+'PROVIDER_DOCUMENTATION_CAPTURE_R1.json'),probe=bind(source+'PROVIDER_SEMANTICS_REVISION_CAPTURE_R1.json'),comparisons=comparisons,tradestatus={'0':'SUSPENDED_PROVIDER_FACT','1':'SHOULD_TRADE_PROVIDER_FACT','empty_or_invalid':'UNKNOWN'},isST={'0':'NOT_ST_MARKER','1':'ST_OR_STAR_ST_BINARY_MARKER','empty_or_invalid':'UNKNOWN'},delisting_semantics='Risk-warning trading-board/delisting phase is separate from ST marker; resume as 退市 name can set isST=0 without clearing delisting special phase',revision_behavior='Compared valid required aliases agree with frozen historical facts in selected windows; query result is revisable and never AS_RECORDED',empty_behavior='No row or malformed flags produce UNKNOWN, never NORMAL or SUSPENDED',alias_behavior='Provider predecessor 300114 returns a suspended placeholder on 2025-02-17 while successor may expose history before its effective date. Required dated aliases restrict eligible code/date. No duplicated identity rows',knowledge_time='Trade date != actual source observation timestamp',first_availability_at_target_proven=False))
    rules=read('config/source_authority_governance_r2.json')['field_rules'];owners={}
    for field in ['TRADING_STATUS','ISST']:
        rule=dict(next(x for x in rules if x['field_id']==field));oid='BAOSTOCK_DATED_'+('TRADING_STATUS' if field=='TRADING_STATUS' else 'ST_STATUS')+'_RECONSTRUCTED_V3'
        rule.update(owner_contract_id=oid,source_family='BAOSTOCK_DATED_RECONSTRUCTED_PROVIDER',role_binding_id='A12_R2_CANDIDATE_ROLE:'+field,authority_status='PENDING_EXTERNAL_ACCEPTANCE',enabled_for_formal_consumer=False)
        owner=dict(contract_id=oid,field_id=field,external_acceptance=None,formal_consumer_authorization=False,allowed_consumers=rule['allowed_consumers'],effective_scope=dict(start_date='2023-07-04',end_date='2026-09-24'),historical_mode='TARGET_DATE_QUERYABLE_FACT',accepted_at=None,supersedes=bind('config/v4_02_status_st_authority_r1.json'),role_binding=rule,source_role='FIELD_AUTHORITY',role_binding_id=rule['role_binding_id'],knowledge_lineage='RECONSTRUCTED_CORRECTED',first_availability_at_target_proven=False,source_observed_at='2026-09-26T12:09:31+00:00' if field=='TRADING_STATUS' else '2026-09-26T14:11:04+00:00',source_bindings=[bind(PATHS['status' if field=='TRADING_STATUS' else 'st'])],source_semantics=bind(OUT+'PROVIDER_SEMANTICS_AND_REVISION_R1.json'),local_actual_precedence=True,forbidden_lineages=['AS_RECORDED','FIRST_AVAILABLE_AT_TARGET','LOCAL_TDX_AUTHORITY'])
        path=OUT+'OWNER_'+field+'_CANDIDATE_R1.json';atomic_json(ROOT/path,owner);owners[field]=dict(owner=owner,binding=bind(path))
    matrix=[]
    def sample(tags,key,day,official,expected,disposition='AGREES_WITH_LOCAL_OR_OFFICIAL'):
        vals=c.execute('select s.security_id,s.source_security_key,s.trade_date,s.status,s.provider_tradestatus,i.is_st,u.source_bar_present,u.board_scope,i.source_revision from status s join st i using(security_id,source_security_key,trade_date) join u using(security_id,source_security_key,trade_date) where s.source_security_key=? and s.trade_date=?',[key,day]).fetchone();assert vals,(key,day)
        sid,key,day,status,ps,st,actual,board,revision=vals;day=str(day)
        member=dict(security_id=sid,source_security_key=key,trade_date=day,source_bar_present=actual)
        sf=candidate_fact(member,{**member,'provider_tradestatus':ps},owners['TRADING_STATUS']['owner'],field='TRADING_STATUS');inf=candidate_fact(member,{**member,'is_st':st,'source_revision':revision},owners['ISST']['owner'],field='ISST')
        assert sf['status']==expected.get('status',status) and inf['is_st']==expected.get('is_st',st)
        matrix.append(dict(categories=tags,security_id=sid,source_security_key=key,effective_date=day,board_scope=board,official_local_evidence=[bind(p) for p in official],provider_value=dict(tradestatus=ps,isST=st,source_revision=revision),local_actual=actual,expected_interpretation={**expected,'status':sf['status'],'is_st':inf['is_st']},conflict_disposition=disposition,scope='HISTORICAL_REQUIRED',candidate_only=True))
    docs=source
    sample(['NORMAL_DAY','SH_MAIN','NON_ST'],'SH.600000','2023-07-04',[PATHS['daily']],{'status':'ACTUAL_TRADED','is_st':'0'})
    sample(['NORMAL_DAY','SZ_MAIN','NON_ST'],'SZ.000001','2023-07-04',[PATHS['daily']],{'status':'ACTUAL_TRADED','is_st':'0'})
    sample(['NORMAL_DAY','STAR','NON_ST'],'SH.688981','2023-07-04',[PATHS['daily']],{'status':'ACTUAL_TRADED','is_st':'0'})
    for day in ['2024-07-02','2024-07-03','2024-07-04']:
        sample(['ST_REMOVAL','ST_DURING_SUSPENSION','SUSPEND_RESUME'],'SH.600518',day,[docs+'600518_st_removal_mirror.pdf',PATHS['daily']],dict(status='SUSPENDED' if day=='2024-07-03' else 'ACTUAL_TRADED',is_st='0' if day=='2024-07-04' else '1'))
    for day in ['2025-03-28','2025-03-31','2025-04-01']:
        sample(['NORMAL_TO_ST_RISK_WARNING'],'SZ.000972',day,[docs+'000972_risk_transition.pdf',PATHS['daily']],dict(is_st='1' if day=='2025-04-01' else '0'))
    for day in ['2024-04-19','2024-04-22','2024-04-23']:
        sample(['ST_TO_STAR_ST','ST_DURING_SUSPENSION'],'SH.600387',day,[docs+'600387_risk_transition.pdf',PATHS['daily']],dict(is_st='1'), 'BINARY_ST_UNCHANGED; OFFICIAL_RISK_SUBTYPE_CHANGES_TO_STAR_ST')
    alias='data/v4/source_evidence/v4_02_r3/szse_2025_028_code_change_302132.pdf'
    sample(['CODE_CHANGE_BOUNDARY','ST_CODE_CHANGE_NEGATIVE_SCOPE'],'SZ.300114','2025-02-14',[alias,PATHS['daily']],dict(is_st='0'))
    sample(['CODE_CHANGE_BOUNDARY','ST_CODE_CHANGE_NEGATIVE_SCOPE','CHINEXT'],'SZ.302132','2025-02-17',[alias,PATHS['daily']],dict(is_st='0'),'OLD_CODE_SUSPENDED_PLACEHOLDER_REJECTED; DATED_SUCCESSOR_USED')
    sample(['NEW_LISTING','CHINEXT'],'SZ.301611','2024-08-16',['data/v4/V4_01_ACCEPTED_HEAD.json',PATHS['daily']],dict(is_st='0'))
    pdf=next(p.relative_to(ROOT).as_posix() for p in (ROOT/'data/v4/source_evidence/v4_02_r4').glob('SH_600225*.pdf'))
    sample(['LONG_SUSPENSION','ST_DURING_SUSPENSION'],'SH.600225','2025-02-06',[pdf,PATHS['daily']],dict(status='SUSPENDED',is_st='1'))
    sample(['DELISTING_RESUME','OFFICIAL_PROVIDER_RISK_TAXONOMY_CONFLICT'],'SH.600225','2025-02-07',[pdf,PATHS['daily']],dict(status='ACTUAL_TRADED',is_st='0'),'OFFICIAL_RISK_WARNING_DELISTING_BOARD_IS_NOT_BINARY_ST; SPECIAL_PHASE_RETAINED')
    for key,day in c.execute("select source_security_key,trade_date from status where status='ACTUAL_TRADED' and provider_tradestatus='0'").fetchall():
        sample(['PROVIDER_LOCAL_ACTUAL_CONFLICT'],key,str(day),[PATHS['daily'],PATHS['status']],dict(status='ACTUAL_TRADED'),'LOCAL_ACTUAL_OVERRIDES_PROVIDER_0; CONFLICT_RETAINED')
    raw=read(capture+'TARGET_DATE_CAPTURE_query_daily_history_k_AStock_response.json')
    # The 9/28 gap supplement independently reads its own frozen native TDX package.
    save('GO_FORWARD_EXISTING_CAPTURE_BOUNDARY',dict(existing_capture=bind(capture+'TARGET_DATE_CAPTURE_query_daily_history_k_AStock_response.json'),independent_source_preflight=bind('reports/audits/A01_R2_INDEPENDENT_CAPTURE_AND_SOURCE_PREFLIGHT_R1.json'),captured_rows=len(raw['rows']),semantics='Observed-on-10/1 delayed target query; eligible future observed daily candidate role only when captured, not AS_RECORDED at 9/28',formal_owner_registration=False,required_new_network_calls=0))
    alias_counts=c.execute("select source_security_key,count(*),min(is_st),max(is_st) from st where source_security_key in ('SZ.300114','SZ.302132') group by all").fetchall()
    save('REAL_SAMPLE_MATRIX',dict(contract_id='A12_R2_REAL_DATED_MATRIX_V1',samples=matrix,required_boards=sorted({r['board_scope'] for r in matrix}),actual_local_provider_conflict_count=4,alias_st_scope_census=alias_counts,positive_st_during_numeric_code_change='NOT_OBSERVED_IN_REQUIRED_SCOPE; THE ONLY OFFICIAL_NUMERIC_ALIAS_HAS_786_NON_ST_ROWS',synthetic_samples_used=False,real_data_gap_source='A01_R2 frozen 9/28 raw oracle; see separate dated gap matrix supplement',official_provider_risk_conflict='EXPLICIT_FIELD_TAXONOMY_DISPOSITION_NOT_SILENT_OVERRIDE',external_acceptance=None))
    save('MASTER_SOURCE_AUTHORITY_AMENDMENT_CANDIDATE',dict(contract_id='MASTER_SOURCE_AUTHORITY_AMENDMENT_CANDIDATE_A12_R2_V1',choice='PATH_B_HISTORICAL_RECONSTRUCTED_AUTHORITY_AMENDMENT_CANDIDATE',historical_owner_bindings={k:v['binding'] for k,v in owners.items()},go_forward_owner='Same versioned provider field semantics with mandatory raw response capture, actual observed/received timestamps and independently accepted scoped owner before formal use; delayed captures remain reconstructed',path_a_rejected='Sparse official notices and current TNF cannot cover 4,035,729 required history rows',source_semantics=bind(OUT+'PROVIDER_SEMANTICS_AND_REVISION_R1.json'),sample_matrix=bind(OUT+'REAL_SAMPLE_MATRIX_R1.json'),historical_scope={'start':'2023-07-04','end':'2026-09-24'},owner_registry=bind('data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json'),registry_written=False,formal_consumer_authorization=False,external_acceptance=None,dm01_final_all_nine='BLOCKED',positive_st_code_change_scope_limit='No positive case exists in sole accepted numeric alias. External review must assess bounded negative census; not fabricate ST history',next_stage='Full candidate replay; independent external amendment acceptance; later explicit owner promotion card'))
    print('PATH_B_CANDIDATE_FROZEN',len(matrix),'real samples; formal owners remain unregistered')
if __name__=='__main__':main()
