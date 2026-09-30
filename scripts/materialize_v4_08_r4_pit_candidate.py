"""Materialize deterministic first 2026-09-30 PIT candidate from frozen R3 facts."""
from __future__ import annotations
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys
import argparse
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from sector.membership_admission_r3 import active_identity_reason,formal_membership_eligible_r3
from sector.membership_baseline import build_source_revision_identity,canonical_json_bytes,snapshot_digest,identity_postcheck

TARGET='2026-09-30'
PIT='PIT_OBSERVED';QUALITY='PIT_OBSERVED_ACCEPTED'
FACTS='data/v4/artifact_store/v4_08/V4_08_PIT_MEMBERSHIP_FACTS_20260930_R1.jsonl.gz'
REVISION='data/v4/artifact_store/v4_08/V4_08_PIT_SOURCE_REVISION_20260930_R1.json'
SNAPSHOT='data/v4/artifact_store/v4_08/V4_08_PIT_SNAPSHOT_20260930_R1.json'
HEAD='data/v4/V4_08_PIT_MEMBERSHIP_CANDIDATE_HEAD_R1.json'

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def sha(data):return hashlib.sha256(data).hexdigest()
def bind(path):
    data=(ROOT/path).read_bytes()
    return {'path':path,'sha256':sha(data),'byte_count':len(data)}
def rows_from_gzip(path):
    with gzip.open(ROOT/path,'rt',encoding='utf-8') as stream:
        return [json.loads(line) for line in stream]
def write_immutable(path,data):
    full=ROOT/path
    if full.exists():
        if full.read_bytes()!=data:raise ValueError('APPEND_ONLY_R4_ARTIFACT_ALREADY_EXISTS_WITH_DIFFERENT_BYTES:'+path)
    else:atomic_bytes(full,data)
def accepted_identity_lookup(identity_input=None):
    head=read('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json')
    input_path=identity_input or head['identity_revision']['path']
    revision=read(input_path)
    if head['status']!='ACCEPTED' or sha((ROOT/head['identity_revision']['path']).read_bytes())!=head['identity_revision']['sha256']:
        raise ValueError('ACCEPTED_IDENTITY_HEAD_INVALID')
    if identity_input:
        equivalence=read('reports/v4_08/V4_08_R4_1_GENERIC_IDENTITY_PROMOTION_EQUIVALENCE.json')
        if equivalence.get('status')!='PASS_CURRENT_IDENTITY_PROMOTION_DATA_SALVAGED':
            raise ValueError('GENERIC_IDENTITY_PROMOTION_EQUIVALENCE_NOT_PASSED')
        if sha((ROOT/input_path).read_bytes())!=head['identity_revision']['sha256'] or equivalence.get('generic_accepted_identity_sha256')!=sha((ROOT/input_path).read_bytes()):
            raise ValueError('GENERIC_IDENTITY_REPLAY_DIFFERS_FROM_ACCEPTED_IDENTITY')
    records={}
    parent_count=len(read(revision['parent_identity']['path'])['records'])
    for index,record in enumerate(revision['records']):
        item=dict(record)
        if index<parent_count:item['acceptance']='ACCEPTED'
        if item['source_security_key'] in records:raise ValueError('DUPLICATE_ACCEPTED_IDENTITY_KEY')
        records[item['source_security_key']]=item
    return head,revision,records,{'path':input_path,'sha256':sha((ROOT/input_path).read_bytes()),'generic_replay':bool(identity_input)}

def admitted_rows(identity_input=None):
    p0=read('reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json')
    if p0['status']!='PASS' or p0['hard_gated_equity_symbol_hits']!=0 or p0['unclassified_paths']:raise ValueError('P0_SYMBOL_RUNTIME_HARD_GATE_FAILED')
    promotion=read('reports/v4_01/V4_01_GO_FORWARD_IDENTITY_PROMOTION_POSTCHECK_R1.json')
    calendar_check=read('reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_PROMOTION_POSTCHECK_R1.json')
    if promotion['status']!='PASS' or calendar_check['status']!='PASS':raise ValueError('INPUT_PROMOTION_POSTCHECK_FAILED')
    identity_head,identity,identities,identity_binding=accepted_identity_lookup(identity_input)
    calendar_head=read('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json')
    calendar=read(calendar_head['accepted_extension']['path'])
    if calendar_head['status']!='ACCEPTED' or not any(x['market']=='SSE' and x['trade_date']==TARGET for x in calendar['sessions']) or not any(x['market']=='SZSE' and x['trade_date']==TARGET for x in calendar['sessions']):
        raise ValueError('ACCEPTED_CALENDAR_TARGET_SESSION_MISSING')
    timing=read('reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json')
    cutoff=read('reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json')['target_publication_cutoff_candidate']
    local_day=datetime.fromisoformat(timing['complete_observed_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    if local_day!=TARGET or timing['complete_observed_at']>timing['system_available_at'] or timing['system_available_at']>cutoff or timing['daily_capture_reused_from_previous_day'] or timing['filesystem_mtime_used_as_availability']:
        raise ValueError('PIT_SOURCE_TIME_GATE_FAILED')
    active_catalogue=read('reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json')
    active={'SZ.'+x['agdm'] for x in active_catalogue['records']}
    for ref in identity['target_sse_catalogues']:
        doc=read(ref['path']);active.update('SH.'+x['A_STOCK_CODE'] for x in doc['result'])
    dispositions={x['source_security_key']:x for x in identity['dispositions']}
    noncore={x['source_security_key']:x['classification'] for x in read('reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json')['classification_detail']}
    raw=rows_from_gzip('reports/v4_08/staging/V4_08_R3_EXACT_DAY_RAW_MEMBERSHIP_DIAGNOSTIC.jsonl.gz')
    registry=read('config/v4_08_sector_type_registry_v1.json')
    regmap=registry['source_mapping']
    registry_sha=sha((ROOT/'config/v4_08_sector_type_registry_v1.json').read_bytes())
    provider_files=dict(sorted(timing['source_file_digests'].items()))
    exclusions=Counter();formal=[];unresolved=set()
    for source in raw:
        if source.get('source_fact_kind')=='DERIVED_PARENT':
            exclusions['DERIVED_PARENT_LINEAGE']=exclusions.get('DERIVED_PARENT_LINEAGE',0)+1
            continue
        row=dict(source)
        row['sector_type']=regmap.get(str(source.get('source_sector_type','')).lower(),'UNKNOWN')
        key=row['source_security_key'];identity_record=identities.get(key);reason=None
        if row['sector_type'] not in {'INDUSTRY','THEME'}:reason='NON_FORMAL_SECTOR_TYPE'
        elif dispositions.get(key,{}).get('classification')=='NOT_LISTED_AT_TARGET':reason='NOT_LISTED_AT_TARGET'
        elif identity_record is None:
            reason=noncore.get(key,'UNMAPPED_IDENTITY')
            if reason in {'AMBIGUOUS_IDENTITY','TRUE_IDENTITY_GAP','UNMAPPED_IDENTITY'}:unresolved.add(key)
        else:
            reason=active_identity_reason(identity_record,TARGET,cutoff)
            if reason is None and key not in active:reason='NOT_IN_TARGET_ACTIVE_EXCHANGE_CATALOGUE'
            if reason is None and identity_record.get('acceptance')!='ACCEPTED':reason='IDENTITY_NOT_ACCEPTED'
        if reason:
            exclusions[reason]+=1
            continue
        row.update(target_trade_date=TARGET,membership_asof_date=TARGET,cutoff=cutoff,
                   observed_at=timing['complete_observed_at'],provider_available_at=timing['complete_observed_at'],
                   system_available_at=timing['system_available_at'],ingested_at=timing['system_available_at'],
                   source_digest=timing['source_bytes_digest'],source_file_digests=provider_files,
                   membership_basis=PIT,membership_quality=QUALITY,snapshot_membership_basis=PIT,
                   snapshot_membership_quality=QUALITY,source_revision_membership_basis=PIT,
                   source_revision_quality=QUALITY,source_revision_chain_valid=True,
                   pit_observed=True,historical_backtest_safe=True,identity_status='MAPPED',
                   security_id=identity_record['security_id'],snapshot_lineage_role='FORWARD_PIT_CANDIDATE',
                   active_universe_exclusion_reason=None)
        if not formal_membership_eligible_r3(row,identity_record):raise ValueError('FORMAL_PIT_HELPER_REJECTED_ADMITTED_ROW')
        formal.append(row)
    if unresolved:raise ValueError('UNRESOLVED_REQUIRED_IDENTITY_KEYS:'+','.join(sorted(unresolved)))
    scope=identity_postcheck(formal)
    if scope['status']!='PASS':raise ValueError('FORMAL_FACT_IDENTITY_CONFLICT')
    formal.sort(key=lambda x:(x['sector_type'],x['sector_id'],x['security_id'],x['source_security_key']))
    excluded_total=sum(exclusions.values())
    if len(formal)+excluded_total!=len(raw):raise ValueError('SOURCE_ROW_CONSERVATION_FAILED')
    return {'formal_rows':formal,'raw_count':len(raw),'exclusions':dict(sorted(exclusions.items())),'identity_head':identity_head,'identity_revision':identity,'identity_input':identity_binding,'calendar_head':calendar_head,'calendar_extension':calendar,'timing':timing,'cutoff':cutoff,'registry_sha256':registry_sha,'source_file_digests':provider_files,'unresolved':sorted(unresolved),'active_catalogue_key_count':len(active)}

def build(identity_input=None):
    result=admitted_rows(identity_input);facts=result['formal_rows']
    temporal={'contract_id':'V4_08_R4_PIT_TEMPORAL_EVIDENCE_V1','revision_chain_valid':True,'supersedes_revision_id':None,'target_trade_date':TARGET,'membership_asof_date':TARGET,'observed_at':result['timing']['complete_observed_at'],'system_available_at':result['timing']['system_available_at'],'provider_available_at':result['timing']['complete_observed_at'],'cutoff':result['cutoff'],'provider_available_at_basis':'PROJECT_FIRST_OBSERVED_PROVIDER_BYTES','membership_asof_basis':'PROJECT_FIRST_OBSERVED_SOURCE_STATE','source_capture':bind('reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json'),'raw_membership_diagnostic':bind('reports/v4_08/staging/V4_08_R3_EXACT_DAY_RAW_MEMBERSHIP_DIAGNOSTIC.jsonl.gz'),'accepted_identity_head':bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'),'accepted_calendar_head':bind('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json'),'sector_type_registry':bind('config/v4_08_sector_type_registry_v1.json'),'no_filesystem_mtime_no_backdating_no_carry_forward':True,'membership_replay_historical':True}
    revision_identity=build_source_revision_identity(result['timing']['source_bytes_digest'],temporal)
    revision={**revision_identity,'source_contract_id':'V4_08_SECTOR_MEMBERSHIP_SOURCE_V1','source_digest':result['timing']['source_bytes_digest'],'source_bytes_digest':result['timing']['source_bytes_digest'],'source_file_digests':result['source_file_digests'],'observed_at':result['timing']['complete_observed_at'],'ingested_at':result['timing']['system_available_at'],'system_available_at':result['timing']['system_available_at'],'provider_available_at':result['timing']['complete_observed_at'],'provider_available_at_basis':'PROJECT_FIRST_OBSERVED_PROVIDER_BYTES','membership_asof_basis':'PROJECT_FIRST_OBSERVED_SOURCE_STATE','membership_asof_date':TARGET,'membership_basis':'PIT_OBSERVED','revision_quality':'PIT_OBSERVED_ACCEPTED','temporal_evidence_digest':revision_identity['temporal_evidence_digest'],'temporal_evidence':temporal,'supersedes_revision_id':None,'revision_chain_valid':True}
    snapshot_id=snapshot_digest(target_trade_date=TARGET,cutoff=result['cutoff'],sector_type_registry_digest=result['registry_sha256'],source_revision_ids=[revision['source_revision_id']],source_digest=revision['source_digest'],source_file_digests=revision['source_file_digests'],rows=facts,membership_basis='PIT_OBSERVED',membership_quality='PIT_OBSERVED_ACCEPTED')
    bound=[]
    for row in facts:
        item=dict(row);item.update(snapshot_id=snapshot_id,source_revision_id=revision['source_revision_id'],supersedes_revision_id=None)
        item['membership_fact_id']=sha(canonical_json_bytes({'snapshot_id':snapshot_id,'source_revision_id':revision['source_revision_id'],'sector_id':item['sector_id'],'security_id':item['security_id'],'source_security_key':item['source_security_key']}))
        bound.append(item)
    ids=[(x['sector_id'],x['security_id']) for x in bound]
    if len(set(ids))!=len(ids):raise ValueError('DUPLICATE_FORMAL_SNAPSHOT_FACT_IDENTITY')
    # Logical source and output identity excludes only database generated created_at fields.
    fact_digest=sha(canonical_json_bytes(bound))
    fact_bytes=gzip.compress(b''.join(canonical_json_bytes(x)+b'\n' for x in bound),compresslevel=9,mtime=0)
    write_immutable(FACTS,fact_bytes)
    type_counts=dict(sorted(Counter(x['sector_type'] for x in bound).items()))
    sector_counts={t:len({x['sector_id'] for x in bound if x['sector_type']==t}) for t in ['INDUSTRY','THEME']}
    member_counts={t:len({x['security_id'] for x in bound if x['sector_type']==t}) for t in ['INDUSTRY','THEME']}
    snapshot={'snapshot_id':snapshot_id,'target_trade_date':TARGET,'cutoff':result['cutoff'],'sector_type_registry_digest':result['registry_sha256'],'source_revision_id':revision['source_revision_id'],'source_digest':revision['source_digest'],'source_file_digests':revision['source_file_digests'],'membership_basis':'PIT_OBSERVED','membership_quality':'PIT_OBSERVED_ACCEPTED','pit_observed':True,'historical_backtest_safe':True,'row_count':len(bound),'derived_parent_row_count':0,'snapshot_lineage_role':'FORWARD_PIT_CANDIDATE','supersedes_snapshot_id':None,'formal_facts':bind(FACTS),'formal_fact_logical_digest':fact_digest}
    fact_count={'status':'PASS_INDEPENDENTLY_RECOMPUTED_NOT_ORACLE_COUNTS','row_count':len(bound),'formal_rows_by_type':type_counts,'unique_sector_count_by_type':sector_counts,'unique_member_count_by_type':member_counts,'unique_sector_id_count':len({x['sector_id'] for x in bound}),'unique_member_id_count':len({x['security_id'] for x in bound}),'raw_source_row_count':result['raw_count'],'active_exchange_catalogue_key_count':result['active_catalogue_key_count'],'expected_R3_counts_treated_as_oracle':False}
    exclusion={'status':'PASS_SOURCE_ROW_CONSERVATION','exclusions_by_reason':result['exclusions'],'excluded_row_count':sum(result['exclusions'].values()),'raw_row_count':result['raw_count'],'formal_row_count':len(bound),'conservation':sum(result['exclusions'].values())+len(bound)==result['raw_count'],'prelist_and_nonformal_diagnostic_rows_preserved':True,'raw_diagnostic':bind('reports/v4_08/staging/V4_08_R3_EXACT_DAY_RAW_MEMBERSHIP_DIAGNOSTIC.jsonl.gz')}
    revision_bytes=json.dumps(revision,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n'
    snapshot_bytes=json.dumps(snapshot,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n'
    write_immutable(REVISION,revision_bytes);write_immutable(SNAPSHOT,snapshot_bytes)
    candidate_head={'head_id':'V4_08_PIT_MEMBERSHIP_CANDIDATE_HEAD_R1','status':'V4_08_R4_PIT_MEMBERSHIP_CANDIDATE_READY_FOR_FINAL_EXTERNAL_ACCEPTANCE','snapshot':bind(SNAPSHOT),'source_revision':bind(REVISION),'facts':bind(FACTS),'identity_head':bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'),'calendar_head':bind('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json'),'source_capture':bind('reports/v4_08/V4_08_R3_FORWARD_PIT_SOURCE_CAPTURE.json'),'formal_consumers_enabled':False,'first_accepted_pit_date_pending_external_acceptance':True}
    headbytes=json.dumps(candidate_head,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n';write_immutable(HEAD,headbytes)
    return {'revision':revision,'snapshot':snapshot,'facts':bound,'facts_bytes':fact_bytes,'fact_digest':fact_digest,'fact_count':fact_count,'exclusion':exclusion,'candidate_head':candidate_head,'raw_count':result['raw_count'],'cutoff':result['cutoff'],'identity_head':result['identity_head'],'identity_input':result['identity_input'],'calendar_head':result['calendar_head'],'timing':result['timing']}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--identity-replay',help='Use the independently verified generic identity promotion replay as the PIT input')
    args=parser.parse_args()
    first=build(args.identity_replay);second=build(args.identity_replay)
    checks={'source_revision_identity_equal':first['revision']['source_revision_id']==second['revision']['source_revision_id'],'snapshot_id_equal':first['snapshot']['snapshot_id']==second['snapshot']['snapshot_id'],'fact_logical_digest_equal':first['fact_digest']==second['fact_digest'],'fact_bytes_equal':first['facts_bytes']==second['facts_bytes'],'sector_and_member_sets_equal':[(x['sector_id'],x['security_id']) for x in first['facts']]==[(x['sector_id'],x['security_id']) for x in second['facts']],'exclusions_equal':first['exclusion']==second['exclusion']}
    if not all(checks.values()):raise ValueError('R4_DETERMINISM_FAILED')
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_SOURCE_REVISION.json',first['revision'])
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_SNAPSHOT.json',first['snapshot'])
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_FACT_COUNTS.json',first['fact_count'])
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_EXCLUSION_INVENTORY.json',first['exclusion'])
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_DETERMINISM.json',{'status':'PASS_TWO_IDENTICAL_MATERIALIZATIONS','checks':checks,'source_revision_id':first['revision']['source_revision_id'],'snapshot_id':first['snapshot']['snapshot_id'],'facts_logical_digest':first['fact_digest'],'facts_byte_sha256':sha(first['facts_bytes']),'row_count':len(first['facts'])})
    obs=datetime.fromisoformat(first['timing']['complete_observed_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_TEMPORAL_LEAKAGE.json',{'status':'PASS_NO_BACKDATING_NO_CARRY_FORWARD','target_date':TARGET,'complete_source_observation_at':first['timing']['complete_observed_at'],'source_observation_local_date':obs,'cutoff':first['cutoff'],'source_available_at_or_before_cutoff':first['timing']['system_available_at']<=first['cutoff'],'provider_available_at_basis':first['revision']['provider_available_at_basis'],'membership_asof_basis':first['revision']['membership_asof_basis'],'mtime_used':False,'prior_days_reconstructed':False,'pre_first_accepted_history':'CURRENT_MEMBERSHIP_REPLAY / DIAGNOSTIC_ONLY'})
    print(json.dumps({'status':first['candidate_head']['status'],'source_revision_id':first['revision']['source_revision_id'],'snapshot_id':first['snapshot']['snapshot_id'],'rows':first['fact_count']['row_count'],'counts':first['fact_count']['formal_rows_by_type'],'exclusions':first['exclusion']['exclusions_by_reason'],'identity_input':first['identity_input'],'snapshot_created':True,'accepted_head_created':False},ensure_ascii=False))

if __name__=='__main__':main()
