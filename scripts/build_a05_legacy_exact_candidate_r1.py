"""Archaeology, exact extraction and frozen real legacy output reconciliation."""
from pathlib import Path
import ast
from datetime import date
import json
import subprocess
import sys
import os
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import binding,digest,immutable_json
from sector.legacy_valid_member_a05_v1 import exact_value

def main():
    import pyarrow.parquet as pq
    target=date(2026,9,24)
    source=ROOT/'src/sector/phase2.py'
    parsed=ast.parse(source.read_text(encoding='utf8'))
    functions={node.name:node for node in parsed.body if isinstance(node,ast.FunctionDef)}
    assignment=next(n for n in functions['prepare'].body if isinstance(n,ast.Assign) and 'valid_member' in ast.unparse(n.targets[0]))
    extracted=ast.dump(assignment,include_attributes=False)
    archaeology=[]
    for base in ('src','config','scripts','docs','reports/phase2','tests'):
        for path in sorted((ROOT/base).rglob('*')):
            if not path.is_file() or path.suffix not in ('.py','.json','.md','.sql','.csv'): continue
            if 'a05' in path.name.lower() or path.stat().st_size>3000000: continue
            try: text=path.read_text(encoding='utf8')
            except (UnicodeError,OSError): continue
            hits=[dict(line=i,text=line[:300]) for i,line in enumerate(text.splitlines(),1) if any(t in line for t in ('valid_member','missing_state','legacy member filter'))]
            if hits: archaeology.append(dict(source=binding(ROOT,path),hits=hits))
    sources=['data/factors/factors_daily.parquet','data/normalized/adjusted_daily.parquet','data/sectors/sector_membership_daily.parquet','data/sectors/sector_factors_daily.parquet']
    original={p:binding(ROOT,ROOT/p) for p in sources}
    archives={}
    output=ROOT/'data/v4/a05_legacy_exact_r1';output.mkdir(parents=True,exist_ok=True)
    for relative in [sources[2],sources[3],'reports/phase2/PHASE2_FINAL_RECEIPT.json','reports/phase1/PHASE1_FINAL_RECEIPT.json']:
        source_path=ROOT/relative; archived=output/('ORIGINAL_BYTES_'+source_path.name)
        data=source_path.read_bytes()
        if archived.exists():
            if archived.read_bytes()!=data: raise ValueError('A05_ARCHIVE_CONFLICT')
        else:
            fd,name=tempfile.mkstemp(dir=output,prefix='.archive.')
            try:
                with os.fdopen(fd,'wb') as stream: stream.write(data);stream.flush();os.fsync(stream.fileno())
                os.link(name,archived)
            finally: Path(name).unlink(missing_ok=True)
        archives[relative]=binding(ROOT,archived)
    facts=pq.read_table(ROOT/sources[0],columns=['security_id'],filters=[('date','=',target)]).to_pylist()
    state_rows=pq.read_table(ROOT/sources[1],columns=['security_id','missing_state'],filters=[('date','=',target)]).to_pylist()
    states={r['security_id']:r['missing_state'] for r in state_rows}
    observations=[dict(source_security_id=r['security_id'],missing_state=states.get(r['security_id']),trade_date=str(target)) for r in facts]
    members=pq.read_table(ROOT/sources[2],columns=['sector_id','sector_role','security_id'],filters=[('date','=',target)]).to_pylist()
    outputs=pq.read_table(ROOT/sources[3],columns=['sector_id','sector_role','total_member_count','valid_member_count','invalid_member_count','coverage','sector_valid','invalid_reason'],filters=[('date','=',target)]).to_pylist()
    frozen=dict(contract_id='A05_REAL_LEGACY_GOLDEN_INPUT_V1',trade_date=str(target),original_source_bindings=original,observations=observations,membership=members,legacy_outputs=outputs,original_receipt=archives['reports/phase2/PHASE2_FINAL_RECEIPT.json'],original_byte_archives=archives,historical_comparability='CURRENT_TDX_MEMBERSHIP_ONLY_NO_HISTORICAL_PIT')
    input_path=output/('REAL_LEGACY_INPUT_'+digest(frozen)+'.json');immutable_json(input_path,frozen)
    index={r['source_security_id']:r for r in observations}; groups={}
    for row in members:
        if row['security_id'] is not None: groups.setdefault(row['sector_id'],set()).add(row['security_id'])
    comparisons=[]
    for old in outputs:
        ids=groups.get(old['sector_id'],set());n=sum(exact_value(sid,index[sid]['missing_state']) for sid in ids if sid in index)
        # Independent source-rule oracle, without calling phase2.validity.
        reasons=[];total=len(ids);role=old['sector_role']
        if total<(5 if role=='INDUSTRY' else 8): reasons.append('MIN_TOTAL_MEMBERS')
        if n<5: reasons.append('MIN_VALID_MEMBERS')
        if not total or n/total<.70: reasons.append('LOW_COVERAGE')
        if role=='EXCLUDE_FROM_THEME_RANK': reasons.append('EXCLUDED_ROLE')
        actual=dict(total_member_count=total,valid_member_count=n,invalid_member_count=total-n,coverage=n/total if total else 0,sector_valid=not reasons,invalid_reason='|'.join(reasons))
        diffs={k:dict(old=old[k],new=v) for k,v in actual.items() if old[k]!=v}
        comparisons.append(dict(sector_id=old['sector_id'],old=old,recomputed=actual,differences=diffs))
    mismatches=sum(bool(r['differences']) for r in comparisons)
    contract=dict(contract_id='LEGACY_VALID_MEMBER_EXACT_PRODUCER_V1',version='1.0.0',status='FROZEN_CANDIDATE',legacy_equivalent=True,source=binding(ROOT,source),source_symbol='sector.phase2.prepare',exact_ast=extracted,exact_ast_digest=digest(extracted),scalar_expression="fullmatch('(SH|SZ|BJ)\\.\\d{6}') AND missing_state IS NOT NULL AND missing_state NOT IN ('FILE_MISSING','DELISTED_OR_INACTIVE')",parameters=dict(identifier_regex=r'(SH|SZ|BJ)\.\d{6}',excluded_missing_states=['FILE_MISSING','DELISTED_OR_INACTIVE']),units='BOOLEAN',time_role='CURRENT_SNAPSHOT_ONLY',unknown_semantics='Missing normalized state => false in legacy rule; unaccepted observation => CANDIDATE, never admitted by accepted consumer.',suspended=True,new_listing_with_NOT_LISTED_YET=True,consumer_migration='External acceptance of exact dated producer observation required; V4-08 unchanged.',production=False,shadow=False,focus_cutover=False)
    immutable_json(ROOT/'config/a05_legacy_valid_member_exact_v1.json',contract)
    report=dict(contract_id='A05_EXACT_RECOVERY_EVIDENCE_R1',baseline_head='bc3e398efb4f4a05c20973ff3cb335a6b101ac87',status='A05_EXACT_PRODUCER_RECOVERED_CANDIDATE',batch_status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',audit='LEGACY_VALID_MEMBER_EXACT_PRODUCER',source_astro=contract,input_binding=binding(ROOT,input_path),archaeology=archaeology,real_observation_count=len(observations),legacy_sector_count=len(comparisons),real_output_mismatch_count=mismatches,full_output_comparison=comparisons,consumer_graph=[dict(path=r['source']['path'],source_sha256=r['source']['sha256'],classification='LEGACY_VALID_MEMBER_DEPENDENCY' if any('valid_member' in h['text'] for h in r['hits']) else 'STATE_SOURCE_DEPENDENCY') for r in archaeology if r['source']['path'].startswith('src/')],v4_08_accepted_head=binding(ROOT,ROOT/'data/v4/V4_08_ACCEPTED_HEAD.json'),formal_consumer_enabled=False,production=False,shadow=False,focus_cutover=False,remaining_external_gate='Independent external acceptance of extraction and exact real producer observations; legacy B2 remains UNKNOWN in accepted runtime.',engineering_gate='PASS' if mismatches==0 else 'BLOCKED')
    report['supersedes']=binding(ROOT,ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R1.json')
    report['hardening']='Original output/membership bytes and Phase1/Phase2 receipts archived for clean-checkout evidence. Giant normalized source retained as original SHA provenance; frozen observed state rows are explicit capture, not reconstructed history.'
    report['original_byte_archives']=archives
    report['producer_runtime_binding']=binding(ROOT,ROOT/'src/sector/legacy_valid_member_a05_v1.py')
    report['shared_entry']=binding(ROOT,ROOT/'reports/next_round_r1/BATCH_STAGE_ENTRY_R1.json')
    immutable_json(ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json',report)
    print(json.dumps(dict(status=report['status'],sectors=len(comparisons),mismatches=mismatches)))
    return bool(mismatches)
if __name__=='__main__': raise SystemExit(main())
