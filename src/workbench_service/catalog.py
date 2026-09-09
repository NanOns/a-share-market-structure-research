"""Stable field and enum mappings for the workbench public API."""

from __future__ import annotations

from copy import deepcopy

API_CONTRACT = "workbench-api-v2.1"
CATALOG_VERSION = "workbench-field-catalog-v1.0"


def _field(field_id: str, label: str, kind: str, unit: str, nullable: bool,
           description: str, sort_supported: bool = False) -> dict:
    return {
        "field_id": field_id,
        "label": label,
        "type": kind,
        "unit": unit,
        "nullable": nullable,
        "description": description,
        "sort_supported": sort_supported,
    }


FIELD_CATALOG = (
    _field("api_contract", "接口合同", "string", "", False, "响应所遵循的公共接口合同版本"),
    _field("catalog_version", "目录版本", "string", "", False, "字段与枚举目录版本"),
    _field("publication_id", "发布版本", "string", "", False, "成功发布的稳定标识", True),
    _field("trade_date", "交易日期", "date", "日期", False, "当前数据对应的实际交易日", True),
    _field("cutoff_date", "截止日期", "date", "日期", True, "所选发布或分析的可观测截止日期", True),
    _field("revision", "发布修订号", "integer", "", True, "同一交易日内的发布修订号", True),
    _field("production_version", "生产版本", "string", "", True, "生成该发布的生产版本标识"),
    _field("source_revision_id", "输入修订号", "integer", "", True, "冻结输入的源修订标识", True),
    _field("analysis_snapshot_id", "分析快照", "string", "", True, "历史分析快照标识；未生成时为空"),
    _field("analysis_capabilities", "分析能力", "object", "", False, "API01按域返回的分析能力状态"),
    _field("capabilities", "能力状态", "object", "", False, "API02按域返回的能力状态"),
    _field("contracts", "关联合同", "object", "", False, "API02绑定的范围、报价、语义及发布合同"),
    _field("data_quality", "数据质量", "object", "", False, "公共响应的质量状态、代码及覆盖摘要"),
    _field("security_id", "股票代码", "string", "", False, "统一证券标识，格式为市场前缀加代码", True),
    _field("security_name", "股票名称", "string", "", True, "本地发布中的证券名称", True),
    _field("name", "名称", "string", "", True, "DTO通用名称字段；由具体对象解释", True),
    _field("quote_date", "报价日期", "date", "日期", False, "原始报价所属交易日", True),
    _field("quote_state", "报价状态", "enum", "", False, "报价是否有可验证的当日原始值"),
    _field("latest_price", "最新价", "number", "CNY/share", True, "兼容旧接口的原始收盘价显示字段", True),
    _field("raw_close", "原始收盘价", "number", "CNY/share", True, "未复权原始收盘价", True),
    _field("quote_ret1", "当日涨幅", "number", "fraction", True, "当前报价相对合同参考前收的简单收益", True),
    _field("RET1", "当日涨幅（兼容）", "number", "fraction", True, "旧接口兼容字段；与quote_ret1同源", True),
    _field("quote_prev_close", "参考前收", "number", "CNY/share", True, "计算当日涨幅使用的参考前收", True),
    _field("turnover_amount", "当日成交额", "number", "CNY", True, "原始成交额，不做价格口径调整", True),
    _field("amount", "成交额", "number", "CNY", True, "DTO标准成交额字段", True),
    _field("volume", "成交量", "number", "shares", True, "原始成交量", True),
    _field("last_known_price", "最近已知价", "number", "CNY/share", True, "仅在明确缺少当日报价时提供", True),
    _field("last_known_date", "最近已知日期", "date", "日期", True, "最近已知价对应日期", True),
    _field("validity", "技术有效性", "enum", "", True, "技术字段是否满足最小有效样本条件"),
    _field("quality_codes", "质量代码", "array", "", False, "数据不足、来源或覆盖情况的可解释代码"),
    _field("ma5", "5日均线", "number", "CNY/share", True, "同一价格基准下的5日均线", True),
    _field("ma10", "10日均线", "number", "CNY/share", True, "同一价格基准下的10日均线", True),
    _field("ma20", "20日均线", "number", "CNY/share", True, "同一价格基准下的20日均线", True),
    _field("ma60", "60日均线", "number", "CNY/share", True, "同一价格基准下的60日均线", True),
    _field("ma_alignment", "均线排列", "enum", "", True, "合同定义的均线排列状态"),
    _field("ret5", "5日涨幅", "number", "fraction", True, "5个有效观察的简单收益", True),
    _field("ret10", "10日涨幅", "number", "fraction", True, "10个有效观察的简单收益", True),
    _field("ret20", "20日涨幅", "number", "fraction", True, "20个有效观察的简单收益", True),
    _field("ret60", "60日涨幅", "number", "fraction", True, "60个有效观察的简单收益", True),
    _field("rps5", "5日相对强弱", "number", "fraction", True, "5日横截面相对强弱值", True),
    _field("rps10", "10日相对强弱", "number", "fraction", True, "10日横截面相对强弱值", True),
    _field("rps20", "20日相对强弱", "number", "fraction", True, "20日横截面相对强弱值", True),
    _field("rps60", "60日相对强弱", "number", "fraction", True, "60日横截面相对强弱值", True),
    _field("turnover_rate", "换手率", "number", "fraction", True, "仅来源可验证时提供", True),
    _field("sector_id", "板块代码", "string", "", True, "本地板块稳定标识", True),
    _field("sector_name", "板块名称", "string", "", True, "发布中的板块名称", True),
    _field("sector_type", "板块类型", "enum", "", True, "行业、主题或风格等受控类型"),
    _field("semantic_bucket", "语义桶", "enum", "", True, "正常属性、价格驱动、事件驱动或状态标签"),
    _field("total_member_count", "成员数", "integer", "stocks", True, "当前发布范围内的板块成员数", True),
    _field("quote_valid_count", "有效报价数", "integer", "stocks", True, "有有效当日报价的成员数", True),
    _field("factor_valid_count", "有效因子数", "integer", "stocks", True, "满足对应因子最小覆盖的成员数", True),
    _field("member_ret1_median", "成员当日涨幅中位数", "number", "fraction", True, "有效成员当日涨幅中位数", True),
    _field("member_amount_sum", "成员成交额合计", "number", "CNY", True, "有效成员原始成交额合计", True),
    _field("rs20_pct", "板块20日相对强弱分位", "number", "fraction", True, "板块横截面相对强弱分位", True),
    _field("display_rank", "显示排名", "integer", "rank", True, "当前页面显示排名", True),
    _field("queue_name", "结构队列", "enum", "", False, "规范化结构队列名称", True),
    _field("hit", "结构命中", "boolean", "", False, "是否满足该队列的结构合同"),
    _field("tier", "队列层级", "enum", "", True, "CORE或SUPPORTED等合同层级"),
    _field("queue_rank", "队内名次", "integer", "rank", True, "未过滤完整队列中的合同名次", True),
    _field("research_band", "研究带", "enum", "", False, "研究优先带，不是交易信号"),
    _field("primary_pattern", "主结构模式", "string", "", True, "确定性规则产生的主要结构模式"),
    _field("v1_grade", "原版等级", "enum", "", True, "兼容旧发布的研究优先等级"),
    _field("association_rank", "关联排名", "integer", "rank", True, "股票与板块关联的合同排名", True),
    _field("member_rank", "板块内名次", "integer", "rank", True, "股票在所属板块内的合同名次", True),
    _field("rank_valid_count", "排名有效数", "integer", "stocks", True, "参与该排名的有效成员数", True),
    _field("eligible", "关联有效", "boolean", "", False, "是否满足关联合同的资格条件"),
    _field("reason_codes", "原因代码", "array", "", False, "关联拒绝或降级原因代码"),
    _field("contract_id", "字段合同", "string", "", False, "产生该字段的版本化合同标识"),
    _field("evidence_id", "证据标识", "string", "", True, "按需展开证据的稳定标识"),
    _field("source_refs", "来源引用", "array", "", True, "证据对应的本地来源引用"),
)

ENUM_CATALOG = {
    "capability": {
        "AVAILABLE": "可用",
        "PARTIAL": "部分可用",
        "UNAVAILABLE": "来源不可用",
        "NOT_BUILT": "尚未生成",
    },
    "quote_state": {
        "VALID": "有效报价",
        "VALID_DEGRADED": "有效但口径降级",
        "MISSING_PREVIOUS_CLOSE": "缺少参考前收",
        "UNKNOWN_CORPORATE_ACTION": "公司行为未确定",
        "MISSING": "缺少当日报价",
    },
    "queue_name": {
        "STEADY_QUEUE": "稳健趋势队列",
        "PULLBACK_QUEUE": "强势回撤队列",
        "BREAKOUT_QUEUE": "突破准备队列",
        "LEADER_QUEUE": "板块龙头队列",
        "EARLY_QUEUE": "早期启动队列",
    },
    "research_band": {
        "CORE_RESEARCH": "核心观察",
        "SUPPORTED_RESEARCH": "一般观察",
        "DIAGNOSTIC_ONLY": "诊断观察",
    },
    "sector_type": {
        "INDUSTRY": "行业板块",
        "THEME": "概念板块",
        "STYLE": "风格板块",
        "OTHER": "其他板块",
    },
    "semantic_bucket": {
        "NORMAL_ATTRIBUTE": "正常属性",
        "PRICE_DRIVEN": "价格驱动标签",
        "EVENT_DRIVEN": "事件驱动标签",
        "STATUS_LABEL": "状态标签",
    },
    "tier": {"CORE": "核心层", "SUPPORTED": "支持层"},
    "validity": {"VALID": "有效", "PARTIAL": "部分有效", "INSUFFICIENT": "数据不足"},
}


def field_catalog(api_contract: str = API_CONTRACT, language: str = "zh-CN") -> dict:
    if api_contract != API_CONTRACT:
        raise ValueError("UNSUPPORTED_API_CONTRACT")
    if language != "zh-CN":
        raise ValueError("LANGUAGE_UNSUPPORTED")
    return {
        "api_contract": API_CONTRACT,
        "catalog_version": CATALOG_VERSION,
        "language": language,
        "items": deepcopy(list(FIELD_CATALOG)),
        "enums": deepcopy(ENUM_CATALOG),
    }
