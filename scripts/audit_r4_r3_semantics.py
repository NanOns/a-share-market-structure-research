"""Reproducible conservative R3 semantic inventory, never a self-certified gate."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, io, json, os, re, subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_semantics_20261011'
CONTRACT=ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):
    path=OUT/name; tmp=path.with_suffix(path.suffix+'.tmp')
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    tmp.write_text(text,encoding='utf8');os.replace(tmp,path)
def csv_write(name,rows):
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows);write(name,buf.getvalue())

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lines=CONTRACT.read_text(encoding='utf8').splitlines();section='preamble';atoms=[];seen={}
    # Modal clauses, tables and formula blocks remain separately reviewable.
    # A sentence is NOT asserted to equal one normative requirement atom.
    for number,line in enumerate(lines,1):
        if line.startswith('# 历史附录'):break
        if line.startswith('#'):section=line.strip()
        if not re.search(r'必须|不得|禁止|须|应当|只能|唯一|required|shall|must',line,re.I):continue
        text=re.sub(r'\s+',' ',line.strip())
        if not text:continue
        identity=(section,text)
        if identity in seen:seen[identity]['duplicate_lines'].append(number);continue
        atom=dict(candidate_id='CANDIDATE_'+str(len(atoms)+1).zfill(5),section=section,
            line=number,text=text,duplicate_lines=[],status='OPEN_NORMATIVE_ATOMICITY_REVIEW')
        seen[identity]=atom;atoms.append(atom)
    write('V4_NORMATIVE_ATOM_DENOMINATOR.json',dict(contract_id='R4_R3_NORMATIVE_REVIEW_R1',source=str(CONTRACT.relative_to(ROOT)),source_sha256=sha(CONTRACT),
        approved_normative_requirement_atoms=None,candidate_modal_line_count=len(atoms),
        extraction_rule='Current body until first historical appendix; modal-line candidates; whitespace-normalized section+text dedup only',
        limitations=['Modal clauses may contain multiple atoms','Non-modal formulas, code, tables and implicit constraints need manual semantic review',
            'Candidate count is not a legal requirement denominator; §87A registry entries are not semantic acceptance'],candidates=atoms,status='OPEN_INDEPENDENT_SEMANTIC_REVIEW'))
    registry=[];inside=False
    for number,line in enumerate(lines,1):
        if line.startswith('# 87A.'):inside=True;continue
        if inside and line.startswith('# '):break
        if not inside or not line.startswith('|') or '---' in line or '字段/字段族' in line:continue
        cells=[v.strip() for v in line.strip('|').split('|')]
        if len(cells)!=5:continue
        for field in cells[0].split(';'):
            registry.append(dict(field_expression=field.strip(),contract=cells[2],stage=cells[3],source=cells[1],missing_policy=cells[4],
                source_line=number,source_sha256=sha(CONTRACT),formula_unit_window_threshold='OPEN_PER_FIELD_REVIEW',
                producer_pg_consumer_api_ui='OPEN_REAL_CONSUMER_BINDING',pit_quality='OPEN_SOURCE_TIMESTAMP_REVIEW',
                oracle_negative='OPEN_INDEPENDENT_NUMERIC_ORACLE',status='OPEN',closure='Versioned concrete field + formula + unit + real producer/PG/read/API/UI trace + independent positive/negative oracle'))
    csv_write('V4_FIELD_SEMANTIC_COMPLIANCE.csv',registry)
    old=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json'
    consumers=json.loads(old.read_bytes())['consumers'];assert len(consumers)==56
    rows=[]
    for index,item in enumerate(consumers,1):
        relative=item['path'].replace('\\','/');path=ROOT/relative
        rows.append(dict(index=index,path=relative,source_sha256=sha(path) if path.exists() else '',
            previous_sha256=item['sha256'],previous_transport=item['transport'],
            reachability='OPEN_DYNAMIC_TRACE_REQUIRED',exact_runtime_consumer='UNTESTED',
            independent_output_delta='OPEN_PER_CALLER_ORACLE',pit_quality='RECONSTRUCTED_IS_NOT_HISTORICAL_PIT',
            status='OPEN',closure='Actual supported entry trace; bound original bytes; typed factors; full downstream delta; oracle and missing-exact negative'))
    csv_write('EXACT_FACTOR_56_CONSUMERS.csv',rows)
    files=['src/adjustment/exact_factor_transport_r1.py','src/adjustment/exact_ohlc_consumer_r1.py',
        'src/adjustment/tdx_adjustment_v0_3.py','src/adjustment/tdx_adjustment.py','tests/test_v4_exact_ohlc_consumer_r3.py',
        'tests/test_v4_exact_transport_r4.py','tests/test_audit_repair_adjustment_r3.py','scripts/audit_r4_r3_semantics.py']
    write('EXECUTION_SOURCE_BINDINGS.json',dict(contract_id='R4_R3_SEMANTICS_EXECUTION_R1',run_utc=datetime.now(timezone.utc).isoformat(),
        source_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_revision_state='UNCOMMITTED_BYTES_BOUND',
        sources=[dict(path=name,sha256=sha(ROOT/name)) for name in files],
        raw_evidence=[dict(path=name,sha256=sha(OUT/name)) for name in ['EXACT_CONSUMER_JUNIT.xml','EXACT_CONSUMER_RAW.log']],
        candidate_consumer_count=1,full_56_consumer_acceptance='OPEN',normative_semantics='OPEN',production_loaded=False,
        command='python -m pytest -q tests/test_v4_exact_transport_r4.py tests/test_v4_exact_ohlc_consumer_r3.py tests/test_audit_repair_adjustment_r3.py --basetemp G:/codex_tmp/test_temp/semantics_r3_final --junitxml docs/audits/r4_r3_semantics_20261011/EXACT_CONSUMER_JUNIT.xml'))
    write('DATA_QUALITY_AND_TIME_CONSTRAINTS.json',dict(contract_id='R4_R3_SEMANTIC_TIME_GATES_R1',
        candidate_exact_rows=dict(knowledge_lineage='RECONSTRUCTED',PIT_ELIGIBLE=False,formal_owner_admission='PENDING_PERMISSION'),
        H21='PENDING_20_REAL_QUALIFIED_PIT_SESSIONS',forward='PENDING_MATURITY',
        formal_56_consumer_promotion='OPEN_ENGINEERING_DELTA_AND_IDENTITY_REVIEW',external_acceptance='PENDING_INDEPENDENT_REVIEW'))
    print(json.dumps(dict(candidate_modal_lines=len(atoms),field_expressions=len(registry),preserved_consumers=len(rows),status='SCOPED_EXACT_CONSUMER_PROGRESS_FULL_SEMANTICS_OPEN')))

if __name__=='__main__':main()
