import { apiRequest } from './api.js'
import { getToken } from './auth.js'

export function getLowStockProducts({ skip = 0, limit = 5 } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  return apiRequest(`/products/low-stock?${params}`, { token: getToken() })
}
