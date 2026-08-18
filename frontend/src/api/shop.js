import { jsonRequest, request } from './http.js'
export const listShops = () => request('/api/shops')
export const createShop = (payload) => jsonRequest('/api/shops', 'POST', payload)
export const updateShop = (id, payload) => jsonRequest(`/api/shops/${id}`, 'PUT', payload)
