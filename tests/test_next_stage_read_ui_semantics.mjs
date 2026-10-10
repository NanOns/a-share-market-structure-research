// Module contract tests, not browser/DOM or two-viewport acceptance.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {test} from 'node:test';

const source = await readFile(new URL('../src/workbench_service/static/core-product-r1/api.js', import.meta.url), 'utf8');
const api = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));

test('HTTP 200 with missing Owner fails only this consumer instead of becoming READY', async () => {
  let calls = 0;
  globalThis.fetch = async () => { calls++; return {ok:true,status:200,json:async()=>({status:'SOURCE_INCOMPLETE',reason:'NO_AUTHORIZED_COHORT_OWNER'})}; };
  await assert.rejects(api.read('forward'), error => error.code === 503 && error.data.status === 'SOURCE_INCOMPLETE');
  assert.equal(calls,1); // Bounded manual retry; no loop for absent authority.
});

test('503 is retryable by explicit user action; independent facts still read', async () => {
  let count = 0;
  globalThis.fetch = async url => {
    const fail = url.includes('/forward?') && count++ === 0;
    return {ok:!fail,status:fail?503:200,json:async()=>fail?{reason:'TEMPORARY_SOURCE_ERROR'}:{status:'READY',items:[]}};
  };
  await assert.rejects(api.read('forward'), error => error.code === 503);
  assert.equal((await api.read('stocks')).status,'READY');
  assert.equal((await api.read('forward')).status,'READY');
  assert.equal(count,2);
});

test('token conflict remains 409 and future date remains 400', async () => {
  for (const status of [409,400]) {
    globalThis.fetch = async () => ({ok:false,status,json:async()=>({reason:status===409?'CONTEXT_TOKEN_MISMATCH':'TARGET_DATE_NOT_GRANTED'})});
    await assert.rejects(api.read('stocks'), error => error.code === status);
  }
});

test('date selection binds token and requested historical date together', async () => {
  api.setContext({context_token:'BOUND_SOURCE_SHA',context:{trade_date:'2026-10-09'}});
  let request;
  globalThis.fetch = async (url,options) => {request={url,options};return {ok:true,status:200,json:async()=>({status:'READY'})};};
  await api.read('stocks',{trade_date:'2026-10-08'});
  const query = new URL(request.url,'http://test.invalid').searchParams;
  assert.equal(query.get('trade_date'),'2026-10-08');
  assert.equal(query.get('context_token'),'BOUND_SOURCE_SHA');
  assert.equal(request.options.cache,'no-store');
});

test('cancellation remains cancellation, without stale fallback data', async () => {
  globalThis.fetch = async () => {const error=new Error('cancelled');error.name='AbortError';throw error;};
  await assert.rejects(api.read('market'), error => error.name==='AbortError');
});
