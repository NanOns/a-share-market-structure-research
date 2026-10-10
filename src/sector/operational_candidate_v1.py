"""Real Native/Core into the unchanged R5 legacy AST, research namespace."""
import json
import re
from pathlib import Path
from .legacy_b2_r5 import build_b2_inputs, evaluate_b2
from .phase2 import VERSION
from .semantic_input_r5_1 import bind_semantic
from workbench_analysis.v4_14_replay_io import digest

CONTRACT = 'SECTOR_D2_OPERATIONAL_CANDIDATE_V1'


def compute(native_rows, core_rows, membership_rows, *, trade_date, root, branch_sources=None, state_rows=None):
    root = Path(root)
    ast = json.loads((root/'config/v4_08_b2_machine_ast_r5.json').read_bytes())
    cfg = json.loads((root/ast['source_parameter_path']).read_bytes())
    # Preserve exact frozen source/parameter identities; no replacement AST.
    import hashlib
    for path, expected in ((ast['source_path'], ast['source_sha256']),
                           (ast['source_parameter_path'], ast['source_parameter_sha256'])):
        if hashlib.sha256((root/path).read_bytes()).hexdigest() != expected:
            raise ValueError('LEGACY_ALGORITHM_BYTES_CHANGED')
    current = {}
    for row in core_rows:
        if row['trade_date'] != trade_date or row['security_id'] in current:
            raise ValueError('CORE_DATE_OR_DUPLICATE')
        current[row['security_id']] = dict(row, fields={k:dict(v,
            quality='ACCEPTED' if v.get('quality_state')=='OBSERVED' else 'UNKNOWN')
            for k,v in row['fields'].items()})
        # Exact frozen identifier predicate can independently be false. This is
        # a research calculation certificate, not accepted A05 provenance.
        from .legacy_valid_member_a05_v1 import exact_value
        identifier_matches = re.fullmatch(r'(SH|SZ|BJ)\\.\\d{6}', row['source_security_key'])
        if identifier_matches is None:
            current[row['security_id']]['legacy_valid_member'] = dict(
                value=False, quality='ACCEPTED', producer_contract=VERSION,
                computation_scope='ENGINEERING_EXACT_FALSE_IDENTIFIER_ONLY')
    # Exact legacy prepare expression is frozen, including its current regex.
    # Inputs needed for missing_state are unavailable here: do not substitute
    # "has ret1" or the latest Native ranking flag for valid-member evidence.
    semantics = bind_semantic(membership_rows, current, trade_date)
    values = build_b2_inputs(native_rows, current, trade_date, cfg, semantics)
    early={}
    if state_rows is not None:
        import pandas as pd
        from workbench_analysis.sector_attention import aggregate_early_width
        states={r['security_id']:r for r in state_rows}
        records=[]
        for native in native_rows:
            for sid in native['member_ids']:
                facts=states.get(sid,{}).get('target_values',{})
                records.append(dict(sector_id=native['sector_id'],security_id=sid,
                    setup=facts.get('setup_v3'),recovery=facts.get('recovery_v3'),extended=facts.get('extended_v3'),
                    close=None,ma20=facts.get('ma20')))
        if records:
            early={r['sector_id']:r for r in aggregate_early_width(pd.DataFrame(records)).to_dict('records')}
    output = []
    for native in native_rows:
        facts = values[native['sector_id']]
        for name in ('early_width','early_count','setup_count','setup_evaluable_count','extended_share'):
            value=early.get(native['sector_id'],{}).get(name)
            facts[name]=dict(value=value,quality='ACCEPTED' if value is not None else 'UNKNOWN')
        risk=early.get(native['sector_id'],{}).get('risk_evaluable_count')
        facts['risk_coverage']=dict(value=risk/len(native['member_ids']) if risk is not None and native['member_ids'] else None,
                                   quality='ACCEPTED' if risk is not None and native['member_ids'] else 'UNKNOWN')
        # Exact rank/window/SETUP/RECOVERY inputs have independent receipts.
        # Missing Amount does not discard non-Amount observations.
        for name, supplied in (branch_sources or {}).get(native['sector_id'], {}).items():
            from workbench_analysis.r43_owner_replay import checked
            document = json.loads(checked(root, supplied).read_bytes())
            if (document.get('T0') != trade_date or document.get('sector_id') != native['sector_id']
                    or document.get('ast_digest') != ast['ast_digest']
                    or document.get('field') != name or name not in ast['fields']
                    or document.get('max_source_date','9999') > trade_date):
                raise ValueError('BRANCH_EXACT_SOURCE_REQUIRED')
            facts[name] = dict(value=document['value'], quality='ACCEPTED', source=supplied)
        result = evaluate_b2(facts, ast, source_sha256=ast['source_sha256'],
            source_parameter_sha256=ast['source_parameter_sha256'], parameter_set_sha256=ast['parameter_set_sha256'])
        output.append(dict(contract_id=CONTRACT, T0=trade_date, sector_id=native['sector_id'],
            member_count=len(native['member_ids']), quoted_count=native['quoted_count'],
            CONFIRMED=result['confirmed_diagnostic'], WARM=result['warm_diagnostic'],
            inputs=facts, native_observations={k:v for k,v in native['fields'].items()
                if k in ('dq5','ret1_median','ret5_median','ret20_median','ma20_width','breadth_delta3')},
            predicates=result['predicates'], ast_digest=ast['ast_digest'],
            valid_member_caveat='EXACT_FROZEN_REGEX_FALSE_IS_NOT_A05_FORMAL_ADMISSION',
            evidence_class='RECONSTRUCTED_RESEARCH_ONLY', production=False,
            formal_consumer_enabled=False, frozen_invalidation='NO_PRIOR_EPISODE',
            episode_invalidation_contract_id=None, followup_complete='UNKNOWN', scenario='UNKNOWN'))
    return output


def produce_rank_window_sources(root, *, technical_binding, memberships_binding,
                                calendar_binding, trade_date, ast_binding):
    """Original cycle rank and three-session stability calculation, no new rank."""
    from workbench_analysis.r43_owner_replay import checked
    from workbench_analysis.v4_14_replay_io import publish
    from workbench_analysis.sector_cycle import build_sector_cycle_daily
    from workbench_service.research_builder import _exact_cycle_delta
    import pandas as pd
    technical=json.loads(checked(root,technical_binding).read_bytes())['rows']
    memberships=json.loads(checked(root,memberships_binding).read_bytes())['rows']
    calendar=json.loads(checked(root,calendar_binding).read_bytes())['session_dates']
    ast=json.loads(checked(root,ast_binding).read_bytes())
    if trade_date not in calendar or calendar.index(trade_date)<3:
        raise ValueError('RANK_REAL_CALENDAR_WINDOW_REQUIRED')
    prior=calendar[calendar.index(trade_date)-3]
    cfg=json.loads((Path(root)/ast['source_parameter_path']).read_bytes())
    cycle=build_sector_cycle_daily(pd.DataFrame(technical),pd.DataFrame(memberships),cutoff=trade_date)
    cycle['q5']=cycle['sector_rs5_pct']
    delta=_exact_cycle_delta(cycle,trade_date,prior,cfg).set_index('sector_id')
    current=cycle[cycle.trade_date.eq(pd.Timestamp(trade_date).date())]
    slot=digest([technical_binding,memberships_binding,calendar_binding,ast_binding,trade_date])
    result={}
    for row in current.to_dict('records'):
        sid=row['sector_id'];result[sid]={}
        for field,value in (('q20',row['sector_rs20_pct']),('dq5_3',delta.loc[sid,'dq5_3'])):
            value=None if pd.isna(value) else float(value)
            document=dict(T0=trade_date,sector_id=sid,field=field,value=value,ast_digest=ast['ast_digest'],
                max_source_date=trade_date,window_start=prior,window_end=trade_date,production=False,
                sources=[technical_binding,memberships_binding,calendar_binding],
                rank_universe_count=int(len(current[current.sector_type.eq(row['sector_type'])])),
                evidence_class='RECONSTRUCTED_RESEARCH_ONLY')
            result[sid][field]=publish(root,f'data/v4/sector_rank_candidates/{slot}/{digest(sid)}/{field}.json',document)
    return result


def create_episode(root, *, source_capture, sector_id, trade_date, members,
                   invalidation_contract, scenario, scenario_priority_binding, price, sessions, price_binding):
    """Candidate genesis only on a real observed day; no historical backfill."""
    from workbench_analysis.r43_owner_replay import checked
    from workbench_analysis.v4_14_replay_io import publish
    from datetime import datetime, timezone, timedelta
    capture = json.loads(checked(root, source_capture).read_bytes())
    today = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    if (capture['T0'] != trade_date or trade_date != today or trade_date not in sessions
            or capture['evidence_class'] != 'CURRENT_OBSERVATION_CANDIDATE' or capture['gaps']):
        raise ValueError('REAL_EPISODE_GENESIS_SOURCE_REQUIRED')
    if sector_id not in capture['sector_ids'] or not members or not set(members) <= set(capture['security_ids']):
        raise ValueError('EPISODE_SCOPE_REQUIRED')
    contract = json.loads(checked(root, invalidation_contract).read_bytes())
    priority = json.loads(checked(root, scenario_priority_binding).read_bytes())
    observation=json.loads(checked(root,price_binding).read_bytes())
    if (observation.get('T0')!=trade_date or observation.get('sector_id')!=sector_id
            or observation.get('price')!=price or observation.get('source_capture')!=source_capture):
        raise ValueError('GENESIS_PRICE_SOURCE_REQUIRED')
    if scenario not in priority['scenario_priority'] or contract.get('version') is None or not contract.get('conditions'):
        raise ValueError('FROZEN_CONTRACT_AND_SCENARIO_REQUIRED')
    if not isinstance(price, (float,int)) or isinstance(price,bool) or price <= 0:
        raise ValueError('GENESIS_PRICE_REQUIRED')
    identity = digest([trade_date,sector_id,source_capture['sha256']])
    document = dict(contract_id='SECTOR_EPISODE_CANDIDATE_V1', episode_id=identity,
        T0=trade_date, sector_id=sector_id, source_capture=source_capture,
        frozen_members=sorted(set(members)), frozen_price=price, invalidation_contract=invalidation_contract,
        price_source=price_binding,
        frozen_conditions=contract['conditions'], scenario=scenario, scenario_priority=scenario_priority_binding,
        created_at=capture['captured_at'], production=False, formal_consumer_enabled=False)
    return publish(root,f'data/v4/sector_episode_candidates/{identity}/genesis.json',document)


def followup(episode, *, trade_date, sessions, settlement=None, root=None):
    if episode['T0'] not in sessions or trade_date not in sessions or trade_date < episode['T0']:
        raise ValueError('REAL_CALENDAR_REQUIRED')
    age = sessions.index(trade_date)-sessions.index(episode['T0'])
    result = {}
    for horizon in (1,3,5):
        due_index = sessions.index(episode['T0'])+horizon
        due = sessions[due_index] if due_index<len(sessions) else None
        binding = (settlement or {}).get(str(horizon))
        item = None
        if binding is not None and root is not None:
            from workbench_analysis.r43_owner_replay import checked
            item=json.loads(checked(root,binding).read_bytes())
        ready = (item is not None and item.get('trade_date')==due and item.get('source_binding')
                 and item.get('episode_id')==episode['episode_id'])
        if ready:
            checked(root,item['source_binding'])
        result[str(horizon)] = dict(status='PENDING' if age<horizon else 'COMPLETE' if ready else 'UNKNOWN',
                                  due_date=due, value=item if ready else None)
    return result


def evaluate_invalidation(root, episode_binding, facts, *, trade_date, sessions):
    """Evaluate the genesis-frozen AST; never recreate yesterday's contract."""
    from workbench_analysis.r43_owner_replay import checked
    from .machine_ast_r3 import evaluate_ast_explain
    episode = json.loads(checked(root, episode_binding).read_bytes())
    if trade_date not in sessions or trade_date < episode['T0']:
        raise ValueError('INVALIDATION_CALENDAR_REQUIRED')
    contract = json.loads(checked(root, episode['invalidation_contract']).read_bytes())
    if any(v.get('max_source_date','9999') > trade_date for v in facts.values()):
        raise ValueError('FUTURE_INVALIDATION_FACT')
    result = evaluate_ast_explain(contract['rule_id'], contract['rules'], facts, contract.get('parameters',{}))
    return dict(episode_id=episode['episode_id'], trade_date=trade_date,
                value='TRUE' if result.state is True else 'FALSE' if result.state is False else 'UNKNOWN',
                reason=result.reason_code, contract=episode['invalidation_contract'], production=False)
