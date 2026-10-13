"""Conserved arithmetic -> market source/digest and normative regime AST checks."""
import hashlib
import argparse
import json
import os
from pathlib import Path

ROOT = Path('G:/codex work/v4-production-20261012')
OUT = Path(__file__).resolve().parents[1] / 'docs/audits/v4_full_closeout_20261012/continuation_20261013/CURRENT_MARKET_ORACLE_R1'


def load(path):
    return json.loads(path.read_bytes())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--continue-failed', action='store_true')
    args = parser.parse_args()
    retained = load(OUT / 'METADATA_AND_REGIME.json') if args.continue_failed else None
    target = OUT / ('METADATA_AND_REGIME_R2.json' if args.continue_failed else 'METADATA_AND_REGIME.json')
    if target.exists():
        raise ValueError('PRESERVE_MARKET_METADATA_ORACLE')
    original = load(OUT / 'RESULT.json')
    if original['acceptance'] != 'PASS_CURRENT_MARKET_ARITHMETIC_SCOPE':
        raise ValueError('MARKET_ARITHMETIC_REQUIRED')
    candidate = load(ROOT / original['candidate']['path'])
    receipt = load(ROOT / candidate['day_receipt']['path'])
    replay = load(ROOT / receipt['numeric_core_oracle']['path'])
    day = original['T0']
    owner = next(row for row in replay['owners'] if row['trade_date'] == day)
    market = load(ROOT / original['market']['path'])
    producer = next(row for row in candidate['accepted_algorithm_bindings'] if row.get('module_path') == 'src/workbench_analysis/r43_market_replay.py')
    raw = (ROOT / producer['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != producer['sha256']:
        raise ValueError('MARKET_PRODUCER_ARCHIVE_DRIFT')
    logical_producer = dict(path=producer['module_path'], sha256=producer['sha256'], bytes=producer['bytes'])
    if args.continue_failed:
        # The actual adapter records externally executed producers under their
        # generation namespace. Consumer policy module paths are not that ref.
        generation_folder = (ROOT / original['market']['path']).parents[3]
        executed_path = generation_folder / 'executed_sources' / producer['sha256'] / producer['module_path']
        executed_bytes = executed_path.read_bytes()
        if executed_bytes != raw:
            raise ValueError('MARKET_EXECUTED_PRODUCER_ARCHIVE_MISMATCH')
        logical_producer = dict(path=executed_path.relative_to(ROOT).as_posix(), sha256=producer['sha256'], bytes=len(executed_bytes))
    source = dict(core_owner=owner['source_digest'], current_limits=market['input_bindings'][4], prior_limits=market['input_bindings'][5], producer=logical_producer)
    source_digest = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    identity = dict(trade_date=day, market_calendar_id='R4_OFFICIAL', market_snapshot_id=owner['source_digest'], adjustment_basis_id=owner['source_digest'], input_source_digest=source_digest)
    checks, errors = [], []
    def check(name, actual, expected):
        if retained is not None and name not in {row['field'] for row in retained['errors']}:
            return
        checks.append(name)
        if actual != expected:
            errors.append(dict(field=name, actual=actual, expected=expected))
    check('core_owner_binding', market['input_bindings'][0], owner['core'])
    for domain in ('axes', 'trend'):
        check(domain + '.identity', market[domain]['identity'], identity)
        payload = {key: value for key, value in market[domain].items() if key != 'output_digest'}
        check(domain + '.output_digest', market[domain]['output_digest'], digest(payload))
    p = original['primitives']
    check('axes.input_digest', market['axes']['input_digest'], digest([identity, p['breadth'], p['participation'], p['coverage'], p['stress'], p['prior_stress'], p['same_member_stress'], True]))
    check('trend.input_digest', market['trend']['input_digest'], digest([identity, p['index_close'], p['index_ma20'], p['index_ma20_t_minus_5']]))
    contract_path = ROOT / 'config/v4_04_algorithm_contracts_v3.json'
    contract = load(contract_path)['rules']['MARKET_REGIME_V1.regime_ui']
    params_path = ROOT / 'config/v4_04_parameter_set_v1.json'
    params = {row['parameter_id']: row['value'] for row in load(params_path)['parameters']}
    switch = int(params[contract['switch_sessions_parameter_id']['parameter_id']])
    def evaluate(node, fields):
        if 'constant' in node:
            return node['constant']
        if 'field' in node:
            return fields[node['field']]
        args = [evaluate(child, fields) for child in node['args']]
        op = node['operator']
        if op == 'EQ': return args[0] == args[1]
        if op == 'AND': return all(args)
        if op == 'OR': return any(args)
        if op == 'NOT': return not args[0]
        raise ValueError('UNSUPPORTED_MARKET_NORMATIVE_OPERATOR:' + op)
    accepted, pending, count = None, None, 0
    dates_checked = []
    for date in sorted(candidate['owners']):
        saved = load(ROOT / candidate['owners'][date]['market']['path'])
        fields = {name: saved['trend'][name] if name == 'trend_axis' else saved['axes'][name] for name in contract['required_axes']}
        label = 'UNKNOWN' if any(fields[key] in (None, 'UNKNOWN') for key in contract['required_axes']) else next(branch['value'] for branch in contract['candidate']['branches'] if evaluate(branch['when'], fields))
        if label == 'UNKNOWN':
            pending, count, value, reason = None, 0, 'UNKNOWN', 'REQUIRED_MARKET_AXIS_UNKNOWN'
        elif label in contract['immediate_labels'] or label == accepted:
            accepted, pending, count, value, reason = label, None, 0, label, None
        else:
            count = count + 1 if label == pending else 1
            pending = label
            if count >= switch:
                accepted, pending, count = label, None, 0
            value, reason = accepted or 'UNKNOWN', None if accepted else 'HYSTERESIS_PENDING_NO_ACCEPTED_LABEL'
        expected = dict(value=value, candidate=label, last_known=accepted, consecutive_count=count, evidence=dict(fields, candidate=label, last_known=accepted, consecutive_count=count, market_input_digest=None), unknown_reason=reason, contract_id='MARKET_REGIME_V1')
        check(date + '.regime', saved['regime'], expected)
        dates_checked.append(date)
    report = dict(contract_id='V4_MARKET_SOURCE_DIGEST_AND_NORMATIVE_REGIME_AST_ORACLE_R1', acceptance='PASS_MARKET_METADATA_AND_REGIME_SCOPE' if not errors else 'FAIL', candidate=original['candidate'], T0=day,
        reused_arithmetic_receipt=dict(path=str(OUT/'RESULT.json'), sha256=hashlib.sha256((OUT/'RESULT.json').read_bytes()).hexdigest()), market=original['market'], producer=producer,
        source_digest_input=source, normative_contract=dict(path=str(contract_path), sha256=hashlib.sha256(contract_path.read_bytes()).hexdigest()),
        check_count=len(checks), checked_fields=checks, error_count=len(errors), errors=errors, regime_dates=dates_checked,
        previous_numeric_producers_reexecuted=False, publication_ready=False,
        limitations=['Prior saved market axes are input facts for the independent regime replay; their arithmetic acceptance remains a separate gate.'],
        execution_history=['Arithmetic R1 initial verifier execution failed before assertions: KeyError candidate_thresholds; corrected the verifier to use versioned engineering_candidate_thresholds; final arithmetic 41/41 PASS.'])
    if retained is not None:
        if len(checks) != len(retained['errors']):
            raise ValueError('MARKET_FAILED_SCOPE_NOT_EXACT')
        report.update(reused_pass_checks=retained['check_count']-retained['error_count'], original_failed_receipt=dict(path=str(OUT/'METADATA_AND_REGIME.json'), sha256=hashlib.sha256((OUT/'METADATA_AND_REGIME.json').read_bytes()).hexdigest()),
            verifier_correction='Bind generation executed_sources producer path rather than the consumer policy logical module path. Actual generation bytes equal the immutable bound algorithm archive.',
            scope='Only the four original failed identity/input digest checks; nine previous PASS checks retained, including all six normative regime outputs.')
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
    os.replace(temporary, target)
    print(json.dumps(dict(acceptance=report['acceptance'], checks=len(checks), errors=len(errors))))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
