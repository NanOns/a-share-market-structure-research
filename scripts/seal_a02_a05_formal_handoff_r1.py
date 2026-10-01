"""Seal scoped formalization and fresh business candidate evidence for root batch."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from v4.rps_pit_history_a02_v1 import binding,immutable_json
from scripts.verify_a02_a05_formal_amendment_readback_r1 import verify_a02,verify_a05

def main():
    proofs=dict(contract_id='A02_A05_FORMAL_AMENDMENT_READBACK_V1',A02=verify_a02(),A05=verify_a05(),status='PASS',business_amendments_externally_accepted=False,production=False)
    proof_path=ROOT/'reports/audits/next_round_r2/A02_A05_INDEPENDENT_FORMAL_READBACK_R1.json';immutable_json(proof_path,proofs)
    files=[]
    for pattern in ['src/v4/a02_a05_external_acceptance_r1.py','src/sector/a05_b2_scoped_amendment_r1.py','scripts/formalize_a02_a05_accepted_producers_r1.py','scripts/replay_a02_accepted_rps_amendments_r1.py','scripts/replay_a05_b2_current_snapshot_amendment_r*.py','scripts/verify_a02_a05_formal_amendment_readback_r1.py','scripts/seal_a02_a05_formal_handoff_r1.py','tests/v4_a02_a05_formal_r1/*.py','data/v4/a02_accepted_amendments_r1/*','data/v4/a05_b2_amendment_r*/*','data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json','reports/audits/next_round_r2/A02*.json','reports/audits/next_round_r2/A05*.json','reports/audits/next_round_r2/V4_*A02*.json','reports/audits/next_round_r2/V4_08_ACCEPTED_HEAD_B2*.json','docs/audits/A02_EXTERNAL_FORMALIZATION_AMENDMENT_CLOSURE_R1_20261001.md','docs/audits/A05_EXTERNAL_FORMALIZATION_B2_AMENDMENT_CLOSURE_R1_20261001.md']:
        files.extend(p for p in ROOT.glob(pattern) if p.is_file())
    excluded=ROOT/'reports/audits/next_round_r2/A02_A05_FORMAL_HANDOFF_R1.json'
    handoff=dict(contract_id='A02_A05_FORMAL_HANDOFF_V1',baseline_commit='66ef2e342dd339cc9795c2d1fd774b8edec4c345',A02_external_acceptance_formalized='PASS',A05_external_acceptance_formalized='PASS',A02_final_amendment='A02_DOWNSTREAM_AMENDMENTS_READY_FOR_EXTERNAL_REAUDIT',A05_final_amendment='V4_08_B2_AMENDMENT_READY_FOR_EXTERNAL_REAUDIT',independent_readback=binding(ROOT,proof_path),targeted_tests=binding(ROOT,ROOT/'reports/audits/next_round_r2/A02_A05_FORMAL_TARGETED_TESTS_R1.xml'),clean_checkout_and_no_symbol='Root batch final receipt must provide new independently committed checkout validation; do not reuse historical clean receipts.',files=[binding(ROOT,p) for p in sorted(set(files)) if p!=excluded],permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False),old_accepted_heads_unchanged=True,Stage_Head_unchanged=True,Data_Head_unchanged=True,V4_12_implemented=False,next_stage='Independent external acceptance of all downstream business amendments; root unified commit/push then STOP.')
    immutable_json(excluded,handoff)
    print(json.dumps(dict(status='SEALED_FOR_BATCH',files=len(handoff['files']),A02=proofs['A02'],A05=proofs['A05'])))
if __name__=='__main__':main()
