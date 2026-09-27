from __future__ import annotations

"""Bind the R3 rule registry to captured official exchange sources."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "data/v4/source_evidence/v4_02_r3"
OUT = ROOT / "config/v4_02_price_limit_rules_r3.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


SOURCES = {
    "SSE_2023": {
        "source_ref": "https://www.sse.com.cn/lawandrules/sselawsrules2025/repeal/rules/c/c_20250612_10824490.shtml",
        "source_capture_path": "data/v4/source_evidence/v4_02_r3/sse_2023_trade_rule.html",
        "clauses": ["2023年修订交易规则发布、生效版本", "涨跌幅限制价格以前收盘价为基准", "A股最小价格变动单位与规则取整"],
    },
    "SSE_2026": {
        "source_ref": "https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml",
        "source_capture_path": "data/v4/source_evidence/v4_02_r3/sse_2026_rule.html",
        "clauses": ["主板通常涨跌幅10%", "科创板通常涨跌幅20%", "涨跌幅价以前收盘价为基准"],
    },
    "SSE_MAIN_RISK_2026": {
        "source_ref": "https://star.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20260424_10816474.shtml",
        "source_capture_path": "data/v4/source_evidence/v4_02_r3/sse_star_2026_notice.html",
        "clauses": ["上交所主板风险警示股票比例变更及生效日期2026-07-06"],
    },
    "SSE_STAR": {
        "source_ref": "https://star.sse.com.cn/star/media/news/c/c_20190719_4866789.shtml",
        "source_capture_path": "data/v4/source_evidence/v4_02_r3/sse_star_2019_qa.html",
        "clauses": ["科创板上市交易价格限制规则说明"],
    },
    "SZSE_2023": {
        "source_ref": "https://www.szse.cn/lawrules/rule/repeal/rules/t20230217_598773.html",
        "source_capture_path": "data/v4/source_evidence/v4_02_r3/szse_2023_trade_rule_notice.html",
        "clauses": ["2023年修订交易规则发布通知及附件指引", "主板通常涨跌幅10%", "创业板通常涨跌幅20%", "涨跌幅限制价格以前收盘价为基准"],
        "attachment_capture_note": "官方通知可访问；所链接2023规则PDF在本次定向捕获时返回404，保留官方通知与2026规则修订本作为可复核来源。",
    },
    "SZSE_2026": {
        "source_ref": "https://www.szse.cn/lawrules/service/member/t20260630_621404.html",
        "source_capture_path": "data/v4/source_evidence/v4_02_r3/szse_2026_st_notice.html",
        "clauses": ["深交所主板风险警示股票比例自2026-07-06调整为10%"],
    },
}


def source_for(rule_id: str) -> str:
    if rule_id.startswith("SSE_MAIN_RISK_20260706"):
        return "SSE_MAIN_RISK_2026"
    if rule_id.startswith("SSE_MAIN"):
        return "SSE_2023"
    if rule_id.startswith("SSE_STAR_RISK"):
        return "SSE_2026"
    if rule_id.startswith("SSE_STAR"):
        return "SSE_STAR"
    if rule_id.startswith("SZSE_MAIN_RISK_20260706"):
        return "SZSE_2026"
    return "SZSE_2023"


def main() -> None:
    source = json.loads((ROOT / "config/v4_02_price_limit_rules_v1.json").read_text(encoding="utf-8"))
    captures = {}
    for source_id, evidence in SOURCES.items():
        path = ROOT / evidence["source_capture_path"]
        if not path.exists():
            raise SystemExit(f"OFFICIAL_RULE_CAPTURE_MISSING:{source_id}")
        captures[source_id] = {**evidence, "source_capture_sha256": sha(path), "source_capture_bytes": path.stat().st_size}
    normalized = []
    for original in source["rules"]:
        rule = dict(original)
        source_id = source_for(rule["rule_id"])
        evidence = captures[source_id]
        clause_map = {"source_id": source_id, "rule_id": rule["rule_id"], "clauses": evidence["clauses"],
                      "effective_from": rule["valid_from"], "effective_to": rule["valid_to"],
                      "exchange": rule["exchange"], "board": rule["board"], "risk_status": rule["risk_status"],
                      "limit_ratio": rule["limit_ratio"], "rounding": rule["rounding_mode"], "tick": rule["tick"]}
        clause_hash = canonical_sha(clause_map)
        rule.update({"source_ref": evidence["source_ref"], "source_capture_path": evidence["source_capture_path"],
                     "source_capture_sha256": evidence["source_capture_sha256"],
                     "clause_mapping_sha256": clause_hash, "source_sha256": clause_hash,
                     "source_evidence_id": source_id})
        normalized.append(rule)
    result = {"contract_id": "PRICE_LIMIT_RULE_R3", "version": "3.0.0", "scope": source["scope"],
              "source_evidence": {"captures": captures, "rounding": source["source_evidence"]["rounding"],
                                  "normalization": "source_ref + source_capture_path + source_capture_sha256 + clause_mapping_sha256"},
              "rules": normalized,
              "acceptance": {"historical_limit_output_is_diagnostic_non_pit": True,
                             "missing_or_unavailable_source_capture_fails_closed": True}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=OUT.name + ".", suffix=".tmp", dir=OUT.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, OUT)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(json.dumps({"path": str(OUT.relative_to(ROOT)), "sha256": sha(OUT), "sources": len(captures),
                      "rules": len(normalized)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
