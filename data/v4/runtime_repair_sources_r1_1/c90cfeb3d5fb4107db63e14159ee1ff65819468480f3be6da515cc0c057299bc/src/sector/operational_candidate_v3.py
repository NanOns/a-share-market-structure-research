"""Append-only qualification-audited research replay; frozen A05 stays intact."""
import json
from pathlib import Path
from .operational_candidate_v1 import compute
from .valid_member_qualification_v3 import compare, CONTRACT as VALIDITY_CONTRACT
from workbench_analysis.r43_owner_replay import checked, gzrows, ref
from workbench_analysis.v4_14_replay_io import publish, digest

CONTRACT = 'SECTOR_OPERATIONAL_RESEARCH_CANDIDATE_V3'


def build(root, *, candidate_binding, trade_date):
    root = Path(root)
    head = json.loads(checked(root, candidate_binding).read_bytes())
    owner = head['owners'][trade_date]
    life = json.loads(checked(root, owner['lifecycle']).read_bytes())
    snapshot = json.loads(checked(root, head['membership_snapshot']).read_bytes())
    states = gzrows(checked(root, owner['prewatch']))
    state_by_id = {r['security_id']: r for r in states}
    validity = {}
    for row in life['rows']:
        if row['security_id'] in validity:
            raise ValueError('DATED_VALIDITY_SCOPE_REQUIRED')
        normal = state_by_id.get(row['security_id'], {}).get('target_values', {}).get('normal_universe')
        validity[row['security_id']] = dict(compare(row, trade_date=trade_date, normal_universe=normal), source=owner['lifecycle'])
    from .research_rank_source_v2 import build as build_ranks
    try:
        branch_sources = build_ranks(root, head=head, trade_date=trade_date)
        rank_gap = None
    except (ValueError, KeyError, OSError) as error:
        branch_sources, rank_gap = {}, str(error)
    rows = compute(gzrows(checked(root, owner['sector'])), gzrows(checked(root, owner['core'])),
        [r for r in gzrows(checked(root, snapshot['memberships'])) if r['security_id']],
        trade_date=trade_date, root=root, state_rows=states, validity_candidates=validity, branch_sources=branch_sources)
    for row in rows:
        row.update(contract_id=CONTRACT, qualification_interpretation='LEGACY_SOURCE_EVIDENCE_REQUIRED_V3',
            valid_member_caveat='QUALIFICATION_UNKNOWN_IS_NOT_FALSE_OR_FORMAL_ADMISSION')
    sources = {k: owner[k] for k in ('lifecycle', 'core', 'sector', 'prewatch')}
    model = ref(root, root/'src/sector/operational_candidate_v3.py')
    dependencies = [ref(root, root/p) for p in (
        'src/sector/operational_candidate_v1.py', 'src/sector/valid_member_qualification_v3.py',
        'src/sector/legacy_valid_member_a05_v1.py', 'src/sector/legacy_b2_r5.py',
        'config/v4_08_b2_machine_ast_r5.json', 'config/research_attention_v3.yaml',
        'src/sector/research_rank_source_v2.py')]
    from workbench_analysis.producer_dependency_archive_v1 import freeze_dependencies
    archive = freeze_dependencies(root,dependencies+[model])
    document = dict(contract_id=CONTRACT, T0=trade_date, rows=rows, sources=sources,
        membership=head['membership_snapshot'], model=model, dependencies=dependencies,
        qualification_audit=list(validity.values()), validity_contract=VALIDITY_CONTRACT,
        frozen_computation_dependencies=archive,
        formal_consumer_enabled=False, production=False, PIT_ELIGIBLE=False,
        evidence_class='RECONSTRUCTED_RESEARCH_ONLY', historical_authority_changed=False, rank_source_gap=rank_gap)
    slot = digest([candidate_binding, sources, model, dependencies])
    return publish(root, f'data/v4/sector_operational_candidates_v3/{slot}/candidate.json', document)
