(function () {
    'use strict';
    if ((document.body.dataset.workbenchMode || '') !== 'v3') return;

    // V3 has no local limit-up ladder/promotion or legacy hot-rank surface.
    // app.js has already registered V2 compatibility handlers, but V3 never calls them.
    document.querySelectorAll('.local-limit-panel, .hot-rank-panel, #market-structure-chart').forEach(function (node) {
        (node.id === 'market-structure-chart' ? node.parentElement : node).remove();
    });

    var select = document.getElementById('publication-select');
    var home = document.getElementById('v3-home');
    var legacy = document.getElementById('v3-legacy-overview');
    var online = document.getElementById('v3-online-panel');
    var requestSerial = 0;
    var context = null;
    var onlineSerial = 0;
    var onlineDateResolved = false;
    var buildSerial = 0;
    var buildTimer = null;
    document.querySelector('.nav-item[data-page="linkage"]').style.display = 'none';

    function esc(value) {
        return String(value === null || value === undefined ? '' : value).replace(/[&<>"']/g, function (char) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
        });
    }

    function show(value) {
        if (value === null || value === undefined || value === '') return '暂无';
        if (typeof value === 'number') {
            if (!Number.isFinite(value)) return '暂无';
            return esc(value.toLocaleString('zh-CN', {maximumFractionDigits: 2}));
        }
        if (typeof value === 'string' && /^-?\d+\.\d{3,}$/.test(value.trim())) {
            return esc(Number(value).toLocaleString('zh-CN', {maximumFractionDigits: 2}));
        }
        return esc(value);
    }

    function localTradeDate() {
        return context && context.local_date || '';
    }

    var labels = {
        READY: '数据就绪', AVAILABLE: '可用', DEGRADED: '部分可用', UNAVAILABLE: '不可用',
        INDUSTRY: '行业', THEME: '概念', STYLE: '风格',
        TODAY_LEADER: '当日领涨', CURRENT_RESEARCH: '当前研究', EARLY_WATCH: '提前观察',
        MID_PACK: '中位军', LOW_RETURN: '低涨幅', QUOTE_UNAVAILABLE: '行情缺失', ALL_MEMBERS: '普通成员',
        CURRENT_STRENGTH: '主升强势', STABILIZATION: '企稳', REACCELERATION: '再加速', NONE: '暂无阶段',
        TRACK_ROLE_ELIGIBLE: '符合当前轨道结构条件',
        BULLISH: '多头排列', BULL: '多头排列',
        BEARISH: '空头排列', BEAR: '空头排列',
        MIXED: '混合排列', NORMAL: '普通排列'
    };
    function zh(value) { return labels[String(value || '').toUpperCase()] || show(value); }
    function pct(value) {
        if (value === null || value === undefined || value === '') return '暂无';
        var number = Number(value);
        return Number.isFinite(number) ? (number * 100).toFixed(2) + '%' : '暂无';
    }
    function price(value) {
        var number = Number(value);
        return value === null || value === undefined || !Number.isFinite(number) ? '暂无' : number.toFixed(2);
    }
    function amount(value) {
        var number = Number(value);
        if (value === null || value === undefined || !Number.isFinite(number)) return '暂无';
        return number >= 100000000 ? (number / 100000000).toFixed(2) + ' 亿' : (number / 10000).toFixed(0) + ' 万';
    }
    function sectorMemberRow(member) {
        return '<tr data-detail-stock="' + esc(member.security_id) + '"><td>' + show(member.performance_rank) + '</td><td><b>' + show(member.name) + '</b><small>' + show(member.security_id) + '</small></td><td><span class="v3-member-tag ' + esc(String(member.performance_tag || '').toLowerCase()) + '">' + zh(member.performance_tag) + '</span></td><td>' + price(member.price) + '</td><td class="' + (Number(member.ret1) > 0 ? 'positive' : Number(member.ret1) < 0 ? 'negative' : '') + '">' + pct(member.ret1) + '</td><td>' + amount(member.amount) + '</td><td>' + pct(member.ret20) + '</td><td>' + zh(member.role) + '</td></tr>';
    }

    function get(path) {
        return fetch(path, {cache: 'no-store'}).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (body) {
                if (!response.ok) throw new Error(body.message || body.code || String(response.status));
                return body;
            });
        });
    }

    function post(path, payload) {
        var csrf = document.querySelector('meta[name="csrf-token"]');
        return fetch(path, {
            method: 'POST',
            cache: 'no-store',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrf ? csrf.content : ''
            },
            body: JSON.stringify(payload || {})
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (body) {
                if (!response.ok) throw new Error(body.message || body.code || String(response.status));
                return body;
            });
        });
    }

    function empty(text) {
        return '<div class="v3-empty">' + esc(text) + '</div>';
    }

    function modal(title, html) {
        var body = document.createElement('div');
        body.className = 'v3-detail-modal';
        body.innerHTML = html;
        window.WorkbenchV2Modal.open(title, body);
        return body;
    }

    function openStockModal(securityId, name) {
        var body = modal(name || securityId, '<p>正在读取本地个股属性…</p>');
        var params = '?publication_id=' + encodeURIComponent(select.value) + '&trade_date=' + encodeURIComponent(localTradeDate()) + '&include=overview,technical,sector_context&days=20&basis=AUTO';
        var membershipParams = '?publication_id=' + encodeURIComponent(select.value) + '&trade_date=' + encodeURIComponent(localTradeDate()) + '&page=1&page_size=50&basis=AUTO';
        Promise.all([get('/api/stocks/' + encodeURIComponent(securityId) + '/insight' + params), get('/api/stocks/' + encodeURIComponent(securityId) + '/memberships' + membershipParams).catch(function () { return {items: [], total: 0}; })]).then(function (results) {
            if (!body.isConnected) return;
            var result = results[0];
            var stock = result.item && result.item.overview || {};
            var technical = result.item && result.item.technical || {};
            var sectors = result.item && result.item.sector_context || {};
            var memberships = results[1].items || [];
            body.innerHTML = '<p class="v3-detail-meta">' + esc(securityId) + ' · 本地数据 ' + show(context && context.local_date) + '</p>' +
                '<div class="v3-detail-facts"><div><b>名称</b><span>' + show(stock.name || name) + '</span></div><div><b>收盘价</b><span>' + price(stock.raw_close) + '</span></div><div><b>当日涨幅</b><span>' + pct(stock.quote_ret1) + '</span></div><div><b>20日收益</b><span>' + pct(technical.ret20) + '</span></div><div><b>MA5 / MA20 / MA60</b><span>' + price(technical.ma5) + ' / ' + price(technical.ma20) + ' / ' + price(technical.ma60) + '</span></div><div><b>量额比</b><span>' + price(technical.amount_ratio20) + '</span></div><div><b>均线状态</b><span>' + zh(technical.ma_alignment) + '</span></div><div><b>强势关联</b><span>' + show(sectors.primary && sectors.primary.sector_name || sectors.reason) + '</span></div></div>' +
                '<h3>关联板块 · ' + show(results[1].total) + '</h3><div class="v3-detail-members">' + memberships.map(function (sector) { return '<button type="button" data-detail-sector="' + esc(sector.sector_id) + '"><b>' + show(sector.sector_name) + '</b><span>' + zh(sector.sector_type) + ' · ' + show(sector.semantic_bucket_label) + '</span></button>'; }).join('') + '</div>';
            body.querySelectorAll('[data-detail-sector]').forEach(function (button) { button.addEventListener('click', function () { openSectorModal(button.dataset.detailSector, button.querySelector('b').textContent); }); });
        }).catch(function (error) { if (body.isConnected) body.textContent = '个股属性读取失败：' + error.message; });
    }

    function openSectorModal(sectorId, name) {
        if (!context || !context.context_id) return;
        var body = modal(name || sectorId, '<p>正在读取本地板块属性和成员…</p>');
        var base = '/api/v3/research/sectors/' + encodeURIComponent(sectorId);
        var query = '?context_id=' + encodeURIComponent(context.context_id);
        Promise.all([get(base + query), get(base + '/members' + query + '&role=ALL_MEMBERS&sort=RET1&page=1&page_size=50')]).then(function (results) {
            if (!body.isConnected) return;
            var sector = results[0].sector || {};
            var members = results[1].items || [];
            body.innerHTML = '<p class="v3-detail-meta">' + show(sector.type) + ' · ' + esc(sectorId) + ' · 本地数据 ' + show(sector.local_as_of || context.local_date) + '</p>' +
                '<div class="v3-detail-facts"><div><b>板块成员</b><span>' + show(sector.member_count) + '</span></div><div><b>报价覆盖</b><span>' + pct(sector.quote_coverage) + '</span></div><div><b>当日中位涨幅</b><span>' + pct(sector.m1) + '</span></div><div><b>上涨宽度</b><span>' + pct(sector.b1) + '</span></div><div><b>相对强度</b><span>' + pct(sector.rel1) + '</span></div><div><b>结构阶段</b><span>' + zh(sector.structure_phase) + '</span></div></div>' +
                '<h3>全部成员 · ' + show(results[1].total) + '</h3><p class="v3-detail-meta">按当日涨幅降序、成交额降序、代码排序；前 20% 标记今日领涨，中间 60% 标记中位军，后 20% 标记低涨幅。</p><div class="v3-member-table-wrap"><table class="v3-member-table"><thead><tr><th>排名</th><th>个股</th><th>表现标签</th><th>最新价</th><th>当日涨幅</th><th>成交额</th><th>20日涨幅</th><th>研究角色</th></tr></thead><tbody>' + members.map(sectorMemberRow).join('') + '</tbody></table></div>' + (results[1].has_more ? '<button type="button" class="v3-more-members">加载更多成员</button>' : '');
            body.querySelectorAll('[data-detail-stock]').forEach(function (button) { button.addEventListener('click', function () { openStockModal(button.dataset.detailStock, button.querySelector('b').textContent); }); });
            var more = body.querySelector('.v3-more-members');
            var page = 1;
            if (more) more.addEventListener('click', function () {
                more.disabled = true;
                get(base + '/members' + query + '&role=ALL_MEMBERS&sort=RET1&page=' + (++page) + '&page_size=50').then(function (next) {
                    if (!body.isConnected) return;
                    var list = body.querySelector('.v3-member-table tbody');
                    list.insertAdjacentHTML('beforeend', (next.items || []).map(sectorMemberRow).join(''));
                    list.querySelectorAll('[data-detail-stock]').forEach(function (row) { row.addEventListener('click', function () { openStockModal(row.dataset.detailStock, row.querySelector('b').textContent); }); });
                    if (next.has_more) more.disabled = false; else more.remove();
                }).catch(function (error) { more.disabled = false; more.textContent = '读取失败，点击重试：' + error.message; page -= 1; });
            });
        }).catch(function (error) { if (body.isConnected) body.textContent = '板块详情读取失败：' + error.message; });
    }

    function renderLocalOverview(result) {
        var item = result.item || {};
        document.getElementById('v3-local-dates').textContent = '交易日 ' + show(item.trade_date || result.trade_date) + ' · 数据日期 ' + show(item.returned_range && item.returned_range.to || result.actual_input_date);
        var market = item.market_summary || {};
        var cards = (market.cards || []).filter(function (card) { return card.value !== null && card.value !== undefined; });
        document.getElementById('v3-local-market').innerHTML = cards.length ? cards.map(function (card) { return '<div><small>' + show(card.label) + '</small><b>' + (card.unit === 'percent' ? pct(card.value) : show(card.value)) + '</b></div>'; }).join('') : '<p>本地市场宽度统计尚无有效快照；下方领先板块可独立查看。</p>';
        var groups = item.strong_sectors || {};
        document.getElementById('v3-local-sectors').innerHTML = [['INDUSTRY', '领先行业'], ['THEME', '领先概念']].map(function (pair) {
            var group = groups[pair[0]] || {};
            return '<section><h4>' + pair[1] + ' <small>前 ' + (group.items || []).length + ' / ' + show(group.total) + '</small></h4><div class="v3-local-sector-list">' + (group.items || []).map(function (sector) {
                return '<button type="button" data-local-sector="' + esc(sector.sector_id) + '"><b>' + show(sector.rank) + '. ' + show(sector.sector_name) + '</b><span>相对强度百分位 ' + pct(sector.sector_rs20_pct) + ' · 当日中位涨幅 ' + pct(sector.member_ret1_median) + ' · 成员 ' + show(sector.total_member_count) + '</span></button>';
            }).join('') + '</div></section>';
        }).join('');
        document.querySelectorAll('[data-local-sector]').forEach(function (button) { button.addEventListener('click', function () { openSectorModal(button.dataset.localSector, button.querySelector('b').textContent); }); });
    }

    function renderLocalMarketCycle(result) {
        var point = (result.points || []).find(function (row) { return row.trade_date === (context && context.local_date); });
        if (!point) return;
        var valid = Number(point.quote_valid_count) || 0;
        var cards = [
            ['上涨 / 下跌 / 平盘', show(point.up_count) + ' / ' + show(point.down_count) + ' / ' + show(point.flat_count)],
            ['有效报价', show(point.quote_valid_count) + ' / ' + show(point.display_count)],
            ['上涨占比', valid ? pct(point.up_count / valid) : '暂无'],
            ['站上 MA20', point.ma20_valid_count ? pct(point.ma20_above_count / point.ma20_valid_count) : '暂无'],
            ['站上 MA60', point.ma60_valid_count ? pct(point.ma60_above_count / point.ma60_valid_count) : '暂无'],
            ['成交额', point.amount_sum === null ? '暂无' : (Number(point.amount_sum) / 1e8).toFixed(0) + ' 亿元']
        ];
        document.getElementById('v3-local-market').innerHTML = cards.map(function (card) { return '<div><small>' + card[0] + '</small><b>' + card[1] + '</b></div>'; }).join('');
    }

    function loadLocalOverview() {
        if (!select || !select.value) return;
        var tradeDate = localTradeDate();
        get('/api/dashboard?publication_id=' + encodeURIComponent(select.value) + '&include_analysis=1&basis=RECONSTRUCTED&trade_date=' + encodeURIComponent(tradeDate)).then(function (result) {
            renderLocalOverview(result);
            return get('/api/market/cycle?publication_id=' + encodeURIComponent(select.value) + '&basis=RECONSTRUCTED&days=1&trade_date=' + encodeURIComponent(tradeDate)).then(renderLocalMarketCycle).catch(function () {});
        }).catch(function (error) {
            document.getElementById('v3-local-market').innerHTML = empty('本地今日总览暂不可用：' + error.message);
        });
    }

    function loadPriorityResearch(page) {
        page = page || 1;
        var target = document.getElementById('v3-priority-stocks');
        var count = document.getElementById('v3-priority-count');
        if (!target || !select || !select.value) return;
        target.textContent = '正在读取本地优先研究个股…';
        get('/api/candidates?publication_id=' + encodeURIComponent(select.value) + '&include_analysis=1&basis=RECONSTRUCTED&final=1&page=' + page + '&page_size=25').then(function (result) {
            var items = result.items || [];
            count.textContent = '第 ' + page + ' 页 · 精选 ' + show(result.total) + ' 股 / 原结构候选 ' + show(result.source_candidate_total) + ' 股';
            target.innerHTML = items.length ? '<div class="v3-priority-table-wrap"><table class="v3-priority-table"><thead><tr><th>排名</th><th>个股</th><th>级别</th><th>最新价</th><th>当日涨幅</th><th>成交额</th><th>RPS20</th><th>综合分</th><th>结构</th><th>主要板块</th></tr></thead><tbody>' + items.map(function (item) {
                return '<tr data-priority-stock="' + esc(item.security_id) + '"><td>' + show(item.final_research_rank) + '</td><td><b>' + show(item.security_name) + '</b><small>' + show(item.security_id) + '</small></td><td>' + show(item.research_priority) + '</td><td>' + price(item.latest_price || item.raw_close || item.adj_close) + '</td><td class="' + (Number(item.quote_ret1) > 0 ? 'positive' : Number(item.quote_ret1) < 0 ? 'negative' : '') + '">' + pct(item.quote_ret1) + '</td><td>' + amount(item.turnover_amount || item.raw_amount) + '</td><td>' + pct(item.stock_rs20_pct) + '</td><td>' + show(item.priority_score) + '</td><td>' + show(item.effective_pattern || item.primary_pattern) + '</td><td>' + show(item.primary_leader_sector_name || item.strength_sector_name || item.best_sector_name) + '</td></tr>';
            }).join('') + '</tbody></table></div>' : empty('当前发布版本没有达到 A/A+ 且具有行业或概念背景的综合候选。');
            target.querySelectorAll('[data-priority-stock]').forEach(function (row) { row.addEventListener('click', function () { openStockModal(row.dataset.priorityStock, row.querySelector('b').textContent); }); });
            if (Number(result.total) > 25) {
                var pager = document.createElement('div');
                pager.className = 'v3-priority-pager';
                pager.innerHTML = '<button type="button" data-priority-prev ' + (page <= 1 ? 'disabled' : '') + '>上一页</button><span>第 ' + page + ' 页</span><button type="button" data-priority-next ' + (page * 25 >= Number(result.total) ? 'disabled' : '') + '>下一页</button>';
                target.after(pager);
                var old = document.querySelectorAll('.v3-priority-pager');
                old.forEach(function (node) { if (node !== pager) node.remove(); });
                pager.querySelector('[data-priority-prev]').addEventListener('click', function () { loadPriorityResearch(page - 1); });
                pager.querySelector('[data-priority-next]').addEventListener('click', function () { loadPriorityResearch(page + 1); });
            }
        }).catch(function (error) { count.textContent = '不可用'; target.innerHTML = empty('优先研究个股读取失败：' + error.message); });
    }

    function trackCard(item, track) {
        var members = (item.preview_members || []).slice(0, 3).map(function (member) {
            return '<span class="v3-preview-row" role="button" tabindex="0" data-preview-stock="' + esc(member.security_id) + '"><span>' + show(member.name) + ' <small>' + show(member.security_id) + '</small></span><span>' + zh(member.role) + '</span></span>';
        }).join('');
        return '<button type="button" class="v3-sector-card" data-v3-sector-id="' + esc(item.sector_id) + '" data-v3-member-role="' + (track === 'CURRENT' ? 'CURRENT_RESEARCH' : 'EARLY_WATCH') + '">' +
            '<div class="v3-sector-title"><b>' + show(item.name) + '</b><small>' + zh(item.type) + '</small></div>' +
            '<div class="v3-metrics"><span>成员 ' + show(item.member_count) + '</span><span>覆盖 ' + show(item.quote_coverage) + '</span><span>' + (track === 'CURRENT' ? '当前' : '提前') + '排名 ' + show(track === 'CURRENT' ? item.current_rank : item.potential_rank) + '</span></div>' +
            '<p>结构阶段：' + zh(item.structure_phase) + (item.branch ? ' · 提前分支：' + show(item.branch) : '') + (item.lifecycle ? ' · 生命周期：' + show(item.lifecycle) : '') + '</p>' +
            '<div class="v3-reasons">' + ((item.reasons || []).slice(0, 3).map(function (reason) { return '<span>' + show(reason.label || reason.code) + '</span>'; }).join('') || '<span>暂无附加理由</span>') + '</div>' +
            '<div class="v3-preview">' + (members || '<span>暂无成员预览</span>') + '</div></button>';
    }

    function renderTrack(targetId, countId, result, track) {
        var target = document.getElementById(targetId);
        var count = document.getElementById(countId);
        var items = result && result.items || [];
        count.textContent = '共 ' + (Number.isFinite(result && result.total) ? result.total : items.length) + ' 个';
        if (!items.length) {
            target.innerHTML = empty(track === 'CURRENT' ? '当前发布日没有同时满足当日强度、宽度与结构条件的板块。' : '暂未形成可确认的提前观察板块。当前板块周期仅有一个派生交易日，3 日变化与先前强势状态不足；这里的 0 不代表市场没有提前机会。');
            return;
        }
        target.innerHTML = items.slice(0, 6).map(function (item) { return trackCard(item, track); }).join('');
        target.querySelectorAll('[data-v3-sector-id]').forEach(function (button) {
            button.addEventListener('click', function () {
                openSectorModal(button.dataset.v3SectorId, button.querySelector('b').textContent);
            });
        });
        target.querySelectorAll('[data-preview-stock]').forEach(function (row) {
            row.addEventListener('click', function (event) {
                event.stopPropagation();
                openStockModal(row.dataset.previewStock, row.querySelector('span').textContent.trim());
            });
            row.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); openStockModal(row.dataset.previewStock, row.querySelector('span').textContent.trim()); }
            });
        });
    }

    function renderFocus(targetId, countId, result, label) {
        var target = document.getElementById(targetId);
        var count = document.getElementById(countId);
        var items = result && result.items || [];
        count.textContent = '共 ' + (Number.isFinite(result && result.total) ? result.total : items.length) + ' 条';
        if (!items.length) {
            target.innerHTML = empty(label === 'CURRENT_FOCUS' ? '当前强势板块中没有更多结构合格成员。' : '提前观察板块的历史证据不足，暂不能形成提前观察个股；不是全市场没有候选。');
            return;
        }
        target.innerHTML = items.slice(0, 10).map(function (item) {
            return '<button type="button" class="v3-focus-row" data-v3-security-id="' + esc(item.security_id) + '"><span><b>' + show(item.name) + '</b><small>' + show(item.security_id) + '</small></span><em>第 ' + show(item.rank) + ' 位</em><span>' + zh(item.selection_reason && item.selection_reason[0] && (item.selection_reason[0].label || item.selection_reason[0].code)) + '</span></button>';
        }).join('');
        target.querySelectorAll('[data-v3-security-id]').forEach(function (button) {
            button.addEventListener('click', function () {
                openStockModal(button.dataset.v3SecurityId, button.querySelector('b').textContent);
            });
        });
    }

    function renderHome(data, serial) {
        if (serial !== requestSerial) return;
        var state = document.getElementById('v3-home-state');
        if (!data || !data.context) {
            state.textContent = '研究上下文不可用';
            renderTrack('v3-current-cards', 'v3-current-count', {items: []}, 'CURRENT');
            renderTrack('v3-potential-cards', 'v3-potential-count', {items: []}, 'POTENTIAL');
            renderFocus('v3-current-focus', 'v3-current-focus-count', {items: []}, 'CURRENT_FOCUS');
            renderFocus('v3-early-focus', 'v3-early-focus-count', {items: []}, 'EARLY_FOCUS');
            return;
        }
        context = data.context;
        state.textContent = context.local_date + ' · ' + zh(context.status) + ' · 当前研究口径';
        loadLocalOverview();
        loadPriorityResearch();
        renderTrack('v3-current-cards', 'v3-current-count', {items: data.current_sectors || []}, 'CURRENT');
        renderTrack('v3-potential-cards', 'v3-potential-count', {items: data.potential_sectors || []}, 'POTENTIAL');
        renderFocus('v3-current-focus', 'v3-current-focus-count', {items: data.current_focus || []}, 'CURRENT_FOCUS');
        renderFocus('v3-early-focus', 'v3-early-focus-count', {items: data.early_focus || []}, 'EARLY_FOCUS');
        var notice = document.getElementById('notice');
        if (context.status === 'READY') {
            notice.textContent = '研究上下文已就绪：' + context.local_date + '。当前没有资格项时保持明确空态，不用旧候选填充首页。';
        }
    }

    function loadHome() {
        if (!select || !select.value) return;
        var option = select.options[select.selectedIndex];
        var tradeDate = (new URLSearchParams(window.location.search)).get('trade_date') || String(option.textContent || '').split(' · ')[0];
        var serial = ++requestSerial;
        var state = document.getElementById('v3-home-state');
        state.textContent = '正在读取研究上下文…';
        get('/api/v3/research/context?publication_id=' + encodeURIComponent(select.value) + '&trade_date=' + encodeURIComponent(tradeDate) + '&mode=CLOSE')
            .then(function (contextResult) {
                if (serial !== requestSerial) return null;
                return get('/api/v3/home/local?context_id=' + encodeURIComponent(contextResult.context && contextResult.context.context_id || '')).then(function (homeResult) {
                    renderHome(homeResult, serial);
                });
            })
            .catch(function (error) {
                if (serial !== requestSerial) return;
                state.textContent = '研究上下文读取失败';
                document.getElementById('notice').textContent = '研究首页暂不可用：' + error.message;
            });
    }

    function selectedResearchInput() {
        return {
            build_research_v3: true
        };
    }

    function setBuildStatus(text, tone) {
        var target = document.getElementById('v3-build-status');
        if (!target) return;
        target.className = 'v3-build-status' + (tone ? ' ' + tone : '');
        target.textContent = text;
    }

    function buildStatusText(job) {
        var status = String(job && job.status || '').toUpperCase();
        var progress = job && job.progress && job.progress.status;
        if (status === 'QUEUED') return '已提交，等待执行 · ' + job.job_id;
        if (status === 'RUNNING') return '正在生成：' + (progress || 'BUILDING_RESEARCH_V3') + ' · ' + job.job_id;
        if (status === 'SUCCESS') return '生成完成 · ' + (job.progress && job.progress.publication_id || job.job_id);
        if (status === 'FAILED' || status === 'ERROR') return '生成失败：' + (progress && progress.error || '请查看服务日志') + ' · ' + job.job_id;
        return '任务状态：' + (status || 'UNKNOWN') + ' · ' + (job.job_id || '无任务编号');
    }

    function pollResearchBuild(jobId, serial, attempt) {
        get('/api/jobs?job_id=' + encodeURIComponent(jobId)).then(function (job) {
            if (serial !== buildSerial) return;
            var status = String(job.status || '').toUpperCase();
            if (status === 'SUCCESS') {
                setBuildStatus(buildStatusText(job), 'ok');
                var button = document.getElementById('v3-build-research');
                if (button) button.disabled = false;
                // Reload the publication catalog so the newly committed trading
                // day becomes the selected V3 context without a second action.
                window.setTimeout(function () { window.location.reload(); }, 300);
                return;
            }
            if (status === 'FAILED' || status === 'ERROR') {
                setBuildStatus(buildStatusText(job), 'error');
                var failedButton = document.getElementById('v3-build-research');
                if (failedButton) failedButton.disabled = false;
                return;
            }
            if (attempt >= 3600) {
                setBuildStatus('任务仍在执行，已停止自动轮询 · ' + jobId, 'warn');
                var timeoutButton = document.getElementById('v3-build-research');
                if (timeoutButton) timeoutButton.disabled = false;
                return;
            }
            setBuildStatus(buildStatusText(job), '');
            buildTimer = window.setTimeout(function () { pollResearchBuild(jobId, serial, attempt + 1); }, 1000);
        }).catch(function (error) {
            if (serial !== buildSerial) return;
            setBuildStatus('任务仍在后台执行，状态读取暂时中断；正在自动重试：' + error.message, 'warn');
            buildTimer = window.setTimeout(function () { pollResearchBuild(jobId, serial, attempt + 1); }, 3000);
        });
    }

    function submitResearchBuild() {
        var button = document.getElementById('v3-build-research');
        if (!button || button.disabled) return;
        if (buildTimer) window.clearTimeout(buildTimer);
        var serial = ++buildSerial;
        button.disabled = true;
        setBuildStatus('正在提交生成任务…', '');
        var payload;
        try { payload = selectedResearchInput(); } catch (error) {
            button.disabled = false;
            setBuildStatus(error.message, 'error');
            return;
        }
        post('/api/jobs', payload).then(function (job) {
            if (serial !== buildSerial) return;
            if (!job.job_id) throw new Error('服务未返回任务编号');
            setBuildStatus(buildStatusText(job), '');
            pollResearchBuild(job.job_id, serial, 0);
        }).catch(function (error) {
            if (serial !== buildSerial) return;
            button.disabled = false;
            setBuildStatus('生成任务提交失败：' + error.message, 'error');
        });
    }

    function onlineStatus(targetId, status, message) {
        document.getElementById(targetId).innerHTML = '<div class="v3-online-status ' + (status === 'AVAILABLE' ? 'ok' : 'warn') + '">' + zh(status) + '</div><p>' + show(message) + '</p>';
    }

    function onlineTradeDate() {
        var input = document.getElementById('v3-online-trade-date');
        return input && input.value || '';
    }

    function resolveOnlineTradeDate() {
        return get('/api/v3/online/latest-trade-date').then(function (result) {
            if (!result.trade_date) throw new Error('最近交易日未获得在线来源确认');
            var input = document.getElementById('v3-online-trade-date');
            if (input && !input.value) input.value = result.trade_date;
            onlineDateResolved = true;
            return input && input.value || result.trade_date;
        });
    }

    function renderOnlineRows(result, sourceLabel) {
        var items = result.items || [];
        if (!items.length) return '';
        return '<div class="v3-online-source">来源：' + esc(sourceLabel) + ' · 请求交易日：' + show(result.request && result.request.date || onlineTradeDate()) + ' · 首次涨停时间升序；无时间按连板、涨幅及来源顺序排后</div><div class="v3-online-table-scroll"><table class="v3-online-table v3-ladder-table"><colgroup><col><col><col><col><col><col><col></colgroup><thead><tr><th>代码</th><th>名称</th><th>首次涨停</th><th>价格</th><th>涨幅</th><th>连板</th><th>涨停说明 / 来源原因</th></tr></thead><tbody>' + items.map(function (item) {
            var epoch = Number(item.first_limit_time || item.last_limit_time || item.source_enter_time);
            var clock = Number.isFinite(epoch) && epoch >= 1000000000 ? new Date(epoch * 1000).toLocaleTimeString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false}) : '暂无';
            return '<tr><td>' + show(item.source_code) + '</td><td>' + show(item.security_name) + '</td><td>' + esc(clock) + '</td><td>' + price(item.price) + '</td><td>' + pct(item.ret1) + '</td><td>' + show(item.source_limit_days) + '</td><td class="v3-pool-reason">' + show(item.source_reason) + '</td></tr>';
        }).join('') + '</tbody></table></div>';
    }

    function loadOnlineLadder(serial, page) {
        page = page || 1;
        var target = document.getElementById('v3-online-ladder');
        var tradeDate = onlineTradeDate();
        target.textContent = '正在读取在线涨停…';
        get('/api/v3/events/pools?pool_type=limit_up&sort=LIMIT_TIME&page=' + page + '&page_size=30&trade_date=' + encodeURIComponent(tradeDate)).then(function (result) {
            if (serial !== onlineSerial) return;
            var pool = result.pools && result.pools.limit_up || {};
            target.innerHTML = (pool.items || []).length ? renderOnlineRows(pool, '在线涨停池（请求时读取）') + '<div class="v3-pool-pager"><button type="button" data-ladder-prev ' + (page <= 1 ? 'disabled' : '') + '>上一页</button><span>共 ' + show(pool.total) + ' 条 · 第 ' + page + ' 页</span><button type="button" data-ladder-next ' + (!pool.has_more ? 'disabled' : '') + '>下一页</button></div>' : empty('在线涨停池当前无可读数据。');
            var prev = target.querySelector('[data-ladder-prev]'), next = target.querySelector('[data-ladder-next]');
            if (prev) prev.onclick = function () { loadOnlineLadder(serial, page - 1); };
            if (next) next.onclick = function () { loadOnlineLadder(serial, page + 1); };
        }).catch(function (error) { if (serial === onlineSerial) target.innerHTML = empty('在线涨停读取失败：' + error.message); });
    }

    function loadOnline() {
        if (!online) return;
        if (!onlineDateResolved) { resolveOnlineTradeDate().then(loadOnline).catch(function (error) { onlineStatus('v3-online-overview', 'UNAVAILABLE', error.message); }); return; }
        var serial = ++onlineSerial;
        document.getElementById('v3-online-overview').textContent = '正在读取…';
        document.getElementById('v3-online-topics').textContent = '正在读取…';
        document.getElementById('v3-online-hot').textContent = '正在读取…';
        var tradeDate = onlineTradeDate();
        get('/api/v3/events/overview?trade_date=' + encodeURIComponent(tradeDate)).then(function (result) {
            if (serial !== onlineSerial) return;
            var market = result.market_overview && result.market_overview.data || {};
            var riseFall = market.rise_fall || {};
            var turnover = market.turnover_display || {};
            document.getElementById('v3-online-overview').innerHTML = '<div class="v3-online-status ' + (result.status === 'AVAILABLE' ? 'ok' : 'warn') + '">' + zh(result.status) + '</div><div class="v3-overview-lines"><span>上涨 <b>' + show(riseFall.rise) + '</b></span><span>下跌 <b>' + show(riseFall.fall) + '</b></span><span>平盘 <b>' + show(riseFall.deuce) + '</b></span><span>涨停 <b>' + show(riseFall.limit_up) + '</b></span><span>跌停 <b>' + show(riseFall.limit_down) + '</b></span><span>成交额（来源显示）<b>' + show(turnover.now) + '</b></span><span>前值成交额（来源显示）<b>' + show(turnover.pre) + '</b></span></div><p class="v3-online-source">在线交易日 ' + show(tradeDate) + ' · 各字段均来自 EXT06；未提供的字段显示“暂无”。</p>';
        }).catch(function (error) { onlineStatus('v3-online-overview', 'UNAVAILABLE', error.message); });
        get('/api/v3/events/topics?trade_date=' + encodeURIComponent(tradeDate)).then(function (result) {
            if (serial !== onlineSerial) return;
            var items = result.items || [];
            document.getElementById('v3-online-topics').innerHTML = '<div class="v3-online-status ' + (result.status === 'AVAILABLE' ? 'ok' : 'warn') + '">' + zh(result.status) + ' · 全部 ' + show(result.topic_count) + ' 个题材</div>' + (items.length ? '<div class="v3-online-list v3-topic-list">' + items.map(function (item) { return '<button type="button" data-online-topic="' + esc(item.source_topic_id) + '"><b>' + show(item.topic_name) + '</b><span>涨停成员 ' + show(item.limit_up_member_count) + ' · 全部成员 ' + show(item.unique_member_count) + '</span></button>'; }).join('') + '</div>' : '<p>当前没有形成同日题材与成员连接。</p>');
            document.querySelectorAll('[data-online-topic]').forEach(function (button) {
                button.addEventListener('click', function () { loadTopicMembers(button.dataset.onlineTopic, button.querySelector('b').textContent); });
            });
        }).catch(function (error) { onlineStatus('v3-online-topics', 'UNAVAILABLE', error.message); });
        Promise.all([get('/api/v3/hot-plates?type=concept'), get('/api/v3/hot-plates?type=industry'), get('/api/v3/hot-topics?page=1&page_size=8')]).then(function (results) {
            if (serial !== onlineSerial) return;
            var concepts = (results[0].items || []).slice(0, 8).map(function (item) { return show(item.plate_name); });
            var industries = (results[1].items || []).slice(0, 8).map(function (item) { return show(item.plate_name); });
            var topics = (results[2].items || []).slice(0, 8).map(function (item) { return show(item.topic_title); });
            document.getElementById('v3-online-hot').innerHTML = '<div class="v3-hot-columns"><p><b>热门概念</b><span>' + (concepts.join('、') || '暂无') + '</span></p><p><b>热门行业</b><span>' + (industries.join('、') || '暂无') + '</span></p><p><b>热门话题</b><span>' + (topics.join('、') || '暂无') + '</span></p></div><small>请求时读取，不保存热榜原始内容。</small>';
        }).catch(function (error) { onlineStatus('v3-online-hot', 'UNAVAILABLE', error.message); });
        loadOnlineLadder(serial);
        loadPool(1);
        loadAllRanks();
    }

    function loadTopicMembers(topicId, topicName) {
        var body = modal(topicName + ' · 在线成员', '<p>正在读取题材成员…</p>');
        var tradeDate = onlineTradeDate();
        var page = 0;
        function nextPage() {
            var next = page + 1;
            get('/api/v3/events/topics/' + encodeURIComponent(topicId) + '/members?trade_date=' + encodeURIComponent(tradeDate) + '&page=' + next + '&page_size=30').then(function (result) {
                if (!body.isConnected) return;
                var items = result.items || [];
                var rows = items.map(function (item) {
                    var entered = Number(item.source_enter_time);
                    var enterText = Number.isFinite(entered) && entered > 0 ? new Date(entered * 1000).toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai'}) : '暂无';
                    var estimate = item.dragon_estimated_amount_yi;
                    return '<tr><td>' + show(item.source_code) + '</td><td>' + show(item.security_name) + '</td><td>' + (item.is_limit_up === true ? '涨停' : item.is_limit_up === false ? '未涨停' : '未知') + '</td><td>' + esc(enterText) + '</td><td>' + (estimate == null ? '暂无' : Number(estimate).toFixed(2) + ' 亿') + '</td><td class="v3-topic-description">' + show(item.source_description) + '</td></tr>';
                }).join('');
                if (page === 0) body.innerHTML = '<p class="v3-detail-meta">交易日 ' + show(tradeDate) + ' · 在线成员 ' + show(result.total) + ' · 估算金额为算法推算，非来源成交额</p><div class="v3-online-table-scroll"><table class="v3-online-table v3-topic-table"><colgroup><col><col><col><col><col><col></colgroup><thead><tr><th>代码</th><th>名称</th><th>涨停状态</th><th>进入时间</th><th>估算金额</th><th>来源描述</th></tr></thead><tbody></tbody></table></div><button type="button" class="v3-topic-more" hidden>加载更多</button>';
                body.querySelector('tbody').insertAdjacentHTML('beforeend', rows);
                page = next;
                var more = body.querySelector('.v3-topic-more');
                more.hidden = !result.has_more;
                more.onclick = nextPage;
            }).catch(function (error) { if (body.isConnected) body.insertAdjacentHTML('beforeend', '<p>成员读取失败：' + esc(error.message) + '</p>'); });
        }
        nextPage();
    }

    function loadPool(page) {
        page = typeof page === 'number' ? page : 1;
        var type = document.getElementById('v3-online-pool-type').value;
        var target = document.getElementById('v3-online-pool');
        target.textContent = '正在读取…';
        get('/api/v3/events/pools?pool_type=' + encodeURIComponent(type) + '&trade_date=' + encodeURIComponent(onlineTradeDate()) + '&page=' + page + '&page_size=30').then(function (result) {
            var pool = result.pools && result.pools[type] || {};
            var items = pool.items || [];
            target.innerHTML = '<div class="v3-online-status ' + (pool.status === 'AVAILABLE' ? 'ok' : 'warn') + '">' + zh(pool.status) + ' · 共 ' + show(pool.total) + ' 条 · 第 ' + page + ' 页</div>' + (items.length ? '<div class="v3-online-table-scroll"><table class="v3-online-table v3-pool-table"><colgroup><col><col><col><col><col><col></colgroup><thead><tr><th>代码</th><th>名称</th><th>价格</th><th>涨幅</th><th>连板</th><th>涨停说明 / 来源原因</th></tr></thead><tbody>' + items.map(function (item) { return '<tr><td>' + show(item.source_code) + '</td><td>' + show(item.security_name) + '</td><td>' + price(item.price) + '</td><td>' + pct(item.ret1) + '</td><td>' + show(item.source_limit_days) + '</td><td class="v3-pool-reason">' + show(item.source_reason) + '</td></tr>'; }).join('') + '</tbody></table></div>' : '<p>当前池没有可展示的在线记录。' + show(pool.empty_state && pool.empty_state.code) + '</p>') + '<div class="v3-pool-pager"><button type="button" data-pool-prev ' + (page <= 1 ? 'disabled' : '') + '>上一页</button><span>第 ' + page + ' 页</span><button type="button" data-pool-next ' + (!pool.has_more ? 'disabled' : '') + '>下一页</button></div>';
            target.querySelector('[data-pool-prev]').onclick = function () { loadPool(page - 1); };
            target.querySelector('[data-pool-next]').onclick = function () { loadPool(page + 1); };
        }).catch(function (error) { onlineStatus('v3-online-pool', 'UNAVAILABLE', error.message); });
    }

    function loadAllRanks() {
        var target = document.getElementById('v3-online-rank');
        target.textContent = '正在读取四榜…';
        get('/api/v3/hot-rankings?page=1&page_size=20').then(function (result) {
            var modes = [['hour_normal','小时热榜'],['hour_skyrocket','小时飙升'],['day_normal','日热榜'],['day_skyrocket','日飙升']];
            target.innerHTML = modes.map(function (mode) {
                var list = result.lists && result.lists[mode[0]] || {};
                var items = list.items || [];
                return '<section><h4>' + mode[1] + '</h4><div class="v3-online-status ' + (list.status === 'AVAILABLE' ? 'ok' : 'warn') + '">' + zh(list.status) + ' · ' + show(list.returned_count) + ' 条</div><div class="v3-compact-list">' + items.map(function (item) { return '<div><b>' + show(item.platform_rank) + ' · ' + show(item.security_name || item.source_code) + '</b><span>名次变化 ' + show(item.rank_change) + '</span></div>'; }).join('') + '</div></section>';
            }).join('');
        }).catch(function (error) { onlineStatus('v3-online-rank', 'UNAVAILABLE', error.message); });
    }

    function syncPage() {
        var isOverview = !new URLSearchParams(window.location.search).get('page');
        home.hidden = !isOverview;
        legacy.open = false;
        if (online) {
            var isMarket = new URLSearchParams(window.location.search).get('page') === 'market';
            online.hidden = !isMarket;
            if (isMarket) loadOnline();
        }
    }

    function waitForPublications(attempt) {
        if (select && select.options.length) {
            select.addEventListener('change', loadHome);
            loadHome();
            syncPage();
            return;
        }
        if (attempt < 80) window.setTimeout(function () { waitForPublications(attempt + 1); }, 100);
    }

    document.querySelectorAll('[data-v3-page]').forEach(function (button) {
        button.addEventListener('click', function () {
            var nav = document.querySelector('.nav-item[data-page="' + button.dataset.v3Page + '"]');
            if (nav) nav.click();
        });
    });
    if (document.getElementById('v3-online-refresh')) document.getElementById('v3-online-refresh').addEventListener('click', loadOnline);
    if (document.getElementById('v3-online-trade-date')) document.getElementById('v3-online-trade-date').addEventListener('change', function () { onlineDateResolved = true; loadOnline(); });
    if (document.getElementById('v3-online-ladder-refresh')) document.getElementById('v3-online-ladder-refresh').addEventListener('click', function () { onlineSerial += 1; loadOnlineLadder(onlineSerial); });
    if (document.getElementById('v3-online-pool-type')) document.getElementById('v3-online-pool-type').addEventListener('change', function () { loadPool(1); });
    if (document.getElementById('v3-build-research')) document.getElementById('v3-build-research').addEventListener('click', submitResearchBuild);
    var technicalMode = document.getElementById('technical-mode');
    var technicalBand = document.getElementById('technical-research-band');
    if (technicalMode) technicalMode.value = 'technical';
    if (technicalBand) technicalBand.value = 'RESEARCHABLE';
    document.querySelectorAll('.nav-item').forEach(function (button) {
        button.addEventListener('click', function () { window.setTimeout(syncPage, 0); });
    });
    window.addEventListener('popstate', syncPage);
    waitForPublications(0);
}());
