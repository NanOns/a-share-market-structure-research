(function () {
    'use strict';
    var pages = ['overview', 'sectors', 'stocks', 'linkage', 'market', 'data-info'];
    var subpages = ['sectors', 'mainlines'];

    function valid(value, allowed, fallback) {
        return allowed.indexOf(value) >= 0 ? value : fallback;
    }

    function read() {
        var params = new URLSearchParams(window.location.search);
        var page = valid(params.get('page'), pages, 'overview');
        return {
            page: page,
            subpage: page === 'sectors' ? valid(params.get('subpage'), subpages, 'sectors') : 'sectors',
            publication_id: params.get('publication_id') || '',
            trade_date: params.get('trade_date') || '',
            basis: params.get('basis') || ''
        };
    }

    function write(route, mode) {
        var url = new URL(window.location.href);
        var next = route || {};
        var page = valid(next.page, pages, 'overview');
        if (page === 'overview') url.searchParams.delete('page');
        else url.searchParams.set('page', page);
        if (page === 'sectors' && valid(next.subpage, subpages, 'sectors') !== 'sectors') url.searchParams.set('subpage', next.subpage);
        else url.searchParams.delete('subpage');
        if (next.publication_id) url.searchParams.set('publication_id', next.publication_id);
        if (next.trade_date) url.searchParams.set('trade_date', next.trade_date);
        if (next.basis) url.searchParams.set('basis', next.basis);
        (mode === 'push' ? window.history.pushState.bind(window.history) : window.history.replaceState.bind(window.history))({}, '', url.toString());
    }

    function navigate(page, options) {
        options = options || {};
        var current = read();
        write({
            page: page,
            subpage: options.subpage || (page === 'sectors' ? current.subpage : 'sectors'),
            publication_id: options.publication_id || current.publication_id,
            trade_date: options.trade_date || current.trade_date,
            basis: options.basis || current.basis
        }, options.mode || 'push');
    }

    function setPublication(publicationId, mode) {
        var current = read();
        write({page: current.page, subpage: current.subpage, publication_id: publicationId, trade_date: '', basis: current.basis}, mode || 'push');
    }

    window.WorkbenchV2Router = {
        pages: pages.slice(),
        subpages: subpages.slice(),
        read: read,
        write: write,
        navigate: navigate,
        setPublication: setPublication,
        normalizePage: function (value) { return valid(value, pages, 'overview'); }
    };
}());
