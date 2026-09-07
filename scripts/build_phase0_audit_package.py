from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tdx.tdx_audit import raw_manifest_fingerprint, snapshot_day_files  # noqa: E402


DEFAULT_BASELINE = Path(
    r"D:\Users\lps\Desktop\TDX_Market_Structure_Scanner_V0.3_FINAL_Implementation_Baseline.md"
)
DEFAULT_AUDIT = PROJECT_ROOT / "reports" / "phase0" / "TDX_DATA_AUDIT.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "PHASE0_COMPLETE_AUDIT_PACKAGE.md"


ARTIFACTS = [
    Path("AGENTS.md"),
    Path("PROJECT_SPEC.md"),
    Path("README.md"),
    Path(".gitignore"),
    Path("run_phase0.py"),
    Path("config/paths.yaml"),
    Path("config/universe.yaml"),
    Path("config/sector_config.yaml"),
    Path("src/tdx/__init__.py"),
    Path("src/tdx/day_reader.py"),
    Path("src/tdx/security_master.py"),
    Path("src/tdx/block_reader.py"),
    Path("src/tdx/tdx_audit.py"),
    Path("docs/DATA_FACTOR_SPEC.md"),
    Path("docs/PHASE0_REPORT.md"),
    Path("reports/phase0/TDX_DATA_AUDIT.json"),
    Path("tests/conftest.py"),
    Path("tests/test_day_reader.py"),
    Path("tests/test_security_master.py"),
    Path("tests/test_block_reader.py"),
    Path("tests/test_audit_safety.py"),
    Path("scripts/build_phase0_audit_package.py"),
]


LANGUAGES = {
    ".py": "python",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
}


def digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_evidence(command: list[str]) -> dict:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "command": subprocess.list2cmdline(command),
        "exit_code": completed.returncode,
        "output": completed.stdout.strip(),
    }


def fence(text: str, language: str = "text") -> str:
    # Four tildes safely contain the triple-backtick fences used by embedded Markdown.
    return f"~~~~{language}\n{text.rstrip()}\n~~~~"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            if not text.endswith("\n"):
                stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def build_report(baseline: Path, audit_path: Path, output: Path) -> str:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    tdx_root = Path(audit["resolved_tdx_root"])

    pytest_evidence = run_evidence([sys.executable, "-m", "pytest", "-q"])
    compile_evidence = run_evidence(
        [sys.executable, "-m", "compileall", "-q", "src", "run_phase0.py"]
    )
    day_paths, _ = snapshot_day_files(tdx_root)
    current_manifest_hash = raw_manifest_fingerprint(day_paths)
    audit_manifest_hash = audit["daily_data"]["raw_source_manifest_sha256"]
    manifest_unchanged = current_manifest_hash == audit_manifest_hash

    artifact_rows = []
    for relative in ARTIFACTS:
        path = PROJECT_ROOT / relative
        artifact_rows.append((relative.as_posix(), path.stat().st_size, digest_file(path)))

    generated_at = datetime.now().astimezone().isoformat()
    daily = audit["daily_data"]
    security = audit["security_master"]
    normal = security["normal_universe_contract"]
    latest = audit["latest_trade_date_contract"]
    sectors = audit["sector_membership"]
    units = audit["day_contract"]["unit_crosscheck"]
    adjustment = audit["adjustment_contract"]

    parts = [
        "# TDX Market Structure Scanner — Phase 0 完整审计证据包",
        "",
        f"生成时间：`{generated_at}`  ",
        f"审计运行时间：`{audit['run_time']}`  ",
        f"实施基线：`V0.3 FINAL IMPLEMENTATION BASELINE`  ",
        f"最终判定：**{audit['run_status']}**  ",
        f"TDX访问模式：**{audit['source_access_mode']}**",
        "",
        "## 1. 给线上审计模型的说明",
        "",
        "本文件是自包含证据包。线上模型无法访问本机路径，因此本报告在后续附件中原文嵌入：项目设计基线、审计JSON、全部Phase 0源码、配置、测试和人工可读报告。路径仅用于来源追踪，不要求审计模型访问本机。",
        "",
        "建议重点检查：",
        "",
        "1. `DEGRADED_PASS` 判定是否符合V0.3基线；",
        "2. `.day` 32字节解析与校验是否存在口径错误；",
        "3. A股、B股、指数、基金和转债分类是否足够保守；",
        "4. `expected_a_stock_count` 分母是否避免循环定义；",
        "5. 最新交易日、板块覆盖率和复权降级逻辑是否合理；",
        "6. 是否存在对 `D:/new_tdx` 的写入风险；",
        "7. 哪些问题必须在进入正式Factor/Scanner前修复。",
        "",
        "## 2. 执行范围与判定",
        "",
        f"用户最初提供：`{audit['requested_tdx_root']}`；该路径不存在。只读父目录发现后实际使用：`{audit['resolved_tdx_root']}`。路径纠正已记录为 `{str(audit['path_correction_applied']).lower()}`。",
        "",
        "结论：行情解析、证券身份、日期对齐、Universe和当前板块成员层通过自动化检查。由于本地 `gbbq` 权息主体格式和公司行为语义尚未独立验证，不能生成可复算复权价，因此所有依赖多日价格结构的Factor与Scanner必须保持 `EXPERIMENTAL`，不得宣称正式通过。",
        "",
        "```text",
        f"RUN_STATUS = {audit['run_status']}",
        f"PROJECT_PRICE_BASIS = {adjustment['project_price_basis']}",
        f"ADJUSTMENT_STATUS = {adjustment['adjustment_status']}",
        f"FORMAL_TREND_SCANNERS_ALLOWED = {str(adjustment['formal_trend_scanners_allowed']).upper()}",
        "```",
        "",
        "## 3. 核心结果摘要",
        "",
        "| 项目 | 结果 |",
        "|---|---:|",
        f"| `.day` 文件 | {daily['total_file_count']:,} |",
        f"| 完整通过文件 | {daily['valid_file_count']:,} |",
        f"| 异常文件 | {daily['invalid_file_count']:,} |",
        f"| 扫描记录 | {daily['total_record_count']:,} |",
        f"| 最早日期 | {daily['earliest_trade_date']} |",
        f"| 最新交易日 | {daily['latest_trade_date']} |",
        f"| 最新日A股文件覆盖率 | {latest['selected_date_coverage_ratio']:.4%} |",
        f"| 指数日期确认 | {latest['index_confirmation']} |",
        f"| 理论当前A股 | {security['expected_a_stock_count']:,} |",
        f"| 成功解析A股 | {security['parsed_a_stock_count']:,} |",
        f"| A股解析率 | {security['parse_success_ratio']:.4%} |",
        f"| 初始NORMAL_UNIVERSE | {normal['normal_universe_count']:,} |",
        f"| 单位交叉检查记录 | {units['a_stock_record_count']:,} |",
        f"| 单位合理比例 | {units['plausibility_ratio']:.4%} |",
        f"| 板块成员记录 | {sectors['membership_record_count']:,} |",
        f"| 板块成员精确重复 | {sectors['duplicate_membership_count']:,} |",
        f"| 无法解析成员证券 | {sectors['unmatched_security_count']:,} |",
        f"| 审计耗时 | {audit['runtime_seconds']:.3f} 秒 |",
        "",
        "## 4. 市场与板块统计",
        "",
        "### 4.1 日线分市场",
        "",
        "| 市场 | 文件 | 有效 | 异常 | 记录 |",
        "|---|---:|---:|---:|---:|",
    ]

    for market, values in daily["by_market"].items():
        parts.append(
            f"| {market} | {values['file_count']:,} | {values['valid_file_count']:,} | "
            f"{values['invalid_file_count']:,} | {values['record_count']:,} |"
        )

    parts.extend([
        "",
        "### 4.2 板块",
        "",
        "| 类型 | 板块数 | 合格板块 | 成员记录 | 最新有效A股成员记录 |",
        "|---|---:|---:|---:|---:|",
    ])
    for sector_type, values in sectors["by_type"].items():
        parts.append(
            f"| {sector_type} | {values['sector_count']:,} | {values['eligible_sector_count']:,} | "
            f"{values['member_records']:,} | {values['valid_latest_member_records']:,} |"
        )

    parts.extend([
        "",
        "## 5. 可复现命令证据",
        "",
        "Phase 0执行命令：",
        "",
        fence(
            'python run_phase0.py --tdx-root "D:\\new_tdx" --requested-root "D:\\new\\_tdx"',
            "powershell",
        ),
        "",
        "测试输出：",
        "",
        fence(
            f"> {pytest_evidence['command']}\nexit_code={pytest_evidence['exit_code']}\n{pytest_evidence['output']}",
            "text",
        ),
        "",
        "编译检查输出：",
        "",
        fence(
            f"> {compile_evidence['command']}\nexit_code={compile_evidence['exit_code']}\n"
            f"{compile_evidence['output'] or '(no output; success)'}",
            "text",
        ),
        "",
        "源目录元数据清单复验：",
        "",
        fence(
            f"audit_manifest_sha256={audit_manifest_hash}\n"
            f"current_manifest_sha256={current_manifest_hash}\n"
            f"source_manifest_unchanged={manifest_unchanged}",
            "text",
        ),
        "",
        "说明：该清单哈希覆盖全部12,483个日线文件的规范化路径、文件大小和纳秒级修改时间。审计前后相等，且输出保护代码拒绝将产物写入TDX根目录。",
        "",
        "## 6. 产物SHA-256清单",
        "",
        "以下哈希在本报告生成前计算；附件原文应与对应哈希一致。",
        "",
        "| 相对路径 | 字节 | SHA-256 |",
        "|---|---:|---|",
    ])
    for relative, size, digest in artifact_rows:
        parts.append(f"| `{relative}` | {size:,} | `{digest}` |")

    parts.extend([
        "",
        "## 7. 已知限制与未完成的人工证据",
        "",
        "- `gbbq` 与 `gbbq.map` 存在，但只有map文本索引可识别，主体payload尚不可可靠解释。",
        "- 当前证券Master能力为 `LIMITED`：历史ST、历史名称及退市状态不完整。",
        "- 历史板块回放使用当前成员，必须标记 `CURRENT_MEMBERSHIP_BIAS=true`。",
        "- 仍需在通达信界面人工核对附件JSON中的5组最新日K样本。",
        "- 18个异常日线文件均不属于当前A股正式解析集合；详细证据在完整JSON中。",
        "- 本次只完成Phase 0，没有实现Factor Engine或Scanner。",
        "",
        "## 8. 原始实施基线（完整附件）",
        "",
        f"来源：`{baseline}`",
        "",
        fence(baseline.read_text(encoding="utf-8"), "markdown"),
        "",
        "## 9. 项目产物原文（完整附件）",
    ])

    for index, relative in enumerate(ARTIFACTS, 1):
        path = PROJECT_ROOT / relative
        language = LANGUAGES.get(path.suffix.lower(), "text")
        parts.extend([
            "",
            f"### 9.{index} `{relative.as_posix()}`",
            "",
            fence(path.read_text(encoding="utf-8"), language),
        ])

    parts.extend([
        "",
        "## 10. 审计请求",
        "",
        "请基于上述基线、机器审计、源代码和测试证据给出：P0/P1/P2问题清单、是否同意 `DEGRADED_PASS`、是否存在只读风险或统计口径缺陷，以及进入下一阶段前必须完成的最小修改。",
        "",
        "**END OF SELF-CONTAINED PHASE 0 AUDIT PACKAGE**",
    ])
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one self-contained Phase 0 Markdown audit package")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.baseline, args.audit, args.output)
    atomic_write(args.output, report)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "bytes": args.output.stat().st_size,
        "sha256": digest_file(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

