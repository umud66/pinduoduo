import { api, jsonApi } from "../../core/api.js";
import { $, $$, setLoading, toast } from "../../core/dom.js";
import { dateTime, escapeHtml } from "../../core/format.js";
import { state } from "../../state.js";

let pollTimer = null;

export function unmountSyncCenter() {
  if (pollTimer) clearTimeout(pollTimer);
  pollTimer = null;
}

export async function mountSyncCenter(root) {
  root.innerHTML = `<article class="card"><div class="card-heading"><div><p class="section-kicker">PDD SYNC</p><h2>拼多多自动同步</h2></div><span id="sync-state" class="status-pill neutral">读取中</span></div><p class="helper-text">商品/SKU 首次全量同步；订单和售后按时间窗口增量同步。任务在本机后台执行，同步完成后会自动重新计算指标并运行确定性诊断。</p><div id="sync-content" class="loading-block">正在读取同步状态…</div></article>`;
  await refreshSyncStatus();
}

async function refreshSyncStatus() {
  if (!state.selectedShopId || !$("#sync-content")) return;
  try {
    const data = await api(`/api/sync/shops/${state.selectedShopId}/status`);
    renderSyncStatus(data);
    pollTimer = setTimeout(refreshSyncStatus, data.active ? 2200 : 10000);
  } catch (error) {
    $("#sync-content").innerHTML = `<div class="empty-state"><strong>同步状态读取失败</strong><p>${escapeHtml(error.message)}</p></div>`;
  }
}

function renderSyncStatus(data) {
  const badge = $("#sync-state");
  badge.textContent = data.active ? "同步中" : data.configured ? "已就绪" : "未配置";
  badge.className = `status-pill ${data.active ? "running" : data.configured ? "success" : "neutral"}`;
  const cursors = data.cursors || {};
  const pref = data.preference || {};
  const latestJob = data.jobs?.[0];
  $("#sync-content").className = "";
  $("#sync-content").innerHTML = `<div class="sync-summary"><div><small>商品</small><strong>${data.product_count}</strong></div><div><small>SKU</small><strong>${data.sku_count}</strong></div><div><small>订单同步</small><strong>${dateTime(cursors.orders?.last_synced_at_iso)}</strong></div><div><small>售后同步</small><strong>${dateTime(cursors.refunds?.last_synced_at_iso)}</strong></div></div>
    ${latestJob ? renderCurrentJob(latestJob) : ""}
    <div class="sync-actions"><button class="button primary" data-sync="full" ${data.active || !data.configured ? "disabled" : ""}>首次/全量同步</button><button class="button secondary" data-sync="incremental" ${data.active || !data.configured ? "disabled" : ""}>立即增量同步</button><button class="button ghost" data-sync="products" ${data.active || !data.configured ? "disabled" : ""}>只同步商品</button></div>
    <div class="sync-options"><label class="switch"><input id="auto-sync" type="checkbox" ${pref.auto_sync ? "checked" : ""} ${!data.configured ? "disabled" : ""}> 自动同步</label><label class="field" style="display:flex;align-items:center;gap:8px">间隔<select id="sync-interval" style="width:auto">${[15,30,60,120,360].map((value) => `<option value="${value}" ${Number(pref.interval_minutes) === value ? "selected" : ""}>${value >= 60 ? `${value / 60} 小时` : `${value} 分钟`}</option>`).join("")}</select></label></div>
    <details ${data.jobs?.some((job) => job.status === "failed") ? "open" : ""}><summary>最近同步任务</summary><div class="sync-job-list">${(data.jobs || []).map(renderJob).join("") || '<div class="empty-state">还没有同步任务</div>'}</div></details>
    ${!data.configured ? '<div class="form-note">请先在设置中填写 Client ID、Client Secret 和 Access Token。</div>' : ""}`;

  $$('[data-sync]', $("#sync-content")).forEach((button) => button.addEventListener("click", () => startSync(button.dataset.sync, button)));
  $$('[data-retry-job]', $("#sync-content")).forEach((button) => button.addEventListener("click", () => retryJob(Number(button.dataset.retryJob), button)));
  $("#auto-sync")?.addEventListener("change", savePreference);
  $("#sync-interval")?.addEventListener("change", savePreference);
}

function renderCurrentJob(job) {
  const progress = Number(job.stats?.progress || (job.status === "success" ? 100 : 8));
  const diagnosis = job.stats?.diagnosis;
  return `<div class="card compact" style="margin:12px 0"><div class="card-heading"><div><strong>${jobLabel(job.job_type)}</strong><small>${escapeHtml(job.stats?.stage || job.status)}</small></div><span class="status-pill ${job.status}">${jobStatus(job.status)}</span></div><div class="progress-bar"><span style="width:${Math.max(3, Math.min(progress, 100))}%"></span></div>${diagnosis ? `<p class="helper-text">自动诊断：${diagnosis.success || 0} 个 SKU 完成，${diagnosis.skipped || 0} 个跳过。</p>` : ""}${job.error_message ? `<p class="helper-text down">${escapeHtml(job.error_message)}</p>` : ""}${job.retryable ? `<div class="card-actions"><button class="button secondary" data-retry-job="${job.id}">按原参数重试</button></div>` : ""}</div>`;
}

function renderJob(job) {
  const retry = job.retryable ? `<button class="button ghost" data-retry-job="${job.id}">重试</button>` : "";
  return `<div class="sync-job-row"><span><strong>${jobLabel(job.job_type)}</strong><small>${dateTime(job.created_at)} · ${escapeHtml(job.stats?.stage || "")}${job.retry_of ? ` · 重试 #${job.retry_of}` : ""}</small></span><span style="display:flex;align-items:center;gap:8px"><span class="status-pill ${job.status}">${jobStatus(job.status)}</span>${retry}</span></div>`;
}

function jobLabel(type) {
  return { full: "首次/全量同步", incremental: "增量同步", products: "商品同步", orders: "订单同步", refunds: "售后同步" }[type] || type;
}
function jobStatus(status) {
  return { queued: "排队中", running: "进行中", success: "成功", failed: "失败" }[status] || status;
}

async function startSync(type, button) {
  setLoading(button, true, "已提交…");
  try {
    const suffix = type === "full" ? "?lookback_days=30" : "";
    await api(`/api/sync/shops/${state.selectedShopId}/${type}${suffix}`, { method: "POST" });
    toast("同步任务已提交", "success");
    await refreshSyncStatus();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(button, false);
  }
}

async function retryJob(jobId, button) {
  setLoading(button, true, "重试中…");
  try {
    await api(`/api/sync/jobs/${jobId}/retry`, { method: "POST" });
    toast("已按原参数创建重试任务", "success");
    await refreshSyncStatus();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setLoading(button, false);
  }
}

async function savePreference() {
  try {
    await jsonApi(`/api/sync/shops/${state.selectedShopId}/preference`, "PUT", {
      auto_sync: $("#auto-sync").checked,
      interval_minutes: Number($("#sync-interval").value),
    });
    toast("自动同步设置已保存", "success");
  } catch (error) {
    toast(error.message, "error");
  }
}
