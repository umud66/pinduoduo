import { api } from "../core/api.js";
import { $, $$ } from "../core/dom.js";
import { escapeHtml, money, number, percent, severityLabel } from "../core/format.js";
import { state } from "../state.js";

function trendSvg(items) {
  if (!items?.length) return '<div class="empty-state">暂无趋势数据</div>';
  const values = items.map((item) => Number(item.gmv || 0)); const max = Math.max(...values, 1); const width = 720, height = 190, pad = 18;
  const points = values.map((value, index) => [pad + (values.length === 1 ? (width - pad * 2) / 2 : index / (values.length - 1) * (width - pad * 2)), pad + (max - value) / max * (height - pad * 2)]);
  return `<svg class="trend-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><polyline points="${points.map((point) => point.join(",")).join(" ")}" fill="none" stroke="#e02e24" stroke-width="3" stroke-linecap="round"/></svg><div class="chart-label-row"><span>${escapeHtml(items[0].date)}</span><span>${escapeHtml(items.at(-1).date)}</span></div>`;
}

export async function renderDashboard({ navigate, openSku }) {
  const root = $("#dashboard-content");
  if (!state.selectedShopId) {
    root.innerHTML = '<article class="card empty-state"><strong>请先创建店铺</strong><p>完成首次设置后才能开始分析。</p><button class="button primary" data-go-settings>创建店铺</button></article>';
    root.querySelector("[data-go-settings]")?.addEventListener("click", () => navigate("settings")); return;
  }
  root.innerHTML = '<div class="loading-block">正在加载经营数据…</div>';
  try {
    const data = await api(`/api/dashboard?shop_id=${state.selectedShopId}`);
    if (data.data_state === "empty") {
      root.innerHTML = '<article class="card empty-state"><strong>当前店铺还没有经营数据</strong><p>优先连接拼多多自动同步，也可以导入经营报表。</p><button class="button primary" data-go-data>去数据中心</button></article>';
      root.querySelector("[data-go-data]")?.addEventListener("click", () => navigate("data")); return;
    }
    const m = data.metrics;
    root.innerHTML = `<div class="stats-grid">
      <article class="stat-card"><span class="label">当日 GMV</span><strong>${money(m.gmv)}</strong><div class="stat-footer">最新 ${escapeHtml(data.latest_date)}</div></article>
      <article class="stat-card"><span class="label">销量</span><strong>${number(m.sales_qty)}</strong><div class="stat-footer">订单 ${number(m.order_count)}</div></article>
      <article class="stat-card"><span class="label">退款率</span><strong>${percent(m.refund_rate)}</strong><div class="stat-footer">退款 ${number(m.refund_count)}</div></article>
      <article class="stat-card"><span class="label">商品</span><strong>${number(m.product_count)}</strong><div class="stat-footer">${number(m.sku_count)} 个 SKU</div></article>
      <article class="stat-card"><span class="label">数据状态</span><strong>${data.data_state === "ready" ? "可诊断" : "待补充"}</strong><div class="stat-footer">本地 SQLite</div></article>
    </div><div class="dashboard-grid">
      <article class="card"><div class="card-heading"><div><p class="section-kicker">14 DAY TREND</p><h2>GMV 趋势</h2></div></div>${trendSvg(data.trend)}</article>
      <article class="card"><div class="card-heading"><div><p class="section-kicker">PRIORITY</p><h2>优先处理 SKU</h2></div><button class="button ghost" data-view-all>查看全部</button></div><div class="issue-list">${(data.urgent_skus || []).length ? data.urgent_skus.map((item) => `<button class="issue-row" data-sku="${item.sku_id}"><span><strong>${escapeHtml(item.product_title)}</strong><small>${escapeHtml(item.sku_name)} · ${escapeHtml(item.issue)}</small></span><span><span class="status-pill ${item.severity}">${severityLabel(item.severity)}</span><div class="health-score">${item.health_score}</div></span></button>`).join("") : '<div class="empty-state">暂无待处理项</div>'}</div></article>
    </div>`;
    root.querySelector("[data-view-all]")?.addEventListener("click", () => navigate("skus"));
    $$('[data-sku]', root).forEach((button) => button.addEventListener("click", () => openSku(Number(button.dataset.sku))));
  } catch (error) { root.innerHTML = `<article class="card empty-state"><strong>加载失败</strong><p>${escapeHtml(error.message)}</p></article>`; }
}
