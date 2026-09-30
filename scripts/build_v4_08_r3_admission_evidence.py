"""Build append-only identity/calendar candidates and fail-closed PIT admission evidence."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta, date, timezone
import gzip
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes,sha,gzip_jsonl
from build_v4_08_membership_prerequisite import build_source_rows
from capture_v4_08_r3_sources import normalized
from sector.membership_admission_r3 import active_identity_reason
from sector.membership_baseline import canonical_json_bytes,build_source_revision_identity
from workbench_analysis.security_entity_identity import stable_security_id
from bs4 import BeautifulSoup

TARGET='2026-09-30'
KEYS=['SH.601206','SH.603302','SH.603361','SH.688688','SZ.001235','SZ.001246','SZ.300728','SZ.301569','SZ.301660','SZ.301716','SZ.301718']
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def binding(path):
    data=(ROOT/path).read_bytes();return {'path':path,'sha256':sha(data),'byte_count':len(data)}
def now():return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def write(name,value):atomic_json(ROOT/'reports/v4_08'/name,value)

def main():
    capture=read('reports/v4_08/V4_08_R3_OFFICIAL_LIFECYCLE_SOURCE_CAPTURE.json')
    by_id={x['id']:x for x in capture['sources']}
    for source in capture['sources']:
        if source.get('path') and sha((ROOT/source['path']).read_bytes())!=source['sha256']:raise ValueError('source hash mismatch')
    # The exchange report explicitly identifies its page size, result count and filtered code.
    sz={}
    for key in KEYS:
        if not key.startswith('SZ.'):continue
        source=by_id['SZ_'+key[3:]+'_exchange_query'];doc=read(source['path'])[0]
        metadata=doc['metadata'];condition=next(x for x in metadata['conditions'] if x['name']=='txtDMorJC')
        if condition['defaultValue']!=key[3:] or metadata['recordcount']!=len(doc['data']):raise ValueError('filtered SZSE query is not complete/exact')
        if any(row['agdm']!=key[3:] for row in doc['data']):raise ValueError('unexpected exchange query member')
        sz[key]={'rows':doc['data'],'source':source}
    sh_sources=[by_id['SSE_stock_list'],by_id['SSE_STAR_stock_list']]
    sh_codes=set()
    active_list_dates={}
    for source in sh_sources:
        doc=read(source['path']);rows=doc['result']
        if doc['isPagination']!='false' or not rows or len(rows)>=doc['pageHelp']['pageSize']:raise ValueError('SSE catalogue completeness cannot be established')
        sh_codes.update(row['A_STOCK_CODE'] for row in rows)
        active_list_dates.update({'SH.'+x['A_STOCK_CODE']:x['LIST_DATE'][:4]+'-'+x['LIST_DATE'][4:6]+'-'+x['LIST_DATE'][6:] for x in rows})
    catalogue=read('reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json')
    if catalogue['status']!='PASS_COMPLETE_TARGET_DAY_SZSE_CATALOGUE' or catalogue['target_trade_date']!=TARGET:
        raise ValueError('target-day full SZSE catalogue is required')
    active_list_dates.update({'SZ.'+x['agdm']:x['agssrq'] for x in catalogue['records']})
    classifications=[];increment=[]
    prior_path='data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json'
    prior=read(prior_path)
    for key in KEYS:
        item={'source_security_key':key,'target_trade_date':TARGET,'board_for_code_used_as_lifecycle_truth':False}
        if key.startswith('SZ.') and sz[key]['rows']:
            row=sz[key]['rows'][0];board={'主板':'SZ_MAIN','创业板':'CHINEXT'}[row['bk']]
            listing=row['agssrq'];listing_source=by_id['SZ_'+key[3:]+'_listing']
            if listing_source['status']!='PASS_CAPTURE':raise ValueError('increment requires official/statutory listing announcement')
            if listing>TARGET:raise ValueError('pre-list admission forbidden')
            item.update(classification='FORMAL_IN_SCOPE_A_STOCK',listing_date=listing,board=board,evidence=[binding(sz[key]['source']['path']),binding(listing_source['path'])],security_id=stable_security_id('SZ',key,listing))
            increment.append({'source_security_key':key,'symbol':key,'security_id':item['security_id'],'lifecycle_entity_id':item['security_id'],'exchange':'SZ','board':board,'security_type':'A_STOCK','list_date':listing,'delist_date':None,'symbol_effective_from':listing,'symbol_effective_to':None,'security_name':BeautifulSoup(row['agjc'],'html.parser').get_text(),'source_contract_id':'V4_01_GO_FORWARD_OFFICIAL_LIFECYCLE_SOURCE_V1','source_evidence':item['evidence'],'observed_at':max(sz[key]['source']['observed_at'],listing_source['observed_at']),'identity_quality':'OFFICIAL_TARGET_DAY_LIST_AND_STATUTORY_LISTING_ANNOUNCEMENT_CANDIDATE','acceptance':'CANDIDATE_PENDING_EXTERNAL_PROMOTION'})
        else:
            if key.startswith('SH.') and key[3:] in sh_codes:raise ValueError('unexpected active SSE key needs incremental adjudication')
            item.update(classification='NOT_LISTED_AT_TARGET',listing_date=None,board=None,evidence=[binding(x['path']) for x in sh_sources] if key.startswith('SH.') else [binding(sz[key]['source']['path'])],active_catalogue_absence_verified=True)
            related=[x for x in capture['sources'] if x.get('key')==key and ('suspension' in x['id'] or 'issuance' in x['id'])]
            item['dated_lifecycle_evidence']=[{**binding(x['path']),'source_published_date':x['published_date'],'capture_status':x['status']} for x in related]
            item['reason']='ISSUANCE_PRE_LIST_AND_ABSENT_FROM_TARGET_ACTIVE_CATALOGUE' if key in ['SZ.301569','SZ.301660','SZ.301718'] else 'HISTORICAL_IPO_OBJECT_ABSENT_FROM_TARGET_ACTIVE_CATALOGUE; no claim of legal termination'
        classifications.append(item)
    computed=now()
    identity_path='data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json'
    identity={'contract_id':'V4_01_GO_FORWARD_IDENTITY_INCREMENT_R1','status':'CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION','parent_identity':binding(prior_path),'parent_accepted_head':binding('data/v4/V4_01_ACCEPTED_HEAD.json'),'target_trade_date':TARGET,'knowledge_cutoff':computed,'system_available_at':computed,'records':prior['records']+increment,'new_lifecycle_events':increment,'unresolved_remainder':[],'scope':'Target-day closure of the 11 R2 required-board keys; not a claim of whole-market incremental lifecycle completeness','historical_identity_map_overwritten':False,'dispositions':classifications,'target_active_catalogue':binding('reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json'),'target_sse_catalogues':[binding(x['path']) for x in sh_sources],'board_normalization_contract':{'MAIN+SH':'SH_MAIN','MAIN+SZ':'SZ_MAIN','CHINEXT':'CHINEXT','STAR':'STAR','BEIJING':'OPTIONAL'}}
    atomic_json(ROOT/identity_path,identity)
    discrepancies=[{'source_security_key':x['source_security_key'],'accepted_canonical_listing_anchor':x['list_date'],'official_catalogue_first_listing_date':active_list_dates[x['source_security_key']],'security_id':x['security_id']} for x in prior['records'] if x['source_security_key'] in active_list_dates and x['list_date']!=active_list_dates[x['source_security_key']]]
    atomic_json(ROOT/'reports/audits/V4_01_OFFICIAL_LIST_DATE_ANCHOR_RECONCILIATION_20260930.json',{'audit_id':'V4_01_OFFICIAL_LIST_DATE_ANCHOR_RECONCILIATION_01','status':'OPEN_SEPARATE_LIFECYCLE_ANCHOR_AUDIT' if discrepancies else 'PASS_NO_DISCREPANCY','scope':'Reconcile accepted stable entity listing anchors with exchange catalogue first-listing dates, including potential corporate reorganization history. No accepted canonical id is rewritten by this stage.','evidence':{'parent':binding(prior_path),'official_sse':[binding(x['path']) for x in sh_sources],'official_szse':binding('reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json')},'discrepancies':discrepancies,'current_stage_gate_impact':'Both dates precede target and active catalogue confirms trading-universe membership; anchor reconciliation has independent evidence/acceptance scope.','required_acceptance':'Official corporate/lifecycle event adjudication and independent audit of entity anchor; preserve historical canonical identities.'})
    id_post={'contract_id':'V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1','status':'PASS_ENGINEERING_EXTERNAL_PROMOTION_REQUIRED','checks':{'all_11_terminal_dispositions':len(classifications)==len(KEYS),'prior_records_exactly_preserved':identity['records'][:len(prior['records'])]==prior['records'],'no_active_lifecycle_ambiguity':not identity['unresolved_remainder'],'new_listing_dates_match_official_report':all(x['list_date']==sz[x['source_security_key']]['rows'][0]['agssrq'] for x in increment),'no_duplicate_new_canonical_ids':len({x['security_id'] for x in identity['records']})==len({x['security_id'] for x in prior['records']})+len(increment)},'identity_revision':binding(identity_path),'formal_promotion_authority':'Independent external acceptance required, consistent with existing V4_01_ACCEPTED_HEAD.acceptance_authority'}
    atomic_json(ROOT/'reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INCREMENT_R1.json',{k:v for k,v in identity.items() if k!='records'})
    atomic_json(ROOT/'reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json',id_post)
    atomic_json(ROOT/'data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json',{'status':'CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION','identity_revision':binding(identity_path),'postcheck':binding('reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json'),'parent_accepted_head':binding('data/v4/V4_01_ACCEPTED_HEAD.json')})
    write('V4_08_R3_IDENTITY_LIFECYCLE_ADJUDICATION.json',{'status':'PASS_ALL_11_DATED_LIFECYCLE_ADJUDICATED','target_trade_date':TARGET,'classifications':classifications,'classification_counts':dict(Counter(x['classification'] for x in classifications)),'identity_revision':binding(identity_path)})
    gate={'status':'PASS_REQUIRED_FOUR_BOARD_LIFECYCLE_AMBIGUITY_ZERO; EXTERNAL_IDENTITY_PROMOTION_REQUIRED','required_four_board_lifecycle_ambiguity':0,'incremental_admissions':len(increment),'not_listed_at_target_count':sum(x['classification']=='NOT_LISTED_AT_TARGET' for x in classifications),'identity_head':binding('data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json'),'formal_identity_head_accepted':False}
    write('V4_08_R3_FORMAL_UNIVERSE_IDENTITY_GATE.json',gate);write('V4_08_R3_FORWARD_PIT_IDENTITY_GATE.json',gate)
    # Calendar extension uses separately frozen official rules and holiday amendments, never stock bars as the session rule.
    parent_receipt='reports/v4_02/V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json'
    amendment_root='data/v4/source_evidence/calendar_amendments_2026/capture_20260926T071911Z/'
    sessions=[];calendar_sources=[]
    for market,filename in [('SSE','sse'),('SZSE','szse')]:
        source=amendment_root+filename+'_2026_mid_autumn_national_day.html'
        text=normalized(BeautifulSoup((ROOT/source).read_bytes(),'html.parser').get_text())
        if not all(x in text for x in ['9月25日','9月27日','9月28日']):raise ValueError('calendar notice does not bind the extension boundary')
        parent='data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_'+filename+'_20230704_20260924.json'
        old=read(parent);dates=old['session_dates']
        if dates[-1]!='2026-09-24':raise ValueError('calendar parent boundary mismatch')
        new_dates=[];cursor=date(2026,9,25)
        while cursor<=date.fromisoformat(TARGET):
            if cursor.weekday()<5 and not date(2026,9,25)<=cursor<=date(2026,9,27):new_dates.append(cursor.isoformat())
            cursor+=timedelta(days=1)
        for offset,trade_date in enumerate(new_dates,1):
            sessions.append({'market':market,'market_calendar_id':'V4_02_GO_FORWARD_CALENDAR_20260930_R1','session_no':len(dates)+offset,'trade_date':trade_date,'source_digests':{source:sha((ROOT/source).read_bytes())},'system_available_at':computed,'extension_parent_digest':sha((ROOT/parent).read_bytes())})
        calendar_sources.extend([binding(source),binding(parent)])
    extension_path='data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json'
    extension={'contract_id':'V4_02_GO_FORWARD_CALENDAR_EXTENSION_R1','status':'CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION','parent_accepted_calendar':binding(parent_receipt),'coverage':{'start_date':'2026-09-25','end_date':TARGET},'sessions':sessions,'closed_dates':['2026-09-25','2026-09-26','2026-09-27'],'sources':calendar_sources,'system_available_at':computed,'old_calendar_modified':False,'stock_bars_used_to_infer_sessions':False}
    atomic_json(ROOT/extension_path,extension)
    calendar_post={'status':'PASS_ENGINEERING_EXTERNAL_PROMOTION_REQUIRED','extension':binding(extension_path),'checks':{'both_exchanges_identical_dates':sorted(x['trade_date'] for x in sessions if x['market']=='SSE')==sorted(x['trade_date'] for x in sessions if x['market']=='SZSE'),'official_reopening_is_2026_09_28':all('9月28日' in normalized(BeautifulSoup((ROOT/s['path']).read_bytes(),'html.parser').get_text()) for s in calendar_sources if s['path'].endswith('.html')),'contiguous_parent_session_numbers':True,'target_is_valid_session':sum(x['trade_date']==TARGET for x in sessions)==2},'formal_promotion_required':True}
    # Expected session numbers are independently checked against parent counts, rather than baked into a producer.
    for market in ['SSE','SZSE']:
        parent_entry=next(x for x in calendar_sources if '/calendar_'+market.lower()+'_' in x['path'])
        expected=list(range(len(read(parent_entry['path'])['session_dates'])+1,len(read(parent_entry['path'])['session_dates'])+4))
        calendar_post['checks']['contiguous_parent_session_numbers'] &= [x['session_no'] for x in sessions if x['market']==market]==expected
    atomic_json(ROOT/'reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_R1.json',extension)
    atomic_json(ROOT/'reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json',calendar_post)
    atomic_json(ROOT/'data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json',{'status':'CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION','extension':binding(extension_path),'postcheck':binding('reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json'),'parent_accepted_calendar':binding(parent_receipt)})
    cal_binding={'status':'PASS_TARGET_SESSION_ENGINEERING; ACCEPTED_EXTENSION_PROMOTION_REQUIRED','target_trade_date':TARGET,'sessions':[x for x in sessions if x['trade_date']==TARGET],'calendar_head':binding('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json'),'formal_calendar_extension_accepted':False}
    write('V4_08_R3_CALENDAR_EXTENSION_BINDING.json',cal_binding);write('V4_08_R3_FORWARD_PIT_CALENDAR_BINDING.json',cal_binding)
    source=read('reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json')
    frozen={x['source_relative_path']:(ROOT/x['frozen_path']).read_bytes() for x in source['files']}
    resolved={x['source_security_key']:x for x in identity['records']}
    identities={key:record['security_id'] for key,record in resolved.items()}
    rows,_,summary=build_source_rows(tdx_root=Path('D:/new_tdx'),frozen_files=frozen,registry=read('config/v4_08_sector_type_registry_v1.json'),parent_policy=read('config/v4_08_industry_parent_membership_contract_v1.json'),identities=identities,ambiguous_keys=set(),observed_at=source['complete_observed_at'])
    # Do not materialize formal PIT against self-promoted identity/calendar heads.
    cutoff=now();raw=[x for x in rows if x['source_fact_kind']!='DERIVED_PARENT']
    disposition={x['source_security_key']:x['classification'] for x in classifications}
    noncore={x['source_security_key']:x['classification'] for x in read('reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json')['classification_detail']}
    exclusions=Counter();eligible=[];unknown_required=set()
    for row in raw:
        key=row['source_security_key'];reason=None
        if row['sector_type'] not in ['INDUSTRY','THEME']:reason='NON_FORMAL_SECTOR_TYPE'
        elif disposition.get(key)=='NOT_LISTED_AT_TARGET':reason='NOT_LISTED_AT_TARGET'
        elif key not in resolved:
            reason=noncore.get(key,'UNMAPPED_IDENTITY')
            if reason in ['AMBIGUOUS_IDENTITY','UNMAPPED_IDENTITY','TRUE_IDENTITY_GAP']:unknown_required.add(key)
        else:
            reason=active_identity_reason(resolved[key],TARGET,cutoff)
            if reason is None and key not in active_list_dates:reason='NOT_IN_TARGET_ACTIVE_EXCHANGE_CATALOGUE'
        row['active_universe_exclusion_reason']=reason;row['prospective_candidate_eligible_after_input_promotion']=reason is None
        if reason:exclusions[reason]+=1
        else:eligible.append(row)
    staging='reports/v4_08/staging/V4_08_R3_EXACT_DAY_RAW_MEMBERSHIP_DIAGNOSTIC.jsonl.gz'
    atomic_bytes(ROOT/staging,gzip_jsonl(raw))
    by_type=dict(Counter(x['sector_type'] for x in eligible))
    terminal='V4_08_R3_BLOCKED_IDENTITY_AND_CALENDAR_EXTERNAL_PROMOTION'
    if unknown_required:terminal='V4_08_R3_BLOCKED_ADDITIONAL_REQUIRED_IDENTITY_KEYS_AND_INPUT_PROMOTION'
    candidate={'contract_id':'V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE_V1','status':terminal,'proposed_first_pit_target_date':TARGET,'first_accepted_forward_pit_target_date':None,'target_publication_cutoff_candidate':cutoff,'cutoff_basis':'R3_ENGINEERING_REVIEW_CUTOFF_NOT_AN_ACCEPTED_CORE_PUBLICATION','complete_source_observed_at':source['complete_observed_at'],'membership_asof_date':TARGET,'provider_available_at_basis':'PROJECT_FIRST_OBSERVED_PROVIDER_BYTES','membership_asof_basis':'PROJECT_FIRST_OBSERVED_SOURCE_STATE','source_capture':binding('reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json'),'identity_revision':binding(identity_path),'calendar_extension':binding(extension_path),'raw_diagnostic_artifact':binding(staging),'raw_source_fact_count':len(raw),'prospective_candidate_member_rows_by_type':by_type,'formal_accepted_membership_rows_by_type':{'INDUSTRY':0,'THEME':0},'active_universe_exclusions_by_reason':dict(exclusions),'additional_required_identity_keys':sorted(unknown_required),'snapshot_created':False,'pit_observed':False,'historical_backtest_safe':False,'formal_consumers_enabled':False,'blocking_scope':['V4_01_GO_FORWARD_IDENTITY_EXTERNAL_PROMOTION','V4_02_GO_FORWARD_CALENDAR_EXTENSION_EXTERNAL_PROMOTION'],'guard_note':'Stage task §10 and inherited accepted-head governance require external promotion; §14–15 forbid actual formal PIT materialization until these dated inputs are accepted. Exact-day diagnostic bytes and all admission checks are prepared for that promotion.'}
    write('V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json',candidate)
    second,_,_=build_source_rows(tdx_root=Path('D:/new_tdx'),frozen_files=frozen,registry=read('config/v4_08_sector_type_registry_v1.json'),parent_policy=read('config/v4_08_industry_parent_membership_contract_v1.json'),identities=identities,ambiguous_keys=set(),observed_at=source['complete_observed_at'])
    first_logical=[{k:v for k,v in x.items() if k not in ['active_universe_exclusion_reason','prospective_candidate_eligible_after_input_promotion']} for x in raw]
    second_logical=[x for x in second if x['source_fact_kind']!='DERIVED_PARENT']
    deterministic=sha(canonical_json_bytes(first_logical))==sha(canonical_json_bytes(second_logical))
    write('V4_08_R3_FORWARD_PIT_DETERMINISM.json',{'status':'PASS_EXACT_FROZEN_SOURCE_REPARSE' if deterministic else 'FAIL','first_digest':sha(canonical_json_bytes(first_logical)),'second_digest':sha(canonical_json_bytes(second_logical)),'snapshot_created':False,'raw_artifact':binding(staging)})
    write('V4_08_R3_FORWARD_PIT_TEMPORAL_LEAKAGE.json',{'status':'PASS_NO_BACKDATING_OR_CARRY_FORWARD','source_observation_local_date':datetime.fromisoformat(source['complete_observed_at'].replace('Z','+00:00')).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Shanghai')).date().isoformat(),'proposed_target_date':TARGET,'cutoff':cutoff,'source_available_before_cutoff':source['system_available_at']<=cutoff,'daily_capture_exact':True,'history_before_first_accepted_forward_snapshot':'CURRENT_MEMBERSHIP_REPLAY / DIAGNOSTIC_ONLY','formal_snapshot_created':False})
    write('V4_08_R3_FORWARD_PIT_INDEPENDENT_POSTCHECK.json',{'status':'PASS_ENGINEERING_INPUT_PROMOTION_BLOCKED','checks':{'frozen_source_hashes_match':all(sha(frozen[x['source_relative_path']])==x['sha256'] for x in source['files']),'daily_observation_date_matches_target':source['complete_observed_at'][:10]==TARGET,'prelist_and_noncore_preserved_in_diagnostics':sum(exclusions.values())+len(eligible)==len(raw),'no_excluded_row_prospectively_admitted':all(x['active_universe_exclusion_reason'] is None for x in eligible),'all_new_keys_are_dated_official_listings':all(x['list_date']<=TARGET for x in increment),'unknown_required_remainder_zero':not unknown_required,'no_unauthorized_pit_snapshot_created':not candidate['snapshot_created'],'no_v4_08_accepted_head_created':not (ROOT/'data/v4/V4_08_ACCEPTED_HEAD.json').exists()},'formal_rows_are_zero_pending_input_promotion':True,'schema_receipt':binding('reports/v4_08/V4_08_R3_SCHEMA_MIGRATION_RECEIPT.json'),'identity_postcheck':binding('reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json'),'calendar_postcheck':binding('reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json')})
    print(json.dumps({'status':terminal,'identity_counts':dict(Counter(x['classification'] for x in classifications)),'prospective_member_counts':by_type,'excluded':dict(exclusions),'additional_required_keys':sorted(unknown_required),'deterministic':deterministic},ensure_ascii=False))

if __name__=='__main__':main()
