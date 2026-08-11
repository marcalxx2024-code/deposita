import { apiRequest } from './api.js'
import { getToken } from './auth.js'

function authenticatedRequest(path, options) {
  return apiRequest(path, { ...options, token: getToken() })
}

export function listSuppliers({ skip = 0, limit = 20 } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  return authenticatedRequest(`/suppliers?${params}`)
}

export function createSupplier(supplier) {
  return authenticatedRequest('/suppliers', { method: 'POST', body: supplier })
}

export function updateSupplier(supplierId, supplier) {
  return authenticatedRequest(`/suppliers/${supplierId}`, { method: 'PUT', body: supplier })
}

export function deleteSupplier(supplierId) {
  return authenticatedRequest(`/suppliers/${supplierId}`, { method: 'DELETE' })
}
