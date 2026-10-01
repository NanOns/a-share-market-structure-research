"""Run unchanged admission/PIT builders and full downstream counterfactuals in memory."""
import copy,gzip,hashlib,importlib.util,json,sys,io,contextlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind
P='reports/audits/A13_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    entry=read(P+'STAGE_ENTRY_R1.json')
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in entry['protected_bindings'])
    case=read('data/v4/source_evidence/a13/COUNTERFACTUAL_CASE_SPEC_R1.json');keys=set(case['known_case_keys'])
    capturepath='reports/v4_08/V4_08_R3_OFFICIAL_LIFECYCLE_SOURCE_CAPTURE.json';capture=read(capturepath)
    removed=[s for s in capture['sources'] if s.get('key') in keys and ('suspension' in s['id'] or 'issuance' in s['id'])]
    assert len(removed)==len(keys)
    logs={};scenarios={};admission={}
    for scenario in ('OLD','WITHOUT_MISNAMED_NOTICES'):
        module=load('admission_'+scenario,'scripts/build_v4_08_r3_admission_evidence.py')
        original_read=module.read
        variant=copy.deepcopy(capture)
        if scenario!='OLD':variant['sources']=[s for s in variant['sources'] if s not in removed]
        store={}
        def collect_json(path,value):store[Path(path).relative_to(ROOT).as_posix()]=copy.deepcopy(value)
        def collect_bytes(path,value):store[Path(path).relative_to(ROOT).as_posix()]=value
        module.atomic_json=collect_json;module.atomic_bytes=collect_bytes
        module.read=lambda path:copy.deepcopy(variant) if path==capturepath else original_read(path)
        # Frozen original scenario cutoff, not corrected candidate availability.
        module.now=lambda:read('reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json')['target_publication_cutoff_candidate']
        output=io.StringIO()
        with contextlib.redirect_stdout(output):module.main()
        logs[scenario]=output.getvalue()
        classified=store['reports/v4_08/V4_08_R3_IDENTITY_LIFECYCLE_ADJUDICATION.json']['classifications']
        for key in keys:assert next(c for c in classified if c['source_security_key']==key)['classification']=='NOT_LISTED_AT_TARGET'
        admission[scenario]=classified
        raw=[json.loads(line) for line in gzip.decompress(store['reports/v4_08/staging/V4_08_R3_EXACT_DAY_RAW_MEMBERSHIP_DIAGNOSTIC.jsonl.gz']).decode('utf8').splitlines()]
        pit=load('pit_'+scenario,'scripts/materialize_v4_08_r4_pit_candidate.py')
        original_identity=pit.accepted_identity_lookup;original_rows=pit.rows_from_gzip
        def identity_lookup(identity_input=None):
            head,revision,records,binding=original_identity(identity_input)
            revision=copy.deepcopy(revision);revision['dispositions']=classified
            return head,revision,records,binding
        pit.accepted_identity_lookup=identity_lookup
        pit.rows_from_gzip=lambda path:copy.deepcopy(raw) if path=='reports/v4_08/staging/V4_08_R3_EXACT_DAY_RAW_MEMBERSHIP_DIAGNOSTIC.jsonl.gz' else original_rows(path)
        pit.write_immutable=lambda path,data:None
        built=pit.build()
        accepted=read('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')
        assert hashlib.sha256(built['facts_bytes']).hexdigest()==accepted['facts']['sha256']
        assert built['snapshot']['snapshot_id']==read(accepted['snapshot']['path'])['snapshot_id']
        scenarios[scenario]=built
    # Equality of complete dated identity and complete PIT facts gates every downstream replay.
    business_keys=('source_security_key','target_trade_date','classification','listing_date','board','security_id')
    projected={s:[{k:c.get(k) for k in business_keys} for c in values] for s,values in admission.items()}
    assert projected['OLD']==projected['WITHOUT_MISNAMED_NOTICES']
    assert scenarios['OLD']['facts_bytes']==scenarios['WITHOUT_MISNAMED_NOTICES']['facts_bytes']
    cascade=load('cascade','scripts/complete_a12_cascade_r2.py')
    ctx,cores,factors=cascade.seed._load_accepted_source_context(ROOT)
    pctx,pcores,pfactors,seeds,package=cascade.prewatch.load_accepted(ROOT)
    seed_outputs=[];prewatch_outputs=[];sector_outputs={};sector_receipts={}
    original_rows=cascade.rows
    for scenario,built in scenarios.items():
        # Membership change is the only counterfactual input; all other accepted sources/parameters exact.
        new_seed=cascade.seed.build_candidate_from_records(copy.deepcopy(cores),copy.deepcopy(factors),copy.deepcopy(ctx),created_at=pctx['knowledge_cutoff'])
        seed_outputs.append(new_seed['rows'])
        new_pre=cascade.prewatch.build(copy.deepcopy(pcores),copy.deepcopy(pfactors),copy.deepcopy(seeds),copy.deepcopy(pctx),package)
        prewatch_outputs.append(new_pre)
        collected={}
        def save(name,values):
            collected[name]=copy.deepcopy(values)
            return dict(path='IN_MEMORY_COUNTERFACTUAL/'+name,sha256=digest(values))
        cascade.save=save
        facts_path=read('data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json')['facts']['path']
        cascade.rows=lambda path:copy.deepcopy(built['facts']) if path==facts_path else original_rows(path)
        sector_receipts[scenario]=cascade.sector_replay(cores,factors,seeds,ctx['source_bindings'])
        sector_outputs[scenario]=collected
    downstream={}
    for kind in sector_outputs['OLD']:
        old=sector_outputs['OLD'][kind];new=sector_outputs['WITHOUT_MISNAMED_NOTICES'][kind]
        result=cascade.diff(old,new,key='sector_id');assert result['security_rows_changed']==0
        assert result['old_business_digest']==result['new_business_digest']
        assert all(x['diff']['security_rows_changed']==0 for v in sector_receipts.values() for x in v['outputs'].values())
        downstream[kind]=result
    downstream['V4_07_BASE_SEED']=cascade.diff(*seed_outputs)
    downstream['V4_09_STOCK_PREWATCH']=cascade.diff(*prewatch_outputs)
    seed_baseline=cascade.diff(seeds,seed_outputs[0])
    prewatch_head=read('data/v4/V4_09_ACCEPTED_HEAD.json')
    prewatch_baseline=cascade.diff(original_rows(prewatch_head['artifact']['path']),prewatch_outputs[0])
    assert seed_baseline['security_rows_changed']==prewatch_baseline['security_rows_changed']==0
    assert all(r['security_rows_changed']==0 and r['old_business_digest']==r['new_business_digest'] for r in downstream.values())
    outputpath='reports/audits/a13_counterfactual_r1/FULL_DOWNSTREAM_REPLAY_OUTPUTS_R1.json.gz'
    payload=json.dumps(dict(sector=sector_outputs,base_seed=seed_outputs,prewatch=prewatch_outputs),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    atomic_bytes(ROOT/outputpath,gzip.compress(payload,mtime=0))
    atomic_json(ROOT/(P+'NOTICE_REMOVAL_ADMISSION_COUNTERFACTUAL_R1.json'),dict(
        status='PASS_NO_BUSINESS_IMPACT_CANDIDATE',external_acceptance='PENDING',
        known_case_keys=sorted(keys),removed_sources=removed,source_capture=bind(capturepath),
        rerun_builders=[bind('scripts/build_v4_08_r3_admission_evidence.py'),bind('scripts/materialize_v4_08_r4_pit_candidate.py'),bind('scripts/complete_a12_cascade_r2.py')],
        scenarios=admission,full_admission_business_digests={s:digest(v) for s,v in projected.items()},
        full_PIT_fact_count=len(scenarios['OLD']['facts']),full_PIT_fact_sha256=hashlib.sha256(scenarios['OLD']['facts_bytes']).hexdigest(),
        full_PIT_equal_to_accepted=True,full_downstream_business_diff=downstream,
        accepted_business_baseline_checks=dict(V4_07=seed_baseline,V4_09=prewatch_baseline),
        replay_outputs=bind(outputpath),V4_08_ACCEPTED_HEAD='KEEP',EVIDENCE_SEMANTICS_AMENDMENT_REQUIRED=True,
        BUSINESS_REBUILD_REQUIRED=False,raw_source_modified=False,network_calls=0,
        replay_scope='ALL_11_ADMISSION_KEYS_ALL_RAW_AND_FORMAL_MEMBERSHIP_ROWS_ALL_SECTOR_ROWS_ALL_BASE_SEED_AND_PREWATCH_ROWS',
        replay_cutoff='ORIGINAL_FROZEN_INPUT_SCENARIO_TIME_ONLY_NOT_CORRECTED_FIRST_AVAILABILITY',
        audit_observed_at=datetime.now(timezone.utc).isoformat(),AS_RECORDED=False,logs=logs))
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in entry['protected_bindings'])
    print(json.dumps(dict(status='PASS_NO_BUSINESS_IMPACT_CANDIDATE',PIT_rows=len(scenarios['OLD']['facts']),downstream={k:v['rows'] for k,v in downstream.items()})))
if __name__=='__main__':main()
