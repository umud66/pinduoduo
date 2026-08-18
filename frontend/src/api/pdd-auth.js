import { jsonRequest, request } from './http.js'

export const getPddApplication = () => request('/api/pdd/application')
export const savePddApplication = (payload) => jsonRequest('/api/pdd/application', 'PUT', payload)
export const getPddAuthorization = (shopId) => request(`/api/pdd/shops/${shopId}/authorization`)
export const startPddAuthorization = (shopId) => jsonRequest(`/api/pdd/shops/${shopId}/authorization/start`, 'POST', {})
export const completePddAuthorization = (state, code) => jsonRequest('/api/pdd/authorization/complete', 'POST', { state, code })
export const refreshPddAuthorization = (shopId) => jsonRequest(`/api/pdd/shops/${shopId}/authorization/refresh`, 'POST', {})
export const disconnectPddAuthorization = (shopId) => request(`/api/pdd/shops/${shopId}/authorization`, { method: 'DELETE' })
export const probeAuthorizedShop = (shopId) => jsonRequest(`/api/pdd/shops/${shopId}/probe`, 'POST', {})
