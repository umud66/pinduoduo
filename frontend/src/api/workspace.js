import { request } from './http.js'

export const getDashboard = (shopId) => request(`/api/dashboard?shop_id=${shopId}`)
export const listSkus = (shopId, q = '', severity = 'all') => request(`/api/skus?shop_id=${shopId}&q=${encodeURIComponent(q)}&severity=${encodeURIComponent(severity)}`)
export const getSku = (skuId) => request(`/api/skus/${skuId}`)
export const getSkuInsights = (skuId) => request(`/api/skus/${skuId}/insights`)
export const getShopTrendOverview = (shopId, limit = 8) => request(`/api/shops/${shopId}/trend-overview?limit=${limit}`)
export const seedDemo = (shopId) => request(`/api/workspace/demo?shop_id=${shopId}`, { method: 'POST' })
