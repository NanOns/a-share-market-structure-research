"""Record limited C/A repair evidence without producing first captures."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/v4_r4_post_audit_repair_20261010'
OLD = ROOT / 'docs/evidence/v4_current_snapshot_r4_20261010'


def binding(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write(name, obj):
    target = OUT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix+'.tmp')
    temporary.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    temporary.replace(target)


def main():
    inventory = json.loads((OLD/'03_C_COHORT/C_LEGACY_EVENT_FIRST_AVAILABLE_INVENTORY.json').read_text('utf8'))
    code = binding(ROOT/'src/workbench_analysis/cohort_capture_readiness_r1.py')
    existing = [binding(OLD/'03_C_COHORT'/name) for name in
                ('C_LEGACY_EVENT_FIRST_AVAILABLE_INVENTORY.json', 'C_ADMISSION_DENIAL_TESTS.json',
                 'C_STAGE_RESULT.json', 'C_MANIFEST_SHA256.json')]
    write('04_C_COHORT/C_NEXT_LEGAL_T0_CAPTURE_READINESS.json', dict(
        contract_id='COHORT_FIRST_CAPTURE_READINESS_R1', code=code,
        base_code_sha=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        T0='2026-10-09', accepted_head=binding(ROOT/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),
        formal_owner=None, observed_count=None, matured_count=None, settled_count=None,
        legacy_events=inventory['total_events'], legacy_by_day=[dict(T0=d['T0'], count=d['event_count'],
        classification=d['classification_counts']) for d in inventory['dates']],
        root_cause='No complete T0 eligible/ineligible freeze receipt and no independent admitted Owner; corrected structure events cannot prove original enrollment',
        actual_source='EXISTING_HEAD_BOUND_EVENT_INVENTORY; NO_NEW_REAL_CAPTURE',
        future_capture_preflight='prepare_capture requires verified daily-job Head context, separate writer grant, complete full ledger, SHA-bound source, revision, frozen versions/parameters and AS_RECORDED membership version',
        daily_entry='DD R2.2 actual-source preflight -> prepare_capture isolated validation -> independent Owner/grant admission -> existing DD publication/CAS; wiring/production activation remains gated',
        production_write_authorized=False, future_data_gate='NO_2026_10_12_CAPTURE_CREATED',
        test=dict(command='python -m pytest tests/test_cohort_capture_readiness_r1.py -q -p no:cacheprovider --basetemp G:/codex_tmp/test_temp/c_capture_r1_v2',
                  exit_code=0, passed=24, output='24 passed in 0.76s', scope='SYNTHETIC_ISOLATED_ONLY'),
        old_evidence_reused_unchanged=existing,
        unmodified_code=[binding(ROOT/'src/workbench_analysis'/name) for name in
                         ('validation_cohort_read_contract_r3.py','v4_15_radar_cohort.py','v4_15_forward_r2.py')],
        status='ENGINEERING_CAPTURE_PREFLIGHT_READY_SCOPED', next_stage='EXTERNAL_RECHECK_REQUESTED; REAL_ENROLLMENT_NOT_GRANTED'))
    write('04_C_COHORT/C_SOURCE_AND_GRANT_ROLE_MATRIX.json', dict(contract_id='COHORT_FIRST_CAPTURE_READINESS_R1', roles=[
        dict(role='READ_STATISTICS', entry='read_authorized_statistics', authority='Accepted Head + exact owner/source/read grant SHA', production_write=False),
        dict(role='PREPARE_FIRST_CAPTURE', entry='prepare_capture', authority='Separate Head-bound writer grant + owner/revision/source receipt', production_write=False),
        dict(role='ISOLATED_PUBLICATION', entry='publish_isolated_candidate', authority='Read grant + exact calendar', production_write=False),
        dict(role='PRODUCTION_WRITE', entry=None, authority='Independent accepted Owner + production grant + DD R2.2 transaction/CAS/outbox', status='NOT_GRANTED')],
        maturity=dict(T1_T3_T5='Official market sessions, due does not mean settled',
                      right_censoring='Insufficient horizon/source remains unknown; no negative-return substitution',
                      benchmark='Frozen benchmark identity checked on read; real prices and outcomes owned by Forward v1.2'),
        no_owner=dict(observed_count=None, matured_count=None, settled_count=None)))
    search=OLD/'01_A_AMOUNT/A_H21_SOURCE_SEARCH_MANIFEST.json'
    write('05_A_AMOUNT/A_SCOPED_CLOSEOUT.json', dict(contract_id='FIX_A_POST_AUDIT_SCOPED_CLOSEOUT_R1',
        previous_search=binding(search), new_original_source_lead=None, new_search_executed=False,
        historical_status='H21_STRICT_HISTORY_NOT_VERIFIABLE', engineering='PASS_SCOPED_REUSED_UNCHANGED',
        formal_gate='FORMAL_H21_BLOCKED', no_full_disk_exhaustion_claim=True,
        limitations='Previous bounded local directory and direct-child Drive inventory did not prove original captures; large archives and all Drive history were not exhausted',
        missing_session_count=20, future_daily_capture_interface='Existing DD R2.2 actual-session source/owner QA/CAS, first_available and AS_RECORDED membership version frozen without backfill',
        future_samples_restore_old_history=False, amount_proxy_substitution=False,
        accepted_available_domains=['Native stock amount','Native market amount','sector participation without H21 dependency'],
        next_stage='Reopen history only on a genuine original receipt lead; no full recomputation'))


if __name__ == '__main__':
    main()
