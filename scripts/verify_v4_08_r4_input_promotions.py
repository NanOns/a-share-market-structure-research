"""Independent exact-digest and logical-diff verifier for R4 input promotion."""
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json

def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def bind(path):return {'path':path,'sha256':digest(path)}

def verify():
    checks={}
    manifest=read('reports/v4_08/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json')
    checks['p0_hard_gate_passed']=manifest['status']=='PASS' and manifest['production_runtime_hits']==0
    authority='docs/evidence/V4_08_R3_INDEPENDENT_EXTERNAL_AUDIT_20260930.md'
    checks['audit_digest_matches_authorized_copy']=digest(authority)=='61890d7c6ac8fcf9a4790aea710bdc2f2e6e6882a3caf128c50a0837eafc8832'
    checks['candidate_heads_match_exact_external_digests']=all(digest(path)==expected for path,expected in [
        ('data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json','9ef49acc749daeb954cce0433363d0f28e54720db58c92fc20da77080049bb2c'),
        ('data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json','98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603'),
        ('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json','800a32d26b8a6089f67eda77e84c2364d4d0fd8a9879ed1b5c620be71202631b'),
        ('data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json','abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3')])
    candidate=read('data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json')
    old=read(candidate['parent_identity']['path'])
    accepted=read('data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_ACCEPTED_R1.json')
    accepted_head=read('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json')
    candidate_head=read('data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json')
    raw_candidate=digest('data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json')
    checks['identity_candidate_is_unchanged_and_accepted_head_binds_new_artifact']=raw_candidate=='98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603' and accepted_head['identity_revision']['sha256']==digest(accepted_head['identity_revision']['path']) and candidate_head['identity_revision']['sha256']==raw_candidate
    parent_count=len(old['records']);before=candidate['records'];after=accepted['records']
    checks['all_R7_records_exactly_preserved']=before[:parent_count]==old['records'] and after[:parent_count]==old['records']
    diff=[(a,b) for a,b in zip(before,after) if a!=b]
    checks['identity_logical_diff_only_two_acceptance_fields']=len(diff)==2 and {b['source_security_key'] for _,b in diff}=={'SZ.001246','SZ.301716'} and all({k for k in set(a)|set(b) if a.get(k)!=b.get(k)}=={'acceptance'} for a,b in diff)
    checks['only_two_target_active_additions_accepted']=len(after[parent_count:])==2 and {x['source_security_key'] for x in after[parent_count:]}=={'SZ.001246','SZ.301716'} and all(x['acceptance']=='ACCEPTED' for x in after[parent_count:])
    checks['all_nine_not_listed_dispositions_stay_outside_identity']=sum(x['classification']=='NOT_LISTED_AT_TARGET' for x in accepted['dispositions'])==9
    calendar=read('data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json')
    cal_head=read('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json')
    candidate_cal_head=read('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json')
    checks['calendar_candidate_and_artifact_exact_audited_digests']=digest(candidate_cal_head['extension']['path'])=='abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3' and digest(cal_head['accepted_extension']['path'])==digest(candidate_cal_head['extension']['path']) and digest(cal_head['accepted_extension']['path'])==cal_head['accepted_extension']['sha256']
    checks['calendar_parent_and_closure_chain_valid']=calendar['parent_accepted_calendar']['sha256']==digest(calendar['parent_accepted_calendar']['path']) and all(x['trade_date'] not in {'2026-09-25','2026-09-26','2026-09-27'} for x in calendar['sessions']) and all(sum(x['trade_date']==day and x['market']==market for x in calendar['sessions'])==1 for day in ['2026-09-28','2026-09-29','2026-09-30'] for market in ['SSE','SZSE'])
    checks['accepted_heads_are_append_only_and_scoped']=accepted_head['status']=='ACCEPTED' and cal_head['status']=='ACCEPTED' and accepted_head['whole_market_lifecycle_completeness_claim'] is False and cal_head['coverage_end']=='2026-09-30'
    result={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'identity_candidate_head':bind('data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json'),'identity_accepted_head':bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'),'identity_candidate_artifact_sha256':raw_candidate,'identity_accepted_artifact':bind('data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_ACCEPTED_R1.json'),'calendar_candidate_head':bind('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json'),'calendar_accepted_head':bind('data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json'),'calendar_artifact':bind('data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json'),'authority':bind(authority),'p0_gate':bind('reports/v4_08/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json')}
    atomic_json(ROOT/'reports/v4_01/V4_01_GO_FORWARD_IDENTITY_PROMOTION_POSTCHECK_R1.json',result)
    atomic_json(ROOT/'reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_PROMOTION_POSTCHECK_R1.json',result)
    print(json.dumps({'status':result['status'],'checks':checks}))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(verify())
