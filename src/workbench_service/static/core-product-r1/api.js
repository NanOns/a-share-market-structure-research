let context = null;

export function setContext(value) {
  context = value;
}

export function getContext() {
  return context;
}

function errorMessage(path, params, response, data) {
  const readFailure = data.code === 'PRODUCT_READ_FAILED';
  const reason = String(data.reason || '来源描述符不可用');
  if (path === 'radar/priority' && readFailure && reason.startsWith('RESEARCH_PRIORITY_BINDING_MISSING')) {
    const token = context?.context_token || '未知';
    const tradeDate = params?.trade_date || context?.context?.trade_date || '未知';
    return `对应候选研究优先级尚未生成（T0 ${tradeDate}；token ${token}）。已知缺口：当前候选没有绑定 Priority Owner；旧 token 结果不能跨版本复用。`;
  }
  if (path === 'radar/priority' && readFailure &&
      ['RESEARCH_PRIORITY_SCOPE_INVALID', 'RESEARCH_PRIORITY_RANKABILITY_INVALID', 'INVALID_QUERY_BOUND'].includes(reason)) {
    return '筛选参数无效，请调整后重试。';
  }
  if (response.status === 409) {
    return data.reason === 'CONTEXT_TOKEN_MISMATCH' || String(data.code).startsWith('CONTEXT_CONFLICT')
      ? '数据版本已变化，请刷新工作台。'
      : '数据来源校验未通过，请查看诊断。';
  }
  if (response.status === 404) {
    return data.code === 'IDENTITY_OUTSIDE_CURRENT_DAILY_UNIVERSE'
      ? '该证券身份存在，但不在当前日行情池。'
      : '未找到该证券或板块，请检查代码。';
  }
  if (response.status === 400) {
    if (readFailure && reason.startsWith('PG_HISTORY_')) {
      return '历史行情尚未绑定有效的 PostgreSQL 来源，请查看数据与诊断。';
    }
    if (readFailure) {
      return '数据来源读取校验未通过：' + reason.slice(0, 120) + '。未回退到其他日期，请查看诊断。';
    }
    return '筛选参数无效，请调整后重试。';
  }
  if (response.status === 429) return '请求频繁，请稍后重试。';
  if (response.status === 501) return '该能力尚待后续任务接入。';
  return '读取失败，请重试。';
}

export async function read(path, params = {}, signal) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value === undefined || value === null || value === '') continue;
    query.set(key, String(value));
  }
  if (context && path !== 'context') {
    query.set('context_token', context.context_token);
    if (!query.has('trade_date')) query.set('trade_date', context.context.trade_date);
  }

  let response;
  try {
    response = await fetch('/api/v4/' + path + '?' + query, { signal, cache: 'no-store' });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('研究服务连接中断，请在服务恢复后重试。');
  }

  const data = await response.json();
  if (!response.ok) {
    const error = new Error(errorMessage(path, params, response, data));
    error.code = response.status;
    error.data = data;
    throw error;
  }
  if (data.status === 'SOURCE_INCOMPLETE') {
    const error = new Error('该领域来源能力不足：' +
      (data.reason || data.code || '当期运营 Owner 尚未接通') + '。当前没有混用旧日期数据。');
    error.code = 503;
    error.data = data;
    throw error;
  }
  return data;
}
