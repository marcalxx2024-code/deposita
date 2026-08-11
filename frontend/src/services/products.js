import { apiRequest } from './api.js'
import { getToken } from './auth.js'

function authenticatedRequest(path, options) {
  return apiRequest(path, { ...options, token: getToken() })
}

export function listProducts({ page = 1, pageSize = 20, ...filters } = {}) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })

  for (const [key, value] of Object.entries(filters)) {
    if (value !== '' && value !== undefined && value !== null) {
      params.set(key, String(value))
    }
  }

  return authenticatedRequest(`/products?${params}`)
}

export function getProduct(productId) {
  return authenticatedRequest(`/products/${productId}`)
}

export function getLowStockProducts({ skip = 0, limit = 5 } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  return authenticatedRequest(`/products/low-stock?${params}`)
}

export function createProduct(product) {
  return authenticatedRequest('/products', { method: 'POST', body: product })
}

export function updateProduct(productId, product) {
  return authenticatedRequest(`/products/${productId}`, { method: 'PUT', body: product })
}

export function deactivateProduct(productId) {
  return authenticatedRequest(`/products/${productId}`, { method: 'DELETE' })
}

export function reactivateProduct(productId) {
  return authenticatedRequest(`/products/${productId}/reactivate`, { method: 'POST' })
}
