from pathlib import Path
exec(compile(Path('G:/codex_tmp/full_system_repair_r3_239fb9b5/a1_close.py').read_text(encoding='utf8'),'a1-close','exec'))
BASE=Path('G:/codex_tmp/full_system_repair_r3_239fb9b5')
for name in ('a2_junit.xml','a2_initial_link_privilege_failure.xml','a3_junit.xml'):
    write(name,(BASE/name).read_bytes().replace(b'\r\n',b'\n'))
for label,issues,files,evidence,limitations in [
    ('A2',['FA-005'],['src/workbench_analysis/fep_e2/registry.py','src/workbench_analysis/fep_e3/protocol.py','src/workbench_analysis/fep_engineering_storage.py','config/fep_engineering_storage_contract_v2.json','tests/test_audit_repair_storage_r3.py'],['a2_junit.xml'],'Windows symlink creation denied (1314); real junction containment/escape tested. Identity and exclusive atomic publication retained. G root as a whole is forbidden.'),
    ('A3',['FA-013','FA-014'],['src/workbench_service/core_product_bff_r1.py','src/workbench_service/static/core-product-r1/replay.js','tests/test_audit_repair_compare_r3.py'],['A3_HTTP_DOM_READBACK.json','a3_junit.xml'],'Five real dated alias/unknown/different-entity HTTP cases and four real Edge DOM modes. Early harness assertions corrected for structured reason code and established three-decimal UI formatting; no production restart.')]:
    write(label+'_REPAIR_RESULT.json',dict(contract_id='FULL_SYSTEM_'+label+'_REPAIR_R3',base_head='239fb9b545ac25305af02a645a77d82246cbb71a',issues=issues,source_bindings=[dict(path=p,sha256=sha(ROOT/p)) for p in files],evidence=evidence,limitations=limitations,acceptance='ENGINEERING_PASS_EXTERNAL_PENDING',production_loaded=False,next='Other independent A/B packages; external recheck before promotion'))
    effective=json.loads((OUT/'EFFECTIVE_AUDIT_ITEMS_R3.json').read_bytes())
    for r in effective['issues']:
        if r.get('audit_item_id') in issues:r.update(status='ENGINEERING_FIXED_EXTERNAL_PENDING',current_block='EXTERNAL_RECHECK_PENDING',repair_evidence=label+'_REPAIR_RESULT.json')
    write('EFFECTIVE_AUDIT_ITEMS_R3.json',effective)
report=OUT/'REPAIR_REPORT_R3.md'
text=report.read_text(encoding='utf8')+'''\n## A2 / A3

E2/E3 仅放行解析后位于 G:/codex_tmp 或 G:/codex work/fep_engineering 的工程路径。目录穿越、非工程、生产、TDX及旧E/F路径拒绝；Windows symlink创建因权限1314失败原件保留，采用真实junction验证重解析点内外路径，12项最终通过，未改变权限设置。

比较与详情共用按日期可用对象的唯一别名解析，支持旧/新六位代码及完整代码，歧义/未知不选任意实体。四mode按股票rps5/20、板块sector_rs5/20取值，显示收益与分位单位。五日真实HTTP及四mode Edge DOM通过。浏览器与HTTP服务仅审计GET，未接管28765。
'''
write('REPAIR_REPORT_R3.md',text.encode())
for path in OUT.rglob('*'):
    if path.is_file() and path.suffix in ('.md','.json','.xml','.py'):
        raw=path.read_bytes();canonical=raw.replace(b'\r\n',b'\n')
        if raw!=canonical:
            temp=path.with_suffix('.tmp');temp.write_bytes(canonical);os.replace(temp,path)
reproduce=OUT/'reproduce';reproduce.mkdir(exist_ok=True)
for name in ('prepare.py','a1_close.py','close_small.py','a3_http_dom.py'):
    write('reproduce/'+name,(BASE/name).read_bytes())
print('SMALL_PACKAGES_CLOSED_ENGINEERING_ONLY')
