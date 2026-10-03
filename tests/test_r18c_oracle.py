"""Independent literal/counter oracle and all mandatory adversarial mutations."""
import json,ast,hashlib
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.v4_14_independent_oracle import Oracle,read,exact,checksum,require
ROOT=Path(__file__).resolve().parents[1]
GATE='reports/v4_14_replay_r18/full_dag_r3/completion_gate.json'

@pytest.fixture(scope='module')
def evidence():
    o=Oracle(ROOT);g=json.loads((ROOT/GATE).read_bytes());m=read(ROOT,g['records'][-1]['publication']);producer=read(ROOT,g['records'][-2]['execution']);consumer=read(ROOT,g['records'][-1]['execution'])
    return o,g,m,producer,consumer

def test_oracle_literal_seventeen_dimensions(evidence):
    o,*_=evidence;v=o.vectors(json.loads((ROOT/'reports/r18a/r3/synthetic_vector_runtime.json').read_bytes()));assert len(v)==60 and len({r['dimension'] for r in v})==17

def test_oracle_full_persisted_chain(evidence):
    o,g,*_=evidence;assert o.gate(ROOT,g)

@pytest.mark.parametrize('mutation',[
 'future_source','after_cutoff','future_membership','current_as_historical','wrong_previous','r2_to_r1','prior_digest','same_pid','producer_not_exited','revision_logical_key','persistent_actionable','duplicate_episode','unknown_false','stale_authority','old_bytes_overwrite','different_output_digest'])
def test_mandatory_perturbations(evidence,mutation,tmp_path):
    o,g,original,p,c=evidence;m=deepcopy(original);e=m['envelope'];p=deepcopy(p);c=deepcopy(c);out=m['output'];prior=read(ROOT,m['previous_state_publication'])['output']['d2']['rows'][0]
    with pytest.raises(ValueError):
        if mutation=='future_source':e['source_availability'][0]['max_source_trade_date']='2026-10-01';o.temporal(e)
        elif mutation=='after_cutoff':e['source_availability'][0]['system_available_at']='2026-10-01T00:00:00+00:00';o.temporal(e)
        elif mutation=='future_membership':e['source_availability'][0]['membership_effective_date']='2026-10-01';o.temporal(e)
        elif mutation=='current_as_historical':e.update(evidence_class='HISTORICAL_PIT_EFFECTIVENESS',AS_RECORDED=False,historical_membership_basis='CURRENT_MEMBERSHIP');o.temporal(e)
        elif mutation=='wrong_previous':e['previous_market_session']='2026-09-28';o.temporal(e)
        elif mutation=='r2_to_r1':m['previous_state_publication']=g['same_day']['r1'];e['previous_state_publication']=m['previous_state_publication'];m['input_digest']=checksum(e);m['replay_publication_id']='REPLAY:'+checksum({k:v for k,v in m.items() if k!='replay_publication_id'});o.manifest(ROOT,m)
        elif mutation=='prior_digest':binding=deepcopy(m['previous_state_publication']);binding['sha256']='0'*64;read(ROOT,binding)
        elif mutation=='same_pid':c['pid']=p['pid'];o.cross_process(p,c)
        elif mutation=='producer_not_exited':p['producer_exited']=False;o.cross_process(p,c)
        elif mutation=='revision_logical_key':out['logical_events'][0]['revision']='r2';o.events(out,prior)
        elif mutation=='persistent_actionable':out['logical_events'].append(dict(out['logical_events'][0],event_type='NEW_CONFIRMED'));o.events(out,prior)
        elif mutation=='duplicate_episode':row=out['d2']['rows'][0];row['episode_id']='DUPLICATE';o.state(row,prior,out['d2']['inputs'][0])
        elif mutation=='unknown_false':u=read(ROOT,g['records'][-3]['publication']);row=u['output']['d2']['rows'][0];row['final_eligibility']='FALSE';old=read(ROOT,u['previous_state_publication'])['output']['d2']['rows'][0];o.state(row,old,u['output']['d2']['inputs'][0])
        elif mutation=='stale_authority':e['authority_bindings']['contract_package'][0]['path']='config/v4_14_replay_gate_b_contract_v1.json';o.authority(e)
        elif mutation=='old_bytes_overwrite':p=tmp_path/'old.json';p.write_bytes(b'original');binding=dict(path='old.json',bytes=8,sha256=hashlib.sha256(b'original').hexdigest());p.write_bytes(b'changed!');exact(tmp_path,binding)
        elif mutation=='different_output_digest':m['output_digest']='0'*64;o.deterministic(original,m)

def test_oracle_has_no_runtime_expected_dependency():
    tree=ast.parse((ROOT/'scripts/v4_14_independent_oracle.py').read_text(encoding='utf8'))
    assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any('v4_14_replay_runtime' in a.name or 'v4_14_full_dag' in a.name for a in getattr(n,'names',[])) for n in ast.walk(tree))
    assert 'evaluate_case(' not in ast.unparse(tree)

def test_real_evidence_classes_kept_separate():
    gate=json.loads((ROOT/'reports/r18c/real_scoped_gate.json').read_bytes());m=read(ROOT,gate['publication'])
    assert gate['R18_REAL_ACCEPTED_SOURCE_REPLAY']=='PASS_CAPABILITY_SCOPED'
    assert m['profile_count']==5224 and m['context_count']==50162
    assert m['knowledge_lineage']=='RECONSTRUCTED_CORRECTED' and m['AS_RECORDED'] is False
    assert m['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' and m['event_counts']['UNKNOWN']==4683
    assert not any(m[k] for k in ['production','shadow','focus','raw_provider_fallback'])
