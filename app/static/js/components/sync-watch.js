import { api } from "../core/api.js";
import { $, toast } from "../core/dom.js";
import { state } from "../state.js";

let timer = null;
const lastSeenByShop = new Map();

export function startSyncWatch() {
  stopSyncWatch();
  tick();
}

export function stopSyncWatch() {
  if (timer) clearTimeout(timer);
  timer = null;
}

async function tick() {
  const badge = $("#global-sync-status");
  if (!state.selectedShopId) {
    if (badge) {
      badge.textContent = "未选择店铺";
      badge.className = "status-pill neutral";
    }
    timer = setTimeout(tick, 15000);
    return;
  }

  try {
    const data = await api(`/api/sync/shops/${state.selectedShopId}/status`);
    renderBadge(badge, data);
    detectNewCompletion(data);
    timer = setTimeout(tick, data.active ? 5000 : 30000);
  } catch {
    if (badge) {
      badge.textContent = "同步状态未知";
      badge.className = "status-pill neutral";
    }
    timer = setTimeout(tick, 30000);
  }
}

function renderBadge(badge, data) {
  if (!badge) return;
  if (data.active) {
    badge.textContent = "数据同步中";
    badge.className = "status-pill running";
  } else if (!data.configured) {
    badge.textContent = "PDD 未配置";
    badge.className = "status-pill neutral";
  } else if (data.latest_failed_job_id && (!data.latest_success_job_id || data.latest_failed_job_id > data.latest_success_job_id)) {
    badge.textContent = "最近同步失败";
    badge.className = "status-pill failed";
  } else {
    badge.textContent = "同步已就绪";
    badge.className = "status-pill success";
  }
}

function detectNewCompletion(data) {
  const latest = data.jobs?.find((job) => job.status === "success" || job.status === "failed");
  if (!latest) return;
  const shopId = state.selectedShopId;
  const signature = `${latest.id}:${latest.status}`;
  const previous = lastSeenByShop.get(shopId);
  lastSeenByShop.set(shopId, signature);
  if (!previous || previous === signature) return;

  if (latest.status === "success") {
    document.dispatchEvent(new CustomEvent("pdd:data-updated", { detail: { source: "sync", job: latest } }));
    toast("拼多多数据同步完成，诊断结果已更新", "success");
  } else {
    toast("拼多多同步失败，可在数据中心按原参数重试", "error");
  }
}
