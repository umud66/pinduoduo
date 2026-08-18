import { api, jsonApi } from "../../core/api.js";
import { setLoading, toast } from "../../core/dom.js";
import { escapeHtml } from "../../core/format.js";
import { state } from "../../state.js";

let reportPreview = null;

export function mountReportImport(root) {
  root.innerHTML = `<article class="card"><div class="card-heading"><div><p class="section-kicker">REPORT IMPORT</p><h2>补充经营报表</h2></div><span class="status-pill good">曝光/点击/推广</span></div><p class="helper-text">API 获取不到的经营指标仍通过 CSV/XLSX 补齐。系统会先识别字段，再由你确认写入 SQLite。</p><label data-drop-zone class="drop-zone"><input data-report-file type="file" accept=".csv,.xlsx,.xlsm" hidden><div class="drop-icon">⇧</div><strong>选择报表文件</strong><span>或将文件拖到这里</span></label><div data-report-preview class="report-preview hidden"></div></article>`;
  const input = root.querySelector("[data-report-file]");
  const zone = root.querySelector("[data-drop-zone]");
  input.addEventListener("change", () => input.files[0] && previewReport(root, input.files[0]));
  ["dragenter", "dragover"].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add("dragover"); }));
  ["dragleave", "drop"].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.remove("dragover"); }));
  zone.addEventListener("drop", (event) => event.dataTransfer.files[0] && previewReport(root, event.dataTransfer.files[0]));
}

async function previewReport(root, file) {
  const box = root.querySelector("[data-report-preview]");
  box.classList.remove("hidden");
  box.innerHTML = '<div class="loading-block">正在识别报表…</div>';
  const form = new FormData();
  form.append("file", file);
  try {
    reportPreview = await api("/api/reports/preview", { method: "POST", body: form });
    box.innerHTML = `<div class="field-tags">${Object.entries(reportPreview.detected_fields || {}).map(([field, header]) => `<span class="field-tag">${escapeHtml(field)} ← ${escapeHtml(header)}</span>`).join("")}</div>${reportPreview.can_import ? '<p class="helper-text">已识别日期和 SKU ID，可以导入。</p>' : `<p class="helper-text down">缺少必需字段：${escapeHtml((reportPreview.missing_required || []).join(", "))}</p>`}<div class="card-actions"><button data-confirm-import class="button primary" ${reportPreview.can_import ? "" : "disabled"}>确认导入</button></div>`;
    box.querySelector("[data-confirm-import]")?.addEventListener("click", (event) => confirmReportImport(event.currentTarget));
  } catch (error) {
    box.innerHTML = `<p class="helper-text down">${escapeHtml(error.message)}</p>`;
  }
}

async function confirmReportImport(button) {
  setLoading(button, true, "导入中…");
  try {
    const result = await jsonApi("/api/reports/import", "POST", { shop_id: state.selectedShopId, stored_as: reportPreview.stored_as });
    toast(`导入完成：${result.summary?.rows_imported || result.summary?.rows || 0} 行`, "success");
    document.dispatchEvent(new CustomEvent("pdd:data-updated", { detail: { source: "report" } }));
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(button, false);
  }
}
