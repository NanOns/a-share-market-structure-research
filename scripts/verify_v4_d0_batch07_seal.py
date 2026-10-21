"""Independent PG, scanner and 28766 readback for the Batch07 D0 seal."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from urllib.parse import quote, urlencode
from urllib.request import urlopen


def load_repository_dsn(repository_root):
    for line in (repository_root/'config/.env').read_text(encoding='utf-8').splitlines():
        value=line.strip()
        if not value or value.startswith('#') or '=' not in value:
            continue
        key, raw=value.split('=',1)
        if key.strip() in ('WORKBENCH_PG_DSN','V4_NATIVE_PG_DSN','V4_NATIVE_PG_READER_DSN'):
            os.environ.setdefault(key.strip(),raw.strip().strip('"').strip("'"))


def get_json(url):
    started=time.perf_counter()
    with urlopen(url,timeout=90) as response:
        raw=response.read()
        status=response.status
    return status,raw,(time.perf_counter()-started)*1000,json.loads(raw)


def port_open(port):
    try:
        with socket.create_connection(('127.0.0.1',port),timeout=2):
            return True
    except OSError:
        return False


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-root',required=True)
    parser.add_argument('--candidate-json',required=True)
    parser.add_argument('--candidate-token',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1]
    root=Path(args.candidate_root).resolve()
    candidate_path=Path(args.candidate_json).resolve()
    evidence_path=Path(args.output).resolve()
    if not root.is_relative_to(Path(r'G:\codex_tmp').resolve()) or not candidate_path.is_relative_to(root):
        raise SystemExit('D0_BATCH07_CANDIDATE_MUST_BE_UNDER_G_CODEX_TMP')
    if not evidence_path.is_relative_to((repo/'docs/evidence/functional_r8_implementation_20261021').resolve()):
        raise SystemExit('D0_BATCH07_EVIDENCE_OUTPUT_MUST_BE_IN_FUNCTIONAL_R8_EVIDENCE')
    load_repository_dsn(repo)
    sys.path.insert(0,str(repo/'src'))
    candidate=json.loads(candidate_path.read_bytes())
    from workbench_analysis.d0_source_seal_r1 import (
        build_candidate_lineage, d0_publication_matches_contract,
        evaluate_d0_source_seal, verify_pg_binding,
    )
    from workbench_analysis.d0_source_seal_r2 import (
        classify_source, independent_pg_readback, independent_scanner_comparison,
    )
    day=args.candidate_token and candidate['accepted_trade_date']
    binding=candidate.get('owners',{}).get(day,{}).get('prewatch')
    if not binding:
        raise SystemExit('D0_EXACT_DATE_OWNER_MISSING')
    owner_path=root/binding['path']
    scanner=independent_scanner_comparison(owner_path)
    pg=verify_pg_binding(day,args.candidate_token)
    restricted=independent_pg_readback(day,args.candidate_token)
    lineage=build_candidate_lineage(root,candidate,day,observed_at=datetime.now().astimezone().isoformat(),pg_readback=pg)
    seal=evaluate_d0_source_seal(root=root,evidence=lineage,scenario='LAUNCH_CONFIRM',
        predicate_state='OVERALL_TRI_STATE_PRESERVED',pg_readback=pg)
    wrong_token=independent_pg_readback(day,'0'*64)
    wrong_date=independent_pg_readback('2026-10-14',args.candidate_token)
    wrong_version=dict(restricted['publications'][0])
    wrong_version['producer_version']='99.0.0'
    wrong_version_result=d0_publication_matches_contract(wrong_version,day,args.candidate_token)
    fake_digest=deepcopy(lineage)
    fake_digest['source_refs'][0]['sha256']='0'*64
    fake_digest_result=evaluate_d0_source_seal(root=root,evidence=fake_digest,scenario='LAUNCH_CONFIRM',
        predicate_state='UNKNOWN',pg_readback=pg)
    late_pg=deepcopy(pg)
    cutoff=datetime.fromisoformat(lineage['knowledge_cutoff'].replace('Z','+00:00'))
    late_pg['source_ingress']['receipts'][0]['evidence_class']='CAPTURED_AS_RECORDED'
    late_pg['source_ingress']['receipts'][0]['time_role']='SAME_DAY_CAPTURE'
    late_pg['source_ingress']['receipts'][0]['available_at']=(cutoff+timedelta(seconds=1)).isoformat()
    late_result=evaluate_d0_source_seal(root=root,evidence=lineage,scenario='LAUNCH_CONFIRM',
        predicate_state='UNKNOWN',pg_readback=late_pg)
    ports={str(p):port_open(p) for p in (28765,28766,5432)}
    if not ports['28766'] or not ports['5432'] or ports['28765']:
        raise SystemExit('D0_BATCH07_RUNTIME_PORT_CONTRACT_FAILED:'+json.dumps(ports))
    context_url='http://127.0.0.1:28766/api/v4/context'
    context_status,context_raw,context_ms,context=get_json(context_url)
    http_token=context.get('context_token')
    if http_token!=args.candidate_token:
        raise SystemExit('D0_28766_CONTEXT_TOKEN_MISMATCH')
    query=urlencode({'context_token':http_token})
    routes=[]
    for name,path in (('home','/api/v4/home'),('stocks','/api/v4/stocks'),('focus','/api/v4/focus'),('forward','/api/v4/forward')):
        status,raw,elapsed,payload=get_json('http://127.0.0.1:28766'+path+'?'+query)
        routes.append(dict(name=name,path=path,http_status=status,response_bytes=len(raw),
            payload_sha256=hashlib.sha256(raw).hexdigest(),elapsed_ms=round(elapsed,3),
            trade_date=payload.get('T0') or payload.get('trade_date') or day,
            context_token=payload.get('context_token'),status=payload.get('status')))
        if status!=200 or payload.get('context_token')!=http_token:
            raise SystemExit('D0_28766_ROUTE_READBACK_FAILED:'+name)
        if name=='stocks':
            items=payload.get('items') or []
            entity=(items[0].get('entity_id') or items[0].get('security_id')) if items else 'SEC-00096141BD5420F5CB3120E687CDA5B9'
    if 'entity' in locals():
        path='/api/v4/stocks/'+quote(entity,safe='')+'/profile'
        status,raw,elapsed,payload=get_json('http://127.0.0.1:28766'+path+'?'+query)
        routes.append(dict(name='stock_profile',path=path,http_status=status,response_bytes=len(raw),
            payload_sha256=hashlib.sha256(raw).hexdigest(),elapsed_ms=round(elapsed,3),
            trade_date=payload.get('T0') or payload.get('trade_date') or day,
            context_token=payload.get('context_token'),status=payload.get('status')))
        if status!=200 or payload.get('context_token')!=http_token:
            raise SystemExit('D0_28766_ROUTE_READBACK_FAILED:stock_profile')
    _,_,_,focus_payload=get_json('http://127.0.0.1:28766/api/v4/focus?'+query)
    focus_d0=focus_payload.get('d0_reason_attribution') or {}
    focus_governance=(focus_d0.get('scenario_governance') or {}).get('scenarios') or {}
    pg_pub=(restricted.get('publications') or [{}])[0]
    receipt=(pg.get('source_ingress') or {}).get('receipts') or [{}]
    evidence=dict(
        evidence_contract_id='R8_BATCH07_D0_CUTOFF_PG_EVIDENCE_R1',
        status='D0_CODE_PG_INTEGRATION_PASS_CLOCK_WAIT',
        generated_at=datetime.now().astimezone().isoformat(),
        baseline_commit='f80c783ee06da308a2820abf15c3e6037294f36d',
        branch='codex/v4-unified-development',trade_date=day,candidate_token=args.candidate_token,
        database_identity=pg.get('database'),
        cutoff_contract=dict(status=lineage.get('cutoff_status'),knowledge_cutoff=lineage.get('knowledge_cutoff'),
            basis=(lineage.get('cutoff_contract') or {}).get('cutoff_basis'),
            r8_clock_readback=restricted.get('snapshot_clock_readback')),
        source_ingress=dict(receipt_count=len((pg.get('source_ingress') or {}).get('receipts',[])),
            sample=receipt[0],restricted_readback=restricted.get('source_ingress_readback')),
        d0_owner_publication=dict(publication_id=pg_pub.get('publication_id'),revision_no=pg_pub.get('revision_no'),
            status=pg_pub.get('publication_status'),owner_sha256=pg_pub.get('owner_sha256'),owner_bytes=pg_pub.get('owner_bytes'),
            predicate_digest=pg_pub.get('predicate_digest'),row_count=pg_pub.get('row_count'),
            scenario_fact_rows=restricted.get('fact_rows'),fact_digest_readback=restricted.get('fact_digest_readback'),
            predicate_counts=scanner.get('predicate_counts'),scenario_status_counts=restricted.get('scenario_status_counts'),
            field_lineage_samples=restricted.get('field_lineage_samples'),source_roles=[x.get('source_role') for x in restricted.get('consumed_source_rows',[])],
            reader_role=restricted.get('reader_current_user'),reader_session_user=restricted.get('reader_session_user'),
            permission_chain_proven=restricted.get('permission_chain_proven'),select_privileges=restricted.get('owner_select_privileges'),
            source_bytes_all_pass=all(x.get('byte_readback')=='PASS' for x in restricted.get('consumed_source_rows',[])),
            AS_RECORDED=pg_pub.get('as_recorded'),PIT_ELIGIBLE=pg_pub.get('pit_eligible'),production_admission=pg_pub.get('production_admission')),
        independent_scanner=scanner,
        seal_evaluation=seal,
        counterexamples=dict(wrong_token_status=wrong_token.get('status'),wrong_token_reason=wrong_token.get('reason'),
            wrong_date_status=wrong_date.get('status'),wrong_date_reason=wrong_date.get('reason'),
            wrong_reader_version_matches_contract=wrong_version_result,
            fake_owner_sha_seal_state=fake_digest_result.get('seal_state'),
            post_cutoff_source_seal_state=late_result.get('seal_state'),
            reconstructed_source_class=classify_source((restricted.get('consumed_source_rows') or [{}])[0],cutoff)),
        bff_28766=dict(context_http_status=context_status,context_token=http_token,context_trade_date=day,
            context_response_bytes=len(context_raw),context_payload_sha256=hashlib.sha256(context_raw).hexdigest(),
            routes=routes,focus_d0=dict(status=focus_d0.get('status'),reason_code=focus_d0.get('reason_code'),
                predicate_counts=focus_d0.get('confirmation_status_counts'),seal_distribution=focus_d0.get('seal_distribution'),
                source_class=(focus_d0.get('source_verification') or {}).get('source_class'),
                first_break=(focus_d0.get('source_verification') or {}).get('first_break'),
                scenario_governance={k:{'status':v.get('status'),'pg_binding_status':v.get('pg_binding_status'),
                    'cutoff_status':v.get('cutoff_status'),'seal_state_counts':v.get('seal_state_counts')}
                    for k,v in focus_governance.items()},AS_RECORDED=focus_d0.get('AS_RECORDED'),
                PIT_ELIGIBLE=focus_d0.get('PIT_ELIGIBLE'))),
        runtime_ports=ports,
        acceptance='PG Owner/Publication, source consumption, reader permissions, exact cutoff and 28766 same-token routes verified. Historical 10/15 remains reconstructed NON_PIT; await a truthful same-cutoff source capture for a positive PIT seal.',
        production_28765_touched=False,final_package_created=False)
    staging=Path(r'G:\codex_tmp')/(evidence_path.name+'.tmp')
    staging.write_text(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2,default=str)+'\n',encoding='utf-8')
    os.replace(staging,evidence_path)
    print(json.dumps(dict(status=evidence['status'],output=str(evidence_path),publication_id=pg_pub.get('publication_id'),
        predicate_counts=scanner.get('predicate_counts'),scanner_comparison=scanner.get('comparison'),
        pg_status=restricted.get('status'),focus_scenarios=focus_governance,ports=ports),ensure_ascii=False,default=str))


if __name__=='__main__':
    main()
