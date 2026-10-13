"""Versioned diagnostic correction; frozen A05 and formal D2 stay untouched."""
import json
import re
from pathlib import Path
from .operational_candidate_v1 import compute
from workbench_analysis.r43_owner_replay import checked, gzrows, ref
from workbench_analysis.v4_14_replay_io import publish, digest

CONTRACT='SECTOR_OPERATIONAL_RESEARCH_CANDIDATE_V2'


def build(root, *, candidate_binding, trade_date):
    root=Path(root);head=json.loads(checked(root,candidate_binding).read_bytes());owner=head['owners'][trade_date]
    life=json.loads(checked(root,owner['lifecycle']).read_bytes())
    snapshot=json.loads(checked(root,head['membership_snapshot']).read_bytes())
    states=gzrows(checked(root,owner['prewatch']));core=gzrows(checked(root,owner['core']))
    native=gzrows(checked(root,owner['sector']))
    membership=[r for r in gzrows(checked(root,snapshot['memberships'])) if r['security_id']]
    valid={}
    for row in life['rows']:
        if row['trade_date']!=trade_date or row['security_id'] in valid:raise ValueError('DATED_VALIDITY_SCOPE_REQUIRED')
        if row['status'] not in ('ACTUAL_TRADED','SUSPENDED'):continue
        valid[row['security_id']]=dict(contract_id='LEGACY_VALID_MEMBER_DIAGNOSTIC_CORRECTION_V2',T0=trade_date,
            value=bool(re.fullmatch(r'(SH|SZ|BJ)\.\d{6}',row['source_security_key'])),
            production=False,source=owner['lifecycle'],missing_state_basis=row['status'])
    from .research_rank_source_v2 import build as build_ranks
    try:
        branch_sources=build_ranks(root,head=head,trade_date=trade_date);rank_gap=None
    except (ValueError,KeyError,OSError) as error:
        branch_sources={};rank_gap=str(error)
    corrected=compute(native,core,membership,trade_date=trade_date,root=root,state_rows=states,validity_candidates=valid,
                      branch_sources=branch_sources)
    for row in corrected:
        row.update(contract_id=CONTRACT,qualification_interpretation='CORRECTED_IDENTIFIER_DIAGNOSTIC_V2',
                   valid_member_caveat='VERSIONED_RESEARCH_CORRECTION_PENDING_INDEPENDENT_A05_ACCEPTANCE')
    model=ref(root,root/'src/sector/operational_candidate_v2.py')
    sources={k:owner[k] for k in ('lifecycle','core','sector','prewatch')}
    dependencies=[ref(root,root/p) for p in ('src/sector/operational_candidate_v1.py','src/sector/legacy_b2_r5.py',
        'config/v4_08_b2_machine_ast_r5.json','config/research_attention_v3.yaml','src/sector/research_rank_source_v2.py')]
    document=dict(contract_id=CONTRACT,T0=trade_date,rows=corrected,sources=sources,membership=head['membership_snapshot'],
        model=model,dependencies=dependencies,validity_contract='LEGACY_VALID_MEMBER_DIAGNOSTIC_CORRECTION_V2',
        formal_consumer_enabled=False,production=False,PIT_ELIGIBLE=False,
        evidence_class='RECONSTRUCTED_RESEARCH_ONLY',historical_authority_changed=False,rank_source_gap=rank_gap)
    slot=digest([candidate_binding,sources,model,dependencies])
    return publish(root,f'data/v4/sector_operational_candidates_v2/{slot}/candidate.json',document)
