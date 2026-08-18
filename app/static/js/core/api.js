export async function api(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(String(data?.detail || data?.message || data || `请求失败 (${response.status})`));
  return data;
}

export function jsonApi(url, method, payload) {
  return api(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}

export function uploadApi(url, formData) {
  return api(url, { method: "POST", body: formData });
}
