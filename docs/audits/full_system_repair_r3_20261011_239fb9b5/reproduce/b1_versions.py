"""Complete finite registry/schema index for current local Focus/profile/control/FEP versions."""
from pathlib import Path
import ast,json,hashlib,collections,re,os,gzip
ROOT=Path('G:/codex work/大A交易');OUT=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[p for p in (ROOT/'config').glob('*.json') if re.search(r'field_registry|^fep_|focus|profile|control|v4_10_|v4_11_',p.name) and not re.search(r'authority|binding|cutover|readiness|reconstruction|machine_vectors',p.name)]
fields=[];atoms=[];versions=[]
def walk(value,pointer,source,contract):
    if isinstance(value,dict):
        name=value.get('field_id',value.get('field_name'))
        if name:fields.append(dict(requirement_id=source+'#'+pointer,field=str(name),contract=contract,registry_row=value,source=source,source_pointer=pointer))
        for key,child in value.items():walk(child,pointer+'/'+str(key).replace('~','~0').replace('/','~1'),source,contract)
    elif isinstance(value,list):
        for i,child in enumerate(value):walk(child,pointer+'/'+str(i),source,contract)
    else:atoms.append(dict(atom_id=source+'#'+pointer,contract=contract,value=value,status='REGISTERED_SCHEMA_OR_PARAMETER_ONLY'))
for p in sorted(files):
    data=json.loads(p.read_bytes());source=p.relative_to(ROOT).as_posix();contract=data.get('contract_id',data.get('registry_id',data.get('parameter_set_id',p.stem)))
    versions.append(dict(path=source,sha256=sha(p),contract=contract));walk(data,'',source,contract)
names={r['field'] for r in fields};anchors=collections.defaultdict(list)
for p in (ROOT/'src').rglob('*.py'):
    try:tree=ast.parse(p.read_text(encoding='utf-8-sig'))
    except (SyntaxError,UnicodeError):continue
    scopes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    for n in ast.walk(tree):
        field=n.value if isinstance(n,ast.Constant) and isinstance(n.value,str) else n.arg if isinstance(n,ast.keyword) else None
        if field not in names:continue
        candidates=[fn for fn in scopes if fn.lineno<=n.lineno<=fn.end_lineno]
        fn=min(candidates,key=lambda f:f.end_lineno-f.lineno).name if candidates else '<module>'
        anchors[field].append(dict(path=p.relative_to(ROOT).as_posix(),line=n.lineno,function=fn,role='FIELD_LITERAL_OR_KEYWORD; dynamic producer/consumer still needs flow verification'))
for row in fields:
    row['source_sha256']=next(v['sha256'] for v in versions if v['path']==row['source'])
    row['anchors']=anchors[row['field']]
    row['formula_source_quality_consumer_acceptance']='OPEN_INDIVIDUAL_FLOW_REVIEW; anchors are not proof'
reviews=[
dict(fields=['control_entity_ids','assignment_digest','ITT_RETAINED'],producer='src/workbench_analysis/v4_15_settlement.py:freeze_controls/SettlementRuntime.control_crossing',formula='Freeze at T0, deterministic matched assignment; later crossing retains original controls under ITT',source_quality='Explicit frozen T0/control refs; source changes cannot regenerate old assignments',consumer='SettlementRuntime.readback benchmark_control_bindings and FEP selection',counterexample='tests/test_r20d_settlement.py::test_controls / tests/test_r20d_settlement.py::test_persisted_revision_readback',acceptance='SCOPED_SOURCE_REVIEW; full live frozen cohort missing'),
dict(fields=['effective_event','risks','net_information_count'],producer='src/workbench_service/core_product_bff_r1.py:prioritize_home_changes',formula='Minimum explicit risk priority per entity; risks and unique information count derived from same set',source_quality='Dated forward owner checked SHA; no inferred events',consumer='Home product API and UI',counterexample='A1_REAL_FIVE_DAY_READBACK.json / test_audit_repair_home_r3.py',acceptance='SCOPED_ENGINEERING_PASS_EXTERNAL_PENDING'),
dict(fields=['rps5','rps20','sector_rs5','sector_rs20'],producer='src/workbench_service/core_product_bff_r1.py:project/resolve_dated_object',formula='Value-preserving dated Owner projection; distinct stock/sector rank fields',source_quality='Owner evidence/units retained; unknown and ambiguous identity fail closed',consumer='static/core-product-r1/replay.js four modes',counterexample='A3_HTTP_DOM_READBACK.json',acceptance='SCOPED_ENGINEERING_PASS_EXTERNAL_PENDING'),
dict(fields=['source_fact_available_at','label_training_mature_at','label_revision_available_at'],producer='src/workbench_analysis/fep_e1/labels.py:project_with_owner_time/project',formula='Exact outcome copied; no label price recompute in adapter; absent three-time owner rejected; real adapter remains disabled',source_quality='Row digest and admitted time owner; real historical reconstruction not first available',consumer='FEP E1 datasets/fold cutoff selection',counterexample='Actual formal missing interface produces FEP_E1_REAL_ADAPTER_NOT_ENABLED; historical labels engineering-only',acceptance='SCOPED_SOURCE_GATE_REVIEW; real label population blocked'),
dict(fields=['training_allowed_engineering_only','real_training_allowed','outcome'],producer='src/workbench_analysis/fep_e2/historical_labels.py:label_worker',formula='V4-15 settle owns arithmetic; ABS_RETURN_N:T1 only, eligible=OBSERVED and non-null',source_quality='Historical RecordStore ref/digest, immutable reconstructed available_at; all real_training_allowed=false',consumer='E2 input bind and conditional date-equal weights',counterexample='tests/fep_e2/test_r1r2_event_strata.py / historical_dataset.verify_label',acceptance='SCOPED_SOURCE_REVIEW; no formal OOS claim'),
]
atomfile=OUT/'B1_SCHEMA_ATOMS_R3.jsonl.gz';temp=atomfile.with_suffix('.tmp');temp.write_bytes(gzip.compress(b''.join((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode() for r in atoms),mtime=0));os.replace(temp,atomfile)
result=dict(contract_id='B1_FULL_FINITE_REGISTRY_VERSION_INDEX_R3',input_versions=versions,registry_field_rows=len(fields),distinct_field_names=len(names),scoped_schema_atoms=len(atoms),fields=fields,atoms_binding=dict(path=atomfile.name,sha256=sha(atomfile),bytes=atomfile.stat().st_size),semantic_reviews=reviews,finite_scope_complete=True,excluded_input_classes=['machine_vectors (counterexamples, not normative atom denominator)','authority/binding/cutover/readiness/reconstruction (observational permission receipts, require separate prose/version audit)'],global_legal_requirement_denominator=None,global_denominator_status='OPEN: registry/schema coverage does not enumerate every normative prose/permission/version requirement',acceptance='INDEX_COMPLETE_FOR_DECLARED_FINITE_SCOPE; FULL_SEMANTIC_AUDIT_INCOMPLETE')
p=OUT/'B1_VERSIONED_ATOM_INDEX_R3.json';t=p.with_suffix('.tmp');t.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());os.replace(t,p)
print(json.dumps(dict(versions=len(versions),fields=len(fields),names=len(names),atoms=len(atoms),bytes=p.stat().st_size)))
