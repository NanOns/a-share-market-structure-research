"""Resume only the relative-owner source/quality failures; preserve other PASS."""
import json,os
from pathlib import Path
from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
from scripts.v4_closeout_sealed_bff_readback import NoLegacyFacts
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
from workbench_service.core_product_bff_r1 import CoreProductBFFR1

ROOT=Path('G:/codex work/v4-production-20261012');OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')

def main():
    report=OUT/'FIELD_PROJECTION_RELATIVE_CONTINUATION_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_RELATIVE_FIELD_CONTINUATION')
    prior=OUT/'FIELD_PROJECTION_ORACLE_R6_R1/RESULT.json';first=json.loads(prior.read_bytes())
    if first['error_count']!=10448 or any(x['field']!='relative_sector_state' or x['scope'] not in ('OWNER_SOURCE_DIGEST','EXPLICIT_OWNER_QUALITY') for x in first['first_errors']):
        raise ValueError('EXPLICIT_RELATIVE_FAILURE_SCOPE_REQUIRED')
    candidate=json.loads(checked(ROOT,first['candidate']).read_bytes());day=candidate['accepted_trade_date'];source=candidate['owners'][day]['relative_sector']
    expected={r['security_id']:r for r in rows(ROOT,source)}
    os.environ['V4_NATIVE_PG_DSN']=load_credentials(ROOT/'config/native_pg_roles.dpapi')[ROLES[0]]
    bff=CoreProductBFFR1(OperationalSuccessorReaderV1(ROOT,candidate),NoLegacyFacts());errors=[];checks=0
    for row in bff.project('stocks',day):
        cell=row['fields']['relative_sector_state'];original=expected[row['entity_id']]
        for name,actual,value in (('source_digest',cell['source_digest'],source['sha256']),('quality',cell['quality'],original['quality']),('value',cell['value'],original['value'])):
            checks+=1
            if actual!=value:errors.append(dict(entity=row['entity_id'],field=name,actual=actual,expected=value))
    result=dict(contract_id='V4_COMPLETE_FIELD_RELATIVE_SOURCE_CONTINUATION_R1',acceptance='PASS_SCOPED' if not errors else 'FAIL',
        candidate=first['candidate'],T0=day,original_result=ref(OUT,prior),original_failed_checks=10448,
        reused_pass_checks=first['total_checks']-first['error_count'],new_checks=checks,errors=errors,
        correction='Verifier expected embedded Profile proxy state; actual Reader deliberately joins the dated relative_sector Owner. Value/unit/window PASS reused; relative Owner quality/source and full values checked.',
        product_source_changed=False,publication=False)
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],reused=result['reused_pass_checks'],new=checks,errors=len(errors))),flush=True)
    return int(bool(errors))

if __name__=='__main__':raise SystemExit(main())
