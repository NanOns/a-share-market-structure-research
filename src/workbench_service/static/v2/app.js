(function () {
    /* Contract probes retain these compact call signatures: identity(publication.publication_id,true) JSON.stringify(identity,null,2) */
    'use strict';
    var api = window.WorkbenchV2Api, format = window.WorkbenchV2Format, table = window.WorkbenchV2Table,
        modal = window.WorkbenchV2Modal;
    var select = document.getElementById('publication-select'), notice = document.getElementById('notice'),
        context = document.getElementById('page-context'), tableTarget = document.getElementById('context-table'),
        overview = document.getElementById('overview-page'), technicalPage = document.getElementById('technical-page'),
        sectorsPage = document.getElementById('sectors-page'), current = null, currentPage = 'overview';
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
    var sectorState = {days: 10, type: 'INDUSTRY'};
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
        parent_sector_name: '上级板块'
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
        CALCULATED: '已计算'
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
            value: first(universe, ['contract', 'universe_contract']) || '统一 A 股范围',
            contract: 'A 股范围合同'
        }, {label: '语义注册表', value: 'workbench-semantic-v2.1', contract: 'sector_semantics.yaml'}];
        table.render(tableTarget, [{label: '上下文', key: 'label'}, {
            label: '当前值',
            key: 'value'
        }, {label: '合同/来源', key: 'contract'}], rows);
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

    function basisText(result) {
        return '数据已加载 · 截止 ' + display(result.as_of_trade_date) + ' · ' + display(result.snapshot_id) + ' · ' + display(result.basis) + ' · 当前表格只显示最新交易日；数值按终端习惯保留两位；NULL 保持 NULL。';
    }

    function historyRows(points) {
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
        return rows.slice(-30).reverse();
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
        api.technicalHistory({
            publication_id: current.publication_id,
            security_id: row.security_id,
            days: 60,
            price_basis: 'ADJUSTED',
            fields: 'ohlc,ma,amount,rps'
        }).then(function (result) {
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
            modal.open('技术历史 · ' + securityLabel(row), modalContent('历史数据暂时无法读取。', [{
                title: '原因',
                rows: [{label: '提示', value: error.message}]
            }]));
        });
    }

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
        }], items); else table.render(document.getElementById('technical-table'), [{
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
        }], items);
    }

    function loadTechnical() {
        if (!current) return;
        setNotice('正在读取个股技术数据…');
        var request = technicalState.mode === 'highs' ? api.newHighs(technicalParams()) : api.technical(technicalParams());
        request.then(function (result) {
            renderTechnical(result);
            setNotice('已加载 ' + (result.total || 0) + ' 条；当前页 ' + (result.items || []).length + ' 条。');
        }).catch(function (error) {
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
        })).then(function (timelineResult) {
            var timeline = timelineResult.value || {};
            optional(api.sectorMembersHistory({
                publication_id: current.publication_id,
                sector_id: row.sector_id,
                days: 10,
                state: 'ALL'
            })).then(function (memberResult) {
                optional(api.sectorLeaderHistory({
                    publication_id: current.publication_id,
                    sector_id: row.sector_id,
                    days: 30
                })).then(function (leaderResult) {
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

    function sectorRequest(level) {
        return api.sectorCycle({
            publication_id: current.publication_id,
            page: 1,
            page_size: 15,
            days: sectorState.days,
            sector_type: sectorState.type,
            hierarchy_level: level
        });
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
        setNotice('正在读取板块周期…');
        var typeName = sectorState.type === 'INDUSTRY' ? '行业' : sectorState.type === 'THEME' ? '概念' : sectorState.type === 'STYLE' ? '通达信风格' : '分类';
        var requests = sectorState.type === 'INDUSTRY' ? [sectorRequest('ROOT'), sectorRequest('LEAF')] : [sectorRequest('FLAT')];
        Promise.all(requests).then(function (results) {
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
            showSectorTableGroups(sectorState.type === 'INDUSTRY');
            var targets = sectorState.type === 'INDUSTRY' ? ['sector-root-table', 'sector-leaf-table'] : ['sector-flat-table'];
            targets.forEach(function (id) {
                var target = document.getElementById(id);
                target.replaceChildren();
                var empty = document.createElement('p');
                empty.className = 'empty';
                empty.textContent = '暂无周期数据：' + error.message;
                target.appendChild(empty);
            });
            setNotice('板块周期读取失败：' + error.message, true);
        });
    }

    function showPage(page) {
        currentPage = page;
        document.querySelectorAll('.nav-item').forEach(function (item) {
            item.classList.toggle('active', item.dataset.page === page);
        });
        overview.hidden = page !== 'overview';
        technicalPage.hidden = page !== 'stocks';
        sectorsPage.hidden = page !== 'sectors';
        if (page === 'overview') {
            document.getElementById('page-title').textContent = '研究总览';
            document.getElementById('page-description').textContent = '版本、输入身份与统一股票范围；证据统一在弹窗查看。';
            return;
        }
        if (page === 'stocks') {
            document.getElementById('page-title').textContent = '个股技术';
            document.getElementById('page-description').textContent = '新高、RPS、均线与量额状态；字段含义和使用方法见页面上方。';
            loadTechnical();
            return;
        }
        if (page === 'sectors') {
            document.getElementById('page-title').textContent = '板块周期';
            document.getElementById('page-description').textContent = '板块强弱周期与成员变化；详细数据统一在弹窗查看。';
            loadSectors();
            return;
        }
        modal.open('功能说明', modalContent('该导航页尚在后续升级范围内，当前不跳转、不把原始接口字段直接铺在页面上。', [{
            title: '当前状态',
            rows: [{
                label: '页面',
                value: page === 'candidates' ? '候选' : page === 'queues' ? '队列' : '联动'
            }, {label: '操作建议', value: '先使用“板块周期”和“个股技术”查看当前已构建数据'}]
        }]));
    }

    function load(publication) {
        current = publication;
        setNotice('正在读取当前发布版本摘要…');
        context.textContent = '交易日 ' + format.text(publication.trade_date) + ' · 当前发布版本';
        setText('publication-value', publication.trade_date);
        setText('publication-detail', publication.publication_id);
        Promise.all([api.identity(publication.publication_id, true), api.universeSummary(publication.publication_id)]).then(function (values) {
            var identity = values[0] || {}, universe = values[1] || {};
            setText('identity-value', first(identity, ['status']) || '已绑定');
            setText('identity-detail', first(identity, ['api_contract', 'contract']) || '输入身份可追溯');
            var count = first(universe, ['display_count', 'quote_valid_count', 'total']);
            setText('universe-value', count === null ? '已加载' : format.number(count, 0));
            setText('universe-detail', first(universe, ['scope', 'classification_summary']) || '统一 A 股范围');
            renderContext(publication, identity, universe);
            setNotice('摘要已加载；点击板块周期或个股技术查看数据。');
            document.getElementById('identity-evidence').onclick = function () {
                evidenceModal('输入身份证据', '以下内容用于核对当前发布版本绑定的输入来源。', identity);
            };
            document.getElementById('universe-evidence').onclick = function () {
                evidenceModal('统一股票范围说明', '以下内容用于核对股票范围、覆盖和边界。', universe);
            };
            if (currentPage === 'stocks') loadTechnical();
            if (currentPage === 'sectors') loadSectors();
        }).catch(function (error) {
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
        document.getElementById('sector-type').addEventListener('change', function () {
            sectorState.type = this.value;
            loadSectors();
        });
        document.getElementById('sector-days').addEventListener('change', function () {
            sectorState.days = Number(this.value);
            loadSectors();
        });
        document.getElementById('sector-refresh').addEventListener('click', loadSectors);
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
        var wanted = new URLSearchParams(location.search).get('publication_id');
        current = items.find(function (item) {
            return item.publication_id === wanted;
        }) || items[0];
        select.value = current.publication_id;
        select.addEventListener('change', function () {
            load(items.find(function (item) {
                return item.publication_id === select.value;
            }));
        });
        load(current);
    }).catch(function (error) {
        setNotice('版本列表读取失败：' + error.message, true);
    });
    document.querySelectorAll('.nav-item').forEach(function (button) {
        button.addEventListener('click', function () {
            showPage(button.dataset.page);
        });
    });
}());
