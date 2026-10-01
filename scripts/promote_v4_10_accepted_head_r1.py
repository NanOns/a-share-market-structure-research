"""Candidate generation precedes independent validation and atomic pointer promotion."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json, atomic_bytes
from scripts import validate_v4_10_promotion_r1 as v

def prepare():
    if (ROOT/v.CANDIDATE).exists(): return v.read(v.CANDIDATE)
    atomic_bytes(ROOT/v.ARCHIVE,(ROOT/v.GLOBAL).read_bytes())
    f=v.read('reports/v4_10/V4_10_R1_2_CONTRACT_FREEZE.json');m=v.read(v.MANIFEST)
    h=dict(contract_id='V4_10_ACCEPTED_HEAD_V1',stage='V4-10',status='ENGINEERING_PASS_INTERFACE_SCOPE',
        external_acceptance='EXTERNALLY_ACCEPTED',external_acceptance_decision=v.DECISION,
        implementation_commit=v.IMPLEMENTATION,audited_sealed_head=v.SEALED,parent_binding=v.bind(v.PARENT),
        evidence_bindings=v.expected_evidence(),capabilities=v.CAPABILITIES,
        protected_head_bindings=[b for b in f['protected_bindings'] if b['path'] not in (v.GLOBAL,v.PARENT)],
        open_audit_registry=m['cross_stage_registry'],global_head_parent=v.bind(v.GLOBAL),
        global_head_parent_archive=v.bind(v.ARCHIVE),accepted_at='2026-10-01',
        next_stage='V4_11_CONFIRMATION_EVENTS_ENTRY_ONLY',**{k:False for k in v.PERMISSIONS})
    atomic_json(ROOT/v.CANDIDATE,h);return h

def promote():
    h=v.read(v.CANDIDATE);result=v.validate(h)
    if result['status']!='PASS': raise ValueError(result)
    before=(ROOT/v.GLOBAL).read_bytes(); existed=(ROOT/v.HEAD).exists()
    if existed: return result
    try:
        atomic_json(ROOT/v.HEAD,h)
        g=v.read(v.GLOBAL);g.update(accepted_stage_range='V4_00_TO_V4_10_ACCEPTED',version='2.4.0',
            v4_10_binding=v.bind(v.HEAD),v4_10_status=h['status'],v4_10_external_acceptance=v.DECISION,
            v4_10_capabilities=v.CAPABILITIES,open_audit_registry=h['open_audit_registry'],
            v4_11_entry='AUTHORIZED_CONFIRMATION_EVENTS_CONTRACT_ENTRY_ONLY')
        atomic_json(ROOT/v.GLOBAL,g);result=v.validate(h)
        if result['status']!='PASS': raise ValueError(result)
    except Exception:
        atomic_bytes(ROOT/v.GLOBAL,before);(ROOT/v.HEAD).unlink(missing_ok=True);raise
    atomic_json(ROOT/'reports/v4_joint/V4_10_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json',result)
    atomic_json(ROOT/'reports/v4_joint/V4_10_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json',dict(status='PASS',
        accepted_head=v.bind(v.HEAD),global_head_after=v.bind(v.GLOBAL),parent_archive=v.bind(v.ARCHIVE),
        external_acceptance_decision=v.DECISION,validation=v.bind('reports/v4_joint/V4_10_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json'),
        data_head_moved=False,next_stage='V4_11_ENTRY_ONLY_STOP'))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');a=p.parse_args()
    print(json.dumps(prepare() if a.prepare else promote()))
