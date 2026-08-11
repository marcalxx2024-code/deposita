import { apiRequest } from './api.js'
import { getToken } from './auth.js'

export function getRecentMovements({ skip = 0, limit = 5 } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  return apiRequest(`/movements?${params}`, { token: getToken() })
}

export function createStockMovement(productId, movementType, movement) {
  return apiRequest(`/products/${productId}/movements/${movementType}`, {
    method: 'POST',
    body: { ...movement, movement_type: movementType },
    token: getToken(),
  })
}
