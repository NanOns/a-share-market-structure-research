(function () {
    'use strict';
    if ((document.body.dataset.workbenchMode || '') !== 'v3') return;

    var select = document.getElementById('publication-select');
    var home = document.getElementById('v3-home');
    var legacy = document.getElementById('v3-legacy-overview');
    var online = document.getElementById('v3-online-panel');
    var requestSerial = 0;
    var context = null;
    var onlineSerial = 0;

    function esc(value) {
        return String(value === null || value === undefined ? '' : value).replace(/[&<>"']/g, function (char) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
        });
    }

    function show(value) {
        return value === null || value === undefined || value === '' ? '暂无' : esc(value);
    }

    function get(path) {
        return fetch(path, {cache: 'no-store'}).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (body) {
                if (!response.ok) throw new Error(body.message || body.code || String(response.status));
                return body;
            });
        });
    }

    function empty(text) {
        return '<div class="v3-empty">' + esc(text) + '</div>';
    }

    function trackCard(item, track) {
        var members = (item.preview_members || []).slice(0, 3).map(function (member) {
            return '<div class="v3-preview-row"><span>' + show(member.name) + ' <small>' + show(member.security_id) + '</small></span><span>' + show(member.role) + '</span></div>';
        }).join('');
        return '<button type="button" class="v3-sector-card" data-v3-page="sectors">' +
            '<div class="v3-sector-title"><b>' + show(item.name) + '</b><small>' + show(item.type) + '</small></div>' +
            '<div class="v3-metrics"><span>成员 ' + show(item.member_count) + '</span><span>覆盖 ' + show(item.quote_coverage) + '</span><span>' + (track === 'CURRENT' ? '当前' : '提前') + '排名 ' + show(track === 'CURRENT' ? item.current_rank : item.potential_rank) + '</span></div>' +
            '<p>' + (item.branch ? '分支：' + show(item.branch) : '生命周期：' + show(item.lifecycle)) + '</p>' +
            '<div class="v3-reasons">' + ((item.reasons || []).slice(0, 3).map(function (reason) { return '<span>' + show(reason.label || reason.code) + '</span>'; }).join('') || '<span>暂无附加理由</span>') + '</div>' +
            '<div class="v3-preview">' + (members || '<span>暂无成员预览</span>') + '</div></button>';
    }

    function renderTrack(targetId, countId, result, track) {
        var target = document.getElementById(targetId);
        var count = document.getElementById(countId);
        var items = result && result.items || [];
        count.textContent = '共 ' + (Number.isFinite(result && result.total) ? result.total : items.length) + ' 个';
        if (!items.length) {
            target.innerHTML = empty(track === 'CURRENT' ? '当前发布日没有符合 CURRENT 条件的板块。' : '当前发布日没有符合 POTENTIAL 条件的板块。');
            return;
        }
        target.innerHTML = items.slice(0, 6).map(function (item) { return trackCard(item, track); }).join('');
        target.querySelectorAll('[data-v3-page]').forEach(function (button) {
            button.addEventListener('click', function () {
                var nav = document.querySelector('.nav-item[data-page="sectors"]');
                if (nav) nav.click();
            });
        });
    }

    function renderFocus(targetId, countId, result, label) {
        var target = document.getElementById(targetId);
        var count = document.getElementById(countId);
        var items = result && result.items || [];
        count.textContent = '共 ' + (Number.isFinite(result && result.total) ? result.total : items.length) + ' 条';
        if (!items.length) {
            target.innerHTML = empty(label + ' 当前没有符合条件的个股。');
            return;
        }
        target.innerHTML = items.slice(0, 10).map(function (item) {
            return '<button type="button" class="v3-focus-row" data-v3-page="stocks"><span><b>' + show(item.name) + '</b><small>' + show(item.security_id) + '</small></span><em>#' + show(item.rank) + '</em><span>' + show(item.selection_reason && item.selection_reason[0] && (item.selection_reason[0].label || item.selection_reason[0].code)) + '</span></button>';
        }).join('');
        target.querySelectorAll('[data-v3-page]').forEach(function (button) {
            button.addEventListener('click', function () {
                var nav = document.querySelector('.nav-item[data-page="stocks"]');
                if (nav) nav.click();
            });
        });
    }

    function renderHome(data, serial) {
        if (serial !== requestSerial) return;
        var state = document.getElementById('v3-home-state');
        if (!data || !data.context) {
            state.textContent = 'V3 上下文不可用';
            renderTrack('v3-current-cards', 'v3-current-count', {items: []}, 'CURRENT');
            renderTrack('v3-potential-cards', 'v3-potential-count', {items: []}, 'POTENTIAL');
            renderFocus('v3-current-focus', 'v3-current-focus-count', {items: []}, 'CURRENT_FOCUS');
            renderFocus('v3-early-focus', 'v3-early-focus-count', {items: []}, 'EARLY_FOCUS');
            return;
        }
        context = data.context;
        state.textContent = context.local_date + ' · ' + context.status + ' · ' + context.algorithm_version;
        renderTrack('v3-current-cards', 'v3-current-count', {items: data.current_sectors || []}, 'CURRENT');
        renderTrack('v3-potential-cards', 'v3-potential-count', {items: data.potential_sectors || []}, 'POTENTIAL');
        renderFocus('v3-current-focus', 'v3-current-focus-count', {items: data.current_focus || []}, 'CURRENT_FOCUS');
        renderFocus('v3-early-focus', 'v3-early-focus-count', {items: data.early_focus || []}, 'EARLY_FOCUS');
        var notice = document.getElementById('notice');
        if (context.status === 'READY') {
            notice.textContent = 'V3 研究上下文已就绪：' + context.local_date + '。当前没有资格项时保持明确空态，不用旧候选填充首页。';
        }
    }

    function loadHome() {
        if (!select || !select.value) return;
        var option = select.options[select.selectedIndex];
        var tradeDate = (new URLSearchParams(window.location.search)).get('trade_date') || String(option.textContent || '').split(' · ')[0];
        var serial = ++requestSerial;
        var state = document.getElementById('v3-home-state');
        state.textContent = '正在读取 V3 研究上下文…';
        get('/api/v3/research/context?publication_id=' + encodeURIComponent(select.value) + '&trade_date=' + encodeURIComponent(tradeDate) + '&mode=CLOSE')
            .then(function (contextResult) {
                if (serial !== requestSerial) return null;
                return get('/api/v3/home/local?context_id=' + encodeURIComponent(contextResult.context && contextResult.context.context_id || '')).then(function (homeResult) {
                    renderHome(homeResult, serial);
                });
            })
            .catch(function (error) {
                if (serial !== requestSerial) return;
                state.textContent = 'V3 研究上下文读取失败';
                document.getElementById('notice').textContent = 'V3 首页暂不可用：' + error.message;
            });
    }

    function onlineStatus(targetId, status, message) {
        document.getElementById(targetId).innerHTML = '<div class="v3-online-status ' + (status === 'AVAILABLE' ? 'ok' : 'warn') + '">' + show(status) + '</div><p>' + show(message) + '</p>';
    }

    function loadOnlineLadder(serial) {
        var target = document.getElementById('v3-online-ladder');
        get('/api/v3/events/ladder?page=1&page_size=20&sort=DEFAULT').then(function (result) {
            if (serial !== onlineSerial) return;
            var items = result.items || [];
            if (!items.length) { target.innerHTML = empty(result.empty_state && result.empty_state.message || '当前没有可展示的在线涨停事实。'); return; }
            target.innerHTML = '<table><thead><tr><th>代码</th><th>名称</th><th>高度</th><th>状态</th><th>涨幅</th><th>首封</th><th>来源原因</th></tr></thead><tbody>' + items.map(function (item) {
                return '<tr><td>' + show(item.security_id || item.source_code) + '</td><td>' + show(item.security_name || item.source_fields && item.source_fields.name) + '</td><td>' + show(item.height_display) + '</td><td>' + show(item.event_state) + '</td><td>' + show(item.ret1) + '</td><td>' + show(item.first_limit_time) + '</td><td>' + show(item.source_reason) + '</td></tr>';
            }).join('') + '</tbody></table>';
        }).catch(function (error) { if (serial === onlineSerial) target.innerHTML = empty('在线涨停读取失败：' + error.message); });
    }

    function loadOnline() {
        if (!online) return;
        var serial = ++onlineSerial;
        document.getElementById('v3-online-overview').textContent = '正在读取…';
        document.getElementById('v3-online-topics').textContent = '正在读取…';
        document.getElementById('v3-online-hot').textContent = '正在读取…';
        get('/api/v3/events/overview').then(function (result) {
            if (serial !== onlineSerial) return;
            var market = result.market_overview && result.market_overview.data || {};
            var riseFall = market.rise_fall || {};
            onlineStatus('v3-online-overview', result.status, '涨 ' + show(riseFall.rise) + ' / 跌 ' + show(riseFall.fall) + ' / 平 ' + show(riseFall.deuce) + '；涨停 ' + show(result.event_close && result.event_close.returned_count) + '；观察 ' + show(result.observed_at || result.source_time && result.source_time.received_at));
        }).catch(function (error) { onlineStatus('v3-online-overview', 'UNAVAILABLE', error.message); });
        get('/api/v3/events/topics').then(function (result) {
            if (serial !== onlineSerial) return;
            var items = (result.items || []).slice(0, 8);
            document.getElementById('v3-online-topics').innerHTML = '<div class="v3-online-status ' + (result.status === 'AVAILABLE' ? 'ok' : 'warn') + '">' + show(result.status) + ' · 题材 ' + show(result.topic_count) + '</div>' + (items.length ? '<ul>' + items.map(function (item) { return '<li>' + show(item.topic_name) + ' · 涨停 ' + show(item.limit_up_member_count) + '</li>'; }).join('') + '</ul>' : '<p>当前没有来源题材可展示。</p>');
        }).catch(function (error) { onlineStatus('v3-online-topics', 'UNAVAILABLE', error.message); });
        Promise.all([get('/api/v3/hot-plates?type=concept'), get('/api/v3/hot-topics?page=1&page_size=5')]).then(function (results) {
            if (serial !== onlineSerial) return;
            var plates = (results[0].items || []).slice(0, 5).map(function (item) { return show(item.plate_name); });
            var topics = (results[1].items || []).slice(0, 5).map(function (item) { return show(item.topic_title); });
            document.getElementById('v3-online-hot').innerHTML = '<p><b>热门板块：</b>' + (plates.join('、') || '暂无') + '</p><p><b>热门话题：</b>' + (topics.join('、') || '暂无') + '</p><small>请求时读取，不保存热榜原始内容。</small>';
        }).catch(function (error) { onlineStatus('v3-online-hot', 'UNAVAILABLE', error.message); });
        document.getElementById('v3-online-ladder').textContent = '按需读取。';
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
    if (document.getElementById('v3-online-ladder-refresh')) document.getElementById('v3-online-ladder-refresh').addEventListener('click', function () { onlineSerial += 1; loadOnlineLadder(onlineSerial); });
    document.querySelectorAll('.nav-item').forEach(function (button) {
        button.addEventListener('click', function () { window.setTimeout(syncPage, 0); });
    });
    window.addEventListener('popstate', syncPage);
    waitForPublications(0);
}());
