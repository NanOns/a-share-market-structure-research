"""R43_SCOPED_EXTERNAL_ADMISSION_V2: provenance and per-domain admission.

An attestation is a workflow record, not a cryptographic identity proof.
Its independent signer and delivery must be verified by the human review process.
This module never creates an acceptance record.
"""
import json
from datetime import datetime,timezone
from .r43_operational_sources import checked
CONTRACT='R43_SCOPED_EXTERNAL_ADMISSION_V2'
BASE_DOMAINS=('raw','core','profile','sector','relative_sector','market')
DOMAINS=BASE_DOMAINS+('rotation','focus','forward','events','diagnostic','lifecycle','special_phase')
USER_CONTRACT='R43_USER_AUTHORIZED_SCOPED_OPERATIONAL_V1'
def verify_user_authorization(root,candidate,record):
    from .r43_operational_publication import digest
    if record.get('status')!='USER_AUTHORIZED_OPERATIONAL_CUTOVER' or record.get('contract_id')!=USER_CONTRACT or record.get('candidate_digest')!=digest(candidate):raise ValueError('EXACT_USER_AUTHORIZATION_REQUIRED')
    if record.get('historical_PIT_permission') is not False or record.get('independent_external_acceptance') is not False:raise ValueError('USER_AUTHORITY_CANNOT_CLAIM_EXTERNAL_OR_PIT_ACCEPTANCE')
    if record.get('request_origin')!='DIRECT_HUMAN_USER_MESSAGE' or record.get('request_text')!='不需要等待什么批准生产准入 ,我现在要求你  进行生产数据切换':raise ValueError('ACTUAL_USER_REQUEST_PROVENANCE_REQUIRED')
    checked(root,record['request_evidence'])
    if record.get('domain_disposition')!={k:('VALIDATION_ONGOING' if k=='rotation' else 'USER_AUTHORIZED') for k in DOMAINS}:raise ValueError('USER_DOMAIN_SCOPE_MISMATCH')
    return record
def verify_record(root,candidate,record):
    from .r43_operational_publication import digest
    if record.get('status')!='EXTERNALLY_ACCEPTED_R43_OPERATIONAL' or record.get('candidate_digest')!=digest(candidate) or record.get('historical_PIT_permission') is not False:raise ValueError('EXTERNAL_ACCEPTANCE_SCOPE_MISMATCH')
    if record.get('review_contract')!=CONTRACT:raise ValueError('VERSIONED_EXTERNAL_REVIEW_CONTRACT_REQUIRED')
    if record.get('simulation_only'):
        from pathlib import Path
        if Path(root).resolve().drive.upper()!='E:':raise ValueError('SIMULATION_AUTHORITY_FORBIDDEN_IN_PRODUCTION')
        return record
    reviewer=record.get('reviewer',{})
    if not all(reviewer.get(k) for k in ('id','name','organization','independence_statement')) or reviewer.get('independent_of_repair_executor') is not True:raise ValueError('INDEPENDENT_REVIEWER_PROVENANCE_REQUIRED')
    if not record.get('signature') or not record.get('review_tools') or not record.get('reviewed_at'):raise ValueError('SIGNED_REVIEW_TRACE_REQUIRED')
    timestamp=datetime.fromisoformat(record['reviewed_at'])
    if timestamp.tzinfo is None or timestamp>datetime.now(timezone.utc):raise ValueError('AUDIT_TIMESTAMP_INVALID')
    proof=record.get('review_evidence')
    if not isinstance(proof,dict):raise ValueError('ACTUAL_INDEPENDENT_REVIEW_EVIDENCE_REQUIRED')
    checked(root,proof)
    refs=record.get('reviewed_files',[])
    if not refs:raise ValueError('REVIEWED_FILE_BINDINGS_REQUIRED')
    for b in refs:checked(root,b)
    scoped=record.get('domain_disposition',{})
    if set(scoped)!=set(DOMAINS) or any(v not in ('ACCEPTED','VALIDATION_ONGOING','NOT_VERIFIABLE','SOURCE_INCOMPLETE') for v in scoped.values()):raise ValueError('EXPLICIT_DOMAIN_DISPOSITION_REQUIRED')
    if any(scoped.get(k)!='ACCEPTED' for k in BASE_DOMAINS):raise ValueError('BASE_RESEARCH_DOMAINS_NOT_INDEPENDENTLY_ACCEPTED')
    if scoped['rotation']=='ACCEPTED' and not record.get('full_rotation_independent_oracle'):raise ValueError('FULL_ROTATION_ORACLE_REQUIRED')
    if scoped['rotation']=='ACCEPTED':checked(root,record['full_rotation_independent_oracle'])
    # Reviewed-file declarations must bind all actual granted owner bytes, not LFS pointers.
    by_path={b['path']:b for b in refs}
    needed=[candidate['membership_snapshot'],candidate['registry']]
    for owners in candidate['owners'].values():
        needed.extend(owners[k] for k,v in scoped.items() if v=='ACCEPTED')
    if any(by_path.get(b['path'])!=b for b in needed):raise ValueError('GRANTED_SOURCE_FILE_REVIEW_NOT_BOUND')
    return record
