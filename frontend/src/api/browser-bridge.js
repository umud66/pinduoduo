import { jsonRequest, request } from './http.js'

export const getBrowserBridgeStatus = () => request('/api/browser-bridge/status')
export const startBrowserBridge = (payload) => jsonRequest('/api/browser-bridge/sessions', 'POST', payload)
export const stopBrowserBridge = () => jsonRequest('/api/browser-bridge/sessions/stop', 'POST', {})
export const listBrowserBridgeSessions = (shopId, limit = 20) => request(`/api/browser-bridge/shops/${shopId}/sessions?limit=${limit}`)
export const getBrowserBridgeSession = (sessionId) => request(`/api/browser-bridge/sessions/${sessionId}`)
export const listBrowserBridgeRecords = (sessionId, category = 'all', limit = 80) => {
  const params = new URLSearchParams({ limit: String(limit) })
  if (category !== 'all') params.set('category', category)
  return request(`/api/browser-bridge/sessions/${sessionId}/records?${params}`)
}
