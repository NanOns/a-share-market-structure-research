"""Versioned canonical resume. Explicit isolated databases; frozen outputs only."""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from scripts.build_fep_e2_r1r1_history import ROOT, binding, now
from scripts import run_fep_e5_r1 as old
from scripts.run_fep_e5_r1r1_identity_gate import schema_readback
from scripts.validate_r25_preflight import protected, selection
from workbench_analysis.fep_e1.contracts import atomic_json, digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e5 import canonical_ledger as c
from workbench_service.canonical_expectancy_service import CanonicalExpectancyReadAPI

BASE='9a6ecd205c690b62063cc80810272dda8001cfe9'
REPORT=ROOT/'reports/fep_e5_r1r1b'
DSNS={k:f'host=127.0.0.1 port={port} user=fep_e5_admin dbname=fep_e5b_{k}' for k,port in [('fresh',55490),('upgrade',55491)]}
CODE=['src/workbench_analysis/fep_e5/canonical_ledger.py','src/workbench_service/canonical_expectancy_service.py',
 'src/workbench_db/migrations/v4_postgres/032_fep_reconstruction_authority_shadow_v1.sql','scripts/run_fep_e5_r1r1b.py',
 'tests/fep_e5/test_e5_reconstruction.py']

def load(p):return json.loads(Path(p).read_bytes())
def emit(n,v):atomic_json(REPORT/(n+'.json'),v)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def rows():
    ids=load(old.PROTOCOL)['planned_observation_ids']; allrows={r['observation_id']:r for r in old.e3.rows()}
    return [allrows[i] for i in ids]
def walk_bindings(value):
    if isinstance(value,dict):
        if {'path','bytes','sha256'}<=value.keys():yield value
        else:
            for v in value.values():yield from walk_bindings(v)
    elif isinstance(value,list):
        for v in value:yield from walk_bindings(v)

def prepare():
    assert git('rev-parse','HEAD').decode().strip()==BASE
    semantic=load(REPORT/'R1R1B_CONTRACT_PROTOCOL_FREEZE.json')
    cp=old.contract(); source=load(ROOT/'config/fep_e2_historical_dataset_contract_v1.json')
    refs=list(walk_bindings(source))+cp['upstream_bindings']+[cp['source_model_rows'],cp['feature_manifest'],binding(old.REPORT/'POSTGRES_LEDGER_EXPORT.json')]
    models=old.catalog(); deps=load(ROOT/'reports/fep_e3_r1/PRETEST_DEPENDENCIES.json')
    for m in models:
        if m['stage']=='E2':
            m['canonical_import_diagnostics']={k:dict(status='NOT_APPLICABLE_DESCRIPTIVE_BASELINE',artifact=m['artifact_references']['primary']) for k in ('transform','calibration','OOD')}
        else:
            stage=m['stage'].lower(); folder=ROOT/f'reports/fep_{stage}_r1'
            m['canonical_import_diagnostics']=dict(transform=deps['preprocessing'],OOD=deps['ood'],
                calibration=binding(folder/'CALIBRATION_DIAGNOSTIC_GATE.json'))
        refs+=list(walk_bindings(m))
    refs=list({b['path']:b for b in refs}.values())
    for b in refs:verify_file(ROOT,b)
    manifest=dict(source_dataset_contract=binding(ROOT/'config/fep_e2_historical_dataset_contract_v1.json'),
        historical_population=dict(dataset_seal=binding(ROOT/'reports/fep_e2_r1r1/HISTORICAL_DATASET_SEAL.json'),
            model_rows=cp['source_model_rows'],feature_manifest=cp['feature_manifest'],observations=205),
        frozen_source_bindings=source['source_bindings'],algorithm_contract=source['owner_runtime_bindings'],parameter_contract=source['parameter_bindings'],
        calendar=source['source_bindings']['calendar'],universe=source['source_bindings']['universe'],
        adjustment_basis=source['source_bindings']['adjustment_identity'],membership=source['source_bindings']['universe'],
        state_event_revision=dict(status='EXACT_ACCEPTED_RECONSTRUCTED_E2_ENTRY_ROWS',source=cp['source_model_rows']),
        enrichment_revision=dict(status='NONE_EXACT_CORE_ONLY'),accepted_head={k:source['source_bindings'][k] for k in ('v4_15_head','data_head')})
    entries=c.authority_entries(rows(),manifest)
    emit('HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT',dict(version=c.VERSION,authority_contract=c.AUTH_CONTRACT,source_manifest=manifest,
        model_import_catalog=models,exact_authorities=entries,publication_authority=False,availability='NOT_HISTORICALLY_OBSERVED',
        recorded_at_policy='ACTUAL_CURRENT_DB_CLOCK_AFTER_CONTRACT_REGISTRATION',historical_cutoff_policy='SOURCE_TRADE_DATE_07_UTC',
        evidence_origin='RECONSTRUCTED_CORRECTED',execution_mode='REPLAY',FIRST_OBSERVED=False,REAL_OOS=False,new_training=0))
    emit('IMPLEMENTATION_INPUT_FREEZE',dict(baseline=BASE,semantic_freeze=binding(REPORT/'R1R1B_CONTRACT_PROTOCOL_FREEZE.json'),
        authority_contract=binding(REPORT/'HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json'),code_bindings=[binding(ROOT/p) for p in CODE],
        input_bindings=refs,planned_source_ids=[r['observation_id'] for r in rows()],planned_outputs=615,planned_slots=616,frozen_at=now(),
        ordering=['E2','E3','E4'],output_policy='EXACT_ACCEPTED_R1_OUTPUT_IMPORT_NO_NEW_FIT_OR_SEARCH'))
    print('Frozen exact code, input and authority bindings before installation',flush=True)

def frozen():
    f=load(REPORT/'IMPLEMENTATION_INPUT_FREEZE.json')
    for b in f['code_bindings']+f['input_bindings']+[f['semantic_freeze'],f['authority_contract']]:verify_file(ROOT,b)
    allocation=load(REPORT/'MIGRATION_ALLOCATION_READBACK.json')
    # Historical migration files remain precisely the pre-stage bytes.
    for b in walk_bindings(allocation):verify_file(ROOT,b)
    return f

def pit_seed(pg):
    """Current synthetic PIT regression facts, never a historical source authority."""
    from tests.v4_phase0.test_postgres_schema import add_namespace,add_publication
    c.contract(pg,'UNIT_PIT_FEATURE',{});c.contract(pg,'UNIT_PIT_OBSERVATION',{})
    add_namespace(pg,'UNIT_PIT_NAMESPACE')
    day=pg.execute('select current_date').fetchone()[0]
    add_publication(pg,publication_id='UNIT_PIT_PUBLICATION',namespace_id='UNIT_PIT_NAMESPACE',trade_date=day,lineage_id='UNIT_PIT_LINE')
    pg.execute("insert into fep.scopes values ('UNIT_PIT_SCOPE','STOCK','ENTRY','FIRST_PREWATCH','CORE','UNIT_PIT_NAMESPACE','UNIT_PIT_OBSERVATION',%s)",(digest('UNIT_PIT_SCOPE'),))
    cutoff=pg.execute("select clock_timestamp()+interval '2 seconds'").fetchone()[0]
    pg.execute("insert into fep.observations values ('UNIT_PIT_OBSERVATION','UNIT_PIT_SCOPE','UNIT_SEC',%s,'UNIT_PIT_SIGNAL',null,'UNIT_PIT_OBSERVATION',%s)",(day,cutoff+timedelta(hours=1)))
    manifest={k:'NONE' for k in ('accepted_head','algorithm_contract','parameter_contract','calendar','universe','adjustment_basis','membership','state_event_revision','enrichment_revision')}
    manifest.update(publication='UNIT_PIT_PUBLICATION',feature_contract='UNIT_PIT_FEATURE')
    pg.execute("insert into fep.observation_revisions(observation_id,revision,publication_id,feature_cutoff,dependency_manifest,dependency_digest,enrichment_token,evidence_origin,execution_mode,created_at) values ('UNIT_PIT_OBSERVATION',1,'UNIT_PIT_PUBLICATION',%s,%s,%s,'NONE','PIT_OBSERVED','SHADOW',clock_timestamp())",(cutoff,Jsonb(manifest),digest(manifest)))
    pg.execute("insert into fep.snapshots values ('UNIT_PIT_SNAPSHOT','UNIT_PIT_OBSERVATION',1,'UNIT_PIT_FEATURE',%s,%s,%s)",(digest('PIT_F'),digest('PIT_Q'),cutoff))
    return pg.execute("select row_to_json(r)::jsonb from (select observation_id,revision,publication_id,feature_cutoff,dependency_manifest,dependency_digest,enrichment_token,evidence_origin,execution_mode,supersedes_revision,created_at from fep.observation_revisions where observation_id='UNIT_PIT_OBSERVATION') r").fetchone()[0]

def install():
    frozen();paths=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql'))]
    assert len(paths)==32
    out={}
    for kind,dsn in DSNS.items():
        with psycopg.connect(dsn.replace('dbname=fep_e5b_'+kind,'dbname=postgres'),autocommit=True) as pg:
            pg.execute(sql.SQL('create database {}').format(sql.Identifier('fep_e5b_'+kind)))
        with psycopg.connect(dsn,autocommit=True) as pg:
            before=None
            if kind=='upgrade':
                applied=c.apply(pg,ROOT,paths[:-1])
                with pg.transaction():before=pit_seed(pg)
                pubfn=pg.execute("select pg_get_functiondef('fep.validate_observation_revision()'::regprocedure)").fetchone()[0]
                applied+=c.apply(pg,ROOT,paths[-1:])
                after=pg.execute("select row_to_json(r)::jsonb from (select observation_id,revision,publication_id,feature_cutoff,dependency_manifest,dependency_digest,enrichment_token,evidence_origin,execution_mode,supersedes_revision,created_at from fep.observation_revisions where observation_id='UNIT_PIT_OBSERVATION') r").fetchone()[0]
                assert before==after and pubfn==pg.execute("select pg_get_functiondef('fep.validate_observation_revision()'::regprocedure)").fetchone()[0]
            else:applied=c.apply(pg,ROOT,paths)
            replay=c.apply(pg,ROOT,paths);assert all(r['status']=='ALREADY_APPLIED' for r in replay)
            out[kind]=dict(migrations=applied,replay=replay,table_counts=c.inventory(pg),schema=schema_readback(pg),
                prior_PIT_fact=before,PIT_fact_preserved=kind=='upgrade',fixture='ISOLATED_EXPLICIT_CURRENT_SYNTHETIC_PIT_ONLY')
    assert out['fresh']['schema']['logical_digest']==out['upgrade']['schema']['logical_digest']
    emit('CANONICAL_SCHEMA_REPAIR_READBACK',dict(status='PASS',fixtures=out,original_028_031_unchanged=True))
    print('Fresh and populated-PIT upgrade installed; checksum replay passed',flush=True)

def project():
    frozen();authority=load(REPORT/'HISTORICAL_RECONSTRUCTION_AUTHORITY_CONTRACT.json');data=rows()
    legacy=load(old.REPORT/'POSTGRES_LEDGER_EXPORT.json')
    print('Legacy export keys: '+str(list(legacy)),flush=True)
    # Source rows are accepted engineering outputs, never canonical authority.
    source=legacy.get('tables',legacy)['predictions']
    all_results={};api={};events={}
    for kind,dsn in DSNS.items():
        with psycopg.connect(dsn,autocommit=True) as pg:
            with pg.transaction():mapping,models=c.seed_identity(pg,data,authority['exact_authorities'],authority['model_import_catalog'])
            lookup={r['observation_id']:r for r in mapping};results=[];activity=[];apireads=[]
            # Optional no-model denominator precedes every inference batch.
            t=c.now();obs=mapping[0]['observation_id'];payload=dict(reason='NO_ACTIVE_MODEL',engineering_only=True)
            with pg.transaction():
                pg.execute("insert into fep.prediction_slots values ('FEP_CANONICAL_OPTIONAL_NO_MODEL',%s,%s,%s,1,'OPTIONAL_UNSUPPORTED_FAMILY',%s,%s,'NO_ACTIVE_MODEL')",(obs,c.SCOPE,c.TARGET,t,t))
                pg.execute("insert into fep.slot_receipts values ('FEP_CANONICAL_OPTIONAL_NO_MODEL','OPTIONAL_NO_MODEL_RECEIPT',%s,'FAILED',%s,%s)",(t,Jsonb(payload),digest(payload)))
            for model in models:
                activation=c.cas(pg,model['grant_id'],'ALLOW',kind+'-'+model['stage']+'-allow');activity.append(activation)
                cutoff=c.now();batch=[p for p in source if p['model_id']==model['model_id']];assert len(batch)==205
                with pg.transaction():
                    for p in batch:c.plan(pg,p,lookup[p['observation_id']],model,cutoff,activation)
                for p in batch:results.append(c.accept(pg,p,lookup[p['observation_id']],model,cutoff,activation))
                r=results[-1];service=CanonicalExpectancyReadAPI(pg);token=service.bootstrap(r['slot_id'])['context']
                apireads.append(dict(stage=model['stage'],context=token,default=service.projection(r['slot_id'],token),diagnostic=service.projection(r['slot_id'],token,diagnostic=True)))
                revoke=c.cas(pg,model['grant_id'],'REVOKE',kind+'-'+model['stage']+'-revoke');activity.append(revoke)
                assert service.projection(r['slot_id'],token,diagnostic=True)['axes'] is None
            assert len(results)==615 and len(mapping)==205
            counts=c.inventory(pg);assert counts['predictions']==615 and counts['prediction_slots']==616 and counts['training_runs']==0
            quality={m['stage']:dict(Counter(p['outputs']['projection_state'] for p in results if p['model_id']==m['model_id'])) for m in models}
            assert all(v=={'READY':46,'REJECTED_QUALITY':159} for v in quality.values())
            # Exact output selected-field equality, including all UNKNOWN/OOD boundaries.
            previous={p['prediction_id']:p for p in source}
            exact=all(r['outputs']=={k:previous[r['source_prediction_id']][k] for k in c.OUTPUT_FIELDS if k in previous[r['source_prediction_id']]} for r in results)
            assert exact
            tables={name:pg.execute(sql.SQL('select to_jsonb(t) from fep.{} t order by to_jsonb(t)::text').format(sql.Identifier(name))).fetchall() for name in counts}
            tables={name:[r[0] for r in v] for name,v in tables.items()}
            emit(kind.upper()+'_CANONICAL_LEDGER_EXPORT',dict(canonical_schema='fep',tables=tables,table_counts=counts,exported_at=now()))
            all_results[kind]=dict(mapping=mapping,models=models,predictions=results,counts=counts,quality=quality,exact_outputs=exact)
            api[kind]=apireads;events[kind]=activity
            print(kind+': canonical 205 observations / 615 predictions / 616 slots; exact frozen outputs',flush=True)
    emit('HISTORICAL_RECONSTRUCTION_AUTHORITY_MAPPING',dict(status='PASS',rows=all_results['fresh']['mapping'],observations=205,dropped=0))
    emit('CANONICAL_IDENTITY_MAPPING',dict(status='PASS_RECONSTRUCTION_AUTHORITY',rows=all_results['fresh']['mapping'],publication_mapping=False))
    emit('CANONICAL_PREDICTION_BINDING_READBACK',dict(status='PASS',fixtures=all_results))
    emit('CANONICAL_LEDGER_READBACK',dict(status='PASS',schema='fep',fixtures={k:dict(table_counts=v['counts'],quality=v['quality']) for k,v in all_results.items()},fep_e5_engineering_used_as_authority=False,production=False))
    emit('CANONICAL_VS_E5_R1_OUTPUT_RECONCILIATION',dict(status='PASS',predictions=615,slots=616,observations=205,exact_selected_output_fields=list(c.OUTPUT_FIELDS),exact_output_equality=True,new_fit=0,new_search=0,new_label_resolution=0,numeric_outputs_changed=0,identity_changes='Canonical RA, snapshot, slot/run/model-set identities; original source prediction mapping retained'))
    emit('API_READBACK',dict(status='PASS',fixtures=api,after_revoke='NO_AXES',real_daily='NOT_ENABLED_NO_ACCEPTED_DAILY_SCOPE',production_mount=False))
    emit('CANONICAL_ACTIVATION_HISTORY',dict(status='PASS',fixtures=events,all_final_heads='REVOKE',historical_predictions_retained=True))

if __name__=='__main__':globals()[sys.argv[1]]()
