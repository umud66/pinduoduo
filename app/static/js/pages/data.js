import { api, jsonApi } from "../core/api.js";
import { $, $$, setLoading, toast } from "../core/dom.js";
import { dateTime, escapeHtml } from "../core/format.js";
import { state } from "../state.js";

let syncPollTimer = null;
let reportPreview = null;

export function unmountDataPage() {
  if (syncPollTimer) clearTimeout(syncPollTimer);
  syncPollTimer = null;
}

export async function renderDataPage({ navigate, refreshGlobal }) {
  const root = $("#data-content");
  if (!state.selectedShopId) {
    root.innerHTML = '<article class="card empty-state"><strong>请先创建店铺</strong><button class="button primary" data-settings>去设置</button></article>';
    root.querySelector("[data-settings]")?.addEventListener("click", () => navigate("settings"));
    return;
  }
  root.innerHTML = `<div class="two-column-layout"><div class="stack">
    <article class="card" id="sync-card"><div class="card-heading"><div><p class="section-kicker">PDD SYNC</p><h2>拼多多自动同步</h2></div><span id="sync-state" class="status-pill neutral">读取中</span></div><p class="helper-text">商品/SKU 首次全量同步；订单和售后按时间窗口增量同步。同步任务在本机后台执行，不会阻塞页面。</p><div id="sync-content" class="loading-block">正在读取同步状态…</div></article>
    <article class="card"><div class="card-heading"><div><p class="section-kicker">CAPABILITY PROBE</p><h2>API 能力检测</h2></div><span id="probe-status" class="status-pill neutral">未检测</span></div><p class="helper-text">用已保存授权进行低频只读检测。接口存在不代表你的应用一定拥有权限。</p><div id="probe-results" class="probe-list"></div><div class="card-actions"><button id="run-probe" class="button secondary">运行能力检测</button><button class="button ghost" data-settings>修改授权</button></div></article>
    <article class="card"><div class="card-heading"><div><p class="section-kicker">REPORT IMPORT</p><h2>补充经营报表</h2></div><span class="status-pill good">曝光/点击/推广</span></div><p class="helper-text">API 获取不到的经营指标仍通过 CSV/XLSX 补齐。系统会先预览字段，再由你确认写入 SQLite。</p><label id="drop-zone" class="drop-zone"><input id="report-file" type="file" accept=".csv,.xlsx,.xlsm" hidden><div class="drop-icon">⇧</div><strong>选择报表文件</strong><span>或将文件拖到这里</span></label><div id="report-preview" class="report-preview hidden"></div></article>
    </div><aside class="stack"><article class="card"><p class="section-kicker">DATA PRIORITY</p><h3>推荐顺序</h3><ol class="helper-text"><li>配置拼多多授权</li><li>运行能力检测</li><li>执行首次同步</li><li>导入曝光/点击/推广报表</li><li>运行 SKU 诊断</li></ol></article><article class="card"><p class="section-kicker">DEMO</p><h3>没有真实数据？</h3><p class="helper-text">可以先生成演示数据体验完整诊断流程。</p><button id="seed-demo" class="button ghost full">创建演示数据</button></article></aside></div>`;
  root.querySelectorAll("[data-settings]").forEach((button) => button.addEventListener("click", () => navigate("settings")));
  bindProbe(); bindReport(); bindDemo(refreshGlobal); await refreshSyncStatus();
}

async function refreshSyncStatus() {
  if (!state.selectedShopId || !$("#sync-content")) return;
  try {
    const data = await api(`/api/sync/shops/${state.selectedShopId}/status`);
    renderSyncStatus(data);
    if (data.active) syncPollTimer = setTimeout(refreshSyncStatus, 2200);
  } catch (error) { $("#sync-content").innerHTML = `<div class="empty-state"><strong>同步状态读取失败</strong><p>${escapeHtml(error.message)}</p></div>`; }
}

function renderSyncStatus(data) {
  const badge = $("#sync-state");
  badge.textContent = data.active ? "同步中" : data.configured ? "已就绪" : "未配置";
  badge.className = `status-pill ${data.active ? "running" : data.configured ? "success" : "neutral"}`;
  const cursors = data.cursors || {}; const pref = data.preference || {}; const latestJob = data.jobs?.[0];
  $("#sync-content").className = "";
  $("#sync-content").innerHTML = `<div class="sync-summary"><div><small>商品</small><strong>${data.product_count}</strong></div><div><small>SKU</small><strong>${data.sku_count}</strong></div><div><small>订单同步</small><strong>${dateTime(cursors.orders?.last_synced_at_iso)}</strong></div><div><small>售后同步</small><strong>${dateTime(cursors.refunds?.last_synced_at_iso)}</strong></div></div>
    ${latestJob ? renderCurrentJob(latestJob) : ""}
    <div class="sync-actions"><button class="button primary" data-sync="full" ${data.active || !data.configured ? "disabled" : ""}>首次/全量同步</button><button class="button secondary" data-sync="incremental" ${data.active || !data.configured ? "disabled" : ""}>立即增量同步</button><button class="button ghost" data-sync="products" ${data.active || !data.configured ? "disabled" : ""}>只同步商品</button></div>
    <div class="sync-options"><label class="switch"><input id="auto-sync" type="checkbox" ${pref.auto_sync ? "checked" : ""} ${!data.configured ? "disabled" : ""}> 自动同步</label><label class="field" style="display:flex;align-items:center;gap:8px">间隔<select id="sync-interval" style="width:auto">${[15,30,60,120,360].map((value) => `<option value="${value}" ${Number(pref.interval_minutes) === value ? "selected" : ""}>${value >= 60 ? `${value / 60} 小时` : `${value} 分钟`}</option>`).join("")}</select></label></div>
    <details ${data.jobs?.length ? "" : "open"}><summary>最近同步任务</summary><div class="sync-job-list">${(data.jobs || []).map(renderJob).join("") || '<div class="empty-state">还没有同步任务</div>'}</div></details>${!data.configured ? '<div class="form-note">请先在设置中填写 Client ID、Client Secret 和 Access Token。</div>' : ""}`;
  $$('[data-sync]', $("#sync-content")).forEach((button) => button.addEventListener("click", () => startSync(button.dataset.sync, button)));
  $("#auto-sync")?.addEventListener("change", savePreference); $("#sync-interval")?.addEventListener("change", savePreference);
}
function renderCurrentJob(job) { const progress = Number(job.stats?.progress || (job.status === "success" ? 100 : 8)); return `<div class="card compact" style="margin:12px 0"><div class="card-heading"><div><strong>${jobLabel(job.job_type)}</strong><small>${escapeHtml(job.stats?.stage || job.status)}</small></div><span class="status-pill ${job.status}">${jobStatus(job.status)}</span></div><div class="progress-bar"><span style="width:${Math.max(3, Math.min(progress, 100))}%"></span></div>${job.error_message ? `<p class="helper-text down">${escapeHtml(job.error_message)}</p>` : ""}</div>`; }
function renderJob(job) { return `<div class="sync-job-row"><span><strong>${jobLabel(job.job_type)}</strong><small>${dateTime(job.created_at)} · ${escapeHtml(job.stats?.stage || "")}</small></span><span class="status-pill ${job.status}">${jobStatus(job.status)}</span></div>`; }
function jobLabel(type) { return { full: "首次/全量同步", incremental: "增量同步", products: "商品同步", orders: "订单同步", refunds: "售后同步" }[type] || type; }
function jobStatus(status) { return { queued: "排队中", running: "进行中", success: "成功", failed: "失败" }[status] || status; }
async function startSync(type, button) { setLoading(button, true, "已提交…"); try { const suffix = type === "full" ? "?lookback_days=30" : ""; await api(`/api/sync/shops/${state.selectedShopId}/${type}${suffix}`, { method: "POST" }); toast("同步任务已提交", "success"); await refreshSyncStatus(); } catch (error) { toast(error.message, "error"); } finally { setLoading(button, false); } }
async function savePreference() { try { await jsonApi(`/api/sync/shops/${state.selectedShopId}/preference`, "PUT", { auto_sync: $("#auto-sync").checked, interval_minutes: Number($("#sync-interval").value) }); toast("自动同步设置已保存", "success"); } catch (error) { toast(error.message, "error"); } }

function bindProbe() { $("#run-probe").addEventListener("click", async (event) => { setLoading(event.currentTarget, true, "检测中…"); $("#probe-results").innerHTML = ""; try { const result = await api(`/api/pdd/shops/${state.selectedShopId}/probe`, { method: "POST" }); $("#probe-status").textContent = result.summary?.error ? "部分异常" : "检测完成"; $("#probe-status").className = "status-pill success"; $("#probe-results").innerHTML = result.items.map((item) => `<div class="probe-row"><span><strong>${escapeHtml(item.api_type)}</strong><small>${escapeHtml(item.message)}</small></span><span class="status-pill ${item.status === "ok" ? "success" : item.status === "denied" ? "medium" : "failed"}">${item.status}</span></div>`).join(""); } catch (error) { toast(error.message, "error"); } finally { setLoading(event.currentTarget, false); } }); }

function bindReport() { const input = $("#report-file"), zone = $("#drop-zone"); input.addEventListener("change", () => input.files[0] && previewReport(input.files[0])); ["dragenter","dragover"].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add("dragover"); })); ["dragleave","drop"].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.remove("dragover"); })); zone.addEventListener("drop", (event) => event.dataTransfer.files[0] && previewReport(event.dataTransfer.files[0])); }
async function previewReport(file) { const box = $("#report-preview"); box.classList.remove("hidden"); box.innerHTML = '<div class="loading-block">正在识别报表…</div>'; const form = new FormData(); form.append("file", file); try { reportPreview = await api("/api/reports/preview", { method: "POST", body: form }); box.innerHTML = `<div class="field-tags">${Object.entries(reportPreview.detected_fields || {}).map(([field, header]) => `<span class="field-tag">${escapeHtml(field)} ← ${escapeHtml(header)}</span>`).join("")}</div>${reportPreview.can_import ? '<p class="helper-text">已识别日期和 SKU ID，可以导入。</p>' : `<p class="helper-text down">缺少必需字段：${escapeHtml((reportPreview.missing_required || []).join(", "))}</p>`}<div class="card-actions"><button id="confirm-report-import" class="button primary" ${reportPreview.can_import ? "" : "disabled"}>确认导入</button></div>`; $("#confirm-report-import")?.addEventListener("click", confirmReportImport); } catch (error) { box.innerHTML = `<p class="helper-text down">${escapeHtml(error.message)}</p>`; } }
async function confirmReportImport(event) { setLoading(event.currentTarget, true, "导入中…"); try { const result = await jsonApi("/api/reports/import", "POST", { shop_id: state.selectedShopId, stored_as: reportPreview.stored_as }); toast(`导入完成：${result.summary?.rows_imported || result.summary?.rows || 0} 行`, "success"); } catch (error) { toast(error.message, "error"); } finally { setLoading(event.currentTarget, false); } }
function bindDemo(refreshGlobal) { $("#seed-demo").addEventListener("click", async (event) => { setLoading(event.currentTarget, true, "创建中…"); try { await api(`/api/workspace/demo?shop_id=${state.selectedShopId}`, { method: "POST" }); toast("演示数据已创建", "success"); await refreshGlobal(); } catch (error) { toast(error.message, "error"); } finally { setLoading(event.currentTarget, false); } }); }
