import { jsonRequest, request } from './http.js'

export const listOptimizationTasks = (shopId, status = 'all') => request(`/api/optimization/tasks?shop_id=${shopId}&status=${encodeURIComponent(status)}`)
export const createTaskFromDiagnosis = (diagnosisId, payload) => jsonRequest(`/api/optimization/diagnoses/${diagnosisId}/tasks`, 'POST', payload)
export const createManualTask = (payload) => jsonRequest('/api/optimization/tasks', 'POST', payload)
export const startOptimizationTask = (taskId) => request(`/api/optimization/tasks/${taskId}/start`, { method: 'POST' })
export const completeOptimizationTask = (taskId, executionNote = '') => jsonRequest(`/api/optimization/tasks/${taskId}/complete`, 'POST', { execution_note: executionNote })
export const cancelOptimizationTask = (taskId) => request(`/api/optimization/tasks/${taskId}/cancel`, { method: 'POST' })
export const refreshOptimizationTask = (taskId) => request(`/api/optimization/tasks/${taskId}/reviews/refresh`, { method: 'POST' })
export const refreshShopOptimizationReviews = (shopId) => request(`/api/optimization/shops/${shopId}/reviews/refresh`, { method: 'POST' })
