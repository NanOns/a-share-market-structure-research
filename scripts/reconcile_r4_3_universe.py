"""Full security/date reconciliation against native frozen source bytes."""
import csv
import io
import json
import struct
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from workbench_analysis.corrected_owner_replay import checked, gzrows, load, ref
from workbench_analysis.market_source_acquisition import write
from workbench_analysis.tdx_official_daily_source import _atomic_write

OUT = ROOT / 'docs/evidence/r4_3_four_session_closeout_20261009'
PRIOR = ROOT / 'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1'
CALENDAR = {
    '2026-09-28': ('2026-09-24', '2026-09-22'),
    '2026-09-29': ('2026-09-28', '2026-09-23'),
    '2026-09-30': ('2026-09-29', '2026-09-24'),
    '2026-10-08': ('2026-09-30', '2026-09-28'),
}


def main():
    entry = load(OUT / '00_ENTRY_DRIVE_HEAD_AND_PROTECTED_DIGESTS.json')
    delta = load(ROOT / 'docs/evidence/r4_2_1_20261009/TDX_A_STOCK_DELTA_V2_RUNTIME_RECEIPT.json')
    owners = load(PRIOR / 'CORE_REPLAY.json')['owners']
    identities = {r['security_id']: r for r in load(checked(ROOT, owners[0]['sources']['identity']))['rows'] if r.get('security_id')}
    bj = load(ROOT / 'docs/evidence/r4_2_1_20261009/BJ_IDENTITY_SCOPED_ADMISSION_CANDIDATES.json')
    write(OUT / 'W0_UNIVERSE_RECONCILIATION_STAGE_ENTRY.json', dict(
        contract_id='R43_NATIVE_SECURITY_DATE_RECONCILIATION_V1', upgrade=entry['stage_contract'],
        evidence='Typed RAW, official ZIP entries, dated BaoStock roster and canonical identity bytes',
        acceptance='IN_PROGRESS', next_stage='W3_INDEPENDENT_NUMERIC_ORACLE',
        supported_scope='EXPLICIT_ACCEPTED_CANONICAL_SH_SZ_A_STOCK',
        BSE='TRACKED_OUTSIDE_CURRENT_CANONICAL_ACCEPTANCE; NO_ALL_MARKET_PASS'))
    rows, summary, errors = [], [], []
    with zipfile.ZipFile(checked(ROOT, entry['frozen_sources']['current_package'])) as archive:
        names = {p.lower().split('/')[-1]: p for p in archive.namelist() if p.endswith('.day')}
        for owner in owners:
            day = owner['trade_date']
            typed = load(checked(ROOT, delta['targets'][day]['binding']))
            bars = {r['security_id']: r for r in typed['target_bars']}
            core = gzrows(checked(ROOT, owner['core']))
            roster_binding = next(r for r in delta['identity_binding']['dated_rosters'] if r['trade_date'] == day)
            roster = {r['code'].upper(): r for r in load(checked(ROOT, roster_binding))['rows']}
            counts = Counter()
            for c in core:
                sid, key = c['security_id'], c['source_security_key'].upper()
                identity = identities[sid]
                eligible = (not identity.get('list_date') or identity['list_date'] <= day) and (not identity.get('delist_date') or day < identity['delist_date'])
                if not eligible:
                    errors.append(dict(date=day, security_id=sid, reason='OWNER_CONTAINS_INELIGIBLE_IDENTITY'))
                bar = bars.get(sid)
                status = roster.get(key, {}).get('tradeStatus')
                zip_name = names.get(key.lower().replace('.', '') + '.day')
                matching = []
                if zip_name:
                    # Examine native bytes independently of the typed decoder.
                    matching = [x for x in struct.iter_unpack('<IIIIIfII', archive.read(zip_name)) if x[0] == int(day.replace('-', ''))]
                if bar:
                    reason = 'ACTUAL_NATIVE_BAR'
                    if len(matching) != 1:
                        errors.append(dict(date=day, security_id=sid, reason='TYPED_NATIVE_CARDINALITY_MISMATCH'))
                    else:
                        n = matching[0]
                        values = [n[1]/100, n[2]/100, n[3]/100, n[4]/100, n[5], n[6]]
                        actual = [bar[k] for k in ('open', 'high', 'low', 'close', 'amount', 'volume')]
                        if values != actual:
                            errors.append(dict(date=day, security_id=sid, reason='NATIVE_TYPED_VALUE_MISMATCH'))
                else:
                    reason = 'VERIFIED_SUSPENSION_NO_NATIVE_BAR' if status == '0' and not matching else 'MISSING_NATIVE_BAR_UNRESOLVED'
                    if reason != 'VERIFIED_SUSPENSION_NO_NATIVE_BAR':
                        errors.append(dict(date=day, security_id=sid, reason=reason, tradeStatus=status, native_records=len(matching)))
                counts[reason] += 1
                rows.append(dict(trade_date=day, predecessor_T1=CALENDAR[day][0], predecessor_T3=CALENDAR[day][1],
                    security_id=sid, source_security_key=key, identity_scope='ACCEPTED_CANONICAL_SH_SZ_A_STOCK',
                    identity_status=identity.get('identity_status'), list_date=identity.get('list_date'),
                    delist_date=identity.get('delist_date'), target_date_eligible=eligible,
                    dated_roster_status=status, raw_bar_present=bool(bar), native_target_records=len(matching),
                    reconciliation_state=reason, typed_raw_sha256=delta['targets'][day]['binding']['sha256'],
                    roster_sha256=roster_binding['sha256'], candidate_security_id='', identity_gate='',
                    AS_RECORDED=False, PIT_ELIGIBLE=False))
            for b in bj['objects']:
                if b['trade_date'] != day:
                    continue
                key = b['source_security_key'].upper()
                name = names.get(key.lower().replace('.', '') + '.day')
                native = [x for x in struct.iter_unpack('<IIIIIfII', archive.read(name)) if x[0] == int(day.replace('-', ''))] if name else []
                rows.append(dict(trade_date=day, predecessor_T1=CALENDAR[day][0], predecessor_T3=CALENDAR[day][1],
                    security_id=b.get('security_id'), source_security_key=key,
                    identity_scope='SEPARATE_BSE_IDENTITY_AUDIT' if b['classification'] != 'INDEX_EXCLUDED' else 'NON_EQUITY_EXCLUDED',
                    identity_status=b['classification'], list_date='', delist_date='', target_date_eligible='NOT_GRANTED',
                    dated_roster_status='NOT_COVERED_BY_BAOSTOCK', raw_bar_present='NOT_ADMITTED', native_target_records=len(native),
                    reconciliation_state=b['classification'], typed_raw_sha256=delta['targets'][day]['binding']['sha256'],
                    roster_sha256=roster_binding['sha256'], candidate_security_id=b.get('candidate_security_id'),
                    identity_gate=b.get('admission_status'), AS_RECORDED=False, PIT_ELIGIBLE=False))
            summary.append(dict(trade_date=day, canonical_rows=len(core), actual_raw=len(bars), states=dict(counts),
                                BSE_and_excluded_counts=bj['counts'][day], T1=CALENDAR[day][0], T3=CALENDAR[day][1]))
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    _atomic_write(OUT / '03_FOUR_SESSION_UNIVERSE_BAR_SUSPENSION_BJ_RECONCILIATION.csv', stream.getvalue().encode('utf8'), tdx_root=Path('D:/new_tdx'))
    write(OUT / '03_RECONCILIATION_ACCEPTANCE.json', dict(contract_id='R43_NATIVE_SECURITY_DATE_RECONCILIATION_V1',
        summary=summary, errors=errors, row_count=len(rows), evidence=ref(ROOT, OUT / '03_FOUR_SESSION_UNIVERSE_BAR_SUSPENSION_BJ_RECONCILIATION.csv'),
        inherited_scope_contracts=[ref(ROOT, ROOT / 'config/v4_02_final_closure_contract_v1.json'),
                                  ref(ROOT, ROOT / 'config/v4_01_historical_code_change_alias_completeness_v1.json')],
        required_boards=['SH_MAIN', 'SZ_MAIN', 'CHINEXT', 'STAR'],
        BSE_scope='INHERITED_EXTERNALLY_ACCEPTED_OPTIONAL_DEGRADED_BSE; NOT_A_NEW_SCOPE_REDUCTION',
        acceptance='PASS_CANONICAL_NATIVE_BAR_AND_SUSPENSION_RECONCILIATION' if not errors else 'FAIL',
        BSE_acceptance='NOT_GRANTED_UNRESOLVED_SOURCE_AND_INDEPENDENT_IDENTITY_ADMISSION',
        comprehensive_audit_item='R43_BSE_IDENTITY_SCOPE_001', full_market_claim=False,
        next_stage='W3_NUMERIC_W4_RETRO_SECTOR'))
    print(json.dumps(dict(summary=summary, errors=len(errors), rows=len(rows))))


if __name__ == '__main__':
    main()
