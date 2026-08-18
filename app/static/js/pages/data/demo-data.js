import { api } from "../../core/api.js";
import { setLoading, toast } from "../../core/dom.js";
import { state } from "../../state.js";

export function mountDemoData(root, { refreshGlobal }) {
  root.innerHTML = `<article class="card"><p class="section-kicker">DEMO</p><h3>没有真实数据？</h3><p class="helper-text">可以先生成明确标记为演示的数据体验完整诊断流程。</p><button data-seed-demo class="button ghost full">创建演示数据</button></article>`;
  root.querySelector("[data-seed-demo]").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    setLoading(button, true, "创建中…");
    try {
      await api(`/api/workspace/demo?shop_id=${state.selectedShopId}`, { method: "POST" });
      toast("演示数据已创建", "success");
      await refreshGlobal();
      document.dispatchEvent(new CustomEvent("pdd:data-updated", { detail: { source: "demo" } }));
    } catch (error) {
      toast(error.message, "error");
    } finally {
      setLoading(button, false);
    }
  });
}
