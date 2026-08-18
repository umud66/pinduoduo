import { escapeHtml, money, percent, severityLabel } from "../core/format.js";

const EVIDENCE_LABELS = {
  current: "当前值", baseline: "基线值", change: "变化",
  current_impression: "当前曝光", baseline_impression: "基线曝光",
  current_ctr: "当前 CTR", baseline_ctr: "基线 CTR",
  current_cvr: "当前 CVR", baseline_cvr: "基线 CVR",
  current_aov: "当前客单价", baseline_aov: "基线客单价",
  current_price: "当前价格", baseline_price: "基线价格",
  price_change: "价格变化", sales_change: "销量变化",
  current_refund_rate: "当前退款率", baseline_refund_rate: "基线退款率",
  refund_count: "退款数", order_count: "订单数", stock: "库存",
  sales_qty: "销量", sellable_days: "可售天数", ad_cost: "推广花费",
  current_roi: "当前 ROI", baseline_roi: "基线 ROI", impression: "曝光", clicks: "点击",
};

function confidenceLabel(value) {
  const n = Number(value || 0);
  if (n >= 0.85) return "高置信";
  if (n >= 0.65) return "中等置信";
  return "低置信";
}

function dataConfidenceLabel(value) {
  return { high: "数据较完整", medium: "数据可用", low: "数据不足" }[value] || "数据状态未知";
}

function evidenceValue(key, value) {
  if (value === null || value === undefined) return "—";
  if (["change", "price_change", "sales_change", "current_ctr", "baseline_ctr", "current_cvr", "baseline_cvr", "current_refund_rate", "baseline_refund_rate"].includes(key)) return percent(value);
  if (["current_aov", "baseline_aov", "current_price", "baseline_price", "ad_cost"].includes(key)) return money(value);
  if (key.includes("roi")) return Number(value).toFixed(2);
  if (key === "sellable_days") return `${Number(value).toFixed(1)} 天`;
  return Number.isFinite(Number(value)) ? Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 }) : String(value);
}

function renderOverview(diagnosis) {
  const quality = diagnosis.data_quality || {};
  const decomposition = diagnosis.decomposition || {};
  const top = diagnosis.issues?.[0];
  return `<article class="diagnosis-overview">
    <div class="diagnosis-score"><small>健康分</small><strong>${diagnosis.health_score ?? "—"}</strong><span class="status-pill ${diagnosis.severity || "healthy"}">${severityLabel(diagnosis.severity || "healthy")}</span></div>
    <div class="diagnosis-summary"><p class="section-kicker">OPERATING CONCLUSION</p><h3>${escapeHtml(diagnosis.summary || "暂无诊断结论")}</h3>
      <div class="diagnosis-meta"><span>数据覆盖 ${quality.coverage_score ?? 0}%</span><span>${escapeHtml(dataConfidenceLabel(quality.confidence))}</span><span>基线 ${quality.baseline_days ?? diagnosis.baseline_days ?? 0} 天</span>${Number(decomposition.estimated_gmv_loss || 0) > 0 ? `<span class="loss-text">估算 GMV 缺口 ${money(decomposition.estimated_gmv_loss)}</span>` : ""}</div>
      ${top ? `<div class="root-cause-line"><strong>当前第一优先级：</strong>${escapeHtml(top.title)} · 优先级 ${top.priority_score} · ${confidenceLabel(top.confidence)}</div>` : ""}
    </div></article>`;
}

function renderDecomposition(diagnosis) {
  const decomposition = diagnosis.decomposition || {};
  const factors = decomposition.factors || [];
  if (!factors.length) return `<article class="card compact"><div class="card-heading"><div><p class="section-kicker">GMV DECOMPOSITION</p><h3>GMV 归因</h3></div><span class="status-pill neutral">数据不足</span></div><p class="helper-text">当前缺少完整漏斗或订单价值数据，系统不会强行分摊 GMV 变化原因。</p></article>`;
  const maxLoss = Math.max(...factors.map((item) => Number(item.estimated_loss || 0)), 1);
  return `<article class="card compact"><div class="card-heading"><div><p class="section-kicker">GMV DECOMPOSITION</p><h3>GMV 下降贡献拆解</h3></div><span class="status-pill neutral">${decomposition.mode === "full_funnel" ? "完整漏斗" : "订单 × 客单价"}</span></div><div class="decomposition-list">${factors.map((factor) => { const loss = Number(factor.estimated_loss || 0); const width = Math.max(loss > 0 ? 4 : 0, Math.min(100, loss / maxLoss * 100)); return `<div class="decomposition-row"><div class="decomposition-label"><strong>${escapeHtml(factor.label)}</strong><span>${factor.change === null || factor.change === undefined ? "—" : percent(factor.change)}</span></div><div class="factor-bar"><span style="width:${width}%"></span></div><div class="factor-loss">${loss > 0 ? money(loss) : "—"}</div></div>`; }).join("")}</div><p class="helper-text">估算损失用于排序和定位，不等同于财务归因；多个因素可能同时变化。</p></article>`;
}

function renderEvidence(evidence = {}) {
  const entries = Object.entries(evidence).filter(([, value]) => value !== null && value !== undefined);
  if (!entries.length) return "";
  return `<details class="diagnosis-evidence"><summary>查看触发依据</summary><div class="evidence-grid">${entries.map(([key, value]) => `<div><small>${escapeHtml(EVIDENCE_LABELS[key] || key)}</small><strong>${escapeHtml(evidenceValue(key, value))}</strong></div>`).join("")}</div></details>`;
}

function renderIssue(issue, index) {
  const validation = issue.validation_metrics || [];
  const actions = issue.actions || [];
  return `<article class="diagnosis-issue ${escapeHtml(issue.severity || "low")}"><header><div><p class="section-kicker">PRIORITY ${index + 1}</p><h3>${escapeHtml(issue.title || issue.code)}</h3></div><div class="issue-scores"><span class="status-pill ${escapeHtml(issue.severity || "low")}">${severityLabel(issue.severity)}</span><strong>${issue.priority_score ?? "—"}</strong></div></header><p class="diagnosis-reason">${escapeHtml(issue.reason || "")}</p><div class="diagnosis-tags"><span>影响度 ${issue.impact_score ?? "—"}</span><span>${confidenceLabel(issue.confidence)} ${Math.round(Number(issue.confidence || 0) * 100)}%</span>${Number(issue.estimated_loss || 0) > 0 ? `<span class="loss-text">估算缺口 ${money(issue.estimated_loss)}</span>` : ""}</div>${renderEvidence(issue.evidence)}${actions.length ? `<div class="action-plan"><strong>建议动作</strong><ol>${actions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}</ol></div>` : ""}${validation.length ? `<div class="validation-plan"><strong>验证指标</strong><div>${validation.map((metric) => `<span>${escapeHtml(metric)}</span>`).join("")}</div></div>` : ""}</article>`;
}

function renderAIAnalysis(diagnosis) {
  const ai = diagnosis.ai_analysis;
  if (!ai?.text) return "";
  return `<article class="card ai-diagnosis"><div class="card-heading"><div><p class="section-kicker">AI FOLLOW-UP</p><h3>AI 运营建议</h3></div><span class="status-pill neutral">${escapeHtml(ai.model || "AI")}</span></div><div class="ai-result">${escapeHtml(ai.text)}</div></article>`;
}

export function renderDiagnosisPanel(diagnosis) {
  if (!diagnosis) return '<div class="empty-state">尚未运行诊断</div>';
  const issues = diagnosis.issues || diagnosis.problems || [];
  return `<div class="diagnosis-panel">${renderOverview(diagnosis)}${renderDecomposition(diagnosis)}<section class="diagnosis-section"><div class="card-heading"><div><p class="section-kicker">PRIORITY QUEUE</p><h3>问题优先级</h3></div><span class="muted">${issues.length} 项</span></div>${issues.length ? `<div class="diagnosis-issue-list">${issues.map(renderIssue).join("")}</div>` : '<div class="empty-state">当前样本下未发现达到规则阈值的明显异常。</div>'}</section>${renderAIAnalysis(diagnosis)}</div>`;
}
