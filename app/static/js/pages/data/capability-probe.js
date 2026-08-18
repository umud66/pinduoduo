import { api } from "../../core/api.js";
import { setLoading, toast } from "../../core/dom.js";
import { escapeHtml } from "../../core/format.js";
import { state } from "../../state.js";

export function mountCapabilityProbe(root, { navigate }) {
  root.innerHTML = `<article class="card"><div class="card-heading"><div><p class="section-kicker">CAPABILITY PROBE</p><h2>API 能力检测</h2></div><span data-probe-status class="status-pill neutral">未检测</span></div><p class="helper-text">用已保存授权进行低频只读检测。接口代码已适配不代表你的应用一定拥有权限，真实结果以这里的检测为准。</p><div data-probe-results class="probe-list"></div><div class="card-actions"><button data-run-probe class="button secondary">运行能力检测</button><button data-settings class="button ghost">修改授权</button></div></article>`;
  root.querySelector("[data-settings]").addEventListener("click", () => navigate("settings"));
  root.querySelector("[data-run-probe]").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    setLoading(button, true, "检测中…");
    root.querySelector("[data-probe-results]").innerHTML = "";
    try {
      const result = await api(`/api/pdd/shops/${state.selectedShopId}/probe`, { method: "POST" });
      const status = root.querySelector("[data-probe-status]");
      status.textContent = result.summary?.error ? "部分异常" : result.summary?.denied ? "存在权限限制" : "检测完成";
      status.className = `status-pill ${result.summary?.error ? "failed" : result.summary?.denied ? "medium" : "success"}`;
      root.querySelector("[data-probe-results]").innerHTML = result.items.map((item) => `<div class="probe-row"><span><strong>${escapeHtml(item.api_type)}</strong><small>${escapeHtml(item.message)}</small></span><span class="status-pill ${item.status === "ok" ? "success" : item.status === "denied" ? "medium" : "failed"}">${item.status}</span></div>`).join("");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setLoading(button, false);
    }
  });
}
