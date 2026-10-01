"""Versioned exact-coordinate runtime repair with complete real-slot equivalence."""
from scripts.next_round_execution_r3 import *
from copy import deepcopy

def main():
    proofpath='reports/v4_11_r3/V4_11_R3C_COORDINATE_SOURCE_CHARACTERIZATION_R2.json'
    proof=read(proofpath)
    if not proof['all_actual_coordinate_strings_exact'] or not proof['all_actual_adjustment_basis_digests_exact'] or proof['actual_price_ready_slots_checked']!=258659:
        raise ValueError('COMPLETE_REAL_SLOT_RUNTIME_EQUIVALENCE_REQUIRED')
    for ref in proof['bindings'].values():exact(ref)
    old='config/v4_11_r3c_candidate_d2_contract_v2.json';value=deepcopy(read(old))
    value.update(revision='R3_EXACT_NUMERIC_COORDINATE_AUTHORITY',prior_contract=bind(old),
        prior_runtime_archive=proof['bindings']['archive'],upstream_adapter=proof['bindings']['final_runtime'],
        coordinate_runtime_equivalence=bind(proofpath),
        exact_change='Numeric coordinate canonicalization only; all 258659 real ready bar coordinate strings and basis digests byte-identical',
        source_publications_action='KEEP_EXACT_SEALED_R2_SOURCE_SET; factor operations, source rows, values and evidence identities unchanged')
    authority=write('config/v4_11_r3c_candidate_d2_contract_v3.json',value)
    rbpath='reports/v4_11_r3/V4_11_R3_D2_READBACK.json'
    rb=read(rbpath);write('reports/v4_11_r3/superseded/D2_READBACK_ORIGINAL_R2.json',rb)
    rb.update(contract=authority,coordinate_runtime_equivalence=bind(proofpath),
        runtime_authority_revision='V3_EXACT_NUMERIC_COORDINATE',
        actual_source_derivations='R2 complete arithmetic execution; equivalence proves every source coordinate string and digest identical under final runtime')
    write(rbpath,rb,immutable=False)
    closure=write('reports/v4_11_r3/R3C_RUNTIME_AUTHORITY_CLOSURE_R3.json',dict(status='PASS_ACTUAL_SOURCE_RUNTIME_IDENTITY_EQUIVALENCE',
        authority=authority,D2_readback=bind(rbpath),proof=bind(proofpath),accepted=False,permissions=PERMISSIONS,
        acceptance='ENGINEERING_CANDIDATE_ONLY',next_stage='CLEAN_CHECKOUT_REAL_D2_REEXECUTION_AND_FULL_REGRESSION'))
    hp='reports/v4_11_r3/V4_11_R3_EXTERNAL_REAUDIT_HANDOFF.json';handoff=read(hp)
    write('reports/v4_11_r3/superseded/EXTERNAL_HANDOFF_ORIGINAL_R2.json',handoff)
    handoff.update(D2_readback=bind(rbpath),runtime_authority=authority,runtime_equivalence_closure=closure)
    write(hp,handoff,immutable=False)
    verify_protected();print('FINAL_RUNTIME_AUTHORITY_V3_SEALED')

if __name__=='__main__':main()
