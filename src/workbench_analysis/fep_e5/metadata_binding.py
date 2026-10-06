"""Exact accepted target/event metadata admission for canonical reconstruction.

Reconstruction authority describes dependency provenance, never signal semantics.
Engineering adapters do not activate registered targets. No schema migration.
"""
import json
import hashlib
from pathlib import Path
from workbench_analysis.fep_e1.contracts import digest

ROOT = Path(__file__).resolve().parents[3]
TARGET_CONTRACT = 'FEP_E1_TARGETS_V1'
SIGNAL_CONTRACT = 'FEP_E2_ENTRY_EVENT_STRATA_V1_1'


def reference(path):
    p = ROOT / path
    raw = p.read_bytes()
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def authority():
    target_path = 'config/fep_target_registry_v1.json'
    signal_path = 'reports/fep_e2_r1r2/ENTRY_EVENT_STRATA_CONTRACT.json'
    for path, expected in ((target_path, '1ac08f5c30e2c6748346fcc5bdbc48c1a148f67cd656fad3357710925a48eeec'),
                           (signal_path, '9884d9df4530ceea9ee3268c30e5dfb65ef149939710eb87e66d73466408025a')):
        if reference(path)['sha256'] != expected:
            raise ValueError('ACCEPTED_METADATA_SOURCE_DRIFT')
    registry = json.loads((ROOT / target_path).read_bytes())
    signal = json.loads((ROOT / signal_path).read_bytes())
    design = registry['design_module_binding']
    if reference(design['path']) != design:
        raise ValueError('TARGET_DESIGN_BINDING_DRIFT')
    text = (ROOT / design['path']).read_text(encoding='utf8')
    if '百分收益存ratio' not in text or '| ABS_RETURN_N / POSITIVE_ABS_N | R_N / I(R_N>0) | endpoint OBSERVED' not in text:
        raise ValueError('TARGET_DEFINITION_NOT_ACCEPTED')
    target = next(t for t in registry['targets'] if t['target_id'] == 'ABS_RETURN_N:T1')
    expected = dict(target_id='ABS_RETURN_N:T1', family='ABS_RETURN_N', horizon=1,
                    scope_id='FEP_STOCK_ENTRY_CORE', definition_reference='FEP.5/ABS_RETURN_N',
                    status='REGISTERED_NOT_ENABLED', training_allowed=False, engineering_adapter=True)
    if registry['contract_id'] != TARGET_CONTRACT or any(target.get(k) != v for k, v in expected.items()):
        raise ValueError('TARGET_REGISTRY_NOT_ACCEPTED')
    if signal['contract_id'] != SIGNAL_CONTRACT or signal['observation_scope'] != expected['scope_id'] or 'FIRST_PREWATCH' not in signal['formal_signals']:
        raise ValueError('EVENT_STRATA_NOT_ACCEPTED')
    row = dict(target_id=target['target_id'], contract_id=TARGET_CONTRACT, scope_id=target['scope_id'],
               horizon=target['horizon'], unit='ratio', value_kind='NUMERIC', formula='R_N',
               risk_set=dict(definition_reference=target['definition_reference'], design_binding=design,
                             endpoint_quality='OBSERVED', upstream_contract='FORWARD_PRICE_PATH_V1'),
               allowed_quality=['OBSERVED'], enabled=False)
    return dict(target_registry=registry, target_reference=reference(target_path), target_row=row,
                signal_body=signal, signal_reference=reference(signal_path),
                predicate_digest=digest(signal['first_prewatch']))


def verify_target(row, registry):
    accepted = authority()
    if registry != accepted['target_registry'] or row != accepted['target_row']:
        raise ValueError('CANONICAL_TARGET_METADATA_MISMATCH')
    return True


def verify_signal(observation, body):
    accepted = authority()
    if body != accepted['signal_body'] or observation['core_signal_contract_id'] != SIGNAL_CONTRACT:
        raise ValueError('CANONICAL_SIGNAL_CONTRACT_MISMATCH')
    if observation['scope_id'] != body['observation_scope'] or not observation['signal_key'].startswith('FIRST_PREWATCH:'):
        raise ValueError('CANONICAL_SIGNAL_EVENT_MISMATCH')
    return True


def register(pg, contract):
    accepted = authority()
    verify_target(accepted['target_row'], accepted['target_registry'])
    contract(pg, TARGET_CONTRACT, dict(source_binding=accepted['target_reference'], accepted_registry=accepted['target_registry']))
    contract(pg, SIGNAL_CONTRACT, dict(source_binding=accepted['signal_reference'], accepted_contract=accepted['signal_body'], predicate_digest=accepted['predicate_digest']))
    return accepted
