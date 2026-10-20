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
  const bars = [{ trade_date: '2026-10-13', open: 10, high: 12, low: 9, close: 11, volume: 987654 }];
  const svg = Kline(bars, null);
  const rects = svg.children.filter(node => node.tagName === 'rect');
  const title = rects[0].children.find(node => node.tagName === 'title');
  assert.equal(rects.length, 1, 'only the price candle should render');
  assert.match(svg.children.at(-1).textContent, /成交量隐藏/);
  assert.doesNotMatch(title.textContent, /987654|量/);
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
