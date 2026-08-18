import { api } from "../core/api.js";
import { $, setLoading, toast } from "../core/dom.js";
import { escapeHtml, money, percent, severityLabel } from "../core/format.js";
import { state } from "../state.js";

function closeDrawer() {
  $("#sku-drawer").classList.remove("open");
  $("#drawer-backdrop").classList.add("hidden");
  $("#sku-drawer").setAttribute("aria-hidden", "true");
}

export function initSkuDrawer() {
  $("#close-drawer").addEventListener("click", closeDrawer);
  $("#drawer-backdrop").addEventListener("click", closeDrawer);
}

export async function openSkuDrawer(skuId) {
  $("#sku-drawer").classList.add("open");
  $("#drawer-backdrop").classList.remove("hidden");
  $("#sku-drawer").setAttribute("aria-hidden", "false");
  $("#drawer-content").innerHTML = '<div class="loading-block">正在读取 SKU…</div>';
  try {
    const data = await api(`/api/skus/${skuId}`);
    $("#drawer-title").textContent = data.sku_name || "SKU 详情";
    const latest = data.latest_metric || {};
    const diagnosis = data.diagnosis;
    $("#drawer-content").innerHTML = `
      <div class="stack">
        <article class="card compact"><p class="section-kicker">PRODUCT</p><h3>${escapeHtml(data.product_title)}</h3><p class="helper-text">${escapeHtml(data.sku_name)} · SKU ${escapeHtml(data.platform_sku_id)}</p></article>
        <div class="metric-grid">
          <div class="metric-box"><small>销量</small><strong>${latest.sales_qty ?? 0}</strong></div>
          <div class="metric-box"><small>GMV</small><strong>${money(latest.gmv)}</strong></div>
          <div class="metric-box"><small>CTR</small><strong>${percent(latest.ctr)}</strong></div>
          <div class="metric-box"><small>CVR</small><strong>${percent(latest.cvr)}</strong></div>
        </div>
        <article class="card">
          <div class="card-heading"><div><p class="section-kicker">DIAGNOSIS</p><h2>SKU 诊断</h2></div>${diagnosis ? `<span class="status-pill ${diagnosis.severity}">${severityLabel(diagnosis.severity)} · ${diagnosis.health_score}</span>` : ""}</div>
          <div>${diagnosis ? renderDiagnosis(diagnosis) : '<div class="empty-state">尚未运行诊断</div>'}</div>
          <div class="card-actions"><button class="button secondary" data-run-diagnosis>重新诊断</button>${state.providers.length ? '<button class="button primary" data-ai-analysis>生成 AI 建议</button>' : ""}</div>
        </article>
      </div>`;
    $("#drawer-content").querySelector("[data-run-diagnosis]")?.addEventListener("click", async (event) => {
      setLoading(event.currentTarget, true);
      try { await api(`/api/diagnosis/skus/${skuId}`, { method: "POST" }); toast("诊断完成", "success"); await openSkuDrawer(skuId); }
      catch (error) { toast(error.message, "error"); }
      finally { setLoading(event.currentTarget, false); }
    });
    $("#drawer-content").querySelector("[data-ai-analysis]")?.addEventListener("click", async (event) => {
      const providerId = state.providers.find((provider) => provider.enabled)?.id;
      if (!providerId || !diagnosis?.diagnosis_id) return toast("请先配置可用 AI Provider", "error");
      setLoading(event.currentTarget, true, "AI 分析中…");
      try {
        const result = await api(`/api/diagnosis/${diagnosis.diagnosis_id}/ai?provider_id=${providerId}`, { method: "POST" });
        const box = document.createElement("div"); box.className = "ai-result"; box.textContent = result.text || JSON.stringify(result, null, 2); event.currentTarget.closest(".card").appendChild(box);
      } catch (error) { toast(error.message, "error"); }
      finally { setLoading(event.currentTarget, false); }
    });
  } catch (error) {
    $("#drawer-content").innerHTML = `<div class="empty-state"><strong>加载失败</strong><p>${escapeHtml(error.message)}</p></div>`;
  }
}

function renderDiagnosis(diagnosis) {
  const items = diagnosis.issues || diagnosis.problems || [];
  if (!items.length) return '<div class="empty-state">当前未发现明显异常</div>';
  return items.map((item) => `<div class="diagnosis-item"><strong>${escapeHtml(item.title || item.message || item.code || "异常")}</strong><p class="helper-text">${escapeHtml(item.reason || item.description || item.action || "")}</p></div>`).join("");
}
