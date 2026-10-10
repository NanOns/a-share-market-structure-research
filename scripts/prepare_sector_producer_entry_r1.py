"""Read-only real Native -> isolated SECTOR Producer entry command."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from sector.producer_entry_r1 import prepare_entry, read_bound


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sector-id')
    parser.add_argument('--publishers', type=Path,
                        help='Isolated per-field binding manifest, not an admission grant')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if not (out.is_relative_to((ROOT / 'docs/evidence').resolve()) or
            out.is_relative_to(Path('G:/codex_tmp').resolve())):
        raise ValueError('EVIDENCE_OR_G_TEMP_OUTPUT_REQUIRED')
    head_path = ROOT / 'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    head_bytes = head_path.read_bytes()
    head = json.loads(head_bytes)
    target = head['accepted_trade_date']
    binding = head['owners'][target]['sector']
    rows = [json.loads(line) for line in read_bound(ROOT, binding).splitlines()]
    native = next(row for row in rows if not args.sector_id or
                  row['sector_id'] == args.sector_id)
    spec = json.loads(args.publishers.read_bytes()) if args.publishers else {}
    prior_binding = spec.get('prior_binding')
    prior = json.loads(read_bound(ROOT, prior_binding)) if prior_binding else None
    result = prepare_entry(ROOT, native, source_binding=binding,
        cutoff=spec.get('cutoff', target + 'T23:59:59+08:00'),
        publishers=spec.get('publishers'), prior=prior, prior_binding=prior_binding,
        sessions=spec.get('sessions'))
    result['operational_head_binding'] = dict(path=str(head_path.relative_to(ROOT)),
        bytes=len(head_bytes), sha256=hashlib.sha256(head_bytes).hexdigest())
    assert head_bytes == head_path.read_bytes(), 'HEAD_CHANGED_DURING_READ'
    out.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf8')
    if out.exists():
        if out.read_bytes() != encoded:
            raise ValueError('CANDIDATE_OUTPUT_NO_CLOBBER')
        print(json.dumps(dict(status=result['readiness'], idempotent=True)))
        return
    temp = out.with_suffix(out.suffix + '.tmp')
    with temp.open('xb') as stream:
        stream.write(encoded)
    try:
        os.link(temp, out)  # atomic publication and no concurrent overwrite
    finally:
        temp.unlink()
    print(json.dumps(dict(status=result['readiness'], entity_id=result['entity_id'],
        entry_contract_id=result['entry_contract_id'], reducer_invoked=False,
        production_authorized=False)))


if __name__ == '__main__':
    main()
