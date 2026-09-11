"""Write an atomic M10 legacy-proxy versus formal amount-A diff preview."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/market_research.duckdb"
REPORT_DIR = ROOT / "reports/upgrade_m10"


def _finite(value: object) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _latest_snapshot(connection: duckdb.DuckDBPyConnection) -> tuple[str, str, str, str]:
    row = connection.execute(
        """
        select pas.snapshot_id, cast(s.cutoff_date as varchar), s.config_hash, s.manifest_hash
          from publication_analysis_snapshots pas
          join publication_heads h on h.publication_id=pas.publication_id
          join analysis_snapshots s on s.snapshot_id=pas.snapshot_id
         where pas.domain='LOCAL_RECONSTRUCTED'
         order by h.trade_date desc, s.created_at desc
         limit 1
        """
    ).fetchone()
    if not row:
        raise RuntimeError("M10_AMOUNT_DIFF_SNAPSHOT_MISSING")
    return str(row[0]), str(row[1]), str(row[2]), str(row[3])


def build_report() -> Path:
    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        snapshot_id, cutoff, config_hash, manifest_hash = _latest_snapshot(connection)
        frame = connection.execute(
            """
            select c.sector_id, cast(c.trade_date as varchar) as trade_date,
                   c.amount_vs_prior20 as legacy_proxy,
                   c.member_amount_ratio_median_vs_prior20 as diagnostic_median,
                   c.sector_amount_vs_prior20 as formal_a,
                   c.total_member_count as legacy_target_members,
                   c.amount_target_member_count as formal_target_members,
                   c.amount_valid_count as legacy_valid_amount_members,
                   c.amount_comparable_member_count as formal_comparable_members,
                   c.amount_comparable_coverage as formal_current_coverage,
                   c.amount_window_coverage as formal_window_coverage,
                   c.amount_quality_codes as formal_quality_codes,
                   c.amount_basis, c.amount_contract_id,
                   c.amount_member_set_hash, c.amount_membership_snapshot_id
              from analysis_snapshot_entries e
              join sector_cycle_daily c on c.slice_id=e.slice_id and c.trade_date=e.trade_date
             where e.snapshot_id=? and e.domain='sector_cycle'
             order by c.trade_date, c.sector_id
            """,
            [snapshot_id],
        ).fetchdf()

    if frame.empty:
        raise RuntimeError("M10_AMOUNT_DIFF_SECTOR_CYCLE_EMPTY")
    frame["delta_formal_minus_legacy"] = frame.apply(
        lambda row: float(row.formal_a) - float(row.legacy_proxy)
        if _finite(row.formal_a) and _finite(row.legacy_proxy)
        else None,
        axis=1,
    )
    frame["member_count_delta_formal_minus_legacy_target"] = frame.apply(
        lambda row: int(row.formal_target_members) - int(row.legacy_target_members)
        if _finite(row.formal_target_members) and _finite(row.legacy_target_members)
        else None,
        axis=1,
    )
    formal_known = frame["formal_a"].map(_finite)
    legacy_known = frame["legacy_proxy"].map(_finite)
    both = formal_known & legacy_known
    quality_known = frame["formal_quality_codes"].notna()
    summary = {
        "snapshot_id": snapshot_id,
        "cutoff_date": cutoff,
        "config_hash": config_hash,
        "manifest_hash": manifest_hash,
        "row_count": int(len(frame)),
        "formal_a_known_count": int(formal_known.sum()),
        "legacy_proxy_known_count": int(legacy_known.sum()),
        "both_known_count": int(both.sum()),
        "formal_a_unknown_count": int((~formal_known).sum()),
        "formal_quality_present_count": int(quality_known.sum()),
        "formal_contract_ids": sorted({str(value) for value in frame["amount_contract_id"].dropna().unique()}),
        "formal_basis": sorted({str(value) for value in frame["amount_basis"].dropna().unique()}),
    }
    comparable = frame.loc[both, "delta_formal_minus_legacy"].dropna()
    summary.update(
        {
            "mean_formal_minus_legacy": float(comparable.mean()) if not comparable.empty else None,
            "max_abs_formal_minus_legacy": float(comparable.abs().max()) if not comparable.empty else None,
            "formal_member_count_mean": float(frame["formal_comparable_members"].dropna().mean()) if frame["formal_comparable_members"].notna().any() else None,
            "legacy_valid_amount_member_count_mean": float(frame["legacy_valid_amount_members"].dropna().mean()) if frame["legacy_valid_amount_members"].notna().any() else None,
        }
    )
    sample = frame.loc[both].copy()
    sample["abs_delta"] = sample["delta_formal_minus_legacy"].abs()
    sample = sample.sort_values(["abs_delta", "sector_id"], ascending=[False, True], kind="mergesort").head(20)

    lines = [
        "# M10 金额 A 新旧差异预览",
        "",
        f"- 生成时间：`{datetime.now(timezone.utc).isoformat()}`",
        f"- 分析快照：`{snapshot_id}`",
        f"- 截止日期：`{cutoff}`",
        f"- 快照配置哈希：`{config_hash}`",
        f"- 清单哈希：`{manifest_hash}`",
        f"- 正式合同：`{', '.join(summary['formal_contract_ids']) or 'NULL'}`",
        "",
        "## 1. 结果摘要",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
    ]
    labels = {
        "row_count": "板块日记录",
        "formal_a_known_count": "正式 A 已知",
        "legacy_proxy_known_count": "旧代理已知",
        "both_known_count": "新旧均已知",
        "formal_a_unknown_count": "正式 A 未知",
        "formal_quality_present_count": "含正式质量码",
        "mean_formal_minus_legacy": "新 A - 旧代理均值",
        "max_abs_formal_minus_legacy": "新 A - 旧代理最大绝对差",
        "formal_member_count_mean": "正式可比成员数均值",
        "legacy_valid_amount_member_count_mean": "旧有效金额成员数均值",
    }
    for key, label in labels.items():
        value = summary.get(key)
        lines.append(f"| {label} | `{value if value is not None else 'NULL'}` |")
    lines.extend(
        [
            "",
            "## 2. 差异解释",
            "",
            "- 公式差：旧 `legacy_proxy` 是成员金额比值中位数；新 `formal_a` 是同一共同成员集合 U 的板块金额合计除以 U 过去 20 个主交易日合计均值。",
            "- 成员差：正式 A 的 U 必须在 H21 的 21 个主交易日金额均已知且合格；新加入成员、缺行、质量失败成员保留在目标分母但不进入 U。",
            "- 质量差：正式 A 额外保存当前覆盖率、窗口覆盖率、质量码和固定成员快照；任何质量门失败时正式 A 为 NULL，旧代理值不作为回退。",
            "- 本报告只描述口径差异，不用差异大小调整 1.10/1.20 阈值，也不构成收益或概率结论。",
            "",
            "## 3. 绝对差最大的并排样例",
            "",
            "| 交易日 | 板块 | 旧代理 | 正式 A | 新-旧 | 正式可比成员 | 正式当前覆盖 | 质量码 |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in sample.itertuples(index=False):
        quality = str(row.formal_quality_codes or "[]").replace("|", "\\|")
        values = [
            row.trade_date,
            row.sector_id,
            f"{row.legacy_proxy:.6f}",
            f"{row.formal_a:.6f}",
            f"{row.delta_formal_minus_legacy:.6f}",
            str(int(row.formal_comparable_members)) if _finite(row.formal_comparable_members) else "NULL",
            f"{row.formal_current_coverage:.3f}" if _finite(row.formal_current_coverage) else "NULL",
            quality,
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "## 4. 复核入口",
            "",
            "- 原始正式字段：`sector_cycle_daily.sector_amount_vs_prior20`。",
            "- 旧兼容字段：`sector_cycle_daily.amount_vs_prior20`，仅按旧代理解释。",
            "- 主线消费字段：`mainline_daily.current_sector_amount_vs_prior20`；v2.4 不读取旧 `current_amount_vs_prior20`。",
            "- 公式、质量门、窗口和必测样例：`docs/M10_AMOUNT_A_DESIGN_DECISION_V1.md` 与 `docs/M10_MAINLINE_STATE_CONTRACT_V2_4_PREVIEW.md`。",
            "",
            "## 5. 机器摘要",
            "",
            "```json",
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
        ]
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = REPORT_DIR / f"M10_AMOUNT_A_NEW_OLD_DIFF_PREVIEW_{cutoff.replace('-', '')}.md"
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(output)
    return output


if __name__ == "__main__":
    print(build_report())
