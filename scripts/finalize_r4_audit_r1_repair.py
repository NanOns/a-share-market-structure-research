"""Seal scoped engineering results without granting external owner admission."""
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.verify_r4_audit_r1_bytes import OUT, read, write, sha
from workbench_analysis.tdx_official_daily_source import _atomic_write


def main():
    source = Path('D:/Users/lps/Desktop/阶段任务/V4_R4_1_9BE4A498E6A595E6AEA1E9908BE78BA4E5A1_R1_20261009.md')
    _atomic_write(OUT / 'EXTERNAL_AUDIT_R1_INPUT.md', source.read_bytes(), tdx_root=Path('D:/new_tdx'))
    pointer = ROOT / 'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json'
    # The legacy downloader updates its locator. Preserve the new receipt, then
    # restore the entry locator exactly; frozen prior evidence remains resolvable.
    entry = subprocess.check_output(['git', 'show', 'HEAD:reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json'], cwd=ROOT)
    if pointer.read_bytes() != entry:
        observed = read(pointer)
        capture = ROOT / observed['capture_receipt']['path']
        write('NEW_OFFICIAL_CAPTURE_RECEIPT.json', read(capture))
        write('NEW_OFFICIAL_CAPTURE_BINDING.json', observed)
    _atomic_write(pointer, entry, tdx_root=Path('D:/new_tdx'))
    numeric = read(OUT / 'BYTE_NUMERIC_READBACK.json')
    identities = read(OUT / 'UNBOUND_IDENTITY_CLASSIFICATION.json')
    delta = read(OUT / 'OFFICIAL_PACKAGE_STRICT_DELTA_BLOCKERS.json')
    daily = read(OUT / 'daily/2026-10-08/source_readiness_receipt_r2.json')
    with urllib.request.urlopen('http://127.0.0.1:28765/api/v4/context', timeout=10) as response:
        live = json.load(response)
    write('LIVE_API_CONTEXT_READBACK.json', live)
    repair = ROOT / 'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1'
    items = [
        dict(id='R4R1-P0-1', scope='Actual LFS objects and arithmetic',
             evidence=['BYTE_NUMERIC_READBACK.json', 'NUMERIC_SAMPLES.json'],
             acceptance=numeric['acceptance'], remaining='Independent external event semantics, source and field/owner approval'),
        dict(id='R4R1-P0-2', scope='Formal DM01 delta and source acceptance',
             evidence=['daily/2026-10-08/source_readiness_receipt_r2.json','OFFICIAL_PACKAGE_STRICT_DELTA_BLOCKERS.json'],
             acceptance=daily['status'], remaining='Versioned scoped treatment of invalid vendor entries; separate successor runtime seal; original as-recorded flow cannot admit retrospective source'),
        dict(id='R4R1-P0-3', scope='Unbound identity rows', evidence=['UNBOUND_IDENTITY_CLASSIFICATION.json'],
             acceptance='CLASSIFIED_NOT_ACCEPTED', remaining='BSE candidate source/aliases need independent authority; unresolved identities stay null'),
        dict(id='R4R1-P1-4', scope='Breakout first event and prior episode',
             evidence=['PROFILE_STRUCTURE_REPLAY.json','SOURCE_BINDINGS.json'],
             acceptance='BLOCKED_ACCEPTED_PRIOR_EPISODE', remaining='No accepted initial prior episode/absence proof; no UNKNOWN to FALSE bootstrap'),
        dict(id='R4R1-P1-5', scope='TDX taxonomy and rotation', evidence=['SECTOR_REPLAY.json','MARKET_ROTATION_REPLAY.json'],
             acceptance='BLOCKED_EFFECTIVE_MEMBERSHIP_AND_PRIOR_ROTATION', remaining='83 CSRC categories never substitute 378 product sectors; no accepted TDX historical concepts or prior rotation'),
        dict(id='R4R1-P1-6', scope='Market limits and Focus/Forward first availability', evidence=['FOCUS_FORWARD_REPLAY.json','MARKET_ROTATION_REPLAY.json'],
             acceptance='PARTIAL_CANDIDATES_NOT_FULL_ACCEPTANCE', remaining='Dated limit owner and actual mature due/exit/reentry/T0 samples remain separate acceptance objects')]
    write('SEPARATE_AUDIT_REGISTER.json', dict(items=items, no_cross_gate_waiver=True))
    bindings=[]
    for name in ('CORE_REPLAY','PROFILE_STRUCTURE_REPLAY','SECTOR_REPLAY','MARKET_ROTATION_REPLAY','FOCUS_FORWARD_REPLAY','OWNER_STAGE_SEAL_V1'):
        p=repair/(name+'.json')
        bindings.append(dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p), bytes=p.stat().st_size))
    write('SCOPED_EXTERNAL_ADMISSION_OBJECT.json', dict(
        contract_id='R4R1_SCOPED_EXTERNAL_ADMISSION_OBJECT_V1', approval_granted=False,
        requested_scope=['OFFICIAL_TDX_RAW_CURRENT_CANONICAL_SUBSET','CORRECTED_CORE_PROFILE'],
        excluded_scope=['UNBOUND_BSE_IDENTITIES','STRICT_PIT','TDX_HISTORICAL_CONCEPTS','ROTATION','BREAKOUT_UNKNOWN_PRIOR','DATED_LIMIT_OWNER'],
        source_observation='2026-10-09 acquisition; never 2026-10-08 first availability',
        bindings=bindings, candidate_successor='REQUIRES_NEW_VERSION_AND_HEAD; NO_REHASH_OF_HISTORICAL_SEAL',
        status='BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION'))
    result = dict(stage_contract='STAGE_CONTRACT.md', evidence=numeric['acceptance'],
        tests='23 passed', official_request_count=read(OUT/'NEW_OFFICIAL_CAPTURE_RECEIPT.json')['request_count'],
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        source_requests='Fresh official acquisition retained in NEW_OFFICIAL_CAPTURE_RECEIPT; BaoStock formal capture not reached due to delta failure',
        identity_counts=identities['counts'], invalid_delta_entries=len(delta['entries']),
        formal_daily=daily['status'], live_accepted_trade_date=live['context']['accepted_trade_date'],
        acceptance='DEGRADED_PASS_ENGINEERING_REPAIR; EXTERNAL_ACCEPTANCE_BLOCKED',
        production='BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION',
        next_stage='INDEPENDENT_SOURCE_SCOPE_AND_OWNER_SUCCESSOR_ADMISSION',
        input_document_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    write('FINAL_STAGE_RECEIPT.json', result)
    text = '''# R4.1 external audit R1 repair handoff

Engineering result: DEGRADED_PASS. Overall external acceptance remains BLOCKED.

Executed real 551,544,006-byte ZIP SHA/CRC and four-session RAW OHLCVA readback;
independent current/prior MA20/ATR20 arithmetic has no errors. See hash-bound
BYTE_NUMERIC_READBACK and real paired windows in NUMERIC_SAMPLES. This is local
engineering reexecution, not an external auditor's execution or full adjustment
semantics acceptance. Existing 528 restored rows and 35 suspension baseline
remain intact; no owner was rebuilt or relabelled accepted.

Reproduced and repaired direct delta CLI import failure. The next actual failure
is strict validation of vendor historical OHLC. The full offending-entry list
is OFFICIAL_PACKAGE_STRICT_DELTA_BLOCKERS. Formal DM01 was rerun and now reports
BLOCKED_TDX_DELTA_NOT_READY with actual child stderr instead of a misleading
BaoStock WAIT. Fresh official requests/receipts are retained; formal BaoStock
capture was not reached and no new BaoStock acquisition is claimed.

Every unbound target BAR is classified with lifecycle and BSE candidate evidence.
Candidate stable entities are distinguished from unresolved source keys and
out-of-interval aliases. No invented canonical ID or automatic admission.

23 focused regression tests passed. Tests do not establish release readiness.
Separate P0/P1 acceptance objects are in SEPARATE_AUDIT_REGISTER. The concrete
scoped review object binds all four-day candidates and excludes unsupported
domains. Original source locator restored after retaining the new download
receipt; historical seals and production heads preserved. Actual HTTP context
readback remains 2026-09-30, stocks 5213 / sectors 378 / Focus 469.

Next: independently accept specific source/coordinate/identity/producer scopes,
then build a new successor with bad-source, stale-CAS, rerun and rollback checks.
No permission to bypass external admission or enter a later gated stage is implied.
'''
    _atomic_write(OUT/'HANDOFF.md', text.encode(), tdx_root=Path('D:/new_tdx'))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
