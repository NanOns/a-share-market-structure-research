"""Promote only the exact R3 identity/calendar candidates authorized by audit."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json

AUDIT='docs/evidence/V4_08_R3_INDEPENDENT_EXTERNAL_AUDIT_20260930.md'
AUDIT_SHA256='61890d7c6ac8fcf9a4790aea710bdc2f2e6e6882a3caf128c50a0837eafc8832'
AUTH={'identity_candidate':'9ef49acc749daeb954cce0433363d0f28e54720db58c92fc20da77080049bb2c','identity_artifact':'98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603','calendar_candidate':'800a32d26b8a6089f67eda77e84c2364d4d0fd8a9879ed1b5c620be71202631b','calendar_artifact':'abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3'}

def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def binding(path):return {'path':path,'sha256':sha(path)}
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def require(path,expected):
    actual=sha(path)
    if actual!=expected:raise ValueError(f'EXTERNAL_AUTHORIZATION_DIGEST_MISMATCH:{path}:{actual}')

def promote():
    # Hard gate is evaluated before either accepted input head is created.
    gate=read('reports/v4_08/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json')
    if gate.get('status')!='PASS' or gate.get('production_runtime_hits')!=0:
        raise ValueError('NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC_HARD_GATE_FAILED')
    require(AUDIT,AUDIT_SHA256)
    identity_candidate_path='data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json'
    identity_candidate_artifact='data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json'
    calendar_candidate_path='data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json'
    calendar_artifact='data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json'
    for path,expected in [(identity_candidate_path,AUTH['identity_candidate']),(identity_candidate_artifact,AUTH['identity_artifact']),(calendar_candidate_path,AUTH['calendar_candidate']),(calendar_artifact,AUTH['calendar_artifact'])]:
        require(path,expected)
    ih=read(identity_candidate_path);candidate=read(identity_candidate_artifact)
    if ih['identity_revision']['sha256']!=AUTH['identity_artifact'] or ih['status']!='CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION':
        raise ValueError('IDENTITY_CANDIDATE_HEAD_BINDING_INVALID')
    target_new={'SZ.001246','SZ.301716'}
    additions=candidate['records'][len(read(candidate['parent_identity']['path'])['records']):]
    if {x['source_security_key'] for x in additions}!=target_new or any(x.get('acceptance')!='CANDIDATE_PENDING_EXTERNAL_PROMOTION' for x in additions):
        raise ValueError('IDENTITY_INCREMENT_SCOPE_OR_STATE_MISMATCH')
    accepted=copy.deepcopy(candidate)
    accepted['status']='ACCEPTED_GO_FORWARD_IDENTITY_TARGET_DAY_INCREMENT'
    accepted['promotion_authority']={'audit_path':AUDIT,'audit_sha256':sha(AUDIT),'authorized_scope':'2026-09-30 TARGET-DAY INCREMENTAL IDENTITY CLOSURE'}
    for records in [accepted['records'],accepted['new_lifecycle_events']]:
        for item in records:
            if item.get('source_security_key') in target_new:item['acceptance']='ACCEPTED'
    accepted_path='data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_ACCEPTED_R1.json'
    atomic_json(ROOT/accepted_path,accepted)
    accepted_hash=sha(accepted_path)
    identity_head_path='data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'
    atomic_json(ROOT/identity_head_path,{'head_id':'V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1','status':'ACCEPTED','identity_revision':binding(accepted_path),'authorized_candidate_head':binding(identity_candidate_path),'authorized_candidate_digest':AUTH['identity_candidate'],'parent_accepted_head':candidate['parent_accepted_head'],'promotion_authority':{'audit_path':AUDIT,'audit_sha256':sha(AUDIT),'scope':'2026-09-30 TARGET-DAY INCREMENTAL IDENTITY CLOSURE'},'whole_market_lifecycle_completeness_claim':False})
    # The accepted calendar head points at the exact audited immutable extension.
    cal_head=read(calendar_candidate_path);calendar=read(calendar_artifact)
    if cal_head['extension']['sha256']!=AUTH['calendar_artifact'] or calendar.get('status')!='CANDIDATE_READY_PENDING_EXTERNAL_PROMOTION':
        raise ValueError('CALENDAR_CANDIDATE_BINDING_INVALID')
    calendar_head_path='data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1.json'
    atomic_json(ROOT/calendar_head_path,{'head_id':'V4_02_GO_FORWARD_CALENDAR_EXTENSION_ACCEPTED_HEAD_R1','status':'ACCEPTED','market_calendar_id':'V4_02_GO_FORWARD_CALENDAR_20260930_R1','coverage_end':'2026-09-30','accepted_extension':binding(calendar_artifact),'authorized_candidate_head':binding(calendar_candidate_path),'authorized_candidate_digest':AUTH['calendar_candidate'],'parent_accepted_calendar':calendar['parent_accepted_calendar'],'promotion_authority':{'audit_path':AUDIT,'audit_sha256':sha(AUDIT),'scope':'SSE/SZSE MARKET SESSIONS THROUGH 2026-09-30'}})
    # Persist an independently recomputable logical diff receipt.
    changes=[]
    parent_count=len(read(candidate['parent_identity']['path'])['records'])
    for before,after in zip(candidate['records'],accepted['records']):
        if before!=after:
            diff={k:{'before':before.get(k),'after':after.get(k)} for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)}
            changes.append({'source_security_key':after['source_security_key'],'changes':diff})
    if {x['source_security_key'] for x in changes}!={'SZ.001246','SZ.301716'} or any(set(x['changes'])!={'acceptance'} for x in changes):
        raise ValueError('IDENTITY_PROMOTION_MUTATED_NON_ACCEPTANCE_FACTS')
    atomic_json(ROOT/'reports/v4_01/V4_01_GO_FORWARD_IDENTITY_EXTERNAL_PROMOTION_R1.json',{'status':'PASS_EXACT_EXTERNAL_PROMOTION','candidate_head':binding(identity_candidate_path),'candidate_artifact_sha256':AUTH['identity_artifact'],'accepted_head':binding(identity_head_path),'accepted_artifact':binding(accepted_path),'parent_records_exactly_preserved':accepted['records'][:parent_count]==candidate['records'][:parent_count],'active_acceptance_count':len(additions),'logical_diff':changes,'audit_authority':binding(AUDIT),'p0_gate':binding('reports/v4_08/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json')})
    sessions=[x for x in calendar['sessions'] if x['market'] in ['SSE','SZSE']]
    atomic_json(ROOT/'reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_EXTERNAL_PROMOTION_R1.json',{'status':'PASS_EXACT_EXTERNAL_PROMOTION','candidate_head':binding(calendar_candidate_path),'candidate_extension_sha256':AUTH['calendar_artifact'],'accepted_head':binding(calendar_head_path),'accepted_extension':binding(calendar_artifact),'accepted_session_count':len(sessions),'coverage_end':'2026-09-30','closed_dates':['2026-09-25','2026-09-26','2026-09-27'],'parent_digest_unchanged':sha(calendar['parent_accepted_calendar']['path'])==calendar['parent_accepted_calendar']['sha256'],'stock_bars_used_to_invent_sessions':False,'audit_authority':binding(AUDIT),'p0_gate':binding('reports/v4_08/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json')})
    print(json.dumps({'status':'PASS_EXACT_EXTERNAL_PROMOTION','identity_artifact_sha256':accepted_hash,'identity_head':identity_head_path,'calendar_head':calendar_head_path,'active_identity_additions':len(additions),'calendar_sessions':len(sessions)}))

if __name__=='__main__':promote()
