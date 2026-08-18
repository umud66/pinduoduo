import { jsonRequest, request } from './http.js'
export const listProviders = () => request('/api/ai/providers')
export const createProvider = (payload) => jsonRequest('/api/ai/providers', 'POST', payload)
export const testProvider = (id) => request(`/api/ai/providers/${id}/test`, { method: 'POST' })
export const deleteProvider = (id) => request(`/api/ai/providers/${id}`, { method: 'DELETE' })
export const aiChat = (providerId, prompt) => jsonRequest(`/api/ai/providers/${providerId}/chat`, 'POST', { prompt })
export const generateImage = (providerId, prompt, size = '1024x1024') => jsonRequest(`/api/ai/providers/${providerId}/images`, 'POST', { prompt, size })
