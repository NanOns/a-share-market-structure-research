"""Executable offline G1-G4 comparator for candidate daily-append vectors."""
from __future__ import annotations

import hashlib
import json


CONTRACT_ID = "V4_R8_CANDIDATE_APPEND_COMPARATOR_R1"


def _sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value.lower())


def _digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def compare_candidate_append(*, formal_predecessor, candidate_predecessor,
                             reference_snapshot, candidate_snapshot, target_session,
                             compute_sessions, source_bindings, revisions_detected=False):
    """Compare a candidate only; never admits, writes, or mutates a formal Head."""
    errors=[]
    formal_ok=(isinstance(formal_predecessor,dict) and formal_predecessor.get('accepted') is True
               and _sha(formal_predecessor.get('head_sha256')))
    if not formal_ok:errors.append('FORMAL_ACCEPTED_PREDECESSOR_NOT_PROVEN')
    candidate_identity_ok=(isinstance(candidate_predecessor,dict) and
        candidate_predecessor.get('accepted') is False and candidate_predecessor.get('evidence_class')=='NON_PIT')
    if candidate_predecessor and not candidate_identity_ok:
        errors.append('CANDIDATE_PREDECESSOR_IDENTITY_INVALID')
    g1_pass=(isinstance(reference_snapshot,dict) and isinstance(candidate_snapshot,dict) and
             reference_snapshot.get('business_values')==candidate_snapshot.get('business_values') and
             reference_snapshot.get('business_values') is not None)
    if not g1_pass:errors.append('G1_BUSINESS_SNAPSHOT_MISMATCH')
    refs=(reference_snapshot or {}).get('historical_identity',{}) if isinstance(reference_snapshot,dict) else {}
    cand=(candidate_snapshot or {}).get('historical_identity',{}) if isinstance(candidate_snapshot,dict) else {}
    g2_pass=bool(refs) and refs==cand
    if not g2_pass:errors.append('G2_HISTORICAL_IDENTITY_NOT_PRESERVED')
    bindings_ok=bool(source_bindings) and all(isinstance(x,dict) and x.get('owner') and _sha(x.get('sha256')) for x in source_bindings)
    g3_pass=bindings_ok and _sha(_digest(source_bindings))
    if not g3_pass:errors.append('G3_SOURCE_BINDINGS_INCOMPLETE')
    g4_pass=(list(compute_sessions or [])==[target_session] and not revisions_detected)
    if not g4_pass:
        errors.append('G4_APPEND_SCOPE_INVALID' if not revisions_detected else 'REVISION_REQUIRES_RANGE_REPAIR')
    status='PASS' if formal_ok and g1_pass and g2_pass and g3_pass and g4_pass and not errors else 'FAIL_CLOSED'
    return dict(contract_id=CONTRACT_ID,version='1.0.0',status=status,
        T0=target_session,formal_predecessor_accepted=formal_ok,
        candidate_predecessor_used_as_formal=False,candidate_predecessor_non_pit=candidate_identity_ok,
        G1='PASS' if g1_pass else 'FAIL',G2='PASS' if g2_pass else 'FAIL',
        G3='PASS' if g3_pass else 'FAIL',G4='PASS' if g4_pass else 'FAIL',
        reference_snapshot_sha256=_digest(reference_snapshot) if isinstance(reference_snapshot,dict) else None,
        candidate_snapshot_sha256=_digest(candidate_snapshot) if isinstance(candidate_snapshot,dict) else None,
        source_binding_count=len(source_bindings or []),errors=errors,
        writes_performed=False,head_modified=False,production_admission=False,
        evidence_class='OFFLINE_ENGINEERING_VECTOR')
