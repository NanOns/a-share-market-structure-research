"""Check only changed member-reference consumers; prior six-route PASS retained."""
import json,os,hashlib
from pathlib import Path
from collections import defaultdict
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.core_product_bff_r1 import CoreProductBFFR1
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.tdx_member_retro_r43 import normalized_frozen_rows

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    report=OUT/'NATIVE_MEMBER_CONSUMER_READBACK_R6.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_MEMBER_CONSUMER_RESULT')
    preparation=json.loads((OUT/'NATIVE_IDENTITY_PREPARATION_R6.json').read_bytes());candidate=json.loads(checked(ROOT,preparation['candidate']).read_bytes())
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    api=OperationalSuccessorReaderV1(ROOT,candidate);bff=CoreProductBFFR1(api,NoLegacyFacts())
    # Independent immutable source evidence is allowed to the verifier.
    from workbench_analysis.r43_operational_publication import rows
    expected=normalized_frozen_rows(rows(ROOT,api.snapshot['memberships']))
    from workbench_service import r43_operational_bff
    original=r43_operational_bff.rows
    def forbidden(*args):raise RuntimeError('BUSINESS_ARCHIVE_ROWS_FORBIDDEN')
    r43_operational_bff.rows=forbidden
    try:
        actual=bff.membership_rows()
        if actual!=expected:raise ValueError('NORMALIZED_NATIVE_REFERENCE_DIFFERENCE')
        projected={domain:bff.project(domain,candidate['accepted_trade_date']) for domain in ('stocks','sectors')}
    finally:r43_operational_bff.rows=original
    if len(projected['stocks'])!=5224 or len(projected['sectors'])!=400:raise ValueError('DATED_MEMBER_CONSUMER_DENOMINATOR')
    result=dict(contract_id='V4_ACTUAL_NATIVE_MEMBER_CONSUMER_READBACK_R1',acceptance='PASS_CHANGED_CONSUMERS_ONLY',candidate=preparation['candidate'],
        T0=candidate['accepted_trade_date'],context_token=api.token,member_rows=len(actual),normalized_source_difference=0,
        stock_objects=len(projected['stocks']),sector_objects=len(projected['sectors']),archive_business_row_loader_forbidden=True,
        previous_six_routes_repeated=False,publication=False,scope='Current stocks/sectors member projection only; complete PG and final source/field gates remain separate')
    atomic_json(OUT,report,result);print(json.dumps({key:result[key] for key in ('acceptance','member_rows','stock_objects','sector_objects')}),flush=True)

if __name__=='__main__':main()
