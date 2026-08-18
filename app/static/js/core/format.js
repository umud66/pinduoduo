export function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
export function money(value) { return `¥${Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }
export function number(value) { return Number(value || 0).toLocaleString("zh-CN"); }
export function percent(value, digits = 1) { if (value === null || value === undefined || Number.isNaN(Number(value))) return "—"; return `${(Number(value) * 100).toFixed(digits)}%`; }
export function severityLabel(value) { return { high: "严重", medium: "关注", low: "轻微", healthy: "健康", unrun: "未诊断" }[value] || "未知"; }
export function dateTime(value) { if (!value) return "从未"; const date = new Date(value); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN"); }
