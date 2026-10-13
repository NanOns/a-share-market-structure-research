import csv,json,hashlib,shutil,subprocess,zipfile
from pathlib import Path
root=Path('G:/codex work/v4-full-closeout-20261012');base=root/'docs/audits/v4_full_closeout_20261012/continuation_20261013';desktop=Path(__file__).parent
published_target=Path('G:/codex_tmp/V4_R4_R3_FINAL_DELIVERY/V4_FULL_CLOSEOUT_FINAL_20261013')
target=published_target.with_name(published_target.name+'.assembling_R4')
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(name,data):
 (target/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def csv_write(name,rows):
 with (target/name).open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
regression=load(base/'FINAL_REGRESSION_R4/RESULT.json');cutover=load(desktop/'FINAL_ACCEPTANCE_R4.json')
assert regression['acceptance']=='PASS_COMPLETE_FROZEN_LEGAL_REGRESSION' and regression['denominator']==7288
assert cutover['acceptance']=='V4_PRODUCTION_CUTOVER_PASS' and cutover['port']==28765 and cutover['restart_consistent'] and cutover['auto_daily_enabled']
assert not target.exists() and not published_target.exists(),'PRESERVE_PRIOR_DELIVERY';target.mkdir(parents=True)
git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
shutil.copy2(base/'FINAL_REGRESSION_R4/02_LEGAL_FULL_TESTS.xml',target/'02_LEGAL_FULL_TESTS.xml')
write('02_FULL_REGRESSION_RESULT.json',regression)
shutil.copy2(base/'FINAL_REGRESSION_R4/FREEZE.json',target/'02_SOURCE_FREEZE.json')
with (base/'AUDIT_MATRIX_R3/MATRIX.csv').open(encoding='utf-8-sig') as f:audits=list(csv.DictReader(f))
full_pending={'FA-006','AR2-E01','AR3-E02','AR3-E03','S2-DENOMINATOR','FINAL-CLEAN','LEGAL_FULL_REGRESSION'}
desktop_pending={'FA-007','SIX_UI_WINDOWS','PRODUCTION_ROLE_AND_CUTOVER'}
for row in audits:
 if row['id'] in full_pending|desktop_pending:
  evidence=base/'FINAL_REGRESSION_R4/RESULT.json' if row['id'] in full_pending else desktop/'FINAL_ACCEPTANCE_R4.json'
  row.update(status='CURRENT_PRODUCTION_GATE_PASS',production_blocker='False',evidence=str(evidence),evidence_sha256=ref(evidence)['sha256'],scope='Complete frozen original-node regression reconciled; current operational scope only' if row['id'] in full_pending else 'Actual frozen Windows package, original 28765, six-entry business readback and real restart verified')
 else:
  if row['evidence']:row['evidence']=str(base/row['evidence'])
specific={
 'FA-005':(base/'FINAL_REGRESSION_R4/RESULT.json','Original E2/E3 validators use the G-local engineering storage contract; full frozen tests pass without granting FEP source/model authority'),
 'FA-013':(desktop/'IAB_STAGING_R4/RESULT.json','Old code 300114 resolves to the stable 302132 identity in real search/detail and historical comparison'),
 'FA-014':(desktop/'IAB_STAGING_R4/RESULT.json','Stock RPS5/RPS20 values and units are visibly rendered in current and historical comparison; sector_rs remains a separate field'),
 'FA-015':(base/'CORE_AVAILABILITY_ORACLE_R1/CORE47_COVERAGE.json','Current CLV numeric contract/field metadata independently checked; historical prose and original numerical receipts remain immutable'),
 'FA-018':(desktop/'FINAL_ACCEPTANCE_R4.json','Actual installed DailyJobs/settings/worker use native PostgreSQL and remain enabled after restart'),
 'FA-019':(base/'PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json','Current chart/period/native derived read consumers and corrected field values are read from accepted PostgreSQL content'),
 'FA-020':(base/'FINAL_REGRESSION_R4/RESULT.json','Scanner indexes newline offsets once per file and preserves exact line semantics in frozen tests; no performance stress or capacity PASS asserted')}
for row in audits:
 if row['id'] in specific:
  evidence,scope=specific[row['id']];row.update(evidence=str(evidence),evidence_sha256=ref(evidence)['sha256'],scope=scope)
 row['current_production_reachable']='CAPABILITY_GATED_UNAVAILABLE' if row['status']=='FUTURE_DATA_WATCH' else 'CURRENT_ENTRY_OR_RELEASE_VALIDATION_PATH'
 row['remaining_unaccepted_scope']='Future first capture/source/model/cohort/PIT/OOS permission and observation gates' if row['status']=='FUTURE_DATA_WATCH' else 'User-excluded performance stress/mobile/formal rollback acceptance' if row['status']=='HISTORICAL_ONLY' else 'None within the stated current operational scope'
 if row['id'] in ('FA-002','FA-009','FEP-87A','FOCUS_FORWARD_SETTLEMENT'):
  row['remaining_unaccepted_scope']='Strict historical PIT and currently unavailable formal producer/cohort/model fields are not granted by current operational numerical acceptance'
 row['independent_acceptance']='SCOPED_ENGINEERING_EVIDENCE; EXTERNAL_ACCEPTANCE_NOT_GRANTED'
assert len(audits)==39 and all(r['production_blocker']=='False' for r in audits)
csv_write('01_CURRENT_ISSUES_MATRIX.csv',audits)
numeric=load(base/'STAGE1_NUMERIC_CLOSEOUT_R1/RESULT.json');pg=load(base/'PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json')
write('03_NUMERICAL_ORACLE_INDEX.json',dict(contract_id='V4_FINAL_CONSERVED_NUMERIC_EVIDENCE_INDEX_R4',reuse_reason='Identical sealed inputs, Owner content and corrected native authorities; no repeated numerical production or giant payload copying',stage1=ref(base/'STAGE1_NUMERIC_CLOSEOUT_R1/RESULT.json'),numeric_receipts=numeric['evidence'],consumer_receipts=pg['receipt_index'],field_receipts=[ref(base/'CORE_AVAILABILITY_ORACLE_R1/CORE47_COVERAGE.json')],source_freeze_commit=regression['source_commit'],current_business_token=cutover['business_token'],current_T0=cutover['T0'],current_snapshot_and_joint=cutover['head_identities'],source_drift=[]))
pg_objects=load(desktop/'PG_OBJECT_PRIMARY_KEY_VERSION_INDEX_R4.json')
write('04_PG_OBJECT_PRIMARY_KEY_VERSION_INDEX.json',pg_objects)
rows=[]
for route in cutover['business_readback']['records']:
 if route['path']=='context':continue
 rows.append(dict(entry=route['path'],pg_objects_primary_keys_versions=json.dumps(pg_objects,ensure_ascii=False),T0=route['T0'],business_token=route['business_token'],status='PASS_CURRENT_OPERATIONAL_SCOPE',total=route.get('total'),formal_database=pg['pg_database'],pg_system_identifier=pg['pg_system_identifier'],runtime_role=cutover['runtime_role'],independent_select_only_role=pg['pg_reader_role'],native_content_authority=json.dumps(cutover['native_content'],ensure_ascii=False),owner_domain_bindings=json.dumps(pg['owner_domains'],ensure_ascii=False),numerical_field_join=ref(base/'PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json')['sha256'],unknown_boundary='Explicit unavailable fields and forward/PIT gaps preserved; no DuckDB/SQLite business fallback',response_sha256=route['response_sha256']))
assert len(rows)==6;csv_write('04_PG_CONSUMER_MATRIX.csv',rows)
with (base/'ORIGINAL56_DISPOSITION_R2/MATRIX.csv').open(encoding='utf-8-sig') as f:exact=list(csv.DictReader(f))
field=load(base/'CORE_AVAILABILITY_ORACLE_R1/CORE47_COVERAGE.json');exact_contract=load(base/'ORIGINAL56_DISPOSITION_R2/RESULT.json')['contract_id'];rows=[]
for e in exact:
 rows.append(dict(record_type='ORIGINAL56',identity=e['path'],disposition=e['disposition'],status='CURRENT_GATE_PASS' if e['disposition']=='ACTIVE_REACHABLE' else 'PROVED_SCOPED_DISPOSITION',source_sha256=e['source_sha256'],contract_id=exact_contract,contract_version='',implementation_role=e['role'],numeric_checks='',evidence=str(base/'ORIGINAL56_DISPOSITION_R2/RESULT.json'),consumer_join=str(base/'PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json'),scope=e['reason']))
assert len(rows)==56
for f in field['matrix']:
 rows.append(dict(record_type='CORE_FIELD',identity=f['field'],disposition='ACTIVE_CURRENT_FIELD',status=f['status'],source_sha256='',contract_id=f['contract_id'],contract_version=f['contract_version'],implementation_role='CURRENT_CORE_FIELD',numeric_checks=f['numeric_checks'],evidence=str(base/'CORE_AVAILABILITY_ORACLE_R1/CORE47_COVERAGE.json'),consumer_join=str(base/'PG_CURRENT_CANDIDATE_CONSUMER_R1/RESULT.json'),scope=f['coverage']))
csv_write('05_EXACT56_AND_FIELDS.csv',rows)
write('05_FIELD_AND_PROFILE_CONSUMER_INDEX.json',dict(exact56=ref(base/'ORIGINAL56_DISPOSITION_R2/RESULT.json'),core47=ref(base/'CORE_AVAILABILITY_ORACLE_R1/CORE47_COVERAGE.json'),complete_field_projection=pg['field_projection'],profile_corrections=pg['profile_corrections'],focus_source_and_settlement=pg['focus'],receipt_index=pg['receipt_index'],full_comprehensive_semantic_claim=False))
write('06_AUTO_DAILY_E2E.json',dict(contract_id='V4_FINAL_AUTO_DAILY_OPERATIONAL_DISPOSITION_R4',functional_stages='SOURCE_CAPTURED_RECONSTRUCTED_CANDIDATE_NORMAL_FOUR_GATE_CAS_AND_REAL_PG_HTTP_PASS',actual_scheduled_success_claim=False,first_capture='FORWARD_PENDING_REAL_SESSION_AND_SOURCE_AVAILABILITY',blocking_current_accepted_scope=False,published_evidence=ref(base/'CURRENT_PUBLICATION_JOINT_AUDIT_R1/ACTUAL_JOINT_PUBLICATION_R1.json'),daily_status=cutover['daily_status'],auto_daily_enabled=True,old_daily_state=ref(desktop/'PREP_DAILY_R4.json'),immutable_v1_1_and_current_v2_separate=True,full_frozen_regression=ref(base/'FINAL_REGRESSION_R4/RESULT.json')))
write('07_DESKTOP_CUTOVER.json',cutover)
(target/'08_OPEN_FUTURE_WATCH.md').write_text('Future watches remain explicit and do not block the accepted current operational release.\n\n- Actual next-session first capture at the real scheduler time, with source availability and auditable first-observed timestamps; no historical replay is first capture.\n- Strict PIT / AS_RECORDED, authorized Validation Cohort/model/settlement and H21/OOS maturity remain unavailable until their independent contracts and observations are satisfied.\n- Forward production UI capability gaps remain visible; reconstructed Focus is neither a Validation Cohort nor a holding.\n- Amount A retains its independent source audit: 136 provider-definition differences and 12 missing native entries; no fabricated numerical equality.\n\nThe immutable preparation Joint retains full_product_release=false. This final cutover receipt accepts the current dated operational desktop scope only and grants no external acceptance, probability or trading permission.\n',encoding='utf8')
(target/'02_REGRESSION_RECONCILIATION.md').write_text(f"Frozen source: {regression['source_commit']}.\n\nAll 7,288 original legal nodes were executed in separate current-native and retained-historical profiles, without exclusions or test assertion changes. Counts: {json.dumps(regression['counts'])}. Native profile: 4,753 passed / 40 skipped; full historical counts and every skip reason are included in 02_FULL_REGRESSION_RESULT.json. Original 5,463 and prior 7,209 denominators remain preserved; final collection added 79 nodes. The earlier 173 targeted passes were repair evidence, not a replacement denominator. Historical frozen source/CRLF, original validator aliases and browser event-loop fixture ownership were restored through external fixtures. Source drift is empty.\n\nSkip reasons:\n"+'\n'.join(f'- {n}: {reason}' for reason,n in regression['skip_reasons'].items())+'\n',encoding='utf8')
(target/'00_FINAL_DECISION.md').write_text(f"V4_PRODUCTION_CUTOVER_PASS\n\nOriginal Windows loopback port 28765 is served by PID {cutover['pid']}, installed frozen package {cutover['package_release']}. Actual restart, current Head/token/T0, six native PG business entries, real built-in browser interactions and enabled automatic daily scheduling were verified.\n\nGit evidence HEAD: {git_head}\nFrozen source commit: {regression['source_commit']}\nSource SHA: {cutover['source_sha']}\nPG: {pg['pg_database']} / cluster {pg['pg_system_identifier']} / runtime role {cutover['runtime_role']}\nT0: {cutover['T0']}\nOld token: {cutover['old_business_token']}\nCurrent token: {cutover['business_token']}\n\n39 inherited items: 33 current production gate passes, 3 historical-only exclusions, 3 future data watches, 0 current true blockers. Complete legal regression: {json.dumps(regression['counts'])}. Future first capture/PIT/cohort/OOS and unavailable Forward capabilities remain separate. No successful genuine future scheduled capture is asserted. Original data, historical Heads, old launch information and source receipts remain preserved. No Drive operation, performance stress, mobile check or formal rollback drill was performed.\n",encoding='utf8')
(target/'COMMANDS.md').write_text('Reproducible commands and original receipts are retained at these G-local paths. Child temporary variables were TMP=TEMP=TMPDIR=G:/codex_tmp.\n\n- E:/python/python.exe -B -m scripts.v4_closeout_final_regression_r4\n- G:/codex_tmp/v4_full_closeout_20261012/denominator/reconcile_final_r4.py\n- G:/codex_tmp/v4_full_closeout_20261012/final_desktop_cutover_r3/cutover_r4.ps1\n- G:/codex_tmp/v4_full_closeout_20261012/final_desktop_cutover_r3/read_runtime_r4.py\n- G:/codex_tmp/v4_full_closeout_20261012/final_desktop_cutover_r3/read_daily_r4.py\n- G:/codex_tmp/v4_full_closeout_20261012/final_desktop_cutover_r3/prepare_final_delivery_r4.py\n\nDo not rerun a successful cutover command blindly. The cutover script enforces the original owned PIDs and tokens and full regression gate. All large immutable evidence remains referenced by exact path/SHA; it is not copied into this ZIP.\n',encoding='utf8')
for file in ('PRODUCTION_HOME.png','RESULT.json'):
 source=desktop/'IAB_PRODUCTION_R4'/file
 if source.exists():shutil.copy2(source,target/('07_'+file))
manifest=[dict(relative_path=p.relative_to(target).as_posix(),path=str(published_target/p.relative_to(target)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(target.rglob('*')) if p.is_file()]
write('09_SHA256_MANIFEST.json',dict(contract_id='V4_FINAL_SINGLE_DELIVERY_SHA256_R4',self_excluded=True,files=manifest,git_head=git_head))
assert target.resolve().parent==published_target.resolve().parent==Path('G:/codex_tmp/V4_R4_R3_FINAL_DELIVERY').resolve()
target.rename(published_target);target=published_target
archive=target.with_suffix('.zip');assert not archive.exists(),'PRESERVE_PRIOR_ZIP'
pending_archive=archive.with_suffix('.zip.partial');assert not pending_archive.exists()
with zipfile.ZipFile(pending_archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(target.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(target.parent))
pending_archive.rename(archive)
print(json.dumps(dict(folder=str(target),zip=ref(archive),git_head=git_head,conclusion='V4_PRODUCTION_CUTOVER_PASS'),ensure_ascii=False))
