"""Bounded primary-source capture driven by an evidence-only approved case plan."""
import json,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from scripts.enter_source_authority_remediation_r2 import bind

def main():
    planpath='docs/evidence/source_authority/A11_OFFICIAL_CASE_CAPTURE_PLAN_R1.json'
    plan=json.loads((ROOT/planpath).read_text(encoding='utf8'))
    assert len(plan['sources'])<=plan['maximum_requests']
    captured=[]
    for source in plan['sources']:
        observed=datetime.now(timezone.utc).isoformat()
        receipt=dict(source,observed_at=observed,request_count=1,lineage=plan['lineage'])
        try:
            req=urllib.request.Request(source['url'],headers={'User-Agent':'Mozilla/5.0 (independent-source-audit)'})
            with urllib.request.urlopen(req,timeout=plan['timeout_seconds']) as response:
                raw=response.read(plan['maximum_response_bytes']+1)
                assert len(raw)<=plan['maximum_response_bytes']
                receipt.update(http_status=response.status,received_at=datetime.now(timezone.utc).isoformat(),content_type=response.headers.get('Content-Type'),final_url=response.url)
            path=f"docs/evidence/source_authority/a11_case/{source['id']}.{source['format']}"
            atomic_bytes(ROOT/path,raw);receipt.update(status='CAPTURED',response=bind(path))
        except Exception as exc:receipt.update(status='QUERY_ATTEMPTED_FAILED',received_at=datetime.now(timezone.utc).isoformat(),error=f'{type(exc).__name__}:{exc}')
        captured.append(receipt)
    atomic_json(ROOT/'reports/audits/A11_OFFICIAL_CASE_CAPTURE_R1.json',dict(contract_id='A11_OFFICIAL_CASE_CAPTURE_R1',plan=bind(planpath),request_count=len(captured),sources=captured,origin='DELAYED_HISTORICAL_RETRIEVAL',first_availability_at_target_proven=False,external_acceptance=None))
    print(json.dumps(captured,ensure_ascii=False))

if __name__=='__main__':main()
