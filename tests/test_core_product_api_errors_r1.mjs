import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { read, setContext } from '../src/workbench_service/static/core-product-r1/api.js';

const originalFetch = globalThis.fetch;
after(() => {
  globalThis.fetch = originalFetch;
  setContext(null);
});

function response(status, body) {
  return { ok: false, status, json: async () => body };
}

test('priority binding absence explains missing owner and identifies the candidate context', async () => {
  const token = 'candidate-token-20261014';
  setContext({ context_token: token, context: { trade_date: '2026-10-14' } });
  globalThis.fetch = async () => response(400, {
    code: 'PRODUCT_READ_FAILED', reason: 'RESEARCH_PRIORITY_BINDING_MISSING',
  });

  await assert.rejects(read('radar/priority', { scope: 'stocks' }), error => {
    assert.match(error.message, /对应候选研究优先级尚未生成/);
    assert.match(error.message, /2026-10-14/);
    assert.match(error.message, new RegExp(token));
    assert.match(error.message, /当前候选没有绑定 Priority Owner/);
    assert.doesNotMatch(error.message, /筛选参数无效/);
    return true;
  });
});

test('invalid priority query parameters retain the filter error message', async () => {
  setContext({ context_token: 'candidate-token', context: { trade_date: '2026-10-14' } });
  globalThis.fetch = async () => response(400, {
    code: 'PRODUCT_READ_FAILED', reason: 'INVALID_QUERY_BOUND',
  });

  await assert.rejects(read('radar/priority', { scope: 'stocks' }), error => {
    assert.match(error.message, /筛选参数无效/);
    assert.doesNotMatch(error.message, /Priority Owner/);
    return true;
  });
});

test('candidate preview binding absence is explained through its operational error wrapper', async () => {
  const token = 'candidate-token-20261014';
  setContext({ context_token: token, context: { trade_date: '2026-10-14' } });
  globalThis.fetch = async () => response(400, {
    code: 'INVALID_OPERATIONAL_QUERY', reason: 'RESEARCH_PRIORITY_BINDING_MISSING',
  });

  await assert.rejects(read('radar/priority', { scope: 'stocks' }), error => {
    assert.match(error.message, /对应候选研究优先级尚未生成/);
    assert.match(error.message, new RegExp(token));
    assert.doesNotMatch(error.message, /筛选参数无效/);
    return true;
  });
});

test('candidate preview query bounds retain the filter error message', async () => {
  setContext({ context_token: 'candidate-token', context: { trade_date: '2026-10-14' } });
  globalThis.fetch = async () => response(400, {
    code: 'INVALID_OPERATIONAL_QUERY', reason: 'INVALID_QUERY_BOUND',
  });

  await assert.rejects(read('radar/priority', { scope: 'stocks' }), error => {
    assert.match(error.message, /筛选参数无效/);
    assert.doesNotMatch(error.message, /Priority Owner/);
    return true;
  });
});
