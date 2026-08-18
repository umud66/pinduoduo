const state = {
  shops: [], providers: [], selectedShopId: null, page: 'dashboard', reportPreview: null, currentSkuId: null, wizardStep: 1,
};
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}
function formatMoney(value) { const n = Number(value || 0); return `¥${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }
function formatNumber(value) { return Number(value || 0).toLocaleString('zh-CN'); }
function formatPercent(value, digits = 1) { return value === null || value === undefined || Number.isNaN(Number(value)) ? '—' : `${(Number(value) * 100).toFixed(digits)}%`; }
function formatChange(value) {
  if (value === null || value === undefined) return '<span class="muted">暂无基线</span>';
  const n = Number(value), cls = n > 0 ? 'up' : n < 0 ? 'down' : '', sign = n > 0 ? '+' : '';
  return `<span class="change ${cls}">${sign}${(n * 100).toFixed(1)}% vs 7日均值</span>`;
}
function severityLabel(value) { return { high: '严重', medium: '关注', low: '轻微', healthy: '健康', unrun: '未诊断' }[value] || '未知'; }
function toast(message, type = '') {
  const item = document.createElement('div'); item.className = `toast ${type}`; item.innerHTML = `<span>${escapeHtml(message)}</span><span>×</span>`;
  item.addEventListener('click', () => item.remove()); $('#toast-stack').appendChild(item); setTimeout(() => item.remove(), 4200);
}
async function api(url, options = {}) {
  const response = await fetch(url, options); const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(String(data?.detail || data?.message || data || `请求失败 (${response.status})`));
  return data;
}
async function jsonApi(url, method, payload) { return api(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); }
function setButtonLoading(button, loading, text = '处理中…') {
  if (!button) return; if (loading) { button.dataset.originalText = button.textContent; button.textContent = text; button.disabled = true; }
  else { button.textContent = button.dataset.originalText || button.textContent; button.disabled = false; }
}
async function refreshCoreState() {
  const [shops, providers, bootstrap] = await Promise.all([api('/api/shops'), api('/api/ai/providers'), api('/api/workspace/bootstrap')]);
  state.shops = shops; state.providers = providers;
  const saved = Number(localStorage.getItem('pdd-selected-shop') || 0), validSaved = shops.some((shop) => shop.id === saved);
  if (!state.selectedShopId || !shops.some((shop) => shop.id === state.selectedShopId)) state.selectedShopId = validSaved ? saved : shops[0]?.id || null;
  if (state.selectedShopId) localStorage.setItem('pdd-selected-shop', String(state.selectedShopId));
  renderShopSelector(); renderProviderSelects(); renderProviderList(); fillShopSettings(); if (!bootstrap.setup_complete) showOnboarding(1); return bootstrap;
}
function renderShopSelector() {
  const select = $('#shop-select');
  if (!state.shops.length) { select.innerHTML = '<option value="">暂无店铺</option>'; select.disabled = true; return; }
  select.disabled = false; select.innerHTML = state.shops.map((shop) => `<option value="${shop.id}" ${shop.id === state.selectedShopId ? 'selected' : ''}>${escapeHtml(shop.name)}</option>`).join('');
}
function renderProviderSelects() {
  const select = $('#studio-provider');
  if (!state.providers.length) { select.innerHTML = '<option value="">未配置模型</option>'; select.disabled = true; return; }
  select.disabled = false; select.innerHTML = state.providers.filter((p) => p.enabled).map((p) => `<option value="${p.id}">${escapeHtml(p.name)} · ${escapeHtml(p.chat_model || '未设聊天模型')}</option>`).join('');
}
async function checkHealth() {
  const status = $('#service-status');
  try { const result = await api('/api/health'); status.textContent = result.ok ? '本地服务运行正常' : '服务状态异常'; status.className = `service-status ${result.ok ? 'ok' : 'bad'}`; }
  catch { status.textContent = '本地服务不可用'; status.className = 'service-status bad'; }
}
const pageMeta = { dashboard: ['店铺经营', '经营总览'], skus: ['诊断中心', 'SKU 诊断'], data: ['数据接入', '数据中心'], studio: ['AI 能力', 'AI 工作台'], settings: ['系统配置', '设置'] };
async function navigate(page) {
  state.page = page; $$('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.page === page));
  $$('[data-page-panel]').forEach((panel) => panel.classList.toggle('active', panel.dataset.pagePanel === page));
  $('#page-kicker').textContent = pageMeta[page][0]; $('#page-title').textContent = pageMeta[page][1];
  if (page === 'dashboard') await loadDashboard(); if (page === 'skus') await loadSkus(); if (page === 'data') await loadDataPage();
  if (page === 'studio') renderProviderSelects(); if (page === 'settings') { fillShopSettings(); renderProviderList(); }
}
function requireShop() { if (!state.selectedShopId) { toast('请先创建店铺', 'error'); showOnboarding(1); return false; } return true; }
function renderTrendSvg(items, field = 'gmv', height = 190) {
  if (!items?.length) return '<div class="empty-state">暂无趋势数据</div>';
  const values = items.map((item) => Number(item[field] || 0)), max = Math.max(...values, 1), min = Math.min(...values, 0), width = 720, pad = 18, usableW = width - pad * 2, usableH = height - pad * 2, range = Math.max(max - min, 1);
  const points = values.map((v, index) => [pad + (values.length === 1 ? usableW / 2 : (index / (values.length - 1)) * usableW), pad + ((max - v) / range) * usableH]);
  return `<svg class="trend-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><line x1="${pad}" y1="${height-pad}" x2="${width-pad}" y2="${height-pad}" stroke="#edf0f4"/><polyline points="${points.map(p => p.join(',')).join(' ')}" fill="none" stroke="#e02e24" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${points.map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="3.2" fill="#e02e24"><title>${escapeHtml(items[i].date)} ${formatMoney(values[i])}</title></circle>`).join('')}</svg><div class="chart-label-row"><span>${escapeHtml(items[0].date)}</span><span>${escapeHtml(items.at(-1).date)}</span></div>`;
}
async function loadDashboard() {
  const root = $('#dashboard-content'); if (!requireShop()) { root.innerHTML = ''; return; }
  root.className = 'page-content loading-block'; root.textContent = '正在加载经营数据…';
  try {
    const data = await api(`/api/dashboard?shop_id=${state.selectedShopId}`); root.className = 'page-content';
    if (data.data_state === 'empty') {
      root.innerHTML = `<article class="card empty-state"><strong>当前店铺还没有经营数据</strong><p>先导入 SKU 经营报表，系统就能计算趋势和异常。也可以用演示数据体验完整流程。</p><div class="card-actions" style="justify-content:center"><button class="button primary" data-empty-action="import">导入经营报表</button><button class="button ghost" data-empty-action="demo">创建演示数据</button></div></article>`;
      $('[data-empty-action="import"]', root)?.addEventListener('click', () => navigate('data')); $('[data-empty-action="demo"]', root)?.addEventListener('click', seedDemoData); return;
    }
    const m = data.metrics, urgent = data.urgent_skus || [];
    root.innerHTML = `<div class="stats-grid">
      <article class="stat-card"><span class="label">当日 GMV</span><strong>${formatMoney(m.gmv)}</strong><div class="stat-footer">${formatChange(data.changes.gmv)}</div></article>
      <article class="stat-card"><span class="label">销量</span><strong>${formatNumber(m.sales_qty)}</strong><div class="stat-footer">${formatChange(data.changes.sales_qty)}</div></article>
      <article class="stat-card"><span class="label">订单</span><strong>${formatNumber(m.order_count)}</strong><div class="stat-footer">${formatChange(data.changes.order_count)}</div></article>
      <article class="stat-card"><span class="label">退款率</span><strong>${formatPercent(m.refund_rate)}</strong><div class="stat-footer">最新数据 ${escapeHtml(data.latest_date)}</div></article>
      <article class="stat-card"><span class="label">SKU 数</span><strong>${formatNumber(m.sku_count)}</strong><div class="stat-footer">${formatNumber(m.product_count)} 个商品</div></article></div>
      <div class="dashboard-grid"><article class="card"><div class="card-heading"><div><p class="section-kicker">14 DAY TREND</p><h2>GMV 趋势</h2></div><span class="muted">截至 ${escapeHtml(data.latest_date)}</span></div>${renderTrendSvg(data.trend)}</article>
      <article class="card"><div class="card-heading"><div><p class="section-kicker">PRIORITY</p><h2>优先处理 SKU</h2></div><button class="button ghost" data-nav="skus">查看全部</button></div><div class="issue-list">${urgent.length ? urgent.map((item) => `<button class="issue-row" data-open-sku="${item.sku_id}" style="border:none;text-align:left;width:100%"><div><strong>${escapeHtml(item.product_title)}</strong><small>${escapeHtml(item.sku_name)} · ${escapeHtml(item.issue)}</small></div><div><span class="status-pill ${escapeHtml(item.severity)}">${severityLabel(item.severity)}</span><div class="health-score">${item.health_score}</div></div></button>`).join('') : '<div class="empty-state"><strong>暂无待处理项</strong><p>运行 SKU 批量诊断后，异常会出现在这里。</p><button class="button ghost" data-nav="skus">去诊断</button></div>'}</div></article></div>`;
    bindDynamicNavigation(root); $$('[data-open-sku]', root).forEach((el) => el.addEventListener('click', () => openSkuDrawer(Number(el.dataset.openSku))));
  } catch (error) { root.className = 'page-content'; root.innerHTML = `<article class="card empty-state"><strong>经营数据加载失败</strong><p>${escapeHtml(error.message)}</p></article>`; }
}
let skuSearchTimer = null;
async function loadSkus() {
  if (!requireShop()) return; const body = $('#sku-table-body'), empty = $('#sku-empty'); body.innerHTML = '<tr><td colspan="7" class="muted">正在加载 SKU…</td></tr>'; empty.classList.add('hidden');
  const q = encodeURIComponent($('#sku-search').value.trim()), severity = encodeURIComponent($('#severity-filter').value);
  try {
    const data = await api(`/api/skus?shop_id=${state.selectedShopId}&q=${q}&severity=${severity}`); $('#sku-count').textContent = `${data.total} 个 SKU`;
    if (!data.items.length) { body.innerHTML = ''; empty.classList.remove('hidden'); empty.innerHTML = `<strong>没有匹配的 SKU</strong><p>${q ? '换一个搜索条件试试。' : '请先在数据中心导入报表。'}</p>${!q ? '<button class="button primary" data-nav="data">去导入数据</button>' : ''}`; bindDynamicNavigation(empty); return; }
    body.innerHTML = data.items.map((item) => { const metric = item.metric || {}, diag = item.diagnosis, sev = diag?.severity || 'unrun', health = diag ? diag.health_score : '—', issue = diag?.main_issue || (diag ? `${diag.issue_count} 个问题` : '尚未运行诊断');
      return `<tr><td class="product-cell"><div class="product-line">${item.image_url ? `<img class="product-thumb" src="${escapeHtml(item.image_url)}" alt=""/>` : '<div class="product-thumb">SKU</div>'}<div><strong>${escapeHtml(item.product_title)}</strong><small>${escapeHtml(item.sku_name)} · ${escapeHtml(item.platform_sku_id)}</small></div></div></td><td>${formatNumber(metric.sales_qty)}</td><td>${formatMoney(metric.gmv)}</td><td>${item.stock ?? metric.stock ?? '—'}</td><td><span class="status-pill ${sev}">${severityLabel(sev)}</span> <strong style="margin-left:6px">${health}</strong></td><td>${escapeHtml(issue)}</td><td><button class="button ghost" data-open-sku="${item.id}">查看</button></td></tr>`;
    }).join(''); $$('[data-open-sku]', body).forEach((button) => button.addEventListener('click', () => openSkuDrawer(Number(button.dataset.openSku))));
  } catch (error) { body.innerHTML = `<tr><td colspan="7" class="muted">${escapeHtml(error.message)}</td></tr>`; }
}
function renderMiniSparkline(metrics, field = 'sales_qty') {
  if (!metrics?.length) return '<div class="muted">暂无趋势</div>'; const values = metrics.map((m) => Number(m?.[field] || 0)), max = Math.max(...values, 1), width = 540, height = 110, pad = 8;
  const points = values.map((v,index) => `${pad + (values.length===1 ? width/2 : index/(values.length-1)*(width-pad*2))},${height-pad-(v/max)*(height-pad*2)}`).join(' ');
  return `<svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><polyline points="${points}" fill="none" stroke="#e02e24" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}
async function openSkuDrawer(skuId) {
  state.currentSkuId = skuId; $('#drawer-backdrop').classList.remove('hidden'); $('#sku-drawer').classList.add('open'); $('#sku-drawer').setAttribute('aria-hidden','false'); $('#drawer-content').innerHTML = '<div class="loading-block">正在加载 SKU 详情…</div>';
  try { renderSkuDrawer(await api(`/api/skus/${skuId}`)); } catch (error) { $('#drawer-content').innerHTML = `<div class="empty-state"><strong>加载失败</strong><p>${escapeHtml(error.message)}</p></div>`; }
}
function closeSkuDrawer() { $('#sku-drawer').classList.remove('open'); $('#sku-drawer').setAttribute('aria-hidden','true'); $('#drawer-backdrop').classList.add('hidden'); state.currentSkuId = null; }
function evidenceText(evidence = {}) {
  const parts = []; for (const [key,value] of Object.entries(evidence)) { if (value === null || value === undefined) continue; let display = value;
    if (['change','current_ctr','baseline_ctr','current_cvr','baseline_cvr','current_refund_rate','baseline_refund_rate'].includes(key)) display = formatPercent(value); else if (typeof value === 'number') display = Number(value).toFixed(2).replace(/\.00$/,''); parts.push(`${key}: ${display}`); }
  return parts.join(' · ');
}
function renderSkuDrawer(detail) {
  $('#drawer-title').textContent = detail.sku_name; const metric = detail.latest_metric || {}, diag = detail.diagnosis, issues = diag?.issues || [], ai = diag?.ai_analysis;
  $('#drawer-content').innerHTML = `<div class="detail-hero">${detail.image_url ? `<img class="detail-image" src="${escapeHtml(detail.image_url)}" alt=""/>` : '<div class="detail-image">SKU</div>'}<div><h3>${escapeHtml(detail.product?.title || '未知商品')}</h3><p>${escapeHtml(detail.sku_name)} · SKU ${escapeHtml(detail.platform_sku_id)}</p><p>售价 ${detail.price === null ? '—' : formatMoney(detail.price)} · 当前库存 ${detail.stock ?? '—'}</p></div></div>
    <div class="mini-stats"><div class="mini-stat"><span>销量</span><strong>${formatNumber(metric.sales_qty)}</strong></div><div class="mini-stat"><span>GMV</span><strong>${formatMoney(metric.gmv)}</strong></div><div class="mini-stat"><span>CTR</span><strong>${formatPercent(metric.ctr)}</strong></div><div class="mini-stat"><span>转化率</span><strong>${formatPercent(metric.cvr)}</strong></div></div>
    <div class="sparkline-wrap"><div class="card-heading"><div><p class="section-kicker">SALES TREND</p><h3>近 30 日销量</h3></div></div>${renderMiniSparkline(detail.metrics)}</div>
    <div class="diagnosis-box">${diag ? `<div class="diagnosis-summary"><div><strong>健康度 ${diag.health_score} / 100</strong><div class="muted" style="font-size:11px;margin-top:3px">${issues.length} 个已识别问题 · ${escapeHtml(diag.period_end || '')}</div></div><span class="status-pill ${escapeHtml(diag.severity)}">${severityLabel(diag.severity)}</span></div>${issues.length ? issues.map((issue)=>`<div class="diagnosis-issue"><strong>${escapeHtml(issue.title)}</strong><p>${escapeHtml(evidenceText(issue.evidence))}</p><ol class="action-list">${(issue.actions||[]).map((action)=>`<li>${escapeHtml(action)}</li>`).join('')}</ol></div>`).join('') : '<div class="diagnosis-issue">没有触发异常规则。</div>'}` : '<div class="diagnosis-summary"><div><strong>尚未运行诊断</strong><div class="muted" style="font-size:11px;margin-top:3px">系统会将最新一天和前 7 日均值比较</div></div></div>'}</div>
    ${ai ? `<div class="ai-analysis"><strong>AI 运营建议</strong>\n\n${escapeHtml(ai.text || '')}</div>` : ''}<div class="card-actions"><button id="drawer-run-diagnosis" class="button primary">${diag ? '重新诊断' : '运行诊断'}</button>${diag && state.providers.length ? '<button id="drawer-ai-analysis" class="button secondary">生成 AI 建议</button>' : ''}</div>`;
  $('#drawer-run-diagnosis')?.addEventListener('click', runDrawerDiagnosis); $('#drawer-ai-analysis')?.addEventListener('click', () => runDrawerAi(diag.id));
}
async function runDrawerDiagnosis() {
  if (!state.currentSkuId) return; const button = $('#drawer-run-diagnosis'); setButtonLoading(button,true,'诊断中…');
  try { await api(`/api/diagnosis/skus/${state.currentSkuId}`, {method:'POST'}); toast('SKU 诊断完成','success'); renderSkuDrawer(await api(`/api/skus/${state.currentSkuId}`)); if (state.page === 'skus') await loadSkus(); }
  catch (error) { toast(error.message,'error'); setButtonLoading(button,false); }
}
async function runDrawerAi(diagnosisId) {
  const provider = state.providers.find((p)=>p.enabled && p.chat_model); if (!provider) { toast('请先配置带聊天模型的 AI Provider','error'); navigate('settings'); return; }
  const button = $('#drawer-ai-analysis'); setButtonLoading(button,true,'AI 分析中…');
  try { await api(`/api/diagnosis/${diagnosisId}/ai?provider_id=${provider.id}`, {method:'POST'}); toast('AI 建议已生成','success'); renderSkuDrawer(await api(`/api/skus/${state.currentSkuId}`)); }
  catch (error) { toast(error.message,'error'); setButtonLoading(button,false); }
}
async function runShopDiagnosis() {
  if (!requireShop()) return; const button = $('#run-shop-diagnosis'); setButtonLoading(button,true,'批量诊断中…');
  try { const result = await api(`/api/diagnosis/shops/${state.selectedShopId}/run`, {method:'POST'}); toast(`诊断完成：成功 ${result.success}，跳过 ${result.skipped}`, result.errors?.length ? 'error':'success'); await loadSkus(); }
  catch (error) { toast(error.message,'error'); } finally { setButtonLoading(button,false); }
}
async function loadDataPage() {
  if (!requireShop()) return; const shop = state.shops.find((item)=>item.id===state.selectedShopId), status = $('#pdd-config-status');
  status.className = `status-pill ${shop?.pdd_configured ? 'good':'neutral'}`; status.textContent = shop?.pdd_configured ? '已配置授权':'未配置授权';
}
async function runPddProbe() {
  if (!requireShop()) return; const button = $('#run-pdd-probe'), root = $('#probe-results'); setButtonLoading(button,true,'检测中…'); root.innerHTML = '<div class="muted">正在连接拼多多开放平台…</div>';
  try { const data = await api(`/api/pdd/shops/${state.selectedShopId}/probe`, {method:'POST'}); root.innerHTML = data.items.map((item)=>`<div class="probe-item"><div><code>${escapeHtml(item.api_type)}</code><small>${escapeHtml(item.message)}</small></div><span class="status-pill ${item.status==='ok'?'good':item.status==='denied'?'medium':'high'}">${item.status==='ok'?'可用':item.status==='denied'?'无权限':'错误'}</span></div>`).join(''); toast(`能力检测完成：${data.summary.ok || 0} 个接口可用`, data.summary.error ? 'error':'success'); }
  catch (error) { root.innerHTML = `<div class="empty-state"><strong>能力检测失败</strong><p>${escapeHtml(error.message)}</p></div>`; toast(error.message,'error'); } finally { setButtonLoading(button,false); }
}
async function previewReport(file) {
  if (!file) return; const root = $('#report-preview'); root.classList.remove('hidden'); root.innerHTML = '<div class="muted">正在读取报表并识别字段…</div>'; const form = new FormData(); form.append('file',file);
  try { const data = await api('/api/reports/preview',{method:'POST',body:form}); state.reportPreview = data; const headers=data.headers||[], rows=data.rows||[];
    root.innerHTML = `<div class="card-heading"><div><strong>${escapeHtml(data.original_filename || file.name)}</strong><div class="muted" style="font-size:11px;margin-top:4px">识别到 ${Object.keys(data.detected_fields||{}).length} 个标准字段</div></div><span class="status-pill ${data.can_import?'good':'high'}">${data.can_import?'可导入':'缺少必填列'}</span></div><div class="detected-fields">${Object.entries(data.detected_fields||{}).map(([key,column])=>`<span class="field-chip">${escapeHtml(key)} ← ${escapeHtml(column)}</span>`).join('')}</div>${!data.can_import?`<div class="form-note">缺少：${(data.missing_required||[]).map(escapeHtml).join('、')}。至少需要日期和 SKU ID。</div>`:''}<div class="preview-scroll"><table class="preview-table"><thead><tr>${headers.map((h)=>`<th>${escapeHtml(h)}</th>`).join('')}</tr></thead><tbody>${rows.slice(0,10).map((row)=>`<tr>${headers.map((h)=>`<td>${escapeHtml(row[h])}</td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="card-actions"><button id="commit-report" class="button primary" ${data.can_import?'':'disabled'}>确认导入到当前店铺</button><button id="change-report" class="button ghost">重新选择</button></div>`;
    $('#commit-report')?.addEventListener('click',commitReport); $('#change-report')?.addEventListener('click',()=>$('#report-file').click());
  } catch (error) { state.reportPreview=null; root.innerHTML=`<div class="empty-state"><strong>报表读取失败</strong><p>${escapeHtml(error.message)}</p></div>`; toast(error.message,'error'); }
}
async function commitReport() {
  if (!state.reportPreview || !requireShop()) return; const button=$('#commit-report'); setButtonLoading(button,true,'正在导入…');
  try { const result=await jsonApi('/api/reports/import','POST',{shop_id:state.selectedShopId,stored_as:state.reportPreview.stored_as}), s=result.summary; toast(`导入完成：${s.rows_imported} 行，新增 ${s.skus_created} 个 SKU`,'success');
    $('#report-preview').innerHTML=`<div class="empty-state"><strong>数据导入完成</strong><p>${escapeHtml(s.date_from||'')} 至 ${escapeHtml(s.date_to||'')} · ${s.rows_imported} 行有效数据</p><div class="card-actions" style="justify-content:center"><button id="after-import-diagnosis" class="button primary">立即批量诊断</button><button class="button ghost" data-nav="dashboard">查看经营总览</button></div></div>`;
    $('#after-import-diagnosis')?.addEventListener('click',async()=>{await api(`/api/diagnosis/shops/${state.selectedShopId}/run`,{method:'POST'});toast('批量诊断完成','success');navigate('skus');}); bindDynamicNavigation($('#report-preview')); await refreshCoreState();
  } catch (error) { toast(error.message,'error'); setButtonLoading(button,false); }
}
async function seedDemoData() {
  if (!requireShop()) return; const buttons=[$('#seed-demo'),$('#wizard-demo')].filter(Boolean); buttons.forEach((b)=>setButtonLoading(b,true,'正在创建…'));
  try { const result=await api(`/api/workspace/demo?shop_id=${state.selectedShopId}`,{method:'POST'}); await api(`/api/diagnosis/shops/${state.selectedShopId}/run`,{method:'POST'}); toast(`演示数据准备完成：${result.sku_count} 个 SKU`,'success'); hideOnboarding(); await refreshCoreState(); await navigate('dashboard'); }
  catch (error) { toast(error.message,'error'); } finally { buttons.forEach((b)=>setButtonLoading(b,false)); }
}
function fillShopSettings() {
  const shop=state.shops.find((item)=>item.id===state.selectedShopId); if(!shop)return; $('#setting-shop-name').value=shop.name||''; $('#setting-client-id').value=shop.client_id||''; $('#setting-client-secret').value=''; $('#setting-access-token').value='';
  $('#setting-client-secret').placeholder=shop.has_client_secret?'已保存 · 留空表示保持不变':'请输入 Client Secret'; $('#setting-access-token').placeholder=shop.has_access_token?'已保存 · 留空表示保持不变':'请输入 Access Token（如需要）';
}
async function saveShopSettings(event) {
  event.preventDefault(); if(!requireShop())return; const button=$('button[type="submit"]',event.currentTarget); setButtonLoading(button,true,'保存中…'); const payload={name:$('#setting-shop-name').value.trim(),client_id:$('#setting-client-id').value.trim()}, secret=$('#setting-client-secret').value.trim(), token=$('#setting-access-token').value.trim(); if(secret)payload.client_secret=secret;if(token)payload.access_token=token;
  try { await jsonApi(`/api/shops/${state.selectedShopId}`,'PUT',payload); await refreshCoreState(); toast('店铺设置已保存','success'); } catch(error){toast(error.message,'error');} finally{setButtonLoading(button,false);}
}
function renderProviderList() {
  const root=$('#provider-list'); if(!root)return; if(!state.providers.length){root.innerHTML='<div class="empty-state" style="padding:24px"><strong>还没有模型服务</strong><p>添加 OpenAI Compatible 中转站或官方 API。</p></div>';return;}
  root.innerHTML=state.providers.map((p)=>`<div class="provider-row"><div><strong>${escapeHtml(p.name)}</strong><small>${escapeHtml(p.provider_type)} · ${escapeHtml(p.chat_model||'未配置聊天模型')}<br>${escapeHtml(p.base_url)}</small></div><div class="provider-actions"><button class="button ghost" data-test-provider="${p.id}">测试</button><button class="button danger" data-delete-provider="${p.id}">删除</button></div></div>`).join('');
  $$('[data-test-provider]',root).forEach((b)=>b.addEventListener('click',()=>testProvider(Number(b.dataset.testProvider),b))); $$('[data-delete-provider]',root).forEach((b)=>b.addEventListener('click',()=>deleteProvider(Number(b.dataset.deleteProvider))));
}
async function addProvider(event) {
  event.preventDefault(); const button=$('button[type="submit"]',event.currentTarget); setButtonLoading(button,true,'保存中…'); const payload={name:$('#provider-name').value.trim(),provider_type:$('#provider-type').value,base_url:$('#provider-base-url').value.trim(),api_key:$('#provider-api-key').value.trim(),chat_model:$('#provider-chat-model').value.trim()||null,vision_model:$('#provider-vision-model').value.trim()||null,image_model:$('#provider-image-model').value.trim()||null};
  try { await jsonApi('/api/ai/providers','POST',payload); event.currentTarget.reset(); $('#provider-base-url').value='https://api.openai.com/v1'; await refreshCoreState(); toast('AI Provider 已保存','success'); } catch(error){toast(error.message,'error');} finally{setButtonLoading(button,false);}
}
async function testProvider(providerId,button){setButtonLoading(button,true,'测试中…');try{const result=await api(`/api/ai/providers/${providerId}/test`,{method:'POST'});toast(`连接成功：${result.response}`,'success');}catch(error){toast(error.message,'error');}finally{setButtonLoading(button,false);}}
async function deleteProvider(providerId){if(!confirm('确定删除这个 AI Provider？'))return;try{await api(`/api/ai/providers/${providerId}`,{method:'DELETE'});await refreshCoreState();toast('Provider 已删除','success');}catch(error){toast(error.message,'error');}}
async function sendChat(){const providerId=Number($('#studio-provider').value||0),prompt=$('#chat-prompt').value.trim();if(!providerId)return toast('请先配置 AI Provider','error');if(!prompt)return toast('请输入问题','error');const button=$('#send-chat'),root=$('#chat-result');setButtonLoading(button,true,'模型思考中…');root.classList.remove('empty-result');root.textContent='正在等待模型响应…';try{root.textContent=(await jsonApi(`/api/ai/providers/${providerId}/chat`,'POST',{prompt})).text;}catch(error){root.textContent=error.message;toast(error.message,'error');}finally{setButtonLoading(button,false);}}
async function generateImage(){const providerId=Number($('#studio-provider').value||0),prompt=$('#image-prompt').value.trim();if(!providerId)return toast('请先配置 AI Provider','error');if(!prompt)return toast('请输入图片描述','error');const button=$('#generate-image'),root=$('#image-results');setButtonLoading(button,true,'生成中…');root.innerHTML='<div class="muted">图片生成可能需要较长时间…</div>';try{const result=await jsonApi(`/api/ai/providers/${providerId}/images`,'POST',{prompt,size:$('#image-size').value});const images=[...(result.urls||[]).map((url)=>({src:url})),...(result.base64_images||[]).map((b64)=>({src:`data:image/png;base64,${b64}`}))];root.innerHTML=images.length?images.map((item)=>`<img src="${escapeHtml(item.src)}" alt="AI 生成商品素材"/>`).join(''):'<div class="muted">模型没有返回图片。</div>';}catch(error){root.innerHTML=`<div class="muted">${escapeHtml(error.message)}</div>`;toast(error.message,'error');}finally{setButtonLoading(button,false);}}
function showOnboarding(step=1){$('#onboarding').classList.remove('hidden');setWizardStep(step);} function hideOnboarding(){$('#onboarding').classList.add('hidden');}
function setWizardStep(step){state.wizardStep=step;$$('[data-wizard-step]').forEach((item)=>item.classList.toggle('active',Number(item.dataset.wizardStep)===step));$$('[data-wizard-indicator]').forEach((item)=>item.classList.toggle('active',Number(item.dataset.wizardIndicator)<=step));}
async function wizardCreateShop(event){event.preventDefault();const button=$('button[type="submit"]',event.currentTarget);setButtonLoading(button,true,'保存中…');try{const shop=await jsonApi('/api/shops','POST',{name:$('#wizard-shop-name').value.trim(),client_id:$('#wizard-client-id').value.trim()||null,client_secret:$('#wizard-client-secret').value.trim()||null,access_token:$('#wizard-access-token').value.trim()||null});state.selectedShopId=shop.id;await refreshCoreState();setWizardStep(2);}catch(error){toast(error.message,'error');}finally{setButtonLoading(button,false);}}
async function wizardCreateProvider(event){event.preventDefault();const key=$('#wizard-provider-key').value.trim();if(!key){setWizardStep(3);return;}const button=$('button[type="submit"]',event.currentTarget);setButtonLoading(button,true,'保存中…');try{await jsonApi('/api/ai/providers','POST',{name:$('#wizard-provider-name').value.trim()||'默认 AI',provider_type:$('#wizard-provider-type').value,base_url:$('#wizard-provider-url').value.trim(),api_key:key,chat_model:$('#wizard-provider-model').value.trim()||null,vision_model:null,image_model:$('#wizard-image-model').value.trim()||null});await refreshCoreState();setWizardStep(3);}catch(error){toast(error.message,'error');}finally{setButtonLoading(button,false);}}
function bindDynamicNavigation(root=document){$$('[data-nav]',root).forEach((button)=>{button.onclick=()=>navigate(button.dataset.nav);});}
function bindEvents(){
  $$('.nav-item').forEach((item)=>item.addEventListener('click',()=>navigate(item.dataset.page)));bindDynamicNavigation(document);
  $('#shop-select').addEventListener('change',async(event)=>{state.selectedShopId=Number(event.target.value)||null;if(state.selectedShopId)localStorage.setItem('pdd-selected-shop',String(state.selectedShopId));fillShopSettings();await navigate(state.page);});
  $('#quick-import').addEventListener('click',()=>navigate('data'));$('#run-shop-diagnosis').addEventListener('click',runShopDiagnosis);$('#run-pdd-probe').addEventListener('click',runPddProbe);$('#seed-demo').addEventListener('click',seedDemoData);$('#shop-settings-form').addEventListener('submit',saveShopSettings);$('#provider-form').addEventListener('submit',addProvider);$('#send-chat').addEventListener('click',sendChat);$('#generate-image').addEventListener('click',generateImage);
  $('#sku-search').addEventListener('input',()=>{clearTimeout(skuSearchTimer);skuSearchTimer=setTimeout(loadSkus,250);});$('#severity-filter').addEventListener('change',loadSkus);
  $('#report-file').addEventListener('change',(event)=>previewReport(event.target.files?.[0]));const drop=$('#drop-zone');['dragenter','dragover'].forEach((type)=>drop.addEventListener(type,(event)=>{event.preventDefault();drop.classList.add('dragover');}));['dragleave','drop'].forEach((type)=>drop.addEventListener(type,(event)=>{event.preventDefault();drop.classList.remove('dragover');}));drop.addEventListener('drop',(event)=>previewReport(event.dataTransfer?.files?.[0]));
  $('#close-drawer').addEventListener('click',closeSkuDrawer);$('#drawer-backdrop').addEventListener('click',closeSkuDrawer);document.addEventListener('keydown',(event)=>{if(event.key==='Escape')closeSkuDrawer();});
  $('#wizard-shop-form').addEventListener('submit',wizardCreateShop);$('#wizard-provider-form').addEventListener('submit',wizardCreateProvider);$('#skip-provider').addEventListener('click',()=>setWizardStep(3));$('#wizard-demo').addEventListener('click',seedDemoData);$('#wizard-go-import').addEventListener('click',()=>{hideOnboarding();navigate('data');setTimeout(()=>$('#report-file').click(),180);});$('#finish-wizard').addEventListener('click',()=>{hideOnboarding();navigate('dashboard');});
}
async function init(){bindEvents();checkHealth();try{await refreshCoreState();await navigate('dashboard');}catch(error){toast(`初始化失败：${error.message}`,'error');$('#dashboard-content').className='page-content';$('#dashboard-content').innerHTML=`<article class="card empty-state"><strong>系统初始化失败</strong><p>${escapeHtml(error.message)}</p></article>`;}}
init();
