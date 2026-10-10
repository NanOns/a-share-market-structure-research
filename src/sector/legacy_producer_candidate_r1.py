"""Executable exact-source B2 extraction; independent of formal admission."""
import json
from .producer_entry_r1 import read_bound
from .legacy_b2_r5 import evaluate_b2

CONTRACT = 'SECTOR_LEGACY_PRODUCER_EXTRACTION_R1'


def extract_legacy_candidate(root, *, input_owner, sector_id, ast_binding,
                             source_bindings):
    """Replay a byte-bound original golden sector without promoting its date.

    The original after_inputs are retained. They are not reconstructed from
    labels, current membership or Native dq5. Both non-Amount confirmed and
    independent warm branch diagnostics are available under candidate scope.
    """
    ast = json.loads(read_bound(root, ast_binding))
    for key, ast_key in (('source', 'source_sha256'),
                         ('source_parameters', 'source_parameter_sha256'),
                         ('parameters', 'parameter_set_sha256')):
        read_bound(root, source_bindings[key])
        if source_bindings[key]['sha256'] != ast[ast_key]:
            raise ValueError('EXACT_LEGACY_SOURCE_PARAMETER_MISMATCH')
    rows = [json.loads(line) for line in read_bound(root, input_owner).splitlines()
            if line.strip()]
    found = [r for r in rows if r['sector_id'] == sector_id]
    if len(found) != 1:
        raise ValueError('EXACT_ONE_LEGACY_SECTOR_REQUIRED')
    row = found[0]
    result = evaluate_b2(row['after_inputs'], ast,
        source_sha256=source_bindings['source']['sha256'],
        source_parameter_sha256=source_bindings['source_parameters']['sha256'],
        parameter_set_sha256=source_bindings['parameters']['sha256'])
    return dict(contract_id=CONTRACT, entity_type='SECTOR', entity_id=sector_id,
        trade_date=row['trade_date'], input_owner=input_owner,
        ast_binding=ast_binding, source_bindings=source_bindings,
        original_input_facts=row['after_inputs'],
        CONFIRMED=dict(value=None, status='NOT_FORMALLY_ADMITTED',
                       candidate_value=result['confirmed_diagnostic']),
        WARM=dict(value=None, status='NOT_FORMALLY_ADMITTED',
                  candidate_value=result['warm_diagnostic'],
                  branches={k: result['predicates'][k] for k in
                            ('BREADTH_BUILD', 'BASE_BUILD', 'RECOVERY_BUILD')}),
        exact_predicates=result['predicates'], accepted=False,
        formal_consumer_enabled=False, production_authorized=False,
        AS_RECORDED=False, historical_PIT_equivalent=False)
