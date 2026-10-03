"""Expanded R17 regression: all 22 historical failures included, no deselection."""
import sys,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCOPE=['tests/test_v4_13_r15_contract.py','tests/test_v4_13_r15r1_lineage.py','tests/test_v4_13_r16a_runtime.py','tests/test_v4_13_r16b_runtime.py','tests/test_v4_13_r16c_publication.py','tests/test_v4_13_r16r1_repair.py','tests/v4_08/test_r5_2_context_authority.py','tests/v4_08/test_r5_runtime.py','tests/v4_09','tests/v4_10','tests/v4_11_r5','tests/test_v4_12_runtime_r1.py','tests/test_v4_12_multi_anchor_r12.py','tests/test_v4_12_persisted_r11.py','tests/test_v4_12_breakout_episode_r13.py']
EXTRA=['tests/test_r17a_historical_governance.py']


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    before=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    args=[sys.executable,'-m','pytest',*SCOPE,*[p for p in EXTRA+['tests/test_r17b_promotion.py','tests/test_r17c_replay_contract.py'] if (ROOT/p).exists()],'-q','--junitxml='+str(output/'regression.xml')]
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace')
    (output/'regression.log').write_text(result.stdout+result.stderr,encoding='utf8')
    tree=ET.parse(output/'regression.xml');cases=list(tree.iter('testcase'))
    failed=[dict(test=c.attrib,failure=c.find('failure').attrib) for c in cases if c.find('failure') is not None]
    errors=[c.attrib for c in cases if c.find('error') is not None];skips=[c.attrib for c in cases if c.find('skipped') is not None]
    after=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
    gate=dict(source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),command=args,exit_code=result.returncode,pass_count=len(cases)-len(failed)-len(errors)-len(skips),failures=failed,errors=errors,skipped=skips,deselected_count=0,deselected=[],git_status_before=before.decode(),git_status_after=after.decode(),source_unchanged=before==after,formal_migration=False,test_database='DISPOSABLE_CLUSTER_ONLY_EXISTING_REGRESSION_FIXTURES')
    (output/'regression_gate.json').write_text(json.dumps(gate,sort_keys=True,ensure_ascii=False),encoding='utf8')
    assert result.returncode==0 and not failed and not errors
    return gate

if __name__=='__main__':print(json.dumps(run(sys.argv[1]),sort_keys=True,ensure_ascii=False))
