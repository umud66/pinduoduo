import { $ } from "../../core/dom.js";
import { state } from "../../state.js";
import { mountCapabilityProbe } from "./capability-probe.js";
import { mountDemoData } from "./demo-data.js";
import { mountReportImport } from "./report-import.js";
import { mountSyncCenter, unmountSyncCenter } from "./sync-center.js";

export function unmountDataPage() {
  unmountSyncCenter();
}

export async function renderDataPage({ navigate, refreshGlobal }) {
  const root = $("#data-content");
  if (!state.selectedShopId) {
    root.innerHTML = '<article class="card empty-state"><strong>请先创建店铺</strong><button class="button primary" data-settings>去设置</button></article>';
    root.querySelector("[data-settings]")?.addEventListener("click", () => navigate("settings"));
    return;
  }

  root.innerHTML = `<div class="two-column-layout"><div class="stack">
    <div id="sync-center-root"></div>
    <div id="capability-probe-root"></div>
    <div id="report-import-root"></div>
  </div><aside class="stack">
    <article class="card"><p class="section-kicker">DATA PRIORITY</p><h3>推荐顺序</h3><ol class="helper-text"><li>配置拼多多授权</li><li>运行能力检测</li><li>执行首次同步</li><li>导入曝光/点击/推广报表</li><li>查看自动诊断结果</li></ol></article>
    <div id="demo-data-root"></div>
    <article class="card"><p class="section-kicker">RECOVERY</p><h3>同步失败不用重新配置</h3><p class="helper-text">失败任务会保存原同步类型和参数，可直接重试。程序异常退出后的未完成任务也会在下次启动时自动转成可重试状态。</p></article>
  </aside></div>`;

  mountCapabilityProbe($("#capability-probe-root"), { navigate });
  mountReportImport($("#report-import-root"));
  mountDemoData($("#demo-data-root"), { refreshGlobal });
  await mountSyncCenter($("#sync-center-root"));
}
