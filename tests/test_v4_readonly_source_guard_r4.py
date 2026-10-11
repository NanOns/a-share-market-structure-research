import json,os,subprocess,sys
from pathlib import Path

def test_readonly_input_guard_blocks_open_replace_and_remove_before_mutation(tmp_path):
    source=tmp_path/'source';source.mkdir();original=source/'frozen.txt';original.write_text('frozen',encoding='utf8')
    stage=tmp_path/'stage.txt';stage.write_text('candidate',encoding='utf8')
    code='''
import json,os,sys
from pathlib import Path
from scripts.r4_readonly_source_guard import install,ReadOnlySourceViolation
source,stage=map(Path,sys.argv[1:]);original=source/'frozen.txt'
receipt=install([source]);assert original.read_text()=='frozen'
actions=[lambda:original.write_text('changed'),lambda:os.open(original,os.O_RDWR),lambda:os.replace(stage,original),lambda:original.unlink()]
for action in actions:
    try:action()
    except ReadOnlySourceViolation as exc:assert not isinstance(exc,Exception)
    else:raise AssertionError('SOURCE_MUTATION_WAS_ALLOWED')
assert original.read_text()=='frozen' and stage.read_text()=='candidate'
assert not (source/'new.txt').exists()
print(json.dumps(dict(rejected=len(receipt['events']),unchanged=True)))
'''
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,'-B','-c',code,str(source),str(stage)],cwd=root,env=dict(os.environ,PYTHONPATH=str(root),TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp'),capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)==dict(rejected=4,unchanged=True)
