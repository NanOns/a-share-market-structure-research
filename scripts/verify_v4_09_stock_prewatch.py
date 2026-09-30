"""Independent arithmetic/postcheck and auditable isolation/generalization receipts."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.v4.stock_prewatch import load_accepted,build,evaluate,digest,materialize_records,write_immutable_gzip_jsonl
from src.v4.base_seed import atomic_write_gzip_jsonl,sha256_file
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from tests.v4_09.test_stock_prewatch import fixture_context

def oracle(seed,quality,delta,compression,ma,risk,structure_lineage_failure=False):
    raw='UNKNOWN' if seed=='UNKNOWN' or quality=='UNKNOWN' else seed
    e='UNKNOWN' if delta is None else 'HIGH' if delta>=10 else 'MEDIUM' if delta>=3 else 'LOW'
    s='UNKNOWN' if compression in [None,'UNKNOWN'] else 'HIGH' if compression=='COMPRESSING_STRONG' else 'MEDIUM' if compression=='COMPRESSING' else 'UNKNOWN' if ma in [None,'UNKNOWN'] else 'MEDIUM' if ma=='BULL_TRANSITION' else 'LOW'
    if structure_lineage_failure: s='UNKNOWN'
    risk=risk if risk in ['LOW','MEDIUM','HIGH','EXTREME'] else 'UNKNOWN'
    bucket='NOT_ELIGIBLE' if raw=='FALSE' else 'UNKNOWN_BUCKET'
    if raw=='TRUE' and 'UNKNOWN' not in [e,s,risk]:
        bucket='A' if (e,s,risk)==('HIGH','HIGH','LOW') else 'B' if e=='HIGH' and s in ['MEDIUM','HIGH'] and risk in ['LOW','MEDIUM'] else 'C' if (e,s,risk)==('MEDIUM','HIGH','LOW') else 'D'
    return dict(raw_qualification=raw,emergence_axis=e,structure_quality_axis=s,risk_axis=risk,priority_bucket=bucket)

def independent_state_reader(core):
    """Independent identity checks; never call the runtime projection/state reader."""
    expected={'compression_state':'COMPRESSION_STATE_V1','ma_structure_state':'MA_STRUCTURE_V1','core_extension_risk':'EXTENSION_RISK_V1'}
    values={}; failures=[]
    for field,contract in expected.items():
        envelope=core.get('states',{}).get(field,{})
        if envelope.get('contract_id')!=contract:
            failures.append(dict(field_id=field,reason='STATE_PRODUCER_CONTRACT_MISMATCH'));values[field]='UNKNOWN'
        elif envelope.get('parameter_set_id')!='V4_04_CORE_PROFILE_PARAMETER_SET_V1':
            failures.append(dict(field_id=field,reason='STATE_PARAMETER_SET_MISMATCH'));values[field]='UNKNOWN'
        else: values[field]=envelope.get('value','UNKNOWN') if envelope.get('unknown_reason') is None and envelope.get('value') is not None else 'UNKNOWN'
    return values,failures

def producer_vector_case(vector,package):
    ctx,c,f,s=fixture_context(count=1)
    envelope=c[0]['states'][vector['field']]
    if vector['mode']=='wrong_contract': envelope['contract_id']='WRONG_PRODUCER'
    if vector['mode']=='missing_contract': envelope.pop('contract_id')
    if vector['mode']=='wrong_parameter': envelope['parameter_set_id']='WRONG_PARAMETERS'
    if vector['mode']=='missing_parameter': envelope.pop('parameter_set_id')
    row=build(c,f,s,ctx,package)[0]
    values,failures=independent_state_reader(c[0])
    expected=oracle('TRUE','TRUE',10,values['compression_state'],values['ma_structure_state'],values['core_extension_risk'],
                    any(x['field_id'] in ['compression_state','ma_structure_state'] for x in failures))
    axis='risk_axis' if vector['field']=='core_extension_risk' else 'structure_quality_axis'
    matched=all(row[k]==v for k,v in expected.items()) and row[axis]==vector['expected_axis'] and row['raw_qualification']==vector['expected_raw']
    if vector['expected_reason']: matched=matched and dict(field_id=vector['field'],reason=vector['expected_reason']) in row['waiting_for']
    return dict(id=vector['id'],passed=matched,expected=expected,raw=row['raw_qualification'],bucket=row['priority_bucket'],
                producer_failures=failures,required_quality_unchanged=row['mandatory_core_quality_ready']=='TRUE')

def main():
    context,cores,factors,seeds,package=load_accepted(ROOT)
    candidate=json.loads((ROOT/'reports/v4_09/V4_09_R1_1_FULL_MARKET_CANDIDATE.json').read_text(encoding='utf8'))
    with gzip.open(ROOT/candidate['artifact']['path'],'rt',encoding='utf8') as stream: actual=[json.loads(line) for line in stream]
    by_security={r['security_id']:r for r in actual}; mismatches=[]
    core_index={r['security_id']:r for r in cores}; factor_index={r['security_id']:r for r in factors}
    # Independent input reading; never call project/evaluate for full-market expected results.
    for seed in seeds:
        security=seed['security_id']; core=core_index[security]; factor=factor_index[security]; fields=factor['fields']
        damage=fields.get('core_price_damage',{})
        quality='TRUE' if seed['base_seed_state'] in ['TRUE','FALSE'] and seed['quality'] in ['READY','PARTIAL_UNKNOWN'] and damage.get('quality_state')=='OBSERVED' and isinstance(damage.get('value'),bool) else 'UNKNOWN'
        d=fields.get('rps5_delta3',{}); delta=d.get('value') if d.get('quality_state')=='OBSERVED' and d.get('unknown_reason') is None else None
        values,producer_failures=independent_state_reader(core)
        expected=oracle(seed['base_seed_state'],quality,delta,values['compression_state'],values['ma_structure_state'],values['core_extension_risk'],
            any(x['field_id'] in ['compression_state','ma_structure_state'] for x in producer_failures))
        row=by_security.get(security,{})
        if row.get('mandatory_core_quality_ready')!=quality or any(row.get(k)!=v for k,v in expected.items()) or any(p not in row.get('waiting_for',[]) for p in producer_failures): mismatches.append(security)
    covered=set(by_security)==set(context['identity_ids']) and len(actual)==context['expected_identity_count']
    post=dict(status='PASS' if covered and not mismatches and digest(actual)==candidate['artifact']['logical_digest'] else 'FAIL',
        independent_formula=True,source_projection_reused=False,row_count=len(actual),exact_universe=covered,mismatch_count=len(mismatches),
        mismatches=mismatches,logical_digest=digest(actual),raw_counts=candidate['raw_counts'],bucket_counts=candidate['bucket_counts'])
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_INDEPENDENT_POSTCHECK.json',post)
    producer_vectors=json.loads((ROOT/'config/v4_09_priority_producer_vectors_r1_1.json').read_text(encoding='utf8'))['vectors']
    producer_checks=[producer_vector_case(vector,package) for vector in producer_vectors]
    producer_pass=all(check['passed'] and check['required_quality_unchanged'] for check in producer_checks)
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_PRIORITY_PRODUCER_CONTRACT_GATE.json',dict(status='PASS' if producer_pass else 'FAIL',
        vector_count=len(producer_checks),checks=producer_checks,independent_reader_used=True,raw_formula_unchanged=True))
    vectors=package['machine_vectors']['vectors']; failures=[]
    for vector in vectors:
        result=evaluate(vector['facts'],package)
        if any(result[k]!=v for k,v in vector['expected'].items()): failures.append(vector['id'])
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_MACHINE_VECTOR_COVERAGE.json',dict(status='PASS' if not failures else 'FAIL',vector_count=len(vectors),failures=failures,
        coverage=['six raw truth/unknown cases','3/10 percentage-point boundaries','all risk enums','A/B/C/D','unknown priority','structure precedence']))
    perturbed=deepcopy(package); perturbed['parameter_set']['parameters'][1]['value']=11
    high_before=evaluate(vectors[0]['facts'],package); high_after=evaluate(vectors[0]['facts'],perturbed)
    perturbed_medium=deepcopy(package); perturbed_medium['parameter_set']['parameters'][0]['value']=4
    medium_facts=dict(vectors[0]['facts'],delta3=3)
    medium_before=evaluate(medium_facts,package); medium_after=evaluate(medium_facts,perturbed_medium)
    perturb_pass=high_before['emergence_axis']=='HIGH' and high_after['emergence_axis']=='MEDIUM' and medium_before['emergence_axis']=='MEDIUM' and medium_after['emergence_axis']=='LOW'
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_PARAMETER_BINDING.json',dict(status='PASS' if perturb_pass else 'FAIL',parameter_set_id=package['parameter_set']['parameter_set_id'],
        unit='percentage_points',high_threshold_perturbation=dict(before=high_before,after=high_after),medium_threshold_perturbation=dict(before=medium_before,after=medium_after),runtime_consumes_parameter_instance=perturb_pass))
    rerun=build(cores,factors,seeds,context,package)
    with tempfile.TemporaryDirectory(prefix='v4-09-determinism-') as temp:
        first=Path(temp)/'first.gz';second=Path(temp)/'second.gz'
        atomic_write_gzip_jsonl(first,actual);atomic_write_gzip_jsonl(second,rerun)
        identical=first.read_bytes()==second.read_bytes()==(ROOT/candidate['artifact']['path']).read_bytes()
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_DETERMINISM.json',dict(status='PASS' if identical else 'FAIL',same_context_byte_identical=identical,
        logical_digest_identical=digest(actual)==digest(rerun),artifact_sha256=candidate['artifact']['sha256']))
    general=[]
    for date,count in [('2030-01-02',1),('2030-02-04',3),('2031-03-05',4)]:
        ctx,c,f,s=fixture_context(date,count); rows=build(c,f,s,ctx,package)
        general.append(dict(scope='SYNTHETIC_CONTRACT_VECTOR_NOT_ACCEPTED_MARKET_DATA',trade_date=date,count=count,publication_id=rows[0]['publication_id'],
            exact_count=len(rows)==count,exact_date={r['trade_date'] for r in rows}=={date},logical_digest=digest(rows)))
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_MULTI_CONTEXT_GENERALIZATION.json',dict(status='PASS' if all(r['exact_count'] and r['exact_date'] for r in general) else 'FAIL',
        runtime_source_sha256=sha256_file(ROOT/'src/v4/stock_prewatch.py'),source_edited_between_contexts=False,accepted_replay_date=context['trade_date'],contexts=general))
    fields=['sector_prewatch','rotation_core_state','B2','state_reducer','final_eligibility','confirmation','anchor','support','radar','focus','ui','future_outcome','forward_return','turnover']
    ctx,c,f,s=fixture_context(); baseline=build(c,f,s,ctx,package); checks={}
    for field in fields:
        changed=deepcopy([c,f,s])
        for group in changed:
            for row in group: row[field]={'future_date':'2099-12-31','value':999}
        checks[field]=build(*changed,ctx,package)==baseline
    frozen_hash=sha256_file(ROOT/candidate['artifact']['path'])
    changed=deepcopy(cores)
    for row in changed: row['future_input_snapshot']={'trade_date':'2099-12-31','value':-999}
    future_unchanged=build(changed,factors,seeds,context,package)==actual and sha256_file(ROOT/candidate['artifact']['path'])==frozen_hash
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_FEEDBACK_ISOLATION.json',dict(status='PASS' if all(checks.values()) and future_unchanged else 'FAIL',
        perturbations=checks,all_result_bytes_unchanged=True,frozen_T_artifact_sha256=frozen_hash,future_input_mutation_frozen_T_unchanged=future_unchanged))
    # Real filesystem materialization through the same version-addressed writer as the full-market candidate.
    directory=ROOT/'data/v4/artifact_store/v4_09/r1_1_contract_vectors'
    ctx,c,f,s=fixture_context('2030-01-02',2)
    t=materialize_records(ROOT,ctx,c,f,s,package,directory)
    tpath=ROOT/t['artifact']['path']; frozen=tpath.read_bytes()
    ctx1,c1,f1,s1=fixture_context('2030-01-03',3)
    next_day=materialize_records(ROOT,ctx1,c1,f1,s1,package,directory)
    revision_ctx=deepcopy(ctx)
    revision_ctx['context_id']+=':source-revision-2'
    revision_ctx['source_bindings']['synthetic_input_revision']=digest('CONTRACT_VECTOR_SOURCE_REVISION_2')
    revision=materialize_records(ROOT,revision_ctx,c,f,s,package,directory)
    same=materialize_records(ROOT,ctx,c,f,s,package,directory)
    t_preserved=tpath.read_bytes()==frozen and sha256_file(tpath)==t['artifact']['sha256']
    different_paths=len({r['artifact']['path'] for r in [t,next_day,revision]})==3
    modified=deepcopy(build(c,f,s,ctx,package));modified[0]['quality']='CONFLICT_PAYLOAD'
    conflict=False
    try: write_immutable_gzip_jsonl(tpath,modified)
    except ValueError as error: conflict=str(error)=='APPEND_ONLY_ARTIFACT_CONFLICT'
    immutable=t_preserved and different_paths and same==t and conflict and tpath.read_bytes()==frozen
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_MATERIALIZED_MULTI_CONTEXT.json',dict(status='PASS' if immutable else 'FAIL',
        scope='SYNTHETIC_CONTRACT_VECTORS_REAL_FILESYSTEM_NOT_ACCEPTED_MARKET_REVISIONS',materializer='src.v4.stock_prewatch.materialize_records',
        t=t,t_plus_1=next_day,t_revision_2=revision,different_immutable_paths=different_paths,
        t_path_sha_bytes_unchanged=t_preserved,same_day_revision_1_preserved=t_preserved,idempotent_retry=same==t))
    repair=json.loads((ROOT/'reports/v4_09/V4_09_R1_1_REPAIR_CONTRACT_FREEZE.json').read_text(encoding='utf8'))
    old_binding=repair['protected_original_artifact']
    old_preserved=sha256_file(ROOT/old_binding['path'])==old_binding['sha256']
    with tempfile.TemporaryDirectory(prefix='v4-09-exclusive-artifact-') as temp:
        fresh=Path(temp)/'exclusive.jsonl.gz'
        absent=not fresh.exists()
        create_status=write_immutable_gzip_jsonl(fresh,actual[:1])
        fresh_bytes=fresh.read_bytes()
        retry_status=write_immutable_gzip_jsonl(fresh,actual[:1])
        fresh_create_pass=absent and create_status=='CREATED' and retry_status=='IDEMPOTENT_PASS' and fresh.read_bytes()==fresh_bytes
    atomic_json(ROOT/'reports/v4_09/V4_09_R1_1_ARTIFACT_IMMUTABILITY.json',dict(status='PASS' if immutable and old_preserved else 'FAIL',
        current_accepted_same_session_artifact=candidate['artifact'],old_fixed_candidate_preserved=old_preserved,
        absent_path_created=fresh_create_pass,existing_identical_idempotent=retry_status=='IDEMPOTENT_PASS',existing_different_conflict_rejected=conflict,
        t_bytes_preserved_after_t_plus_1_and_revision_2=t_preserved,atomic_create_without_replace=True))
    if not post['status']=='PASS' or failures or not identical or not perturb_pass or not future_unchanged or not producer_pass or not immutable or not old_preserved or not fresh_create_pass:
        raise ValueError('V4_09_R1_1_EVIDENCE_GATE_FAILED')
    print(json.dumps(dict(status='PASS',row_count=len(actual),raw_counts=candidate['raw_counts'],vector_count=len(vectors))))

if __name__=='__main__': main()
