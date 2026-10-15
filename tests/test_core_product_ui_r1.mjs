import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { FilterPanel, Kline, StatCard } from '../src/workbench_service/static/core-product-r1/components.js';

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
