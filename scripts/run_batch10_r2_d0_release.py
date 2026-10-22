"""Publish D0 closures for already frozen, exact-date R8 candidates.

This command never builds candidates from a guessed root: --input-root is
required and candidate-safe mode is mandatory. R8 publication must exist before
the D0 publisher is called. All writes are append-only D0 publication rows.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


def _dates(first: date, last: date):
    current = first
    while current <= last:
        if current.weekday() < 5:
            yield current.isoformat()
        current += timedelta(days=1)


def _load_local_dsn(root: Path):
    env_file = root / 'config' / '.env'
    if env_file.is_file():
        for line in env_file.read_text(encoding='utf-8-sig').splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip() in ('WORKBENCH_PG_DSN', 'V4_NATIVE_PG_DSN', 'V4_NATIVE_PG_READER_DSN') and value.strip():
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    if not os.environ.get('V4_NATIVE_PG_DSN') and os.environ.get('WORKBENCH_PG_DSN'):
        os.environ['V4_NATIVE_PG_DSN'] = os.environ['WORKBENCH_PG_DSN']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-date', required=True, type=date.fromisoformat)
    parser.add_argument('--to-date', required=True, type=date.fromisoformat)
    parser.add_argument('--input-root', required=True, type=Path)
    parser.add_argument('--resume', action='store_true', help='skip dates whose exact-token D0 PG readback is already valid')
    parser.add_argument('--dry-run', action='store_true', help='validate candidates and emit plan without database writes')
    parser.add_argument('--candidate-token', help='select one exact immutable candidate token when a date has superseding revisions')
    parser.add_argument('--candidate-safe', action='store_true', help='required; prohibit production admission and formal Head changes')
    args = parser.parse_args(argv)
    if not args.candidate_safe:
        parser.error('--candidate-safe is required')
    root = args.input_root.resolve(strict=True)
    if not root.is_dir() or args.from_date > args.to_date:
        parser.error('input root must be a directory and date range must be ordered')
    repo = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(repo), str(repo / 'src')]
    _load_local_dsn(root)
    from workbench_analysis.operational_successor_v1 import digest, validate
    from workbench_analysis.d0_source_seal_r2 import independent_pg_readback, publish_candidate

    plan = []
    for day in _dates(args.from_date, args.to_date):
        day_folder = root / 'data' / 'v4' / 'dynamic_daily_owners' / day
        paths = list(day_folder.glob('*/SUCCESSOR_CANDIDATE.json')) + list(day_folder.glob('*/SUCCESSOR_CANDIDATE_MEMBERSHIP_R1.json'))
        eligible = []
        for candidate_path in paths:
            candidate_value = json.loads(candidate_path.read_bytes())
            if candidate_value.get('accepted_trade_date') != day:
                continue
            if args.candidate_token and digest(candidate_value) != args.candidate_token:
                continue
            try:
                membership_value = json.loads((root / candidate_value['native_membership_reference']['path']).read_bytes())
            except (KeyError, OSError, ValueError):
                continue
            if membership_value.get('T0') == day:
                eligible.append((candidate_path, candidate_value, membership_value))
        if len(eligible) != 1:
            raise RuntimeError(f'{day}: EXPECTED_ONE_EXACT_DATE_CANDIDATE_GOT_{len(eligible)}')
        path, candidate, membership = eligible[0]
        token = digest(candidate)
        validate(root, candidate)
        if candidate.get('AS_RECORDED') is not False or candidate.get('PIT_ELIGIBLE') is not False:
            raise RuntimeError(f'{day}: HISTORICAL_PIT_FLAGS_MUST_REMAIN_FALSE')
        item = {'trade_date': day, 'candidate_token': token, 'candidate_path': str(path),
                'membership_reference_t0': membership.get('T0'), 'action': 'DRY_RUN'}
        if not args.dry_run:
            if args.resume:
                checked = independent_pg_readback(day, token)
                if checked.get('status') == 'PG_BINDING_PRESENT':
                    item.update(action='RESUMED_VALID', d0_readback=checked.get('status'))
                    plan.append(item)
                    continue
            published = publish_candidate(repository_root=repo, candidate_root=root,
                                          candidate=candidate, trade_date=day, candidate_token=token)
            readback = independent_pg_readback(day, token)
            item.update(action='PUBLISHED', publication=published, d0_readback=readback.get('status'),
                        d0_fact_rows=readback.get('fact_rows'), d0_fact_digest=readback.get('fact_digest_readback'))
            if readback.get('status') != 'PG_BINDING_PRESENT':
                raise RuntimeError(f'{day}: RESTRICTED_D0_READBACK_FAILED:{readback.get("status")}')
        plan.append(item)
    print(json.dumps({'contract_id': 'BATCH10_R2_D0_RELEASE_R1', 'status': 'DRY_RUN' if args.dry_run else 'COMPLETE',
                      'candidate_safe': True, 'formal_head_modified': False, 'production_admission': False,
                      'input_root': str(root), 'dates': plan}, ensure_ascii=False, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
