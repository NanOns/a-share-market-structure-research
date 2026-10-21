import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { FilterPanel, Kline, StatCard } from '../src/workbench_service/static/core-product-r1/components.js';
import { rotationAutoAcceptanceComplete, rotationAutoAcceptance } from '../src/workbench_service/static/core-product-r1/rotation-auto-acceptance.js';
import { ResearchHeader } from '../src/workbench_service/static/research/components.js';

class Node {
  constructor(tag) { this.tagName = tag; this.children = []; this.attributes = {}; this.value = ''; this.disabled = false; }
  append(...items) { this.children.push(...items); }
  setAttribute(key, value) { this.attributes[key] = value; }
}

globalThis.document = {
  createElement: tag => new Node(tag),
  createElementNS: (_namespace, tag) => new Node(tag),
};
after(() => { delete globalThis.document; });

test('research UI components module parses and exports its snapshot header', () => {
  assert.equal(typeof ResearchHeader, 'function');
});

test('unverified index volume is absent from chart bars and hover text', () => {
  const bars = [{ trade_date: '2026-10-13', open: 10, high: 12, low: 9, close: 11, volume: 987654, quality: 'KNOWN' }];
  const svg = Kline(bars, null);
  const rects = svg.children.filter(node => node.tagName === 'rect');
  const title = rects[0].children.find(node => node.tagName === 'title');
  assert.equal(rects.length, 1, 'only the price candle should render');
  assert.match(svg.children.at(-1).textContent, /成交量隐藏/);
  assert.doesNotMatch(title.textContent, /987654|量/);
});

test('K-line preserves unknown trading-day slots and splits moving averages at gaps', () => {
  const bars = Array.from({ length: 8 }, (_, i) => ({
    trade_date: `2026-10-${String(10 + i).padStart(2, '0')}`,
    open: 10 + i, high: 11 + i, low: 9 + i, close: 10.5 + i,
    volume: 100, quality: 'KNOWN', reason: null, ma5: 10 + i, ma20: 10 + i, ma60: 10 + i,
  }));
  for (const i of [0, 3, 4, 5, 7]) Object.assign(bars[i], {
    open: null, high: null, low: null, close: null, quality: 'UNKNOWN', reason: 'PRICE_ADJUSTMENT_UNSUPPORTED',
  });
  const svg = Kline(bars, null);
  const candles = svg.children.filter(node => node.tagName === 'rect');
  const gaps = svg.children.filter(node => node.tagName === 'line' && node.attributes['stroke-dasharray'] === '2 2');
  const averages = svg.children.filter(node => node.tagName === 'polyline');
  assert.equal(candles.length, 3);
  assert.equal(gaps.length, 5, 'leading, internal, and trailing unknown rows remain visible');
  assert.equal(averages.length, 6, 'each MA has separate segments before and after the three-row gap');
  const slots = candles.map(node => Number(node.attributes.x) + Number(node.attributes.width) / 2);
  assert.equal(slots[1] - slots[0], 105, 'two adjacent known trading days retain adjacent slots');
  assert.equal(slots[2] - slots[1], 420, 'the three unknown trading-day slots are not compressed');
  assert.ok(averages.every(node => node.attributes.points.trim().split(' ').length <= 2));
  assert.ok(gaps.every(node => /PRICE_ADJUSTMENT_UNSUPPORTED/.test(node.children[0].textContent)));
});

test('missing MA values split lines even when the candle OHLC is known', () => {
  const bars = Array.from({ length: 4 }, (_, i) => ({
    trade_date: `2026-10-${10 + i}`, open: 10, high: 11, low: 9, close: 10.5,
    volume: 10, quality: 'KNOWN', ma5: 10, ma20: 10, ma60: 10,
  }));
  bars[1].ma5 = null;
  const svg = Kline(bars, null);
  const ma5 = svg.children.filter(node => node.tagName === 'polyline' && node.attributes.stroke === '#ca9623');
  assert.equal(ma5.length, 2);
  assert.deepEqual(ma5.map(node => node.attributes.points.trim().split(' ').length), [1, 2]);
});

test('sector search does not offer maturity or health classification filters without admitted owners', () => {
  const form = FilterPanel(() => {}, '', 'id', '', 'sectors', {});
  const selects = form.children.filter(node => node.tagName === 'select');
  const labels = selects.map(node => node.attributes['aria-label']);
  assert.deepEqual(labels, ['排序', '研究状态筛选']);
  assert.ok(!labels.some(label => /成熟度|健康/.test(label)));
});

test('Radar card labels the standalone change count scope', () => {
  const card = StatCard('研究雷达', { value: 12, status: 'PARTIAL', scope: 'TODAY_CHANGE_STANDALONE', href: '/v4/research/radar' });
  const metadata = card.children.find(node => node.tagName === 'small');
  assert.match(metadata.textContent, /独立个股变化数（轮动覆盖项单列）/);
  assert.equal(card.children.find(node => node.tagName === 'a').href, '/v4/research/radar');
});

function rotationFixture() {
  const contextToken = 'candidate-token';
  const summary = {
    automatic_acceptance_contract: 'V4_ROTATION_PIPELINE_AUTO_ACCEPTANCE_R1',
    automatic_acceptance_state: 'AUTO_ACCEPTED_WITH_LIMITATIONS',
    automatic_acceptance_scope: 'OWNER_DATA_COMPLETE_FOR_DISPLAY_ONLY',
    owner_bound: true, formal_publication: false,
    numeric_acceptance: 'NOT_INDEPENDENTLY_VALIDATED',
    total: 2, expected_total: 2, covered_total: 2,
    current_states: { UNKNOWN: 1, NONE: 0 },
  };
  const rows = [
    { entity_id: 'INDUSTRY:1', output_state: 'UNKNOWN' },
    { entity_id: 'THEME:2', output_state: 'NONE' },
  ];
  const pages = [{ offset: 0, limit: 200, total: 2, context_token: contextToken, items: rows }];
  return { contextToken, summary, rows, pages };
}

test('rotation completeness accepts complete same-token owner rows and preserves unknown status', () => {
  const { contextToken, summary, pages } = rotationFixture();
  assert.equal(rotationAutoAcceptanceComplete(summary, pages, contextToken), true);
  const card = rotationAutoAcceptance(summary, pages, '2026-10-20', contextToken, 0);
  const rendered = card.children.map(child => child.textContent).join(' ');
  assert.match(rendered, /完整，可用于本日候选展示/);
  assert.match(rendered, /未知 1/);
  assert.match(rendered, /不代表轮动数值已独立验收/);
});

test('rotation completeness rejects a missing row, duplicate identity, and mismatched token', () => {
  const { contextToken, summary, rows, pages } = rotationFixture();
  assert.equal(rotationAutoAcceptanceComplete(summary, [{ ...pages[0], items: rows.slice(0, 1) }], contextToken), false);
  assert.equal(rotationAutoAcceptanceComplete(summary, [{ ...pages[0], items: [rows[0], rows[0]] }], contextToken), false);
  assert.equal(rotationAutoAcceptanceComplete(summary, [{ ...pages[0], context_token: 'stale-token' }], contextToken), false);
});
