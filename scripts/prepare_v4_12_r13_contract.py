"""Archive the explicit R13 bundle and record exact protected baseline."""
import argparse,json,hashlib,subprocess
from pathlib import Path
from scripts.v4_11_promotion_contract_r1 import ROOT
def write(path,value):
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
def ref(p):return dict(path=p.as_posix(),sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),bytes=(ROOT/p).stat().st_size)
def run(bundle):
    archive=ROOT/'docs/evidence/next_round_v4_12_r13';archive.mkdir(parents=True,exist_ok=True);(archive/'.gitattributes').write_bytes(b'* -text\n')
    names=['V4_NEXT_ROUND_EXECUTION_MASTER_R13_20261002.md','V4_12_R13A_BREAKOUT_EPISODE_CONTINUITY_CONTRACT_TASK_20261002.md','V4_12_R13B_BREAKOUT_LIFECYCLE_RUNTIME_CLOSURE_TASK_20261002.md','V4_R12_INDEPENDENT_EXTERNAL_AUDIT_R1_20261002.md']
    for n in names:(archive/n).write_bytes((Path(bundle)/n).read_bytes())
    protected=[Path('AGENTS.md'),*Path('data/v4').glob('*ACCEPTED_HEAD.json')]
    protected += list(Path('config').glob('v4_12_*.json'))
    for directory in ['reports/v4_12_runtime_r11','reports/v4_12_runtime_r12']:
        protected += [p for p in Path(directory).rglob('*') if p.is_file()]
    protected += [Path('reports/v4_12')/n for n in ['V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json','V4_12_CONTRACT_FREEZE_EXTERNAL_ACCEPTANCE_R1.json','V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json']]
    stage=dict(contract_id='V4_12_R13_STAGE_CONTRACT',baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),phase0='DEGRADED_PASS',order=['R13A','CONTRACT_LOCAL_PASS','R13B','UNIFIED_COMMIT_PUSH','STOP'],upgrade='docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md#10J',protected=[ref(p) for p in sorted(set(protected))],external_acceptance=False,next_stage='WAIT_INDEPENDENT_EXTERNAL_AUDIT',production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    # Preserve preexisting working bytes and separately bind Git's checkout
    # bytes when text attributes already normalize an unrelated owner head.
    for r in stage['protected']:
        if r['path'].startswith('data/v4/'):
            raw=subprocess.check_output(['git','show',stage['baseline']+':'+r['path']],cwd=ROOT)
            sha=hashlib.sha256(raw).hexdigest()
            if sha!=r['sha256']:r.update(checkout_sha256=sha,checkout_bytes=len(raw),checkout_variance='PREEXISTING_GIT_TEXT_NORMALIZATION_WORKING_BYTES_PRESERVED')
    write('reports/v4_12_runtime_r13/R13_STAGE_CONTRACT.json',stage)
    (ROOT/'reports/v4_12_runtime_r13/.gitattributes').write_bytes(b'* -text\n')
    contract=dict(contract_id='V4_12_BREAKOUT_EPISODE_CONTINUITY_V1',status='ENGINEERING_CANDIDATE',snapshot_extension='V4_12_FROZEN_D1_BREAKOUT_EXTENSION_V1',base_snapshot_contract='config/v4_12_frozen_snapshot_contract_v2.json',owning_anchor_type='PRIOR_HIGH',owner_rule='UNIQUE_TYPE_NOT_ACTIVE_SELECTOR',creation_allowed='KNOWN_NO_ACTIVE_EPISODE',existing_source='EXACT_T_MINUS_1_FROZEN_EPISODE_OWNER_OVERLAY',existing_prior_breakout_exists='FROZEN_ACTIVE_EPISODE_VALIDITY',creation_rule='FROZEN_breakout_trigger',machine='FROZEN_breakout',business_rules='NO_SECOND_RULE_SET',creation_outputs=['BREAKOUT_TENTATIVE','APPROACHING','NO_BREAKOUT','UNKNOWN'],existing_outputs=['FAILED_BREAKOUT','BREAKOUT_ACCEPTED','TESTING','BREAKOUT_TENTATIVE','UNKNOWN'],terminal_states=['FAILED_BREAKOUT'],terminal_history='RETAIN_IMMUTABLE_IDENTITY_ALLOW_LATER_NEW_TRIGGER',same_day_revision='ALL_REVISIONS_USE_EXACT_PREVIOUS_MARKET_SESSION',bootstrap='EXPLICIT_EMPTY_ENGINEERING_SEED_ONLY_OTHERWISE_UNKNOWN',unknown='PRESERVE_ACTIVE_EPISODE_AND_BLOCK_CREATION',creation_day='NO_TESTING_NO_ACCEPTANCE',duplicate_guard='ACTIVE_OR_UNKNOWN_DISALLOWS_BREAKOUT_ANCHOR_CREATION',identity_fields=['breakout_episode_id','event_id','security_id','owning_anchor_id','created_trade_date','state','validity','prior_episode_ref','last_observation_ref'],projection_fields=['basic_breakout_state','breakout_episode_id','breakout_owner_anchor_id','breakout_projection_quality','breakout_projection_reason'],transition_fields=['security_id','breakout_episode_id','event_id','owning_anchor_id','trade_date','revision','from_state','to_state','prior_session_state_ref'],failure_time_role='FROZEN_AST_PRIOR_SUPPORT_STATE_NO_SAME_DAY_OVERRIDE',hard_vectors=['C%02d'%i for i in range(1,13)],unknown_is_false=False,raw_fallback=False,provider_replacement=False,V4_11_candidate_substitution=False)
    write('config/v4_12_breakout_episode_contract_v1.json',contract)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle-dir',required=True);run(p.parse_args().bundle_dir)
