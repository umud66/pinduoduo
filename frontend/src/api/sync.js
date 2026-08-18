import { jsonRequest, request } from './http.js'
export const getSyncStatus = (shopId) => request(`/api/sync/shops/${shopId}/status`)
export const startSync = (shopId, type) => request(`/api/sync/shops/${shopId}/${type}${type === 'full' ? '?lookback_days=30' : ''}`, { method: 'POST' })
export const retrySync = (jobId) => request(`/api/sync/jobs/${jobId}/retry`, { method: 'POST' })
export const saveSyncPreference = (shopId, payload) => jsonRequest(`/api/sync/shops/${shopId}/preference`, 'PUT', payload)
export const probeCapabilities = (shopId) => request(`/api/pdd/shops/${shopId}/probe`, { method: 'POST' })
