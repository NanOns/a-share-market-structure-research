"""Independent synthetic counterexamples; never produces real/PIT evidence."""
import copy
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from workbench_analysis import v4_15_settlement as old
from workbench_analysis import v4_15_settlement_successor as new
from workbench_analysis.v4_current_stage_authority import CurrentStageAuthority

class MemoryStore:
    def __init__(self):
        self.data = {}
    def read(self, ref):
        return copy.deepcopy(self.data[(ref['kind'], ref['id'])])
    def refs(self, kind):
        return [dict(kind=k, id=i) for k, i in self.data if k == kind]
    def append(self, kind, key, row):
        ident = kind, key
        if ident in self.data and self.data[ident] != row:
            raise ValueError('IMMUTABLE_MEMORY_RECORD')
        self.data[ident] = copy.deepcopy(row)
        return dict(kind=kind, id=key)

def fixture(entity_type):
    # Synthetic authority interface only; no reading Accepted Heads or database.
    authority = CurrentStageAuthority.__new__(CurrentStageAuthority)
    authority.sessions = ['2030-01-02', '2030-01-03']
    store = MemoryStore()
    basket = old.freeze_basket([dict(security_id=s, close=10) for s in ('A', 'B')], '2030-01-02', 'SECTOR')
    frozen = dict(enrollment_id='SYNTHETIC_E', T0='2030-01-02', signal_id='A', comparison_reference=1 if entity_type=='SECTOR' else 10,
                  entity_type=entity_type, subject_basket=basket, market=dict(basket, kind='MARKET'), sector=basket,
                  controls={k:dict(control_entity_ids=[], control_assignment_id=k) for k in ('A', 'B', 'C')})
    frozen['controls']['assignment_digest'] = 'SYNTHETIC_ONLY'
    frozen['snapshot'] = store.append('snapshots', 'T0', dict(universe=[]))
    ref = store.append('t0_freezes', 'F', frozen)
    row = dict(close=11, high=12, low=10, verified_identity=True, verified_adjustment=True,
               T0_basis_verified=True, evaluation_basis_date='2030-01-03', adjustment_identity='SYNTHETIC_AFFINE',
               transform_coefficients=dict(alpha=1,beta=0), source_asof='2030-01-03', available_at='2030-01-03')
    source = old.VectorPriceSource({s:{'2030-01-03':row} for s in ('A', 'B')})
    return authority, store, ref, source

results = []
for runtime, label in ((old.SettlementRuntime,'historical'), (new.SettlementRuntime,'successor')):
    authority, store, ref, source = fixture('SECTOR')
    outcome = store.read(runtime(authority,store).settle(ref,source,'2030-01-03',horizons=(1,))[0])
    results.append(dict(probe='SECTOR_BASKET_VALID_ENDPOINT', implementation=label,
        expected_absolute_return=.1, actual={k:outcome.get(k) for k in ('R_N','MFE_N','MAE_N','outcome_status','reason_codes')},
        interpretation='Sector synthetic row lacks adjustment_identity; successor rejects it. Historical path also uses close-only values as MFE_N/MAE_N.'))

authority, store, ref, source = fixture('STOCK')
runtime = new.SettlementRuntime(authority,store)
pending_ref = runtime.settle(ref,source,'2030-01-02',horizons=(1,))[0]
mature_ref = runtime.settle(ref,source,'2030-01-03',horizons=(1,))[0]
results.append(dict(probe='PENDING_THEN_DUE_SAME_EVALUATION_DIGEST', expected='DUE evaluation must not reuse PENDING outcome',
    pending_status=store.read(pending_ref)['outcome_status'], due_status=store.read(mature_ref)['outcome_status'],
    same_ref=pending_ref==mature_ref, applicability='Generic V4-15 engineering API. Durable worker admits only due obligations, so this is not a proved current real-worker failure.'))

valid = dict(close=11,high=12,low=10,verified_identity=True,verified_adjustment=True,T0_basis_verified=True,
             evaluation_basis_date='2030-01-03',adjustment_identity='SYNTHETIC_AFFINE',transform_coefficients=dict(alpha=1,beta=0))
interior = dict(valid,close=None,high=None,low=None,verified_adjustment=False)
out = new.price_path(10,[interior,valid],'2030-01-03')
results.append(dict(probe='UNKNOWN_INTERIOR_VALID_ENDPOINT',expected_endpoint_return=.1,
    actual={k:out.get(k) for k in ('R_N','MFE_N','MAE_N','outcome_status','reason_codes')},
    contract='FORWARD_PRICE_PATH_V1 unknown_gap: ENDPOINT_RETURN_INDEPENDENT_IF_VERIFIED'))

bad = dict(valid,close=-1,high=-.5,low=-2)
out = new.price_path(10,[bad],'2030-01-03')
results.append(dict(probe='INVALID_NEGATIVE_ACTUAL_PRICE', actual=out,
    applicability='Boundary hardening. Whether a formal Accepted Daily producer can emit this row is not established.'))

out = Path(__file__).resolve().parent / 'semantic_probes.json'
tmp = out.with_suffix('.tmp')
tmp.write_text(json.dumps(dict(evidence_class='SYNTHETIC_AUDIT_COUNTEREXAMPLES_NOT_REAL_OBSERVATION',results=results),
    ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
os.replace(tmp,out)
print(out.read_text(encoding='utf8'))
