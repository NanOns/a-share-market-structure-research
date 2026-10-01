"""Capture exact old golden files outside TDX, preserving their original namespace."""
from pathlib import Path
import csv
import io
import json
import os
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import binding,immutable_json
from sector.legacy_valid_member_a05_v1 import exact_value

def main():
    evidence=json.loads((ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json').read_text(encoding='utf8'))
    archive=[];checked=0;bad=0
    for item in evidence['archaeology']:
        relative=item['source']['path']
        if not relative.startswith('reports/phase2/SAMPLE_MEMBERS_'): continue
        source=ROOT/relative;destination=ROOT/'data/v4/a05_legacy_exact_r1/legacy_samples'/source.name
        data=source.read_bytes();destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():
            if destination.read_bytes()!=data: raise ValueError('A05_GOLDEN_ARCHIVE_CONFLICT')
        else:
            fd,name=tempfile.mkstemp(dir=destination.parent,prefix='.sample.')
            try:
                with os.fdopen(fd,'wb') as stream: stream.write(data);stream.flush();os.fsync(stream.fileno())
                os.link(name,destination)
            finally: Path(name).unlink(missing_ok=True)
        records=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        for row in records:
            if 'valid_member' in row and 'missing_state' in row:
                expected=row['valid_member'].lower()=='true';actual=exact_value(row['security_id'],row['missing_state'] or None)
                bad+=actual!=expected;checked+=1
        archive.append(dict(original_namespace=item['source'],archive=binding(ROOT,destination),rows=len(records)))
    if bad: raise ValueError('A05_GOLDEN_MISMATCH')
    immutable_json(ROOT/'reports/audits/A05_REAL_GOLDEN_SAMPLE_READBACK_R1.json',dict(contract_id='A05_REAL_GOLDEN_SAMPLE_READBACK_V1',status='PASS',candidate_scope='Exact legacy real golden examples only; no external acceptance',archives=archive,real_member_values_checked=checked,mismatches=bad,namespace_resolution='Original frozen namespace + exact SHA resolves only to explicit original-byte archive; no normalization or heuristic fallback.'))
    print(json.dumps(dict(real_member_values_checked=checked,samples=len(archive),mismatches=bad)))
if __name__=='__main__': main()
