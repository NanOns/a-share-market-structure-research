"""Exact external authority pins; scoped accepted producer readers only."""
from pathlib import Path
from hashlib import sha256
import json
from .rps_pit_history_a02_v1 import read_bound,read_publication,delta,digest

BASELINE='66ef2e342dd339cc9795c2d1fd774b8edec4c345'
AUDIT_PATH='docs/evidence/next_round_r2/V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md'
AUDIT_SHA='7d6c8d3faf64a948d206a318d122d41baf757613d0beb88e6d5bd54fcff96bb3'
RPS_HEAD='data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json'
A05_RECORD='reports/audits/next_round_r2/A05_EXTERNAL_ACCEPTANCE_RECORD_R1.json'
ACCEPTED_RPS_EVIDENCE_SHA='1a19deb785cd3dcede58a6ffae4f8f3558d8a1d5732f3cc6f95522e51c95e602'
ACCEPTED_A05_EVIDENCE_SHA='a0e618960c4ecec9d24b42e47607f87172c699ee2f2144c7b68ef4099dc7ff16'

def accepted_evidence(root,ref,path,expected_sha):
    if ref.get('path')!=path or ref.get('sha256')!=expected_sha:raise ValueError('AUDITED_PRODUCER_EVIDENCE_PIN')
    return read_bound(root,ref)

def validate_authority(root,ref,scope):
    if ref.get('path')!=AUDIT_PATH or ref.get('sha256')!=AUDIT_SHA or ref.get('bytes')!=8244:
        raise ValueError('EXTERNAL_AUTHORITY_PIN_MISMATCH')
    path=(Path(root)/AUDIT_PATH).resolve();raw=path.read_bytes()
    if sha256(raw).hexdigest()!=AUDIT_SHA or len(raw)!=8244: raise ValueError('EXTERNAL_AUTHORITY_BYTES_MISMATCH')
    text=raw.decode('utf8')
    if BASELINE not in text or scope not in text: raise ValueError('EXTERNAL_SCOPE_NOT_ACCEPTED')
    return path

def read_accepted_rps(root,day):
    root=Path(root).resolve();head=json.loads((root/RPS_HEAD).read_bytes())
    validate_authority(root,head['external_authority'],'PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE')
    record=read_bound(root,head['acceptance_record'])
    audited=accepted_evidence(root,record['producer_evidence'],'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json',ACCEPTED_RPS_EVIDENCE_SHA)
    if record['publications']!=audited['publications'] or record['inputs']!=audited['inputs'] or record['deltas']!=audited['deltas']:raise ValueError('A02_UNAUDITED_PUBLICATION_SUBSTITUTION')
    if record['external_authority']!=head['external_authority'] or record['audited_head']!=BASELINE or record['status']!='PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE': raise ValueError('A02_ACCEPTANCE_RECORD_INVALID')
    if head['AS_RECORDED'] is not False or head['historical_first_availability_proven'] is not False or head['knowledge_lineage']!='RECONSTRUCTED_CORRECTED': raise ValueError('A02_ACCEPTANCE_SCOPE_EXPANSION')
    if head['publications']!=record['publications'] or head['accepted_dates']!=record['accepted_dates']: raise ValueError('A02_HEAD_RECORD_PUBLICATION_MISMATCH')
    if head['accepted_dates']!=sorted(audited['publications']) or any(head.get(k) is not False for k in ('production','shadow','focus','global_mandatory_adoption','downstream_amendments_accepted')):raise ValueError('A02_ACCEPTED_SCOPE_OR_PERMISSION_EXPANSION')
    if day not in head['accepted_dates']: raise ValueError('A02_DATE_NOT_ACCEPTED')
    publication=read_publication(root,head['publications'][day])
    if publication['trade_date']!=day: raise ValueError('A02_ACCEPTED_DATE_MISMATCH')
    inputs=read_bound(root,record['inputs'][day]);sessions=inputs['sessions']
    if publication['input_digest']!=digest(inputs): raise ValueError('A02_ACCEPTED_INPUT_DIGEST')
    priors={};index=sessions.index(day)
    for offset in (1,3):
        prior_day=sessions[index-offset] if index>=offset else None
        prior=read_publication(root,head['publications'][prior_day]) if prior_day in head['publications'] else None
        priors[offset]=prior
    return dict(head=head,publication=publication,prior_publications=priors,sessions=sessions,deltas={o:delta(publication,p,o,sessions) for o,p in priors.items()})

def validate_a05_record(root):
    root=Path(root).resolve();record=json.loads((root/A05_RECORD).read_bytes())
    validate_authority(root,record['external_authority'],'PASS_EXACT_CURRENT_SNAPSHOT_PRODUCER_SCOPE')
    audited=accepted_evidence(root,record['producer_evidence'],'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json',ACCEPTED_A05_EVIDENCE_SHA)
    if record['real_observations']!=audited['input_binding'] or record['source']!=audited['source_astro']['source']:raise ValueError('A05_UNAUDITED_OBSERVATION_SUBSTITUTION')
    if record['audited_head']!=BASELINE or record['status']!='PASS_EXACT_CURRENT_SNAPSHOT_PRODUCER_SCOPE' or record['historical_PIT_equivalent'] is not False or record['AS_RECORDED'] is not False:
        raise ValueError('A05_SCOPE_OR_ACCEPTANCE_INVALID')
    if any(record.get(k) is not False for k in ('production','shadow','focus','global_mandatory_adoption','historical_membership_acceptance','V4_08_business_head_amendment_accepted')):raise ValueError('A05_PERMISSION_EXPANSION')
    for key in ('source','producer','contract','real_observations'):
        ref=record[key];p=(root/ref['path']).resolve()
        if not p.is_relative_to(root) or sha256(p.read_bytes()).hexdigest()!=ref['sha256']: raise ValueError('A05_EXACT_ACCEPTANCE_BINDING')
    data=read_bound(root,record['real_observations'])
    if data['trade_date']!=record['accepted_snapshot_trade_date'] or len(data['observations'])!=6188: raise ValueError('A05_SNAPSHOT_SCOPE_MISMATCH')
    return record,data

def accepted_legacy_observations(root,*,target):
    from sector.legacy_valid_member_a05_v1 import exact_value,LEGACY_VERSION
    record,data=validate_a05_record(root)
    if target!=record['accepted_snapshot_trade_date']: raise ValueError('A05_CURRENT_SNAPSHOT_TARGET_NOT_ACCEPTED')
    return {r['source_security_id']:dict(value=exact_value(r['source_security_id'],r['missing_state']),quality='ACCEPTED',producer_contract=LEGACY_VERSION,accepted_source_scope='CURRENT_SNAPSHOT_ONLY',trade_date=target,max_source_date=target,acceptance_record=A05_RECORD,source_binding=record['real_observations']) for r in data['observations']}
