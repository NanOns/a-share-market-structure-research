"""Controlled proof bridge to the unchanged accepted reducer.

This bridge accepts explicitly synthetic vectors only. Real candidate facts cannot
cross the old reducer's UNACCEPTED_D0_D1_DETECTOR gate before external acceptance.
Events re-execute reducer inputs, rather than trusting serialized final axes.
"""
from copy import deepcopy
from .confirmation import digest,ConfirmationError
from .research_state import reduce_state
from .state_provenance import validate_output

def engineering_d2_publication(inputs):
    if any(x.get('mode')!='SYNTHETIC_CONTRACT_VECTOR' for x in inputs):
        raise ConfirmationError('EXTERNAL_ACCEPTANCE_REQUIRED_FOR_REAL_D0_D2_ADOPTION')
    rows=[reduce_state(x) for x in inputs]
    if len({r['entity_id'] for r in rows})!=len(rows):raise ConfirmationError('DUPLICATE_D2_ENTITY')
    material=dict(contract_id='V4_11_CONTROLLED_D2_ENGINEERING_PROOF_V1',inputs=deepcopy(inputs),rows=rows,
        scope='SYNTHETIC_ENGINEERING_ONLY',accepted=False,production=False)
    material['publication_id']='V4_11_D2_PROOF:'+digest(material)
    return material

def verify_d2_publication(publication):
    if not isinstance(publication,dict) or publication.get('scope')!='SYNTHETIC_ENGINEERING_ONLY':raise ConfirmationError('CONTROLLED_D2_PUBLICATION_REQUIRED')
    expected=engineering_d2_publication(publication['inputs'])
    if expected!=publication:raise ConfirmationError('D2_REDUCER_READBACK_MISMATCH')
    for row in publication['rows']:validate_output(row)
    return publication['rows']
