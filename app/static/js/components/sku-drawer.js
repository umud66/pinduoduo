import { api } from "../core/api.js";
import { $, setLoading, toast } from "../core/dom.js";
import { escapeHtml, money, percent } from "../core/format.js";
import { state } from "../state.js";
import { renderDiagnosisPanel } from "./diagnosis-panel.js";

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
    const product = data.product || {};
    $("#drawer-content").innerHTML = `
      <div class="stack">
        <article class="card compact"><p class="section-kicker">PRODUCT</p><h3>${escapeHtml(product.title || "未命名商品")}</h3><p class="helper-text">${escapeHtml(data.sku_name)} · SKU ${escapeHtml(data.platform_sku_id)}</p></article>
        <div class="metric-grid">
          <div class="metric-box"><small>销量</small><strong>${latest.sales_qty ?? 0}</strong></div>
          <div class="metric-box"><small>GMV</small><strong>${money(latest.gmv)}</strong></div>
          <div class="metric-box"><small>CTR</small><strong>${percent(latest.ctr)}</strong></div>
          <div class="metric-box"><small>CVR</small><strong>${percent(latest.cvr)}</strong></div>
          <div class="metric-box"><small>退款率</small><strong>${percent(latest.refund_rate)}</strong></div>
          <div class="metric-box"><small>推广 ROI</small><strong>${latest.ad_roi === null || latest.ad_roi === undefined ? "—" : Number(latest.ad_roi).toFixed(2)}</strong></div>
        </div>
        <section id="sku-diagnosis-panel">${renderDiagnosisPanel(diagnosis)}</section>
        <article class="card compact"><div class="card-heading"><div><p class="section-kicker">ACTIONS</p><h3>重新计算与 AI 跟进</h3></div></div><p class="helper-text">确定性诊断由程序计算；AI 只基于诊断结果补充执行建议，不修改指标。</p><div class="card-actions"><button class="button secondary" data-run-diagnosis>重新诊断</button>${state.providers.length ? '<button class="button primary" data-ai-analysis>生成 AI 建议</button>' : ""}</div></article>
      </div>`;

    $("#drawer-content").querySelector("[data-run-diagnosis]")?.addEventListener("click", async (event) => {
      setLoading(event.currentTarget, true, "重新计算中…");
      try {
        await api(`/api/diagnosis/skus/${skuId}`, { method: "POST" });
        toast("诊断完成", "success");
        await openSkuDrawer(skuId);
        document.dispatchEvent(new CustomEvent("pdd:data-updated", { detail: { source: "diagnosis" } }));
      } catch (error) {
        toast(error.message, "error");
      } finally {
        setLoading(event.currentTarget, false);
      }
    });

    $("#drawer-content").querySelector("[data-ai-analysis]")?.addEventListener("click", async (event) => {
      const providerId = state.providers.find((provider) => provider.enabled)?.id;
      const diagnosisId = diagnosis?.id || diagnosis?.diagnosis_id;
      if (!providerId || !diagnosisId) return toast("请先完成诊断并配置可用 AI Provider", "error");
      setLoading(event.currentTarget, true, "AI 分析中…");
      try {
        await api(`/api/diagnosis/${diagnosisId}/ai?provider_id=${providerId}`, { method: "POST" });
        toast("AI 建议已生成", "success");
        await openSkuDrawer(skuId);
      } catch (error) {
        toast(error.message, "error");
      } finally {
        setLoading(event.currentTarget, false);
      }
    });
  } catch (error) {
    $("#drawer-content").innerHTML = `<div class="empty-state"><strong>加载失败</strong><p>${escapeHtml(error.message)}</p></div>`;
  }
}
