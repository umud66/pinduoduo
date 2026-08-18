import { initSkuDrawer, openSkuDrawer } from "./components/sku-drawer.js";
import { bindShell, checkHealth, refreshGlobalState, showPage } from "./components/shell.js";
import { startSyncWatch } from "./components/sync-watch.js";
import { maybeShowOnboarding } from "./onboarding.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderDataPage, unmountDataPage } from "./pages/data/index.js";
import { loadSkus, mountSkusPage } from "./pages/skus.js";
import { renderSettings } from "./pages/settings.js";
import { renderStudio } from "./pages/studio.js";
import { state } from "./state.js";

async function refreshGlobal() {
  return refreshGlobalState();
}

async function navigate(page) {
  if (page !== "data") unmountDataPage();
  showPage(page);
  if (page === "dashboard") await renderDashboard({ navigate, openSku: openSkuDrawer });
  if (page === "skus") {
    mountSkusPage(openSkuDrawer);
    await loadSkus(openSkuDrawer);
  }
  if (page === "data") await renderDataPage({ navigate, refreshGlobal });
  if (page === "studio") renderStudio();
  if (page === "settings") renderSettings({ refreshGlobal });
}

async function refreshVisibleDataPage() {
  await refreshGlobal();
  if (state.currentPage === "dashboard") {
    await renderDashboard({ navigate, openSku: openSkuDrawer });
  } else if (state.currentPage === "skus") {
    await loadSkus(openSkuDrawer);
  }
}

async function bootstrap() {
  initSkuDrawer();
  bindShell(navigate, async () => {
    startSyncWatch();
    await navigate(document.querySelector(".nav-item.active")?.dataset.nav || "dashboard");
  });
  document.addEventListener("pdd:data-updated", () => {
    refreshVisibleDataPage().catch(console.error);
  });
  await checkHealth();
  await refreshGlobal();
  startSyncWatch();
  await navigate("dashboard");
  await maybeShowOnboarding(refreshGlobal, navigate);
}

bootstrap().catch((error) => {
  console.error(error);
  const status = document.querySelector("#service-status");
  if (status) {
    status.textContent = "初始化失败";
    status.className = "service-status bad";
  }
});
