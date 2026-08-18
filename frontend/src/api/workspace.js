import { request } from './http.js'
export const getDashboard = (shopId) => request(`/api/dashboard?shop_id=${shopId}`)
export const listSkus = (shopId, q = '', severity = 'all') => request(`/api/skus?shop_id=${shopId}&q=${encodeURIComponent(q)}&severity=${encodeURIComponent(severity)}`)
export const getSku = (skuId) => request(`/api/skus/${skuId}`)
export const seedDemo = (shopId) => request(`/api/workspace/demo?shop_id=${shopId}`, { method: 'POST' })
