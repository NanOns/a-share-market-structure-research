"""Full required-scope, audit-first authority reconciliation. No business writes."""
import ast,gzip,hashlib,json,sys,zipfile,struct
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_bytes,atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.identity_authority_audit_r1 import field_matrix,independently_check_stable_id,FIELDS
from tdx.security_master import read_tnf

def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def verify(ref):
    assert bind(ref['path'])['sha256']==ref['sha256'],ref['path']
    return ROOT/ref['path']
def main():
    contract=read('config/source_authority_governance_r1.json')
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in contract['protected_bindings'])
    head=read('data/v4/V4_01_ACCEPTED_HEAD.json');mapping=read(head['canonical_identity']['path'])
    verify(head['canonical_identity']);universe=verify(head['historical_universe'])
    entry=dict(contract_id='A11_STAGE_ENTRY_R1',authority=bind('docs/evidence/source_authority/V4_A11_V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION_TASK_R1_20261001.md'),
        stage_contract='V4_01_IDENTITY_FIELD_AUTHORITY_MATRIX_R1',dependency=bind('reports/audits/A10_STAGE_CLOSURE_R1.json'),protected_bindings=contract['protected_bindings'],
        acceptance='ENGINEERING_CANDIDATE_ONLY',next_stage='A12 producer authority repair; independent A11 external decision')
    atomic_json(ROOT/'reports/audits/A11_STAGE_ENTRY_R1.json',entry)
    required={};rows=0;board_rows=Counter();dates=set()
    with gzip.open(universe,'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line);rows+=1;key=row['source_security_key'];board=row['board_scope']
            item=required.setdefault(key,dict(board=board,rows=0,first_date=row['trade_date'],last_date=row['trade_date'],ids=set()))
            assert item['board']==board;item['rows']+=1;item['last_date']=max(item['last_date'],row['trade_date']);item['ids'].add(row['security_id'])
            board_rows[board]+=1;dates.add(row['trade_date'])
    print('FULL_SCOPE_INVENTORY_COMPLETE',len(required),rows,len(dates),flush=True)
    accepted_scope=read('reports/v4_01/V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.json')['scope']
    assert len(required)==head['required_scope']['source_keys'] and rows==accepted_scope['accepted_r7_rows_scanned'] and len(dates)==head['required_scope']['sessions']
    index={r['source_security_key']:r for r in mapping['records']};assert set(required)<=set(index)
    tnf=set();tnf_refs=[]
    for name,market in [('shs.tnf','SH'),('szs.tnf','SZ'),('bjs.tnf','BJ')]:
        source=Path(r'D:\new_tdx\T0002\hq_cache')/name
        raw=source.read_bytes();before=hashlib.sha256(raw).hexdigest()
        p=f'data/v4/source_evidence/a11_authority_r1/tnf/{name}';atomic_bytes(ROOT/p,raw)
        names,meta=read_tnf(ROOT/p,market);tnf.update(names)
        assert hashlib.sha256(source.read_bytes()).hexdigest()==before
        tnf_refs.append(dict(binding=bind(p),readonly_source=str(source),observed_at=datetime.now(timezone.utc).isoformat(),decoder=bind('src/tdx/security_master.py'),metadata=meta,scope='MUTABLE_CURRENT_NAMES_AND_CODES_NOT_HISTORICAL_TYPE_OR_ST'))
    official={};catalogue_refs=[]
    for p,board in [('data/v4/source_evidence/v4_08_r3/capture_20260930T063255Z/SSE_stock_list.html','SH_MAIN'),('data/v4/source_evidence/v4_08_r3/capture_20260930T063255Z/SSE_STAR_stock_list.html','STAR')]:
        catalogue_refs.append(bind(p))
        for r in read(p)['result']:
            code=r.get('A_STOCK_CODE');d=r.get('LIST_DATE','')
            if code:official['SH.'+code]=dict(board=board,list_date=f'{d[:4]}-{d[4:6]}-{d[6:8]}' if len(d)==8 else d,source=bind(p))
    p='reports/v4_08/V4_08_R3_TARGET_ACTIVE_EXCHANGE_CATALOGUE.json';catalogue_refs.append(bind(p))
    for r in read(p)['records']:official['SZ.'+r['agdm']]=dict(board='CHINEXT' if r['bk']=='创业板' else 'SZ_MAIN',list_date=r['agssrq'],source=bind(p))
    relation=head['relation_resolution'];alias_keys={relation['old_code'],relation['new_code']}
    relation_ref=head['evidence_bindings']['known_official_event_index'];verify(relation_ref)
    archive=read('reports/v4_01/V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.json')['scope']['tdx_source_archive'];verify(archive)
    inventory=[];stats=defaultdict(lambda:defaultdict(Counter));stable_failures=[];distinct_ids=set();boundary=Counter()
    with zipfile.ZipFile(ROOT/archive['path']) as z:
        for key,item in sorted(required.items()):
            record=index[key];matrix=field_matrix(record,tnf_present=key in tnf,official=official.get(key),official_alias=relation_ref if key in alias_keys else None)
            # Accepted R7 explicitly retained the then-current new-symbol ID;
            # both aliases use that pre-existing ID, not a newly rekeyed predecessor.
            anchor=relation['new_code'] if key in alias_keys else None
            if anchor:matrix['stable_id_inputs'].update(anchor_symbol=anchor,anchor_semantics='R7_PRESERVED_EXISTING_CURRENT_ALIAS_ID',anchor_proof=bind('scripts/v4_01_security_alias_board_repair_r7.py'))
            if not independently_check_stable_id(record,anchor):stable_failures.append(key)
            distinct_ids.add(record['security_id'])
            assert item['ids']=={record['security_id']},key
            market,code=key.lower().split('.');member=f'{market}/lday/{market}{code}.day'
            try:
                with z.open(member) as f:raw=f.read(32)
                first=struct.unpack('<I',raw[:4])[0] if len(raw)==32 else None
            except KeyError:first=None
            day_date=f'{first:08d}' if first else None
            matched=day_date==record['list_date'].replace('-','') if day_date else False
            boundary['FIRST_BAR_MATCHES_ANCHOR' if matched else 'FIRST_BAR_DIFFERS_OR_MISSING']+=1
            matrix['listing_anchor'].update(tdx_first_bar_date=day_date,tdx_boundary_consistent=matched,tdx_first_bar_proves_legal_anchor=False)
            for field in FIELDS:stats[item['board']][field][matrix[field]['classification']]+=1
            stats[item['board']]['listing_anchor_corrob'][matrix['listing_anchor']['independent_corrob']]+=1
            stats[item['board']]['security_type_local_historical']['UNKNOWN']+=1
            inventory.append(dict(source_security_key=key,security_id=record['security_id'],board=item['board'],membership_rows=item['rows'],first_required_date=item['first_date'],last_required_date=item['last_date'],authority=matrix))
    assert not stable_failures,stable_failures
    matrixpath='reports/audits/V4_01_IDENTITY_FIELD_AUTHORITY_MATRIX_R1.json'
    atomic_json(ROOT/matrixpath,dict(contract_id='V4_01_IDENTITY_FIELD_AUTHORITY_MATRIX_R1',status='RESULT_C_WIDESPREAD_FORMAL_AUTHORITY_UNRESOLVED',source_keys=len(required),distinct_stable_entities=len(distinct_ids),membership_rows=rows,sessions=len(dates),board_rows=dict(board_rows),
        stats={b:{f:dict(c) for f,c in fs.items()} for b,fs in stats.items()},tdx_boundary_counts=dict(boundary),records=inventory,tnf=tnf_refs,
        current_official_catalogues=catalogue_refs,accepted_head=bind('data/v4/V4_01_ACCEPTED_HEAD.json'),canonical_map=head['canonical_identity'],universe=head['historical_universe'],archive=archive,
        optional_bse=dict(scope='OUTSIDE_REQUIRED_SCOPE',existing_accepted_limitations=mapping['acceptance_limitations']),
        stable_id_derivation_checks=len(inventory),stable_id_mismatches=[],external_acceptance=None))
    files=[]
    for directory in ['src','scripts']:
        for path in sorted((ROOT/directory).rglob('*.py')):
            if '__pycache__' in path.parts:continue
            try:tree=ast.parse(path.read_text(encoding='utf-8-sig'))
            except (SyntaxError,UnicodeError):continue
            uses=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value in {'security_id','source_security_key','security_type','board','list_date','delist_date','identity_revision_id'}:
                    uses.append(dict(line=node.lineno,field=node.value))
            if uses:files.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=bind(path.relative_to(ROOT).as_posix())['sha256'],accesses=uses))
    stages={stage:dict(identity_consumption='EXPLICIT_SECURITY_ID_AND_EXACT_PUBLICATION_BINDING',input_identity_changed=False,business_output_changed=False,logical_digest_changed=False,rebuild_required=False,
                         accepted_head=bind(f'data/v4/V4_{stage}_ACCEPTED_HEAD'+('_AMENDED_R1' if stage=='08' else '')+'.json')) for stage in ['02','03','04','05','07','08','09']}
    graphpath='reports/audits/A11_DOWNSTREAM_CONSUMER_GRAPH_AND_BUSINESS_DIFF_R1.json'
    atomic_json(ROOT/graphpath,dict(status='PASS_AUDIT_NO_BUSINESS_WRITES',scan_scope=['src/**/*.py','scripts/**/*.py'],method='AST_LITERAL_FIELD_ACCESS_INVENTORY_WITH_EXPLICIT_STAGE_BINDINGS',files=files,stages=stages,
        canonical_old_sha256=head['canonical_identity']['sha256'],canonical_candidate_sha256=bind(head['canonical_identity']['path'])['sha256'],identity_rows_changed=0,security_ids_renumbered=0,
        equivalence_scope='AUDIT_ONLY_NO_PROPOSED_VALUE_CORRECTIONS; DOES_NOT_PROVE_ALL_HISTORICAL_FIELDS_TRUE',external_acceptance=None))
    proposalpath='reports/audits/A11_MASTER_AUTHORITY_AMENDMENT_PROPOSAL_R1.json'
    atomic_json(ROOT/proposalpath,dict(contract_id='A11_MASTER_AUTHORITY_AMENDMENT_PROPOSAL_R1',status='RESULT_C_EXTERNAL_DECISION_REQUIRED',matrix=bind(matrixpath),
        proposed_historical_label='PROVIDER_RECONSTRUCTED_FACT / RECONSTRUCTED_CORRECTED',formal_authority='UNRESOLVED_MASTER_AUTHORITY',
        proposed_capability_downgrade='HISTORICAL_LEGAL_LIFECYCLE_AND_TYPE_NOT_LOCAL_TDX_CONFIRMED',existing_historical_acceptance='PRESERVED_REVALIDATION_REQUIRED',
        stable_security_id_policy='DO_NOT_RENUMBER',go_forward_accepted_head=bind('data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json'),go_forward_scope='TARGET_DAY_OFFICIAL_OBSERVED_PRESERVED_NO_ROLLBACK',
        proposal_does_not_amend_accepted_head=True,external_acceptance=None))
    assert all(bind(r['path'])['sha256']==r['sha256'] for r in contract['protected_bindings'])
    print(json.dumps(dict(status='PASS_A11_FULL_SCOPE_AUDIT_RESULT_C',keys=len(inventory),entities=len(distinct_ids),board_stats={b:dict(s['listing_anchor_corrob']) for b,s in stats.items()})),flush=True)

if __name__=='__main__':main()
