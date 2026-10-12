"""Unmocked isolated PG probes and preserved 56-consumer trace, not a release gate."""
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import sys
from collections import Counter
from decimal import Decimal
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
OUT = Path('G:/codex_tmp/v4_full_closeout_20261012/pg_semantics')
DSN = 'host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(name, value):
    target = OUT / name
    if target.exists():
        raise ValueError('PRESERVE_EXISTING_EVIDENCE:' + name)
    temp = target.with_suffix(target.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    temp.replace(target)

def finalize_ledgers():
    """Preserve registry clauses and dynamic intents without granting semantics."""
    old_root = Path('G:/codex work/大A交易')
    contract = old_root / 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
    inside = False
    fields = []
    for number, line in enumerate(contract.read_text(encoding='utf8').splitlines(), 1):
        if line.startswith('# 87A.'):
            inside = True
            continue
        if inside and line.startswith('# '):
            break
        if not inside or not line.startswith('|') or '---' in line or '字段/字段族' in line:
            continue
        cells = [v.strip() for v in line.strip('|').split('|')]
        if len(cells) != 5:
            continue
        for field in cells[0].split(';'):
            fields.append(dict(field_expression=field.strip(), authoritative_input=cells[1], contract=cells[2], stage=cells[3], missing_policy=cells[4], source_line=number, source_sha256=sha(contract), producer_cutoff_quality_transform_stored_consumer='OPEN_PER_FIELD_REAL_EXECUTION', oracle='OPEN_PER_FIELD_NUMERIC_AND_COUNTERFACTUAL', acceptance='OPEN_NOT_A_COLUMN_ENUMERATION_PASS'))
    rows = []
    for line in (OUT / 'PG_INTENTS.jsonl').read_text(encoding='utf8').splitlines():
        event = json.loads(line)
        key = event.get('nodeid')
        if not key:
            continue
        record = next((r for r in rows if r['nodeid'] == key), None)
        if record is None:
            record = dict(nodeid=key, pg_connections=0, pg_sql_intents=0, non_pg_intents=0, negative_control=False, scope='TARGETED_ISOLATED_PROBE_NOT_FULL_PRODUCT', acceptance='SCOPED_REAL_RUNTIME_ONLY')
            rows.append(record)
        if event.get('engine') == 'postgresql':
            record['pg_sql_intents' if event.get('event') == 'SQL_INTENT' else 'pg_connections'] += 1
        elif event.get('engine') in ('sqlite3', 'duckdb'):
            record['non_pg_intents'] += 1
            record['negative_control'] = key.endswith('test_guard_cannot_satisfy_business_exception')
    for filename, records in [('V4_PG_ACTIVE_REACHABILITY_MATRIX.csv', rows), ('V4_NORMATIVE_FIELD_LEDGER.csv', fields)]:
        output = OUT / filename
        if output.exists():
            raise ValueError('PRESERVE_EXISTING_EVIDENCE:' + filename)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
        output.write_text(buf.getvalue(), encoding='utf8')
    restored = ['docs/audits/full_system_audit_r2_20261011_58faf74e/b2_rounding_counterexamples.json', 'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json']
    write('FIXTURE_RESTORATION_AND_SCOPE.json', dict(restored=[dict(path=p, original_sha256=sha(old_root / p), restored_sha256=sha(ROOT / p), identity_equal=(old_root / p).read_bytes() == (ROOT / p).read_bytes()) for p in restored], first_execution='60_PASS_1_FAIL_MISSING_FROZEN_FIXTURE', affected_node_reexecution='1_PASS', registry_expression_count=len(fields), legal_normative_requirement_denominator=None, full_field_semantics='OPEN', engineering_algorithm_changed=False, cross_cutting_audits=['FA-009', 'M10_AMOUNT_A'], cross_cutting_audit_acceptance='NOT_ESTABLISHED_BY_THIS_PROBE'))

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = 'G:/codex_tmp'
    os.environ.update(V4_NATIVE_PG_DSN=DSN, R4_NATIVE_ISOLATION='1')
    import psycopg
    from workbench_db import api_connection, v4_native
    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
    from adjustment.tdx_adjustment_v0_3 import XrxdEvent, build_affine_factors
    inventory = ROOT / 'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json'
    consumers = json.loads(inventory.read_bytes())['consumers']
    assert len(consumers) == 56
    known = {str((ROOT / r['path']).resolve()).casefold(): r['path'].replace('\\', '/') for r in consumers}
    calls = Counter()
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code.co_filename.casefold() in known:
            calls[known[frame.f_code.co_filename.casefold()]] += 1
    sys.setprofile(profile)
    with psycopg.connect(DSN) as pg:
        identity = pg.execute("SELECT current_database(),current_user,current_setting('data_directory'),system_identifier::text FROM pg_control_system()").fetchone()
    assert Path(identity[2]).resolve() == Path('G:/codex_tmp/full_system_r4_fbd23a6b/pg_data').resolve()
    intents = []
    for config, value in [('missing', None), ('empty', ''), ('invalid', 'invalid_connection_option=x'), ('disconnected', 'host=127.0.0.1 port=1 user=r4_isolated_admin dbname=postgres')]:
        if value is None:
            os.environ.pop('V4_NATIVE_PG_DSN', None)
        else:
            os.environ['V4_NATIVE_PG_DSN'] = value
        try:
            with v4_native.connection('v4_probe_semantics'):
                raise AssertionError('UNEXPECTED_DATABASE_SUCCESS')
        except (RuntimeError, psycopg.Error) as error:
            intents.append(dict(entry='v4_native.connection', config=config, result='EXPECTED_REJECTION', exception=type(error).__name__, reason=str(error)))
        for provider in (api_connection.DuckDBApiConnectionProvider(OUT / 'forbidden.duckdb'), api_connection.PostgresDuckDBApiConnectionProvider(DSN)):
            for entry in ('connect', 'memory'):
                try:
                    with getattr(provider, entry)():
                        raise AssertionError('LEGACY_DATABASE_REACHED')
                except RuntimeError as error:
                    assert str(error) == 'V4_LEGACY_API_DATABASE_FORBIDDEN_NO_FALLBACK'
                    intents.append(dict(entry=type(provider).__name__ + '.' + entry, config=config, result='EXPECTED_REJECTION', reason=str(error)))
    os.environ['V4_NATIVE_PG_DSN'] = DSN
    jobs = DailyJobs(OUT / 'real_scheduler')
    jobs.settings(False)
    assert DailyJobs(OUT / 'real_scheduler').settings()['auto_enabled'] is False
    jobs.write_probe('2026-10-09', {'real_database_roundtrip': True})
    assert DailyJobs(OUT / 'real_scheduler').read_probe('2026-10-09') == {'real_database_roundtrip': True}
    with jobs.worker_lock():
        try:
            with DailyJobs(OUT / 'real_scheduler').worker_lock():
                raise AssertionError('SECOND_WORKER_ENTERED')
        except RuntimeError as error:
            assert str(error) == 'V4_PG_WORKER_ALREADY_OWNED'
    rollback_probe = '2099-01-01'
    try:
        with jobs.connect() as db:
            db.execute('INSERT INTO source_probe_state VALUES(?,?,clock_timestamp())', (rollback_probe, '{"rollback":true}'))
            raise ValueError('INJECTED_ROLLBACK')
    except ValueError:
        pass
    assert jobs.read_probe(rollback_probe) == {}
    frozen = ROOT / 'docs/audits/full_system_audit_r2_20261011_58faf74e/b2_rounding_counterexamples.json'
    oracles = []
    for row in json.loads(frozen.read_bytes())['rows']:
        events = [XrxdEvent(e['security_id'], e['event_date'], Decimal(str(e['cash_dividend'])), Decimal(str(e['rights_price'])), Decimal(str(e['bonus_transfer'])), Decimal(str(e['rights_ratio'])), e['source_record_index']) for e in row['events']]
        day = int(row['trade_date'].replace('-', ''))
        expected = Fraction(str(row['raw_price']))
        for event in sorted(events, key=lambda e: (e.ex_day, e.source_record_index)):
            if day < event.ex_day <= 20261009:
                expected = (expected * 10 - Fraction(event.cash_dividend_per_10) + Fraction(event.rights_price) * Fraction(event.rights_ratio_per_10)) / (10 + Fraction(event.bonus_transfer_per_10) + Fraction(event.rights_ratio_per_10))
        cents, rem = divmod(abs(expected.numerator) * 100, expected.denominator)
        cents += int(rem * 2 >= expected.denominator)
        exact = Decimal(('-' if expected < 0 else '') + f'{cents // 100}.{cents % 100:02d}')
        actual = build_affine_factors([day, 20261009], events)[day].qfq_price(str(row['raw_price']))
        assert actual == exact and float(actual) == row['exact_rational']
        oracles.append(dict(sid=row['sid'], trade_date=row['trade_date'], raw=str(row['raw_price']), rational=str(expected), expected=str(exact), actual=str(actual), result='PASS'))
    sys.setprofile(None)
    assert not list(OUT.rglob('*.sqlite*')) and not list(OUT.rglob('*.duckdb'))
    write('INDEPENDENT_PG_AND_NUMERIC_RECEIPT.json', dict(contract='V4_FULL_CLOSEOUT_PG_SEMANTICS_SCOPED_R1', database_identity=identity, negative_count=len(intents), scheduler_restart=True, worker_single_winner=True, rollback=True, driver_functions_replaced=False, oracle_source_sha256=sha(frozen), numeric_oracles=oracles, full_acceptance='OPEN_REAL_PRODUCT_PRODUCERS_AND_PER_FIELD_REQUIRED'))
    (OUT / 'V4_PG_NEGATIVE_INTENTS.jsonl').write_text(''.join(json.dumps(i) + '\n' for i in intents), encoding='utf8')
    rows = [dict(index=i, path=r['path'].replace('\\', '/'), original_sha256=r['sha256'], current_sha256=sha(ROOT / r['path']), original_transport=r['transport'], actual_calls=calls[r['path'].replace('\\', '/')], reachability='OBSERVED_IN_ISOLATED_PROBE' if calls[r['path'].replace('\\', '/')] else 'UNRESOLVED_NOT_OBSERVED', acceptance='OPEN_REAL_PRODUCT_CALLER_ORACLE') for i, r in enumerate(consumers, 1)]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    (OUT / 'V4_EXACT_56_MATRIX.csv').write_text(buf.getvalue(), encoding='utf8')
    print(json.dumps(dict(negative_count=len(intents), exact_oracles=len(oracles), preserved_consumers=len(rows), observed_consumers=sum(bool(r['actual_calls']) for r in rows))))

if __name__ == '__main__':
    main()
