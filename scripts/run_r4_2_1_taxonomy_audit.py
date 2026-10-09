"""Read frozen R4.1 and accepted TDX bytes; write isolated R4.2.1 evidence."""
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path
from workbench_analysis.corrected_owner_replay import load, checked, gzrows, gzwrite, ref, OUT
from workbench_analysis.market_source_acquisition import write
from workbench_analysis.market_source_acquisition import official_sessions
from v4.base_seed import _normalize_facts, evaluate_facts, _known, _unknown
from v4.stock_prewatch import load_package, evaluate
from workbench_analysis.sector_taxonomy_v2 import (validate_primary_memberships,
    auxiliary_projection, primary_projection, loo_medians, PRIMARY_FIELDS)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def main(root):
    root = Path(root).resolve(); out = root/'docs/evidence/r4_2_1_20261009'
    old = root/OUT
    frozen_before = {p.relative_to(old).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in old.rglob('*') if p.is_file()}
    policy = ref(root, root/'config/v4_primary_sector_taxonomy_v2.json')
    write(out/'TAXONOMY_STAGE_CONTRACT.json', dict(contract=policy,
          upgrade_document='R4.2.1 §2A', scope='TDX primary / CSRC auxiliary isolation',
          evidence='accepted membership bytes, frozen corrected owner bytes, source AST and real LOO samples',
          next_stage='SCOPED_SUCCESSOR_QA', acceptance='IN_PROGRESS'))
    authority = load(root/'config/v4_sector_operational_authority_v1.json')
    binding = authority['sources']['membership']; members = gzrows(checked(root, binding))
    validate_primary_memberships(members, '2026-09-30')
    assert len(members) == 50162 and len({r['sector_id'] for r in members}) == 378
    sectors = load(old/'SECTOR_REPLAY.json'); profiles = load(old/'PROFILE_STRUCTURE_REPLAY.json')
    owners = []; comparison = []; stock_lineage=[]
    sessions=official_sessions(root); seedparams=load(root/'config/v4_07_parameter_set_v1.json')
    prewatch_package=load_package(root)
    for sector, profile in zip(sectors['owners'], profiles['owners']):
        day = sector['trade_date']; folder = out/'taxonomy'/day
        auxiliary = {'taxonomy': 'BAOSTOCK_CSRC_INDUSTRY', 'default_primary_score': False}
        for name in ('native', 'relative_sector'):
            rows = gzrows(checked(root, sector[name]))
            auxiliary['csrc_'+name] = gzwrite(root, folder/('csrc_'+name+'.jsonl.gz'),
                                            [auxiliary_projection(r) for r in rows])
        auxiliary['CSRC_AUX_RELATIVE_KNOWN'] = sector['relative_sector_known']
        rotations = next(r for r in load(old/'MARKET_ROTATION_REPLAY.json')['owners'] if r['trade_date']==day)
        auxiliary['csrc_rotation'] = gzwrite(root, folder/'csrc_rotation.jsonl.gz',
            [auxiliary_projection(r) for r in gzrows(checked(root, rotations['rotation']))])
        primary = primary_projection(day, members if day=='2026-09-30' else [],
                                     lambda rows: {'accepted_membership': binding,
                                         'accepted_native': authority['native'],
                                         'member_count':len(rows)}, auxiliary=auxiliary)
        owners.append(dict(trade_date=day, primary=primary, auxiliary=auxiliary,
            stock_only_seed=sector['seed'], seed_preserved=True,
            TDX_V4_RELATIVE_SECTOR_KNOWN='NOT_RECOMPUTED_FROM_CSRC',
            accepted_0930_preserved=day=='2026-09-30'))
        owner=profile['owner']; factorrows=gzrows(checked(root,owner['core']))
        profileby={r['security_id']:r for r in gzrows(checked(root,owner['profiles']))}
        previous={r['security_id']:r for r in gzrows(checked(root,owner['prior_core']))}
        histories={r['security_id']:{b['trade_date']:b for b in r['bars']} for r in gzrows(checked(root,owner['history']))}
        savedseed={r['security_id']:r for r in gzrows(checked(root,sector['seed']))}
        savedcalc={r['security_id']:r for r in gzrows(old/'owners'/day/'corrected_d0_prewatch.jsonl.gz')}
        prior_day=sessions[sessions.index(day)-1]; results=[]
        board_counts=dict(Counter(r['board_scope'] for r in factorrows))
        for f in factorrows:
            sid=f['security_id'];p=dict(profileby[sid],historical_as_recorded_claim=False)
            context=dict(trade_date=day,expected_board_counts=board_counts,profile_row_publication_id=p['publication_id'])
            facts=_normalize_facts(p,f,context);pc=previous.get(sid,{}).get('fields',{}).get('ma20',{});pb=histories[sid].get(prior_day)
            facts['ma20_t_minus_1']=_known(pc['value']) if pc.get('quality_state')=='OBSERVED' else _unknown('EXACT_PRIOR_CORE_MA20_UNKNOWN')
            facts['close_t_minus_1']=_known(pb['qfq_ohlc'][3]) if pb and pb['qfq_ohlc'] else _unknown('EXACT_PRIOR_ADJUSTED_CLOSE_UNKNOWN')
            seed=evaluate_facts(facts,seedparams)
            assert seed['base_seed_state']==savedseed[sid]['base_seed_state']
            state=seed['base_seed_state'];damage=f['fields']['core_price_damage']['value']
            pf=dict(base_seed_state=state,mandatory_core_quality_ready='TRUE' if state!='UNKNOWN' and isinstance(damage,bool) else 'UNKNOWN',delta3=f['fields']['rps5_delta3']['value'],priority_lineage_failures=[],**{k:p['states'][k]['value'] for k in ('compression_state','ma_structure_state','core_extension_risk')})
            prewatch=evaluate(pf,prewatch_package)
            assert prewatch==savedcalc[sid]['prewatch']
            results.append(dict(security_id=sid,seed=state,prewatch=prewatch))
        stock_lineage.append(dict(trade_date=day,rows=len(results),seed_exact_match=len(results),prewatch_exact_match=len(results),stock_only_result_digest=digest(results),csrc_membership_reads=0,tdx_membership_reads=0))
        if day=='2026-09-30':
            auxmembers=gzrows(checked(root,sector['membership']))
            factors=gzrows(checked(root,profile['owner']['core']))
            returns={r['security_id']:r['fields']['ret5']['value'] for r in factors}
            common=sorted({r['security_id'] for r in members}&{r['security_id'] for r in auxmembers})
            # Cover distinct CSRC fields first, then fill to 30 real securities.
            chosen=[]; seen=set()
            for row in sorted(auxmembers,key=lambda r:(r['sector_id'],r['security_id'])):
                if row['security_id'] in common and row['sector_id'] not in seen:
                    chosen.append(row['security_id']);seen.add(row['sector_id'])
                if len(chosen)==30:break
            for sid in chosen:
                tdx=loo_medians(members,returns,sid);csrc=loo_medians(auxmembers,returns,sid)
                comparison.append(dict(security_id=sid,trade_date=day,TDX_LOO=tdx,CSRC_AUX_LOO=csrc,
                    same_namespace=False,median_value_differs=any(
                        a['ret5_median']!=b['ret5_median'] for a in tdx.values() for b in csrc.values())))
            def universe(rows):
                groups={}
                for r in rows:groups.setdefault((r['sector_id'],r['sector_type']),[]).append(r['security_id'])
                return [dict(sector_id=k[0],sector_type=k[1],sector_member_count=len(v),member_digest=digest(sorted(v))) for k,v in sorted(groups.items())]
            write(out/'TDX_CSRC_0930_UNIVERSE_COMPARISON.json',dict(TDX=universe(members),CSRC_AUX=universe(auxmembers)))
    caches=[]
    for name in ('tdxhy.cfg','tdxzs.cfg','infoharbor_block.dat','block_gn.dat','block_fg.dat','block_zs.dat'):
        path=Path('D:/new_tdx/T0002/hq_cache')/name
        caches.append(dict(path=str(path),exists=path.exists(),sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,
            effective_date_evidence='NONE: current bytes and mtime do not prove historical availability'))
    # Trace consumers from exact source, rather than infer pollution from file names.
    focus=(root/'src/workbench_analysis/corrected_focus_replay.py').read_text(encoding='utf8')
    tree=ast.parse(focus); sector_reads=sorted({n.slice.value for n in ast.walk(tree) if isinstance(n,ast.Subscript)
        and isinstance(n.value,ast.Name) and n.value.id=='sector' and isinstance(n.slice,ast.Constant)})
    assert sector_reads==['seed']
    matrix={k:'TDX_PRIMARY' for k in PRIMARY_FIELDS}
    matrix.update({k:'TDX_PRIMARY' for k in ('sector_rs1/5/20','Breadth','MA20 width',
        'Base/Seed industry aggregate','B0','Rotation','stock.relative_sector_state',
        'homepage_sector_ranks','Focus.mainline_sector')})
    matrix.update({'CSRC_'+k:'CSRC_AUX_ONLY' for k in PRIMARY_FIELDS})
    matrix.update({k:'UNAFFECTED' for k in ('stock.base_seed_state','PREWATCH','D0','D2','Focus.stock_episode','Forward.stock_outcome')})
    matrix.update({'relative_market_state':'STOCK_ONLY','individual_research_display':'UNKNOWN_UNTIL_PROVEN'})
    write(out/'CSRC_TAXONOMY_POLLUTION_MATRIX.json',dict(contract=policy,fields=matrix,
        focus_sector_subscript_reads=sector_reads,focus_source=ref(root,root/'src/workbench_analysis/corrected_focus_replay.py'),
        seed_source=ref(root,root/'src/workbench_analysis/corrected_sector_replay.py'),
        proof='Seed evaluation precedes dated_industry_memberships; Focus consumes only exact seed binding, not native/LOO/rotation.',
        stock_seed_prewatch_rerun_required=False,mainline_sector='UNKNOWN without accepted TDX predecessor',
        stock_only_numerical_replay=stock_lineage,
        audit_item='P0-TAX independent of delta and scoped release gate'))
    frozen_after={p.relative_to(old).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in old.rglob('*') if p.is_file()}
    assert frozen_before==frozen_after
    write(out/'TDX_V4_SECTOR_TAXONOMY_AND_MEMBERSHIP_RESTORATION.json',dict(contract=policy,
        accepted_0930_membership=binding,accepted_native=authority['native'],TDX_sector_count=378,TDX_member_count=50162,
        immutable_owner_digest=digest(frozen_before),immutable_owner_verified=True,owners=owners,current_cache_inventory=caches,
        missing_dates=['2026-09-28','2026-09-29','2026-10-08'],
        missing_resource='No accepted exact-date TDX membership Owner/temporal evidence binding for these dates; current files cannot fill history.',
        samples=comparison,sample_count=len(comparison),sample_median_differences=sum(r['median_value_differs'] for r in comparison),
        acceptance='ISOLATION_IMPLEMENTED; TDX_DATED_RESTORATION_SCOPED_MISSING_INPUT',production_admission=False,
        next_stage='SCOPED_SUCCESSOR_QA; retain unknown primary fields on missing dates'))
    write(out/'TAXONOMY_STAGE_ACCEPTANCE.json', dict(contract=policy,
        acceptance='PASS_ISOLATION_AND_STOCK_ONLY_REPLAY; SCOPED_TDX_HISTORY_INPUT_MISSING',
        real_loo_samples=len(comparison),stock_only_replay=stock_lineage,
        next_stage='SCOPED_SUCCESSOR_QA',production_admission=False))
    print(json.dumps({'samples':len(comparison),'differences':sum(r['median_value_differs'] for r in comparison),'old_owner_unchanged':True}))


if __name__=='__main__':
    main(Path(__file__).resolve().parents[1])
