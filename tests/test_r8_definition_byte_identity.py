import hashlib
import json
from pathlib import Path
from workbench_analysis.forward_r7 import load_definitions,DEFINITIONS_PATH


def test_real_legacy_definition_identity_survives_windows_git_line_endings(tmp_path):
    source=(Path(__file__).resolve().parents[1]/DEFINITIONS_PATH).read_bytes().replace(b'\r\n',b'\n')
    results=[]
    for name,raw in [('lf',source),('crlf',source.replace(b'\n',b'\r\n'))]:
        root=tmp_path/name;path=root/DEFINITIONS_PATH;path.parent.mkdir(parents=True);path.write_bytes(raw)
        value,digest=load_definitions(root);identity=value.pop('source_byte_identity')
        assert identity['raw_sha256']==hashlib.sha256(raw).hexdigest()
        assert identity['lf_sha256']==digest
        results.append((value,digest,identity))
    assert results[0][:2]==results[1][:2]
    assert results[0][1]=='b90f0ff4c8f47f045cbbe2f3e000581b5c3a1ca89d65440993c8059acb62e6a5'
    assert results[0][2]['raw_sha256']!=results[1][2]['raw_sha256']


def test_rule_content_change_is_not_normalized_away(tmp_path):
    source=json.loads((Path(__file__).resolve().parents[1]/DEFINITIONS_PATH).read_bytes())
    source['rules'][0]['unapproved_semantic_change']=True
    path=tmp_path/DEFINITIONS_PATH;path.parent.mkdir(parents=True);path.write_text(json.dumps(source),encoding='utf8')
    _,digest=load_definitions(tmp_path)
    assert digest!='b90f0ff4c8f47f045cbbe2f3e000581b5c3a1ca89d65440993c8059acb62e6a5'
