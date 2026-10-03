"""Append-only horizon-scoped debt; corrections preserve first observed proof."""
import copy,hashlib,json
from pathlib import Path
from scripts.r20r1r1_io import ROOT,ref,exact,atomic
from scripts.r20r1r1_packet_validation import validate_packet,require,HORIZONS,data_chain
NAMESPACE='reports/r20r1r1'
DENIED='NOT_GRANTED_PENDING_MATURITY_EVIDENCE'
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def refresh(packets=(),root=ROOT):
    root=Path(root);registry=json.loads((root/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes())
    require(ref('data/v4/V4_14_ACCEPTED_HEAD.json',root)==registry['accepted_head'],'IMMUTABLE_ACCEPTED_HEAD');data_chain(root,registry)
    readback=root/NAMESPACE/'MATURITY_DEBT_READBACK.json';previous=json.loads(readback.read_bytes()) if readback.exists() else None
    if previous:
        last=exact(previous['LATEST_VALIDATED'],root)
        require({k:v for k,v in previous.items() if k not in ['FIRST_OBSERVED','LATEST_VALIDATED']}==last,'READBACK_MUST_MATCH_IMMUTABLE_REVISION')
    entries=copy.deepcopy(previous['proofs_by_enrollment_horizon'] if previous else {})
    for key,entry in entries.items():
        require(entry['FIRST_OBSERVED']==entry['receipt_history'][0] and entry['LATEST_VALIDATED']==entry['receipt_history'][-1],'FIRST_LATEST_APPEND_ONLY')
        for b in entry['receipt_history']:
            proof=exact(b,root);require(validate_packet(proof['packet'],root)==proof,'INHERITED_EXACT_PROOF_REVALIDATION')
            require(key==digest([proof['enrollment_id'],proof['horizon'],proof['due_date']]) and all(entry[k]==proof[k] for k in ['enrollment_id','horizon','due_date']),'COVERAGE_REQUIRES_EXACT_ENROLLMENT_HORIZON_PROOF')
    verified=[validate_packet(p,root) for p in packets]
    for proof in verified:
        packet=copy.deepcopy(proof['packet']);snapshot=packet['data_head'];raw=(root/snapshot['path']).read_bytes()
        frozen_snapshot=atomic(NAMESPACE+'/accepted_data_snapshots/'+snapshot['sha256']+'.json',raw,root,raw=True,immutable=True)
        packet['data_head']=frozen_snapshot;proof=validate_packet(packet,root)
        key=digest([proof['enrollment_id'],proof['horizon'],proof['due_date']]);receipt_path=NAMESPACE+'/proof_receipts/'+digest(proof)+'.json'
        if key in entries:
            old=entries[key];latest=exact(old['LATEST_VALIDATED'],root)
            if latest==proof:continue
            old_outcome=exact(latest['packet']['outcome'],root);new_outcome=exact(packet['outcome'],root)
            require(new_outcome['revision_sequence']==old_outcome['revision_sequence']+1 and new_outcome['supersedes']==latest['packet']['outcome'],'CORRECTION_MUST_APPEND_NEXT_REVISION')
            require(packet['accepted_endpoints']!=latest['packet']['accepted_endpoints'],'CHANGED_SOURCE_REQUIRED_FOR_CORRECTION')
            require(all(packet[k]==latest['packet'][k] for k in ['accepted_head','owner_publication','enrollment','freeze','horizon','freeze_completed_at']),'CORRECTION_CANNOT_CHANGE_T0')
        receipt=atomic(receipt_path,proof,root,immutable=True)
        if key not in entries:entries[key]=dict(FIRST_OBSERVED=receipt,LATEST_VALIDATED=receipt,receipt_history=[receipt],enrollment_id=proof['enrollment_id'],horizon=proof['horizon'],due_date=proof['due_date'])
        else:entries[key]['LATEST_VALIDATED']=receipt;entries[key]['receipt_history'].append(receipt)
    proved=sorted({v['horizon'] for v in entries.values()});unproved=[n for n in HORIZONS if n not in proved]
    state='OPEN' if not proved else 'PARTIAL_MATURITY_EVIDENCE' if unproved else 'FULL_REQUIRED_HORIZONS_PROVEN'
    actual=root.resolve()==ROOT.resolve()
    payload=dict(contract_id='R20R1R1_HORIZON_SCOPED_DEBT_V2',required_horizons=list(HORIZONS),proved_horizons=proved,unproved_horizons=unproved,capability_by_horizon={str(n):'PASS_CAPABILITY_SCOPED' if n in proved else DENIED for n in HORIZONS},aggregate_state=state,status=state,REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME='PASS_CAPABILITY_SCOPED' if actual and not unproved else DENIED,REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED',T0_OBSERVATION_SCOPE='RECONSTRUCTED_ASOF',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',blocks_unrelated_development=False,blocks_matured_real_claims=bool(unproved) or not actual,blocks_unqualified_matured_real_claims=bool(unproved) or not actual,stage_promotion_authorized=False,validation_environment='CURRENT_ACCEPTED_AUTHORITY' if actual else 'ISOLATED_ENGINEERING_REACHABILITY_ONLY',proofs_by_enrollment_horizon=entries,verified_maturity_receipts=[exact(v['LATEST_VALIDATED'],root) for v in entries.values()],matured_real_horizons=proved,unproved_horizons_remain_restricted=bool(unproved),accepted_data_authority=ref('data/v4/V4_DATA_ACCEPTED_HEAD.json',root))
    revision=atomic(NAMESPACE+'/debt_revisions/'+digest(payload)+'.json',payload,root,immutable=True)
    view=dict(payload,FIRST_OBSERVED=previous['FIRST_OBSERVED'] if previous else revision,LATEST_VALIDATED=revision)
    atomic(NAMESPACE+'/MATURITY_DEBT_READBACK.json',view,root)
    return revision
if __name__=='__main__':
    import sys
    print(json.dumps(refresh(json.loads(Path(sys.argv[1]).read_text(encoding='utf8')) if len(sys.argv)>1 else [])))
