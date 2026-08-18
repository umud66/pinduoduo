import { api, jsonApi } from "./core/api.js";
import { $, $$, setLoading, toast } from "./core/dom.js";
import { state } from "./state.js";

let step = 1;

export async function maybeShowOnboarding(refreshGlobal, navigate) {
  const status = await api("/api/workspace/bootstrap");
  if (status.setup_complete) { $("#onboarding").classList.add("hidden"); return; }
  showOnboarding(refreshGlobal, navigate, state.shops.length ? 2 : 1);
}

export function showOnboarding(refreshGlobal, navigate, initialStep = 1) {
  step = initialStep; $("#onboarding").classList.remove("hidden"); renderStep(refreshGlobal, navigate);
}
function setIndicator() { $$('[data-wizard-indicator]').forEach((item) => item.classList.toggle("active", Number(item.dataset.wizardIndicator) === step)); }
function renderStep(refreshGlobal, navigate) {
  setIndicator(); const root = $("#onboarding-main");
  if (step === 1) {
    root.innerHTML = `<p class="section-kicker">STEP 1 OF 3</p><h2>创建你的店铺</h2><p class="helper-text">数据默认保存在本机 SQLite。拼多多授权可以现在填写，也可以稍后补充。</p><form id="wizard-shop-form" class="form-grid"><label class="field full"><span>店铺名称 *</span><input id="wizard-shop-name" required placeholder="例如：我的家居店"></label><label class="field full"><span>Client ID</span><input id="wizard-client-id"></label><label class="field"><span>Client Secret</span><input id="wizard-client-secret" type="password"></label><label class="field"><span>Access Token</span><input id="wizard-access-token" type="password"></label><div class="card-actions full"><button class="button primary" type="submit">保存并继续</button></div></form>`;
    $("#wizard-shop-form").addEventListener("submit", async (event) => { event.preventDefault(); setLoading(event.submitter, true, "保存中…"); try { await jsonApi("/api/shops", "POST", { name: $("#wizard-shop-name").value.trim(), client_id: $("#wizard-client-id").value.trim() || null, client_secret: $("#wizard-client-secret").value || null, access_token: $("#wizard-access-token").value || null }); await refreshGlobal(); step = 2; renderStep(refreshGlobal, navigate); } catch (error) { toast(error.message, "error"); } finally { setLoading(event.submitter, false); } }); return;
  }
  if (step === 2) {
    root.innerHTML = `<p class="section-kicker">STEP 2 OF 3</p><h2>配置 AI 或中转站</h2><p class="helper-text">可以跳过。确定性 SKU 诊断不依赖大模型。</p><form id="wizard-provider-form" class="form-grid"><label class="field"><span>名称</span><input id="wizard-provider-name" value="默认 AI"></label><label class="field"><span>类型</span><select id="wizard-provider-type"><option value="openai_compatible">OpenAI Compatible</option><option value="anthropic">Anthropic</option><option value="gemini">Gemini</option></select></label><label class="field full"><span>Base URL</span><input id="wizard-provider-url" value="https://api.openai.com/v1"></label><label class="field full"><span>API Key</span><input id="wizard-provider-key" type="password"></label><label class="field full"><span>聊天模型</span><input id="wizard-provider-model" placeholder="例如 gpt-5-mini / deepseek-chat"></label><div class="card-actions full"><button id="skip-ai" class="button ghost" type="button">稍后配置</button><button class="button primary" type="submit">保存并继续</button></div></form>`;
    $("#skip-ai").addEventListener("click", () => { step = 3; renderStep(refreshGlobal, navigate); });
    $("#wizard-provider-form").addEventListener("submit", async (event) => { event.preventDefault(); const key = $("#wizard-provider-key").value.trim(); if (!key) { step = 3; renderStep(refreshGlobal, navigate); return; } setLoading(event.submitter, true, "保存中…"); try { await jsonApi("/api/ai/providers", "POST", { name: $("#wizard-provider-name").value.trim() || "默认 AI", provider_type: $("#wizard-provider-type").value, base_url: $("#wizard-provider-url").value.trim(), api_key: key, chat_model: $("#wizard-provider-model").value.trim() || null }); await refreshGlobal(); step = 3; renderStep(refreshGlobal, navigate); } catch (error) { toast(error.message, "error"); } finally { setLoading(event.submitter, false); } }); return;
  }
  root.innerHTML = `<p class="section-kicker">STEP 3 OF 3</p><h2>准备经营数据</h2><p class="helper-text">推荐先到数据中心运行拼多多能力检测和首次同步。没有真实数据时，也可以先创建演示数据。</p><div class="stack"><button id="wizard-data-center" class="button primary full">进入数据中心</button><button id="wizard-demo" class="button ghost full">创建演示数据并开始体验</button></div>`;
  $("#wizard-data-center").addEventListener("click", () => { $("#onboarding").classList.add("hidden"); navigate("data"); });
  $("#wizard-demo").addEventListener("click", async (event) => { if (!state.selectedShopId) return; setLoading(event.currentTarget, true, "创建中…"); try { await api(`/api/workspace/demo?shop_id=${state.selectedShopId}`, { method: "POST" }); $("#onboarding").classList.add("hidden"); toast("演示数据已创建", "success"); navigate("dashboard"); } catch (error) { toast(error.message, "error"); } finally { setLoading(event.currentTarget, false); } });
}
