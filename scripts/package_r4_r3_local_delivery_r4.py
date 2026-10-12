"""One G-only reviewable delivery, explicitly retaining unresolved engineering gates."""
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'docs/audits/r4_r3_local_delivery_20261012'
DEST = Path('G:/codex_tmp/V4_R4_R3_FINAL_DELIVERY')
WORK = Path('G:/codex_tmp/r4_r3_pg_publication_v2')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    journal = json.loads((AUDIT / 'S1_JOURNAL_REPAIRED/RESULT.json').read_bytes())
    oracle = json.loads((AUDIT / 'S1_ORACLE_FULL/RESULT.json').read_bytes())
    assert journal['status'] == oracle['status'] == 'PASS_SCOPED'
    assert journal['source_bytes_stable'] and journal['protected_before'] == journal['protected_after']
    assert not DEST.exists(), 'PRESERVE_EXISTING_DELIVERY'
    DEST.mkdir(parents=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    records = []

    def write(name, value):
        path = DEST / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = value.encode('utf8') if isinstance(value, str) else value
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_bytes(data)
        os.replace(temp, path)

    def copy(source, name, role):
        source = Path(source)
        path = DEST / name
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + '.tmp')
        shutil.copyfile(source, temp)
        assert sha(source) == sha(temp)
        os.replace(temp, path)
        records.append(dict(path=name, source=str(source), role=role))

    def compact(source, name, role):
        source = Path(source)
        write(name, gzip.compress(source.read_bytes(), mtime=0))
        records.append(dict(path=name, source=str(source), source_bytes=source.stat().st_size, source_sha256=sha(source), role=role, encoding='gzip'))

    for path in sorted(AUDIT.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(AUDIT).as_posix()
        if path.suffix == '.gz' and path.with_suffix('').is_file():
            continue
        if path.name == 'PG_INTENTS.jsonl':
            compact(path, 'evidence/postgres/' + relative + '.gz', 'actual_native_pg_sql_intents')
        elif 'ORACLE' in relative or 'IDENTITY_REPAIR' in relative:
            copy(path, 'evidence/oracle/' + relative, 'actual_independent_oracle_and_delta')
        else:
            copy(path, 'evidence/recovery/' + relative, 'checkpoint_and_stage_evidence')
    pause = ROOT / 'docs/audits/r4_r3_integration_20261011/PAUSE_CHECKPOINT_20261012_R1'
    for path in sorted(pause.iterdir()):
        if path.is_file():
            copy(path, 'evidence/recovery/PAUSE_CHECKPOINT_20261012_R1/' + path.name, 'unaltered_432_pause_archives_and_seal')
    scope = ROOT / 'docs/audits/r4_r3_scope_20261011'
    for path in sorted(scope.glob('LOCAL_S1_*')):
        if path.suffix == '.gz' and path.with_suffix('').is_file():
            continue
        if path.name.endswith('.jsonl') or path.name.endswith('_SOURCE_BINDINGS.json'):
            compact(path, 'evidence/junit/' + path.name + '.gz', 'bounded_test_raw_and_source_freeze')
        else:
            copy(path, 'evidence/junit/' + path.name, 'bounded_test_raw_and_source_freeze')
    for name in ('V4_TEST_LEGAL_SCOPE_FINAL.json', 'V4_MODULE_LEGAL_SCOPE_REVIEW.json', 'TEST_NODE_DISPOSITION_FINAL.csv'):
        copy(scope / name, 'evidence/junit/baseline/' + name, 'unaccepted_legal_scope_preserved_without_reclassification')
    for name in ('DRIVE_MASTER_R4.md', 'DRIVE_TASK_CARD_R3.md'):
        copy(ROOT / 'docs/audits/r4_r3_integration_20261011' / name, 'reports/contracts/' + name, 'historical_contract_drive_steps_superseded')
    override = Path('D:/Users/lps/Desktop/阶段任务/V4_R4_R3_Codex本地执行与集中交付规则_R4_20261012.md')
    copy(override, 'reports/contracts/' + override.name, 'user_authorized_current_workflow_override')
    source_names = [
        'scripts/verify_r4_r3_local_resume_s0.py', 'scripts/audit_r4_r3_focus_semantics_s1.py',
        'scripts/repair_r4_r3_focus_identity_s1.py', 'scripts/publish_r4_r3_focus_journal_s1.py',
        'scripts/package_r4_r3_local_delivery_r4.py', 'src/focus_tracker/v4_exact_identity_adapter_r4.py',
        'src/focus_tracker/v4_native_core_journal.py', 'tests/test_v4_focus_source_identity_r4.py']
    for name in source_names:
        copy(ROOT / name, 'evidence/source/' + name, 'reviewable_source_not_a_clean_full_regression_claim')
    repair = json.loads((AUDIT / 'S1_IDENTITY_REPAIR_R2/RESULT.json').read_bytes())
    projection = WORK / repair['result']['focus']['path']
    assert sha(projection) == repair['result']['focus']['sha256']
    copy(projection, 'evidence/oracle/REPAIRED_FOCUS_FORWARD.json.gz', 'full_repaired_2805_episode_candidate')
    copy(WORK / journal['journal']['path'], 'evidence/postgres/REPAIRED_JOURNAL.pg.json', 'immutable_pg_descriptor_requires_original_instance_or_rebinding_on_restore')
    external = []
    for path, expected in repair['inputs'].items():
        p = Path(path)
        external.append(dict(path=path, bytes=p.stat().st_size, sha256=expected, identity='S0_VERIFIED_IMMUTABLE_INPUT', restore='Keep original G path; replay supplied repair and journal scripts in isolated attested PG. A restored cluster needs a new descriptor and independent validation.'))
    write('evidence/recovery/LARGE_INPUT_REFERENCES.json', json.dumps(external, indent=2, ensure_ascii=False) + '\n')
    write('evidence/recovery/RESTORE.md', '# 恢复边界\n\n432 项暂停归档按 ARCHIVE_MANIFEST.json 解压核对，不覆盖已有不同字节文件。大体积输入按 LARGE_INPUT_REFERENCES.json 只读取证。新 Journal 在原隔离集群中有完整内容封存；新 PG 实例恢复须生成新身份 descriptor 并重新核验，不能复用旧签名。\n\n原失败 Journal 仅证明旧错误投影的存储一致，不能作为公司行动数值接受。修复复现顺序：身份修复脚本 → FULL 独立 oracle → repaired Journal 脚本；示例命令/输入路径已在各回执中冻结。现有输出拒绝覆盖，复跑需新版本命名空间。\n')
    delta = json.loads((AUDIT / 'S1_IDENTITY_REPAIR_R2/NUMERICAL_DELTA.json').read_bytes())
    status = ('# 完成与遗留\n\n整体：ENGINEERING_INCOMPLETE / EXTERNAL_ACCEPTANCE_BLOCKED。这是本地续行检查点交付，不能称全部任务完成。\n\n'
              f'S0 PASS：432 项暂停归档、2,805 episodes、原输入、3 个暂停保护对象和 4 个 PG 身份一致。\n\n'
              f'S1 局部通过：{oracle["numerical_comparisons"]:,} 个价格比较、{oracle["actual_company_action_paths"]} 条公司行动路径、{oracle["predicate_input_formula_checks"]:,} 个谓词输入/公式检查、{oracle["settlement_checks"]:,} 条结算检查；11 条缺失保留 UNKNOWN。修复改变 {len(delta)} 条路径、{len({r["security"] for r in delta})} 只证券的数值。新隔离 Journal 五日写入/读回、幂等、CAS 冲突及失败回滚通过。\n\n'
              'S1 默认 HTTP/联合 Head 消费及源符号缺陷的其它生产者路径仍 OPEN，S1 总门未签 PASS；按工作包出口要求未自动进入 S2。S2 唯一合法分母、全部真实消费者、56 类、FEP/§87A 全语义、前端/性能及最终 clean run 未完成。历史原 4,568 节点和旧失败全部保留。当前本地额外候选模块为 155，文档引用 148；需追溯版本变化，不能擅改分母。\n\n'
              '外审、生产切换、正式 Grant、真实首获及成熟门独立。无 Drive 操作、生产切换或 TDX 写入。\n')
    write('01_FINAL_STATUS_完成与遗留.md', status)
    write('reports/修复报告.md', status + '\n缺陷：Series.symbol 使用 SEC 内部 ID，GBBQ 使用交易所代码，导致公司行动匹配失效。新增精确身份候选适配器，以冻结身份映射拒绝缺失/重复/错配，以 v0.3 有理数实现公司行动；只在显式候选合同下由 native Journal 选用，旧投影/旧接受对象保留。\n')
    write('reports/独立数值和数据流核对报告.md', f'# 独立核对\n\n独立 oracle 不调用 Focus 分类器、生命周期 reducer 或复权 builder。复用二进制 parser 解码源记录，按独立有理数公式、身份表、D2、Core/Profile 输入和交易日核对。\n\n{json.dumps({k:v for k,v in oracle.items() if k not in ("limitations","source_projection")}, ensure_ascii=False, indent=2)}\n\n测试有两次冻结局部运行：24 PASS 与 23 PASS；有重叠节点，禁止相加宣称 47 个唯一节点或全回归通过。尚未完成独立外审或完整命令级 clean run。\n')
    write('00_README_上传说明.md', '# 人工统一上传\n\n推荐手动上传本目录的 V4_R4_R3_FINAL_DELIVERY.zip；也可上传整个文件夹。目标：https://drive.google.com/drive/folders/1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD 。建议子目录 V4_R4_R3_20261012_最终交付。Codex 未调用或验证云端。\n\n本包完整保留本次局部修复和暂停现场，包含未完成事项，不是全系统 PASS 或生产准入包。所有接受范围以 01_FINAL_STATUS 和原始收据为准。大输入/PG 集群未机械收入 ZIP，恢复说明位于 evidence/recovery。\n')
    write('02_CHANGELOG_提交与源码版本.md', '# 源码版本\n\nGit HEAD：' + head + '\n\n只提交本轮指定源码和证据；其它既有工作区改动保留。HEAD 不代替实际运行源码字节，测试及 Journal 的实际 source bindings 均收录。封存源码 SHA 与工程通过范围独立于整体 clean run。\n\n' + subprocess.check_output(['git', 'log', '-5', '--format=%H %s'], cwd=ROOT, text=True))
    nodes = list(csv.DictReader((scope / 'TEST_NODE_DISPOSITION_FINAL.csv').open(encoding='utf-8-sig')))
    assert len(nodes) == len({r['nodeid'] for r in nodes}) == 4568
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(nodes[0]))
    writer.writeheader(); writer.writerows(nodes)
    write('03_TEST_MATRIX_全量节点与定向验证.csv', buf.getvalue())
    items = [
        ('AUDIT-FOCUS-SOURCE-IDENTITY-R4', 'OPEN_CROSS_CUTTING', '其它重放生产者和 HTTP/联合 Head 尚需独立接受', '源映射反例、实际源 oracle、全部相关消费者'),
        ('S1-HTTP-JOINT', 'OPEN_ENGINEERING', '新候选默认 HTTP/联合 Head 尚未完整发布读回', '相同 T0/token；实际 PG 来源；联合回滚'),
        ('S2-DENOMINATOR', 'NOT_ENTERED', '4568/245 保留；额外148与当前155差异未复审', '逐节点/模块规范与动态可达证据；冻结唯一集合'),
        ('ALL-PG-CONSUMERS', 'OPEN_ENGINEERING', '本轮 Journal 不能代替全部入口', '真实 HTTP/desktop/worker/恢复；零非 PG 意图'),
        ('EXACT-56', 'OPEN_ENGINEERING', '170 条实际路径不能代替56类', '每类实际调用、输入、输出和数值反例'),
        ('FEP-87A', 'OPEN_ENGINEERING', '本轮仅 Focus 谓词范围', '全部规范原子和字段语义'),
        ('UI-CAPACITY', 'OPEN_ENGINEERING', '本轮未重跑六入口和容量', '浏览器证据、内容一致、批准阈值'),
        ('FINAL-CLEAN', 'NOT_RUN', '未执行完整合法冻结节点集', '相同冻结源码与 clean PG 完整命令/JUnit'),
        ('EXTERNAL', 'PENDING_INDEPENDENT_ACCEPTANCE', '开发者不能代替外审', '外部精确版本签收'),
        ('REAL-SESSION-MATURITY', 'PENDING_REAL_FACTS', '不能用重构赋予 PIT/成熟', '真实首获/H21/OOS/各 horizon'),
        ('PRODUCTION', 'PENDING_PERMISSION', '未授权正式切换', '明确维护窗口/正式角色/回滚')]
    buf = io.StringIO(); writer = csv.writer(buf); writer.writerow(['item', 'status', 'evidence_or_gap', 'acceptance'])
    writer.writerows(items); write('04_OPEN_ITEMS_未闭环事项.csv', buf.getvalue())
    write('06_EVIDENCE_INDEX.json', json.dumps(dict(contract='R4_LOCAL_DELIVERY_INDEX_V1', files=records, full_engineering_pass=False), indent=2, ensure_ascii=False) + '\n')
    files = sorted(p for p in DEST.rglob('*') if p.is_file())
    manifest = dict(contract='R4_LOCAL_DELIVERY_SHA256_V1', git_head=head, status='ENGINEERING_INCOMPLETE', exclusions=['05_SOURCE_MANIFEST_SHA256.json (self-reference)', 'V4_R4_R3_FINAL_DELIVERY.zip (archive itself)'], source_files={name: sha(ROOT / name) for name in source_names}, files=[dict(path=p.relative_to(DEST).as_posix(), bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    write('05_SOURCE_MANIFEST_SHA256.json', json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    files = sorted(p for p in DEST.rglob('*') if p.is_file())
    archive = DEST / 'V4_R4_R3_FINAL_DELIVERY.zip'
    temp = archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipout:
        for path in files:
            zipout.write(path, path.relative_to(DEST).as_posix())
    with zipfile.ZipFile(temp) as zipin:
        assert zipin.testzip() is None
        assert set(zipin.namelist()) == {p.relative_to(DEST).as_posix() for p in files}
        for item in manifest['files']:
            assert hashlib.sha256(zipin.read(item['path'])).hexdigest() == item['sha256']
    os.replace(temp, archive)
    print(json.dumps(dict(directory=str(DEST), zip=str(archive), bytes=archive.stat().st_size, sha256=sha(archive), included_files=len(files), git_head=head, status='ENGINEERING_INCOMPLETE'), ensure_ascii=False))


if __name__ == '__main__':
    main()
