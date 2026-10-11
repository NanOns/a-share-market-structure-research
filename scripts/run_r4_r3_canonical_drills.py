"""Replay original canonical drills on explicitly attested engineering fixtures."""
import hashlib,json,os,sys,inspect,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
if not os.environ.get('R4_R3_EXTRA_PG_FIXTURES'):
    raise ValueError('EXPLICIT_ENGINEERING_MANIFEST_REQUIRED')
from scripts import run_fep_e5_r1r1b as builder
from scripts import finalize_fep_e5_r1r1b as drills
receipt=json.loads((ROOT/'docs/audits/r4_r3_scope_20261011/FEP_CANONICAL_FIXTURE_SOURCE_BINDINGS_R1.json').read_bytes())
def verified():
    for name,expected in receipt['input_sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
            raise ValueError('CANONICAL_FROZEN_SOURCE_CHANGED:'+name)
    if receipt['REAL_OOS'] or receipt['FIRST_OBSERVED'] or receipt['production_changed']:
        raise ValueError('ENGINEERING_ONLY_RECEIPT_REQUIRED')
    return receipt
drills.REPORT=builder.REPORT
drills.DSNS=builder.DSNS
drills.verified=verified
drills.emit=builder.emit
def external_binding(path):
    path=Path(path)
    raw=path.read_bytes()
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
drills.binding=external_binding
verified()
# Unique drill request identities preserve failed attempts and permit another
# actual race after an earlier attempt committed its race before failing.
run_id=uuid.uuid4().hex[:12]
source=inspect.getsource(drills.drills).replace('canonical-race-',run_id+'-canonical-race-').replace('canonical-final-revoke',run_id+'-canonical-final-revoke').replace('injected-after-receipt',run_id+'-injected-after-receipt')
namespace=dict(drills.__dict__)
exec(compile(source,'<R4_R3_CANONICAL_UNIQUE_DRILL_REQUESTS>','exec'),namespace)
namespace['drills']()
