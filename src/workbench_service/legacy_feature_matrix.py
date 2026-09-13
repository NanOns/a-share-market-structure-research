"""Versioned P10-01 map for retained legacy workbench capabilities.

The matrix is deliberately a pure, read-only registry.  It does not inspect
the database and it does not infer runtime data availability.  Runtime
availability remains the responsibility of the linked API/page contracts.
"""

from __future__ import annotations

from urllib.parse import urlencode


CONTRACT_ID = "v3-p10-legacy-feature-matrix-v1.0"
SPEC_SECTION = "V3 §2、§18.13 P10-01、§20.3–§20.8"


def _route(path: str, publication_id: str = "", trade_date: str = "", **extra: str) -> str:
    params = {}
    if publication_id:
        params["publication_id"] = publication_id
    if trade_date:
        params["trade_date"] = trade_date
    params.update({key: value for key, value in extra.items() if value})
    return f"{path}?{urlencode(params)}" if params else path


def _row(
    feature_id: str,
    feature: str,
    decision: str,
    status: str,
    new_label: str,
    new_path: str,
    legacy_path: str,
    legacy_apis: tuple[str, ...],
    evidence_path: str | None,
    note: str,
    *,
    history_path: str | None = None,
) -> dict[str, object]:
    return {
        "feature_id": feature_id,
        "feature": feature,
        "decision": decision,
        "status": status,
        "new_entry": {"label": new_label, "path": new_path},
        "legacy_compatibility": {
            "path": legacy_path,
            "apis": list(legacy_apis),
            "history_path": history_path,
        },
        "evidence": {
            "kind": "QUERY_CONTRACT" if evidence_path else "EXPLICIT_DECISION",
            "path": evidence_path,
            "runtime_data_claim": False,
        },
        "note": note,
    }


def build_legacy_matrix(publication_id: str = "", trade_date: str = "") -> dict[str, object]:
    """Return the complete P10-01 matrix for an optional publication context."""

    publication_id = str(publication_id or "").strip()
    trade_date = str(trade_date or "").strip()
    v2_overview = _route("/v2", publication_id, trade_date, page="overview")
    v2_sectors = _route("/v2", publication_id, trade_date, page="sectors")
    v2_mainlines = _route("/v2", publication_id, trade_date, page="sectors", subpage="mainlines")
    v2_stocks = _route("/v2", publication_id, trade_date, page="stocks")
    v2_linkage = _route("/v2", publication_id, trade_date, page="linkage")
    v2_market = _route("/v2", publication_id, trade_date, page="market")
    v3 = _route("/v3", publication_id, trade_date)
    v3_events = _route("/v3/events", publication_id, trade_date)
    v3_online = _route("/v3/online", publication_id, trade_date)

    items = [
        _row(
            "LEGACY-01",
            "首页市场概况",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "V3 本地双轨研究",
            v3,
            v2_overview,
            ("/api/dashboard", "/api/market/cycle"),
            _route("/api/dashboard", publication_id, trade_date),
            "本地收盘概况与在线事件概况分源展示；在线不可用不阻断本地页面。",
        ),
        _row(
            "LEGACY-02",
            "首页强势板块",
            "REPLACE",
            "REPLACED_BY_V3_TRACKS",
            "CURRENT / POTENTIAL 双轨",
            v3,
            v2_sectors,
            ("/api/dashboard", "/api/sectors/cycle"),
            _route("/api/sectors/cycle", publication_id, trade_date, page="1", page_size="20", days="30"),
            "旧强势榜不再作为 V3 首页优先语义；旧页面和旧查询保留用于历史回看。",
        ),
        _row(
            "LEGACY-03",
            "首页优先研究",
            "REPLACE",
            "REPLACED_BY_V3_SHORTLISTS",
            "CURRENT_FOCUS / EARLY_FOCUS",
            v3,
            v2_overview,
            ("/api/candidates",),
            _route("/api/candidates", publication_id, trade_date, page="1", page_size="50"),
            "旧候选池退出 V3 首页优先清单，但不删除旧池或改变其 API31 语义。",
        ),
        _row(
            "LEGACY-04",
            "全板块",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "板块研究 / 全部板块",
            v3,
            v2_sectors,
            ("/api/sectors", "/api/sector-library"),
            _route("/api/sectors", publication_id, trade_date, page="1", page_size="20"),
            "全量列表不默认挤占 V3 首页；保留名称、类型和分页查询。",
        ),
        _row(
            "LEGACY-05",
            "板块周期矩阵",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "板块研究 / 周期矩阵",
            v2_sectors,
            v2_sectors,
            ("/api/sectors/cycle", "/api/sectors/{sector_id}/timeline"),
            _route("/api/sectors/cycle", publication_id, trade_date, page="1", page_size="20", days="30"),
            "5/10/20/30 日指标保持原义；双轨资格和失效标记不覆盖旧历史指标。",
            history_path=_route("/api/sectors/{sector_id}/timeline", publication_id, trade_date, days="30"),
        ),
        _row(
            "LEGACY-06",
            "主线周期",
            "RETAIN",
            "RELABLED_MEDIUM_TERM_BACKGROUND",
            "中期主线背景",
            v2_mainlines,
            v2_mainlines,
            ("/api/mainlines", "/api/mainlines/{sector_id}/evidence"),
            _route("/api/mainlines", publication_id, trade_date, page="1", page_size="20", days="30"),
            "主线是中期背景，不作为 CURRENT/POTENTIAL 必需资格；证据查询继续可达。",
            history_path=_route("/api/mainlines/{sector_id}/evidence", publication_id, trade_date, days="30"),
        ),
        _row(
            "LEGACY-07",
            "成员留存与龙头更替",
            "RETAIN",
            "RELABLED_HISTORICAL_MEMBER_VIEW",
            "原结构强成员 / 历史代表",
            v3,
            v2_sectors,
            ("/api/sectors/{sector_id}/members/history", "/api/sectors/{sector_id}/leader-history"),
            _route("/api/sectors/{sector_id}/members/history", publication_id, trade_date, days="10", page="1", page_size="50"),
            "历史成员和代表不冒充当日领涨成员；两类来源在页面和计数中分开。",
            history_path=_route("/api/sectors/{sector_id}/leader-history", publication_id, trade_date, days="30"),
        ),
        _row(
            "LEGACY-08",
            "板块—个股联动",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "V3 板块/个股详情",
            v3,
            v2_linkage,
            ("/api/linkage", "/api/linkage/history", "/api/stocks/{security_id}/sector-associations"),
            _route("/api/linkage", publication_id, trade_date, page="1", page_size="50"),
            "旧 API 保持兼容；V3 详情从已选板块或个股进入，集合筛选增强属于 P10-02。",
        ),
        _row(
            "LEGACY-09",
            "板块属性库与交集/并集/排除",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "联动 / 属性库",
            v2_linkage,
            v2_linkage,
            ("/api/sector-library", "/api/sector-intersection/query"),
            _route("/api/sector-library", publication_id, trade_date, page="1", page_size="50"),
            "属性和集合能力保留；名称选择 2–4 板块及角色过滤不在 P10-01 提前关闭。",
        ),
        _row(
            "LEGACY-10",
            "五类结构",
            "RETAIN",
            "RELABLED_STRUCTURAL_EVIDENCE",
            "全部结构候选 / 结构证据",
            v2_overview,
            v2_overview,
            ("/api/candidates", "/api/queues", "/api/evidence"),
            _route("/api/candidates", publication_id, trade_date, page="1", page_size="50"),
            "五类算法和历史等级保留；CORE 只表示结构含义，不替代当日重点资格。",
        ),
        _row(
            "LEGACY-11",
            "新高 / RPS / MA / 量额 / 换手",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "个股研究 / 技术状态",
            v2_stocks,
            v2_stocks,
            ("/api/stocks/technical", "/api/stocks/new-highs", "/api/stocks/{security_id}/technical-history"),
            _route("/api/stocks/technical", publication_id, trade_date, page="1", page_size="50"),
            "新高窗口、MA、RPS 和量额筛选保留；换手只有在可靠流通股本/来源可用时展示。",
            history_path=_route("/api/stocks/{security_id}/technical-history", publication_id, trade_date, days="20"),
        ),
        _row(
            "LEGACY-12",
            "个股证据与透视",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "V3 个股详情 / 证据",
            v3,
            v2_stocks,
            ("/api/stocks/{security_id}/insight", "/api/evidence"),
            _route("/api/stocks/{security_id}/insight", publication_id, trade_date, days="20"),
            "详情按选择、风险、板块、技术和在线分组；旧抽屉/证据查询继续可达。",
        ),
        _row(
            "LEGACY-13",
            "本地涨停 / 连板 / 晋级",
            "RETAIN",
            "LOCAL_ESTIMATE_EXPLICIT_SWITCH",
            "事件页 / 本地收盘估算",
            v3_events,
            v2_market,
            ("/api/limit-ladder", "/api/limit-ladder/promotion-history"),
            _route("/api/limit-ladder", publication_id, trade_date, page="1", page_size="50"),
            "本地链保留为估算/历史切换；在线事实不可用时不静默补零或冒充在线。",
            history_path=_route("/api/limit-ladder/promotion-history", publication_id, trade_date, days="30"),
        ),
        _row(
            "LEGACY-14",
            "最强题材 / 涨停分布 / 简图 / 速览",
            "RETAIN",
            "ONLINE_V3_PRODUCT_ENTRY",
            "在线事件页",
            v3_events,
            v2_market,
            ("/api/v3/events/overview", "/api/v3/events/distribution", "/api/v3/events/ladder"),
            _route("/api/v3/events/overview", publication_id, trade_date),
            "P09 在线事件为独立来源事实；本地估算和在线结果分源、分日期。",
        ),
        _row(
            "LEGACY-15",
            "人气热榜",
            "RETAIN",
            "REQUEST_TIME_ONLY",
            "在线总览 / 热榜",
            v3_online,
            v2_market,
            ("/api/hot-rankings", "/api/v3/hot-rankings"),
            _route("/api/v3/hot-rankings", publication_id, trade_date, page="1", page_size="30"),
            "热榜只在请求时读取；不写 raw、row、batch 或历史快照，不参与本地研究持久化。",
        ),
        _row(
            "LEGACY-16",
            "板块精选",
            "REPLACE",
            "REPLACED_BY_CURRENT_POTENTIAL",
            "CURRENT / POTENTIAL 叠加在线证据",
            v3,
            v2_sectors,
            ("/api/dashboard", "/api/sectors/cycle"),
            _route("/api/sectors/cycle", publication_id, trade_date, page="1", page_size="20", days="30"),
            "不再新增第三套强势榜；本地主体双轨，在线事件仅作独立证据徽标。",
        ),
        _row(
            "LEGACY-17",
            "数据状态与运维",
            "RETAIN",
            "EVIDENCE_RETAINED",
            "数据能力 / 运维中心",
            "/operations",
            "/operations",
            ("/api/operations/status", "/api/operations/storage", "/api/operations/backups"),
            "/api/operations/status",
            "保留普通运维入口；维护页不占研究主导航，也不阻塞本地研究页。",
        ),
        _row(
            "LEGACY-18",
            "每日导出 / 登录会员 / 投资日历 / 外部软件跳转",
            "EXCLUDE",
            "EXPLICITLY_EXCLUDED",
            "V3 本版不提供",
            "",
            "",
            (),
            None,
            "用户取舍和 V3 §20.3 明确排除；不做空壳入口、不生成隐含依赖。",
        ),
        _row(
            "LEGACY-19",
            "龙虎榜 / 新闻原因",
            "DEFER",
            "EXPLICITLY_DEFERRED",
            "V3 后置能力",
            "",
            "",
            (),
            None,
            "仅在后续有独立需求和来源证据时单独立项；缺失不由热榜或题材名称伪造。",
        ),
    ]
    return {
        "api_contract": CONTRACT_ID,
        "spec_section": SPEC_SECTION,
        "status": "AVAILABLE",
        "publication_id": publication_id or None,
        "trade_date": trade_date or None,
        "total": len(items),
        "items": items,
        "storage": {
            "database_written": False,
            "tdx_modified": False,
            "runtime_data_claim": False,
        },
        "acceptance": {
            "all_rows_have_decision": all(item["decision"] for item in items),
            "all_rows_have_status": all(item["status"] for item in items),
            "all_rows_have_evidence_or_explicit_decision": all(item["evidence"]["path"] or item["decision"] in {"EXCLUDE", "DEFER"} for item in items),
            "historical_routes_are_context_bound": bool(publication_id) == bool(trade_date),
        },
    }
