(function () {
    /* Contract probes retain these compact call signatures: identity(publication.publication_id,true) JSON.stringify(identity,null,2) */
    'use strict';
    var api = window.WorkbenchV2Api, format = window.WorkbenchV2Format, table = window.WorkbenchV2Table,
        modal = window.WorkbenchV2Modal, router = window.WorkbenchV2Router, initialRoute = router.read();
    var select = document.getElementById('publication-select'), notice = document.getElementById('notice'),
        context = document.getElementById('page-context'), tableTarget = document.getElementById('context-table'),
        overview = document.getElementById('overview-page'), technicalPage = document.getElementById('technical-page'),
        sectorsPage = document.getElementById('sectors-page'), mainlinePage = document.getElementById('mainlines-page'),
        linkagePage = document.getElementById('linkage-page'), marketPage = document.getElementById('market-page'),
        dataInfoPage = document.getElementById('data-info-page'), current = null,
        currentPage = initialRoute.page, sectorSubpage = initialRoute.subpage;
    var technicalState = {
        mode: 'highs',
        page: 1,
        pageSize: 50,
        window: 20,
        rpsMin: '',
        streakMin: '',
        maState: '',
        amountClass: '',
        researchBand: ''
    };
    var sectorState = {days: 10, type: 'INDUSTRY', query: ''};
    var limitLadderState = {page: 1, pageSize: 50};
    var hotRankState = {page: 1, pageSize: 20, source: 'ALL'};
    var overviewState = {page: 1, pageSize: 50, q: '', grade: '', pattern: '', requestId: 0};
    var mainlineState = {className: '', days: 30, historyPolicy: null};
    var linkageState = {mode: 'attributes', page: 1, days: 10, attributeType: '', attributeBucket: '', attributeQuery: '', sectorId: '', securityId: '', stockQuery: '', tradeDate: '', includeSectors: '', operator: 'INTERSECTION', excludeSectors: '', selectionCollapsed: false};
    var insightRequestId = 0, insightAbortController = null, insightRouteActive = false, openingInsight = false,
        modalRequestId = 0, modalAbortController = null;
    var viewRequests = {};
    function beginViewRequest(key) {
        var previous = viewRequests[key];
        if (previous && previous.controller) previous.controller.abort();
        var controller = typeof AbortController === 'function' ? new AbortController() : null;
        var token = {epoch: previous ? previous.epoch + 1 : 1, controller: controller, signal: controller && controller.signal};
        viewRequests[key] = token;
        return token;
    }
    function viewRequestActive(key, token) { return viewRequests[key] === token; }
    function cancelHiddenViewRequests(page, subpage) {
        var active = page === 'overview' ? ['overview'] : page === 'market' ? ['market', 'limit', 'hot'] : page === 'stocks' ? ['technical'] : page === 'linkage' ? ['linkage'] : page === 'sectors' ? [subpage === 'mainlines' ? 'mainlines' : 'sectors'] : [];
        Object.keys(viewRequests).forEach(function (key) {
            if (active.indexOf(key) < 0 && viewRequests[key] && viewRequests[key].controller) viewRequests[key].controller.abort();
        });
    }
    var insightTabs = {overview: true, history: true, evidence: true};
    function normalizeInsightTab(value) { return insightTabs[value] ? value : 'overview'; }
    function normalizeInsightDays(value) {
        var days = Number(value);
        if (!Number.isFinite(days)) return 20;
        return Math.max(1, Math.min(250, Math.round(days)));
    }
    function readInsightRoute() {
        var params = new URLSearchParams(window.location.search), securityId = params.get('security_id');
        if (!securityId) return null;
        return {publication_id: params.get('publication_id') || '', security_id: securityId, tab: normalizeInsightTab(params.get('tab')), days: normalizeInsightDays(params.get('days'))};
    }
    function writeInsightRoute(route, mode) {
        var url = new URL(window.location.href);
        if (route) {
            url.searchParams.set('publication_id', route.publication_id || (current && current.publication_id) || '');
            url.searchParams.set('security_id', route.security_id);
            url.searchParams.set('tab', normalizeInsightTab(route.tab));
            url.searchParams.set('days', String(normalizeInsightDays(route.days)));
        } else {
            url.searchParams.delete('security_id');
            url.searchParams.delete('tab');
            url.searchParams.delete('days');
        }
        (mode === 'push' ? window.history.pushState.bind(window.history) : window.history.replaceState.bind(window.history))({}, '', url.toString());
    }
    function cancelInsightRequest() {
        if (insightAbortController) { insightAbortController.abort(); insightAbortController = null; }
    }
    function cancelModalRequest() {
        if (modalAbortController) { modalAbortController.abort(); modalAbortController = null; }
        modalRequestId += 1;
    }
    function beginModalRequest() {
        if (modalAbortController) modalAbortController.abort();
        var controller = typeof AbortController === 'function' ? new AbortController() : null;
        var token = {id: ++modalRequestId, controller: controller, signal: controller && controller.signal};
        modalAbortController = controller;
        return token;
    }
    function modalRequestActive(token) { return token && token.id === modalRequestId; }
    function releaseModalRequest(token) {
        if (modalRequestActive(token)) modalAbortController = null;
    }
    function clearInsightRoute() {
        insightRouteActive = false;
        writeInsightRoute(null, 'replace');
    }
    modal.onClose(function () {
        cancelModalRequest();
        insightRequestId += 1;
        cancelInsightRequest();
        if (insightRouteActive && !openingInsight) clearInsightRoute();
    });
    var labels = {
        security_id: '股票代码',
        security_name: '股票名称',
        trade_date: '交易日',
        publication_id: '发布版本',
        snapshot_id: '分析快照',
        price_basis: '价格口径',
        history_basis: '历史基础',
        source_identity_sha256: '输入文件摘要',
        source_manifest_sha256: '输入清单摘要',
        api_contract: '接口合同',
        contract: '合同版本',
        status: '状态',
        basis: '分析基础',
        rps_capability: 'RPS能力',
        rps_valid_universe_count20: 'RPS20有效样本（全市场分母）',
        research_band: '研究级别',
        research_band_quality: '研究级别质量',
        quality_codes: '数据质量',
        strength_quality_codes: '强弱质量',
        member_ret20_median: '成员20日收益中位数',
        member_ret1_median: '成员当日收益中位数',
        breadth_ret1: '成员上涨比例',
        coverage: '覆盖率',
        rank: '板块名次',
        sector_rs20_pct: '板块RPS20百分位',
        board_quote_source: '板块行情来源',
        member_present: '是否在板',
        strong_state: '是否强势',
        member_change_kind: '成员变化',
        candidate_id: '候选代表',
        confirmed_id: '已确认代表',
        candidate_streak: '候选连续天数',
        confirmation_event: '确认事件',
        hierarchy_level: '板块层级',
        parent_sector_name: '上级板块',
        limit_state: '涨跌停状态',
        ladder_level: '梯队层级',
        promotion_state: '晋级状态',
        previous_level: '前一日层级'
    };
    var enums = {
        VALID: '正常',
        PARTIAL: '部分可用',
        INSUFFICIENT: '资料不足',
        DATA_INSUFFICIENT: '资料不足',
        INSUFFICIENT_HISTORY: '历史不足',
        AVAILABLE: '可用',
        NOT_BUILT: '尚未构建',
        RECONSTRUCTED: '本地重建',
        LOCAL_RECONSTRUCTED: '本地重建',
        CORE_RESEARCH: '核心研究',
        SUPPORTED_RESEARCH: '支持观察',
        DIAGNOSTIC_ONLY: '诊断参考',
        FADING: '退潮',
        HIGH_LEVEL_CONTRACTION: '高位收缩',
        REACCELERATING: '再加速',
        SUSTAINED: '持续',
        NEW: '新晋',
        BROADENING: '扩散',
        INDUSTRY: '行业',
        THEME: '概念',
        REGION: '地区',
        STYLE: '通达信风格标签',
        NORMAL_STYLE: '通达信风格标签',
        TRUE: '是',
        FALSE: '否',
        UNKNOWN: '待确认',
        INITIAL_CONFIRMATION: '初次确认',
        ADDED: '新增成员',
        REMOVED: '移除成员',
        RETAINED: '继续强势',
        ENTERED: '进入强势',
        EXITED: '退出强势',
        UNCHANGED: '保持不变',
        BULLISH: '多头排列',
        BEARISH: '空头排列',
        MIXED: '混合排列',
        NORMAL: '正常',
        INCREASED: '放量',
        NOTABLE: '显著放量',
        SIGNIFICANT: '大幅放量',
        OK: '正常',
        CALCULATED: '已计算',
        CORE: '核心',
        SUPPORTED: '支持',
        STEADY_QUEUE: '稳健趋势队列',
        PULLBACK_QUEUE: '强势回撤队列',
        BREAKOUT_QUEUE: '突破准备队列',
        LEADER_QUEUE: '板块领先队列',
        EARLY_QUEUE: '早期启动队列',
        UP: '涨停',
        DOWN: '跌停',
        NONE: '未涨跌停',
        NO_LIMIT: '无涨跌幅限制',
        SUSPENDED: '停牌',
        NOT_EVALUATED: '未评估',
        NOT_ELIGIBLE: '未晋级',
        SUCCESS: '晋级',
        FOURPLUS: '4板及以上',
        OUTSIDE_V1_STEADY_TREND: '未满足稳健趋势条件',
        OUTSIDE_V1_STRONG_PULLBACK: '未满足强势回撤条件',
        OUTSIDE_V1_BREAKOUT_PREP: '未满足突破准备条件',
        OUTSIDE_V1_SECTOR_LEADER: '未满足板块领先条件',
        OUTSIDE_V1_EARLY_MOVER: '未满足早期启动条件'
    };

    function setText(id, value) {
        document.getElementById(id).textContent = value === undefined || value === null || value === '' ? '—' : String(value);
    }

    function first(obj, keys) {
        for (var i = 0; i < keys.length; i++) if (obj && obj[keys[i]] !== undefined && obj[keys[i]] !== null) return obj[keys[i]];
        return null;
    }

    function display(value, digits) {
        if (value === undefined || value === null || value === '') return '—';
        if (typeof value === 'boolean') return value ? '是' : '否';
        if (typeof value === 'number' && Number.isFinite(value)) return format.number(value, digits === undefined ? 2 : digits);
        var key = String(value);
        return enums[key] || enums[key.toUpperCase()] || key;
    }

    function percent(value) {
        return value === undefined || value === null ? '—' : format.percent(Number(value) * 100);
    }

    function fieldLabel(key) {
        return labels[key] || String(key).replace(/_/g, ' ');
    }

    function securityLabel(row) {
        var name = row && row.security_name;
        var id = row && row.security_id;
        return name ? String(name) + '（' + String(id || '') + '）' : display(id);
    }

    function band(row) {
        var value = first(row, ['research_band', 'shadow_research_band']);
        return value === undefined || value === null || value === '' ? '暂无' : display(value);
    }

    function quality(row) {
        var codes = [];
        (row && row.quality_codes || []).forEach(function (x) {
            codes.push(display(x));
        });
        (row && row.strength_quality_codes || []).forEach(function (x) {
            codes.push(display(x));
        });
        return codes.length ? codes.join('、') : '正常';
    }

    function setNotice(message, error) {
        notice.className = error ? 'notice error' : 'notice';
        notice.textContent = message + (error ? '' : ' · ' + new Date().toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        }));
    }

    function publicationRows(items) {
        return items.map(function (item) {
            var option = document.createElement('option');
            option.value = item.publication_id;
            option.textContent = item.trade_date + ' · ' + item.publication_id;
            return option;
        });
    }

    function renderContext(publication, identity, universe) {
        var rows = [{label: '交易日期', value: publication.trade_date, contract: '发布头'}, {
            label: '发布身份',
            value: publication.publication_id,
            contract: first(identity, ['api_contract', 'contract']) || '工作台接口'
        }, {
            label: '股票范围',
            value: universeDescription(universe),
            contract: 'A 股范围合同'
        }, {label: '语义注册表', value: 'workbench-semantic-v2.1', contract: 'sector_semantics.yaml'}];
        table.render(tableTarget, [{label: '上下文', key: 'label'}, {
            label: '当前值',
            key: 'value'
        }, {label: '合同/来源', key: 'contract'}], rows);
    }

    function overviewEmpty(targetId, message) {
        var target = document.getElementById(targetId); target.replaceChildren();
        var empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = message; target.appendChild(empty);
    }

    function overviewValue(card) {
        if (card.value === null || card.value === undefined || card.value === '') return '暂无';
        if (card.unit === 'percent') return percent(card.value);
        if (card.unit === 'count') return display(card.value, 0);
        return display(card.value, 2);
    }

    function renderOverviewMarket(summary) {
        var target = document.getElementById('overview-market-cards'); target.replaceChildren();
        if (!summary || summary.status !== 'AVAILABLE') { overviewEmpty('overview-market-cards', '市场摘要暂不可用；当前不会用空数据替代市场统计。'); return; }
        (summary.cards || []).forEach(function (card) {
            var button = document.createElement('button'); button.type = 'button'; button.className = 'overview-market-card';
            button.addEventListener('click', function () { showPage(card.target === 'technical' ? 'stocks' : 'market'); });
            var label = document.createElement('span'); label.className = 'overview-card-label'; label.textContent = card.label || card.id;
            var value = document.createElement('strong'); value.className = 'overview-card-value'; value.textContent = overviewValue(card);
            var hint = document.createElement('span'); hint.className = 'overview-card-hint'; hint.textContent = '查看' + (card.target === 'technical' ? '个股技术' : '市场周期');
            button.append(label, value, hint); target.appendChild(button);
        });
    }

    function openOverviewSector(row) {
        sectorState.type = row.sector_type === 'THEME' ? 'THEME' : 'INDUSTRY'; sectorState.query = row.sector_id || '';
        var query = document.getElementById('sector-query'); if (query) query.value = sectorState.query; showPage('sectors');
    }

    function renderOverviewSectors(groups) {
        var target = document.getElementById('overview-sector-groups'); target.replaceChildren();
        ['INDUSTRY', 'THEME'].forEach(function (key) {
            var group = groups && groups[key], section = document.createElement('section'); section.className = 'overview-sector-group';
            var heading = document.createElement('h3'); heading.textContent = group && group.label ? group.label : key; section.appendChild(heading);
            if (group && group.items && group.items.length) {
                var tableTarget = document.createElement('div'); section.appendChild(tableTarget);
                table.render(tableTarget, [
                    {label: '板块', key: 'sector_name'}, {label: 'RPS20百分位', value: function (row) { return percent(row.sector_rs20_pct); }},
                    {label: '当日成员中位收益', value: function (row) { return percent(row.member_ret1_median); }},
                    {label: '成员成交额', value: function (row) { return amountOrDash(row.member_amount_sum); }},
                    {label: '覆盖率', value: function (row) { return percent(row.coverage); }},
                    {label: '查看', action: {label: '进入板块', onClick: openOverviewSector}}
                ], group.items);
            } else {
                var empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = group && group.status === 'UNAVAILABLE' ? 'M9 板块快照尚未生成。' : '该分组暂无可用板块。'; section.appendChild(empty);
            }
            target.appendChild(section);
        });
    }

    function renderOverviewMainlines(data) {
        var target = document.getElementById('overview-mainline-counts'); target.replaceChildren();
        if (!data || data.status !== 'AVAILABLE') { overviewEmpty('overview-mainline-counts', 'M10 主线快照尚未生成；当前不会用板块排名临时替代主线分类。'); return; }
        Object.keys(data.counts || {}).forEach(function (key) {
            var button = document.createElement('button'); button.type = 'button'; button.className = 'overview-mainline-card';
            button.addEventListener('click', function () { mainlineState.className = key; document.getElementById('mainline-class').value = key; showPage('sectors', {subpage: 'mainlines'}); });
            var label = document.createElement('span'); label.className = 'overview-card-label'; label.textContent = mainlineClassText(key);
            var value = document.createElement('strong'); value.className = 'overview-card-value'; value.textContent = display(data.counts[key], 0);
            button.append(label, value); target.appendChild(button);
        });
    }

    function renderOverviewRepresentatives(data) {
        if (!data || data.status !== 'AVAILABLE') { overviewEmpty('overview-representatives', '代表股状态暂不可用；请先生成 M9 代表状态快照。'); return; }
        table.render(document.getElementById('overview-representatives'), [
            {label: '股票', value: securityLabel}, {label: '状态', value: function (row) { return display(row.representative_status); }},
            {label: '来源板块', value: function (row) { return (row.sector_sources || []).filter(function (source) { return String(source.sector_type || '').toUpperCase() !== 'STYLE' && String(source.sector_id || '').toUpperCase().indexOf('STYLE:') !== 0; }).map(function (source) { return source.sector_name; }).join('、') || '暂无'; }},
            {label: '候选连续天数', value: function (row) { return display(row.candidate_streak, 0); }},
            {label: '透视', action: {label: '打开', onClick: showStockInsight}}
        ], data.items || []);
    }

    function renderOverviewPriority(result) {
        var total = result.total || 0, pageSize = result.page_size || overviewState.pageSize, pages = Math.max(1, Math.ceil(total / pageSize));
        document.getElementById('overview-priority-page-label').textContent = '第 ' + result.page + ' 页 / 共 ' + pages + ' 页 · ' + total + ' 条';
        document.getElementById('overview-priority-prev').disabled = result.page <= 1; document.getElementById('overview-priority-next').disabled = result.page >= pages;
        table.render(document.getElementById('overview-priority-table'), [
            {label: '股票', value: securityLabel}, {label: '最新价', value: function (row) { return valueOrDash(row.latest_price); }},
            {label: '当日涨幅', value: function (row) { return percent(first(row, ['RET1', 'quote_ret1'])); }},
            {label: '成交额', value: function (row) { return amountOrDash(first(row, ['turnover_amount', 'raw_amount'])); }},
            {label: '主要结构', value: function (row) { return display(row.primary_pattern || row.effective_pattern); }},
            {label: '研究带', value: band}, {label: '强势关联', value: function (row) { return row.strength_sector_name || row.best_sector_name || '暂无'; }},
            {label: '透视', action: {label: '打开', onClick: showStockInsight}}
        ], result.items || []);
    }

    function loadOverviewAnalysis() {
        if (!current) return;
        var token = beginViewRequest('overview'), requestId = ++overviewState.requestId;
        overviewState.q = (document.getElementById('overview-priority-q').value || '').trim();
        overviewState.grade = document.getElementById('overview-priority-grade').value;
        overviewState.pattern = document.getElementById('overview-priority-pattern').value;
        document.getElementById('overview-analysis-basis').textContent = '正在读取当前发布版本的 API30/API31…';
        api.dashboard({publication_id: current.publication_id, include_analysis: '1', basis: 'RECONSTRUCTED'}, {signal: token.signal}).then(function (result) {
            if (requestId !== overviewState.requestId || !viewRequestActive('overview', token)) return;
            var item = result.item || {}; renderOverviewMarket(item.market_summary); renderOverviewSectors(item.strong_sectors); renderOverviewMainlines(item.mainline_counts); renderOverviewRepresentatives(item.representatives);
            document.getElementById('overview-analysis-basis').textContent = '快照 ' + display(item.snapshot_id || result.snapshot_id) + ' · ' + display(item.resolved_basis || result.resolved_basis) + ' · 截止 ' + display(item.trade_date || result.trade_date) + ' · 首页数据按能力独立降级。';
        }).catch(function (error) {
            if (requestId !== overviewState.requestId || !viewRequestActive('overview', token) || error.name === 'AbortError') return;
            ['overview-market-cards', 'overview-sector-groups', 'overview-mainline-counts', 'overview-representatives'].forEach(function (id) { overviewEmpty(id, '首页分析暂不可用：' + error.message); });
            document.getElementById('overview-analysis-basis').textContent = '当前发布版本未提供 API30 分析快照：' + error.message;
        });
        api.candidates({publication_id: current.publication_id, page: overviewState.page, page_size: overviewState.pageSize, q: overviewState.q, grade: overviewState.grade, pattern: overviewState.pattern, include_analysis: '1', basis: 'RECONSTRUCTED'}, {signal: token.signal}).then(function (result) {
            if (requestId !== overviewState.requestId || !viewRequestActive('overview', token)) return; renderOverviewPriority(result);
        }).catch(function (error) {
            if (requestId !== overviewState.requestId || !viewRequestActive('overview', token) || error.name === 'AbortError') return;
            overviewEmpty('overview-priority-table', '优先研究暂不可用：' + error.message); document.getElementById('overview-priority-prev').disabled = true; document.getElementById('overview-priority-next').disabled = true;
        });
    }

    function modalTable(columns, rows) {
        var wrap = document.createElement('div');
        if (!rows || !rows.length) {
            wrap.className = 'modal-empty';
            wrap.textContent = '暂无可展示数据';
            return wrap;
        }
        var target = document.createElement('table');
        target.className = 'modal-data';
        var head = document.createElement('tr');
        columns.forEach(function (column) {
            var th = document.createElement('th');
            th.textContent = column.label;
            head.appendChild(th);
        });
        var thead = document.createElement('thead');
        thead.appendChild(head);
        target.appendChild(thead);
        var tbody = document.createElement('tbody');
        rows.forEach(function (row) {
            var tr = document.createElement('tr');
            columns.forEach(function (column) {
                var td = document.createElement('td');
                var value = column.value ? column.value(row) : row[column.key];
                td.textContent = value === undefined || value === null || value === '' ? '—' : String(value);
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        target.appendChild(tbody);
        wrap.appendChild(target);
        return wrap;
    }

    function modalContent(intro, sections) {
        var wrap = document.createElement('div');
        var p = document.createElement('p');
        p.className = 'modal-intro';
        p.textContent = intro;
        wrap.appendChild(p);
        (sections || []).forEach(function (section) {
            var block = document.createElement('section');
            block.className = 'modal-section';
            var h = document.createElement('h3');
            h.textContent = section.title;
            block.appendChild(h);
            if (section.type === 'table') {
                block.appendChild(modalTable(section.columns, section.rows));
            } else {
                var t = document.createElement('table');
                t.className = 'modal-kv';
                (section.rows || []).forEach(function (row) {
                    var tr = document.createElement('tr');
                    var th = document.createElement('th');
                    th.textContent = row.label;
                    var td = document.createElement('td');
                    td.textContent = display(row.value);
                    tr.append(th, td);
                    t.appendChild(tr);
                });
                block.appendChild(t);
            }
            wrap.appendChild(block);
        });
        return wrap;
    }

    var buildModalContent = modalContent;
    modalContent = function (intro, sections) {
        var order = {'代表状态': 0, '成员状态（最多显示80条）': 1, '板块周期': 2};
        var ordered = (sections || []).slice().sort(function (a, b) {
            return (order[a.title] === undefined ? 99 : order[a.title]) - (order[b.title] === undefined ? 99 : order[b.title]);
        });
        return buildModalContent(intro, ordered);
    };

    function flatten(value, prefix, rows, depth) {
        if (depth > 2) return;
        if (value && typeof value === 'object' && !Array.isArray(value)) {
            Object.keys(value).forEach(function (key) {
                flatten(value[key], prefix ? prefix + ' · ' + fieldLabel(key) : fieldLabel(key), rows, depth + 1);
            });
        } else {
            rows.push({label: prefix, value: Array.isArray(value) ? value.map(display).join('、') : value});
        }
    }

    function evidenceModal(title, intro, data) {
        var rows = [];
        flatten(data, '', rows, 0);
        modal.open(title, modalContent(intro, [{title: '可核对信息', rows: rows}]));
    }

    function valueOrDash(value) {
        return value === null || value === undefined ? '暂无' : display(value, 2);
    }

    function amountOrDash(value) {
        return format.amount(value);
    }

    function universeDescription(universe) {
        var scope = universe && universe.scope;
        if (scope && typeof scope === 'object') {
            var markets = Array.isArray(scope.markets) ? scope.markets.join(' / ') : '';
            return [markets, scope.security_type, displayScopeDescription(universe && universe.display_scope), statisticalScopeDescription(universe && universe.statistical_scope)].filter(Boolean).join(' · ') || '统一 A 股范围';
        }
        return [first(universe, ['classification_summary', 'universe_contract', 'contract_id']), displayScopeDescription(universe && universe.display_scope), statisticalScopeDescription(universe && universe.statistical_scope)].filter(Boolean).join(' · ') || '统一 A 股范围';
    }

    function displayScopeDescription(scope) {
        if (!scope || scope.show_star_stocks) return '展示范围含科创板和北交所';
        var prefixes = Array.isArray(scope.excluded_board_prefixes) ? scope.excluded_board_prefixes : [];
        var boards = [];
        if (prefixes.some(function (prefix) { return prefix.indexOf('SH.688') === 0 || prefix.indexOf('SH.689') === 0; })) boards.push('科创板');
        if (prefixes.some(function (prefix) { return prefix.indexOf('BJ.') === 0; })) boards.push('北交所');
        return boards.length ? '展示范围默认排除' + boards.join('和') + '；数据仍正常生成' : '展示范围按配置确定';
    }

    function statisticalScopeDescription(scope) {
        if (!scope) return '统计范围按配置确定';
        var prefixes = Array.isArray(scope.excluded_board_prefixes) ? scope.excluded_board_prefixes : [];
        var boards = [];
        if (scope.include_star_stocks) boards.push('科创板');
        if (scope.include_bj_stocks) boards.push('北交所');
        return boards.length ? '统计范围含' + boards.join('和') : '统计范围排除科创板和北交所';
    }

    function basisText(result) {
        return '数据已加载 · 截止 ' + display(result.as_of_trade_date) + ' · ' + display(result.snapshot_id) + ' · ' + display(result.basis) + ' · 当前表格只显示最新交易日；数值按终端习惯保留两位；NULL 保持 NULL。';
    }

    function historyRows(points, limit) {
        var all = points || [];
        var rows = [];
        all.forEach(function (point, index) {
            var close = first(point, ['adj_close', 'close']);
            var amount = first(point, ['amount_ratio20', 'AMOUNT_RATIO20']);
            var volumeRatio = first(point, ['volume_vs_prior20', 'VOLUME_VS_PRIOR20']);
            if (amount === null && index >= 19) {
                var amountWindow = all.slice(index - 19, index + 1).map(function (x) {
                    return Number(first(x, ['amount', 'turnover']));
                }).filter(Number.isFinite);
                var currentAmount = Number(first(point, ['amount', 'turnover']));
                if (amountWindow.length === 20 && Number.isFinite(currentAmount)) {
                    amount = currentAmount / (amountWindow.reduce(function (sum, x) {
                        return sum + x;
                    }, 0) / amountWindow.length);
                }
            }
            if (volumeRatio === null && index >= 20) {
                var volumeWindow = all.slice(index - 20, index).map(function (x) {
                    return Number(first(x, ['volume', 'vol']));
                }).filter(Number.isFinite);
                var currentVolume = Number(first(point, ['volume', 'vol']));
                if (volumeWindow.length === 20 && Number.isFinite(currentVolume)) {
                    volumeRatio = currentVolume / (volumeWindow.reduce(function (sum, x) {
                        return sum + x;
                    }, 0) / volumeWindow.length);
                }
            }
            var ret20 = first(point, ['ret20', 'RET20']);
            if (ret20 === null && index >= 20) {
                var priorClose = Number(first(all[index - 20], ['adj_close', 'close']));
                if (Number.isFinite(Number(close)) && Number.isFinite(priorClose) && priorClose !== 0) ret20 = Number(close) / priorClose - 1;
            }
            rows.push({
                trade_date: first(point, ['trade_date', 'date']),
                close: valueOrDash(close),
                ret20: ret20 === null || ret20 === undefined ? '暂无' : percent(ret20),
                ma5: valueOrDash(first(point, ['ma5', 'MA5'])),
                ma20: valueOrDash(first(point, ['ma20', 'MA20'])),
                ma60: valueOrDash(first(point, ['ma60', 'MA60'])),
                amount: valueOrDash(amount),
                volume: valueOrDash(volumeRatio),
                rps: point.rps20 === undefined ? valueOrDash(point.RPS20) : percent(point.rps20),
                quality: quality(point)
            });
        });
        return rows.slice(-(limit || 30)).reverse();
    }

    function structureHistoryRows(points, limit) {
        var all = points || [], dates = [], seen = Object.create(null), maxDays = limit || 30;
        for (var index = all.length - 1; index >= 0 && dates.length < maxDays; index--) {
            var date = all[index] && all[index].trade_date;
            if (date !== undefined && date !== null && !seen[date]) {
                seen[date] = true;
                dates.push(String(date));
            }
        }
        var allowed = Object.create(null);
        dates.forEach(function (date) { allowed[date] = true; });
        return all.filter(function (item) { return item && allowed[String(item.trade_date)]; }).sort(function (left, right) {
            var dateOrder = String(right.trade_date).localeCompare(String(left.trade_date));
            return dateOrder || String(left.queue_name || '').localeCompare(String(right.queue_name || ''));
        });
    }

    function technicalParams() {
        var params = {
            publication_id: current.publication_id,
            page: technicalState.page,
            page_size: technicalState.pageSize,
            basis: 'AUTO',
            research_band: technicalState.researchBand
        };
        if (technicalState.mode === 'highs') {
            params.window = technicalState.window;
            params.rps_min = technicalState.rpsMin;
            params.streak_min = technicalState.streakMin;
        } else {
            params.ma_state = technicalState.maState;
            params.amount_class = technicalState.amountClass;
        }
        return params;
    }

    function showHistory(row) {
        modal.open('技术历史 · ' + securityLabel(row), '正在读取历史数据…');
        var token = beginModalRequest();
        api.technicalHistory({
            publication_id: current.publication_id,
            security_id: row.security_id,
            days: 60,
            price_basis: 'ADJUSTED',
            fields: 'ohlc,ma,amount,rps'
        }, {signal: token.signal}).then(function (result) {
            if (!modalRequestActive(token)) return;
            releaseModalRequest(token);
            var rows = historyRows(result.points || []);
            modal.open('技术历史 · ' + securityLabel(row), modalContent('历史用于观察状态延续与变化，不是自动买卖信号。价格口径：调整后；RET20、额比20和量比前20由历史序列按页面说明计算。', [{
                title: '历史数据（最近30个交易日）',
                type: 'table',
                columns: [{label: '交易日', key: 'trade_date'}, {label: '调整后收盘', key: 'close'}, {
                    label: 'RET20',
                    key: 'ret20'
                }, {label: 'MA5', key: 'ma5'}, {label: 'MA20', key: 'ma20'}, {
                    label: 'MA60',
                    key: 'ma60'
                }, {label: '额比20', key: 'amount'}, {label: '量比前20', key: 'volume'}, {
                    label: 'RPS20',
                    key: 'rps'
                }, {label: '质量', key: 'quality'}],
                rows: rows
            }, {
                title: '口径',
                rows: [{label: '股票', value: securityLabel(row)}, {
                    label: '分析快照',
                    value: result.snapshot_id
                }, {label: '历史基础', value: '本地重建'}, {label: 'RPS能力', value: display(result.rps_capability)}]
            }]));
        }).catch(function (error) {
            if (!modalRequestActive(token) || error.name === 'AbortError') return;
            releaseModalRequest(token);
            modal.open('技术历史 · ' + securityLabel(row), modalContent('历史数据暂时无法读取。', [{
                title: '原因',
                rows: [{label: '提示', value: error.message}]
            }]));
        });
    }

    function insightValue(value) {
        return value === null || value === undefined || value === '' ? '暂无' : display(value);
    }

    function insightTable(columns, rows) {
        return modalTable(columns, rows || []);
    }

    function insightTabButton(label, key, active, onClick) {
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'insight-tab' + (active ? ' active' : '');
        button.textContent = label;
        button.setAttribute('aria-selected', active ? 'true' : 'false');
        button.dataset.insightTab = key;
        button.addEventListener('click', onClick);
        return button;
    }

    function svgNode(name, attributes) {
        var node = document.createElementNS('http://www.w3.org/2000/svg', name);
        Object.keys(attributes || {}).forEach(function (key) { node.setAttribute(key, String(attributes[key])); });
        return node;
    }

    function chartNumber(value) {
        if (value === null || value === undefined || value === '') return null;
        var number = Number(value);
        return Number.isFinite(number) ? number : null;
    }

    function renderHistoryChart(technicalHistory) {
        var points = technicalHistory.points || [];
        var block = document.createElement('section');
        block.className = 'insight-chart-panel';
        var title = document.createElement('h3');
        title.textContent = '历史图表（同一日期锚）';
        block.appendChild(title);
        var note = document.createElement('p');
        note.className = 'insight-chart-note';
        note.textContent = '价格：ADJUSTED（' + display(technicalHistory.chart_basis || technicalHistory.price_basis) + '） · RPS/金额按同一交易日对齐；NULL 和历史缺口不补零。';
        block.appendChild(note);
        if (!points.length) {
            var empty = document.createElement('p');
            empty.className = 'empty';
            empty.textContent = '当前窗口没有可绘制的本地历史序列。';
            block.appendChild(empty);
            return block;
        }

        var width = 760, left = 62, right = 18, panelHeight = 112, panelGap = 22, top = 44;
        var height = top + panelHeight * 3 + panelGap * 2 + 26;
        var plotWidth = width - left - right;
        var svg = svgNode('svg', {class: 'insight-chart', viewBox: '0 0 ' + width + ' ' + height, role: 'img', 'aria-label': 'OHLC、均线、RPS20 和成交金额历史图表'});
        var finiteValues = function (key) { return points.map(function (point) { return chartNumber(point[key]); }).filter(function (value) { return value !== null; }); };
        var priceValues = ['low', 'high', 'open', 'close', 'ma5', 'ma10', 'ma20', 'ma60'].reduce(function (all, key) { return all.concat(finiteValues(key)); }, []);
        var priceMin = priceValues.length ? Math.min.apply(Math, priceValues) : 0;
        var priceMax = priceValues.length ? Math.max.apply(Math, priceValues) : 1;
        var pricePad = (priceMax - priceMin) * 0.08 || 1;
        priceMin -= pricePad;
        priceMax += pricePad;
        var amountValues = finiteValues('amount');
        var amountMax = amountValues.length ? Math.max.apply(Math, amountValues) : 1;
        var rpsValues = finiteValues('rps20');
        var rpsMin = rpsValues.length ? Math.min(0, Math.min.apply(Math, rpsValues)) : 0;
        var rpsMax = rpsValues.length ? Math.max(1, Math.max.apply(Math, rpsValues)) : 1;
        var x = function (index) { return left + (points.length === 1 ? plotWidth / 2 : plotWidth * index / (points.length - 1)); };
        var y = function (value, min, max, panelTop) { return panelTop + panelHeight - (value - min) / (max - min || 1) * panelHeight; };
        var drawText = function (text, xValue, yValue, attributes) {
            var textNode = svgNode('text', Object.assign({x: xValue, y: yValue}, attributes || {}));
            textNode.textContent = text;
            svg.appendChild(textNode);
        };
        var drawLine = function (key, min, max, panelTop, color, widthValue) {
            var segment = [];
            var flush = function () {
                if (segment.length > 1) svg.appendChild(svgNode('path', {d: 'M ' + segment.join(' L '), fill: 'none', stroke: color, 'stroke-width': widthValue || 1.7}));
                segment = [];
            };
            points.forEach(function (point, index) {
                var value = chartNumber(point[key]);
                if (value === null || point.gap) { flush(); return; }
                segment.push(x(index).toFixed(2) + ' ' + y(value, min, max, panelTop).toFixed(2));
            });
            flush();
        };
        var panel = function (panelTop, label, min, max, formatter) {
            svg.appendChild(svgNode('rect', {x: left, y: panelTop, width: plotWidth, height: panelHeight, class: 'chart-panel-bg'}));
            [0, 0.5, 1].forEach(function (fraction) {
                var lineY = panelTop + panelHeight * fraction;
                svg.appendChild(svgNode('line', {x1: left, y1: lineY, x2: width - right, y2: lineY, class: 'chart-grid-line'}));
                drawText(formatter(max - (max - min) * fraction), left - 8, lineY + 4, {class: 'chart-axis-label', 'text-anchor': 'end'});
            });
            drawText(label, 8, panelTop + 15, {class: 'chart-panel-label'});
        };
        var priceTop = top, amountTop = top + panelHeight + panelGap, rpsTop = amountTop + panelHeight + panelGap;
        panel(priceTop, 'OHLC + MA', priceMin, priceMax, function (value) { return display(value, 2); });
        panel(amountTop, '金额', 0, amountMax, function (value) { return format.amount(value); });
        panel(rpsTop, 'RPS20', rpsMin, rpsMax, function (value) { return percent(value); });
        points.forEach(function (point, index) {
            if (!point.gap) return;
            var gapX = points.length === 1 ? left : x(index) - plotWidth / Math.max(points.length - 1, 1) / 2;
            svg.appendChild(svgNode('rect', {x: gapX, y: priceTop, width: plotWidth / Math.max(points.length - 1, 1), height: panelHeight * 3 + panelGap * 2, class: 'chart-gap'}));
        });
        ['ma5', 'ma20', 'ma60'].forEach(function (key, index) { drawLine(key, priceMin, priceMax, priceTop, ['#2d8bd8', '#e07a35', '#7a5ab8'][index], 1.8); });
        points.forEach(function (point, index) {
            if (point.gap) return;
            var open = chartNumber(point.open), high = chartNumber(point.high), low = chartNumber(point.low), close = chartNumber(point.close);
            if (open === null || high === null || low === null || close === null) return;
            var candleX = x(index), candleColor = close >= open ? '#d34b4b' : '#2f8f68';
            svg.appendChild(svgNode('line', {x1: candleX, y1: y(high, priceMin, priceMax, priceTop), x2: candleX, y2: y(low, priceMin, priceMax, priceTop), stroke: candleColor, 'stroke-width': 1}));
            svg.appendChild(svgNode('rect', {x: candleX - 3, y: Math.min(y(open, priceMin, priceMax, priceTop), y(close, priceMin, priceMax, priceTop)), width: 6, height: Math.max(2, Math.abs(y(open, priceMin, priceMax, priceTop) - y(close, priceMin, priceMax, priceTop))), fill: candleColor, class: 'chart-candle'}));
            var amount = chartNumber(point.amount);
            if (amount !== null) svg.appendChild(svgNode('rect', {x: candleX - 3, y: y(amount, 0, amountMax, amountTop), width: 6, height: amountTop + panelHeight - y(amount, 0, amountMax, amountTop), class: 'chart-amount-bar'}));
        });
        drawLine('rps20', rpsMin, rpsMax, rpsTop, '#2d8bd8', 2);
        drawText('价格：ADJUSTED', left + 6, 18, {class: 'chart-legend chart-legend-adjusted'});
        drawText('MA5', left + 112, 18, {class: 'chart-legend chart-legend-ma5'});
        drawText('MA20', left + 155, 18, {class: 'chart-legend chart-legend-ma20'});
        drawText('MA60', left + 208, 18, {class: 'chart-legend chart-legend-ma60'});
        points.forEach(function (point, index) {
            if (index !== 0 && index !== points.length - 1 && index !== Math.floor(points.length / 2)) return;
            drawText(display(point.date || point.trade_date), x(index), height - 5, {class: 'chart-date-label', 'text-anchor': index === 0 ? 'start' : (index === points.length - 1 ? 'end' : 'middle')});
        });
        svg.appendChild(svgNode('line', {x1: left, y1: rpsTop + panelHeight, x2: width - right, y2: rpsTop + panelHeight, class: 'chart-axis-line'}));
        block.appendChild(svg);
        var gaps = technicalHistory.gaps || [];
        var gapNote = document.createElement('p');
        gapNote.className = 'insight-chart-note';
        gapNote.textContent = gaps.length ? '历史缺口：' + gaps.length + ' 处，图中以浅色区标识；RPS 的 NULL 仍按 NULL 显示。' : '历史缺口：无；RPS 的 NULL 仍按 NULL 显示。';
        block.appendChild(gapNote);
        return block;
    }

    function marketChartValue(value) {
        return chartNumber(value);
    }

    function marketChartText(value, kind) {
        if (value === null || value === undefined) return '暂无';
        if (kind === 'amount') return amountOrDash(value);
        if (kind === 'percent') return Number(value).toFixed(1) + '%';
        return String(Math.round(Number(value)));
    }

    function marketCoverage(point, prefix) {
        var above = marketChartValue(point[prefix + '_above_count']);
        var valid = marketChartValue(point[prefix + '_valid_count']);
        return above === null || valid === null || valid === 0 ? null : above * 100 / valid;
    }

    function marketNewHighValue(point, window) {
        var item = point.new_high_counts && point.new_high_counts[String(window)];
        return item ? marketChartValue(item.hit_count) : null;
    }

    function openMarketDetail(row) {
        if (!current || !row || !row.trade_date) return;
        modal.open('市场日明细 · ' + row.trade_date, '正在读取单日明细…');
        var token = beginModalRequest();
        api.marketDayDetail({publication_id: current.publication_id, trade_date: row.trade_date, basis: 'RECONSTRUCTED'}, {signal: token.signal}).then(function (detail) {
            if (!modalRequestActive(token)) return;
            releaseModalRequest(token);
            modal.open('市场日明细 · ' + row.trade_date, modalContent('单日明细绑定同一分析快照；涨跌停能力未构建时保持暂无。', [{title: '广度与成交', rows: [{label: '有效报价', value: detail.item.quote_valid_count}, {label: '上涨', value: detail.item.up_count}, {label: '下跌', value: detail.item.down_count}, {label: '平盘', value: detail.item.flat_count}, {label: '成交额', value: amountOrDash(detail.item.amount_sum)}, {label: '涨跌停能力', value: detail.item.capabilities && detail.item.capabilities.limit_state}]}, {title: '下钻接口', rows: [{label: '技术', value: detail.drilldown.technical}, {label: '新高', value: detail.drilldown.new_highs}, {label: '队列', value: detail.drilldown.queues}]}]));
        }).catch(function (error) {
            if (!modalRequestActive(token) || error.name === 'AbortError') return;
            releaseModalRequest(token);
            modal.open('市场日明细 · ' + row.trade_date, modalContent('单日明细暂时无法读取。', [{title: '原因', rows: [{label: '提示', value: error.message}]}]));
        });
    }

    function renderMarketChartSvg(points, series, label) {
        var width = 760, height = 218, left = 58, right = 18, top = 22, bottom = 34, plotHeight = height - top - bottom, plotWidth = width - left - right;
        var svg = svgNode('svg', {class: 'market-chart-svg', viewBox: '0 0 ' + width + ' ' + height, role: 'img', 'aria-label': label});
        var x = function (index) { return left + (points.length === 1 ? plotWidth / 2 : plotWidth * index / (points.length - 1)); };
        var values = [];
        series.forEach(function (item) { points.forEach(function (point) { var value = marketChartValue(item.value(point)); if (value !== null) values.push(value); }); });
        var boundsFor = function (item) {
            var itemValues = [];
            points.forEach(function (point) { var value = marketChartValue(item.value(point)); if (value !== null) itemValues.push(value); });
            if (item.kind === 'percent') return {min: 0, max: 100};
            var itemMin = itemValues.length ? Math.min.apply(Math, itemValues) : 0, itemMax = itemValues.length ? Math.max.apply(Math, itemValues) : 1;
            itemMin = Math.min(0, itemMin); itemMax = Math.max(1, itemMax);
            var padding = (itemMax - itemMin) * 0.08 || 1;
            return {min: Math.max(0, itemMin - padding), max: itemMax + padding};
        };
        var axisSeries = series.filter(function (item) { return points.some(function (point) { return marketChartValue(item.value(point)) !== null; }); })[0] || series[0] || {};
        var primaryBounds = boundsFor(axisSeries);
        var y = function (value, item) { var bounds = boundsFor(item); return top + plotHeight - (value - bounds.min) / (bounds.max - bounds.min || 1) * plotHeight; };
        var text = function (value, xValue, yValue, attributes) { var node = svgNode('text', Object.assign({x: xValue, y: yValue}, attributes || {})); node.textContent = value; svg.appendChild(node); };
        svg.appendChild(svgNode('rect', {x: left, y: top, width: plotWidth, height: plotHeight, class: 'market-chart-bg'}));
        [0, 0.5, 1].forEach(function (fraction) {
            var lineY = top + plotHeight * fraction;
            svg.appendChild(svgNode('line', {x1: left, y1: lineY, x2: width - right, y2: lineY, class: 'chart-grid-line'}));
            text(marketChartText(primaryBounds.max - (primaryBounds.max - primaryBounds.min) * fraction, axisSeries.displayKind), left - 8, lineY + 4, {class: 'chart-axis-label', 'text-anchor': 'end'});
        });
        if (series.some(function (item) { return item.kind === 'percent'; })) {
            text('100%', width - right + 8, top + 4, {class: 'chart-axis-label'});
            text('0%', width - right + 8, top + plotHeight + 4, {class: 'chart-axis-label'});
        }
        series.forEach(function (item, seriesIndex) {
            if (item.kind === 'bar') {
                var barWidth = Math.min(24, plotWidth / Math.max(points.length, 1) * 0.6 / Math.max(series.filter(function (entry) { return entry.kind === 'bar'; }).length, 1));
                points.forEach(function (point, index) {
                    var value = marketChartValue(item.value(point));
                    if (value === null) return;
                    var barX = x(index) - barWidth / 2 + seriesIndex * barWidth;
                    svg.appendChild(svgNode('rect', {x: barX, y: y(value, item), width: barWidth - 1, height: Math.max(1, top + plotHeight - y(value, item)), class: 'market-chart-bar', fill: item.color}));
                });
                return;
            }
            var segment = [];
            var flush = function () { if (segment.length > 1) svg.appendChild(svgNode('path', {d: 'M ' + segment.join(' L '), fill: 'none', stroke: item.color, 'stroke-width': 2})); segment = []; };
            points.forEach(function (point, index) {
                var value = marketChartValue(item.value(point));
                if (value === null) { flush(); return; }
                segment.push(x(index).toFixed(2) + ' ' + y(value, item).toFixed(2));
            });
            flush();
            points.forEach(function (point, index) {
                var value = marketChartValue(item.value(point));
                if (value !== null) svg.appendChild(svgNode('circle', {cx: x(index), cy: y(value, item), r: 3, fill: item.color}));
            });
        });
        series.forEach(function (item, index) { text(item.label, left + index * 116, top - 7, {class: 'market-chart-legend', fill: item.color}); });
        points.forEach(function (point, index) {
            var interval = plotWidth / Math.max(points.length - 1, 1), hitWidth = points.length === 1 ? plotWidth : Math.min(interval, 56);
            var hitX = points.length === 1 ? left : Math.max(left, Math.min(x(index) - hitWidth / 2, width - right - hitWidth));
            var hit = svgNode('rect', {x: hitX, y: top, width: hitWidth, height: plotHeight, fill: 'transparent', class: 'market-chart-hit', role: 'button', tabindex: 0, 'aria-label': '查看 ' + point.trade_date + ' 市场日明细', 'data-trade-date': point.trade_date});
            hit.addEventListener('click', function () { openMarketDetail(point); });
            hit.addEventListener('keydown', function (event) { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openMarketDetail(point); } });
            svg.appendChild(hit);
            if (index === 0 || index === points.length - 1 || index === Math.floor(points.length / 2)) text(display(point.trade_date), x(index), height - 8, {class: 'chart-date-label', 'text-anchor': index === 0 ? 'start' : (index === points.length - 1 ? 'end' : 'middle')});
        });
        if (!values.length) text('当前窗口暂无可绘制数据', width / 2, top + plotHeight / 2, {class: 'market-chart-empty', 'text-anchor': 'middle'});
        return svg;
    }

    function renderMarketCharts(points) {
        var target = document.getElementById('market-charts');
        if (!points.length) {
            target.querySelectorAll('.market-chart').forEach(function (chart) { chart.replaceChildren(); var empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = '当前窗口没有可绘制的市场聚合点。'; chart.appendChild(empty); }); return;
        }
        var configs = [
            {title: '市场广度', series: [{label: '上涨', color: '#d34b4b', value: function (point) { return point.up_count; }}, {label: '下跌', color: '#2f8f68', value: function (point) { return point.down_count; }}, {label: '平盘', color: '#7c8b9e', value: function (point) { return point.flat_count; }}]},
            {title: '量额与 MA 覆盖', series: [{label: '成交额', color: '#8fb9d8', kind: 'bar', displayKind: 'amount', value: function (point) { return point.amount_sum; }}, {label: 'MA20覆盖', color: '#e07a35', kind: 'percent', displayKind: 'percent', value: function (point) { return marketCoverage(point, 'ma20'); }}, {label: 'MA60覆盖', color: '#7a5ab8', kind: 'percent', displayKind: 'percent', value: function (point) { return marketCoverage(point, 'ma60'); }}]},
            {title: '涨跌停 / 新高 / 队列', series: [{label: '涨停', color: '#d34b4b', value: function (point) { return point.limit_up_count; }}, {label: '跌停', color: '#2f8f68', value: function (point) { return point.limit_down_count; }}, {label: '新高20日', color: '#2d8bd8', value: function (point) { return marketNewHighValue(point, 20); }}, {label: '新高60日', color: '#4d9f72', value: function (point) { return marketNewHighValue(point, 60); }}, {label: '队列去重', color: '#b06a3c', value: function (point) { return point.queue_unique_count; }}]}
        ];
        configs.forEach(function (config, index) {
            var card = document.getElementById(['market-breadth-chart', 'market-amount-chart', 'market-structure-chart'][index]).parentElement;
            var chart = document.getElementById(['market-breadth-chart', 'market-amount-chart', 'market-structure-chart'][index]);
            chart.replaceChildren(); chart.appendChild(renderMarketChartSvg(points, config.series, config.title));
            card.querySelector('.market-chart-note').textContent = index === 0 ? '上涨 / 下跌 / 平盘；三者之和等于有效报价分母。' : index === 1 ? '成交额柱形；MA20 / MA60 为上方数 ÷ 有效样本。' : '新高和队列按各自能力与有效分母绘制，NULL 保持缺口。';
        });
    }

    function limitLevelLabel(value) {
        if (value === '4PLUS') return '4板及以上';
        if (value === '1' || value === '2' || value === '3') return value + '板';
        return display(value);
    }

    function limitRate(value) {
        return value === null || value === undefined ? '暂无' : percent(value);
    }

    function renderLimitCapabilityEmpty(target, message, result) {
        target.replaceChildren();
        var empty = document.createElement('p');
        empty.className = 'empty';
        empty.textContent = message + ' · 能力状态：' + display(result && result.status);
        target.appendChild(empty);
    }

    function renderLimitLadder(result) {
        var target = document.getElementById('limit-ladder-table');
        var basis = document.getElementById('limit-ladder-basis');
        var counts = document.getElementById('limit-ladder-counts');
        var pageLabel = document.getElementById('limit-ladder-page-label');
        var previous = document.getElementById('limit-ladder-prev');
        var next = document.getElementById('limit-ladder-next');
        var levelCounts = result.level_counts || {};
        counts.textContent = '分层数量：1板 ' + display(levelCounts['1'], 0) + ' · 2板 ' + display(levelCounts['2'], 0) + ' · 3板 ' + display(levelCounts['3'], 0) + ' · 4板及以上 ' + display(levelCounts['4PLUS'], 0) + ' · 未知 ' + display(levelCounts.UNKNOWN, 0);
        pageLabel.textContent = '第 ' + display(result.page, 1) + ' 页 / 共 ' + display(result.total, 0) + ' 行';
        previous.disabled = !result.page || result.page <= 1;
        next.disabled = !result.page || (result.page * result.page_size >= result.total);
        if (result.status === 'NOT_BUILT') {
            renderLimitCapabilityEmpty(target, '收盘梯队尚未构建；需要本地 M8C 参考价与规则输入。', result);
            basis.textContent = '收盘梯队：尚未构建 · 快照 ' + display(result.snapshot_id) + ' · 不用 0 代替未知。';
            counts.textContent = '分层数量：尚未构建'; pageLabel.textContent = '暂无分页'; previous.disabled = true; next.disabled = true;
            return;
        }
        var items = result.items || [];
        if (!items.length) {
            renderLimitCapabilityEmpty(target, '当前快照暂无可展示的收盘梯队行。', result);
        } else {
            table.render(target, [
                {label: '交易日', key: 'trade_date'},
                {label: '证券', key: 'security_id'},
                {label: '状态', value: function (row) { return display(row.limit_state); }},
                {label: '层级', value: function (row) { return limitLevelLabel(row.ladder_level); }},
                {label: '连续天数', key: 'streak'},
                {label: '晋级状态', value: function (row) { return display(row.promotion_state); }},
                {label: '成交额', value: function (row) { return amountOrDash(row.raw_amount); }},
                {label: '关联来源', value: function (row) { return display(row.association_ref); }},
                {label: '规则版本', key: 'rule_id'}
            ], items);
        }
        var unknownOnly = Number(levelCounts.UNKNOWN || 0) === Number(result.total || 0) && Number(result.total || 0) > 0;
        basis.textContent = unknownOnly
            ? '收盘梯队：' + result.total + ' 行仍为未知；本地 M8C 参考价/规则尚未通过精确能力门，不能把未知推断为 1/2/3 板。快照 ' + display(result.snapshot_id) + '。'
            : '收盘梯队：' + (result.total || 0) + ' 行 · 快照 ' + display(result.snapshot_id) + ' · 历史基础 ' + display(result.history_basis) + ' · 第 ' + display(result.page) + ' 页。';
    }

    function renderLimitPromotion(result) {
        var target = document.getElementById('limit-promotion-table');
        if (result.status === 'NOT_BUILT') {
            renderLimitCapabilityEmpty(target, '晋级历史尚未构建；当前不生成虚假晋级率。', result);
            return;
        }
        var points = result.points || [];
        if (!points.length) {
            renderLimitCapabilityEmpty(target, '当前没有可计算的晋级历史；合格分母不足，不代表晋级率为 0。', result);
            return;
        }
        table.render(target, [
            {label: '交易日', key: 'trade_date'},
            {label: '前一日层级', value: function (row) { return limitLevelLabel(row.previous_level); }},
            {label: '成功 / 合格分母', value: function (row) { return row.success_count + ' / ' + row.eligible_count; }},
            {label: '晋级率', value: function (row) { return limitRate(row.rate); }},
            {label: '未知 / 停牌 / 无限制', value: function (row) { return [row.excluded_unknown, row.excluded_suspended, row.excluded_no_limit].join(' / '); }},
            {label: '前一日涨停 / 未确认', value: function (row) { return row.previous_up_count + ' / ' + row.previous_unconfirmed_count; }}
        ], points);
    }

    function loadLimitViews() {
        if (!current) return;
        var token = beginViewRequest('limit');
        var days = Number(document.getElementById('market-days').value || 60);
        var ladderParams = {
            publication_id: current.publication_id,
            page: limitLadderState.page,
            page_size: limitLadderState.pageSize,
            level: document.getElementById('limit-ladder-level').value,
            state: document.getElementById('limit-ladder-state').value,
            promotion: document.getElementById('limit-ladder-promotion').value,
            basis: 'RECONSTRUCTED'
        };
        document.getElementById('limit-ladder-basis').textContent = '正在读取收盘梯队与晋级能力…';
        api.limitLadder(ladderParams, {signal: token.signal}).then(function (result) { if (viewRequestActive('limit', token)) renderLimitLadder(result); }).catch(function (error) {
            if (!viewRequestActive('limit', token) || error.name === 'AbortError') return;
            renderLimitCapabilityEmpty(document.getElementById('limit-ladder-table'), '收盘梯队读取失败：' + error.message, {status: 'UNAVAILABLE'});
            document.getElementById('limit-ladder-basis').textContent = '收盘梯队读取失败，请检查当前分析快照。';
        });
        api.limitPromotionHistory({publication_id: current.publication_id, days: days, previous_level: document.getElementById('limit-promotion-level').value, basis: 'RECONSTRUCTED'}, {signal: token.signal}).then(function (result) { if (viewRequestActive('limit', token)) renderLimitPromotion(result); }).catch(function (error) {
            if (!viewRequestActive('limit', token) || error.name === 'AbortError') return;
            renderLimitCapabilityEmpty(document.getElementById('limit-promotion-table'), '晋级历史读取失败：' + error.message, {status: 'UNAVAILABLE'});
        });
    }

    function hotRankSourceLabel(source) {
        return source === 'EASTMONEY_HOT_RANK' ? '东方财富' : source === 'TONGHUASHUN_HOT_RANK' ? '同花顺' : display(source);
    }

    function hotRankPercent(value, sourceValue) {
        if (value === undefined || value === null || value === '') return '—';
        var number = Number(value);
        if (!Number.isFinite(number)) return display(value);
        return format.percent(sourceValue ? number : number * 100);
    }

    function hotRankItems(result) {
        if (result && Array.isArray(result.items)) {
            return (result.items || []).map(function (item) {
                item._source_id = result.source_id;
                item._reason_status = result.reason_status;
                return item;
            });
        }
        return (result && result.source_views || []).reduce(function (items, view) {
            return items.concat((view.items || []).map(function (item) {
                item._source_id = view.source_id;
                item._reason_status = view.reason_status;
                return item;
            }));
        }, []);
    }

    function renderHotRank(result) {
        var target = document.getElementById('hot-rank-table');
        var items = hotRankItems(result);
        var views = result && result.source_views ? result.source_views : [result];
        var quoteStatuses = views.map(function (view) { return hotRankSourceLabel(view.source_id) + '：' + display(view.quote_status); }).join('；');
        var reasonStatuses = views.map(function (view) { return hotRankSourceLabel(view.source_id) + '：' + display(view.reason_status); }).join('；');
        if (!items.length) {
            target.replaceChildren();
            var empty = document.createElement('p');
            empty.className = 'empty';
            empty.textContent = '当前请求没有可展示的热榜行。';
            target.appendChild(empty);
        } else {
            table.render(target, [
                {label: '来源', value: function (row) { return hotRankSourceLabel(row._source_id || row.source_code); }},
                {label: '平台排名', key: 'platform_rank'},
                {label: '证券', value: function (row) { return securityLabel({security_id: row.security_id, security_name: row.security_name || '未映射'}); }},
                {label: '排名变化', key: 'source_rank_change'},
                {label: '榜单涨跌幅', value: function (row) { return hotRankPercent(row.source_quote_fields && row.source_quote_fields.rise_and_fall, true); }},
                {label: '最新价', value: function (row) { return row.quote ? display(row.quote.price) : '—'; }},
                {label: '当日涨跌幅', value: function (row) { return hotRankPercent(row.quote && row.quote.ret1, false); }},
                {label: '成交额', value: function (row) { return row.quote ? amountOrDash(row.quote.amount) : '—'; }},
                {label: '报价状态', value: function (row) { return display(row.quote && row.quote.quote_state); }},
                {label: '时间语义', value: function (row) { return display(row.quote && row.quote.time_semantics); }},
                {label: '原因', value: function (row) { return row._reason_status === 'UNAVAILABLE_NO_VERIFIED_REASON_SOURCE' ? '不可用（无已验证来源）' : display(row._reason_status); }}
            ], items);
        }
        document.getElementById('hot-rank-basis').textContent = '实时请求 · 不保存热榜快照 · ' + (items.length || 0) + ' 行 · 报价 ' + (quoteStatuses || '未请求') + ' · 原因 ' + (reasonStatuses || '不可用');
        document.getElementById('hot-rank-page-label').textContent = '第 ' + ((result && result.page) || hotRankState.page) + ' 页';
        document.getElementById('hot-rank-prev').disabled = hotRankState.page <= 1;
        document.getElementById('hot-rank-next').disabled = items.length < hotRankState.pageSize;
    }

    function loadHotRank() {
        var token = beginViewRequest('hot');
        var source = document.getElementById('hot-rank-source').value;
        hotRankState.source = source;
        document.getElementById('hot-rank-basis').textContent = '正在实时读取平台热榜…';
        api.hotRankings({source: source, page: hotRankState.page, page_size: hotRankState.pageSize, co_listed: source === 'ALL' ? '1' : undefined}, {signal: token.signal}).then(function (result) { if (viewRequestActive('hot', token)) renderHotRank(result); }).catch(function (error) {
            if (!viewRequestActive('hot', token) || error.name === 'AbortError') return;
            var target = document.getElementById('hot-rank-table');
            target.replaceChildren();
            var empty = document.createElement('p');
            empty.className = 'empty';
            empty.textContent = '热榜暂不可用：' + error.message;
            target.appendChild(empty);
            document.getElementById('hot-rank-basis').textContent = '实时请求失败；未保存热榜快照。';
            document.getElementById('hot-rank-next').disabled = true;
        });
    }

    function evidenceDisplay(value) {
        if (Array.isArray(value)) return value.map(function (item) { return evidenceDisplay(item); }).join('、');
        if (value === null || value === undefined || value === '') return '暂无';
        var labels = {
            OBSERVING: '观察模式',
            AVAILABLE: '可用',
            UNAVAILABLE: '不可用',
            UNKNOWN: '未知',
            LOCAL_RECONSTRUCTED: '本地重建',
            RECONSTRUCTED: '本地重建',
            STOCK_SECTOR_ASSOC_V1: '股票-板块强势关联合同 V1',
            PATTERN_NOT_CURRENT_STRENGTH_OR_REACCELERATION: '当前不是强势或再加速形态',
            LEAVE_ONE_OUT_RET20_MEDIAN_NOT_POSITIVE: '排除该板块后，20日收益中位数未为正',
            LEAVE_ONE_OUT_BREADTH20_LT_0_60: '排除该板块后，上涨宽度低于 60%',
            SECTOR_ROLE_EXCLUDED: '板块角色被排除',
            SECTOR_INVALID: '板块数据无效',
            NORMAL_ATTRIBUTE: '普通属性',
            PRICE_BEHAVIOR_TAG: '行情标签',
            EXCLUDE_FROM_THEME_RANK: '排除概念排名',
            true: '是',
            false: '否'
        };
        if (Object.prototype.hasOwnProperty.call(labels, String(value))) return labels[String(value)];
        return display(value);
    }

    function associationEvidenceRows(sector, fallbackRows) {
        var items = sector && Array.isArray(sector.evidence_items) ? sector.evidence_items : [];
        if (!items.length) return fallbackRows || [];
        return items.map(function (item) {
            var evidence = item.evidence_json || {}, thresholds = evidence.thresholds || {}, thresholdText = Object.keys(thresholds).sort().map(function (key) {
                return fieldLabel(key) + '=' + evidenceDisplay(thresholds[key]);
            }).join('；');
            var evidenceText = [];
            if (evidence.pattern) evidenceText.push('模式：' + evidenceDisplay(evidence.pattern));
            if (thresholdText) evidenceText.push('阈值：' + thresholdText);
            return {
                kind: item.eligible ? '合格关联' : '候选/拒绝',
                sector: item.sector_name,
                rank: item.association_rank,
                eligibility: item.eligible,
                pattern: item.pattern,
                reason: (item.rejection_reasons || []).map(evidenceDisplay).join('、') || (item.eligible ? '满足关联门槛' : '未形成合格关联'),
                contract: evidenceDisplay(item.contract_id),
                basis: item.history_basis,
                evidence: evidenceText.join('；') || '暂无结构化证据摘要'
            };
        });
    }

    function evidenceSection(title, body) {
        var section = document.createElement('section');
        section.className = 'evidence-section';
        var heading = document.createElement('h4');
        heading.className = 'evidence-section-title';
        heading.textContent = title;
        section.appendChild(heading);
        if (body && body.nodeType) section.appendChild(body);
        return section;
    }

    function evidencePointTable(points) {
        return modalTable([
            {label: '交易日', key: 'trade_date'},
            {label: '队列', value: function (item) { return evidenceDisplay(item.queue_name); }},
            {label: '命中', value: function (item) { return evidenceDisplay(item.hit); }},
            {label: '层级', value: function (item) { return evidenceDisplay(item.tier); }},
            {label: '研究级别', value: function (item) { return evidenceDisplay(item.research_band); }},
            {label: '变化', value: function (item) { return evidenceDisplay(item.transition); }},
            {label: '质量', value: function (item) { return evidenceDisplay(item.quality_codes); }}
        ], (points || []).slice(-20).reverse());
    }

    function evidenceQueueSummary(queues) {
        return Object.keys(queues || {}).sort().map(function (queueName) {
            var queue = queues[queueName] || {};
            return {
                queue: evidenceDisplay(queueName),
                hit: evidenceDisplay(queue.hit),
                tier: evidenceDisplay(queue.tier),
                source: evidenceDisplay(queue.source_class)
            };
        });
    }

    function externalEvidencePlaceholder() {
        return evidenceSection('在线增强 · 当前不可用', modalContent('在线能力尚未接入；该状态不阻塞本地个股透视首屏。', [{
            title: '能力状态',
            rows: [
                {label: '当前状态', value: 'NOT_BUILT'},
                {label: '来源策略', value: '未启用在线来源'},
                {label: '首屏策略', value: '在线慢或不可用不阻塞首屏'},
                {label: '后续接口', value: 'API38（M14）'}
            ]
        }]));
    }

    function stockInsightBody(row, result, requestId, route) {
        var wrap = document.createElement('div');
        var intro = document.createElement('p');
        intro.className = 'modal-intro';
        intro.textContent = '统一查看报价、技术、结构与板块关联；历史按需加载，所有数值保留原始 NULL 语义，不构成自动买卖信号。';
        wrap.appendChild(intro);
        var tabs = document.createElement('div');
        tabs.className = 'insight-tabs';
        tabs.setAttribute('role', 'tablist');
        var content = document.createElement('div');
        content.className = 'insight-tab-content';
        wrap.append(tabs, content);

        function renderOverview() {
            var overview = result.item.overview || {};
            var technical = result.item.technical || {};
            var structures = result.item.structures || {};
            var sector = result.item.sector_context || {};
            var primary = sector.primary;
            var alternatives = sector.alternatives || [];
            content.replaceChildren();
            content.appendChild(modalContent('当前快照与统一股票范围内的可核对信息。', [{
                title: '行情概览', rows: [{label: '股票', value: securityLabel({security_id: overview.security_id, security_name: overview.name})}, {label: '原始收盘', value: overview.raw_close}, {label: '当日收益', value: percent(overview.quote_ret1)}, {label: '金额', value: amountOrDash(overview.amount)}, {label: '报价状态', value: overview.quote_state}]
            }, {
                title: '技术摘要', rows: [{label: '技术日期', value: technical.trade_date}, {label: '调整后收盘', value: technical.adj_close}, {label: 'RET20', value: percent(technical.ret20)}, {label: '均线排列', value: technical.ma_alignment}, {label: '额比20', value: technical.amount_ratio20}, {label: '量额状态', value: technical.amount_class}, {label: '质量', value: quality(technical)}]
            }, {
                title: 'M11 板块关联上下文', rows: [{label: '主关联板块', value: primary ? primary.sector_name + '（' + display(primary.association_rank, 0) + '）' : sector.reason}, {label: '备选关联', value: alternatives.length ? alternatives.map(function (item) { return item.sector_name + '（' + display(item.association_rank, 0) + '）'; }).join('、') : '暂无'}, {label: '研究级别', value: structures.research_band}, {label: '结构命中数', value: structures.unique_hit_count}]
            }]));
        }

        function renderEvidence() {
            var sector = result.item.sector_context || {};
            var structures = result.item.structures || {};
            var technical = result.item.technical || {};
            var eligibleRows = [];
            if (sector.primary) eligibleRows.push(sector.primary);
            (sector.alternatives || []).forEach(function (item) { eligibleRows.push(item); });
            var rows = associationEvidenceRows(sector, eligibleRows.map(function (item) {
                return {kind: item.association_rank === 1 ? '主关联' : '备选关联', sector: item.sector_name, rank: item.association_rank, eligibility: item.eligible, pattern: item.pattern, reason: (item.rejection_reasons || []).map(evidenceDisplay).join('、') || '满足关联门槛', contract: evidenceDisplay(item.contract_id), basis: item.history_basis, evidence: evidenceDisplay(item.evidence_json || {})};
            }));
            content.replaceChildren();
            content.appendChild(modalContent('证据按来源分组展示；未通过或缺失条件不转译为强势结论。', [{
                title: '证据摘要（5项）', rows: [
                    {label: '数据状态', value: result.status},
                    {label: '分析快照', value: result.snapshot_id},
                    {label: '截止日期', value: result.cutoff_date || result.trade_date || result.as_of_trade_date},
                    {label: '历史基础', value: sector.history_basis || result.history_basis},
                    {label: '主关联板块', value: sector.primary ? sector.primary.sector_name + '（' + display(sector.primary.association_rank, 0) + '）' : (sector.reason || '暂无可确认的强势关联板块')}
                ]
            }]));
            var groups = document.createElement('section');
            groups.className = 'evidence-groups';
            var heading = document.createElement('h3');
            heading.textContent = '证据分组与详情';
            groups.appendChild(heading);
            var associationBody = modalTable([
                {label: '分组', key: 'kind'},
                {label: '板块', key: 'sector'},
                {label: '名次', value: function (item) { return display(item.rank, 0); }},
                {label: '门槛', value: function (item) { return evidenceDisplay(item.eligibility); }},
                {label: '模式', value: function (item) { return evidenceDisplay(item.pattern); }},
                {label: '说明', value: function (item) { return evidenceDisplay(item.reason); }},
                {label: '合同', value: function (item) { return evidenceDisplay(item.contract); }},
                {label: '历史基础', value: function (item) { return evidenceDisplay(item.basis); }},
                {label: '证据摘要', key: 'evidence'}
            ], rows);
            var associationStatus = sector.evidence_status || (rows.length ? 'AVAILABLE' : 'NO_ELIGIBLE_ASSOCIATION');
            groups.appendChild(evidenceSection('M11 板块关联 · ' + rows.length + ' 条 · ' + evidenceDisplay(associationStatus), associationBody));
            var queueRows = evidenceQueueSummary(structures.queues || {});
            groups.appendChild(evidenceSection('结构摘要 · ' + queueRows.length + ' 个队列', modalTable([
                {label: '队列', key: 'queue'},
                {label: '命中', key: 'hit'},
                {label: '层级', key: 'tier'},
                {label: '来源状态', key: 'source'}
            ], queueRows)));
            var activeQueues = Object.keys(structures.queues || {}).filter(function (queueName) { return structures.queues[queueName] && structures.queues[queueName].hit === true; });
            if (!activeQueues.length) {
                var noQueue = document.createElement('p');
                noQueue.className = 'modal-empty';
                noQueue.textContent = '当前没有命中结构队列，未生成 API15 结构详情；缺失不替换为零值。';
                groups.appendChild(evidenceSection('API15 结构详情 · 暂无命中队列', noQueue));
            } else {
                activeQueues.forEach(function (queueName) {
                    var loading = document.createElement('p');
                    loading.className = 'modal-empty';
                    loading.textContent = '正在读取本地分组证据…';
                    var details = evidenceSection(evidenceDisplay(queueName) + ' · API15 详情', loading);
                    groups.appendChild(details);
                    api.evidence({publication_id: current.publication_id, queue: queueName, security_id: row.security_id, format: 'groups', basis: 'RECONSTRUCTED'}, {signal: insightAbortController && insightAbortController.signal}).then(function (evidence) {
                        if (requestId !== insightRequestId) return;
                        var evidenceGroups = evidence.item && evidence.item.groups || [];
                        var group = evidenceGroups.find(function (candidate) { return candidate.group_id === 'historical_structure'; }) || evidenceGroups[0];
                        var body = group ? evidencePointTable(group.items) : modalContent('当前队列暂无可展示的本地详情。', [{title: '状态', rows: [{label: '接口状态', value: evidence.status}]}]);
                        var heading = details.querySelector('.evidence-section-title');
                        heading.textContent = evidenceDisplay(queueName) + ' · API15 详情 · ' + (group && group.items ? group.items.length : 0) + ' 条';
                        details.replaceChildren(heading, body);
                    }).catch(function (error) {
                        if (requestId !== insightRequestId || error.name === 'AbortError') return;
                        var heading = details.querySelector('.evidence-section-title');
                        heading.textContent = evidenceDisplay(queueName) + ' · API15 详情 · 暂不可用';
                        details.replaceChildren(heading, modalContent('本地分组证据暂时无法读取。', [{title: '原因', rows: [{label: '提示', value: error.message}]}]));
                    });
                });
            }
            groups.appendChild(evidenceSection('合同与基础', modalContent('该分组只展示当前发布版本的可追溯元数据。', [{title: '合同与基础', rows: [{label: '关联合同', value: sector.contract_id}, {label: '结构合同', value: structures.queue_contract}, {label: '技术质量', value: technical.quality_codes}, {label: '分析快照', value: result.snapshot_id}, {label: '截止日期', value: result.cutoff_date || result.trade_date || result.as_of_trade_date}]}])));
            groups.appendChild(externalEvidencePlaceholder());
            content.appendChild(groups);
        }

        function renderHistoryLoading() {
            content.replaceChildren();
            var loading = document.createElement('p');
            loading.className = 'empty';
            loading.textContent = '正在读取本地历史序列…';
            content.appendChild(loading);
        }

        function renderHistory(technicalHistory, structureHistory) {
            if (requestId !== insightRequestId) return;
            var history = historyRows(technicalHistory.points || [], route.days);
            var structures = structureHistoryRows(structureHistory.points || [], route.days).map(function (item) {
                return {trade_date: item.trade_date, queue: item.queue_name, hit: display(item.hit), tier: display(item.tier), band: display(item.research_band), transition: display(item.transition), quality: quality(item)};
            });
            content.replaceChildren();
            content.appendChild(renderHistoryChart(technicalHistory));
            content.appendChild(modalContent('历史页签只使用本地已绑定快照；技术历史口径为调整后价格，结构历史按队列逐日展开。窗口：' + route.days + ' 日。', [{
                title: '技术历史（最近' + route.days + '个交易日）', type: 'table', columns: [{label: '交易日', key: 'trade_date'}, {label: '调整后收盘', key: 'close'}, {label: 'RET20', key: 'ret20'}, {label: 'MA5', key: 'ma5'}, {label: 'MA20', key: 'ma20'}, {label: 'MA60', key: 'ma60'}, {label: '额比20', key: 'amount'}, {label: '量比前20', key: 'volume'}, {label: 'RPS20', key: 'rps'}, {label: '质量', key: 'quality'}], rows: history
            }, {
                title: '结构历史（最近' + route.days + '个交易日）', type: 'table', columns: [{label: '交易日', key: 'trade_date'}, {label: '队列', key: 'queue'}, {label: '命中', key: 'hit'}, {label: '层级', key: 'tier'}, {label: '研究级别', key: 'band'}, {label: '变化', key: 'transition'}, {label: '质量', key: 'quality'}], rows: structures
            }, {title: '历史口径', rows: [{label: '技术基础', value: technicalHistory.history_basis || technicalHistory.basis}, {label: '结构基础', value: structureHistory.history_basis || structureHistory.basis}, {label: '股票', value: securityLabel(row)}]}]));
        }

        function selectTab(key) {
            route.tab = normalizeInsightTab(key);
            writeInsightRoute(route, 'replace');
            Array.prototype.forEach.call(tabs.children, function (button) {
                var active = button.dataset.insightTab === key;
                button.classList.toggle('active', active);
                button.setAttribute('aria-selected', active ? 'true' : 'false');
            });
            if (key === 'overview') renderOverview();
            else if (key === 'evidence') renderEvidence();
            else {
                renderHistoryLoading();
                Promise.all([api.technicalHistory({publication_id: current.publication_id, security_id: row.security_id, days: route.days, price_basis: 'ADJUSTED', fields: 'ohlc,ma,amount,rps'}, {signal: insightAbortController && insightAbortController.signal}), api.structureHistory({publication_id: current.publication_id, security_id: row.security_id, days: route.days, basis: 'RECONSTRUCTED'}, {signal: insightAbortController && insightAbortController.signal})]).then(function (values) {
                    renderHistory(values[0], values[1]);
                }).catch(function (error) {
                    if (requestId !== insightRequestId) return;
                    content.replaceChildren();
                    var failure = document.createElement('p');
                    failure.className = 'empty';
                    failure.textContent = '历史数据暂不可用：' + error.message;
                    content.appendChild(failure);
                });
            }
        }

        tabs.appendChild(insightTabButton('概览', 'overview', true, function () { selectTab('overview'); }));
        tabs.appendChild(insightTabButton('历史', 'history', false, function () { selectTab('history'); }));
        tabs.appendChild(insightTabButton('证据', 'evidence', false, function () { selectTab('evidence'); }));
        selectTab(route.tab || 'overview');
        return wrap;
    }

    function showStockInsight(row, routeOptions) {
        cancelInsightRequest();
        var route = {publication_id: current.publication_id, security_id: row.security_id, tab: normalizeInsightTab(routeOptions && routeOptions.tab), days: normalizeInsightDays(routeOptions && routeOptions.days)};
        insightRouteActive = true;
        if (!(routeOptions && routeOptions.fromRoute)) writeInsightRoute(route, 'push');
        insightAbortController = typeof AbortController === 'function' ? new AbortController() : null;
        var requestId = ++insightRequestId;
        api.stockInsight({publication_id: current.publication_id, security_id: row.security_id, include: 'overview,technical,structures,sector_context', days: route.days, basis: 'RECONSTRUCTED'}, {signal: insightAbortController && insightAbortController.signal}).then(function (result) {
            if (requestId !== insightRequestId) return;
            openingInsight = true;
            modal.open('个股透视 · ' + securityLabel(row), stockInsightBody(row, result, requestId, route));
            openingInsight = false;
        }).catch(function (error) {
            if (requestId !== insightRequestId || error.name === 'AbortError') return;
            modal.open('个股透视 · ' + securityLabel(row), modalContent('个股透视暂时无法读取。', [{title: '原因', rows: [{label: '提示', value: error.message}]}]));
        });
    }

    function restoreInsightRoute() {
        var route = readInsightRoute();
        if (!route || !current || (route.publication_id && route.publication_id !== current.publication_id)) return;
        if (modal.isOpen() && insightRouteActive) return;
        showStockInsight({security_id: route.security_id}, {tab: route.tab, days: route.days, fromRoute: true});
    }

    window.addEventListener('popstate', function () {
        var pageRoute = router.read(), insightRoute = readInsightRoute();
        if (currentPage !== pageRoute.page || (pageRoute.page === 'sectors' && sectorSubpage !== pageRoute.subpage)) {
            showPage(pageRoute.page, {fromRoute: true, subpage: pageRoute.subpage});
        }
        if (!insightRoute) {
            if (modal.isOpen() && insightRouteActive) modal.close();
            return;
        }
        if (current && (!insightRoute.publication_id || insightRoute.publication_id === current.publication_id)) restoreInsightRoute();
    });

    function renderTechnical(result) {
        var items = result.items || [];
        var pages = Math.max(1, Math.ceil((result.total || 0) / result.page_size));
        document.getElementById('technical-heading').textContent = technicalState.mode === 'highs' ? '创新高 · RPS' : '技术状态';
        document.getElementById('technical-description').textContent = technicalState.mode === 'highs' ? '只比较前序窗口；并列前高、历史不足和缺失值不会被当作有效新高。当前表格只显示截止日最新记录，同一股票不会跨日期重复。' : '均线、收益、量额状态来自同一分析快照；当前表格只显示截止日最新记录，暂无数据明确显示为“暂无”。';
        document.getElementById('technical-basis').textContent = basisText(result);
        document.getElementById('technical-page-label').textContent = '第 ' + result.page + ' 页 / 共 ' + pages + ' 页 · ' + (result.total || 0) + ' 条';
        document.getElementById('technical-prev').disabled = result.page <= 1;
        document.getElementById('technical-next').disabled = result.page >= pages;
        if (technicalState.mode === 'highs') table.render(document.getElementById('technical-table'), [{
            label: '股票',
            value: securityLabel
        }, {label: '日期', key: 'trade_date'}, {
            label: '新高窗口', value: function (row) {
                return display(row.window, 0) + '日';
            }
        }, {
            label: '新高状态', value: function (row) {
                return row.new_high === null ? '暂无' : row.new_high ? '是' : '否';
            }
        }, {
            label: '距前高', value: function (row) {
                return row.dist_prior_high === null ? '暂无' : percent(row.dist_prior_high);
            }
        }, {
            label: '连续新高', value: function (row) {
                return row.streak === null ? '暂无' : display(row.streak, 0) + '天';
            }
        }, {
            label: 'RPS20', value: function (row) {
                return row.rps20 === null ? '暂无' : percent(row.rps20);
            }
        }, {
            label: '有效样本', value: function (row) {
                return display(row.rps_valid_universe_count20, 0);
            }
        }, {label: '研究级别', value: band}, {label: '质量', value: quality}, {
            label: '历史',
            action: {label: '查看', onClick: showHistory}
        }, {label: '透视', action: {label: '打开', onClick: showStockInsight}}], items); else table.render(document.getElementById('technical-table'), [{
            label: '股票',
            value: securityLabel
        }, {label: '日期', key: 'trade_date'}, {
            label: '收盘', value: function (row) {
                return valueOrDash(row.adj_close);
            }
        }, {
            label: 'RET20', value: function (row) {
                return row.ret20 === null ? '暂无' : percent(row.ret20);
            }
        }, {
            label: 'MA5 / MA20 / MA60', value: function (row) {
                return [row.ma5, row.ma20, row.ma60].map(valueOrDash).join(' / ');
            }
        }, {
            label: '均线排列', value: function (row) {
                return display(row.ma_alignment);
            }
        }, {
            label: '额比20', value: function (row) {
                return valueOrDash(row.amount_ratio20);
            }
        }, {
            label: '量比前20', value: function (row) {
                return valueOrDash(row.volume_vs_prior20);
            }
        }, {
            label: '量额状态', value: function (row) {
                return display(row.amount_class);
            }
        }, {label: '研究级别', value: band}, {label: '质量', value: quality}, {
            label: '历史',
            action: {label: '查看', onClick: showHistory}
        }, {label: '透视', action: {label: '打开', onClick: showStockInsight}}], items);
    }

    function loadTechnical() {
        if (!current) return;
        var token = beginViewRequest('technical');
        setNotice('正在读取个股技术数据…');
        var request = technicalState.mode === 'highs' ? api.newHighs(technicalParams(), {signal: token.signal}) : api.technical(technicalParams(), {signal: token.signal});
        request.then(function (result) {
            if (!viewRequestActive('technical', token)) return;
            renderTechnical(result);
            setNotice('已加载 ' + (result.total || 0) + ' 条；当前页 ' + (result.items || []).length + ' 条。');
        }).catch(function (error) {
            if (!viewRequestActive('technical', token) || error.name === 'AbortError') return;
            document.getElementById('technical-table').replaceChildren();
            var empty = document.createElement('p');
            empty.className = 'empty';
            empty.textContent = error.message.indexOf('RPS_NOT_BUILT') >= 0 ? 'RPS 尚未构建，当前筛选不会伪造结果。' : '暂无可用数据：' + error.message;
            document.getElementById('technical-table').appendChild(empty);
            document.getElementById('technical-basis').textContent = '当前发布版本未提供可用分析快照或该字段能力。';
            setNotice('技术数据读取失败：' + error.message, true);
        });
    }

    function namedSecurity(id, name) {
        return id ? securityLabel({security_id: id, security_name: name}) : '暂无';
    }

    function renderSectorTimeline(row, timeline, members, leaders, failures) {
        if (!members.items || !members.items.length) members = {items: row.member_state_preview || timeline.member_state || []};
        var timelineRows = (timeline.points || []).map(function (x) {
            return {
                trade_date: x.trade_date,
                rank: x.hierarchy_rank === undefined || x.hierarchy_rank === null ? '暂无' : display(x.hierarchy_rank, 0),
                rps: percent(x.hierarchy_sector_rs20_pct),
                ret: valueOrDash(x.member_ret20_median),
                breadth: percent(x.breadth_ret1),
                coverage: percent(x.coverage)
            };
        }).reverse();
        var memberRows = (members.items || []).slice(0, 80).map(function (x) {
            return {
                trade_date: x.trade_date,
                security_id: namedSecurity(x.security_id, x.security_name),
                present: display(x.member_present),
                strong: display(x.strong_state),
                change: display(x.member_change_kind),
                rank: display(x.member_rank, 0),
                delta: display(x.rank_delta, 0),
                percentile: percent(x.member_percentile),
                structure: x.structure_hit === null ? '暂无' : display(x.structure_hit),
                high: x.high_hit === null ? '暂无' : display(x.high_hit),
                basis: display(x.history_basis)
            };
        });
        var leaderRows = (leaders.points || []).map(function (x) {
            return {
                trade_date: x.trade_date,
                first: namedSecurity(x.ranked_first_id, x.ranked_first_name),
                second: namedSecurity(x.ranked_second_id, x.ranked_second_name),
                candidate: namedSecurity(x.candidate_id, x.candidate_name),
                confirmed: namedSecurity(x.confirmed_id, x.confirmed_name),
                streak: display(x.candidate_streak, 0),
                event: display(x.confirmation_event),
                stale: x.stale ? '是' : '否'
            };
        }).reverse();
        var intro = '板块指标按交易日回看；成员变化和代表状态用于研究核对，不是自动交易信号。当前历史基础：' + display(timeline.history_basis) + (failures.length ? '。以下模块暂时无法读取：' + failures.join('、') : '');
        modal.open('板块时间线 · ' + display(row.sector_name), modalContent(intro, [{
            title: '板块周期',
            type: 'table',
            columns: [{label: '交易日', key: 'trade_date'}, {label: '板块名次（本层级）', key: 'rank'}, {
                label: 'RPS20百分位（本层级）',
                key: 'rps'
            }, {label: '成员20日收益中位数', key: 'ret'}, {label: '成员上涨比例', key: 'breadth'}, {
                label: '覆盖率',
                key: 'coverage'
            }],
            rows: timelineRows
        }, {
            title: '成员状态（最多显示80条）',
            type: 'table',
            columns: [{label: '交易日', key: 'trade_date'}, {label: '股票', key: 'security_id'}, {
                label: '是否在板',
                key: 'present'
            }, {label: '强势状态', key: 'strong'}, {label: '成员变化', key: 'change'}, {
                label: '成员名次',
                key: 'rank'
            }, {label: '名次变化', key: 'delta'}, {label: '成员百分位', key: 'percentile'}, {
                label: '结构命中',
                key: 'structure'
            }, {label: '新高命中', key: 'high'}, {label: '历史基础', key: 'basis'}],
            rows: memberRows
        }, {
            title: '代表状态',
            type: 'table',
            columns: [{label: '交易日', key: 'trade_date'}, {label: '第一候选', key: 'first'}, {
                label: '第二候选',
                key: 'second'
            }, {label: '当前候选', key: 'candidate'}, {label: '已确认代表', key: 'confirmed'}, {
                label: '候选连续天数',
                key: 'streak'
            }, {label: '确认事件', key: 'event'}, {label: '是否陈旧', key: 'stale'}],
            rows: leaderRows
        }]));
    }

    function showSectorTimeline(row) {
        modal.open('板块时间线 · ' + display(row.sector_name), '正在读取板块历史…');
        var token = beginModalRequest();

        function optional(request) {
            return request.then(function (value) {
                return {value: value};
            }).catch(function (error) {
                return {error: error};
            });
        }

        optional(api.sectorTimeline({
            publication_id: current.publication_id,
            sector_id: row.sector_id,
            days: 30
        }, {signal: token.signal})).then(function (timelineResult) {
            var timeline = timelineResult.value || {};
            optional(api.sectorMembersHistory({
                publication_id: current.publication_id,
                sector_id: row.sector_id,
                days: 10,
                state: 'ALL'
            }, {signal: token.signal})).then(function (memberResult) {
                optional(api.sectorLeaderHistory({
                    publication_id: current.publication_id,
                    sector_id: row.sector_id,
                    days: 30
                }, {signal: token.signal})).then(function (leaderResult) {
                    if (!modalRequestActive(token)) return;
                    releaseModalRequest(token);
                    var members = memberResult.value || {items: timeline.member_state || []};
                    if (!members.items || !members.items.length) members = {items: timeline.member_state || []};
                    var leaders = leaderResult.value || {};
                    var failures = [];
                    if (timelineResult.error) failures.push('板块周期');
                    if (memberResult.error && !timeline.member_state) failures.push('成员状态');
                    if (leaderResult.error) failures.push('代表状态');
                    renderSectorTimeline(row, timeline, members, leaders, failures);
                });
            });
        });
    }

    function sectorColumns() {
        return [{
            label: '板块',
            key: 'sector_name'
        }, {label: '板块层级', key: 'hierarchy_level'}, {
            label: '上级板块', value: function (row) {
                return row.parent_sector_name || '—';
            }
        }, {
            label: '类型', value: function (row) {
                return display(row.sector_type);
            }
        }, {
            label: '最新名次（本层级）', value: function (row) {
                var c = row.cells[row.cells.length - 1];
                return c && c.hierarchy_rank !== undefined && c.hierarchy_rank !== null ? display(c.hierarchy_rank, 0) : '暂无';
            }
        }, {
            label: '最新RPS20百分位（本层级）', value: function (row) {
                var c = row.cells[row.cells.length - 1];
                return c && c.hierarchy_sector_rs20_pct !== undefined && c.hierarchy_sector_rs20_pct !== null ? percent(c.hierarchy_sector_rs20_pct) : '暂无';
            }
        }, {
            label: '最新覆盖率', value: function (row) {
                var c = row.cells[row.cells.length - 1];
                return c && c.coverage !== undefined && c.coverage !== null ? percent(c.coverage) : '暂无';
            }
        }, {
            label: '周期单元格', value: function (row) {
                return row.cells.map(function (c) {
                    return c.trade_date + '：' + (c.hierarchy_rank === undefined || c.hierarchy_rank === null ? '暂无' : '第 ' + display(c.hierarchy_rank, 0) + ' 名');
                }).join(' · ');
            }
        }, {label: '详细历史', action: {label: '查看', onClick: showSectorTimeline}}];
    }

    function sectorRequest(level, options) {
        return api.sectorCycle({
            publication_id: current.publication_id,
            page: 1,
            page_size: 15,
            days: sectorState.days,
            sector_type: sectorState.type,
            q: sectorState.query,
            hierarchy_level: level
        }, options);
    }

    function renderSectorTable(targetId, result) {
        table.render(document.getElementById(targetId), sectorColumns(), result.items || []);
    }

    function showSectorTableGroups(industry) {
        document.getElementById('sector-industry-tables').hidden = !industry;
        document.getElementById('sector-flat-tables').hidden = industry;
    }

    function loadSectors() {
        if (!current) return;
        var token = beginViewRequest('sectors');
        document.getElementById('sector-type').value = sectorState.type;
        document.getElementById('sector-query').value = sectorState.query || '';
        setNotice('正在读取板块周期…');
        var typeName = sectorState.type === 'INDUSTRY' ? '行业' : sectorState.type === 'THEME' ? '概念' : sectorState.type === 'STYLE' ? '通达信风格' : '分类';
        var requests = sectorState.type === 'INDUSTRY' ? [sectorRequest('ROOT', {signal: token.signal}), sectorRequest('LEAF', {signal: token.signal})] : [sectorRequest('FLAT', {signal: token.signal})];
        Promise.all(requests).then(function (results) {
            if (!viewRequestActive('sectors', token)) return;
            var rootResult = results[0];
            var actualDates = rootResult.dates || [];
            showSectorTableGroups(sectorState.type === 'INDUSTRY');
            if (sectorState.type === 'INDUSTRY') {
                renderSectorTable('sector-root-table', rootResult);
                renderSectorTable('sector-leaf-table', results[1]);
            } else {
                renderSectorTable('sector-flat-table', rootResult);
            }
            var total = results.reduce(function (sum, result) { return sum + (result.total || 0); }, 0);
            var layoutName = sectorState.type === 'INDUSTRY' ? '一级大板块、细分行业分别展示' : '平级板块单表展示';
            document.getElementById('sector-basis').textContent = '当前分类已加载 ' + total + ' 个板块 · ' + layoutName + ' · 每表默认展示前 15 个 · 截止 ' + display(rootResult.as_of_trade_date) + ' · 请求 ' + sectorState.days + ' 日，实际可用 ' + actualDates.length + ' 日 · ' + display(rootResult.snapshot_id) + ' · ' + display('RECONSTRUCTED');
            setNotice('已加载 ' + total + ' 个 ' + typeName + '板块；' + layoutName + '；截止 ' + display(rootResult.as_of_trade_date) + '；请求 ' + sectorState.days + ' 日，实际可用 ' + actualDates.length + ' 日。');
        }).catch(function (error) {
            if (!viewRequestActive('sectors', token) || error.name === 'AbortError') return;
            showSectorTableGroups(sectorState.type === 'INDUSTRY');
            var targets = sectorState.type === 'INDUSTRY' ? ['sector-root-table', 'sector-leaf-table'] : ['sector-flat-table'];
            var unavailable = error.code === 'ANALYSIS_NOT_BUILT' || error.code === 'BASIS_UNAVAILABLE';
            targets.forEach(function (id) {
                var target = document.getElementById(id);
                target.replaceChildren();
                var empty = document.createElement('p');
                empty.className = 'empty';
                empty.textContent = unavailable ? 'M9 板块周期快照尚未生成；请先运行 M8/M9 预览构建。' : '暂无周期数据：' + error.message;
                target.appendChild(empty);
            });
            document.getElementById('sector-basis').textContent = unavailable ? '当前发布版本未提供可用的 M9 板块周期分析快照。' : '板块周期数据读取失败。';
            setNotice(unavailable ? 'M9 板块周期尚未生成：请先运行 M8/M9 预览构建。' : '板块周期读取失败：' + error.message, true);
        });
    }

    var mainlinePredicateMeaning = {
        history_minimum_3_observations: '有效板块 RPS20 分位是否至少有 3 个交易日',
        history_minimum_5_observations: '有效板块 RPS20 分位是否至少有 5 个交易日',
        history_minimum_10_observations: '有效板块 RPS20 分位是否至少有 10 个交易日',
        current_coverage_ge_080: '当前板块成员数据覆盖率是否达到 80%',
        fading_was_listed: '可用的近 20 日历史中是否曾达到主线入选阈值',
        fading_current_below_060: '当前 RPS20 分位是否低于 60%',
        fading_percentile_delta_le_neg_015: '相对 3 个交易日前的 RPS20 分位是否下降至少 15 个百分点',
        fading_breadth_declined: '上涨成员宽度是否比 3 个交易日前下降',
        fading_amount_declined: '同一共同成员集合上的正式金额 A 是否比 3 个交易日前下降',
        contraction_current_ge_080: '当前仍处于 RPS20 分位 80% 以上高位',
        contraction_breadth_declined: '上涨成员宽度是否明显收缩',
        contraction_retention_lt_050: '强势成员留存率是否低于 50%',
        reaccelerating_on_list_10_ge_3: '近 10 日达到入选阈值的天数是否至少 3 天',
        reaccelerating_current_ge_080: '当前是否仍处于 80% 以上高位',
        reaccelerating_percentile_improved: '近 3 日 RPS20 分位是否改善至少 10 个百分点',
        reaccelerating_breadth_improved: '近 3 日上涨成员宽度是否改善至少 10 个百分点',
        reaccelerating_amount_ge_120: '正式板块金额 A 是否达到过去 20 日基准的 120%',
        sustained_on_list_5_ge_3: '近 5 日达到入选阈值的天数是否至少 3 天',
        sustained_consecutive_ge_2: '连续达到入选阈值是否至少 2 天',
        sustained_breadth_ge_050: '当前上涨成员宽度是否至少 50%',
        sustained_retention_ge_060: '强势成员留存率是否至少 60%',
        new_current_ge_080: '当前是否首次达到 80% 以上高位条件',
        new_prior_on_list_5_le_1: '当前日前连续 5 个历史位置中达到入选阈值是否不超过 1 天',
        new_breadth_ge_055: '当前上涨成员宽度是否至少 55%',
        new_amount_ge_110: '正式板块金额 A 是否达到过去 20 日基准的 110%',
        new_entered_gt_exited: '进入强势成员数是否多于退出强势成员数',
        broadening_current_ge_070: '当前 RPS20 分位是否至少 70%',
        broadening_entered_gt_exited: '进入强势成员数是否多于退出强势成员数',
        broadening_breadth_improved: '上涨成员宽度是否改善至少 10 个百分点',
        fading: '退潮组合条件是否全部成立', high_level_contraction: '高位收缩组合条件是否全部成立',
        reaccelerating: '再加速组合条件是否全部成立', sustained: '持续组合条件是否全部成立',
        sustained_current_ge_080: '持续状态当前是否仍处于 80% 以上高位', new: '新晋组合条件是否全部成立',
        broadening: '扩散组合条件是否全部成立'
    };
    var mainlinePredicateLabel = {
        history_minimum_3_observations: '有效历史数量（观察）', history_minimum_5_observations: '有效历史数量（快速状态）', history_minimum_10_observations: '有效历史数量（稳定状态）', current_coverage_ge_080: '当前覆盖率',
        fading_was_listed: '过去曾经入选', fading_current_below_060: '当前强度低于60%',
        fading_percentile_delta_le_neg_015: '强度明显回落', fading_breadth_declined: '上涨宽度下降', fading_amount_declined: '成交额走弱',
        contraction_current_ge_080: '仍处高位', contraction_breadth_declined: '上涨宽度收缩', contraction_retention_lt_050: '成员留存偏低',
        reaccelerating_on_list_10_ge_3: '10日高位次数', reaccelerating_current_ge_080: '当前处于高位', reaccelerating_percentile_improved: '强度重新改善',
        reaccelerating_breadth_improved: '宽度重新改善', reaccelerating_amount_ge_120: '成交额扩张', sustained_on_list_5_ge_3: '5日高位次数',
        sustained_consecutive_ge_2: '连续高位天数', sustained_breadth_ge_050: '上涨宽度达标', sustained_retention_ge_060: '成员留存达标',
        new_current_ge_080: '新晋当前高位', new_prior_on_list_5_le_1: '此前较少入选', new_breadth_ge_055: '新晋宽度达标',
        new_amount_ge_110: '新晋成交额达标', new_entered_gt_exited: '进入成员多于退出', broadening_current_ge_070: '扩散强度达标',
        broadening_entered_gt_exited: '扩散成员增加', broadening_breadth_improved: '扩散宽度改善',
        fading: '退潮组合判断', high_level_contraction: '高位收缩组合判断', reaccelerating: '再加速组合判断',
        sustained: '持续组合判断', sustained_current_ge_080: '持续当前高位', new: '新晋组合判断', broadening: '扩散组合判断'
    };
    var mainlineClassMeaning = {
        DATA_INSUFFICIENT: '历史观察或关键输入不足，暂不下结论', FADING: '曾经强势，但当前强度、宽度或成交额共同转弱',
        HIGH_LEVEL_CONTRACTION: '仍在高位，但上涨宽度或强势成员留存收缩', REACCELERATING: '中期仍强，近期强度、宽度和成交额重新改善',
        SUSTAINED: '连续处于高位，宽度和成员留存保持稳定', NEW: '近期新进入高位，并出现成员和成交额扩张',
        BROADENING: '强度达到扩散区间，且上涨宽度改善', OBSERVING: '历史尚未达到正式状态门槛，保留在短期观察池'
    };
    var mainlineClassLabel = {
        DATA_INSUFFICIENT: '数据不足', FADING: '退潮', HIGH_LEVEL_CONTRACTION: '高位收缩',
        REACCELERATING: '再加速', SUSTAINED: '持续', NEW: '新晋', BROADENING: '扩散', OBSERVING: '观察中'
    };
    function mainlineClassText(value) {
        return mainlineClassLabel[value] || display(value);
    }
    var mainlineTransitionMeaning = {
        UNCHANGED: '保持不变', MODEL_CHANGE: '模型合同变化', BASIS_CHANGE: '历史口径变化',
        DATA_INSUFFICIENT: '变为数据不足', FADING: '变为退潮', HIGH_LEVEL_CONTRACTION: '变为高位收缩',
        REACCELERATING: '变为再加速', SUSTAINED: '变为持续', NEW: '变为新晋', BROADENING: '变为扩散', OBSERVING: '变为观察中'
    };
    var mainlineConflictMeaning = {
        OBSERVATION_HISTORY_NOT_REACHED: '有效 RPS20 观察日不足 3 天',
        BASE_INPUT_UNKNOWN: '当前成员覆盖率缺失或未达到合同要求，暂不做正式分类',
        UNKNOWN_HIGHER_PRIORITY: '更高优先级状态的条件未知，因此不下调为低优先级状态',
        FAST_HISTORY_NOT_REACHED: '有效历史尚未达到快速状态所需的 5 天',
        STABLE_HISTORY_NOT_REACHED: '有效历史尚未达到稳定状态所需的 10 天'
    };
    function mainlineTransitionLabel(value) {
        return mainlineTransitionMeaning[value] || display(value);
    }

    function mainlinePredicateRows(predicates) {
        return Object.keys(predicates || {}).map(function (key) {
            var value = predicates[key];
            return {key: key, predicate: mainlinePredicateLabel[key] || key, meaning: mainlinePredicateMeaning[key] || '该条件的业务解释尚未登记', result: value === true ? '满足' : value === false ? '不满足' : '未知（缺少数据）'};
        });
    }

    var mainlinePredicateGroupDefs = [
        {title: '历史与数据门槛', keys: ['history_minimum_3_observations', 'history_minimum_5_observations', 'history_minimum_10_observations', 'current_coverage_ge_080', 'fading_was_listed', 'reaccelerating_on_list_10_ge_3', 'sustained_on_list_5_ge_3', 'sustained_consecutive_ge_2', 'new_prior_on_list_5_le_1']},
        {title: '持续与强度条件', keys: ['fading_current_below_060', 'fading_percentile_delta_le_neg_015', 'contraction_current_ge_080', 'reaccelerating_current_ge_080', 'reaccelerating_percentile_improved', 'new_current_ge_080', 'broadening_current_ge_070', 'sustained_current_ge_080']},
        {title: '上涨宽度条件', keys: ['fading_breadth_declined', 'contraction_breadth_declined', 'reaccelerating_breadth_improved', 'sustained_breadth_ge_050', 'new_breadth_ge_055', 'broadening_breadth_improved']},
        {title: '成交额条件', keys: ['fading_amount_declined', 'reaccelerating_amount_ge_120', 'new_amount_ge_110']},
        {title: '成员变化与留存', keys: ['contraction_retention_lt_050', 'sustained_retention_ge_060', 'new_entered_gt_exited', 'broadening_entered_gt_exited']},
        {title: '最终组合判断', keys: ['fading', 'high_level_contraction', 'reaccelerating', 'sustained', 'new', 'broadening']}
    ];
    function mainlinePredicateSections(predicates) {
        var rows = mainlinePredicateRows(predicates);
        var used = {};
        var sections = mainlinePredicateGroupDefs.map(function (group) {
            var groupRows = rows.filter(function (row) { return group.keys.indexOf(row.key) >= 0; });
            groupRows.forEach(function (row) { used[row.key] = true; });
            return groupRows.length ? {title: group.title, type: 'table', columns: [{label: '条件', key: 'predicate'}, {label: '它在检查什么', key: 'meaning'}, {label: '结果', key: 'result'}], rows: groupRows} : null;
        }).filter(function (section) { return section; });
        var otherRows = rows.filter(function (row) { return !used[row.key]; });
        if (otherRows.length) sections.push({title: '其他条件', type: 'table', columns: [{label: '条件', key: 'predicate'}, {label: '它在检查什么', key: 'meaning'}, {label: '结果', key: 'result'}], rows: otherRows});
        return sections;
    }

    function mainlineMissingLabels(fields) {
        return (fields || []).map(function (field) {
            if (field === 'sector_rs20_pct_3_observations') return '板块 RPS20 分位至少需要 3 个有效交易日';
            if (field === 'sector_rs20_pct_5_observations') return '达到快速状态至少需要 5 个有效交易日';
            if (field === 'sector_rs20_pct_10_observations') return '达到稳定状态至少需要 10 个有效交易日';
            if (field === 'coverage') return '当前成员覆盖率缺失或未达到合同要求';
            if (field === 'recent_listing_history') return '缺少可判断近期是否曾入选的历史';
            if (field === 'sector_rs20_pct_comparison_3d') return '缺少 3 日强度比较值';
            if (field === 'breadth_ret1_comparison_3d') return '缺少 3 日上涨宽度比较值';
            if (field === 'amount_vs_prior20_comparison_3d') return '缺少旧兼容金额比较值';
            if (field === 'sector_amount_ratio_delta_3sessions_common') return '缺少正式金额 A 三交易日共同集合比较值';
            if (field === 'retention_rate') return '缺少强势成员留存率';
            if (field === 'on_list_days_5') return '缺少完整 5 日入选窗口';
            if (field === 'on_list_days_10') return '缺少完整 10 日入选窗口';
            if (field === 'current_amount_vs_prior20') return '缺少旧兼容金额字段';
            if (field === 'sector_amount_vs_prior20') return '缺少正式板块金额 A';
            if (field === 'member_change_counts') return '缺少可比较的成员进入/退出数据';
            if (field === 'breadth_ret1_previous_day') return '缺少前一日上涨宽度';
            return field;
        });
    }

    function mainlineHistoryStage(validDays, policy) {
        policy = policy || {observation_min: 3, fast_min: 5, stable_min: 10, long_evidence_min: 20};
        var value = Number(validDays || 0);
        if (value < policy.observation_min) return '数据不足 ' + value + '/' + policy.observation_min;
        if (value < policy.fast_min) return '短期观察 ' + value + '/' + policy.fast_min;
        if (value < policy.stable_min) return '快速状态 ' + value + '/' + policy.stable_min;
        if (value < policy.long_evidence_min) return '稳定状态 ' + value + '/' + policy.long_evidence_min;
        return '完整证据 ' + value + '日';
    }

    function showMainlineEvidence(row) {
        modal.open('主线证据 · ' + display(row.sector_name), '正在读取主线证据…');
        var token = beginModalRequest();
        api.mainlineEvidence({
            publication_id: current.publication_id,
            sector_id: row.sector_id,
            days: mainlineState.days
        }, {signal: token.signal}).then(function (result) {
            if (!modalRequestActive(token)) return;
            releaseModalRequest(token);
            mainlineState.historyPolicy = result.history_policy || mainlineState.historyPolicy;
            var points = (result.points || []).slice().reverse().map(function (point) {
                return {
                    trade_date: point.trade_date,
                    class_name: mainlineClassText(point.mainline_class),
                    percentile: percent(point.current_percentile),
                    breadth: percent(point.current_breadth),
                    retention: percent(point.retention_rate),
                    transition: mainlineTransitionLabel(point.transition),
                    missing: mainlineMissingLabels(point.missing_fields).join('、') || '—'
                };
            });
            points.forEach(function (item, index) {
                var source = (result.points || []).slice().reverse()[index] || {};
                item.amount = source.current_sector_amount_vs_prior20 == null ? '—' : Number(source.current_sector_amount_vs_prior20).toFixed(2);
            });
            var currentPoint = result.points && result.points.length ? result.points[result.points.length - 1] : row;
            modal.open('主线证据 · ' + display(row.sector_name), modalContent('先看“当前分类”：' + (mainlineClassMeaning[currentPoint.mainline_class] || '当前分类由版本化硬条件决定') + '。条件“满足”表示成立，“不满足”表示未成立，“未知”表示历史或输入字段不足；未知不等于反向信号，也不等于退潮。', [{
                title: '当前分类',
                rows: [{label: '板块', value: row.sector_name}, {label: '展示分组', value: row.hierarchy_level || row.mainline_group || '—'}, {label: '分类', value: mainlineClassText(currentPoint.mainline_class)}, {label: '分类含义', value: mainlineClassMeaning[currentPoint.mainline_class] || '—'}, {label: '历史阶段', value: mainlineHistoryStage(currentPoint.valid_observation_days, result.history_policy)}, {
                    label: '历史基础',
                    value: display(currentPoint.history_basis)
                }, {label: '有效观察', value: display(currentPoint.valid_observation_days, 0) + ' / ' + display(currentPoint.observation_days, 0) + ' 天'}, {label: '当前强度 / 宽度', value: percent(currentPoint.current_percentile) + ' / ' + percent(currentPoint.current_breadth)}, {label: '合同版本', value: currentPoint.contract_id}, {label: '缺失字段', value: mainlineMissingLabels(currentPoint.missing_fields).join('、') || '无'}, {
                    label: '冲突解释',
                    value: currentPoint.conflict_resolution ? (mainlineConflictMeaning[currentPoint.conflict_resolution] || currentPoint.conflict_resolution) : '无'
                }]
            }].concat(mainlinePredicateSections(currentPoint.predicates), [{
                title: '历史变化',
                type: 'table',
                columns: [{label: '交易日', key: 'trade_date'}, {label: '分类', key: 'class_name'}, {label: '强度百分位', key: 'percentile'}, {label: '金额 A', key: 'amount'}, {
                    label: '上涨宽度',
                    key: 'breadth'
                }, {label: '成员留存', key: 'retention'}, {label: '状态变化', key: 'transition'}, {label: '缺失字段', key: 'missing'}],
                rows: points
            }])));
        }).catch(function (error) {
            if (!modalRequestActive(token) || error.name === 'AbortError') return;
            releaseModalRequest(token);
            modal.open('主线证据 · ' + display(row.sector_name), modalContent('主线证据暂时无法读取。', [{title: '原因', rows: [{label: '提示', value: error.message}]}]));
        });
    }

    function mainlineColumns() {
        return [{label: '板块', key: 'sector_name'}, {label: '主线分类', value: function (row) { return mainlineClassText(row.mainline_class); }}, {label: '历史阶段', value: function (row) { return mainlineHistoryStage(row.valid_observation_days, mainlineState.historyPolicy); }}, {label: '连续入选', value: function (row) { return display(row.consecutive_on_list, 0) + ' 天'; }}, {label: '5/10/20日入选', value: function (row) { var counts = row.on_list_days || {}; return [counts['5'], counts['10'], counts['20']].map(function (value) { return display(value, 0); }).join(' / '); }}, {label: 'RPS20分位', value: function (row) { return percent(row.current_percentile); }}, {label: '上涨宽度', value: function (row) { return percent(row.current_breadth); }}, {label: '金额 A', value: function (row) { return row.current_sector_amount_vs_prior20 == null ? '—' : Number(row.current_sector_amount_vs_prior20).toFixed(2); }}, {label: '成员留存', value: function (row) { return percent(row.retention_rate); }}, {label: '状态变化', value: function (row) { return mainlineTransitionLabel(row.transition); }}, {label: '证据', action: {label: '查看', onClick: showMainlineEvidence}}];
    }

    var mainlineStatusOrder = [
        {key: 'FADING', help: '强度、宽度或成交额走弱'},
        {key: 'HIGH_LEVEL_CONTRACTION', help: '高位但宽度或留存收缩'},
        {key: 'REACCELERATING', help: '近期强度、宽度和成交额改善'},
        {key: 'SUSTAINED', help: '连续高位且结构稳定'},
        {key: 'NEW', help: '近期新进入高位并扩张'},
        {key: 'BROADENING', help: '强度与上涨宽度扩散'},
        {key: 'OBSERVING', help: '短期观察池，尚未形成正式状态'},
        {key: 'DATA_INSUFFICIENT', help: '历史或关键输入仍不足'}
    ];
    function renderMainlineStatusCards(counts) {
        var target = document.getElementById('mainline-status-cards');
        if (!target) return;
        target.replaceChildren();
        var total = mainlineStatusOrder.reduce(function (sum, item) { return sum + Number(counts[item.key] || 0); }, 0);
        var all = [{key: '', label: '全部状态', help: '当前快照内全部板块', count: total}].concat(mainlineStatusOrder.map(function (item) {
            return {key: item.key, label: mainlineClassText(item.key), help: item.help, count: Number(counts[item.key] || 0)};
        }));
        all.forEach(function (item) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'mainline-status-card' + (mainlineState.className === item.key ? ' active' : '');
            button.setAttribute('aria-pressed', mainlineState.className === item.key ? 'true' : 'false');
            var label = document.createElement('span'); label.className = 'mainline-status-card-label'; label.textContent = item.label;
            var count = document.createElement('span'); count.className = 'mainline-status-card-count'; count.textContent = String(item.count);
            var help = document.createElement('span'); help.className = 'mainline-status-card-help'; help.textContent = item.help;
            button.append(label, count, help);
            button.addEventListener('click', function () {
                mainlineState.className = item.key;
                document.getElementById('mainline-class').value = item.key;
                renderMainlineStatusCards(counts);
                loadMainlines();
            });
            target.appendChild(button);
        });
    }

    function loadMainlines() {
        if (!current) return;
        var token = beginViewRequest('mainlines');
        setNotice('正在读取主线周期…');
        var groups = [{key: 'INDUSTRY_ROOT', target: 'mainline-industry-root-table', limit: 10}, {key: 'INDUSTRY_LEAF', target: 'mainline-industry-leaf-table', limit: 20}, {key: 'THEME', target: 'mainline-theme-table', limit: 20}];
        Promise.all(groups.map(function (group) {
            return api.mainlines({publication_id: current.publication_id, page: 1, page_size: group.limit, class: mainlineState.className, days: mainlineState.days, group: group.key}, {signal: token.signal}).then(function (result) { return {group: group, result: result}; });
        })).then(function (results) {
            if (!viewRequestActive('mainlines', token)) return;
            var total = 0, shown = 0, allTotal = 0, cutoff = null, snapshot = null, classCounts = {};
            results.forEach(function (entry) {
                var items = entry.result.items || [];
                if (entry.result.history_policy) mainlineState.historyPolicy = entry.result.history_policy;
                total += entry.result.total || 0; shown += items.length;
                Object.keys(entry.result.class_counts || {}).forEach(function (key) { classCounts[key] = (classCounts[key] || 0) + Number(entry.result.class_counts[key] || 0); });
                cutoff = cutoff || (items.length ? items[0].trade_date : (entry.result.dates || [])[0]); snapshot = snapshot || entry.result.snapshot_id;
                var target = document.getElementById(entry.group.target);
                if (items.length) table.render(target, mainlineColumns(), items);
                else { target.replaceChildren(); var empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = '该分组暂无符合条件的主线状态。'; target.appendChild(empty); }
            });
            allTotal = Object.keys(classCounts).reduce(function (sum, key) { return sum + Number(classCounts[key] || 0); }, 0);
            renderMainlineStatusCards(classCounts);
            document.getElementById('mainline-basis').textContent = '主线快照共 ' + allTotal + ' 个板块 · 当前筛选后 ' + total + ' 个 · 展示 ' + shown + ' 条 · 截止 ' + display(cutoff) + ' · 证据回看 ' + mainlineState.days + ' 日 · ' + display(snapshot) + ' · 内部/未知类型已排除';
            setNotice('已加载 ' + total + ' 个主线状态；一级行业、细分行业和概念分别展示。');
        }).catch(function (error) {
            if (!viewRequestActive('mainlines', token) || error.name === 'AbortError') return;
            var errorCode = error.code || error.message;
            var analysisUnavailable = errorCode === 'ANALYSIS_NOT_BUILT';
            var mainlineUnavailable = errorCode === 'MAINLINE_NOT_BUILT';
            ['mainline-industry-root-table', 'mainline-industry-leaf-table', 'mainline-theme-table'].forEach(function (id) { var target = document.getElementById(id); target.replaceChildren(); var empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = mainlineUnavailable ? 'M10 主线快照尚未生成；当前不会用板块排名临时替代主线分类。' : analysisUnavailable ? '当前发布版本未绑定分析快照；请先生成 M8/M9，再生成 M10。' : '暂无主线数据：' + error.message; target.appendChild(empty); });
            document.getElementById('mainline-basis').textContent = analysisUnavailable ? '当前发布版本未绑定可用分析快照；请先生成 M8/M9，再生成 M10。' : '当前发布版本未提供可用的 M10 主线分析快照。';
            renderMainlineStatusCards({});
            setNotice(analysisUnavailable ? '当前版本未生成 M8/M9/M10 分析数据。' : mainlineUnavailable ? 'M10 主线快照尚未生成。' : '主线周期读取失败：' + error.message, true);
        });
    }

    function parseSectorIds(value) {
        return String(value || '').split(/[,，\s]+/).map(function (item) { return item.trim(); }).filter(Boolean);
    }

    function resolveSectorTokens(tokens, signal) {
        var unique = [];
        tokens.forEach(function (token) { if (unique.indexOf(token) < 0) unique.push(token); });
        return Promise.all(unique.map(function (token) {
            if (token.indexOf(':') >= 0) return Promise.resolve(token);
            return api.sectorLibrary({publication_id: current.publication_id, page: 1, page_size: 100, q: token, basis: 'RECONSTRUCTED'}, {signal: signal}).then(function (result) {
                var items = result.items || [], normalized = token.toLowerCase();
                var exact = items.filter(function (item) { return String(item.sector_name || '').toLowerCase() === normalized || String(item.sector_id || '').toLowerCase() === normalized; });
                var matches = exact.length ? exact : items.filter(function (item) { return String(item.sector_name || '').toLowerCase().indexOf(normalized) >= 0; });
                if (matches.length !== 1) throw new Error('板块名称“' + token + '”无法唯一匹配，请改用更完整名称或在属性库确认板块ID。');
                return matches[0].sector_id;
            });
        }));
    }

    function setLinkageMode(mode) {
        linkageState.mode = mode;
        linkageState.page = 1;
        document.querySelectorAll('.linkage-tab').forEach(function (button) {
            button.classList.toggle('active', button.dataset.linkageMode === mode);
            button.setAttribute('aria-selected', button.dataset.linkageMode === mode ? 'true' : 'false');
        });
        document.getElementById('linkage-attributes-controls').hidden = mode !== 'attributes';
        document.getElementById('linkage-linkage-controls').hidden = mode !== 'linkage';
        document.getElementById('linkage-intersection-controls').hidden = mode !== 'intersection';
        var heading = mode === 'attributes' ? '属性库' : mode === 'linkage' ? '关联联动' : '交叉筛选';
        var description = mode === 'attributes' ? '按板块类型和语义查看可追溯的板块属性；标签不自动当作强势关联。' : mode === 'linkage' ? '板块查股票或股票查板块；成员名次来自同一日快照，筛选不会重排。' : '先做板块集合运算，再做同一快照的技术/结构筛选；交集、并集和排除口径分开显示。';
        document.getElementById('linkage-heading').textContent = heading;
        document.getElementById('linkage-description').textContent = description;
        document.getElementById('linkage-result-description').textContent = description;
        if (currentPage === 'linkage') loadLinkage();
    }

    function renderLinkageResult(result, mode) {
        var target = document.getElementById('linkage-table'), items = result.items || [];
        var columns;
        if (mode === 'attributes') {
            columns = [{label: '板块', key: 'sector_name'}, {label: '类型', value: function (row) { return display(row.sector_type); }}, {label: '语义', value: function (row) { return display(row.semantic_bucket); }}, {label: '成员数', key: 'total_member_count'}, {label: '有效数', key: 'valid_count'}, {label: '操作', action: {label: '查看成员', onClick: function (row) { linkageState.sectorId = row.sector_id; document.getElementById('linkage-sector-id').value = row.sector_id; setLinkageMode('linkage'); }}}];
        } else if (mode === 'linkage') {
            columns = [{label: '板块', key: 'sector_name'}, {label: '板块ID', key: 'sector_id'}, {label: '股票代码', key: 'security_id'}, {label: '股票名称', key: 'security_name'}, {label: '板块内名次', key: 'sector_member_rank'}, {label: '成员总数', key: 'sector_member_count'}, {label: '强势关联', value: function (row) { var association = row.association || {}; return association.eligible ? (association.rank === 1 ? '主选' : '备选 ' + association.rank) : association.eligible === false ? '未通过' : '暂无'; }}, {label: '透视', action: {label: '打开', onClick: showStockInsight}}];
        } else {
            columns = [{label: '股票代码', key: 'security_id'}, {label: '股票名称', key: 'security_name'}, {label: '命中板块数', key: 'matched_sector_count'}, {label: '命中板块', value: function (row) { return (row.matched_sector_ids || []).join('、'); }}, {label: 'RPS20', value: function (row) { return percent(row.rps20); }}, {label: 'RET20', value: function (row) { return percent(row.ret20); }}, {label: '研究级别', value: function (row) { return display(row.research_band); }}, {label: '透视', action: {label: '打开', onClick: showStockInsight}}];
        }
        table.render(target, columns, items);
        var pages = Math.max(1, Math.ceil(Number(result.total || 0) / Number(result.page_size || 50)));
        document.getElementById('linkage-page-label').textContent = '第 ' + (result.page || 1) + ' 页 / 共 ' + pages + ' 页 · ' + (result.total || 0) + ' 条';
        document.getElementById('linkage-prev').disabled = (result.page || 1) <= 1;
        document.getElementById('linkage-next').disabled = (result.page || 1) >= pages;
        var basis = display(result.history_basis || result.resolved_basis || 'RECONSTRUCTED');
        var resultLabel = mode === 'attributes' ? 'M11 属性库结果' : mode === 'linkage' ? 'M11 关联结果' : 'M11 交叉筛选结果';
        document.getElementById('linkage-basis').textContent = resultLabel + ' ' + (result.total || 0) + ' 条 · 快照 ' + display(result.snapshot_id) + ' · 截止 ' + display(result.trade_date) + ' · 历史基础 ' + basis;
    }

    function renderLinkageEmpty(message) {
        var target = document.getElementById('linkage-table');
        target.replaceChildren();
        var empty = document.createElement('p');
        empty.className = 'empty';
        empty.textContent = message;
        target.appendChild(empty);
    }

    function loadLinkage() {
        if (!current) return;
        var token = beginViewRequest('linkage');
        var mode = linkageState.mode;
        linkageState.days = Number(document.getElementById('linkage-days').value || 10);
        setNotice('正在读取联动结果…');
        var request;
        if (mode === 'attributes') {
            linkageState.attributeType = document.getElementById('linkage-attribute-type').value;
            linkageState.attributeBucket = document.getElementById('linkage-attribute-bucket').value;
            linkageState.attributeQuery = document.getElementById('linkage-attribute-query').value.trim();
            request = api.sectorLibrary({publication_id: current.publication_id, page: linkageState.page, page_size: 50, type: linkageState.attributeType, bucket: linkageState.attributeBucket, q: linkageState.attributeQuery, basis: 'RECONSTRUCTED'}, {signal: token.signal});
        } else if (mode === 'intersection') {
            linkageState.includeSectors = document.getElementById('linkage-include-sectors').value;
            linkageState.operator = document.getElementById('linkage-operator').value;
            linkageState.excludeSectors = document.getElementById('linkage-exclude-sectors').value;
            var includeTokens = parseSectorIds(linkageState.includeSectors), excludeTokens = parseSectorIds(linkageState.excludeSectors);
            if (includeTokens.length < 2) { setNotice('交叉筛选至少需要两个纳入板块。', true); renderLinkageEmpty('请输入至少两个板块名称或ID后刷新。'); return; }
            request = Promise.all([resolveSectorTokens(includeTokens, token.signal), resolveSectorTokens(excludeTokens, token.signal)]).then(function (resolved) {
                var include = resolved[0], exclude = resolved[1];
                document.getElementById('linkage-basis').textContent = '已将板块名称解析为板块ID，正在读取交叉结果…';
                return api.sectorIntersectionQuery({publication_id: current.publication_id, basis: 'RECONSTRUCTED', include_sector_ids: include, exclude_sector_ids: exclude, operator: linkageState.operator, filters: {}, sort: 'rps20.desc', page: linkageState.page, page_size: 50}, {signal: token.signal});
            });
        } else {
            linkageState.sectorId = document.getElementById('linkage-sector-id').value.trim();
            linkageState.securityId = document.getElementById('linkage-security-id').value.trim();
            linkageState.stockQuery = document.getElementById('linkage-stock-query').value.trim();
            linkageState.tradeDate = document.getElementById('linkage-trade-date').value;
            if (!linkageState.sectorId && !linkageState.securityId) { setNotice('请输入板块ID或股票代码后刷新。', true); renderLinkageEmpty('请输入板块ID或股票代码后查询。'); return; }
            request = api.linkage({publication_id: current.publication_id, sector_id: linkageState.sectorId, security_id: linkageState.securityId, q: linkageState.stockQuery, trade_date: linkageState.tradeDate, basis: 'RECONSTRUCTED', page: linkageState.page, page_size: 50}, {signal: token.signal});
        }
        request.then(function (result) { if (!viewRequestActive('linkage', token)) return; renderLinkageResult(result, mode); setNotice('联动结果已加载。'); }).catch(function (error) { if (!viewRequestActive('linkage', token) || error.name === 'AbortError') return; renderLinkageEmpty('联动数据暂不可用：' + error.message); document.getElementById('linkage-basis').textContent = '请检查板块名称是否唯一，或当前发布版本是否已绑定 M11 分析快照。'; setNotice('联动读取失败：' + error.message, true); });
    }

    function loadMarket() {
        if (!current) return;
        var token = beginViewRequest('market');
        var days = Number(document.getElementById('market-days').value || 60);
        loadLimitViews();
        loadHotRank();
        setNotice('正在读取市场历史聚合…');
        api.marketCycle({publication_id: current.publication_id, days: days, basis: 'RECONSTRUCTED', metrics: 'breadth,amount,ma,new_high,queues'}, {signal: token.signal}).then(function (result) {
            if (!viewRequestActive('market', token)) return;
            var points = result.points || [];
            renderMarketCharts(points);
            table.render(document.getElementById('market-table'), [{label: '交易日', key: 'trade_date'}, {label: '有效报价', key: 'quote_valid_count'}, {label: '涨 / 跌 / 平', value: function (row) { return [row.up_count, row.down_count, row.flat_count].join(' / '); }}, {label: '成交额', value: function (row) { return amountOrDash(row.amount_sum); }}, {label: 'MA20上方', value: function (row) { return row.ma20_above_count === null || row.ma20_valid_count === 0 ? '暂无' : row.ma20_above_count + ' / ' + row.ma20_valid_count; }}, {label: 'MA60上方', value: function (row) { return row.ma60_above_count === null || row.ma60_valid_count === 0 ? '暂无' : row.ma60_above_count + ' / ' + row.ma60_valid_count; }}, {label: '新高', value: function (row) { return Object.keys(row.new_high_counts || {}).map(function (key) { return key + '日 ' + row.new_high_counts[key].hit_count; }).join('、') || '暂无'; }}, {label: '明细', action: {label: '查看', onClick: openMarketDetail}}], points);
            document.getElementById('market-basis').textContent = '共 ' + points.length + ' 个交易日 · 快照 ' + display(result.snapshot_id) + ' · 历史基础 ' + display(result.history_basis) + ' · ' + statisticalScopeDescription(result.statistical_scope) + ' · 个股下钻' + displayScopeDescription(result.display_scope).replace('展示范围', '按展示范围') + ' · 涨跌停状态尚未构建时不填 0。';
            setNotice('市场历史聚合已加载。');
        }).catch(function (error) { if (!viewRequestActive('market', token) || error.name === 'AbortError') return; document.querySelectorAll('#market-charts .market-chart').forEach(function (chart) { chart.replaceChildren(); }); document.getElementById('market-table').replaceChildren(); var empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = '市场周期暂不可用：' + error.message; document.getElementById('market-table').appendChild(empty); setNotice('市场周期读取失败：' + error.message, true); });
    }

    function renderDataInfo() {
        var target = document.getElementById('data-info-table');
        if (!current) { overviewEmpty('data-info-table', '当前发布版本尚未加载。'); return; }
        document.getElementById('data-info-basis').textContent = '当前发布 ' + current.publication_id + ' · 交易日 ' + current.trade_date + ' · 路由状态可由地址栏恢复。';
        table.render(target, [{label: '能力', key: 'label'}, {label: '当前状态', key: 'status'}, {label: '合同/说明', key: 'contract'}], [
            {label: '发布与输入身份', status: '已绑定', contract: 'API01 / API02 · publication_id 固定'},
            {label: '市场周期', status: '按发布能力显示', contract: 'M13 market_cycle · 缺失字段保持暂无'},
            {label: '板块与主线', status: '独立快照降级', contract: 'M9/M10 · 主线不由板块排名临时替代'},
            {label: '个股透视', status: '可从表格进入抽屉', contract: 'M12 · URL 保留 security_id/tab/days'},
            {label: '在线热榜', status: '请求时读取', contract: 'M14 · 不保存 raw payload、批次或历史快照'}
        ]);
    }

    function showPage(page, options) {
        options = options || {};
        if (page === 'mainlines') { page = 'sectors'; options.subpage = 'mainlines'; }
        page = router.normalizePage(page);
        if (page === 'sectors') sectorSubpage = router.subpages.indexOf(options.subpage) >= 0 ? options.subpage : sectorSubpage;
        else sectorSubpage = 'sectors';
        currentPage = page;
        if (!options.fromRoute) router.navigate(page, {subpage: sectorSubpage});
        cancelHiddenViewRequests(page, sectorSubpage);
        document.querySelectorAll('.nav-item').forEach(function (item) {
            item.classList.toggle('active', item.dataset.page === page);
        });
        document.querySelectorAll('.secondary-nav-item').forEach(function (item) {
            item.classList.toggle('active', page === 'sectors' && item.dataset.sectorSubpage === sectorSubpage);
        });
        overview.hidden = page !== 'overview';
        marketPage.hidden = page !== 'market';
        technicalPage.hidden = page !== 'stocks';
        sectorsPage.hidden = page !== 'sectors' || sectorSubpage !== 'sectors';
        mainlinePage.hidden = page !== 'sectors' || sectorSubpage !== 'mainlines';
        linkagePage.hidden = page !== 'linkage';
        dataInfoPage.hidden = page !== 'data-info';
        if (page === 'overview') {
            document.getElementById('page-title').textContent = '研究总览';
            document.getElementById('page-description').textContent = '版本、输入身份与统一股票范围；总体统计保留科创板和北交所，个股展示按权限范围处理。';
            loadOverviewAnalysis();
            return;
        }
        if (page === 'market') {
            document.getElementById('page-title').textContent = '市场周期';
            document.getElementById('page-description').textContent = '市场广度、成交额与均线覆盖；统计包含科创板和北交所，个股下钻按展示范围隐藏两者。';
            loadMarket();
            return;
        }
        if (page === 'stocks') {
            document.getElementById('page-title').textContent = '个股技术';
            document.getElementById('page-description').textContent = '新高、RPS、均线与量额状态；个股展示包含科创板和北交所，字段含义和使用方法见页面上方。';
            loadTechnical();
            return;
        }
        if (page === 'sectors') {
            if (sectorSubpage === 'mainlines') {
                document.getElementById('page-title').textContent = '主线周期';
                document.getElementById('page-description').textContent = '主线分类、状态变化与可复核证据；分类来自版本化硬条件，不使用隐藏综合分。';
                loadMainlines();
            } else {
                document.getElementById('page-title').textContent = '板块周期';
                document.getElementById('page-description').textContent = '板块强弱周期与成员变化；板块统计包含科创板和北交所，个股成员展示按权限范围处理。';
                loadSectors();
            }
            return;
        }
        if (page === 'linkage') {
            document.getElementById('page-title').textContent = '联动选股';
            document.getElementById('page-description').textContent = '属性库、关联联动与交叉筛选；结果绑定当前发布版本和分析快照。';
            loadLinkage();
            return;
        }
        if (page === 'data-info') {
            document.getElementById('page-title').textContent = '数据能力';
            document.getElementById('page-description').textContent = '当前发布版本的来源、合同、覆盖和降级状态。';
            renderDataInfo();
        }
    }

    function load(publication) {
        current = publication;
        setNotice('正在读取当前发布版本摘要…');
        context.textContent = '交易日 ' + format.text(publication.trade_date) + ' · 当前发布版本';
        setText('publication-value', publication.trade_date);
        setText('publication-detail', publication.publication_id);
        var identityRequest = api.identity(publication.publication_id, true);
        var universeRequest = api.universeSummary(publication.publication_id);
        var identity = null, universe = null;
        function currentPublication() {
            return current && current.publication_id === publication.publication_id;
        }
        function applyUniverse(universeResponse) {
            if (!currentPublication()) return;
            universe = universeResponse.item || universeResponse || {};
            var displayCount = first(universe, ['display_count', 'quote_valid_count', 'total']);
            var statisticalCount = first(universe, ['statistical_count']);
            setText('universe-value', displayCount === null ? '已加载' : format.number(displayCount, 0) + (statisticalCount === null ? '' : ' / ' + format.number(statisticalCount, 0)));
            setText('universe-detail', universeDescription(universe));
            if (identity) renderContext(publication, identity, universe);
        }
        universeRequest.then(applyUniverse).catch(function (error) {
            if (!currentPublication()) return;
            setText('universe-value', '不可用');
            setText('universe-detail', '范围摘要读取失败：' + error.message);
        });
        identityRequest.then(function (identityResponse) {
            if (!currentPublication()) return;
            identity = identityResponse || {};
            setText('identity-value', first(identity, ['status']) || '已绑定');
            setText('identity-detail', first(identity, ['api_contract', 'contract']) || '输入身份可追溯');
            if (!universe) {
                setText('universe-value', '读取中');
                setText('universe-detail', '范围摘要后台加载中…');
            }
            renderContext(publication, identity, universe);
            setNotice('发布身份已加载；点击板块周期或个股技术查看数据。');
            document.getElementById('identity-evidence').onclick = function () {
                evidenceModal('输入身份证据', '以下内容用于核对当前发布版本绑定的输入来源。', identity);
            };
            document.getElementById('universe-evidence').onclick = function () {
                evidenceModal('统一股票范围说明', '以下内容用于核对股票范围、覆盖和边界。', universe);
            };
            showPage(currentPage, {fromRoute: true, subpage: sectorSubpage});
        }).catch(function (error) {
            if (!currentPublication()) return;
            setNotice('摘要读取失败：' + error.message, true);
        });
    }

    function bindControls() {
        var controls = ['technical-mode', 'technical-window', 'technical-rps-min', 'technical-streak-min', 'technical-ma-state', 'technical-amount-class', 'technical-research-band'];
        controls.forEach(function (id) {
            document.getElementById(id).addEventListener('change', function () {
                technicalState.mode = document.getElementById('technical-mode').value;
                technicalState.window = Number(document.getElementById('technical-window').value);
                technicalState.rpsMin = document.getElementById('technical-rps-min').value;
                technicalState.streakMin = document.getElementById('technical-streak-min').value;
                technicalState.maState = document.getElementById('technical-ma-state').value;
                technicalState.amountClass = document.getElementById('technical-amount-class').value;
                technicalState.researchBand = document.getElementById('technical-research-band').value;
                technicalState.page = 1;
                loadTechnical();
            });
        });
        document.getElementById('technical-refresh').addEventListener('click', loadTechnical);
        document.getElementById('technical-prev').addEventListener('click', function () {
            if (technicalState.page > 1) {
                technicalState.page--;
                loadTechnical();
            }
        });
        document.getElementById('technical-next').addEventListener('click', function () {
            technicalState.page++;
            loadTechnical();
        });
        document.getElementById('market-days').addEventListener('change', loadMarket);
        document.getElementById('market-refresh').addEventListener('click', loadMarket);
        document.getElementById('hot-rank-source').addEventListener('change', function () { hotRankState.page = 1; loadHotRank(); });
        document.getElementById('hot-rank-refresh').addEventListener('click', function () { hotRankState.page = 1; loadHotRank(); });
        document.getElementById('hot-rank-prev').addEventListener('click', function () { if (hotRankState.page > 1) { hotRankState.page--; loadHotRank(); } });
        document.getElementById('hot-rank-next').addEventListener('click', function () { hotRankState.page++; loadHotRank(); });
        ['limit-ladder-level', 'limit-ladder-state', 'limit-ladder-promotion', 'limit-promotion-level'].forEach(function (id) {
            document.getElementById(id).addEventListener('change', function () { limitLadderState.page = 1; loadLimitViews(); });
        });
        document.getElementById('limit-ladder-refresh').addEventListener('click', loadLimitViews);
        document.getElementById('limit-ladder-prev').addEventListener('click', function () { if (limitLadderState.page > 1) { limitLadderState.page--; loadLimitViews(); } });
        document.getElementById('limit-ladder-next').addEventListener('click', function () { limitLadderState.page++; loadLimitViews(); });
        document.getElementById('sector-type').addEventListener('change', function () {
            sectorState.type = this.value;
            sectorState.query = document.getElementById('sector-query').value.trim();
            loadSectors();
        });
        document.getElementById('sector-query').addEventListener('keydown', function (event) {
            if (event.key === 'Enter') { sectorState.query = this.value.trim(); loadSectors(); }
        });
        document.getElementById('sector-days').addEventListener('change', function () {
            sectorState.days = Number(this.value);
            loadSectors();
        });
        document.getElementById('sector-refresh').addEventListener('click', loadSectors);
        document.querySelectorAll('.secondary-nav-item').forEach(function (button) {
            button.addEventListener('click', function () { showPage('sectors', {subpage: button.dataset.sectorSubpage}); });
        });
        document.getElementById('overview-priority-prev').addEventListener('click', function () { if (overviewState.page > 1) { overviewState.page--; loadOverviewAnalysis(); } });
        document.getElementById('overview-priority-next').addEventListener('click', function () { overviewState.page++; loadOverviewAnalysis(); });
        document.getElementById('overview-priority-filter').addEventListener('click', function () { overviewState.page = 1; loadOverviewAnalysis(); });
        ['overview-priority-q', 'overview-priority-grade', 'overview-priority-pattern'].forEach(function (id) {
            document.getElementById(id).addEventListener('keydown', function (event) { if (event.key === 'Enter') { overviewState.page = 1; loadOverviewAnalysis(); } });
        });
        ['mainline-class', 'mainline-days'].forEach(function (id) {
            document.getElementById(id).addEventListener('change', function () {
                mainlineState.className = document.getElementById('mainline-class').value;
                mainlineState.days = Number(document.getElementById('mainline-days').value);
                loadMainlines();
            });
        });
        document.getElementById('mainline-refresh').addEventListener('click', loadMainlines);
        document.querySelectorAll('.linkage-tab').forEach(function (button) { button.addEventListener('click', function () { setLinkageMode(button.dataset.linkageMode); }); });
        document.getElementById('linkage-refresh').addEventListener('click', loadLinkage);
        document.getElementById('linkage-toggle-selection').addEventListener('click', function () {
            linkageState.selectionCollapsed = !linkageState.selectionCollapsed;
            document.getElementById('linkage-selection-panel').hidden = linkageState.selectionCollapsed;
            this.setAttribute('aria-expanded', linkageState.selectionCollapsed ? 'false' : 'true');
            this.textContent = linkageState.selectionCollapsed ? '展开选择栏' : '折叠选择栏';
        });
        ['linkage-attribute-type', 'linkage-attribute-bucket', 'linkage-attribute-query', 'linkage-sector-id', 'linkage-security-id', 'linkage-stock-query', 'linkage-trade-date', 'linkage-include-sectors', 'linkage-operator', 'linkage-exclude-sectors', 'linkage-days'].forEach(function (id) {
            document.getElementById(id).addEventListener('change', function () { if (id !== 'linkage-attribute-query' && id !== 'linkage-stock-query') loadLinkage(); });
        });
        ['linkage-attribute-query', 'linkage-stock-query', 'linkage-sector-id', 'linkage-security-id', 'linkage-include-sectors', 'linkage-exclude-sectors'].forEach(function (id) {
            document.getElementById(id).addEventListener('keydown', function (event) { if (event.key === 'Enter') { linkageState.page = 1; loadLinkage(); } });
        });
        document.getElementById('linkage-prev').addEventListener('click', function () { if (linkageState.page > 1) { linkageState.page--; loadLinkage(); } });
        document.getElementById('linkage-next').addEventListener('click', function () { linkageState.page++; loadLinkage(); });
        showSectorTableGroups(true);
    }

    bindControls();
    api.publications(true).then(function (result) {
        var items = result.items || [];
        select.replaceChildren.apply(select, publicationRows(items));
        if (!items.length) {
            setNotice('没有可用的成功发布版本', true);
            return;
        }
        var wanted = initialRoute.publication_id;
        current = items.find(function (item) {
            return item.publication_id === wanted;
        }) || items[0];
        select.value = current.publication_id;
        select.addEventListener('change', function () {
            if (modal.isOpen()) modal.close();
            var next = items.find(function (item) {
                return item.publication_id === select.value;
            });
            if (!next) return;
            router.setPublication(next.publication_id, 'push');
            load(next);
        });
        load(current);
        window.setTimeout(restoreInsightRoute, 0);
    }).catch(function (error) {
        setNotice('版本列表读取失败：' + error.message, true);
    });
    document.querySelectorAll('.nav-item').forEach(function (button) {
        button.addEventListener('click', function () {
            showPage(button.dataset.page);
        });
    });
}());
