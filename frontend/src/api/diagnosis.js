import { request } from './http.js'
export const diagnoseSku = (skuId) => request(`/api/diagnosis/skus/${skuId}`, { method: 'POST' })
export const diagnoseShop = (shopId) => request(`/api/diagnosis/shops/${shopId}/run`, { method: 'POST' })
export const analyzeDiagnosis = (diagnosisId, providerId) => request(`/api/diagnosis/${diagnosisId}/ai?provider_id=${providerId}`, { method: 'POST' })
