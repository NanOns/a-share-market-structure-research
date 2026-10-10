"""Read current event bindings; create auditable R4-C evidence outside data roots."""
import os,json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/v4_current_snapshot_r4_20261010/03_C_COHORT'
def binding(path):
    raw=path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode() if not isinstance(value,str) else value.encode()
    p=OUT/name;t=OUT/(name+'.tmp');t.write_bytes(raw);os.replace(t,p)
def main():
    hpath=ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';h=json.loads(hpath.read_bytes())
    records=[];dates=[]
    fields=('publication_id','frozen_signal_version','frozen_at_T0','eligible_at_T0','asof_first_available','benchmark','no_lookahead')
    for day,owners in sorted(h['owners'].items()):
        source=owners.get('events')
        if not source:continue
        p=ROOT/source['path'];actual=binding(p)
        if actual['sha256']!=source['sha256']:raise ValueError('CURRENT_EVENT_SHA_MISMATCH')
        rows=[json.loads(x) for x in p.read_bytes().splitlines() if x.strip()]
        counter=Counter()
        for row in rows:
            available=row.get('available_at');local=datetime.fromisoformat(available).astimezone(timezone(timedelta(hours=8))) if available else None
            status='FIRST_AVAILABLE_AFTER_T0' if local and local.date().isoformat()>day else 'RECONSTRUCTED' if row.get('candidate_only') is True else 'UNPROVEN'
            counter[status]+=1
            records.append(dict(T0=day,event_id=row.get('event_id'),anchor_id=row.get('anchor_id'),security_id=row.get('security_id'),event_type=row.get('event_type'),source_revision=row.get('observation_revision'),source_fact_digest=row.get('source_fact_digest'),actual_available_at=available,classification=status,publication_id=row.get('publication_id'),freeze_receipt=None,missing_frozen_fields=[k for k in fields if not row.get(k)],admission='NO_ASOF_ENROLLMENT',source=source))
        dates.append(dict(T0=day,event_count=len(rows),classification_counts=dict(counter),source=source,validation_cohort_owner=owners.get('validation_cohort'),eligibility_owner=owners.get('core'),qualification_scope='ALL_BOUND_EVENTS; NO_FOCUS_FILTER; COMPLETE_ELIGIBLE_AND_INELIGIBLE_FREEZE_OWNER_NOT_PRESENT'))
    write('C_LEGACY_EVENT_FIRST_AVAILABLE_INVENTORY.json',dict(contract='R4-C-C02',generated_at=datetime.now(timezone.utc).isoformat(),head=binding(hpath),dates=dates,event_records=records,total_events=len(records),real_enrollment_count=None,matured_count=None,settled_count=None,legal_asof_records_proven_by_this_inventory=0,status='NO_ASOF_ENROLLMENT',scope='CURRENT_OPERATIONAL_HEAD_BOUND_STRUCTURE_EVENTS; NOT_ALL_HISTORICAL_FILES',head_unchanged=True))
    write('C_COHORT_PUBLISHER_CANDIDATE.py','''"""Evidence entry point; uses the existing module and issues no production grant."""
from workbench_analysis.validation_cohort_read_contract_r3 import publish_isolated_candidate

# Invoke only with an independently accepted Head/read grant/source manifest.
# Output must be docs/evidence; current production has no authorized owner.
__all__ = ['publish_isolated_candidate']
''')
    write('C_AUTHORIZED_ADMISSION_DESIGN.md','''# R4-C authorized admission candidate

Contract: COHORT_ISOLATED_PUBLISHER_R4_V1. Existing RadarCohortRuntime remains the event/enrollment producer; existing Forward V1.2 owns prices, controls and outcome formulas. The adapter in validation_cohort_read_contract_r3.py reuses v4_14_replay_io.publish for atomic no-clobber publication and v4_15_settlement.due_plan for session maturity.

Production read entry is read_authorized_statistics. Accepted Head binding comes from the trusted API context. It checks the Head-bound owner, explicit exact read grant, source manifest, exact frozen event bytes and source SHA. Publication/model/benchmark/signal version and AS_RECORDED membership-asof must match. Source first_available, accepted_at and published_at cannot exceed T0 freeze. Caller authorized_read=True cannot supply these authorities. A changed Head/grant/source/owner fails digest checks.

Future next legal T0: accepted reducer produces the full eligible/ineligible event ledger, freezes all required fields and first-capture receipt, then requests independent grant/Owner admission. The prepared adapter validates these artifacts, checks frozen-row equality and publishes a content-addressed isolated candidate. Retried identical input is idempotent; conflicting frozen bytes cannot overwrite. Future production activation still requires independent acceptance, publication transaction/outbox wiring and a production WRITE grant; READ_STATISTICS authorizes only isolated preparation here.

Original freezes and event identities are preserved. Corrections belong to appended revision/corrected cohort, never replacement of original T0. Missing calendar horizons remain pending/unknown; due does not mean settled. Suspension/delisting requires existing Forward settlement provenance. This stage creates no Head, production enrollment or outcome.
''')
    write('C_API_SCOPED_READ_QA.md','''# R4-C API scope

The BFF production statistics route now calls read_authorized_statistics through its trusted exact Head token; owner JSON booleans alone are rejected. Current Head has no validation_cohort owner for any of the five dates, so observed/matured/settled denominator remains unknown. Required domain reasons are NO_AUTHORIZED_COHORT_OWNER, NO_AUTHORIZED_SETTLEMENT_OWNER and MODEL_OR_PERMISSION_NOT_READY; product API/live process receipts are owned by R4-E/root and must be consulted for runtime acceptance.

C unit receipts establish hash, grant, source issuance, freeze and candidate publication scope only. They do not establish live UI/runtime acceptance. Focus remains a separate episode source; no Focus rows enter this inventory or observed cohort counts. No endpoint activation or production write occurred in C.
''')
    write('C_LIVE_ENROLLMENT_BLOCKER.md',f'''# R4-C real enrollment remains OPEN

Scanned {len(records)} exact Head-bound structure events across {len(dates)} dates. Every row lacks a formal enrollment freeze/publication receipt. Historical first-availability after T0 is explicitly classified per event; same-day candidate-only events remain reconstructed, without proof of legally frozen PIT first-capture. Operational Head is AS_RECORDED=false and PIT_ELIGIBLE=false. No formal validation_cohort owner, source admission manifest or read/write grant exists.

REAL_COHORT_ENROLLMENT_NOT_GRANTED remains OPEN. Real cohort denominator is UNKNOWN, not zero. Next step is independent acceptance of the next actual legal T0 complete producer/first-capture receipt and capability grant. No retrospective enrollment, production activation or fake maturity is authorized by these engineering tests.
''')
    write('C_STAGE_RESULT.json',dict(contract='R4-C',status='COHORT_ENGINEERING_READY_SCOPED',dimensions=dict(engineering_implemented=True,current_source_covered='SCOPED_REAL_EVENT_INVENTORY; NO_LEGAL_ENROLLMENT',strict_pit_eligible=False,shadow_permitted=False,production_permitted=False,externally_accepted=False),real_enrollment_gate='REAL_COHORT_ENROLLMENT_NOT_GRANTED_OPEN',next_stage='INDEPENDENT_SOURCE_OWNER_AND_GRANT_ACCEPTANCE',evidence_sources=[binding(ROOT/x) for x in ['src/workbench_analysis/validation_cohort_read_contract_r3.py','src/workbench_analysis/v4_15_radar_cohort.py','src/workbench_analysis/v4_15_forward_r2.py','src/workbench_analysis/v4_15_settlement.py','tests/test_cohort_admission_r4.py','tests/test_validation_cohort_read_contract_r3.py']]))
if __name__=='__main__':main()
