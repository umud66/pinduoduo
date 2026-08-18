import { api } from "../core/api.js";
import { $, $$, setLoading, toast } from "../core/dom.js";
import { escapeHtml, money, severityLabel } from "../core/format.js";
import { state } from "../state.js";

let debounceTimer = null;

export function mountSkusPage(openSku) {
  const root = $("#skus-content");
  root.innerHTML = `<div class="toolbar card compact"><input id="sku-search" type="search" placeholder="搜索商品名、SKU、商品 ID"><select id="severity-filter" class="control"><option value="all">全部状态</option><option value="high">严重</option><option value="medium">关注</option><option value="healthy">健康</option><option value="unrun">未诊断</option></select><button id="run-shop-diagnosis" class="button primary">批量诊断</button></div><article class="card"><div class="card-heading"><div><p class="section-kicker">SKU WORKBENCH</p><h2>SKU 经营状态</h2></div><span id="sku-count" class="muted">0 个 SKU</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>商品 / SKU</th><th>销量</th><th>GMV</th><th>库存</th><th>健康度</th><th>主要问题</th><th></th></tr></thead><tbody id="sku-table-body"></tbody></table></div><div id="sku-empty" class="empty-state hidden"></div></article>`;
  $("#sku-search").addEventListener("input", () => { clearTimeout(debounceTimer); debounceTimer = setTimeout(() => loadSkus(openSku), 250); });
  $("#severity-filter").addEventListener("change", () => loadSkus(openSku));
  $("#run-shop-diagnosis").addEventListener("click", async (event) => {
    if (!state.selectedShopId) return;
    setLoading(event.currentTarget, true, "诊断中…");
    try { const result = await api(`/api/diagnosis/shops/${state.selectedShopId}/run`, { method: "POST" }); toast(`诊断完成：${result.success} 个 SKU`, "success"); await loadSkus(openSku); }
    catch (error) { toast(error.message, "error"); }
    finally { setLoading(event.currentTarget, false); }
  });
}

export async function loadSkus(openSku) {
  const body = $("#sku-table-body"); const empty = $("#sku-empty");
  if (!body || !state.selectedShopId) return;
  body.innerHTML = '<tr><td colspan="7" class="muted">正在加载 SKU…</td></tr>'; empty.classList.add("hidden");
  const query = encodeURIComponent($("#sku-search")?.value.trim() || ""); const severity = encodeURIComponent($("#severity-filter")?.value || "all");
  try {
    const data = await api(`/api/skus?shop_id=${state.selectedShopId}&q=${query}&severity=${severity}`); $("#sku-count").textContent = `${data.total} 个 SKU`;
    if (!data.items.length) { body.innerHTML = ""; empty.classList.remove("hidden"); empty.innerHTML = "<strong>没有匹配的 SKU</strong><p>请调整筛选条件，或先到数据中心同步/导入数据。</p>"; return; }
    body.innerHTML = data.items.map((item) => { const metric = item.metric || {}; const diag = item.diagnosis; const sev = diag?.severity || "unrun"; const issue = diag?.main_issue || (diag ? `${diag.issue_count || 0} 个问题` : "尚未诊断"); return `<tr><td><div class="product-line">${item.image_url ? `<img class="product-thumb" src="${escapeHtml(item.image_url)}" alt="">` : '<span class="product-thumb"></span>'}<span><strong>${escapeHtml(item.product_title)}</strong><small>${escapeHtml(item.sku_name)} · ${escapeHtml(item.platform_sku_id)}</small></span></div></td><td>${metric.sales_qty ?? 0}</td><td>${money(metric.gmv)}</td><td>${item.stock ?? metric.stock ?? "—"}</td><td><span class="status-pill ${sev}">${severityLabel(sev)}</span> ${diag?.health_score ?? "—"}</td><td>${escapeHtml(issue)}</td><td><button class="button ghost" data-open-sku="${item.id}">查看</button></td></tr>`; }).join("");
    $$('[data-open-sku]', body).forEach((button) => button.addEventListener("click", () => openSku(Number(button.dataset.openSku))));
  } catch (error) { body.innerHTML = `<tr><td colspan="7">${escapeHtml(error.message)}</td></tr>`; }
}
