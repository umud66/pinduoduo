export async function request(path, options = {}) {
  const response = await fetch(path, options)
  const text = await response.text()
  let payload = null
  try { payload = text ? JSON.parse(text) : null } catch { payload = text }
  if (!response.ok) {
    const message = payload?.detail || payload?.message || payload || `请求失败 (${response.status})`
    throw new Error(String(message))
  }
  return payload
}

export function jsonRequest(path, method, body) {
  return request(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
