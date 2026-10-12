"""Reject unversioned bytes, wider repair scopes and changed upstream identities."""
import copy,hashlib,json
import pytest
from workbench_desktop.closeout_runtime_sources_r1 import admitted,CONTRACT,AUTHORITY,REPAIRS
@pytest.fixture
def source_root(tmp_path):
    def put(name,raw):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    repairs=[];accepted=[]
    for number,name in enumerate(sorted(REPAIRS)):
        upstream=put('archive/upstream/'+name,('old'+str(number)).encode())
        runtime=put('archive/runtime/'+name,('new'+str(number)).encode())
        accepted.append(dict(upstream,path=name));repairs.append(dict(module_path=name,upstream=upstream,runtime=runtime))
    put('config/read_only_operational_daily_release_policy_v1_1.json',json.dumps(dict(accepted_algorithm_bindings=accepted)).encode())
    document=dict(contract_id=CONTRACT,scope='BOUNDED_NATIVE_PG_ADAPTER_AND_CORRECTED_FOCUS_ONLY',production_acceptance=False,general_algorithm_upgrade_permission=False,historical_PIT_permission=False,automated_trading_permission=False,
        task_card=put('task.md',b'test-only task'),user_scope_amendment=put('amendment.md',b'test-only scope'),repairs=repairs)
    put(AUTHORITY,json.dumps(document).encode());return tmp_path,document
def write(root,document):(root/AUTHORITY).write_text(json.dumps(document),encoding='utf8')
def test_both_versioned_source_sets_are_checked(source_root):
    root,document=source_root;before=(root/AUTHORITY).read_bytes()
    assert set(admitted(root))==REPAIRS and (root/AUTHORITY).read_bytes()==before
@pytest.mark.parametrize('kind',['upstream','runtime'])
def test_actual_source_corruption_rejected(source_root,kind):
    root,document=source_root;(root/document['repairs'][0][kind]['path']).write_bytes(b'changed')
    with pytest.raises(ValueError,match='EXACT_BYTES'):admitted(root)
@pytest.mark.parametrize('permission',['production_acceptance','general_algorithm_upgrade_permission','historical_PIT_permission','automated_trading_permission'])
def test_scope_escalation_rejected(source_root,permission):
    root,document=source_root;document[permission]=True;write(root,document)
    with pytest.raises(ValueError,match='SCOPE_ESCALATION'):admitted(root)
def test_extra_unreviewed_module_rejected(source_root):
    root,document=source_root;document['repairs'].append(copy.deepcopy(document['repairs'][0]));write(root,document)
    with pytest.raises(ValueError,match='REPAIR_SET'):admitted(root)
def test_relabelled_accepted_upstream_rejected(source_root):
    root,document=source_root;document['repairs'][0]['upstream']['sha256']='0'*64;write(root,document)
    with pytest.raises(ValueError,match='ACCEPTED_IDENTITY'):admitted(root)
def test_path_escape_rejected(source_root):
    root,document=source_root;document['repairs'][0]['runtime']['path']='../outside.py';write(root,document)
    with pytest.raises(ValueError,match='PATH_ESCAPE'):admitted(root)
