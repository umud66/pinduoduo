import { api } from "../core/api.js";
import { $, $$ } from "../core/dom.js";
import { hydrateShops, selectShop, state } from "../state.js";

const PAGE_META = {
  dashboard: ["店铺经营", "经营总览"],
  skus: ["诊断中心", "SKU 诊断"],
  data: ["数据接入", "数据中心"],
  studio: ["AI 能力", "AI 工作台"],
  settings: ["系统配置", "设置"],
};

export async function refreshGlobalState() {
  const [shops, providers] = await Promise.all([api("/api/shops"), api("/api/ai/providers")]);
  hydrateShops(shops);
  state.providers = providers;
  renderShopSelector();
  return { shops, providers };
}

export function renderShopSelector() {
  const select = $("#shop-select");
  if (!state.shops.length) {
    select.innerHTML = '<option value="">暂无店铺</option>';
    select.disabled = true;
    return;
  }
  select.disabled = false;
  select.innerHTML = state.shops.map((shop) => `<option value="${shop.id}" ${shop.id === state.selectedShopId ? "selected" : ""}>${shop.name}</option>`).join("");
}

export async function checkHealth() {
  const status = $("#service-status");
  try {
    const result = await api("/api/health");
    status.textContent = result.ok ? "本地服务运行正常" : "服务状态异常";
    status.className = `service-status ${result.ok ? "ok" : "bad"}`;
  } catch {
    status.textContent = "本地服务不可用";
    status.className = "service-status bad";
  }
}

export function bindShell(onNavigate, onShopChange) {
  $$('[data-nav]').forEach((button) => button.addEventListener("click", (event) => {
    event.preventDefault();
    onNavigate(button.dataset.nav);
  }));
  $("#shop-select").addEventListener("change", () => {
    selectShop($("#shop-select").value);
    onShopChange();
  });
}

export function showPage(page) {
  state.currentPage = page;
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.nav === page));
  $$(".page").forEach((panel) => panel.classList.toggle("active", panel.id === `page-${page}`));
  $("#page-kicker").textContent = PAGE_META[page][0];
  $("#page-title").textContent = PAGE_META[page][1];
}
