"""R9：真实 DuckDB 参数执行与 V4 静态资源可达性回归。"""
import importlib
import json

import duckdb
import pytest

from scripts import check_v4_business_literals as scanner


@pytest.mark.parametrize('module_name', [
    'scripts.run_v4_04_full_market_candidate',
    'scripts.run_v4_04_full_market_candidate_r4',
])
def test_real_parquet_queries_bind_path_before_cutoff(tmp_path, module_name):
    module = importlib.import_module(module_name)
    path = tmp_path / "data's.parquet"
    with duckdb.connect() as db:
        db.execute('''CREATE TABLE input AS
            SELECT sid canonical_security_id, sid source_security_key,
                   'SH_MAIN' board_scope, d::INTEGER trade_date,
                   d::INTEGER period_last_session, 'CLOSED_ONLY' period_view,
                   'CLOSED' period_status, 'QFQ' price_basis, 10.0 AS "close",
                   'source' source_daily_digest, 10.0 qfq_close,
                   11.0 qfq_high, 9.0 qfq_low, 100.0 amount,
                   'OBSERVED' adjusted_quality, 'ACTUAL_TRADED' trading_status
            FROM (VALUES ('SYN-A'), ('SYN-B')) s(sid)
            CROSS JOIN (VALUES (20260302), (20260303), (20260304)) t(d)''')
        db.execute('COPY input TO ? (FORMAT PARQUET)', [str(path)])
        daily = module._daily(db, path, 20260303)
        periods = module._periods(db, path, 1, 20260303)
        assert set(daily) == set(periods) == {'SYN-A', 'SYN-B'}
        for sid in daily:
            assert [row['trade_date'] for row in daily[sid]] == ['2026-03-02', '2026-03-03']
            assert [row['period_last_session'] for row in periods[sid]] == ['2026-03-03']
        with pytest.raises(duckdb.Error):
            module._daily(db, tmp_path / 'absent.parquet', 20260303)
        with pytest.raises(duckdb.Error):
            module._periods(db, tmp_path / 'absent.parquet', 1, 20260303)


def test_service_static_edges_survive_import_graph_and_follow_jsx(tmp_path, monkeypatch):
    service = 'src/workbench_service/v4_server.py'
    ui = 'src/workbench_service/static/v4-workbench.html'
    js = 'src/workbench_service/static/v4-workbench.js'
    jsx = 'src/components/chart.jsx'
    bodies = {service: 'from workbench_service import helper\n',
              'src/workbench_service/helper.py': 'VALUE = 1\n',
              ui: '<script src="v4-workbench.js"></script>',
              js: 'import Chart from "../../components/chart.jsx";\nconst stock="sh600001";',
              jsx: 'const date = "2026-03-03";'}
    for rel, body in bodies.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')
    monkeypatch.setattr(scanner, 'ROOT', tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(scanner, 'tracked_files', lambda: list(bodies))
    monkeypatch.setattr(scanner, 'active_entrypoint_inventory',
                        lambda files: ([service], {'status': 'SOURCE_VERIFIED'}))
    reachable, graph, _, _ = scanner.runtime_graph(list(bodies))
    assert {ui, js, jsx, 'src/workbench_service/helper.py'} <= reachable
    assert 'src/workbench_service/helper.py' in graph[service]
    findings, _ = scanner.scan(list(bodies))
    assert all(row['runtime_reachable'] for row in findings if row['file'] in {js, jsx})
    gate = scanner.global_gate(findings)
    assert gate['active_unknown'] >= 2
    assert scanner.gate_exit_code(gate) == 1


def test_source_sha_alone_does_not_prove_historical_consumption(tmp_path, monkeypatch):
    path = tmp_path / 'docs/evidence/history_20260303.json'
    path.parent.mkdir(parents=True)
    path.write_text('{}', encoding='utf-8')
    import ast, hashlib
    source = f'SOURCE="docs/evidence/history_20260303.json"\nSOURCE_SHA256="{hashlib.sha256(path.read_bytes()).hexdigest()}"\ndef current(): return SOURCE\n'
    monkeypatch.setattr(scanner, 'ROOT', tmp_path)
    assert scanner.verified_historical_evidence_binding('src/current.py', '20260303', ast.parse(source), source) is None


def test_dynamic_local_tests_and_js_imports_remain_active(tmp_path,monkeypatch):
    bodies={'run_v4.py':'import importlib\nimportlib.import_module("tests.fixture")\n',
        'tests/fixture.py':'DAY="2026-03-03"\n',
        'src/workbench_service/static/app.js':'const chunk=import("./chunk.jsx"); fetch(route);',
        'src/workbench_service/static/chunk.jsx':'const s="sh600001";'}
    for rel,body in bodies.items():
        p=tmp_path/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf8')
    monkeypatch.setattr(scanner,'ROOT',tmp_path)
    monkeypatch.setattr(scanner,'tracked_files',lambda:list(bodies))
    monkeypatch.setattr(scanner,'active_entrypoint_inventory',lambda files:(['run_v4.py','src/workbench_service/static/app.js'],{'status':'SOURCE_VERIFIED'}))
    findings,summary=scanner.scan(list(bodies))
    assert any(r['environment']=='ACTIVE_TEST_IMPORT' and r['handling']=='UNRESOLVED' for r in findings)
    assert any(r['file'].endswith('chunk.jsx') and r['runtime_reachable'] for r in findings)
    assert scanner.global_gate(findings,summary)['browser_route_unresolved']>0


def test_package_preparation_stops_before_writes_on_strict_gate(monkeypatch):
    from scripts import build_windows_package_v1 as package
    calls=[]
    def refuse(command,**kwargs):
        calls.append(command)
        import subprocess
        raise subprocess.CalledProcessError(1,command)
    monkeypatch.setattr(package.subprocess,'run',refuse)
    with pytest.raises(Exception):package.prepare()
    assert len(calls)==1 and 'check_v4_business_literals.py' in ' '.join(map(str,calls[0]))
    assert '--strict-runtime' in calls[0]
    assert '--allow-incomplete-inventory' not in calls[0]


@pytest.mark.parametrize('case,expected',[
    ('calendar_ahead','TARGET_UNIVERSE_SESSION_MISSING'),
    ('missing_status','TARGET_STATUS_MISSING_OR_INCOMPLETE'),
    ('suspended_bar','TARGET_UNIVERSE_STATUS_BAR_CONFLICT'),
])
def test_period_main_refuses_incomplete_target_before_output(tmp_path,monkeypatch,case,expected):
    import gzip,sys
    from scripts import build_v4_02_formal_periods as module
    def write(name,value):
        p=tmp_path/name;p.write_text(json.dumps(value),encoding='utf8');return p
    contract=write('contract.json',{'calendar_acceptance_receipt':'calendar_receipt.json'})
    write('calendar_receipt.json',{'status':'FORMAL_MARKET_CALENDAR_PASS'})
    write('calendar.json',{'session_dates':['2026-03-02','2026-03-03','2026-03-04','2026-03-05']})
    day='2026-03-03' if case!='calendar_ahead' else '2026-03-02'
    row=dict(source_security_key='SH.SYN-A',security_id='SYN-A',board_scope='SH_MAIN',trade_date=day,source_bar_present=True)
    for name,rows in [('universe.gz',[row]),('status.gz',[] if case=='missing_status' else [dict(row,status='SUSPENDED' if case=='suspended_bar' else 'ACTUAL_TRADED')])]:
        (tmp_path/name).write_bytes(gzip.compress(('\n'.join(json.dumps(r) for r in rows)).encode()))
    args=['build','--asof','20260303']
    for key,value in {'universe':'universe.gz','status':'status.gz','raw':'missing.parquet','dispositions':'missing.gz','gbbq':'missing.gbbq','gbbq-map':'missing.map','calendar-sse':'calendar.json','calendar-szse':'calendar.json','daily-output':'daily.parquet','weekly-output':'weekly.parquet','monthly-output':'monthly.parquet','receipt':'receipt.json'}.items():args.extend(['--'+key,value])
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'CONTRACT',contract);monkeypatch.setattr(sys,'argv',args)
    with pytest.raises(ValueError,match=expected):module.main()
    assert not (tmp_path/'daily.parquet').exists()


def test_preview_executes_with_real_enveloped_context_dates():
    import re,shutil,subprocess
    from pathlib import Path
    node=shutil.which('node')
    if not node:pytest.skip('需 Node.js 执行实际页面脚本')
    html=(Path(__file__).resolve().parents[2]/'src/workbench_service/static/r43-operational-preview.html').read_text(encoding='utf8')
    script=re.search(r'<script>(.*?)</script>',html,re.S).group(1)
    harness=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const calls=[],options=[],day={value:'',append(o){options.push(o.value);this.value ||=o.value;}};
const document={querySelector(){return {};},createElement(){return {};}};
const context={context_token:'synthetic-token',context:{accepted_trade_date:'2026-03-04',available_trade_dates:['2026-03-03','2026-03-04']}};
vm.runInNewContext(SOURCE,{day,domain:{value:'stocks'},document,fetch:async url=>{calls.push(url);return {json:async()=>calls.length===1?context:{rows:[]}};}});
setImmediate(()=>{assert.deepEqual(options,['2026-03-03','2026-03-04']);assert.equal(day.value,'2026-03-04');assert.match(calls[1],/trade_date=2026-03-04&context_token=synthetic-token/);});
'''.replace('SOURCE',json.dumps(script,ensure_ascii=False))
    subprocess.run([node,'-e',harness],check=True,capture_output=True,text=True)


def test_period_main_crosses_week_month_and_retains_suspended_target(tmp_path,monkeypatch):
    import gzip,sys
    import pyarrow as pa
    import pyarrow.parquet as pq
    from scripts import build_v4_02_formal_periods as module
    sessions=['2026-01-29','2026-01-30','2026-02-02','2026-02-03','2026-02-04']
    def write(name,value):
        path=tmp_path/name;path.write_text(json.dumps(value),encoding='utf8');return path
    contract=write('contract.json',{'contract_id':'SYN-PERIODS','calendar_acceptance_receipt':'calendar_receipt.json'})
    write('calendar_receipt.json',{'status':'FORMAL_MARKET_CALENDAR_PASS'})
    write('calendar.json',{'session_dates':sessions});write('classification.json',{'per_security_scope_counts':{}})
    universe=[];status=[];raw=[]
    for sid in ['SYN-A','SYN-B']:
        for day in sessions:
            suspended=sid=='SYN-B' and day==sessions[-2]
            universe.append(dict(source_security_key='SH.'+sid,security_id=sid,board_scope='SH_MAIN',trade_date=day,source_bar_present=not suspended))
            status.append(dict(source_security_key='SH.'+sid,trade_date=day,status='SUSPENDED' if suspended else 'ACTUAL_TRADED'))
            if not suspended:raw.append(dict(source_security_key='SH.'+sid,trade_date=int(day.replace('-','')),open_price_raw=1000,high_price_raw=1100,low_price_raw=900,close_price_raw=1050,amount_source_native=1000.,volume_source_native=100,record_quality='VALID'))
    for name,rows in [('universe.gz',universe),('status.gz',status),('dispositions.gz',[])]:
        (tmp_path/name).write_bytes(gzip.compress(('\n'.join(json.dumps(r) for r in rows)).encode()))
    with pq.ParquetWriter(tmp_path/'raw.parquet',pa.Table.from_pylist(raw).schema) as writer:
        for sid in ['SYN-A','SYN-B']:writer.write_table(pa.Table.from_pylist([r for r in raw if r['source_security_key']=='SH.'+sid]))
    (tmp_path/'actions').write_bytes(b'');(tmp_path/'map').write_bytes(b'')
    args=['build','--asof','20260203']
    for key,value in {'universe':'universe.gz','status':'status.gz','raw':'raw.parquet','classification':'classification.json','dispositions':'dispositions.gz','gbbq':'actions','gbbq-map':'map','calendar-sse':'calendar.json','calendar-szse':'calendar.json','daily-output':'daily.parquet','weekly-output':'weekly.parquet','monthly-output':'monthly.parquet','receipt':'receipt.json'}.items():args.extend(['--'+key,value])
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'CONTRACT',contract);monkeypatch.setattr(sys,'argv',args)
    monkeypatch.setattr(module,'read_gbbq',lambda p:[])
    assert module.main()==0
    daily=pq.read_table(tmp_path/'daily.parquet').to_pylist()
    assert len(daily)==7 and max(r['trade_date'] for r in daily)==20260203
    for name in ['weekly.parquet','monthly.parquet']:
        rows=pq.read_table(tmp_path/name).to_pylist()
        assert {r['canonical_security_id'] for r in rows}=={'SYN-A','SYN-B'}
        assert all(r['max_source_trade_date']<=20260203 for r in rows)
        assert any(r['canonical_security_id']=='SYN-B' and r['suspended_count']==1 for r in rows)
        assert {r['period_view'] for r in rows}=={'CLOSED_ONLY','AS_OF_PARTIAL'}
